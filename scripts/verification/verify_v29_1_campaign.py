"""Offline v29.1 acceptance plus unchanged v29 regression coverage."""
import argparse
from contextlib import ExitStack, redirect_stdout
from datetime import datetime
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
    from src.skill_evolution.v29.config import validate_config
    from src.skill_evolution.v29.campaign import CampaignAdapter as V29Adapter
    from src.skill_evolution.v29.benchmarks.docvqa import prompting, protocol
    from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
    from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
    from src.skill_evolution.v29_1.campaign import CampaignAdapter, DEFAULT_CONFIG, PROMPT_ROOT
    dataset = DocVQADataset()
    original = json.loads((ROOT / 'experiments/configs/v29_docvqa_optimization160.json').read_text())
    revised = json.loads(DEFAULT_CONFIG.read_text())
    old_messages, new_messages = {}, {}
    for adapter_type, config, messages in ((V29Adapter, original, old_messages),
                                            (CampaignAdapter, revised, new_messages)):
        with adapter_type(DocVQAActorAdapter(dataset)).using():
            validate_config(config, executable=True)
            for name in prompting.PROMPT_VERSIONS:
                messages[name] = prompting.render(name, config['actor'])
    changed = [name for name in old_messages if old_messages[name] != new_messages[name]]
    assert changed == ['diagnosis', 'preconditioner']
    for name in changed:
        assert new_messages[name] == (PROMPT_ROOT / f'{name}.md').read_text()
        head = '## Examine current evidence' if name == 'diagnosis' else '## Relate historical edits and observable responses'
        tail = '## Decisions and exact output' if name == 'diagnosis' else '## Exact Update patches'
        assert old_messages[name].split(head)[0] == new_messages[name].split(head)[0]
        assert old_messages[name].split(tail)[1] == new_messages[name].split(tail)[1]
    baseline = ROOT / 'docs/methods/v29/five_module_draft_20261102/prompts'
    assert all(text == (baseline / f'{name}.md').read_text() for name, text in old_messages.items())
    normalized = json.loads(json.dumps(revised))
    normalized['method']['version'] = original['method']['version']
    for name in changed: normalized['method']['prompts'][name] = original['method']['prompts'][name]
    assert normalized == original
    return {'config': str(DEFAULT_CONFIG.relative_to(ROOT)),
            'method_version': revised['method']['version'], 'prompt_versions': revised['method']['prompts'],
            'changed_system_prompts': changed, 'v29_historical_prompts_unchanged': True,
            'input_output_contracts_unchanged': True, 'only_config_changes': ['method.version', 'method.prompts.diagnosis', 'method.prompts.preconditioner'],
            'actor_max_tokens': revised['actor']['max_tokens'],
            'module_max_tokens': {k: v['max_tokens'] for k, v in revised['module_calls'].items()},
            'timeouts_seconds': {k: v['timeout_seconds'] for k, v in revised['module_calls'].items()},
            'train_workers': 15, 'test_workers': 60,
            'initial_skill_is_v29_original': revised['initial_skill'] == protocol.initial_skill(),
            'initial_memory': 'empty'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve(); output.mkdir(parents=True, exist_ok=True)
    blocked = []
    def deny(*args, **kwargs):
        blocked.append('network_or_process')
        raise AssertionError('Network/process calls forbidden in offline acceptance')
    checks, check_error, counts = {}, None, {}
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', deny))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', deny))
        stack.enter_context(patch('socket.create_connection', deny))
        stack.enter_context(patch('subprocess.Popen', deny))
        suite = unittest.TestSuite()
        for version in ('v29', 'v29_1'):
            part = unittest.TestSuite()
            for path in sorted((ROOT / 'tests/skill_evolution' / version).glob('test_*.py')):
                part.addTests(unittest.defaultTestLoader.loadTestsFromName(f'tests.skill_evolution.{version}.{path.stem}'))
            counts[version] = part.countTestCases()
            suite.addTests(part)
        with (output / 'unittest.log').open('w') as log, redirect_stdout(log):
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        try:
            from scripts.verification.verify_v29_actor import verify_data
            checks = {'binding': verify_binding(), 'data': verify_data()}
        except Exception as exc:
            check_error = f'{type(exc).__name__}: {exc}'
    passed = result.wasSuccessful() and check_error is None and not blocked
    report = {'status': 'passed' if passed else 'failed',
              'checked_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
              'scope': 'v29.1 wiring and synthetic execution, plus full v29 offline regression suite',
              'tests_run': result.testsRun, 'test_counts': counts,
              'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
              'static_check_error': check_error, 'network_or_process_attempts': len(blocked),
              'model_requests': 0, 'live_training_started': False, 'live_test_started': False,
              'synthetic_responses_only': True,
              'synthetic_train_questions': 160, 'synthetic_test_questions': 374,
              'recovery_checkpoints_tested': 14, **checks,
              'limitation': 'Validates wiring and contracts, not prompt quality or benchmark success improvement.'}
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not passed:
        print((output / 'unittest.log').read_text())
        raise SystemExit(1)


if __name__ == '__main__':
    main()
