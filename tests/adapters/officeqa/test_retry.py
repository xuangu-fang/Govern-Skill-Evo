"""No network: durable budgets, temporary correction and tool commit boundaries."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
import requests

from src.adapters.officeqa import retry, runtime as runtime_module
from src.adapters.officeqa.retry import GenerationExhausted
from src.adapters.officeqa.runtime import ChatTransport, ToolExecutionInterrupted
from src.adapters.officeqa.transport import RequestFailure
from test_aligned import fixture, no_network, response, ScriptedProvider, invoke


def bad_call():
    value = response(calls=[('read', {'path': 'a'})])
    value['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = '{not JSON'
    return value


def run(fixture, provider):
    dataset, runtime, root = fixture
    return runtime.run(dataset.case('fixture'), None,
        ChatTransport(offline_create=provider, model='fixture', max_completion_tokens=1234),
        owner='govern', directory=root/'retry')


def state(fixture):
    return json.loads((fixture[2]/'retry/actor_state.json').read_text())


@pytest.mark.parametrize('calls', [{}, '', False, 0])
def test_empty_invalid_tool_calls_receive_temporary_format_feedback(fixture, calls):
    invalid = response(None)
    invalid['choices'][0]['finish_reason'] = 'tool_calls'
    invalid['choices'][0]['message']['tool_calls'] = calls
    provider = ScriptedProvider([invalid, response('1000')])
    record = run(fixture, provider)
    messages = provider.bodies[1]['messages']
    assert messages[:-2] == provider.bodies[0]['messages']
    assert json.loads(messages[-2]['content'])['tool_calls'] == calls
    assert 'tool_calls must be a JSON array' in messages[-1]['content']
    assert 'No tools from this response were executed' in messages[-1]['content']
    assert record['raw_result']['api_requests'] == 2
    assert record['raw_result']['n_tool_calls'] == 0
    assert record['metrics']['em'] == 1
    assert state(fixture)['rounds'][0]['attempts'][0]['status'] == 'format_error'
    assert state(fixture)['rounds'][0]['repair'] is None
    assert 'Previous Tool Call Validation Error' not in json.dumps(record['raw_result']['messages'])


@pytest.mark.parametrize('calls', [[], None, 'absent'])
def test_valid_empty_or_missing_tool_calls_keep_empty_response_retry(fixture, calls):
    empty = response(None)
    message = empty['choices'][0]['message']
    if calls == 'absent':
        message.pop('tool_calls')
    else:
        message['tool_calls'] = calls
    provider = ScriptedProvider([empty, response('1000')])
    record = run(fixture, provider)
    assert provider.bodies[0] == provider.bodies[1]
    assert state(fixture)['rounds'][0]['attempts'][0]['status'] == 'technical_error'
    assert record['raw_result']['api_requests'] == 2


def test_shared_six_attempt_budget_and_latest_temporary_feedback(fixture):
    truncated = response('partial')
    truncated['choices'][0]['finish_reason'] = 'length'
    invalid = bad_call()
    duplicate = response(calls=[('glob', {'pattern': '*'})] * 2)
    duplicate['choices'][0]['message']['tool_calls'][1]['id'] = 'call_0'
    script = iter([TimeoutError(), invalid, truncated, response(''), duplicate, response('wrong answer')])
    bodies = []
    def provider(**body):
        bodies.append(deepcopy(body))
        value = next(script)
        if isinstance(value, Exception):
            raise value
        return value
    record = run(fixture, provider)
    assert len(bodies) == record['raw_result']['api_requests'] == 6
    assert bodies[0] == bodies[1]  # Network failure changed no input.
    assert bodies[2] == bodies[3] == bodies[4]  # Truncation/empty preserve current repair.
    assert 'valid JSON' in bodies[2]['messages'][-1]['content']
    assert 'unique' in bodies[5]['messages'][-1]['content']
    assert len(bodies[5]['messages']) == len(bodies[0]['messages']) + 2
    assert 'tool_calls' not in bodies[5]['messages'][-2]  # Invalid calls are plain text.
    assert len(record['raw_result']['messages']) == len(bodies[0]['messages']) + 1
    assert record['raw_result']['n_turns'] == 1 and record['metrics']['em'] == 0
    assert state(fixture)['rounds'][0]['repair'] is None
    assert len(record['raw_result']['usage_records']) == 6


@pytest.mark.parametrize('owner', ['govern', 'skillopt', 'skilladam'])
def test_all_method_bridges_use_format_correction(fixture, owner):
    provider = ScriptedProvider([bad_call(), response(''), response('1000')])
    record = invoke(owner, fixture, provider)
    assert record['raw_result']['api_requests'] == 3
    assert record['metrics']['em'] == 1
    assert provider.bodies[1] == provider.bodies[2]


def test_whole_round_is_validated_before_first_tool(fixture, monkeypatch):
    invalid = response(calls=[('glob', {'pattern': '*'}), ('read', {'path': 'a'})])
    invalid['choices'][0]['message']['tool_calls'][1]['function']['arguments'] = '['
    monkeypatch.setattr(runtime_module.native, '_run_officeqa_tool', lambda *a, **k: pytest.fail('No tool may run'))
    record = run(fixture, ScriptedProvider([invalid, response('1000')]))
    assert record['raw_result']['n_tool_calls'] == 0


def test_new_round_gets_budget_only_after_accepted_tool_turn(fixture):
    values = iter([TimeoutError()] * 5 + [response(calls=[('glob', {'pattern': '*'})])]
                  + [TimeoutError()] * 5 + [response('1000')])
    def provider(**body):
        value = next(values)
        if isinstance(value, Exception):
            raise value
        return value
    record = run(fixture, provider)
    assert record['raw_result']['n_turns'] == 2
    assert record['raw_result']['api_requests'] == 12
    assert [len(rd['attempts']) for rd in state(fixture)['rounds']] == [6, 6]


def test_resume_retains_used_attempt_and_format_context(fixture):
    bodies = []
    def interrupted(**body):
        bodies.append(deepcopy(body))
        if len(bodies) == 1:
            return bad_call()
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        run(fixture, interrupted)
    assert len(state(fixture)['rounds'][0]['attempts']) == 2
    provider = ScriptedProvider([response('1000')])
    record = run(fixture, provider)
    assert provider.bodies[0] == bodies[-1]
    assert record['raw_result']['api_requests'] == 3
    assert state(fixture)['rounds'][0]['attempts'][1]['status'] == 'interrupted'


def test_unknown_sixth_request_does_not_get_seventh_on_resume(fixture):
    calls = []
    def provider(**body):
        calls.append(body)
        if len(calls) == 6:
            raise KeyboardInterrupt()
        raise TimeoutError()
    with pytest.raises(KeyboardInterrupt):
        run(fixture, provider)
    with pytest.raises(GenerationExhausted):
        run(fixture, lambda **kw: pytest.fail('Must not issue seventh request'))
    assert len(calls) == 6
    assert state(fixture)['status'] == 'generation_incomplete'
    assert 'record' not in state(fixture)


@pytest.mark.parametrize('count', [1, 6])
def test_saved_response_recovers_without_another_request(fixture, monkeypatch, count):
    real = retry.parse_turn
    def interrupted(value, **kwargs):
        if value['choices'][0]['message']['content'] == '1000':
            raise KeyboardInterrupt()
        return real(value, **kwargs)
    monkeypatch.setattr(retry, 'parse_turn', interrupted)
    with pytest.raises(KeyboardInterrupt):
        run(fixture, ScriptedProvider([response('')] * (count - 1) + [response('1000')]))
    assert state(fixture)['rounds'][0]['attempts'][-1]['status'] == 'received'
    monkeypatch.setattr(retry, 'parse_turn', real)
    record = run(fixture, lambda **kw: pytest.fail('Durable response must be reused'))
    assert record['raw_result']['api_requests'] == count
    assert run(fixture, lambda **kw: pytest.fail('Completed Actor must be reused')) == record


def test_temporary_feedback_clears_after_tool_execution(fixture):
    provider = ScriptedProvider([bad_call(), response(calls=[('glob', {'pattern': '*'})]), response('1000')])
    record = run(fixture, provider)
    assert 'Previous Tool Call Validation Error' in provider.bodies[1]['messages'][-1]['content']
    assert 'Previous Tool Call Validation Error' not in json.dumps(provider.bodies[2]['messages'])
    assert [len(rd['attempts']) for rd in state(fixture)['rounds']] == [2, 1]
    assert record['raw_result']['n_tool_calls'] == 1


def test_valid_call_argument_error_is_a_normal_tool_observation(fixture):
    dataset, runtime, _ = fixture
    provider = ScriptedProvider([response(calls=[('read', {
        'path': str(runtime.text_root / dataset.case('fixture').payload['source_files'][0]), 'start': 'bad'})]), response('1000')])
    record = run(fixture, provider)
    assert provider.bodies[1]['messages'][-1]['role'] == 'tool'
    assert 'invalid line window' in provider.bodies[1]['messages'][-1]['content']
    assert [len(rd['attempts']) for rd in state(fixture)['rounds']] == [1, 1]
    assert record['raw_result']['n_tool_calls'] == 1


def test_non_retryable_request_failure_is_not_reissued_on_resume(fixture):
    calls = []
    def provider(**body):
        calls.append(body)
        raise RequestFailure('HTTP 401', retryable=False)
    with pytest.raises(RequestFailure):
        run(fixture, provider)
    with pytest.raises(RequestFailure):
        run(fixture, provider)
    assert len(calls) == 1


def test_completed_tools_are_not_replayed_on_resume(fixture, monkeypatch):
    calls = []
    real_save = runtime_module.atomic_json
    def tool(call, **kwargs):
        calls.append(call.call_id)
        return 'fixture observation'
    def interrupted_save(path, value):
        real_save(path, value)
        if value['calls'] == 1:
            raise KeyboardInterrupt()
    monkeypatch.setattr(runtime_module.native, '_run_officeqa_tool', tool)
    monkeypatch.setattr(runtime_module, 'atomic_json', interrupted_save)
    with pytest.raises(KeyboardInterrupt):
        run(fixture, ScriptedProvider([response(calls=[('glob', {'pattern': '*'})] * 2)]))
    monkeypatch.setattr(runtime_module, 'atomic_json', real_save)
    record = run(fixture, ScriptedProvider([response('1000')]))
    assert calls == ['call_0', 'call_1']
    assert record['raw_result']['n_tool_calls'] == 2
    assert record['raw_result']['api_requests'] == 2


def test_unknown_tool_result_blocks_replay_and_model_requests(fixture, monkeypatch):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt()
    monkeypatch.setattr(runtime_module.native, '_run_officeqa_tool', interrupted)
    with pytest.raises(KeyboardInterrupt):
        run(fixture, ScriptedProvider([response(calls=[('glob', {'pattern': '*'})])]))
    monkeypatch.setattr(runtime_module.native, '_run_officeqa_tool', lambda *a, **kw: pytest.fail('No replay'))
    with pytest.raises(ToolExecutionInterrupted):
        run(fixture, lambda **kw: pytest.fail('No generation after tool execution starts'))


@pytest.mark.parametrize('finish', ['content_filter', 'unsupported'])
def test_non_retryable_finish_is_persistent(fixture, finish):
    value = response('blocked')
    value['choices'][0]['finish_reason'] = finish
    provider = ScriptedProvider([value])
    with pytest.raises(RequestFailure):
        run(fixture, provider)
    with pytest.raises(RequestFailure):
        run(fixture, lambda **kw: pytest.fail('Fatal error must remain fatal'))
    assert len(provider.bodies) == 1


@pytest.mark.parametrize('status,code,retryable', [
    (400, 'bad_request', False), (401, 'invalid_key', False), (403, 'permission', False),
    (429, 'insufficient_quota', False), (429, 'rate_limit', True), (408, '', True),
    (409, '', True), (500, '', True), (502, '', True), (503, '', True), (504, '', True),
])
def test_http_classification_is_single_attempt(monkeypatch, status, code, retryable):
    calls = []
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def mount(self, prefix, adapter):
            assert adapter.max_retries.total == 0
        def post(self, endpoint, **kwargs):
            calls.append(kwargs)
            assert kwargs['timeout'] == (10, 300)
            assert kwargs['allow_redirects'] is False
            return SimpleNamespace(status_code=status, text='fixture HTTP error',
                                   json=lambda: {'error': {'code': code}})
    monkeypatch.setattr(requests, 'Session', Session)
    transport = ChatTransport(endpoint='https://fixture.invalid/chat/completions', api_key='synthetic-key',
                              model='fixture', max_completion_tokens=1234)
    with pytest.raises(RequestFailure) as error:
        transport(messages=[{'role': 'user', 'content': 'synthetic'}], tools=retry.TOOL_SCHEMAS)
    assert error.value.retryable is retryable and len(calls) == 1
    assert 'synthetic-key' not in json.dumps(transport.metadata())


def test_direct_http_success_uses_no_sdk_and_flattens_extra_body(monkeypatch):
    calls = []
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def mount(self, prefix, adapter): assert adapter.max_retries.total == 0
        def post(self, endpoint, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(status_code=200, json=lambda: response('1000'))
    monkeypatch.setattr(requests, 'Session', Session)
    transport = ChatTransport(endpoint='https://fixture.invalid/chat/completions', api_key='synthetic-key',
        model='fixture', max_completion_tokens=1234, reasoning_effort='medium', reasoning_mode='extra_body')
    assert transport(messages=[{'role': 'user', 'content': 'synthetic'}], tools=retry.TOOL_SCHEMAS) == response('1000')
    assert 'extra_body' not in calls[0]['json']
    assert calls[0]['json']['reasoning'] == {'effort': 'medium'}


@pytest.mark.parametrize('mode,explicit', [('omit', False), ('top_level', False), ('explicit_none', True)])
def test_explicit_nonthinking_is_opt_in_and_recorded(monkeypatch, mode, explicit):
    calls = []
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def mount(self, prefix, adapter): assert adapter.max_retries.total == 0
        def post(self, endpoint, **kwargs):
            calls.append(kwargs)
            assert kwargs['timeout'] == (10, 300) and kwargs['allow_redirects'] is False
            return SimpleNamespace(status_code=200, json=lambda: response('1000'))
    monkeypatch.setattr(requests, 'Session', Session)
    transport = ChatTransport(endpoint='https://fixture.invalid/chat/completions', api_key='synthetic-key',
        model='fixture', max_completion_tokens=8192, reasoning_mode=mode, token_limit_field='max_tokens')
    messages = [{'role': 'user', 'content': 'synthetic'}]
    transport(messages=messages, tools=retry.TOOL_SCHEMAS)
    body = calls[0]['json']
    assert ('reasoning_effort' in body) == explicit
    if explicit: assert body['reasoning_effort'] == 'none'
    assert body['messages'] == messages and body['max_tokens'] == 8192
    assert transport.metadata()['reasoning_mode'] == mode
    with pytest.raises(ValueError, match='requires'):
        ChatTransport(model='fixture', max_completion_tokens=8192, offline_create=lambda **_: None,
                      reasoning_effort='high', reasoning_mode='explicit_none')
