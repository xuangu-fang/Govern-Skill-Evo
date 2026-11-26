"""Offline safety checks for scheduled execution and bounded recovery."""
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import httpx
import pytest

ENTRY = Path(__file__).resolve().parent
HOME = ENTRY.parents[5] / 'experiments/comparisons' / ENTRY.parent.name / 'scheduled_run'
from src.skill_evolution.skilladam.spreadsheetbench.layout import UPSTREAM, UPSTREAM_CONFIG
from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.scheduled.bridge import spreadsheetbench_native_optimizer as native

sys.path[:0] = [str(ENTRY), str(UPSTREAM), str(HOME.parent)]
import worker
import control
from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.scheduled.actor_runtime.scheduled_recovery import limit
from src.skill_evolution.skilladam.spreadsheetbench.upstream_actor.scheduled.actor_runtime.benchmarks.spreadsheetbench import actor, protocol, transport
from regression_cases.test_execution_history import setup, good
from regression_cases.support import PARENT, fast_execute


def test_launch_before_deadline_makes_no_process():
    with patch.object(control.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
        with patch.object(control, 'read', return_value={'not_before': '2099-01-01T00:00:00+00:00'}):
            assert control.launch('v25', 'train', False)['status'] == 'waiting'


def test_test_requires_both_complete_trainings(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, 'folder_for', lambda side: tmp_path / side)
    with pytest.raises(FileNotFoundError): worker.completed_training()


def test_actor_extra_three_is_persisted_and_does_not_reset(tmp_path):
    cfg, task = setup(tmp_path)
    count = []
    def fail(*args):
        count.append(1); raise transport.RequestError('offline network failure')
    run = tmp_path / 'run'
    def invoke(): return actor.run(task, PARENT, run, cfg, generate=fail, execute=fast_execute)
    for _ in range(2):
        with pytest.raises(actor.GenerationExhausted): invoke()
    base = cfg['actor_profile']['request_attempts_total']
    assert len(count) == base
    worker.save(run / 'recovery_slot_001.json', {'schema': 'scheduled_extra3_v1', 'target': str(run.resolve()),
        'base_limit': base, 'extra': 3, 'slot': 1})
    for _ in range(2):
        with pytest.raises(actor.GenerationExhausted): invoke()
    assert len(count) == base + 3
    state = worker.read(run / 'actor_state.json')
    assert state['protocol'] == cfg['actor_profile']
    assert len(state['requests']) == base + 3 and not state['actor_complete']


def test_grant_limit_is_specific_and_cannot_expand(tmp_path):
    assert limit(tmp_path, 6) == 6
    grant = {'schema': 'scheduled_extra3_v1', 'target': str(tmp_path.resolve()), 'base_limit': 6, 'extra': 3, 'slot': None}
    worker.save(tmp_path / 'recovery_extra3.json', grant)
    assert limit(tmp_path, 6) == 9 and limit(tmp_path, 6, 1) == 6
    grant['extra'] = 4; worker.save(tmp_path / 'recovery_extra3.json', grant)
    with pytest.raises(ValueError): limit(tmp_path, 6)


def test_actor_can_succeed_in_extra_allowance(tmp_path):
    cfg, task = setup(tmp_path); run = tmp_path / 'run'; count = []
    def fail(*args): count.append(1); raise transport.RequestError('offline')
    with pytest.raises(actor.GenerationExhausted): actor.run(task, PARENT, run, cfg, generate=fail)
    base = cfg['actor_profile']['request_attempts_total']
    worker.save(run / 'recovery_slot_001.json', {'schema': 'scheduled_extra3_v1', 'target': str(run.resolve()),
        'base_limit': base, 'extra': 3, 'slot': 1})
    def ok(*args): count.append(1); return good()
    result = worker.read(actor.run(task, PARENT, run, cfg, generate=ok, execute=fast_execute))
    assert result['status'] == 'completed' and result['score']['hard'] == 1
    assert len(count) == base + 1


def test_v25_stage_extra_three_survives_repeated_resume(tmp_path):
    from src.skill_evolution.v25.revisions.upstream_actor_scheduled import evolution as ev, feedback_retry
    cfg = worker.read(worker.PUBLISHED / 'config.json')
    cfg['retry_delay_seconds'] = 0
    rd = tmp_path / 'round'; rd.mkdir()
    calls = []
    def fail(messages, path):
        calls.append(messages); raise feedback_retry.RequestFailure('offline network failure')
    def invoke(path, generator, call_cfg):
        path.mkdir(parents=True, exist_ok=True)
        messages = [{'role': 'system', 'content': 'unchanged'}, {'role': 'user', 'content': 'unchanged'}]
        worker.save(path / 'messages.json', messages)
        worker.save(path / 'request_context.json', generator.request_context)
        return generator(messages, path)
    with patch.object(ev, '_check_contract'):
        for resume in (False, True):
            with pytest.raises(ev.Stopped, match='budget exhausted'):
                feedback_retry.run_stage(tmp_path, rd, 'grouping', invoke, cfg, fail, resume)
        base = cfg['max_attempts']
        assert len(calls) == base
        worker.save(rd / 'grouping/recovery_extra3.json', {'schema': 'scheduled_extra3_v1',
            'target': str((rd / 'grouping').resolve()), 'base_limit': base, 'extra': 3, 'slot': None})
        for _ in range(2):
            with pytest.raises(ev.Stopped, match='budget exhausted'):
                feedback_retry.run_stage(tmp_path, rd, 'grouping', invoke, cfg, fail, True)
        assert len(calls) == base + 3
        assert all(messages == calls[0] for messages in calls)


def test_momentum_extra_three_has_no_nested_sdk_retries(tmp_path):
    bridge = native.load_bridge(UPSTREAM_CONFIG)
    shared = worker.read(UPSTREAM_CONFIG / 'shared_config.json'); cfg = worker.read(UPSTREAM_CONFIG / 'skilladam.json')
    from skilladam.execution.contracts import GenerationRequest
    req = GenerationRequest('momentum_update', ({'role': 'user', 'content': 'offline'},), bridge.context_for(shared, cfg), {'tools': [{'type': 'function', 'function': {'name': 'record_attempt', 'description': 'offline', 'parameters': {'type': 'object', 'properties': {}}}}]})
    sent = []
    def handler(request):
        sent.append(request)
        assert str(request.url) == 'https://api.deepseek.com/chat/completions'
        return httpx.Response(500, json={'error': {'message': 'offline'}})
    original = native.native_transport
    def offline(*args, **kwargs): return original(*args, **kwargs, http_transport=httpx.MockTransport(handler))
    with patch.object(native, 'native_transport', side_effect=offline), patch('time.sleep'):
        backend = worker.native_backend(native, bridge, shared, cfg, tmp_path, 'offline-key')
        with pytest.raises(Exception): backend.generate(req)
        assert len(sent) == 3
        directory = next((tmp_path / 'logical_calls').iterdir())
        worker.save(directory / 'grant.json', {'schema': 'momentum_extra3_v1',
            'request_sha256': worker.digest(worker.read(directory / 'request.json')), 'extra': 3})
        for _ in range(2):
            resumed = worker.native_backend(native, bridge, shared, cfg, tmp_path, 'offline-key')
            with pytest.raises(ValueError, match='extra-three'): resumed.generate(req)
        assert len(sent) == 6
        assert len(list(directory.glob('extra_*.json'))) == 3


def test_successful_optimizer_call_replays_without_http(tmp_path):
    bridge = native.load_bridge(UPSTREAM_CONFIG)
    shared = worker.read(UPSTREAM_CONFIG / 'shared_config.json'); cfg = worker.read(UPSTREAM_CONFIG / 'skilladam.json')
    from skilladam.execution.contracts import GenerationRequest
    req = GenerationRequest('trajectory_compression', ({'role': 'user', 'content': 'offline'},), bridge.context_for(shared, cfg), {})
    sent = []
    def handler(request):
        sent.append(request)
        return httpx.Response(200, json={'id':'offline','object':'chat.completion','created':0,'model':'deepseek-flash',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':'summary'}}]})
    original = native.native_transport
    def offline(*args, **kwargs): return original(*args, **kwargs, http_transport=httpx.MockTransport(handler))
    with patch.object(native, 'native_transport', side_effect=offline):
        first = worker.native_backend(native, bridge, shared, cfg, tmp_path, 'offline-key').generate(req)
        second = worker.native_backend(native, bridge, shared, cfg, tmp_path, 'offline-key').generate(req)
    assert first == second and len(sent) == 1
