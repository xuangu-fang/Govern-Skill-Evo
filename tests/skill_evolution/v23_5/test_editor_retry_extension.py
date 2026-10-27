"""Authorized extra attempts are local, bounded, and preserve prior feedback."""
import hashlib

import pytest

from src.skill_evolution.v23_5 import evolution as ev, editor_retry
from .test_feedback_retry import Scripted, run
from .test_retry_budget import six_attempt_config


def exhaust(root, actions):
    h = Scripted('editor', actions)
    with pytest.raises(ev.Stopped, match='exhausted'):
        run(root, h, config=six_attempt_config())
    assert h.calls.count('editor') == 6
    return h


def test_extension_continues_feedback_without_repeating_completed_stages(tmp_path):
    h = exhaust(tmp_path, ['json'] * 6 + ['valid'])
    before_calls = len(h.calls); before_actors = len(h.actor_calls)
    original = (tmp_path/'contract.json').read_bytes(), (tmp_path/'config.json').read_bytes()
    info = editor_retry.enable(tmp_path, round_number=1, reason='Explicit test authorization')
    assert editor_retry.request_limit(tmp_path, tmp_path/'rounds/R01', 'editor', 6) == 12
    assert editor_retry.request_limit(tmp_path, tmp_path/'rounds/R02', 'editor', 6) == 6
    assert editor_retry.request_limit(tmp_path, tmp_path/'rounds/R01', 'replay', 6) == 6
    result = run(tmp_path, h, resume=True)
    assert result['status'] == 'complete'
    assert h.calls[before_calls:] == ['editor', 'replay']
    assert len(h.actor_calls) == before_actors + 2  # New Candidate only.
    stage = tmp_path/'rounds/R01/editor'
    assert ev.read(stage/'result.json')['path'] == 'attempts/007'
    context = ev.read(stage/'attempts/007/request_context.json')
    assert context['feedback_from'] == str((stage/'attempts/006').resolve())
    assert ev.read(stage/'attempts/006/messages.json')[:2] == ev.read(stage/'attempts/007/messages.json')[:2]
    assert all(hashlib.sha256((tmp_path/p).read_bytes()).hexdigest() == sha
               for p, sha in info['preserved_attempt_files'].items())
    assert original == ((tmp_path/'contract.json').read_bytes(), (tmp_path/'config.json').read_bytes())
    calls = len(h.calls), len(h.actor_calls)
    run(tmp_path, h, resume=True)
    assert calls == (len(h.calls), len(h.actor_calls))


def test_extension_stops_at_twelve_and_never_resets(tmp_path):
    h = exhaust(tmp_path, ['json'] * 12)
    info = editor_retry.enable(tmp_path, round_number=1, reason='Explicit test authorization')
    assert editor_retry.enable(tmp_path, round_number=1, reason='Same request') == info
    for _ in range(2):
        with pytest.raises(ev.Stopped, match='exhausted'): run(tmp_path, h, resume=True)
        assert h.calls.count('editor') == 12
    assert not (tmp_path/'rounds/R01/editor/attempts/013').exists()


def test_grant_tampering_and_unapproved_source_rejected(tmp_path, monkeypatch):
    exhaust(tmp_path, ['json'] * 6)
    current = ev.frozen_contract(); changed = dict(current)
    changed['src/skill_evolution/v23_5/editor_prompt.md'] += '\nunauthorized'
    monkeypatch.setattr(ev, 'frozen_contract', lambda: changed)
    with pytest.raises(ValueError, match='Unrelated'):
        editor_retry.enable(tmp_path, round_number=1, reason='Explicit test authorization')
    monkeypatch.setattr(ev, 'frozen_contract', lambda: current)
    editor_retry.enable(tmp_path, round_number=1, reason='Explicit test authorization')
    ev._check_contract(tmp_path)
    path = tmp_path/editor_retry.DIRECTORY/'grant.json'
    grant = ev.read(path); grant['round'] = 'R02'; ev.save(path, grant)
    with pytest.raises(ValueError, match='grant changed'): ev._check_contract(tmp_path)


def test_wrong_round_cannot_receive_extension(tmp_path):
    exhaust(tmp_path, ['json'] * 6)
    with pytest.raises(ValueError, match='stopped Editor round'):
        editor_retry.enable(tmp_path, round_number=2, reason='Explicit test authorization')
