from .comparison import behavior
"""Second-pass coverage for import isolation, recovery and adapter boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from threading import Barrier, Event, Lock

import pytest

from src.skill_evolution.v24 import evolution as ev, config
from src.skill_evolution.v24.benchmark import current, using_benchmark
from .test_equivalence import CapturedHarness, cfg, old, ROOT, CAMPAIGN, read

STAGES = ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay', 'verifier', 'repair']


def migrated(rounds=1):
    return config.baseline_config(cfg(rounds), benchmark=current())


@pytest.mark.parametrize('stage', STAGES)
def test_interruption_consumes_budget_and_resume_does_not_reset(tmp_path, stage):
    from tests.skill_evolution.v23_5.test_unified_retry import Scripted
    captures = []
    for label, module in [('old', old), ('new', ev)]:
        h = Scripted(stage, ['schema', 'timeout', 'interrupt', 'json', 'length', 'schema', 'valid'])
        value = cfg(1) if module is old else migrated()
        value.update(max_attempts=6, retry_delay_seconds=0)
        root = tmp_path/label/'S1'
        with pytest.raises(KeyboardInterrupt):
            module.run_campaign(root, config=value, generate=h.generate, actor_runner=h.actor)
        assert len(h.requests) == 3
        for _ in range(2):
            with pytest.raises(module.Stopped, match='exhausted'):
                module.run_campaign(root, resume=True, generate=h.generate, actor_runner=h.actor)
            assert len(h.requests) == 6
        assert h.requests[1] == h.requests[2] == h.requests[3]
        assert not (root/'rounds/R01/memory').exists()
        captures.append(h.requests)
    assert behavior(captures[0]) == behavior(captures[1])


@pytest.mark.parametrize('stage', STAGES)
def test_saved_response_recovery_and_feedback_provenance(tmp_path, monkeypatch, stage):
    from tests.skill_evolution.v23_5.test_unified_retry import Scripted
    module = ev.MODULES.get(stage, ev.knowledge_review)
    write = module.write_record
    fired = False
    def interrupt(path, value):
        nonlocal fired
        write(path, value)
        if stage in path.parts and '002' in path.parts and path.name == 'response.json' and not fired:
            fired = True
            raise KeyboardInterrupt('saved complete response')
    monkeypatch.setattr(module, 'write_record', interrupt)
    h = Scripted(stage, ['schema', 'valid'])
    with pytest.raises(KeyboardInterrupt):
        ev.run_campaign(tmp_path, config=migrated(), generate=h.generate, actor_runner=h.actor)
    ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert len(h.requests) == 2
    folder = tmp_path/'rounds/R01'/stage
    selected = folder/read(folder/'result.json')['path']
    assert read(selected/'recovered_from.json')['additional_requests'] == 0
    assert read(selected/'messages.json') == h.requests[1]
    ev.final_parent(tmp_path)
    error = read(folder/'attempts/001/error.json')
    error['diagnostic']['error'] = 'tampered feedback'
    ev.save(folder/'attempts/001/error.json', error)
    with pytest.raises((ValueError, ev.Stopped)):
        ev.final_parent(tmp_path)
    assert len(h.requests) == 2


@pytest.mark.parametrize('point', ['diagnosis', 'before_publish', 'after_publish'])
def test_publication_crash_matches_baseline(tmp_path, point):
    captures = []
    for label, module in [('old', old), ('new', ev)]:
        h = CapturedHarness()
        root = tmp_path/label/'S1'
        def crash(stage):
            if stage == point:
                raise KeyboardInterrupt()
        with pytest.raises(KeyboardInterrupt):
            module.run_campaign(root, config=cfg(1) if module is old else migrated(),
                                generate=h.generate, actor_runner=h.actor, hook=crash)
        before = len(h.requests), len(h.actor_calls)
        module.run_campaign(root, resume=True, generate=h.generate, actor_runner=h.actor)
        module.final_parent(root)
        if point != 'diagnosis':
            assert before == (len(h.requests), len(h.actor_calls))
        captures.append((h.requests, read(root/'state.json'), read(root/'rounds/R01/memory/view.json')))
    assert behavior(captures[0]) == behavior(captures[1])


@pytest.mark.parametrize('stop', ['editor_empty', 'editor_null', 'preconditioner_patch'])
def test_editor_semantics_and_preconditioner_patch_match(tmp_path, stop):
    captures = []
    for label, module in [('old', old), ('new', ev)]:
        h = CapturedHarness(); h.stop = stop
        root = tmp_path/label/'S1'
        if stop == 'editor_null':
            with pytest.raises(module.Stopped, match='semantic'):
                module.run_campaign(root, config=cfg(1) if module is old else migrated(),
                                    generate=h.generate, actor_runner=h.actor)
            with pytest.raises(ValueError, match='Semantic blocker'):
                module.run_campaign(root, resume=True, generate=h.generate, actor_runner=h.actor)
        else:
            module.run_campaign(root, config=cfg(1) if module is old else migrated(),
                                generate=h.generate, actor_runner=h.actor)
            module.final_parent(root)
        captures.append((h.requests, read(root/'state.json')))
    assert behavior(captures[0]) == behavior(captures[1])


def test_historical_evidence_source_matches_and_tampering_rejected(tmp_path):
    captures = []
    for label, module in [('old', old), ('new', ev)]:
        h = CapturedHarness('supported'); h.history_ref = True
        root = tmp_path/label/'S1'
        module.run_campaign(root, config=cfg(2) if module is old else migrated(2),
                            generate=h.generate, actor_runner=h.actor)
        review = read(root/'rounds/R02/knowledge_review/input.json')
        assert list(review['historical_sources']) == ['S1_R01']
        captures.append((h.requests, review['verifier_input']))
        path = root/'rounds/R01/memory/archive/S1_R01.json'
        archive = read(path)
        archive['context']['execution_context'] = 'tampered'
        module.save(path, archive)
        with pytest.raises(ValueError):
            module.final_parent(root)
    assert behavior(captures[0]) == behavior(captures[1])


def test_actor_threads_inherit_adapter_without_alfworld_record_assumptions(tmp_path):
    original = current()
    barrier, lock = Barrier(3), Lock()
    seen = []
    class OtherBenchmark:
        def frozen_files(self): return {}
        def check_record(self, record, task, skill, config):
            assert record == {'artifact': task} and skill is None
            return record
        def is_complete(self, record): return 'artifact' in record
    adapter = OtherBenchmark()
    def runner(task, skill, dest, config):
        assert current() is adapter
        barrier.wait(timeout=10)
        with lock: seen.append(task)
        path = dest/'trajectory.json'
        ev.save(path, {'artifact': task})
        return path
    with using_benchmark(adapter):
        ev.save(tmp_path/'contract.json', ev.frozen_contract())
        tasks = ['book/a', 'book/b', 'book/c']
        paths, records = ev._actors(tmp_path, tmp_path, 'runs', tasks, None,
                                    {'actor_max_workers': 3}, runner, False)
        assert records == [{'artifact': t} for t in tasks]
        ev._actors(tmp_path, tmp_path, 'runs', tasks, None, {'actor_max_workers': 3},
                   lambda *_: pytest.fail('completed task reran'), True)
        assert len(seen) == 3 and len(paths) == 3
    assert current() is original


def test_fresh_process_replays_real_round_with_old_imports_and_source_reads_forbidden(tmp_path):
    # Unlike the paired tests, the child has no legacy fixture/harness loaded.
    code = r'''
import sys, importlib.abc, json, socket, subprocess
from pathlib import Path
root, output = Path(sys.argv[1]), Path(sys.argv[2])
old_prefixes = ('src.skill_evolution.v22', 'src.skill_evolution.v23', 'src.skill_evolution.shared', 'tests.')
class BlockOld(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(old_prefixes): raise AssertionError('legacy import: ' + fullname)
sys.meta_path.insert(0, BlockOld())
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        p = str(args[0])
        if '/src/skill_evolution/v23' in p or '/src/skill_evolution/v22' in p or '/src/skill_evolution/shared/' in p:
            raise AssertionError('legacy source read: ' + p)
    if event in ('socket.connect', 'subprocess.Popen'): raise AssertionError('live execution forbidden')
sys.addaudithook(audit)
from src.skill_evolution.v24 import evolution as ev, config
from src.skill_evolution.v24.benchmark import using_benchmark
from src.skill_evolution.v24.benchmarks.alfworld.adapter import ALFWorldAdapter
base = root/'artifacts/methods/v23_5/alfworld_verified_feedback_001/S1'
rd = base/'rounds/R01'
read = ev.read
adapter = ALFWorldAdapter()
with using_benchmark(adapter):
    value = config.baseline_config(read(base/'config.json'), benchmark=adapter)
    value['batches'] = value['batches'][:1]
    value['task_items'] = {t: value['task_items'][t] for t in value['batches'][0]}
    # Metadata query only is disabled; no real interpreter/environment is started.
    value['actor_python'] = 'offline'
    pairs = read(rd/'pairs/input.json')['record_paths']
    records = {side: {read(p)['task']['id']: p for p in paths} for side, paths in pairs.items()}
    calls = []
    def actor(task, skill, dest, cfg):
        return records['candidate' if 'candidate_runs' in dest.parts else 'parent'][task]
    def generate(messages, dest):
        stage = next(s for s in ('grouping','diagnosis','preconditioner','editor','replay','verifier','repair') if s in dest.parts)
        selected = rd/stage/read(rd/stage/'result.json')['path']
        # Preconditioner has an intentional template/input change. Compare the
        # rendered context and every remaining input field against the old record.
        if stage == 'preconditioner':
            previous = read(selected/'messages.json')
            left, right = json.loads(messages[1]['content']), json.loads(previous[1]['content'])
            right.pop('grouping')
            assert left == right
            name = 'v23_5/preconditioner_knowledge_only_prompt_feedback.md'
            template = adapter.resource(name).read_text()
            frozen = root/'experiments/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/code/src/skill_evolution/v24/benchmarks/alfworld/prompts'/name
            prefix, suffix = template.split('{{execution_context}}')
            old_prefix, old_suffix = frozen.read_text().split('{{execution_context}}')
            prompt = messages[0]['content']
            assert prompt.startswith(prefix) and prompt.count(suffix) == 1
            assert old_prefix + prompt[len(prefix):].replace(suffix, old_suffix) == previous[0]['content']
        elif stage not in ('verifier', 'repair'):
            assert messages == read(selected/'messages.json'), stage
        else:
            assert messages[0] == read(selected/'messages.json')[0]
            left, right = json.loads(messages[1]['content']), json.loads(read(selected/'messages.json')[1]['content'])
            right['context']['execution_context'].pop('backend_id', None)
            for source in right['source_records'].values():
                if 'execution_context' in source: source['execution_context'].pop('backend_id', None)
            assert left == right
        calls.append(stage)
        return read(selected/'response.json')
    result = ev.run_campaign(output/'S1', config=value, generate=generate, actor_runner=actor)
    ev.final_parent(output/'S1')
    ev.run_campaign(output/'S1', resume=True, generate=lambda *_: (_ for _ in ()).throw(AssertionError('new call')),
                    actor_runner=lambda *_: (_ for _ in ()).throw(AssertionError('new actor')))
    assert read(output/'S1/rounds/R01/knowledge_review/candidate.json') == read(rd/'knowledge_review/candidate.json')
    assert len(calls) in (6,7)
assert not [n for n in sys.modules if n.startswith(old_prefixes)]
print('isolated recorded campaign passed')
'''
    result = subprocess.run([sys.executable, '-c', code, str(ROOT), str(tmp_path)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('complete_before_crash', [False, True])
def test_actor_failure_stops_replenishment_and_resume_preserves_saved_records(tmp_path, complete_before_crash):
    barrier = Barrier(2)
    failed = Event()
    calls = []
    class OtherBenchmark:
        def frozen_files(self): return {}
        def check_record(self, record, task, skill, config):
            assert record == {'artifact': task, 'complete': True}
            return record
        def is_complete(self, record): return record['complete']
    tasks = ['a', 'b', 'c']
    first = True
    def runner(task, skill, dest, config):
        calls.append(task)
        path = dest/'trajectory.json'
        ev.save(path, {'artifact': task, 'complete': not first or task != 'a' or complete_before_crash})
        if first:
            barrier.wait(timeout=10)
            if task == 'a': raise RuntimeError('actor interrupted')
            # Ensure the scheduler sees failure before it can replenish.
            assert failed.wait(timeout=10)
        return path
    def guarded(*args):
        try: return runner(*args)
        except RuntimeError:
            failed.set()
            raise
    with using_benchmark(OtherBenchmark()):
        ev.save(tmp_path/'contract.json', ev.frozen_contract())
        with pytest.raises(RuntimeError, match='actor interrupted'):
            ev._actors(tmp_path, tmp_path, 'runs', tasks, None, {'actor_max_workers': 2}, guarded, False)
        assert sorted(calls) == ['a', 'b']
        saved = {p: p.read_bytes() for p in (tmp_path/'runs').rglob('trajectory.json')}
        first = False
        _, records = ev._actors(tmp_path, tmp_path, 'runs', tasks, None, {'actor_max_workers': 2}, guarded, True)
        assert records == [{'artifact': t, 'complete': True} for t in tasks]
        assert calls.count('a') == (1 if complete_before_crash else 2)
        assert calls.count('b') == calls.count('c') == 1
        assert all(p.read_bytes() == data for p, data in saved.items())


@pytest.mark.parametrize('field', ['max_input_chars', 'max_input_bytes'])
def test_input_limit_stops_before_model_request(tmp_path, field):
    h = CapturedHarness()
    value = migrated(); value[field] = 1
    with pytest.raises(ev.Stopped):
        ev.run_campaign(tmp_path, config=value, generate=h.generate, actor_runner=h.actor)
    assert not h.requests
    with pytest.raises(ev.Stopped):
        ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert not h.requests
