"""Offline protocol tests: real OpenAI SDK, simulated HTTP, no model calls."""
from copy import deepcopy
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.bridge import spreadsheetbench_native_optimizer as app
from src.skill_evolution.skilladam.spreadsheetbench.layout import ALIGNED_CONFIG as EXPERIMENT


@pytest.fixture(scope='module')
def config():
    bridge = app.load_bridge(EXPERIMENT)
    return bridge, app.read(EXPERIMENT / 'shared_config.json'), app.read(EXPERIMENT / 'skilladam.json')


def response(text='summary', finish='stop', tools=None):
    return {'id': 'offline', 'object': 'chat.completion', 'created': 0, 'model': 'offline',
            'choices': [{'index': 0, 'finish_reason': finish,
                         'message': {'role': 'assistant', 'content': text, 'tool_calls': tools}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}


def request(config):
    from skilladam.execution.contracts import GenerationRequest
    bridge, shared, cfg = config
    return GenerationRequest('trajectory_compression', ({'role': 'user', 'content': 'summarize'},),
                             bridge.context_for(shared, cfg), {})


def transport(config, tmp_path, handler):
    bridge, shared, cfg = config
    return app.native_transport(bridge, shared, cfg, tmp_path,
                                api_key='offline-placeholder', http_transport=httpx.MockTransport(handler))


@pytest.mark.parametrize('status,total', [(429, 3), (500, 3), (401, 1)])
def test_sdk_retry_policy_without_outer_retry(config, tmp_path, status, total):
    calls = []
    def handler(req):
        calls.append(json.loads(req.content))
        return httpx.Response(status, json={'error': {'message': 'offline'}})
    backend = transport(config, tmp_path, handler)
    with patch('time.sleep'), pytest.raises(Exception):
        backend.generate(request(config))
    assert len(calls) == total
    assert all(body == calls[0] for body in calls)
    assert len(list(tmp_path.glob('model_calls/*/http_request_*.json'))) == total


def test_sdk_recovers_429_and_preserves_model_parameters(config, tmp_path):
    calls = []
    def handler(req):
        calls.append(json.loads(req.content))
        return httpx.Response(429, json={'error': {'message': 'offline'}}) if len(calls) == 1 else httpx.Response(200, json=response())
    backend = transport(config, tmp_path, handler)
    with patch('time.sleep'):
        assert backend.generate(request(config)).text == 'summary'
    assert len(calls) == 2
    body = calls[-1]
    assert body['max_tokens'] == 16384 and body['model'] == config[1]['actor_model']
    assert body['temperature'] == 1 and body['reasoning_effort'] == 'medium'
    assert body['thinking'] == config[1]['call_config']['thinking'] and body['stream'] is False


@pytest.mark.parametrize('raw,raises', [
    (response('unfinished', 'length'), False),
    (response('not valid patch JSON'), False),
    (response(''), True),
    (response(None, 'tool_calls', [{'id': 'x', 'type': 'function',
       'function': {'name': 'record_attempt', 'arguments': '{bad json'}}]), True),
])
def test_native_parsing_without_added_repair_or_resampling(config, tmp_path, raw, raises):
    calls = []
    def handler(req):
        calls.append(req)
        return httpx.Response(200, json=raw)
    backend = transport(config, tmp_path, handler)
    if raises:
        with pytest.raises(Exception):
            backend.generate(request(config))
    else:
        assert backend.generate(request(config)).text == raw['choices'][0]['message']['content']
    assert len(calls) == 1


def test_actor_bridge_delegates_once_even_on_optimizer_failure(config, tmp_path):
    bridge, shared, cfg = config
    calls = []
    def generate(req):
        calls.append(req)
        raise ValueError('native failure')
    backend = app.backend_type(bridge)(shared, cfg, tmp_path, optimizer=SimpleNamespace(generate=generate))
    with pytest.raises(ValueError, match='native failure'):
        backend.generate(request(config))
    assert len(calls) == 1


def test_native_patch_loop_keeps_three_attempts_and_application_feedback(config):
    from skilladam.core.feedback_loop import FeedbackLoop
    bridge, shared, cfg = config
    contexts = []
    def propose(context):
        contexts.append(context)
        if len(contexts) < 3:
            return 'this is not an applicable diff'
        return '--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-Original\n+Updated\n'
    loop = SimpleNamespace(config=bridge.native_config(cfg).feedback_loop)
    batch = SimpleNamespace(training_case_ids=('task',))
    report, count, error = FeedbackLoop._generate_candidate(loop, iteration=0,
        current_skill='Original\n', batch=batch, edit_budget=4, propose_patch=propose)
    assert count == 3 and not error and not report.all_failed
    assert contexts[0].previous_patch_error == ''
    assert contexts[1].previous_patch_error and contexts[2].previous_patch_error


@pytest.mark.parametrize('limit', ['max_input_chars', 'max_message_utf8_bytes'])
def test_original_input_capacity_still_rejects_before_http(config, tmp_path, limit):
    bridge, shared, cfg = config
    shared = deepcopy(shared)
    shared[limit] = 1
    calls = []
    def handler(req):
        calls.append(req)
        return httpx.Response(200, json=response())
    backend = transport((bridge, shared, cfg), tmp_path, handler)
    with pytest.raises(Exception):
        backend.generate(request(config))
    assert calls == []
    assert not (tmp_path / 'model_calls').exists()


