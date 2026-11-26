from copy import deepcopy
import json

import pytest

from src.skill_evolution.v26.benchmark import using_benchmark
from src.skill_evolution.v26 import evolution as ev, modules, stages
from src.skill_evolution.v26.transport import RequestFailure, HTTPGenerator
from .test_campaign import campaign, FixedModules


@pytest.fixture
def stage_case(campaign):
    root, adapter, provider, config, generate = campaign()
    def prepare():
        skill = root.parent / 'parent.md'; skill.write_text('Parent\n')
        records = adapter.actor_batch(['a'], skill, root.parent / 'actors', {'split': 'train', 'role': 'parent'})
        call = modules.grouping_call(records, 'offline_R01')
        kwargs = dict(call_config=config['module_calls']['grouping'], max_attempts=6,
                      max_input_chars=config['max_input_chars'], max_message_utf8_bytes=config['max_message_utf8_bytes'])
        return root / 'grouping', call, kwargs
    return adapter, generate, prepare


def test_only_latest_output_error_feedback_and_technical_retry_unchanged(stage_case):
    adapter, good, prepare = stage_case; calls = []
    def generate(name, messages, directory, config):
        calls.append(deepcopy(messages))
        if len(calls) == 1: return {'content': 'not JSON', 'finish_reason': 'stop'}
        if len(calls) == 2: raise RequestFailure('timeout')
        if len(calls) == 3: return {'content': '{}', 'finish_reason': 'stop'}
        return good(name, messages, directory, config)
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        stages.run_stage(directory, call, generate=generate, **kwargs)
        assert len(calls) == 4
        assert calls[1] == calls[2] and calls[1][:2] == calls[0]
        assert calls[1][2]['content'] == 'not JSON'
        assert calls[3][2]['content'] == '{}' and len(calls[3]) == 4
        assert 'not JSON' not in json.dumps(calls[3])
        stages.run_stage(directory, call, generate=None, read_only=True, **kwargs)
        assert len(calls) == 4


@pytest.mark.parametrize('failure', ['format', 'timeout', 'truncated', 'malformed'])
def test_six_slots_are_total_attempts_and_resume_does_not_reset(stage_case, failure):
    adapter, _, prepare = stage_case; calls = []
    def generate(name, messages, directory, config):
        calls.append(messages)
        if failure == 'timeout': raise RequestFailure('timeout')
        if failure == 'malformed': return []
        return {'content': '{}' if failure == 'format' else 'partial',
                'finish_reason': 'stop' if failure == 'format' else 'length'}
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        with pytest.raises(stages.Stopped, match='exhausted'): stages.run_stage(directory, call, generate=generate, **kwargs)
        with pytest.raises(stages.Stopped, match='exhausted'): stages.run_stage(directory, call, generate=generate, resume=True, **kwargs)
    assert len(calls) == 6
    assert len(list((directory / 'attempts').iterdir())) == 6
    if failure != 'format': assert all(c == calls[0] for c in calls)


@pytest.mark.parametrize('saved_kind', ['response', 'http'])
def test_sixth_saved_response_recovers_without_seventh_request(stage_case, saved_kind):
    adapter, good, prepare = stage_case; calls = []
    def generate(name, messages, directory, config):
        calls.append(messages)
        if len(calls) < 6: raise RequestFailure('temporary error')
        response = good(name, messages, directory, config)
        if saved_kind == 'response': stages.save(directory / 'response.json', response)
        else:
            stages.save(directory / 'http_status.json', {'status_code': 200})
            stages.save(directory / 'http_response.txt', {'choices': [{'message': {'content': response['content']}, 'finish_reason': 'stop'}]})
        raise KeyboardInterrupt('Response is durable; result is not')
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        with pytest.raises(KeyboardInterrupt): stages.run_stage(directory, call, generate=generate, **kwargs)
        selected, result = stages.run_stage(directory, call, generate=None, resume=True, **kwargs)
    assert selected.name == '006' and result['grouping']['groups']
    assert len(calls) == 6 and stages.read(selected / 'recovery.json')['additional_requests'] == 0


def test_unknown_interrupted_request_consumes_slot(stage_case):
    adapter, good, prepare = stage_case
    def interrupted(*args): raise KeyboardInterrupt('No durable response')
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        with pytest.raises(KeyboardInterrupt): stages.run_stage(directory, call, generate=interrupted, **kwargs)
        selected, _ = stages.run_stage(directory, call, generate=good, resume=True, **kwargs)
    assert selected.name == '002'
    assert stages.read(directory / 'attempts/001/error.json')['kind'] == 'technical'


@pytest.mark.parametrize('exception', [OSError('disk'), ValueError('generator bug'), RequestFailure('quota', retryable=False)])
def test_local_or_fatal_failures_stop_without_format_feedback(stage_case, exception):
    adapter, _, prepare = stage_case; calls = []
    def generate(*args):
        calls.append(1); raise exception
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        with pytest.raises(stages.Stopped): stages.run_stage(directory, call, generate=generate, **kwargs)
        with pytest.raises(stages.Stopped): stages.run_stage(directory, call, generate=generate, resume=True, **kwargs)
    assert len(calls) == 1
    assert stages.read(directory / 'attempts/001/error.json')['kind'] == 'technical'


def test_selected_archive_corruption_is_not_output_retry(stage_case):
    adapter, good, prepare = stage_case
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        selected, _ = stages.run_stage(directory, call, generate=good, **kwargs)
        stages.save(selected / 'result.json', {'fake': 'archive'})
        with pytest.raises(ValueError): stages.run_stage(directory, call, generate=good, resume=True, **kwargs)
    assert len(good.calls) == 1


@pytest.mark.parametrize('key', ['max_input_chars', 'max_message_utf8_bytes'])
def test_capacity_failure_consumes_no_request_slot(stage_case, key):
    adapter, good, prepare = stage_case
    with using_benchmark(adapter):
        directory, call, kwargs = prepare(); kwargs[key] = 1
        with pytest.raises(ValueError, match='capacity'): stages.run_stage(directory, call, generate=good, **kwargs)
    assert not good.calls and not list((directory / 'attempts').iterdir())


def test_method_http_transport_is_one_request_with_frozen_options(tmp_path, monkeypatch):
    seen = []
    class Raw:
        status_code = 200
        content = b'{"choices":[{"message":{"content":"{}"},"finish_reason":"stop"}]}'
        def json(self): return json.loads(self.content)
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def mount(self, prefix, adapter): assert adapter.max_retries.total == 0
        def post(self, endpoint, **kwargs):
            seen.append((endpoint, kwargs)); return Raw()
    monkeypatch.setattr('requests.Session', Session)
    config = {'endpoint': 'https://fixture.invalid/chat/completions', 'model': 'fixture', 'max_tokens': 4321,
              'timeout_seconds': 301, 'temperature': 0.7, 'reasoning_effort': 'medium',
              'token_limit_field': 'max_completion_tokens'}
    result = HTTPGenerator('SYNTHETIC_KEY')('diagnosis', [{'role': 'user', 'content': 'fixture'}], tmp_path, config)
    assert result['finish_reason'] == 'stop' and len(seen) == 1
    options = seen[0][1]
    assert options['json']['max_completion_tokens'] == 4321 and options['timeout'] == (10, 301)
    assert options['allow_redirects'] is False and 'SYNTHETIC_KEY' not in (tmp_path / 'request.json').read_text()


@pytest.mark.parametrize('status,body,retryable', [(403, 'denied', False), (429, 'insufficient_quota', False),
                                                 (500, 'temporary', True), (200, 'bad JSON', True)])
def test_recovered_raw_http_error_preserves_classification(stage_case, status, body, retryable):
    adapter, good, prepare = stage_case
    def interrupted(name, messages, directory, config):
        stages.save(directory / 'http_status.json', {'status_code': status})
        (directory / 'http_response.txt').write_text(body)
        raise KeyboardInterrupt('Raw HTTP response saved before parsing')
    with using_benchmark(adapter):
        directory, call, kwargs = prepare()
        with pytest.raises(KeyboardInterrupt): stages.run_stage(directory, call, generate=interrupted, **kwargs)
        if retryable:
            selected, _ = stages.run_stage(directory, call, generate=good, resume=True, **kwargs)
            assert selected.name == '002'
        else:
            with pytest.raises(stages.Stopped): stages.run_stage(directory, call, generate=good, resume=True, **kwargs)
            assert not good.calls
