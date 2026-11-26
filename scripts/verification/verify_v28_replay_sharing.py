"""R01-R10 read-only Replay comparison, or unchanged R09 publication regression.

No provider calls. Old archives are read under a checked TEST-ONLY source identity
bridge; normal execution still rejects the old campaign. Never rewrite its files.
"""
import argparse
import ast
from contextlib import ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillAdam')]
sys.dont_write_bytecode = True
from scripts.verification.verify_v28_memory_optimization import CHANGES as MEMORY_CHANGES, digest

REPLAY_CHANGES = {'src/skill_evolution/v28/' + name for name in (
    'config.py', 'benchmarks/searchqa/prompting.py', 'benchmarks/searchqa/replay_input_view.py',
    'benchmarks/searchqa/prompts/replay.md')}


def check_baseline():
    baseline = json.loads((ROOT / 'artifacts/replay-baseline/sha256.json').read_text())
    # Existing tests may adapt to the new view; all Memory code and artifacts stay exact.
    allowed = REPLAY_CHANGES | {'tests/skill_evolution/v28/test_method.py'}
    assert all(digest(ROOT / name) == value for name, value in baseline.items() if name not in allowed)
    from src.skill_evolution.v28.benchmarks.searchqa import replay_input_view
    frozen = ROOT / 'src/skill_evolution/v25_2/replay_shared_initial.py'
    def functions(path):
        return {node.name: ast.dump(node) for node in ast.parse(path.read_text()).body
                if isinstance(node, ast.FunctionDef)}
    old, new = functions(frozen), functions(Path(replay_input_view.__file__))
    assert all(old[name] == new[name] for name in ('exact', 'share_initial', 'restore_initial'))
    return baseline, frozen


def regression(out):
    """Run all existing v28 tests and the new display tests with network disabled."""
    from scripts.verification.verify_v28_actor_scoring import verify_data_and_messages
    from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
    out.mkdir(parents=True, exist_ok=False)
    before, blocked = p.implementation_identity(), []
    def deny(*args, **kwargs):
        blocked.append(1)
        raise AssertionError('Offline verification forbids network and subprocesses')
    with ExitStack() as stack:
        for name in ('socket.socket.connect', 'socket.socket.connect_ex', 'socket.create_connection', 'subprocess.Popen'):
            stack.enter_context(patch(name, deny))
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests/skill_evolution/v28'), top_level_dir=str(ROOT))
        with (out / 'unittest.log').open('w') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        data = verify_data_and_messages()
    assert p.implementation_identity() == before
    check_baseline()
    report = {'status': 'passed' if result.wasSuccessful() and not blocked else 'failed',
              'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': len(result.skipped), 'blocked_network_or_process_attempts': len(blocked),
              'model_requests': 0, 'training_started': False, 'source_unchanged': True, 'data_checks': data}
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    assert report['status'] == 'passed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-root', type=Path, required=True)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--launch-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--publication', action='store_true', help='Run existing R09 full publication acceptance')
    mode.add_argument('--regression', action='store_true', help='Run all v28 offline tests and data checks')
    args = parser.parse_args()
    baseline, sharing_source = check_baseline()
    assert not args.output.resolve().is_relative_to(args.original_root.resolve())
    if args.regression:
        regression(args.output.resolve())
        return
    if args.publication:
        from scripts.verification import verify_v28_memory_publication as publication
        # Extend only the test harness allowlist, never production source validation.
        publication.CHANGES = MEMORY_CHANGES | REPLAY_CHANGES
        sys.argv.remove('--publication')
        publication.main()
        check_baseline()
        return

    original, campaign, out = args.original_root.resolve(), args.campaign.resolve(), args.output.resolve()
    assert original != ROOT and campaign.is_relative_to(original) and not out.is_relative_to(original)
    out.mkdir(parents=True, exist_ok=False)
    denied = []
    def guard(event, values):
        if event == 'open':
            name, mode, flags = values
            if isinstance(name, (str, bytes)):
                path = Path(os.fsdecode(name)).absolute()
                writing = (flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                if writing and not path.is_relative_to(out): raise RuntimeError(f'Write outside report: {path}')
        if event.startswith('socket.') and event != 'socket.__new__':
            denied.append(event); raise RuntimeError('Network disabled')
        if event in ('subprocess.Popen', 'os.system', 'os.kill', 'os.killpg'):
            raise RuntimeError('External execution/signals disabled')
        if event in ('os.remove', 'os.rename', 'os.mkdir', 'os.rmdir', 'os.link', 'os.symlink', 'os.chmod', 'os.truncate', 'os.utime'):
            paths = values[:2] if event in ('os.rename', 'os.link', 'os.symlink') else values[:1]
            if any(not Path(os.fsdecode(name)).absolute().is_relative_to(out) for name in paths):
                raise RuntimeError(f'Mutation outside report: {event}')
    sys.addaudithook(guard)
    protected = [q for q in (original / 'src').rglob('*') if q.suffix in ('.py', '.md', '.json')]
    protected += list((original / 'data/searchqa').rglob('*')) + list(campaign.rglob('*'))
    before = {str(q): digest(q) for q in protected if q.is_file()}
    launch = json.loads(args.launch_manifest.read_text())['sha256']
    frozen = json.loads((campaign / 'contract.json').read_text())
    assert all(digest(Path(name)) == value for name, value in launch.items())
    assert all((original / name).read_text() == value for name, value in frozen.items())

    from src.skill_evolution.v28.benchmarks.searchqa import protocol as p, evidence, facts, prompting, replay_input_view
    from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
    from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
    from src.skill_evolution.v28.method import SearchQAMethod
    from src.skill_evolution.v28 import modules, validation
    from src.skill_evolution.v28.storage import read
    from src.skill_evolution.v27.memory_view import historical_references

    old = read(campaign / 'rounds/R09/parent_runs/batch.json')['signature']['protocol']
    factory, actual = p._implementation_identity, p._implementation_identity()
    assert {k: v for k, v in old.items() if k != 'implementation_sha256'} == {
        k: v for k, v in actual.items() if k != 'implementation_sha256'}
    a, b = old['implementation_sha256'], actual['implementation_sha256']
    changed = {name for name in a.keys() | b.keys() if a.get(name) != b.get(name)}
    assert changed == MEMORY_CHANGES | REPLAY_CHANGES, changed
    assert all(digest(original / name) == value for name, value in a.items())
    dataset = SearchQADataset(batch_size=30)
    native = SearchQAMethod(SearchQAActorAdapter(dataset), archives=[])
    try: native.register_archive(campaign / 'rounds/R01/parent_runs')
    except ValueError: pass
    else: raise AssertionError('Old source identity was accepted natively')
    def bridge():
        if factory() != actual: raise ValueError('Implementation changed during acceptance')
        return deepcopy(old)
    def sizes(messages):
        serialized = json.dumps(messages, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        return {'serialized_messages_chars': len(serialized), 'utf8_bytes': len(serialized.encode('utf-8')),
                'system_chars': len(messages[0]['content']), 'user_chars': len(messages[1]['content'])}
    def allowed(view):
        return {'diff'} | set().union(*(facts.run_references(run) for run in view['runs'])) | historical_references(view['memory'])

    rows = []
    with patch.object(p, '_implementation_identity', bridge):
        method = SearchQAMethod(SearchQAActorAdapter(dataset), archives=[])
        with validation.operation(method.actor_adapter):
            for n in range(1, 11):
                for side in ('parent_runs', 'candidate_runs'):
                    method.register_archive(campaign / f'rounds/R{n:02}' / side)
        for n in range(1, 11):
            rd = campaign / f'rounds/R{n:02}/replay'
            bundle, old_messages = read(rd / 'input.json'), read(rd / 'base_messages.json')
            bundle_digest = p.digest(bundle)
            selected = read(rd / 'result.json')['path']
            result = read(rd / selected / 'result.json')['replay']
            response = read(rd / selected / 'response.json')
            assert response['finish_reason'] == 'stop' and json.loads(response['content']) == result
            with method.using(), validation.operation(method.actor_adapter):
                original_view = evidence.model_input(bundle)
                assert p.equal(original_view, json.loads(old_messages[1]['content']))
                start = time.perf_counter()
                shared = replay_input_view.model_input(original_view)
                projection_seconds = time.perf_counter() - start
                call = modules.replay_call(bundle)
                assert p.equal(json.loads(call.messages[1]['content']), shared)
                assert call.input is bundle and p.digest(bundle) == bundle_digest
                restored = replay_input_view.restore_initial(shared)
                for run in restored['runs']:
                    assert len(run['attempts']) == 1 and 'request_messages' not in run['attempts'][0]
                    run['attempts'][0]['request_messages'] = deepcopy(run['initial']['messages'])
                assert p.exact(restored) == p.exact(original_view)
                assert allowed(shared) == allowed(original_view)
                assert call.complete(result) == {'replay': result}
                # The original learning system Prompt is reproduced except for the approved view edits.
                old_prompt = (original / 'src/skill_evolution/v28/benchmarks/searchqa/prompts/replay.md').read_text()
                old_prompt = old_prompt.replace(p.execution_context(p.ACTOR), p.execution_context(bundle['background']))
                assert old_prompt == old_messages[0]['content']
            before_size, after_size = sizes(old_messages), sizes(call.messages)
            assert after_size['serialized_messages_chars'] < before_size['serialized_messages_chars']
            assert after_size['utf8_bytes'] < before_size['utf8_bytes']
            table = shared['shared_initial']['messages']
            row = {'round': f'R{n:02}', 'before': before_size, 'after': after_size,
                   'character_reduction': 1 - after_size['serialized_messages_chars'] / before_size['serialized_messages_chars'],
                   'pairs': len(shared['pairs']), 'runs': len(shared['runs']),
                   'shared_system_messages': sum(m['role'] == 'system' for m in table.values()),
                   'shared_user_messages': sum(m['role'] == 'user' for m in table.values()),
                   'projection_seconds': projection_seconds, 'content_and_references_match': True,
                   'archived_replay_output_valid': True, 'archived_api_prompt_tokens': response.get('usage', {}).get('prompt_tokens'),
                   'new_api_prompt_tokens': None, 'reference_tokens': None}
            rows.append(row)
            (out / f'R{n:02}_messages.json').write_text(json.dumps(call.messages, ensure_ascii=False, indent=2) + '\n')
            print(f"R{n:02}: {before_size['serialized_messages_chars']:,} -> {after_size['serialized_messages_chars']:,} chars ({row['character_reduction']:.1%} reduction)", flush=True)

    assert all(digest(Path(name)) == value for name, value in before.items())
    assert all(digest(Path(name)) == value for name, value in launch.items())
    assert all((original / name).read_text() == value for name, value in frozen.items())
    assert factory() == actual
    check_baseline()
    report = {'status': 'passed', 'rounds': rows, 'protected_files_unchanged': len(before),
              'launch_manifest_files_unchanged': len(launch), 'campaign_source_texts_unchanged': len(frozen),
              'memory_baseline_preserved': True, 'baseline_manifest_sha256': digest(ROOT / 'artifacts/replay-baseline/sha256.json'),
              'native_old_identity_rejected': True, 'test_only_identity_bridge': sorted(changed),
              'sharing_source': str(sharing_source), 'sharing_source_sha256': digest(sharing_source),
              'shared_functions_match_v25_2_ast': True, 'denied_network_operations': denied,
              'model_requests': 0, 'training_started': False,
              'size_note': 'Exact compact JSON message-array sizes, including the changed system Prompt and sharing table. No token estimates or API savings claims.',
              'optimized_source_sha256': b}
    (out / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f'All ten rounds passed; {len(before)} protected files unchanged.', flush=True)


if __name__ == '__main__':
    main()
