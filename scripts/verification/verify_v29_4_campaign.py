"""Offline v29.4 acceptance: synthetic execution, frozen baseline and no network."""
import argparse
from contextlib import ExitStack, redirect_stdout
import hashlib
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
    from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
    from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
    from src.skill_evolution.v29_2 import config as previous
    from src.skill_evolution.v29_4 import config
    from src.skill_evolution.v29_4.campaign import CampaignAdapter, DEFAULT_CONFIG
    from scripts.runs import run_v29_4_campaign as cli

    old = json.loads((ROOT / 'experiments/configs/v29_2_docvqa_optimization160_references_v4.json').read_text())
    new = json.loads(DEFAULT_CONFIG.read_text())
    with CampaignAdapter(DocVQAActorAdapter(DocVQADataset())).using():
        previous.validate_config(old, executable=True)
        config.validate_config(new, executable=True)
        before, after = previous.render_prompts(), config.render_prompts()
    expected = json.loads(json.dumps(old))
    del expected['module_calls']['grouping']
    assert expected['module_calls']['editor']['max_tokens'] == 16384
    expected['module_calls']['editor']['max_tokens'] = 32768
    method = expected['method']
    for section in ('prompts', 'contracts', 'execution_input_views'):
        del method[section]['grouping']
        for module in ('diagnosis', 'preconditioner'):
            method[section][module] = new['method'][section][module]
    for key in ('version', 'stage_contract'):
        method[key] = new['method'][key]
    assert expected == new, 'Configuration changed outside Grouping removal and authorized Editor budget increase'
    assert set(before) - set(after) == {'grouping'}
    assert [name for name in after if before[name] != after[name]] == ['diagnosis', 'preconditioner']
    with tempfile.TemporaryDirectory() as temporary:
        campaign = Path(temporary) / 'not_created'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('Credentials forbidden')), \
             patch.object(cli, 'run_training', side_effect=AssertionError('Live training forbidden')), \
             patch.object(cli, 'run_test', side_effect=AssertionError('Live Test forbidden')):
            cli.main(['train', str(campaign), '--config', str(DEFAULT_CONFIG), '--validate-only'])
        assert not campaign.exists(), 'Preflight created a campaign'
    return {'method': config.METHOD_VERSION, 'modules': list(config.MODEL_MODULES),
            'batch_sizes': list(map(len, new['batches'])),
            'module_max_tokens': {k: v['max_tokens'] for k, v in new['module_calls'].items()},
            'editor_max_tokens_change': {'baseline': 16384, 'current': 32768},
            'other_config_unchanged': True, 'editor_replay_prompts_unchanged': True,
            'full_dataset_cli_preflight': 'passed_without_credentials_or_campaign'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline', required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve(); output.mkdir(parents=True, exist_ok=True)
    baseline = json.loads(Path(args.baseline).read_text())
    blocked, counts, checks, error = [], {}, {}, None

    def deny(*args, **kwargs):
        blocked.append('network_or_process')
        raise AssertionError('Network/process calls forbidden in offline acceptance')

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', deny))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', deny))
        stack.enter_context(patch('socket.create_connection', deny))
        stack.enter_context(patch('subprocess.Popen', deny))
        suite = unittest.TestSuite()
        for version in ('v29', 'v29_1', 'v29_2', 'v29_3', 'v29_4'):
            part = unittest.defaultTestLoader.discover(str(ROOT / 'tests/skill_evolution' / version), top_level_dir=str(ROOT))
            counts[version] = part.countTestCases()
            suite.addTests(part)
        with (output / 'unittest.log').open('w') as log, redirect_stdout(log):
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
            try:
                checks = verify_config()
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'
    changed = [name for name, digest in baseline.items()
               if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    passed = result.wasSuccessful() and not result.skipped and not blocked and error is None and not changed
    source_root = ROOT / 'src/skill_evolution/v29_4'
    report = {'status': 'passed' if passed else 'failed', 'test_counts': counts,
              'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': len(result.skipped), 'checks': checks, 'check_error': error,
              'protected_files': len(baseline), 'changed_baseline_files': changed,
              'blocked_network_or_process_attempts': blocked,
              'real_training_or_test_started': False,
              'implementation_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in sorted(source_root.rglob('*'))
                                        if p.is_file() and p.suffix in ('.py', '.md')}}
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('status', 'test_counts', 'tests_run', 'failures', 'errors',
                                                  'changed_baseline_files', 'check_error')}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
