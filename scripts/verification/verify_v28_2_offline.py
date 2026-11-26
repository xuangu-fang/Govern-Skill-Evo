"""Network-blocked SearchQA v28.2 acceptance; all executions use temporary synthetic fixtures."""
import argparse
from contextlib import ExitStack, redirect_stdout
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
sys.dont_write_bytecode = True


class Results(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.passed = []
    def addSuccess(self, test):
        super().addSuccess(test); self.passed.append(test.id())


def protected_files():
    files = set()
    for version in ('v28', 'v29', 'v29_1', 'v29_2', 'v29_3'):
        files.update(p for p in (ROOT / 'src/skill_evolution' / version).rglob('*')
                     if p.is_file() and p.suffix in ('.py', '.md', '.json'))
    files.update((ROOT / 'docs/methods/v28_2/prompts').glob('*.md'))
    return {p: p.read_bytes() for p in files}


def formal_outputs():
    return {str(p.relative_to(ROOT)) for folder in ('campaigns', 'evaluations')
            for p in (ROOT / 'experiments' / folder).glob('*v28_2*')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/methods/v28_2')
    parser.add_argument('--with-regressions', action='store_true', help='Also run existing SearchQA v28/v28.1 suites')
    parser.add_argument('--docvqa-only', action='store_true', help='Run v29–v29.3 regressions in the DocVQA environment')
    args = parser.parse_args(argv)
    if args.docvqa_only and args.with_regressions:
        parser.error('Choose one benchmark environment per run')
    started = time.monotonic(); stamp = datetime.now(timezone.utc).isoformat()
    old, outputs = protected_files(), formal_outputs()
    attempts, log = [], io.StringIO()
    def blocked(*args, **kwargs):
        attempts.append('network_or_subprocess')
        raise AssertionError('Offline acceptance forbids network and subprocesses')
    versions = (['v29', 'v29_1', 'v29_2', 'v29_3'] if args.docvqa_only else
                ['v28_2'] + (['v28', 'v28_1'] if args.with_regressions else []))
    with ExitStack() as stack, redirect_stdout(log):
        for target in ('socket.socket.connect', 'socket.socket.connect_ex', 'socket.create_connection', 'subprocess.Popen', 'os.system'):
            stack.enter_context(patch(target, side_effect=blocked))
        suite = unittest.TestSuite(unittest.TestLoader().discover(str(ROOT / 'tests/skill_evolution' / v),
                                  top_level_dir=str(ROOT)) for v in versions)
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Results).run(suite)
    changed = [str(p.relative_to(ROOT)) for p, content in old.items() if not p.is_file() or p.read_bytes() != content]
    new_outputs = sorted(formal_outputs() - outputs)
    report = {
        'started_at_utc': stamp, 'elapsed_seconds': round(time.monotonic() - started, 3),
        'status': 'passed' if result.wasSuccessful() and not attempts and not changed and not new_outputs else 'failed',
        'python': sys.executable, 'versions': versions, 'tests_run': result.testsRun, 'passed': len(result.passed),
        'failures': [{'test': str(t), 'detail': detail} for t, detail in result.failures],
        'errors': [{'test': str(t), 'detail': detail} for t, detail in result.errors],
        'skipped': [{'test': str(t), 'reason': reason} for t, reason in result.skipped],
        'passed_tests': result.passed,
        'network_and_subprocesses_blocked': True, 'blocked_attempts': len(attempts), 'live_model_requests': 0,
        'formal_training_started': False, 'formal_test_started': False, 'new_formal_output_paths': new_outputs,
        'protected_file_count': len(old), 'changed_protected_files': changed,
        'v28_2_hash_policy': 'Failing stubs for sha256/digest/file_digest during all integration tests; exact byte comparisons only.',
        'coverage': ['Exact real 600/1400 schedule and design prompts; Editor32768, Diagnosis/Preconditioner65536',
                     'Synthetic 20x30 campaign and separate 1400 final-Skill evaluation with no optimizer in Test',
                     'No Checks, KEEP/full-text REPLACE/WITHDRAW, per-Update patch composition and selected subsets',
                     'Native float EM, F1-only skip, null attribution, net-positive mixed Defer, full-batch evidence verification',
                     'Append-only sequential Memory, immutable source recomputation, atomic HEAD and cursor recovery',
                     'Fifteen campaign interruption boundaries, six-slot Actor/method retry recovery, no semantic resampling',
                     'Cold archive-only audit, frozen prompt/config/input/task identity, legacy versions kept separate'],
        'limitations': ['Synthetic outputs verify wiring and contracts, not model reasoning quality or benchmark improvement.',
                       'Replay attribution is a joint-execution judgment; selected subsets have no measured training score unless text matches an executed Skill.']}
    if args.docvqa_only:
        report['coverage'] = ['Existing DocVQA v29/v29.1/v29.2/v29.3 regression suites in their own environment']
        report.pop('v28_2_hash_policy')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'offline_acceptance.log').write_text(log.getvalue(), encoding='utf-8')
    (args.output / 'offline_acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('status', 'tests_run', 'passed', 'blocked_attempts', 'elapsed_seconds', 'errors', 'failures')}, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
