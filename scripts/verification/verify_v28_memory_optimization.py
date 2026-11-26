"""Read-only R09 equivalence/profile, with an explicit TEST-ONLY identity bridge.

The optimized implementation must reject old archives natively. For differential
testing only, verify both source trees and allow exactly the reviewed validation
changes before mapping the computed implementation identity to the original one.
No production identity check or archive is rewritten. Network and subprocesses
are blocked; corruption tests write independent copies, never original evidence.
"""
import argparse
import cProfile
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import pstats
import shutil
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
sys.dont_write_bytecode = True
CHANGES = {'src/skill_evolution/v28/' + name for name in (
    'validation.py', 'method.py', 'memory_operation.py', 'evolution.py',
    'benchmarks/searchqa/protocol.py', 'benchmarks/searchqa/adapter.py')}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-root', type=Path, required=True)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--launch-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    original, campaign, out = args.original_root.resolve(), args.campaign.resolve(), args.output.resolve()
    assert original != ROOT and campaign.is_relative_to(original)
    assert not out.is_relative_to(original)
    out.mkdir(parents=True, exist_ok=False)
    phase, opens, denied = 'setup', Counter(), []
    source_fixture = ROOT / 'src/skill_evolution/v28/validation.py'

    def guard(event, values):
        if event == 'open':
            name, mode, flags = values
            if isinstance(name, (str, bytes)):
                path = Path(os.fsdecode(name)).absolute()
                writing = (flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                if writing and not (path.is_relative_to(out) or (phase == 'faults' and path == source_fixture)):
                    raise RuntimeError(f'Write outside acceptance fixtures: {path}')
                if not writing and phase == 'profile': opens[str(path)] += 1
        if event.startswith('socket.') and event != 'socket.__new__':
            denied.append(event)
            raise RuntimeError('Network disabled')
        if event in ('subprocess.Popen', 'os.system', 'os.kill', 'os.killpg'):
            raise RuntimeError('External execution/signals disabled')
        if event in ('os.remove', 'os.rename', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink', 'os.chmod', 'os.truncate', 'os.utime'):
            paths = values[:2] if event in ('os.rename', 'os.link', 'os.symlink') else values[:1]
            if any(not Path(os.fsdecode(name)).absolute().is_relative_to(out) for name in paths):
                raise RuntimeError(f'Mutation outside acceptance fixtures: {event}')

    sys.addaudithook(guard)
    protected = list((original / 'src').rglob('*.py')) + list((original / 'src').rglob('*.md'))
    protected += list((original / 'data/searchqa').rglob('*'))
    protected += [path for n in range(1, 10) for path in (campaign / f'rounds/R{n:02}').rglob('*')]
    before = {str(path): digest(path) for path in protected if path.is_file()}
    frozen = json.loads((campaign / 'contract.json').read_text())
    assert all((original / name).read_text() == value for name, value in frozen.items()), 'Original frozen source changed'
    launch = json.loads(args.launch_manifest.read_text())['sha256']
    assert all(digest(Path(name)) == value for name, value in launch.items()), 'Launch manifest changed'
    print(f'Protected {len(before)} files, {len(frozen)} campaign sources and {len(launch)} launch hashes', flush=True)

    from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
    from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
    from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
    from src.skill_evolution.v28.method import SearchQAMethod
    from src.skill_evolution.v28 import validation
    from src.skill_evolution.v28.storage import read, save

    old = read(campaign / 'rounds/R09/parent_runs/batch.json')['signature']['protocol']
    factory = p._implementation_identity
    optimized = factory()
    assert {k: v for k, v in old.items() if k != 'implementation_sha256'} == {
        k: v for k, v in optimized.items() if k != 'implementation_sha256'}
    old_files, new_files = old['implementation_sha256'], optimized['implementation_sha256']
    changed = {name for name in old_files.keys() | new_files.keys() if old_files.get(name) != new_files.get(name)}
    assert changed == CHANGES, ('Unexpected source changes', changed)
    assert all(digest(original / name) == value for name, value in old_files.items())

    # A normal adapter must still reject the old source identity.
    dataset = SearchQADataset(batch_size=30)
    native = SearchQAMethod(SearchQAActorAdapter(dataset), archives=[])
    try:
        native.register_archive(campaign / 'rounds/R01/parent_runs')
    except ValueError:
        native_rejected = True
    else:
        raise AssertionError('Native source identity rejection was weakened')

    def test_only_identity():
        value = factory()
        if value != optimized:
            raise ValueError('Optimized source identity changed during acceptance')
        return deepcopy(old)

    started = time.perf_counter()
    faults = []
    with patch.object(p, '_implementation_identity', test_only_identity):
        adapter = SearchQAActorAdapter(dataset)
        method = SearchQAMethod(adapter, archives=[])
        for n in range(1, 10):
            for side in ('parent_runs', 'candidate_runs'):
                method.register_archive(campaign / f'rounds/R{n:02}' / side)
        setup_seconds = time.perf_counter() - started
        print(f'Registered 540 records in {setup_seconds:.2f}s; starting profile', flush=True)
        with method.using():
            phase = 'profile'
            prof = cProfile.Profile(); started = time.perf_counter(); cpu = time.process_time()
            prof.enable()
            try:
                view = method.load_memory(campaign / 'rounds/R09/memory')
            finally:
                prof.disable()
                elapsed, cpu_elapsed = time.perf_counter() - started, time.process_time() - cpu
                phase = 'done'
        expected = read(campaign / 'rounds/R09/memory/view.json')
        assert p.exact(view) == p.exact(expected), 'Memory values, references or order changed'
        prof.dump_stats(str(out / 'r09_load_memory.prof'))
        stats = pstats.Stats(prof)
        rows = [{'file': k[0], 'line': k[1], 'function': k[2], 'calls': v[1],
                 'self_seconds': v[2], 'cumulative_seconds': v[3]} for k, v in stats.stats.items()]
        with (out / 'stats.txt').open('w') as handle:
            pstats.Stats(prof, stream=handle).sort_stats('cumulative').print_stats(60)
        print(f'Profile complete: {elapsed:.2f}s, {sum(opens.values())} file opens', flush=True)

        phase = 'faults'
        fixture = out / 'corruptible_batch'
        shutil.copytree(campaign / 'rounds/R09/parent_runs', fixture)
        isolated = SearchQAMethod(adapter, archives=[fixture])
        records = read(fixture / 'records.json'); record = records[0]
        folder = fixture / 'actor' / p.digest(record['task_id'])

        def response_change():
            path = folder / 'attempts/001/response.json'
            value = read(path); value['choices'][0]['message']['content'] = '<answer>tampered</answer>'
            save(path, value)

        def order_change():
            path = fixture / 'records.json'; value = read(path); value.reverse(); save(path, value)

        def skill_change():
            path = fixture / 'batch.json'; value = read(path); value['signature']['skill'] += ' altered'; save(path, value)

        mutations = [
            ('raw_response', folder / 'attempts/001/response.json', response_change),
            ('batch_order', fixture / 'records.json', order_change),
            ('skill', fixture / 'batch.json', skill_change),
            ('source_identity', source_fixture, lambda: source_fixture.write_bytes(source_fixture.read_bytes() + b'\n# fault\n')),
        ]
        for name, path, mutate in mutations:
            for timing in ('before_operation', 'after_cache_hit'):
                original_bytes = path.read_bytes()
                try:
                    if timing == 'before_operation': mutate()
                    try:
                        with validation.operation(adapter):
                            isolated.validate_record(record)
                            if timing == 'after_cache_hit':
                                mutate()
                                isolated.validate_record(record)
                    except (ValueError, FileNotFoundError) as exc:
                        faults.append({'mutation': name, 'timing': timing, 'rejected': True, 'reason': str(exc)})
                    else:
                        raise AssertionError(f'Tampering accepted: {name}, {timing}')
                finally:
                    path.write_bytes(original_bytes)
        phase = 'done'
    assert factory() == optimized, 'Optimized source was not restored'
    changed_protected = [name for name, checksum in before.items() if digest(Path(name)) != checksum]
    assert not changed_protected, changed_protected
    assert all((original / name).read_text() == value for name, value in frozen.items())
    assert all(digest(Path(name)) == value for name, value in launch.items())
    baseline = read(args.baseline)
    def calls(name): return sum(row['calls'] for row in rows if row['function'] == name)
    assert calls('_validate_record_archive') == 540
    assert calls('_signature') == 18
    assert calls('_implementation_identity') == 1
    report = {
        'status': 'passed', 'wall_seconds': elapsed, 'cpu_seconds': cpu_elapsed,
        'setup_registration_seconds': setup_seconds, 'file_opens': sum(opens.values()),
        'unique_paths_opened': len(opens), 'top_opened_paths': opens.most_common(30),
        'complete_record_validations': calls('_validate_record_archive'), 'batch_signatures': calls('_signature'),
        'implementation_identity_computations': calls('_implementation_identity'),
        'validation_entry_calls': calls('validate_record'), 'view_matches_archive': True,
        'canonical_view_sha256': p.digest(view), 'entries': len(view['entries']), 'sources': len(view['sources']),
        'protected_files': len(before), 'changed_files': changed_protected,
        'campaign_contract_files': len(frozen), 'frozen_manifest_files': len(launch),
        'native_old_archive_rejected': native_rejected, 'test_only_identity_bridge': sorted(changed),
        'optimized_implementation_sha256': new_files, 'fault_tests': faults, 'denied_network_operations': denied,
        'baseline_wall_seconds': baseline['wall_seconds'], 'baseline_file_opens': baseline['file_opens'],
        'profiled_speedup': baseline['wall_seconds'] / elapsed,
        'measurement_scope': 'One load_memory after registration; cProfile and open audit, including dependency snapshots and end checks. No commit/publish or model requests.',
        'functions': rows,
    }
    (out / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in (
        'functions', 'top_opened_paths', 'optimized_implementation_sha256', 'fault_tests')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
