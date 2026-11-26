from copy import deepcopy
import json
from threading import Event
import time

import pytest

from src.adapters.officeqa import retry, runtime as common_runtime
from src.adapters.officeqa.retry import GenerationExhausted
from src.adapters.officeqa.transport import RequestFailure
from src.adapters.officeqa.runtime import ToolExecutionInterrupted
from src.skill_evolution.v26.benchmarks.officeqa import facts, protocol as p
from .conftest import response


def test_completion_order_and_resume_preserve_run_identity(office):
    root, _, _, factory = office
    folder = root / 'batch'
    def slow_a():
        deadline = time.monotonic() + 5
        journal = folder / 'actor/results.jsonl'
        while time.monotonic() < deadline:
            if journal.exists() and journal.read_text().endswith('\n'):
                break
            Event().wait(0.005)
        else:
            raise AssertionError('Fast task did not commit its journal entry')
        return response('1000')
    def fast_b():
        return response('1000')
    adapter, provider = factory({'a': [slow_a], 'b': [fast_b]})
    cfg = {'split': 'train', 'role': 'parent'}
    records = adapter.actor_batch(['a', 'b'], None, folder, cfg)
    journal = [json.loads(line)['id'] for line in (folder / 'actor/results.jsonl').read_text().splitlines()]
    assert [r['task_id'] for r in records] == journal
    assert journal == ['b', 'a']
    assert len(provider.requests) == 2
    assert adapter.actor_batch(['a', 'b'], None, folder, cfg) == records
    assert len(provider.requests) == 2
    with pytest.raises(ValueError, match='identity differs'):
        adapter.actor_batch(['a', 'b'], None, folder, {**cfg, 'role': 'candidate'})


def test_failed_case_drains_queued_tasks_and_resume_never_resets_budget(office):
    root, dataset, _, factory = office; exhausted = Event()
    for uid in ('c', 'd', 'e', 'f'):
        row = deepcopy(dataset.rows['b']); row.update(id=uid, uid=uid, question=f'Question for {uid}?')
        dataset.rows[uid] = row
    def last_failure():
        exhausted.set(); raise RequestFailure('Timeout')
    def wait_for_failure():
        assert exhausted.wait(5)
        return response('1000')
    scripts = {'a': [RequestFailure('Timeout')] * 5 + [last_failure],
               **{uid: [wait_for_failure] for uid in ('b', 'c', 'd')},
               'e': [response('1000')], 'f': [response('1000')]}
    adapter, provider = factory(scripts); folder = root / 'drain'; cfg = {'split': 'train', 'role': 'parent'}
    with pytest.raises(GenerationExhausted):
        adapter.actor_batch(list(scripts), None, folder, cfg)
    rows = [json.loads(line) for line in (folder / 'actor/results.jsonl').read_text().splitlines()]
    assert {row['id'] for row in rows} == {'b', 'c', 'd', 'e', 'f'}
    assert len(provider.requests) == 11
    with pytest.raises(GenerationExhausted):
        adapter.actor_batch(list(scripts), None, folder, cfg)
    assert len(provider.requests) == 11
    states = [json.loads(path.read_text()) for path in (folder / 'actor/cases').rglob('actor_state.json')]
    stopped = next(s for s in states if s['identity']['task_id'] == 'a')
    assert stopped['status'] == 'generation_incomplete' and len(stopped['rounds'][0]['attempts']) == 6
    assert not adapter.is_complete(stopped)


@pytest.mark.parametrize('attempts', [1, 6])
def test_saved_response_recovered_without_another_request(office, monkeypatch, attempts):
    root, _, _, factory = office
    adapter, provider = factory({'a': [RequestFailure('Timeout')] * (attempts - 1) + [response('1000')]})
    folder = root / 'recover'; cfg = {'split': 'train', 'role': 'parent'}; original = retry.parse_turn
    def interrupt(_, **kwargs): raise KeyboardInterrupt()
    monkeypatch.setattr(retry, 'parse_turn', interrupt)
    with pytest.raises(KeyboardInterrupt): adapter.actor_batch(['a'], None, folder, cfg)
    assert len(provider.requests) == attempts
    monkeypatch.setattr(retry, 'parse_turn', original)
    record = adapter.actor_batch(['a'], None, folder, cfg)[0]
    assert record['execution']['raw_result']['api_requests'] == attempts and len(provider.requests) == attempts
    assert len(facts.build_facts([record])['facts']['runs'][0]['attempts']) == 1


def test_unknown_tool_outcome_blocks_wrapper_resume(office, monkeypatch):
    root, _, _, factory = office
    adapter, provider = factory({'a': [response(calls=[('glob', {'pattern': '*'})])]})
    folder = root / 'unknown'; cfg = {'split': 'train', 'role': 'parent'}
    def interrupt(*a, **kw): raise KeyboardInterrupt()
    monkeypatch.setattr(common_runtime.native, '_run_officeqa_tool', interrupt)
    with pytest.raises(KeyboardInterrupt): adapter.actor_batch(['a'], None, folder, cfg)
    monkeypatch.setattr(common_runtime.native, '_run_officeqa_tool', lambda *a, **kw: pytest.fail('Tool must not replay'))
    with pytest.raises(ToolExecutionInterrupted): adapter.actor_batch(['a'], None, folder, cfg)
    assert len(provider.requests) == 1


def test_source_drift_rejected_before_resume_requests(office):
    root, _, runtime, factory = office; adapter, provider = factory({'a': [response('1000')]})
    folder = root / 'source'; cfg = {'split': 'train', 'role': 'parent'}
    adapter.actor_batch(['a'], None, folder, cfg)
    source = runtime.text_root / 'treasury_bulletin_2011_03.txt'; source.write_text(source.read_text() + 'Changed\n')
    with pytest.raises(ValueError, match='identity differs'): adapter.actor_batch(['a'], None, folder, cfg)
    assert len(provider.requests) == 1


def test_native_score_rechecked_without_exposing_gold(make_run):
    record, adapter, _, _ = make_run([response('wrong')]); bad = deepcopy(record)
    bad['execution']['metrics'] = {'em': 1.0, 'f1': 1.0}
    bad['provenance']['record_sha256'] = p.digest(bad['execution'])
    with pytest.raises(ValueError, match='Native score differs'):
        adapter.check_record(bad, 'a', 'Parent\n', {'split': 'train', 'role': 'parent'})


@pytest.mark.parametrize('config,final', [
    ({'split': 'test', 'role': 'parent'}, False),
    ({'split': 'train', 'role': 'evaluation'}, True),
    ({'split': 'test', 'role': 'evaluation'}, False),
])
def test_split_and_role_guards_precede_actor_requests(office, config, final):
    root, _, _, factory = office; adapter, provider = factory({'a': [response('1000')]})
    with pytest.raises(ValueError): adapter.actor_batch(['a'], None, root / 'denied', config, final=final)
    assert provider.requests == []


def test_source_locators_can_include_pages_beyond_actual_context(make_run, office):
    # The complete requested-source list must never imply that all source bytes were shown.
    _, _, runtime, _ = office
    page = runtime.parsed_root / 'jsons/treasury_bulletin_2011_03.json'
    data = json.loads(page.read_text()); data['document']['elements'][0]['content'] = 'A' * 25000 + 'OMITTED_FROM_INITIAL'
    page.write_text(json.dumps(data))
    record, _, _, _ = make_run()
    run = facts.build_facts([record])['facts']['runs'][0]
    assert run['initial']['declared_source_pages'][0]['source_page'] == 2
    assert 'OMITTED_FROM_INITIAL' not in json.dumps(run)
    assert 'characters omitted' in json.dumps(run)
