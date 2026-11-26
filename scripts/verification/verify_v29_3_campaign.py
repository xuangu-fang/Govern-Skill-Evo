"""Network-blocked v29.3 acceptance and unchanged v29/v29.1/v29.2 regressions."""
import argparse
from contextlib import ExitStack, redirect_stdout
from datetime import datetime
import hashlib
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]


def verify_binding():
    from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
    from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
    from src.skill_evolution.v29_2 import config as old
    from src.skill_evolution.v29_3 import config as new
    from src.skill_evolution.v29_3.campaign import CampaignAdapter, DEFAULT_CONFIG
    from scripts.runs import run_v29_3_campaign as cli
    previous = json.loads((ROOT / 'experiments/configs/v29_2_docvqa_optimization160_references_v4.json').read_text())
    revised = json.loads(DEFAULT_CONFIG.read_text())
    with CampaignAdapter(DocVQAActorAdapter(DocVQADataset())).using():
        old.validate_config(previous, executable=True)
        new.validate_config(revised, executable=True)
        original_prompts, revised_prompts = old.render_prompts(), new.render_prompts()
    normalized = json.loads(json.dumps(revised))
    normalized['method']['version'] = previous['method']['version']
    for name in ('diagnosis', 'preconditioner'):
        normalized['method']['prompts'][name] = previous['method']['prompts'][name]
    assert revised['module_calls']['editor']['max_tokens'] == 32768
    normalized['module_calls']['editor']['max_tokens'] = previous['module_calls']['editor']['max_tokens']
    assert normalized == previous
    changed = [name for name in original_prompts if original_prompts[name] != revised_prompts[name]]
    assert changed == ['diagnosis', 'preconditioner']
    # The actual CLI preflight is exercised against the full frozen dataset;
    # no campaign directory, credentials or execution is allowed.
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / 'not_created'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('Credentials forbidden')), \
             patch.object(cli, 'run_training', side_effect=AssertionError('Live training forbidden')), \
             patch.object(cli, 'run_test', side_effect=AssertionError('Live Test forbidden')):
            cli.main(['train', str(output), '--config', str(DEFAULT_CONFIG), '--validate-only'])
        assert not output.exists()
    return {'method_version': new.METHOD_VERSION, 'config': str(DEFAULT_CONFIG.relative_to(ROOT)),
            'changed_system_prompts': changed,
            'only_config_changes': ['method.version', 'method.prompts.diagnosis', 'method.prompts.preconditioner',
                                    'module_calls.editor.max_tokens'],
            'contracts_unchanged': new.contracts() == old.contracts(),
            'batch_sizes': list(map(len, revised['batches'])),
            'actor_unchanged': revised['actor'] == previous['actor'],
            'editor_max_tokens': revised['module_calls']['editor']['max_tokens'],
            'other_call_settings_unchanged': normalized['module_calls'] == previous['module_calls'],
            'full_dataset_cli_preflight': 'passed_without_credentials_or_output'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--baseline', required=True, help='Pre-change v29.2 SHA-256 manifest')
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
        for version in ('v29', 'v29_1', 'v29_2', 'v29_3'):
            part = unittest.TestSuite()
            for path in sorted((ROOT / 'tests/skill_evolution' / version).glob('test_*.py')):
                part.addTests(unittest.defaultTestLoader.loadTestsFromName(f'tests.skill_evolution.{version}.{path.stem}'))
            counts[version] = part.countTestCases()
            suite.addTests(part)
        with (output / 'unittest.log').open('w') as log, redirect_stdout(log):
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
            try:
                checks = verify_binding()
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'
    changed = [name for name, expected in baseline.items()
               if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    passed = result.wasSuccessful() and error is None and not blocked and not changed
    report = {'status': 'passed' if passed else 'failed',
              'checked_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
              'tests_run': result.testsRun, 'test_counts': counts,
              'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
              'binding_error': error, 'binding': checks,
              'protected_v29_2_files': len(baseline), 'changed_protected_files': changed,
              'network_or_process_attempts': len(blocked), 'live_model_requests': 0,
              'live_training_started': False, 'live_test_started': False,
              'synthetic_responses_only': True,
              'limitation': 'Offline checks validate prompt routing, contracts and recovery, not model behavior or benchmark improvement.'}
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not passed: raise SystemExit(1)


if __name__ == '__main__':
    main()
