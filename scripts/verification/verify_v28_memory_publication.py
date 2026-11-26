"""R09 post-Replay publication in disposable campaigns; no Actor/model/Gate run.

Only the test harness bridges the explicitly checked implementation identity and
campaign source text. Production still rejects old frozen-source campaigns.
"""
import argparse
from collections import Counter
from copy import deepcopy
import cProfile
from datetime import datetime
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
from scripts.verification.verify_v28_memory_optimization import CHANGES, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-root', type=Path, required=True)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--launch-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    original, campaign, out = args.original_root.resolve(), args.campaign.resolve(), args.output.resolve()
    assert original != ROOT and campaign.is_relative_to(original) and not out.is_relative_to(original)
    out.mkdir(parents=True, exist_ok=False)
    phase, opens, denied = 'setup', Counter(), []

    def guard(event, values):
        if event == 'open':
            name, mode, flags = values
            if isinstance(name, (str, bytes)):
                path = Path(os.fsdecode(name)).absolute()
                writing = (flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                if writing and not path.is_relative_to(out): raise RuntimeError(f'Write outside fixtures: {path}')
                if not writing and phase == 'profile': opens[str(path)] += 1
        if event.startswith('socket.') and event != 'socket.__new__':
            denied.append(event); raise RuntimeError('Network disabled')
        if event in ('subprocess.Popen', 'os.system', 'os.kill', 'os.killpg'):
            raise RuntimeError('External execution/signals disabled')
        if event in ('os.remove', 'os.rename', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink', 'os.chmod', 'os.truncate', 'os.utime'):
            paths = values[:2] if event in ('os.rename', 'os.link', 'os.symlink') else values[:1]
            if any(not Path(os.fsdecode(name)).absolute().is_relative_to(out) for name in paths):
                raise RuntimeError(f'Mutation outside fixtures: {event}')

    sys.addaudithook(guard)
    protected = list((original / 'src').rglob('*.py')) + list((original / 'src').rglob('*.md'))
    protected += list((original / 'data/searchqa').rglob('*'))
    protected += [path for n in range(1, 10) for path in (campaign / f'rounds/R{n:02}').rglob('*')]
    before_hashes = {str(path): digest(path) for path in protected if path.is_file()}
    frozen = json.loads((campaign / 'contract.json').read_text())
    launch = json.loads(args.launch_manifest.read_text())['sha256']
    assert all((original / name).read_text() == value for name, value in frozen.items())
    assert all(digest(Path(name)) == value for name, value in launch.items())

    from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
    from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
    from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
    from src.skill_evolution.v28.campaign import CampaignAdapter
    from src.skill_evolution.v28 import evolution, stages

    rd = campaign / 'rounds/R09'
    bundle = stages.read(rd / 'replay/input.json')
    selected = stages.read(rd / 'replay/result.json')['path']
    replayed = stages.read(rd / 'replay' / selected / 'result.json')['replay']
    # Bind the saved response to the parsed proposal, without a model request.
    response = stages.read(rd / 'replay' / selected / 'response.json')
    assert response['finish_reason'] == 'stop' and json.loads(response['content']) == replayed
    gate, expected_result = stages.read(rd / 'gate/result.json'), stages.read(rd / 'result.json')
    before_state, after_state = expected_result['before'], expected_result['after']
    config = stages.read(campaign / 'config.json')
    candidate_path = after_state['parent']
    assert gate['result']['decision'] == 'ACCEPT' and before_state['next_round'] == 9
    cid = campaign.name + '_R09'
    expected_commit = stages.read(rd / f'memory/archive/{cid}.json')
    assert expected_commit['context'] == bundle and expected_commit['result'] == replayed
    inputs_digest = p.digest([bundle, replayed, gate])

    old = stages.read(rd / 'parent_runs/batch.json')['signature']['protocol']
    factory, optimized = p._implementation_identity, p._implementation_identity()
    assert {k: v for k, v in old.items() if k != 'implementation_sha256'} == {
        k: v for k, v in optimized.items() if k != 'implementation_sha256'}
    a, b = old['implementation_sha256'], optimized['implementation_sha256']
    changed = {name for name in a.keys() | b.keys() if a.get(name) != b.get(name)}
    assert changed == CHANGES
    assert all(digest(original / name) == value for name, value in a.items())
    dataset = SearchQADataset(batch_size=30)
    native = CampaignAdapter(SearchQAActorAdapter(dataset))
    try: native.register_archive(rd / 'parent_runs')
    except ValueError: pass
    else: raise AssertionError('Native source identity rejection was weakened')

    def bridge():
        if factory() != optimized: raise ValueError('Optimized source identity changed')
        return deepcopy(old)

    # One independent Actor batch supports response fault injection; others stay read-only.
    actor_fixture = out / 'actor_fixture'
    shutil.copytree(rd / 'parent_runs', actor_fixture)
    archives = [actor_fixture if n == 9 and side == 'parent_runs' else campaign / f'rounds/R{n:02}' / side
                for n in range(1, 10) for side in ('parent_runs', 'candidate_runs')]

    def method():
        bound = CampaignAdapter(SearchQAActorAdapter(dataset))
        for path in archives: bound.register_archive(path)
        # Explicit TEST-ONLY source text mapping; dependency checks remain active.
        bound.frozen_files = lambda: deepcopy(frozen)
        return bound

    def prepare(label):
        root = out / label / campaign.name
        root.mkdir(parents=True)
        for name in ('config.json', 'initial_config.json', 'contract.json', 'runtime.json'):
            shutil.copy2(campaign / name, root / name)
        shutil.copytree(campaign / before_state['active_memory'], root / before_state['active_memory'])
        target = root / candidate_path; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(campaign / candidate_path, target)
        stages.save(root / 'state.json', before_state)
        return root

    def invoke(bound, root, *, hook=None, read_only=False):
        target = root / 'rounds/R09'
        def checkpoint(name):
            if not read_only: stages.save(target / 'progress.json', {'stage': name, 'at': stages.now()})
            if hook: hook(name)
        return evolution._finish_replay(root, target, config, before_state, bundle, replayed, gate, candidate_path,
                                        checkpoint=checkpoint, hook=hook, read_only=read_only)

    def assert_outputs(root):
        target = root / 'rounds/R09'
        assert stages.read(root / 'state.json') == after_state
        assert stages.read(target / 'result.json') == expected_result
        names = ('memory/active.json', 'memory/view.json', f'memory/archive/{cid}.json',
                 'knowledge_review/candidate.json', 'knowledge_review/result.json')
        for name in names: assert (target / name).read_bytes() == (rd / name).read_bytes(), name
        for path in (rd / 'memory/archive').glob('*.json'):
            assert (target / 'memory/archive' / path.name).read_bytes() == path.read_bytes()
        base = stages.read(target / 'memory/base.json')
        assert base['source'] == str(root / before_state['active_memory'])
        assert base['state'] == stages.read(rd / 'memory/base.json')['state']
        assert (root / candidate_path).read_bytes() == (campaign / candidate_path).read_bytes()

    faults, recovery = [], {}
    with patch.object(p, '_implementation_identity', bridge):
        bound, target = method(), prepare('profile')
        with bound.using(), evolution._lock(target):
            phase = 'profile'; prof = cProfile.Profile(); start = time.perf_counter(); cpu = time.process_time()
            prof.enable()
            try: result = invoke(bound, target)
            finally:
                prof.disable(); elapsed, cpu_elapsed = time.perf_counter() - start, time.process_time() - cpu
                phase = 'verify'
        assert result == expected_result
        assert_outputs(target)
        prof.dump_stats(str(out / 'publication.prof'))
        statistics = pstats.Stats(prof)
        rows = [{'file': k[0], 'line': k[1], 'function': k[2], 'calls': v[1],
                 'self_seconds': v[2], 'cumulative_seconds': v[3]} for k, v in statistics.stats.items()]
        with (out / 'stats.txt').open('w') as handle:
            pstats.Stats(prof, stream=handle).sort_stats('cumulative').print_stats(65)
        print(f'R09 complete publication: {elapsed:.3f}s; {sum(opens.values())} file opens', flush=True)

        # Fresh adapter, empty caches, audit the entire published Memory without writes.
        audit_before = {str(q): digest(q) for q in target.rglob('*') if q.is_file()}
        fresh = method(); start = time.perf_counter()
        with fresh.using(): assert invoke(fresh, target, read_only=True) == expected_result
        recovery['fresh_readonly_seconds'] = time.perf_counter() - start
        assert all(digest(Path(q)) == h for q, h in audit_before.items())
        recovery['fresh_readonly_unchanged'] = True

        interrupted = prepare('interrupted')
        def interrupt(stage):
            if stage == 'memory_prepared': raise KeyboardInterrupt()
        with bound.using(), evolution._lock(interrupted):
            try: invoke(bound, interrupted, hook=interrupt)
            except KeyboardInterrupt: pass
            else: raise AssertionError('Missing interruption')
        assert stages.read(interrupted / 'state.json') == before_state
        fresh = method()
        with fresh.using(), evolution._lock(interrupted): assert invoke(fresh, interrupted) == expected_result
        assert_outputs(interrupted)
        recovery['interrupted_after_memory_prepared_resumed'] = True

        fault_root = out / 'faults' / campaign.name
        shutil.copytree(target, fault_root)
        record = stages.read(actor_fixture / 'records.json')[0]
        response_path = actor_fixture / 'actor' / p.digest(record['task_id']) / 'attempts/001/response.json'
        paths = {
            'active': fault_root / 'rounds/R09/memory/active.json',
            'view': fault_root / 'rounds/R09/memory/view.json',
            'history_commit': next((fault_root / 'rounds/R09/memory/archive').glob('*_R01.json')),
            'skill': fault_root / candidate_path, 'actor_response': response_path,
            'frozen_contract': fault_root / 'contract.json',
        }
        # A recovery copy's base receipt legitimately names its own source directory.
        stages.save(fault_root / 'rounds/R09/memory/base.json', {
            'source': str(fault_root / before_state['active_memory']),
            'state': stages.read(fault_root / before_state['active_memory'] / 'active.json')})
        for name, path in paths.items():
            content = path.read_bytes()
            stages.save(fault_root / 'state.json', before_state)
            def corrupt(stage):
                if stage == 'before_publish':
                    if name == 'frozen_contract':
                        value = stages.read(path); value['injected'] = 'changed'; stages.save(path, value)
                    elif name == 'active':
                        value = stages.read(path); value['active_ids'].append('M999'); stages.save(path, value)
                    elif name == 'view':
                        value = stages.read(path); value['entries'] = []; stages.save(path, value)
                    elif name == 'history_commit':
                        value = stages.read(path); value['result']['entries'][0]['knowledge'][0]['text'] += ' altered'
                        stages.save(path, value)
                    elif name == 'actor_response':
                        value = stages.read(path); value['choices'][0]['message']['content'] = '<answer>altered</answer>'
                        stages.save(path, value)
                    else: path.write_bytes(content + b' altered')
            try:
                with bound.using(), evolution._lock(fault_root):
                    try: invoke(bound, fault_root, hook=corrupt)
                    except ValueError as exc: faults.append({'target': name, 'rejected': True, 'reason': str(exc)})
                    else: raise AssertionError(f'Publication accepted tampering: {name}')
                assert stages.read(fault_root / 'state.json') == before_state
            finally:
                path.write_bytes(content)

    assert factory() == optimized and p.digest([bundle, replayed, gate]) == inputs_digest
    assert all(digest(Path(name)) == value for name, value in before_hashes.items())
    assert all(digest(Path(name)) == value for name, value in launch.items())
    assert all((original / name).read_text() == value for name, value in frozen.items())
    def calls(name): return sum(row['calls'] for row in rows if row['function'] == name)
    assert calls('_load_memory') == 1 and calls('_archive') == 1
    assert calls('_validate_record_archive') == 540 and calls('_signature') == 18
    archived_gap = datetime.fromisoformat(stages.read(rd / 'progress.json')['at']).timestamp() - (rd / 'knowledge_review/candidate.json').stat().st_mtime
    report = {
        'status': 'passed', 'wall_seconds': elapsed, 'cpu_seconds': cpu_elapsed,
        'measurement_scope': 'Complete post-Replay production helper: knowledge_review, prepare, commit, view, result receipt, official state publication and final dependency checks. No Actor, Gate or model execution.',
        'file_opens': sum(opens.values()), 'unique_paths_opened': len(opens),
        'cold_memory_loads': calls('_load_memory'), 'history_archive_scans': calls('_archive'),
        'complete_record_validations': calls('_validate_record_archive'), 'batch_signatures': calls('_signature'),
        'implementation_identity_computations': calls('_implementation_identity'),
        'published_state_matches': True, 'commit_view_and_review_bytes_match': True,
        'all_history_commits_match': True, 'candidate_skill_matches': True,
        'relocated_base_source_only': True, 'inputs_unchanged': True,
        'archived_post_replay_gap_seconds': archived_gap,
        'baseline_note': 'Archived marker interval, not a newly profiled baseline. Do not compare the prior single-load benchmark as if it were full publication.',
        'recovery': recovery, 'fault_tests': faults, 'native_old_identity_rejected': True,
        'test_only_identity_and_source_text_bridge': sorted(changed),
        'protected_files': len(before_hashes), 'changed_files': [], 'frozen_manifest_files': len(launch),
        'campaign_contract_files': len(frozen), 'denied_network_operations': denied,
        'optimized_implementation_sha256': b, 'functions': rows,
    }
    (out / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('functions', 'optimized_implementation_sha256')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
