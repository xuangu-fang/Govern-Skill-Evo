#!/usr/bin/env python3
"""Run V24 offline acceptance with network and live Actor/model calls prohibited."""
import argparse
import json
from pathlib import Path
import socket
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Verification requires a new output directory')
    output.mkdir(parents=True)

    def forbidden(*args, **kwargs):
        raise AssertionError('Network/live execution is prohibited by offline acceptance')

    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    import pytest
    from src.skill_evolution.v24 import baseline
    from src.skill_evolution.v24.benchmark import using_benchmark
    from src.skill_evolution.v24.benchmarks.alfworld.adapter import ALFWorldAdapter
    from src.skill_evolution.v24 import evolution
    evidence, _ = baseline.audit()
    with using_benchmark(ALFWorldAdapter()):
        frozen = evolution.frozen_contract()
    # The tests use fake Actor runners and generators. Guard the real paths too.
    from src.skill_evolution.v24.benchmarks.alfworld import runtime
    from src.skill_evolution.v23_5 import evolution as legacy
    from src.skill_evolution.v24.contracts import grouping
    runtime.actor_task = forbidden
    ALFWorldAdapter.actor_task = staticmethod(forbidden)
    grouping.live_generator = forbidden
    evolution._generator = forbidden
    legacy._generator = forbidden
    counts = {'passed': 0, 'failed': 0, 'skipped': 0, 'errors': 0}

    class Results:
        def pytest_runtest_logreport(self, report):
            if report.when == 'call':
                counts[report.outcome] += 1
            elif report.failed:
                counts['errors'] += 1
            elif report.skipped:
                counts['skipped'] += 1

    code = pytest.main([str(ROOT/'tests/skill_evolution/v24'), '-q', '--tb=short',
                        f'--junitxml={output / "tests.xml"}'], plugins=[Results()])
    paths = sorted((ROOT/'tests/skill_evolution/v24').glob('*.py'))
    report = {'baseline': evidence['baseline'], 'candidate': evidence['version'],
              'baseline_source_files': evidence['source_files'],
              'implementation_files': list(frozen),
              'test_files': [str(p.relative_to(ROOT)) for p in paths],
              'verification_script': str(Path(__file__).relative_to(ROOT)),
              'counts': counts, 'pytest_exit_code': int(code),
              'passed': code == 0 and counts['skipped'] == 0,
              'real_model_requests': 0, 'real_environment_episodes': 0,
              'raw_rounds_checked': ['R01', 'R02', 'R03'],
              'scope': 'Offline regression with preset responses; runtime bookkeeping simplified; '
                       'Preconditioner history-primary Prompt and Grouping input removal are intentional differences',
              'live_performance_verified': False,
              'created_at': datetime.now(timezone.utc).isoformat()}
    (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('passed', 'counts', 'live_performance_verified')}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
