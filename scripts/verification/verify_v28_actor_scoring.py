"""Validate only v28 prompt/scoring components, with networking disabled."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_data_and_messages():
    from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
    from skilladam.benchmarks.searchqa.rollout import build_messages
    from skilladam.types import BenchmarkCase
    base = ROOT / 'data/searchqa'
    plan = json.loads((ROOT / 'docs/methods/v28/experiment_plan.json').read_text())
    lock = json.loads((base / 'v28_dataset.lock.json').read_text())
    view = json.loads((base / 'v28_train600_v1/manifest.json').read_text())
    require(digest(base / 'v28_dataset.lock.json') == plan['dataset']['lock_sha256'] == view['dataset_lock_sha256'], 'Dataset lock drift')
    require(digest(base / 'v28_train600_v1/manifest.json') == plan['dataset']['optimization_view_sha256'], 'Optimization view drift')
    for relative, expected in lock['sha256'].items():
        require(digest(base / relative) == expected, f'Frozen data drift: {relative}')
    counts, ids, seen = {}, {}, set()
    max_context_chars = 0
    skill = '## Synthetic Skill\nLiteral braces: {context} {skill_section}.\nUse the provided context.'
    for split, entry in lock['splits'].items():
        rows = json.loads((base / entry['path']).read_text())
        ids[split] = [row['id'] for row in rows]
        require(len(rows) == entry['count'], 'Wrong split size')
        counts[split] = len(rows)
        for row in rows:
            require(row['id'] not in seen, 'Overlapping task ID')
            seen.add(row['id'])
            # Reference is deliberately a sentinel; the upstream message must
            # depend only on task payload and Skill, never gold answers.
            case = BenchmarkCase(case_id=row['id'], payload={'question': row['question'], 'context': row['context']}, reference=['GOLD_SENTINEL'])
            for current_skill in (None, skill):
                actual = p.messages_for_row(row, current_skill)
                native = build_messages(case, method='skilladam', skill=current_skill)
                require(actual[1] == native[1], 'Raw task text changed')
                require(actual[0]['content'].split('## Answer Format')[0] == native[0]['content'].split('## Answer Format')[0], 'Task/Skill placement changed')
                changed_gold = {**row, 'answers': ['ALTERED_GOLD_SENTINEL'], 'metadata': 'PRIVATE_SENTINEL'}
                require(p.messages_for_row(changed_gold, current_skill) == actual, 'Gold/internal field leaked into messages')
            max_context_chars = max(max_context_chars, len(row['context']))
    optimization_ids = [c['id'] for c in view['optimization_cases']]
    require(optimization_ids == ids['train'] + ids['val'], 'Optimization order drift')
    require(view['test_ids'] == ids['test'], 'Test order drift')
    require([task for batch in view['batches'] for task in batch] == optimization_ids, 'Batch order drift')
    require(len(view['batches']) == 40 and all(len(batch) == 15 for batch in view['batches']), 'Batch size drift')
    require(plan['scoring']['f1_affects_gate'] is False, 'Gate configuration drift')
    require(plan['schedule']['actor_workers'] == plan['schedule']['test_workers'] == 15, 'Concurrency configuration drift')
    from src.skill_evolution.v27.benchmarks.lmb.protocol import ACTOR
    require(plan['actor'] == ACTOR, 'Actor parameters differ from v27')
    return {'locked_files_verified': len(lock['sha256']), 'split_counts': counts,
            'input_rows_verified': len(seen), 'message_variants_verified': 2 * len(seen),
            'optimization_count': len(optimization_ids), 'test_count': len(ids['test']),
            'max_context_chars': max_context_chars, 'actor_parameters_equal_v27': True,
            'provider_token_capacity_verified': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    require(Path(sys.prefix).name == 'SearchQA', 'Use conda environment SearchQA')
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    connections = []

    def blocked(*args, **kwargs):
        connections.append('blocked')
        raise AssertionError('Network/process execution is forbidden in this offline check')

    data_paths = sorted((ROOT / 'data/searchqa').rglob('*.json'))
    before = {str(path.relative_to(ROOT)): digest(path) for path in data_paths}
    manifest = json.loads((ROOT / 'src/skill_evolution/v28/benchmarks/searchqa/source_provenance.json').read_text())
    for relative, expected in manifest['source_sha256'].items():
        require(digest(ROOT / relative) == expected, f'Upstream source drift: {relative}')
    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, 'connect', blocked))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', blocked))
        stack.enter_context(patch('socket.create_connection', blocked))
        stack.enter_context(patch('subprocess.Popen', blocked))
        suite = unittest.defaultTestLoader.loadTestsFromName('tests.skill_evolution.v28.test_actor_scoring')
        with (out / 'unittest.log').open('w') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        data_check = verify_data_and_messages()
    unchanged = before == {str(path.relative_to(ROOT)): digest(path) for path in data_paths}
    source_paths = [p for p in (ROOT / 'src/skill_evolution/v28').rglob('*') if p.suffix in ('.py', '.md', '.json')]
    source_paths += [Path(__file__), ROOT / 'tests/skill_evolution/v28/test_actor_scoring.py']
    report = {
        'status': 'passed' if result.wasSuccessful() and unchanged and not connections else 'failed',
        'checked_at': datetime.now(timezone.utc).isoformat(), 'environment': sys.prefix,
        'scope': 'Offline prompt/scoring/score-comparison components only; no campaign or recovery acceptance.',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'network_or_process_attempts': len(connections), 'model_requests': 0,
        'training_started': False, 'test_evaluation_started': False,
        'dataset_files_unchanged': unchanged, **data_check,
        'source_sha256': {str(path.relative_to(ROOT)): digest(path) for path in sorted(source_paths)},
        'upstream_source_sha256': manifest['source_sha256'],
    }
    (out / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if not k.endswith('sha256')}, ensure_ascii=False, indent=2))
    if report['status'] != 'passed':
        print((out / 'unittest.log').read_text())
        raise SystemExit(1)


if __name__ == '__main__':
    main()
