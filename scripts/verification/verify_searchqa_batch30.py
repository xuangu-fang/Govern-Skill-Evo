"""Reproduce batch-30 and legacy regression checks with external I/O blocked."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
MODULES = ['tests.adapters.searchqa.test_batch30', 'tests.adapters.searchqa.test_skilladam'] + [
    'tests.skill_evolution.v28.' + name for name in
    ('test_actor_scoring', 'test_actor_runtime', 'test_archive_gate', 'test_method', 'test_stages', 'test_campaign')]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if Path(sys.prefix).name != 'SearchQA':
        parser.error('Use the SearchQA conda environment')
    out = Path(args.output).resolve()
    if out == ROOT or not out.is_relative_to(ROOT / 'artifacts/verification'):
        parser.error('Use a dedicated artifacts/verification directory')
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'validation.json').exists():
        parser.error('Use a fresh verification directory to preserve prior evidence')
    manifest = ROOT / 'artifacts/verification/searchqa_batch30_20261102/protected_before.json'
    protected = json.loads(manifest.read_text())
    def unchanged():
        return all((ROOT / name).is_file() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
                   for name, sha in protected.items())
    if not unchanged():
        raise RuntimeError('Protected batch-15 experiment/data files changed')
    blocked = []
    def deny(*args, **kwargs):
        blocked.append(True)
        raise AssertionError('Offline validation attempted external I/O')
    with ExitStack() as stack:
        for name in ('socket.socket.connect', 'socket.socket.connect_ex', 'socket.create_connection', 'subprocess.Popen'):
            stack.enter_context(patch(name, side_effect=deny))
        suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
        with (out / 'tests.log').open('w') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    preserved = unchanged()
    summary = {'status': 'passed' if result.wasSuccessful() and not blocked and preserved else 'failed',
               'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'blocked_external_attempts': len(blocked), 'real_model_requests': 0,
               'training_started': False, 'test_started': False,
               'protected_file_count': len(protected), 'protected_files_unchanged': preserved}
    (out / 'validation.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    if summary['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
