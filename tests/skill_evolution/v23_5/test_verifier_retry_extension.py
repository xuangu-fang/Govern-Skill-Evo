"""Recovery preserves evidence, changes only the granted call, and stays bounded."""
import hashlib

import pytest

from src.skill_evolution.v23_5 import evolution as ev, verifier_retry
from .test_unified_retry import Scripted, run, config


def exhaust(root, actions):
    h = Scripted('verifier', actions)
    with pytest.raises(ev.Stopped, match='exhausted'):
        run(root, h)
    return h


def test_resume_finishes_review_without_repeating_actors_or_replay(tmp_path):
    h = exhaust(tmp_path, ['length'] * 6 + ['valid'])
    before_calls, before_actors = len(h.calls), len(h.actor_calls)
    original = [(tmp_path/n).read_bytes() for n in ('config.json', 'initial_config.json', 'contract.json')]
    info = verifier_retry.enable(tmp_path, round_number=1, reason='User requested double output budget')
    assert verifier_retry.enable(tmp_path, round_number=1, reason='Same authorization') == info
    assert run(tmp_path, h, resume=True)['status'] == 'complete'
    assert h.calls[before_calls:] == ['verifier', 'repair']
    assert len(h.actor_calls) == before_actors
    stage = tmp_path/'rounds/R01/verifier'
    assert ev.read(stage/'result.json')['path'] == 'attempts/007'
    cfg = ev.read(stage/'attempts/007/run.json')['call_config']
    assert cfg['max_tokens'] == 65536 and cfg['timeout_seconds'] == 600
    assert h.requests[0] == h.requests[-1]
    assert all(hashlib.sha256((tmp_path/p).read_bytes()).hexdigest() == sha
               for p, sha in info['preserved_files'].items())
    assert original == [(tmp_path/n).read_bytes() for n in ('config.json', 'initial_config.json', 'contract.json')]
    base = ev.stage_call_config(config(), 'verifier')
    assert verifier_retry.call_config(tmp_path, tmp_path/'rounds/R02', 'verifier', base) == base
    assert verifier_retry.call_config(tmp_path, tmp_path/'rounds/R01', 'repair', base) == base
    assert verifier_retry.call_config(tmp_path, tmp_path/'rounds/R01', 'verifier', base, stage/'attempts/001') == base
    ev.final_parent(tmp_path)  # Final audit reloads the amended call configuration.
    before = len(h.calls), len(h.actor_calls)
    run(tmp_path, h, resume=True)
    assert before == (len(h.calls), len(h.actor_calls))


def test_extra_budget_never_resets_and_tampering_is_rejected(tmp_path):
    h = exhaust(tmp_path, ['length'] * 12)
    verifier_retry.enable(tmp_path, round_number=1, reason='Explicit recovery')
    for _ in range(2):
        with pytest.raises(ev.Stopped, match='exhausted'):
            run(tmp_path, h, resume=True)
        assert h.calls.count('verifier') == 12
    assert not (tmp_path/'rounds/R01/verifier/attempts/013').exists()
    path = tmp_path/verifier_retry.DIRECTORY/'grant.json'
    grant = ev.read(path); grant['round'] = 'R02'; ev.save(path, grant)
    with pytest.raises(ValueError, match='grant changed'):
        ev._check_contract(tmp_path)


def test_wrong_round_and_unrelated_changes_are_rejected(tmp_path, monkeypatch):
    exhaust(tmp_path, ['length'] * 6)
    with pytest.raises(ValueError, match='stopped Verifier round'):
        verifier_retry.enable(tmp_path, round_number=2, reason='Explicit recovery')
    changed = ev.frozen_contract()
    changed['src/skill_evolution/v23_5/knowledge_verifier_prompt.md'] += '\nchanged'
    monkeypatch.setattr(ev, 'frozen_contract', lambda: changed)
    with pytest.raises(ValueError, match='Unrelated'):
        verifier_retry.enable(tmp_path, round_number=1, reason='Explicit recovery')
