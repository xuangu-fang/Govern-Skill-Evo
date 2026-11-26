from copy import deepcopy
import json
import pytest

from src.adapters.officeqa import runtime as runtime_module
from src.adapters.officeqa.retry import GenerationExhausted
from src.adapters.officeqa.transport import ChatTransport
from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26.benchmarks.officeqa.adapter import OfficeQAEvidenceAdapter
from src.skill_evolution.v26.benchmarks.officeqa import facts, evidence, prompting as pr, input_view as iv
from src.skill_evolution.v26 import modules
from src.skill_evolution.v26.contracts.editor import actual_diff
from .conftest import response, Provider
from .test_evidence import saved_plan, proposal
from .test_prompts import keep, conflict

SECRET = 'PRIVATE_REASONING_SENTINEL 001.00\r\n思考 é e\u0301'


def thinking(text=None, calls=(), label=''):
    value = response(text, calls)
    value['choices'][0]['message']['reasoning_content'] = SECRET + label
    value['usage']['completion_tokens_details'] = {'reasoning_tokens': 7}
    return value


def transport(provider):
    return ChatTransport(offline_create=provider, model='deepseek-flash', max_completion_tokens=16384,
                         reasoning_mode='deepseek_thinking', reasoning_effort='medium', token_limit_field='max_tokens')


def script():
    return [thinking(calls=[('glob', {'pattern': '*.txt'}), ('glob', {'pattern': '*'})], label='first'),
            thinking(calls=[('glob', {'pattern': '*'})], label='second'), thinking('1000', label='final')]


@pytest.mark.parametrize('point', ['received', 'accepted', 'tool', 'next_request'])
def test_thinking_resume_preserves_wire_history_and_budget(office, monkeypatch, point):
    root, dataset, runtime, _ = office; values = script(); provider = Provider({'a': values})
    actor = transport(provider); real = runtime_module.atomic_json; tripped = False
    def save(path, state):
        nonlocal tripped
        real(path, state)
        if tripped or not state['rounds']: return
        rd = state['rounds'][-1]; attempts = rd['attempts']
        hit = (point == 'received' and attempts and attempts[-1]['status'] == 'received' or
               point == 'accepted' and rd['phase'] == 'generation' and attempts and attempts[-1]['status'] == 'accepted' or
               point == 'tool' and state['calls'] == 1 or
               point == 'next_request' and len(state['rounds']) == 2 and attempts and attempts[-1]['status'] == 'requesting')
        if hit: tripped = True; raise KeyboardInterrupt('offline durable boundary')
    monkeypatch.setattr(runtime_module, 'atomic_json', save)
    with pytest.raises(KeyboardInterrupt):
        runtime.run(dataset.case('a'), 'Parent\n', actor, owner='govern', directory=root/'thinking')
    monkeypatch.setattr(runtime_module, 'atomic_json', real)
    record = runtime.run(dataset.case('a'), 'Parent\n', actor, owner='govern', directory=root/'thinking')
    assert len(provider.requests) == 3
    assert record['raw_result']['api_requests'] == (4 if point == 'next_request' else 3)
    assert record['raw_result']['n_tool_calls'] == 3
    for index, body in enumerate(provider.requests):
        assert body['thinking'] == {'type': 'enabled'} and body['reasoning_effort'] == 'medium'
        prior = [m['reasoning_content'] for m in body['messages'] if m['role'] == 'assistant']
        assert prior == [v['choices'][0]['message']['reasoning_content'] for v in values[:index]]
    assert SECRET in json.dumps(record, ensure_ascii=False).replace('\\r\\n', '\r\n')
    assert 'reasoning_content' not in json.dumps(facts.audit_record(record))
    assert runtime.run(dataset.case('a'), 'Parent\n', actor, owner='govern', directory=root/'thinking') == record
    assert len(provider.requests) == 3


def test_thinking_format_feedback_is_temporary_and_resumable(office):
    root, dataset, runtime, _ = office
    bad = thinking(label='invalid'); bad['choices'][0]['message']['tool_calls'] = {}
    seen = []
    def interrupted(**body):
        seen.append(deepcopy(body))
        if len(seen) == 1: return bad
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        runtime.run(dataset.case('a'), None, transport(interrupted), owner='govern', directory=root/'thinking')
    provider = Provider({'a': script()})
    record = runtime.run(dataset.case('a'), None, transport(provider), owner='govern', directory=root/'thinking')
    assert provider.requests[0] == seen[1]
    repair = provider.requests[0]['messages'][-2]
    assert repair['reasoning_content'] == SECRET+'invalid'
    assert 'reasoning_content' not in json.loads(repair['content'])
    assert 'Previous Tool Call Validation Error' not in json.dumps(provider.requests[1]['messages'])
    assert 'reasoning_content' not in json.dumps(facts.audit_record(record))
    assert record['raw_result']['api_requests'] == 5


@pytest.mark.parametrize('bad', [None, 1, {}, 'absent'])
def test_missing_reasoning_consumes_attempt_without_tool_execution(office, bad):
    root, dataset, runtime, _ = office
    invalid = thinking(calls=[('glob', {'pattern': '*'})])
    if bad == 'absent': invalid['choices'][0]['message'].pop('reasoning_content')
    else: invalid['choices'][0]['message']['reasoning_content'] = bad
    provider = Provider({'a': [invalid]*5+[thinking('1000')]})
    record = runtime.run(dataset.case('a'), None, transport(provider), owner='govern', directory=root/'thinking')
    assert record['raw_result']['api_requests'] == 6 and record['raw_result']['n_tool_calls'] == 0
    facts.audit_record(record)


def test_unknown_sixth_thinking_request_cannot_reset_budget(office):
    root, dataset, runtime, _ = office; calls = []
    def provider(**body):
        calls.append(body)
        if len(calls) == 6: raise KeyboardInterrupt()
        raise TimeoutError()
    with pytest.raises(KeyboardInterrupt):
        runtime.run(dataset.case('a'), None, transport(provider), owner='govern', directory=root/'thinking')
    with pytest.raises(GenerationExhausted):
        runtime.run(dataset.case('a'), None, transport(provider), owner='govern', directory=root/'thinking')
    assert len(calls) == 6


def test_tampered_reasoning_rejected_before_resumed_request(office):
    root, dataset, runtime, _ = office; seen = []
    def provider(**body):
        seen.append(body)
        if len(seen) == 1: return script()[0]
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        runtime.run(dataset.case('a'), None, transport(provider), owner='govern', directory=root/'thinking')
    path = root/'thinking/actor_state.json'; state = json.loads(path.read_text())
    next(m for m in state['messages'] if m['role'] == 'assistant')['reasoning_content'] = 'tampered'
    path.write_text(json.dumps(state))
    with pytest.raises(ValueError, match='history differs'):
        runtime.run(dataset.case('a'), None, transport(provider), owner='govern', directory=root/'thinking')
    assert len(seen) == 2


def test_all_seven_module_messages_exclude_actor_reasoning(office):
    root, dataset, runtime, _ = office; provider = Provider({'a': script()*2})
    adapter = OfficeQAEvidenceAdapter(dataset, runtime, transport(provider))
    with using_benchmark(adapter):
        rows = []
        for role, skill in [('parent', 'Parent\n'), ('candidate', 'Candidate\n')]:
            path = root/(role+'.md'); path.write_text(skill)
            rows.append(adapter.actor_batch(['a'], path, root/role, {'split': 'train', 'role': role}))
        saved = saved_plan(rows[0]); adjusted = modules.preconditioner_call(saved, {'entries': [], 'sources': {}}).complete(keep())
        edited = {**saved, 'editor_status': 'candidate', 'candidate_text': 'Candidate\n',
                  'actual_diff': actual_diff('Parent\n', 'Candidate\n'), 'effective_plan': adjusted['effective_plan']}
        bundle = evidence.build_replay_from_editor(edited, 'offline', rows[0], rows[1])
        candidate = proposal(refs=['diff', 'P1:2', 'P1:3', 'Q1:outcome'])
        view, _ = evidence.build_input(bundle, candidate)
        verdict = conflict(); verdict['results'][0]['issues'][0]['evidence'] = ['Q1:outcome']
        calls = [modules.grouping_call(rows[0], 'R1'), modules.diagnosis_call(saved),
            modules.preconditioner_call(saved, {'entries': [], 'sources': {}}), modules.editor_call(adjusted),
            modules.replay_call(bundle), modules.verifier_call(view),
            modules.repair_call(evidence.build_repair_input(view, verdict, candidate), candidate, bundle['payload'])]
        for call in calls:
            encoded = json.dumps(call.messages, ensure_ascii=False)
            assert 'PRIVATE_REASONING_SENTINEL' not in encoded and 'reasoning_content' not in encoded
            assert 'PRIVATE_REASONING_SENTINEL' not in iv.exact(iv.restore(json.loads(call.messages[1]['content'])))
