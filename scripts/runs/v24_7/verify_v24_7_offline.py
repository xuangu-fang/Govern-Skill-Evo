"""Exercise v24.7 without live calls; optionally reproduce v24.6's recorded Gate decisions."""
import argparse
from collections import Counter
from contextlib import ExitStack
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

from scripts.runs.v24_6.verify_v24_6_offline import archived_pairs
from src.skill_evolution.v24_1.benchmarks.alfworld.adapter import ALFWorldAdapter
from src.skill_evolution.v24_2.storage import read
from src.skill_evolution.v24_6 import campaign as previous
from src.skill_evolution.v24_7 import PROMPTS, STAGES, campaign


def verify_archive(source):
    config = read(source / 'config.json')
    if config['method'] != previous.VERSION:
        raise ValueError('Expected a v24.6 comparison campaign')
    # Rebuild pairs from episode receipts before applying the saved attribution.
    routing = {r['round']: r for r in archived_pairs(source)}
    rounds = []
    selected = config['initial_skill']['text']
    for number, tasks in enumerate(config['batches'], 1):
        rd = source / 'rounds' / f'R{number:02}'
        assert read(rd / 'round_input.json')['tasks'] == tasks
        publication = read(rd / 'publication.json')
        decisions = []
        events = []
        if rd.name in routing:
            routed = routing[rd.name]
            assert routed['paired_tasks'] == len(tasks)
            events = routed['events']
            replay = []
            if events:
                payload = read(rd / 'replay/input.json')
                assert payload['pairs'] == events
                replay = campaign.gate.knowledge(read(rd / 'replay/result.json')['parsed'], payload)
            else:
                assert not (rd / 'replay/result.json').exists()
            view = read(rd / 'editor/input.json')
            assert view['parent'] == selected
            decisions, selection = campaign.gate.select(view, read(rd / 'editor/result.json')['parsed'], events, replay)
            saved = read(rd / 'gate.json')
            assert decisions == saved['decisions'] and selection == saved['selection']
            selected = selection['selected_text']
        else:
            # A candidate outcome must have a verified pair audit, even with zero events.
            assert publication['outcome'] != 'candidate'
            assert not (rd / 'candidate_runs').exists()
        assert publication['selected'] == selected == (rd / 'selected.md').read_text()
        rounds.append(dict(round=rd.name, outcome=publication['outcome'],
                           paired_tasks=len(tasks) if rd.name in routing else 0,
                           events=len(events), decisions=decisions))
    assert selected == (source / 'final_skill.md').read_text()
    return rounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='completed v24.6 campaign to check read-only')
    parser.add_argument('--report', type=Path, help='JSON output path')
    args = parser.parse_args()
    suites = ['v24_2', 'v24_3', 'v24_4', 'v24_6', 'v24_7']
    counts = Counter()

    class Results:
        def pytest_runtest_logreport(self, report):
            if report.when == 'call' or report.failed or report.skipped:
                counts[report.outcome] += 1

    def forbidden(*args, **kwargs):
        raise AssertionError('Live execution disabled during offline verification')

    with ExitStack() as stack:
        for obj, attr in [(socket.socket, 'connect'), (socket, 'create_connection'), (subprocess, 'Popen'),
                          (ALFWorldAdapter, 'actor_task'), (campaign, 'HTTPGenerator'), (previous, 'HTTPGenerator')]:
            stack.enter_context(patch.object(obj, attr, forbidden))
        targets = [str(ROOT / 'tests/skill_evolution' / suite) for suite in suites]
        code = pytest.main(['-q', '-p', 'no:cacheprovider', '--tb=short', *targets], plugins=[Results()])
        rounds = verify_archive(args.archive) if args.archive else []

    config = campaign.configuration()
    contract = campaign.contract(config)
    gate_path = Path(campaign.gate.__file__).relative_to(ROOT)
    report = dict(method=campaign.VERSION, passed=code == 0 and not counts['skipped'],
                  suites=suites, tests=dict(counts), real_model_requests=0, real_environment_episodes=0,
                  config_sha256=contract['config_sha256'], batch_sizes=[len(b) for b in config['batches']],
                  prompt_sha256={s: hashlib.sha256((PROMPTS / f'{s}.md').read_bytes()).hexdigest() for s in STAGES},
                  gate=dict(path=str(gate_path), sha256=contract['files'][str(gate_path)]),
                  archive=args.archive.name if args.archive else None, archive_rounds=rounds)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(f"{dict(counts)}, {len(rounds)} archived rounds checked.")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
