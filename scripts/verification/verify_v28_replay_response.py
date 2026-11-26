"""Offline acceptance of response projection and Replay-local validation scopes.

The archived six-round experiment is read-only. Its source identity is bridged
only inside this verification process after checking the archived frozen inputs.
Normal production loading must reject it. No provider requests are permitted.
"""
import argparse
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
sys.dont_write_bytecode = True
CHANGES = {'src/skill_evolution/v28/' + name for name in (
    'modules.py', 'benchmarks/searchqa/replay_input_view.py',
    'benchmarks/searchqa/prompting.py', 'benchmarks/searchqa/prompts/replay.md')}


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def archives(receipt, out):
    from src.skill_evolution.v28 import modules, replay, validation
    from src.skill_evolution.v28.method import SearchQAMethod
    from src.skill_evolution.v28.benchmarks.searchqa import actor, prompting, protocol as p, replay_input_view
    from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
    from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter

    saved = read(receipt / 'archive.json')
    campaign = Path(saved['train'])
    protected = read(receipt / 'campaign_content_sha256.json')
    frozen = read(receipt / 'launch_manifest_original.json')['sha256']
    assert all(digest(Path(name)) == value for name, value in protected.items())
    for name, value in frozen.items():
        assert digest(receipt / 'frozen_inputs' / Path(name).relative_to(ROOT)) == value
    old = read(campaign / 'rounds/R01/parent_runs/batch.json')['signature']['protocol']
    factory, actual = p._implementation_identity, p._implementation_identity()
    a, b = old['implementation_sha256'], actual['implementation_sha256']
    changed = {name for name in a.keys() | b.keys() if a.get(name) != b.get(name)}
    assert changed == CHANGES, changed
    assert {k: v for k, v in old.items() if k != 'implementation_sha256'} == {
        k: v for k, v in actual.items() if k != 'implementation_sha256'}
    assert all(digest(ROOT / name) == value for name, value in a.items() if name not in CHANGES)
    dataset = SearchQADataset(batch_size=30)
    native = SearchQAMethod(SearchQAActorAdapter(dataset), archives=[])
    try:
        native.register_archive(campaign / 'rounds/R01/parent_runs')
    except ValueError:
        pass
    else:
        raise AssertionError('Production unexpectedly accepted old source identity')

    def bridge():
        assert factory() == actual, 'Source changed during offline acceptance'
        return deepcopy(old)

    def size(messages):
        value = json.dumps(messages, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        return {'chars': len(value), 'utf8_bytes': len(value.encode())}

    def measure(adapter, action):
        with patch.object(adapter, '_signature', wraps=adapter._signature) as signatures, \
             patch.object(actor, 'read_completed', wraps=actor.read_completed) as records, \
             patch.object(p, '_implementation_identity', wraps=bridge) as identities:
            start = time.perf_counter(); result = action()
            stats = {'seconds': time.perf_counter() - start, 'batch_signatures': signatures.call_count,
                     'full_record_checks': records.call_count, 'source_identities': identities.call_count}
        assert validation.current() is None
        return result, stats

    rows = []
    with patch.object(p, '_implementation_identity', bridge):
        method = SearchQAMethod(SearchQAActorAdapter(dataset), archives=[])
        with validation.operation(method.actor_adapter):
            for n in range(1, 7):
                for side in ('parent_runs', 'candidate_runs'):
                    method.register_archive(campaign / f'rounds/R{n:02}' / side)
        with method.using():
            for n in range(1, 7):
                rd = campaign / f'rounds/R{n:02}/replay'
                bundle, old_messages = read(rd / 'input.json'), read(rd / 'base_messages.json')
                before = deepcopy(bundle)
                selected = read(rd / 'result.json')['path']
                result = read(rd / selected / 'result.json')['replay']
                call, construction = measure(method.actor_adapter, lambda: modules.replay_call(bundle))
                completed, completion = measure(method.actor_adapter, lambda: call.complete(result))
                assert completed == {'replay': result} and bundle == before and call.input is bundle
                old_view = replay_input_view.restore_initial(json.loads(old_messages[1]['content']))
                new_view = replay_input_view.restore_initial(json.loads(call.messages[1]['content']))
                for run in new_view['runs']:
                    assert 'raw_content' not in run['outcome']['answer']
                    run['outcome']['answer']['raw_content'] = run['attempts'][0]['assistant']['content']
                assert p.equal(new_view, old_view), 'Projection lost or changed evidence'
                row = {'round': n, 'old_messages': size(old_messages), 'new_messages': size(call.messages),
                       'request_construction': construction, 'output_validation': completion,
                       'exact_content_and_references_restored': True, 'archived_replay_output_valid': True}
                if n == 6:
                    direct, row['without_scope_request'] = measure(method.actor_adapter, lambda: prompting.replay_messages(bundle))
                    assert direct == call.messages
                    _, row['without_scope_output'] = measure(method.actor_adapter, lambda: replay.validate_result(result, bundle['payload']))
                rows.append(row)
                print(f'R{n:02} content and output valid; construction {construction["seconds"]:.3f}s', flush=True)
    assert all(digest(Path(name)) == value for name, value in protected.items())
    assert factory() == actual
    report = {'status': 'passed', 'rounds': rows, 'protected_files_unchanged': len(protected),
              'frozen_snapshot_files_verified': len(frozen), 'native_old_identity_rejected': True,
              'test_only_identity_mapping': sorted(changed), 'model_requests': 0,
              'note': 'Message sizes are exact serialized characters/bytes, not API tokens. Timings are local single measurements, not publication or training time.'}
    write(out / 'archives.json', report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    blocked = []
    def deny(*args, **kwargs):
        blocked.append(1)
        raise AssertionError('Offline verification forbids network and subprocesses')
    from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
    from scripts.verification.verify_v28_actor_scoring import verify_data_and_messages
    identity = p.implementation_identity()
    with ExitStack() as stack:
        for name in ('socket.socket.connect', 'socket.socket.connect_ex', 'socket.create_connection', 'subprocess.Popen'):
            stack.enter_context(patch(name, deny))
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests/skill_evolution/v28'), top_level_dir=str(ROOT))
        with (out / 'unittest.log').open('w') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        report = {'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                  'passed': result.wasSuccessful(), 'blocked_network_or_process_attempts': len(blocked)}
        write(out / 'regression.json', report); print(json.dumps(report), flush=True)
        assert result.wasSuccessful()
        archives(args.receipt.resolve(), out)
        write(out / 'data.json', verify_data_and_messages())
    assert not blocked and p.implementation_identity() == identity
    write(out / 'summary.json', {'status': 'passed', **report, 'model_requests': 0,
                               'training_started': False, 'source_unchanged_during_checks': True})


if __name__ == '__main__':
    main()
