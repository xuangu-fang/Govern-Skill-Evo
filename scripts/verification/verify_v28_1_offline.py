"""Offline v28.1 acceptance and v28 regression, without hash manifests or providers.

Run with the SearchQA Python environment. All generated campaign/Test archives
belong to unittest temporary directories and are removed at the end.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]


class Results(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.append(test.id())


def main():
    if Path(sys.prefix).name != 'SearchQA':
        raise SystemExit('Use the SearchQA Python environment')
    output = ROOT / 'docs/methods/v28_1'
    started = time.monotonic()
    stamp = datetime.now(timezone.utc).isoformat()
    log = io.StringIO()
    attempts = []

    def blocked(*args, **kwargs):
        attempts.append('network_or_subprocess')
        raise AssertionError('Offline acceptance cannot use network or subprocesses')

    with ExitStack() as stack:
        for target in ('socket.socket.connect', 'socket.socket.connect_ex', 'socket.create_connection',
                       'subprocess.Popen', 'os.system'):
            stack.enter_context(patch(target, side_effect=blocked))
        loader = unittest.TestLoader()
        suite = unittest.TestSuite(loader.discover(str(ROOT / folder), top_level_dir=str(ROOT)) for folder in (
            'tests/skill_evolution/v28', 'tests/skill_evolution/v28_1'))
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Results).run(suite)

    report = {
        'started_at_utc': stamp, 'elapsed_seconds': round(time.monotonic() - started, 3),
        'status': 'passed' if result.wasSuccessful() and not attempts else 'failed',
        'python': sys.executable, 'command': 'python -B scripts/verification/verify_v28_1_offline.py',
        'config': 'experiments/configs/v28_1_searchqa_train600_batch30_20261103.json',
        'tests_run': result.testsRun, 'passed': len(result.passed),
        'failures': [{'test': str(test), 'detail': detail} for test, detail in result.failures],
        'errors': [{'test': str(test), 'detail': detail} for test, detail in result.errors],
        'skipped': [{'test': str(test), 'reason': reason} for test, reason in result.skipped],
        'passed_tests': result.passed,
        'network_and_subprocesses_blocked': True, 'blocked_attempts': len(attempts),
        'live_model_requests': 0, 'formal_training_started': False, 'formal_test_started': False,
        'v28_1_digest_calls': 'Failing stubs installed throughout all v28.1 tests; original v28 regression retains its legacy checks.',
        'coverage': [
            'Exact baseline config comparison except method version and two prompt IDs',
            'Real 600/1400 IDs and order; all 2000 Actor messages match archived templates',
            'Five rendered prompts dispatch to reviewed text; only Diagnosis/Preconditioner differ',
            'Four Updates accepted; KEEP, real patch, withdrawal, and conditional preference reach Editor',
            'Long synthetic Skill accepted without added length limit',
            'Five-module execution, ACCEPT/RETAIN and Memory on both outcomes',
            'Synthetic 20x30 training and separate 1400 fixed Skill Test including resume',
            '13 stage/publication interruption boundaries; archive-only recovery',
            'Six Actor and method attempts persist on resume; semantic stop does not resample',
            'Strict EM gate with F1 observational only and complete-pair requirement',
            'Default v28 regressions, including SearchQA Actor, scoring, archives and recovery',
        ],
        'limitations': [
            'Synthetic responses test wiring and contracts, not real model rule quality or Test improvement.',
            'Package-level Gate can still retain Updates without independently demonstrated gains.',
        ],
    }
    (output / 'offline_acceptance.log').write_text(log.getvalue())
    (output / 'offline_acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(log.getvalue())
    print(json.dumps({key: report[key] for key in ('status', 'tests_run', 'passed', 'blocked_attempts', 'elapsed_seconds')}, indent=2))
    raise SystemExit(0 if report['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
