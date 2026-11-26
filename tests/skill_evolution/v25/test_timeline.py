from copy import deepcopy
import json

import pytest

from src.skill_evolution.v25 import output_feedback as feedback, grouping
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter
from src.skill_evolution.v25.benchmarks.spreadsheetbench import timeline
from .support import MethodResponses
from .test_pipeline import campaign


def run_fixture():
    initial = [{'role': 'system', 'content': 'Full Skill'},
               {'role': 'user', 'content': 'Task and workbook preview'}]
    history = deepcopy(initial)
    attempts = []
    for i, response in enumerate(['', '```python\nraise ValueError()\n```', '```python\nsave()\n```'], 1):
        returned = {'role': 'user', 'content': 'Only visible error prefix'} if i < 3 else None
        attempts.append({'ref': f'P1:{i}', 'request_messages': deepcopy(history),
                         'response': response, 'executed_code': 'adapted code' if i > 1 else None,
                         'executed': i > 1, 'execution': {'stderr': 'x' * 10000},
                         'feedback_to_actor': returned})
        history.append({'role': 'assistant', 'content': response})
        if returned is not None:
            history.append(deepcopy(returned))
    return {'ref': 'P1', 'task_id': 'task', 'run_id': 'run',
            'initial': {'ref': 'P1:0', 'messages': initial}, 'attempts': attempts,
            'outcome': {'ref': 'P1:outcome', 'score': {'hard': 0}}}


def test_round_trip_preserves_all_fields_and_actor_knowledge_boundary():
    payload = {'parent': 'Full Skill', 'runs': [run_fixture()]}
    original = timeline.exact(payload)
    compact = timeline.project(payload)
    assert timeline.exact(payload) == original
    assert timeline.exact(timeline.restore(compact)) == original
    assert len(timeline.exact(compact)) < len(original)
    requests = list(timeline.requests_for(compact['runs'][0]))
    assert [len(x) for x in requests] == [2, 4, 6]
    assert requests[1][2] == {'role': 'assistant', 'content': ''}
    assert 'xxxxxxxx' not in timeline.exact(requests)
    assert 'score' not in timeline.exact(requests)
    assert all('request_messages' not in a for a in compact['runs'][0]['attempts'])


def test_unreconstructable_history_fails_without_mutation():
    payload = {'runs': [run_fixture()]}
    payload['runs'][0]['attempts'][1]['request_messages'][0]['content'] = 'changed system'
    original = timeline.exact(payload)
    with pytest.raises(ValueError, match='cannot be reconstructed: P1:2'):
        timeline.project(payload)
    assert timeline.exact(payload) == original


def test_review_keeps_isolated_attempt_context_and_exact_source_scope():
    run = run_fixture()
    payload = {'context': {}, 'targets': [], 'source_records': {
        'P1': {'record': run}, 'old_round/P1:2': {'record': run['attempts'][1]},
        'P1:outcome': {'record': run['outcome']}}}
    compact = timeline.project(payload)
    assert set(compact['source_records']) == set(payload['source_records'])
    assert compact['source_records']['old_round/P1:2'] == payload['source_records']['old_round/P1:2']
    assert 'request_messages' not in compact['source_records']['P1']['record']['attempts'][0]
    assert timeline.exact(timeline.restore(compact)) == timeline.exact(payload)


def test_legacy_context_and_feedback_recovery_keep_original_messages():
    messages = [{'role': 'system', 'content': 'prompt'},
                {'role': 'user', 'content': json.dumps({'runs': [run_fixture()]})}]
    with using_benchmark(SpreadsheetBenchAdapter()):
        for context in (None, {'policy': feedback.POLICY, 'feedback_from': None}):
            assert feedback.request_messages(messages, context) == messages
            def recovered():
                pass
            recovered.request_context = context
            assert feedback.generation_context(recovered) == context
        current = feedback.generation_context(lambda: None)
        projected = feedback.request_messages(messages, current)
        assert timeline.INSTRUCTION in projected[0]['content']
        assert timeline.exact(timeline.restore(json.loads(projected[1]['content']))) == timeline.exact(json.loads(messages[1]['content']))
        with pytest.raises(ValueError, match='Unsupported execution input view'):
            feedback.request_messages(messages, {**current, 'execution_view': 'unknown'})


def test_pipeline_uses_timeline_and_preserves_archives_across_retry_and_reload(tmp_path):
    method = MethodResponses(conflict=True, invalid_once='preconditioner')
    root, cfg, adapter, actors, method, result = campaign(tmp_path, method=method)
    assert result['status'] == 'complete'
    assert method.calls.count('preconditioner') == 2
    for stage, payload in method.payloads:
        if stage == 'preconditioner':
            assert set(payload) == {'parent', 'plan', 'runs', 'memory'}
        for run in timeline.full_runs(payload):
            assert all('request_messages' not in a for a in run['attempts'])
    for stage in ('grouping', 'diagnosis', 'preconditioner', 'replay', 'verifier', 'repair'):
        directory = root / 'rounds/R01' / stage
        selected = json.loads((directory / 'result.json').read_text())['path']
        path = directory / selected
        context = json.loads((path / 'request_context.json').read_text())
        assert context['execution_view'] == feedback.TIMELINE
        saved = json.loads((path / 'input.json').read_text())
        raw = saved if stage == 'grouping' else saved.get('payload', saved)
        raw = raw.get('facts', raw)
        for run in timeline.full_runs(raw):
            assert all('request_messages' in a for a in run['attempts'])
    path = root / 'rounds/R01/grouping/attempts/001'
    with using_benchmark(adapter):
        assert grouping.load_grouping(path)['facts'] == json.loads((path / 'input.json').read_text())['facts']
    assert all('request_messages' in a for p in root.rglob('actor_state.json')
               for a in json.loads(p.read_text())['attempts'])
