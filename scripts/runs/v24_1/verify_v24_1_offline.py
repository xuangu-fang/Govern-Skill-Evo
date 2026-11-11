#!/usr/bin/env python3
"""Verify V24.1 and the unchanged V24 regression suite without network/live execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Verification requires a new output directory')
    output.mkdir(parents=True)
    sys.dont_write_bytecode = True

    def forbidden(*args, **kwargs):
        raise AssertionError('Network/live execution is prohibited by offline verification')

    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    import pytest
    from src.skill_evolution.v24_1 import baseline, evolution
    from src.skill_evolution.v24_1.benchmark import using_benchmark
    from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
    evidence, _ = baseline.audit()
    with using_benchmark(ALFWorldAdapter()):
        frozen = evolution.frozen_contract()
    # All production entry points stay blocked; tests supply fake generators and Actors.
    from importlib import import_module
    for version in ('v24_1', 'v24'):
        prefix = 'src.skill_evolution.' + version
        ev = import_module(prefix + '.evolution')
        adapter = import_module(prefix + '.benchmarks.alfworld.adapter')
        runtime = import_module(prefix + '.benchmarks.alfworld.runtime')
        grouping = import_module(prefix + '.contracts.grouping')
        ev._generator = forbidden
        adapter.ALFWorldAdapter.actor_task = staticmethod(forbidden)
        runtime.actor_task = forbidden
        grouping.live_generator = forbidden
    from src.skill_evolution.v23_5 import evolution as legacy
    legacy._generator = forbidden
    counts = {version: dict(passed=0, failed=0, skipped=0, errors=0) for version in ('v24_1', 'v24')}

    class Results:
        def pytest_runtest_logreport(self, report):
            version = 'v24_1' if '/v24_1/' in report.nodeid else 'v24'
            if report.when == 'call':
                counts[version][report.outcome] += 1
            elif report.failed:
                counts[version]['errors'] += 1
            elif report.skipped:
                counts[version]['skipped'] += 1

    code = pytest.main([str(ROOT/'tests/skill_evolution/v24_1'), str(ROOT/'tests/skill_evolution/v24'),
                       '-q', '-p', 'no:cacheprovider', '--tb=short', f'--junitxml={output / "tests.xml"}'],
                      plugins=[Results()])
    paths = [p for version in counts for p in sorted((ROOT/'tests/skill_evolution'/version).glob('*.py'))]
    report = {
        'created_at': datetime.now(timezone.utc).isoformat(), 'baseline': evidence['baseline'],
        'candidate': 'v24.1', 'approved_prompt_sha256': evidence['approved_prompts'],
        'implementation_sha256': {p: hashlib.sha256(s.encode()).hexdigest() for p, s in frozen.items()},
        'test_sha256': {str(p.relative_to(ROOT)): baseline.digest(p) for p in paths},
        'verification_script_sha256': baseline.digest(__file__),
        'counts': counts, 'pytest_exit_code': int(code),
        'passed': code == 0 and all(c['skipped'] == 0 for c in counts.values()),
        'real_model_requests': 0, 'real_environment_episodes': 0, 'live_performance_verified': False,
        'scope': 'Approved Prompt parity, baseline configuration parity, mock campaign contracts/retries/'
                 'publication/recovery, independent imports, and unchanged V24 regression tests.'}
    (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('passed', 'counts', 'live_performance_verified')}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
