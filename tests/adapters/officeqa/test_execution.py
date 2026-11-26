"""Offline integration tests for concurrency, request timeout and restart."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from threading import Event, Lock
import time

import pytest
from skilladam.execution.contracts import BackendContext, BatchExecution

from src.adapters.officeqa.bridges import GovernActor, SkillAdamAdapter, SkillAdamBackend, SkillOptAdapter
from src.adapters.officeqa.execution import run_batch
from src.adapters.officeqa.runtime import ChatTransport
from test_aligned import fixture, no_network, response


def batch_fixture(fixture):
    dataset, runtime, root = fixture
    template = dataset.rows['fixture']
    dataset.rows = {}
    for i in range(5):
        row = deepcopy(template)
        row.update(id=str(i), uid=str(i), question=f'Question {i}?')
        dataset.rows[str(i)] = row
    dataset.splits['train'] = list(dataset.rows)
    return dataset, runtime, root


def make_runner(owner, fixture, provider, *, limit=1234):
    dataset, runtime, root = fixture
    transport = ChatTransport(offline_create=provider, model='fixture', max_completion_tokens=limit)
    directory = root / owner
    if owner == 'govern':
        actor = GovernActor(dataset, runtime, transport)
        return lambda: actor.actor_batch(list(dataset.rows), None, directory, {'split': 'train'})
    if owner == 'skillopt':
        actor = SkillOptAdapter(dataset, runtime, transport)
        return lambda: [r['aligned_record'] for r in actor.rollout(list(dataset.rows.values()), None, directory)]
    adapter = SkillAdamAdapter(dataset)
    requests = tuple(adapter.build_rollout_request(case, method='skilladam', split='train', skill=None, seed=42)
                     for case in dataset.cases('train'))
    context = BackendContext('officeqa', 'skilladam', 'fixture', 'none', 4, 42)
    backend = SkillAdamBackend(dataset, runtime, transport, output_dir=directory)
    return lambda: [r.result['aligned_record'] for r in backend.execute_batch(BatchExecution(requests, context, 'offline'))]


def journal(directory):
    path = directory / 'results.jsonl'
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines(keepends=True) if line.endswith('\n')]


def wait_for(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('Timed out waiting for offline test synchronization')


@pytest.mark.parametrize('owner', ['govern', 'skillopt', 'skilladam'])
def test_four_workers_completion_order_and_restart(fixture, owner):
    fixture = batch_fixture(fixture)
    started = [Event() for _ in range(5)]
    release = [Event() for _ in range(5)]
    calls, lock = [], Lock()

    def provider(**body):
        assert body['timeout'] == 300
        i = next(i for i in range(5) if f'Question {i}?' in body['messages'][1]['content'])
        with lock:
            calls.append(i)
        started[i].set()
        assert release[i].wait(10)
        return response('1000')

    runner = make_runner(owner, fixture, provider)
    directory = fixture[2] / owner
    with ThreadPoolExecutor(max_workers=1) as coordinator:
        pending = coordinator.submit(runner)
        try:
            assert all(event.wait(5) for event in started[:4])
            assert not started[4].is_set()  # Fifth task must remain queued.
            order = [3, 4, 1, 2, 0]
            for count, i in enumerate(order, 1):
                release[i].set()
                wait_for(lambda: len(journal(directory)) == count)
            records = pending.result(timeout=5)
        finally:
            for event in release:
                event.set()
    assert [r['task_id'] for r in records] == list(map(str, order))
    assert [r['id'] for r in journal(directory)] == list(map(str, order))
    assert runner() == records
    assert sorted(calls) == list(range(5))  # No second provider calls on restart.
    with pytest.raises(ValueError, match='identity differs'):
        make_runner(owner, fixture, provider, limit=2345)()
    assert len(calls) == 5


@pytest.mark.parametrize('owner', ['govern', 'skillopt', 'skilladam'])
def test_request_failure_preserves_other_cases_and_restarts_only_missing(fixture, owner):
    fixture = batch_fixture(fixture)
    calls, lock = [], Lock()
    failing = True

    def provider(**body):
        i = next(i for i in range(5) if f'Question {i}?' in body['messages'][1]['content'])
        with lock:
            calls.append(i)
        if i == 2 and failing:
            raise TimeoutError('synthetic request timeout')
        return response('wrong' if i == 1 else '1000')

    runner = make_runner(owner, fixture, provider)
    from src.adapters.officeqa.retry import GenerationExhausted
    with pytest.raises(GenerationExhausted):
        runner()
    assert calls.count(2) == 6 and len(calls) == 10
    rows = journal(fixture[2] / owner)
    assert {r['id'] for r in rows} == {'0', '1', '3', '4'}
    assert next(r['record'] for r in rows if r['id'] == '1')['metrics']['em'] == 0
    failing = False
    with pytest.raises(GenerationExhausted):
        runner()
    assert calls.count(2) == 6 and len(calls) == 10  # Resume cannot replenish requests.
    assert len(journal(fixture[2] / owner)) == 4


def test_torn_journal_tail_is_repaired_without_repeating_committed_cases(tmp_path):
    calls = []
    def execute(uid):
        calls.append(uid)
        return {'task_id': uid}
    items = [('a', 'a'), ('b', 'b')]
    expected = run_batch(items, execute, tmp_path, identity={})
    path = tmp_path / 'results.jsonl'
    with path.open('ab') as handle:
        handle.write(b'{"id": "interrupted')
    assert run_batch(items, execute, tmp_path, identity={}) == expected
    assert sorted(calls) == ['a', 'b']
    assert len(journal(tmp_path)) == 2


def test_complete_corrupt_journal_is_rejected_before_execution(tmp_path):
    run_batch([], lambda _: None, tmp_path, identity={})
    (tmp_path/'results.jsonl').write_text('{bad json}\n')
    with pytest.raises(json.JSONDecodeError):
        run_batch([], lambda _: pytest.fail('must not execute'), tmp_path, identity={})


def test_single_govern_task_resume_precedes_model_call(fixture):
    dataset, runtime, root = fixture
    calls = []
    def provider(**body):
        calls.append(body)
        return response('1000')
    actor = GovernActor(dataset, runtime, ChatTransport(offline_create=provider, model='fixture', max_completion_tokens=12))
    first = actor.actor_task('fixture', None, root/'one', {'split': 'train'})
    assert actor.actor_task('fixture', None, root/'one', {'split': 'train'}) == first
    assert len(calls) == 1
