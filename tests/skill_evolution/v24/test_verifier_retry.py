"""Authorized extra requests preserve prior evidence and remain round-local."""
from copy import deepcopy
import hashlib

import pytest

from src.skill_evolution.v24 import evolution as ev, verifier_retry
from tests.skill_evolution.v23_5.test_unified_retry import Scripted
from .test_review_paths import migrated


@pytest.mark.parametrize('last', ['valid', 'length'])
def test_three_extra_requests_are_persistent_and_scoped(tmp_path, last):
    h = Scripted('verifier', ['length'] * 8 + [last])
    cfg = migrated()
    cfg.update(max_attempts=6, retry_delay_seconds=0)
    with pytest.raises(ev.Stopped, match='exhausted'):
        ev.run_campaign(tmp_path, config=cfg, generate=h.generate, actor_runner=h.actor)
    assert len(h.requests) == 6
    actors = deepcopy(h.actor_calls)
    round_dir = tmp_path/'rounds/R01'
    prior = {p: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in (round_dir/'verifier/attempts').rglob('*') if p.is_file()}
    info = verifier_retry.enable(tmp_path, round_number=1, reason='Offline test: three additional requests')
    assert verifier_retry.enable(tmp_path, round_number=1, reason='Same allowance') == info
    assert verifier_retry.request_limit(tmp_path, round_dir, 'verifier', 6) == 9
    assert verifier_retry.request_limit(tmp_path, tmp_path/'rounds/R02', 'verifier', 6) == 6
    assert verifier_retry.request_limit(tmp_path, round_dir, 'repair', 6) == 6
    if last == 'valid':
        assert ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)['status'] == 'complete'
        ev.final_parent(tmp_path)
        ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    else:
        for _ in range(2):
            with pytest.raises(ev.Stopped, match='exhausted'):
                ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert len(h.requests) == 9 and h.actor_calls == actors
    assert all(messages == h.requests[0] for messages in h.requests)
    assert prior == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in prior}
    assert ev.read(tmp_path/'config.json') == ev.read(tmp_path/'initial_config.json') == cfg
    for a in (round_dir/'verifier/attempts').iterdir():
        assert ev.read(a/'run.json')['call_config'] == ev.stage_call_config(cfg, 'verifier')
    grant_path = tmp_path/verifier_retry.DIRECTORY/'grant.json'
    grant = ev.read(grant_path)
    grant['total_limit'] = 12
    ev.save(grant_path, grant)
    with pytest.raises(ValueError, match='grant changed'):
        ev._check_contract(tmp_path)


def test_extension_rejects_unrelated_source_change(tmp_path, monkeypatch):
    h = Scripted('verifier', ['length'] * 6)
    cfg = migrated()
    cfg.update(max_attempts=6, retry_delay_seconds=0)
    with pytest.raises(ev.Stopped, match='exhausted'):
        ev.run_campaign(tmp_path, config=cfg, generate=h.generate, actor_runner=h.actor)
    current = ev.frozen_contract()
    current['unexpected_prompt.md'] = 'changed'
    monkeypatch.setattr(ev, 'frozen_contract', lambda: current)
    with pytest.raises(ValueError, match='Unrelated'):
        verifier_retry.enable(tmp_path, round_number=1, reason='Offline test')
    assert not (tmp_path/verifier_retry.DIRECTORY).exists()


@pytest.mark.parametrize('last', ['valid', 'length'])
def test_later_round_grant_preserves_first_grant_and_request_limits(tmp_path, last):
    h = Scripted('verifier', ['length'] * 6 + ['valid', 'valid'] + ['length'] * 8 + [last])
    cfg = migrated(3)
    cfg.update(max_attempts=6, retry_delay_seconds=0)
    with pytest.raises(ev.Stopped, match='exhausted'):
        ev.run_campaign(tmp_path, config=cfg, generate=h.generate, actor_runner=h.actor)
    verifier_retry.enable(tmp_path, round_number=1, reason='First round authorization')
    original_grant = {p: p.read_bytes() for p in (tmp_path/verifier_retry.DIRECTORY).iterdir()}
    with pytest.raises(ev.Stopped, match='exhausted'):
        ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert ev.read(tmp_path/'state.json')['next_round'] == 3
    assert len(h.requests) == 14  # R01: seven, R02: one, R03: six.
    actors = deepcopy(h.actor_calls)
    stage = tmp_path/'rounds/R03/verifier'
    prior = {p: p.read_bytes() for p in stage.rglob('*') if p.is_file()}
    info = verifier_retry.enable(tmp_path, round_number=3, reason='Third round authorization')
    assert verifier_retry.enable(tmp_path, round_number=3, reason='Same allowance') == info
    for number, limit in [(1, 9), (2, 6), (3, 9), (4, 6)]:
        rd = tmp_path/'rounds'/f'R{number:02}'
        assert verifier_retry.request_limit(tmp_path, rd, 'verifier', 6) == limit
        assert verifier_retry.request_limit(tmp_path, rd, 'repair', 6) == 6
    if last == 'valid':
        assert ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)['status'] == 'complete'
        ev.final_parent(tmp_path)
    else:
        for _ in range(2):
            with pytest.raises(ev.Stopped, match='exhausted'):
                ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert len(h.requests) == 17 and h.actor_calls == actors
    assert original_grant == {p: p.read_bytes() for p in original_grant}
    assert prior == {p: p.read_bytes() for p in prior}
    assert ev.read(tmp_path/'config.json') == ev.read(tmp_path/'initial_config.json') == cfg
