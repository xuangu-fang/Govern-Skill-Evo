"""Offline v28.5 integration checks; no model calls or real training/Test."""
import argparse
import base64
from contextlib import ExitStack, redirect_stdout
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]


def verify_config():
    from scripts.runs import run_v28_5_campaign as cli
    from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
    from src.skill_evolution.v28_5.actor_io import ActorAdapter
    from src.skill_evolution.v28_5.campaign import CampaignAdapter, RUNTIME_VERSION
    from src.skill_evolution.v28_5 import config

    docs = ROOT / 'docs/methods/v28_5'
    baseline = json.loads((docs / 'baseline/v28_3_config.json').read_text())
    actual = json.loads(config.DEFAULT_CONFIG.read_text())
    assert json.loads(json.dumps(actual).replace('v28_5', 'v28_3')) == baseline
    data = SearchQADataset(batch_size=30, verify_hashes=False)
    with CampaignAdapter(ActorAdapter(data)).using():
        config.validate_config(actual, executable=True)
        prompts = config.render_prompts()
    for name, text in prompts.items():
        assert text.encode('utf-8') == (docs / f'prompts/{name}.md').read_bytes()
    planned = json.loads((docs / 'source_map.json').read_text())['planned_identity']
    assert planned['method'] == actual['method']['version']
    assert planned['stage'] == actual['method']['stage_contract']
    assert planned['runtime'] == RUNTIME_VERSION
    for key in ('prompts', 'contracts', 'memory_view', 'replay_input_view'):
        assert planned[key] == actual['method'][key], key
    assert set(actual['method']['execution_input_views'].values()) == {planned['execution_input_view']}
    source_names = sorted(p.name for p in (ROOT / 'src/skill_evolution/v28_3').glob('*.py'))
    assert source_names == sorted(p.name for p in (ROOT / 'src/skill_evolution/v28_5').glob('*.py'))
    for name in source_names:
        old = (ROOT / 'src/skill_evolution/v28_3' / name).read_text()
        new = (ROOT / 'src/skill_evolution/v28_5' / name).read_text()
        assert old.replace('v28_3', 'v28_5').replace('v28.3', 'v28.5') == new, name
    old_cli = (ROOT / 'scripts/runs/run_v28_3_campaign.py').read_text()
    assert old_cli.replace('v28_3', 'v28_5').replace('v28.3', 'v28.5') == Path(cli.__file__).read_text()
    with tempfile.TemporaryDirectory(prefix='v28_5_preflight_') as temporary:
        campaign = Path(temporary) / 'not_created'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('No credentials')), \
             patch.object(cli, 'run_training', side_effect=AssertionError('No live training')), \
             patch.object(cli, 'run_test', side_effect=AssertionError('No live Test')):
            cli.main(['train', str(campaign), '--config', str(config.DEFAULT_CONFIG), '--validate-only'])
        assert not campaign.exists()
    return {'method': config.METHOD_VERSION, 'runtime': RUNTIME_VERSION,
            'all_runtime_sources_and_cli_identical_after_version_substitution': True,
            'runtime_source_files_compared': len(source_names),
            'reviewed_prompts_bound_verbatim': list(prompts),
            'configuration_identical_except_version_identities': True,
            'batch_sizes': list(map(len, actual['batches'])), 'test_count': len(data.splits['test']),
            'module_max_tokens': {k: v['max_tokens'] for k, v in actual['module_calls'].items()},
            'full_dataset_preflight': 'passed_without_credentials_or_campaign'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline', required=True, help='Pre-implementation byte snapshot')
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    baseline = json.loads(Path(args.baseline).read_text())
    # v28.5 design status documents evolve during implementation; approved
    # prompts and every pre-existing v28.3 source remain protected byte-for-byte.
    protected = {name: value for name, value in baseline.items()
                 if not name.startswith('docs/methods/v28_5/') or
                 name.startswith(('docs/methods/v28_5/prompts/', 'docs/methods/v28_5/baseline/'))}
    assert protected
    blocked, counts, checks, error = [], {}, {}, None

    def deny(*args, **kwargs):
        blocked.append('network_or_process')
        raise AssertionError('Network/process calls forbidden in offline checks')

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', deny))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', deny))
        stack.enter_context(patch('socket.create_connection', deny))
        stack.enter_context(patch('subprocess.Popen', deny))
        suite = unittest.TestSuite()
        for version in ('v28_3', 'v28_5'):
            part = unittest.defaultTestLoader.discover(str(ROOT / 'tests/skill_evolution' / version),
                                                       top_level_dir=str(ROOT))
            counts[version] = part.countTestCases()
            suite.addTests(part)
        with (output / 'unittest.log').open('w') as log, redirect_stdout(log):
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
            try:
                checks = verify_config()
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'
    changed = [name for name, value in protected.items()
               if not (ROOT / name).is_file() or (ROOT / name).read_bytes() != base64.b64decode(value)]
    passed = result.wasSuccessful() and not result.skipped and not blocked and error is None and not changed
    report = {'status': 'passed' if passed else 'failed', 'test_counts': counts,
              'python_executable': sys.executable, 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
              'checks': checks, 'check_error': error, 'protected_files': len(protected),
              'changed_baseline_or_prompt_files': changed, 'blocked_network_or_process_attempts': blocked,
              'real_model_calls': 0, 'real_training_or_test_started': False,
              'scope': 'Inherited synthetic software tests and read-only real-data preflight; no prompt behavior scenarios.'}
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
