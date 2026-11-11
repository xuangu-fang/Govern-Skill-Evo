"""Run the v24.6 fixtures and optionally check event routing on archived ALFWorld rounds."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.skill_evolution.v24_1.benchmark import using_benchmark
from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
from src.skill_evolution.v24_2.storage import read
from src.skill_evolution.v24_6 import PROMPTS, STAGES, campaign, gate


def archived_pairs(source):
    adapter = ALFWorldAdapter()
    rounds = []
    with using_benchmark(adapter):
        for rd in sorted((source / 'rounds').glob('R*/')):
            if not (rd / 'pair_audit.json').exists():
                continue
            tasks = read(rd / 'round_input.json')['tasks']
            records = {}
            for side in ('parent', 'candidate'):
                batch = []
                for task in tasks:
                    folder = rd / (side + '_runs') / task.replace(':', '_')
                    batch.append(read(folder / read(folder / 'record.json')['trajectory']))
                records[side] = batch
            edits = read(rd / 'editor/result.json')
            payload, audit = gate.replay_input(adapter, tasks, read(rd / 'editor/input.json'),
                                               edits['parsed'], edits['result'], records['parent'], records['candidate'])
            assert audit == read(rd / 'pair_audit.json'), 'Historical audit differs from fresh pair checks'
            rounds.append(dict(round=rd.name, paired_tasks=len(tasks), events=payload['pairs']))
    if not rounds:
        raise ValueError(f'No archived audited rounds in {source}')
    return rounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='read-only prior campaign with paired trajectories')
    parser.add_argument('--report', type=Path, help='write JSON verification result')
    args = parser.parse_args()

    counts = Counter()
    class Results:
        def pytest_runtest_logreport(self, report):
            if report.when == 'call' or report.failed or report.skipped:
                counts[report.outcome] += 1

    def forbidden(*args, **kwargs):
        raise AssertionError('Live execution is disabled during offline verification')

    versions = ('v24_2', 'v24_3', 'v24_4', 'v24_6')
    suites = [str(ROOT / 'tests/skill_evolution' / v) for v in versions]
    with patch.object(socket.socket, 'connect', forbidden), patch.object(socket, 'create_connection', forbidden), \
            patch.object(subprocess, 'Popen', forbidden), patch.object(ALFWorldAdapter, 'actor_task', forbidden), \
            patch.object(campaign, 'HTTPGenerator', forbidden):
        code = pytest.main(['-q', '-p', 'no:cacheprovider', '--tb=short', *suites], plugins=[Results()])
        rounds = archived_pairs(args.archive) if args.archive else []
    result = dict(method=campaign.VERSION, suites=versions, tests=dict(counts), passed=code == 0 and
                  not counts['skipped'], real_model_requests=0, real_environment_episodes=0,
                  prompt_sha256={s: hashlib.sha256((PROMPTS / f'{s}.md').read_bytes()).hexdigest() for s in STAGES},
                  archive=args.archive.name if args.archive else None, archived_routing=rounds)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"Verified {len(rounds)} archived rounds; offline tests: {dict(counts)}")
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
