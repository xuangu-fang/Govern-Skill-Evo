"""Replay publication without online Knowledge review, including recovery."""
import json
from copy import deepcopy

import pytest

from src.skill_evolution.v24 import evolution as ev, config
from .test_review_paths import migrated
from .test_equivalence import CapturedHarness


def no_review(rounds=2):
    value = migrated(rounds)
    value['method'] = config.method_config(config.REVIEW_DISABLED)
    value['actor_max_workers'] = 10
    for name in ('verifier', 'repair'):
        value['module_max_tokens'].pop(name, None)
    return value


@pytest.mark.parametrize('outcome', ['ACCEPT', 'RETAIN'])
@pytest.mark.parametrize('interrupted', [False, True])
def test_replay_publishes_without_review_and_resumes(tmp_path, monkeypatch, outcome, interrupted):
    value = no_review()
    h = CapturedHarness('replace', outcome)
    def forbidden(*args, **kwargs):
        raise AssertionError('Verifier/Repair must not execute')
    monkeypatch.setattr(ev.knowledge_review, 'review', forbidden)
    monkeypatch.setattr(ev.knowledge_review, 'run_model', forbidden)
    if interrupted:
        def stop(stage):
            if stage == 'before_publish':
                raise KeyboardInterrupt()
        with pytest.raises(KeyboardInterrupt):
            ev.run_campaign(tmp_path, config=value, generate=h.generate, actor_runner=h.actor, hook=stop)
        ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    else:
        ev.run_campaign(tmp_path, config=value, generate=h.generate, actor_runner=h.actor)
    assert h.calls == ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'] * 2
    for number in (1, 2):
        rd = tmp_path/'rounds'/f'R{number:02}'
        assert not (rd/'verifier').exists() and not (rd/'repair').exists()
        candidate = ev.read(rd/'replay/attempts/001/replay.json')
        committed = ev.read(rd/'memory/archive'/f'{tmp_path.name}_R{number:02}.json')
        assert committed['result'] == candidate
        assert ev.read(rd/'knowledge_review/result.json')['status'] == 'disabled'
    before = deepcopy(h.calls), deepcopy(h.actor_calls)
    ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    ev.final_parent(tmp_path)
    assert before == (h.calls, h.actor_calls)
    # A structurally valid but edited Memory must still be rejected on reload.
    archive = tmp_path/'rounds/R02/memory/archive'/f'{tmp_path.name}_R02.json'
    saved = ev.read(archive)
    saved['result']['entries'][0]['knowledge'][0]['text'] = 'Unpublished replacement'
    ev.save(archive, saved)
    with pytest.raises(ValueError):
        ev.final_parent(tmp_path)


def test_invalid_replay_citation_cannot_publish_without_verifier(tmp_path):
    value = no_review(1)
    value.update(max_attempts=2, retry_delay_seconds=0)
    h = CapturedHarness()
    def generate(messages, dest):
        response = h.generate(messages, dest)
        if 'replay' in dest.parts:
            output = json.loads(response['content'])
            output['entries'][0]['knowledge'][0]['evidence'] = ['Q999:outcome']
            response['content'] = json.dumps(output)
        return response
    with pytest.raises(ev.Stopped, match='exhausted'):
        ev.run_campaign(tmp_path, config=value, generate=generate, actor_runner=h.actor)
    assert not (tmp_path/'rounds/R01/memory').exists()
    assert ev.read(tmp_path/'state.json')['next_round'] == 1
    assert h.calls.count('replay') == 2
    assert 'verifier' not in h.calls and 'repair' not in h.calls


def test_disabled_review_has_no_review_stage_budget():
    value = no_review()
    ev.validate_config(value)
    assert set(ev.enabled_modules(value)) == {'grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'}
    value['module_max_tokens']['verifier'] = 32768
    with pytest.raises(ValueError, match='Unknown module output budget'):
        ev.validate_config(value)
