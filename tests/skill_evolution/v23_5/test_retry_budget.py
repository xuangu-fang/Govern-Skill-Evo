"""Five retries means six total requests; resume must not reset the limit."""
import pytest
import requests
from unittest.mock import Mock

from src.skill_evolution.v23_5 import evolution as ev
from src.adapters.alfworld.run_task_upstream import chat
from .test_baseline import config
from .test_feedback_retry import Scripted, run


def six_attempt_config():
    cfg = config(1)
    cfg.update(max_attempts=6, actor_request_attempts=6,
               module_max_tokens={'preconditioner': 32768, 'replay': 32768})
    return cfg


@pytest.mark.parametrize('stage', list(ev.MODULES))
def test_five_failures_then_sixth_request_succeeds(tmp_path, stage):
    cfg = six_attempt_config()
    h = Scripted(stage, ['json'] * 5 + ['valid'])
    assert run(tmp_path, h, config=cfg)['status'] == 'complete'
    assert h.calls.count(stage) == 6
    paths = list((tmp_path/'rounds/R01'/stage/'attempts').glob('*/run.json'))
    assert len(paths) == 6
    assert all(ev.read(p)['call_config'] == ev.stage_call_config(cfg, stage) for p in paths)
    before = len(h.calls), len(h.actor_calls)
    run(tmp_path, h, resume=True)
    assert before == (len(h.calls), len(h.actor_calls))


@pytest.mark.parametrize('stage', ['preconditioner', 'replay'])
def test_six_failures_exhaust_budget_across_resume(tmp_path, stage):
    h = Scripted(stage, ['length'] * 6)
    with pytest.raises(ev.Stopped, match='exhausted'): run(tmp_path, h, config=six_attempt_config())
    assert h.calls.count(stage) == 6
    with pytest.raises(ev.Stopped, match='exhausted'): run(tmp_path, h, resume=True)
    assert h.calls.count(stage) == 6


@pytest.mark.parametrize('failure', ['503', 'timeout'])
def test_actor_stops_after_six_requests(monkeypatch, failure):
    monkeypatch.setattr('src.adapters.alfworld.run_task_upstream.time.sleep', lambda _: None)
    session = Mock()
    if failure == 'timeout': session.post.side_effect = requests.Timeout('offline')
    else:
        response = requests.Response(); response.status_code = 503; response._content = b'{}'
        session.post.return_value = response
    with pytest.raises((RuntimeError, requests.Timeout)):
        chat(session, 'https://offline.invalid/chat/completions', 'unused', 'offline', [],
             max_attempts=6, strict_response=True)
    assert session.post.call_count == 6


@pytest.mark.parametrize('field', ['max_attempts', 'actor_request_attempts'])
@pytest.mark.parametrize('value', [0, 7, True, '6'])
def test_invalid_budget_rejected(field, value):
    cfg = six_attempt_config(); cfg[field] = value
    with pytest.raises(ValueError): ev.validate_config(cfg)
