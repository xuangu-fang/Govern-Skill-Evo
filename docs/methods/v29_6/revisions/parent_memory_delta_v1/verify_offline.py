"""Run existing v29.6 offline tests and verify this prompt-only revision."""
from contextlib import ExitStack, redirect_stdout
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from scripts.verification.verify_v29_6_campaign import verify_config


def main():
    revision = Path(__file__).resolve().parent
    manifest = json.loads((revision / 'manifest.json').read_text())
    output = ROOT / 'artifacts/verification/v29_6_parent_memory_delta_v1'
    output.mkdir(parents=True, exist_ok=True)
    blocked, checks, error = [], {}, None

    def deny(*args, **kwargs):
        blocked.append('network_or_process')
        raise AssertionError('Network/process forbidden in offline acceptance')

    with ExitStack() as stack:
        for target in ('socket.socket.connect', 'socket.socket.connect_ex',
                       'socket.create_connection', 'subprocess.Popen'):
            stack.enter_context(patch(target, deny))
        suite = unittest.defaultTestLoader.discover(
            str(ROOT / 'tests/skill_evolution/v29_6'), top_level_dir=str(ROOT))
        with (output / 'unittest.log').open('w') as log, redirect_stdout(log):
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
            try:
                checks = verify_config()
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    changed = [name for name, expected in manifest['protected_files'].items()
               if not (ROOT / name).is_file() or digest(ROOT / name) != expected]
    passed = result.wasSuccessful() and not result.skipped and not blocked and not changed and error is None
    report = {
        'revision': manifest['id'], 'status': 'passed' if passed else 'failed',
        'tests_run': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'skipped': len(result.skipped),
        'checks': checks, 'check_error': error,
        'protected_files': len(manifest['protected_files']),
        'changed_baseline_files': changed, 'blocked_network_or_process_attempts': blocked,
        'real_training_or_test_started': False,
        'unittest_log_sha256': digest(output / 'unittest.log'),
        'implementation_sha256': {
            str(p.relative_to(ROOT)): digest(p)
            for p in sorted((ROOT / 'src/skill_evolution/v29_6').rglob('*'))
            if p.is_file() and p.suffix in ('.py', '.md')},
    }
    (output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('checks', 'implementation_sha256')}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
