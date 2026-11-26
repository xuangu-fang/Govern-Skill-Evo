"""SearchQA-only v28.4 offline acceptance; no DocVQA suite or environment required."""
import argparse
import base64
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import json
import importlib.abc
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]


def searchqa_baseline_path(name):
    """Exclude other benchmarks even when given the original broad snapshot."""
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        return False
    for prefix in ('src/skill_evolution', 'tests/skill_evolution', 'docs/methods'):
        if any(name.startswith(f'{prefix}/{version}/')
               for version in ('v28', 'v28_1', 'v28_2', 'v28_3')):
            return True
    if name.startswith('experiments/configs/'):
        return 'searchqa' in path.name and not path.name.startswith('v28_4')
    if name.startswith(('experiments/campaigns/v28_2_searchqa',
                        'experiments/automations/v28_2_searchqa')):
        return True
    return name in ('scripts/runs/run_v28_2_campaign.py',
                    'scripts/runs/run_v28_3_campaign.py',
                    'scripts/verification/verify_v28_2_campaign.py',
                    'scripts/verification/verify_v28_3_campaign.py',
                    'scripts/runs/run_searchqa_skilladam.py',
                    'src/skill_evolution/v29_2/execution_references.py',
                    'src/skill_evolution/v29_2/explicit_references.py')


def verify_config():
    from scripts.runs import run_v28_4_campaign as cli
    from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
    from src.skill_evolution.v28_4.actor_io import ActorAdapter
    from src.skill_evolution.v28_4.campaign import CampaignAdapter
    from src.skill_evolution.v28_4 import config

    baseline = json.loads((ROOT / 'docs/methods/v28_4/baseline/v28_3_config.json').read_text())
    actual = json.loads(config.DEFAULT_CONFIG.read_text())
    normalized = json.loads(json.dumps(actual).replace('v28_4', 'v28_3'))
    assert normalized == baseline, 'Frozen SearchQA configuration changed beyond version identities'
    with CampaignAdapter(ActorAdapter(SearchQADataset(batch_size=30, verify_hashes=False))).using():
        config.validate_config(actual, executable=True)
        prompts = config.render_prompts()
    spec = json.loads((ROOT / 'docs/methods/v28_4/source_map.json').read_text())
    assert {k: v['max_tokens'] for k, v in actual['module_calls'].items()} == {
        'diagnosis': 65536, 'preconditioner': 65536, 'editor': 32768, 'replay': 65536}
    assert spec['preserved_runtime']['module_max_tokens'] == {k: v['max_tokens'] for k, v in actual['module_calls'].items()}
    assert spec['planned_identity']['contracts'] == actual['method']['contracts']
    assert {k: v['planned_prompt_version'] for k, v in spec['prompts'].items()} == actual['method']['prompts']
    for name, value in prompts.items():
        assert value == (ROOT / f'docs/methods/v28_4/prompts/{name}.md').read_text()
    assert prompts['replay'] == (ROOT / 'docs/methods/v28_4/baseline/prompts/replay_v28_3.md').read_text()
    planned = deepcopy(spec['planned_identity'])
    assert planned.pop('runtime') == 'v28_4_light_runtime_v1'
    assert planned.pop('gate_rule') == actual['gate_rule']
    assert planned == actual['method']
    with tempfile.TemporaryDirectory(prefix='v28_4_preflight_') as temporary:
        campaign = Path(temporary) / 'not_created'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('No credentials')), \
             patch.object(cli, 'run_training', side_effect=AssertionError('No live training')), \
             patch.object(cli, 'run_test', side_effect=AssertionError('No live Test')):
            cli.main(['train', str(campaign), '--config', str(config.DEFAULT_CONFIG), '--validate-only'])
        assert not campaign.exists(), 'Preflight created a campaign'
    assert not any((ROOT / 'src/skill_evolution/v28_4').glob('grouping*'))
    return {'method': config.METHOD_VERSION, 'modules': list(config.MODEL_MODULES),
            'batch_sizes': list(map(len, actual['batches'])), 'test_count': 1400,
            'module_max_tokens': spec['preserved_runtime']['module_max_tokens'],
            'other_searchqa_configuration_unchanged': True, 'replay_prompt_unchanged': True,
            'full_dataset_preflight': 'passed_without_credentials_or_campaign'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline', required=True, help='Pre-implementation files encoded as base64, not hashes')
    parser.add_argument('--suite', choices=('searchqa',), default='searchqa',
                        help='SearchQA only (default); other benchmark suites are outside acceptance')
    args = parser.parse_args(argv)
    output = Path(args.output).resolve(); output.mkdir(parents=True, exist_ok=True)
    baseline = json.loads(Path(args.baseline).read_text())
    excluded_baseline_count = sum(not searchqa_baseline_path(name) for name in baseline)
    baseline = {name: content for name, content in baseline.items() if searchqa_baseline_path(name)}
    assert baseline, 'A nonempty pre-implementation SearchQA baseline is required'
    blocked, counts, checks, error = [], {}, {}, None

    def deny(*args, **kwargs):
        blocked.append('network_or_process')
        raise AssertionError('Network/process calls forbidden in offline acceptance')

    class NoDocVQA(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if 'docvqa' in fullname.lower() or fullname == 'PIL' or fullname.startswith('PIL.'):
                blocked.append('forbidden_import:' + fullname)
                raise AssertionError('DocVQA/Pillow is not a SearchQA acceptance dependency')
            return None

    with ExitStack() as stack:
        finder = NoDocVQA()
        sys.meta_path.insert(0, finder)
        stack.callback(sys.meta_path.remove, finder)
        stack.enter_context(patch.object(socket.socket, 'connect', deny))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', deny))
        stack.enter_context(patch('socket.create_connection', deny))
        stack.enter_context(patch('subprocess.Popen', deny))
        suite = unittest.TestSuite()
        versions = ('v28', 'v28_1', 'v28_2', 'v28_3', 'v28_4')
        for version in versions:
            part = unittest.defaultTestLoader.discover(str(ROOT / 'tests/skill_evolution' / version),
                                                       top_level_dir=str(ROOT))
            counts[version] = part.countTestCases(); suite.addTests(part)
        with (output / 'unittest.log').open('w') as log, redirect_stdout(log):
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
            try:
                checks = verify_config()
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'
    changed = [name for name, content in baseline.items()
               if not (ROOT / name).is_file() or (ROOT / name).read_bytes() != base64.b64decode(content)]
    prompt_changes = [name for name in ('diagnosis', 'preconditioner', 'editor', 'replay')
                      if (Path(args.baseline).resolve().parent / f'design_before/prompts/{name}.md').read_bytes() !=
                      (ROOT / f'docs/methods/v28_4/prompts/{name}.md').read_bytes()]
    archive_manifest = json.loads((Path(args.baseline).resolve().parent / 'protected_experiments_before.json').read_text())
    archive_before = archive_manifest['files']
    archive_after = {str(p.relative_to(ROOT)): [p.stat().st_size, p.stat().st_mtime_ns]
                     for name in archive_manifest['roots'] for p in (ROOT / name).rglob('*') if p.is_file()}
    archive_changes = sorted(name for name in archive_before.keys() | archive_after.keys()
                             if archive_before.get(name) != archive_after.get(name))
    passed = not archive_changes and result.wasSuccessful() and not result.skipped and not blocked and error is None and not changed and not prompt_changes
    report = {'status': 'passed' if passed else 'failed', 'test_counts': counts,
              'suite': args.suite, 'python_executable': sys.executable,
              'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': len(result.skipped), 'checks': checks, 'check_error': error,
              'protected_files': len(baseline), 'changed_baseline_files': changed,
              'out_of_scope_baseline_files_excluded': excluded_baseline_count,
              'required_benchmark': 'SearchQA', 'docvqa_required': False,
              'reviewed_prompt_changes': prompt_changes, 'docvqa_pillow_imports_blocked': True,
              'protected_experiment_files': len(archive_before), 'changed_experiment_inventory_or_metadata': archive_changes, 'blocked_network_or_process_attempts': blocked,
              'real_training_or_test_started': False,
              'scope': 'Synthetic offline execution plus read-only full SearchQA configuration validation'}
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('status', 'test_counts', 'tests_run', 'failures', 'errors',
                                                  'changed_baseline_files', 'check_error')}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
