"""Fixed initial Skill, repeated epochs and restart integrity."""
import hashlib
import pytest

from src.skill_evolution.v23_5 import evolution as ev
from .test_baseline import Harness, config


def configured():
    cfg = config(2)
    cfg['batches'][1] = list(reversed(cfg['batches'][0]))
    cfg['epoch_schedule'] = {'epochs': 2, 'round_epochs': [1, 2], 'batch_size': 40, 'seed': 42}
    text = '# Initial Skill\nInspect visible objects.\n'
    cfg['initial_skill'] = {'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest()}
    return cfg


@pytest.mark.parametrize('outcome', ['ACCEPT', 'RETAIN', 'no_change'])
def test_initial_and_repeated_tasks_survive_complete_and_resume(tmp_path, outcome):
    cfg = configured()
    h = Harness(outcome)
    if outcome == 'no_change':
        h.stop = 'diagnosis_no_change'
    ev.run_campaign(tmp_path, config=cfg, generate=h.generate, actor_runner=h.actor)
    assert ev.read(tmp_path/'rounds/R01/round_input.json')['parent'] == cfg['initial_skill']['text']
    assert len(h.actor_calls) == (4 if outcome == 'no_change' else 8)
    final = ev.final_parent(tmp_path)
    assert final.read_text().startswith(cfg['initial_skill']['text'])
    if outcome != 'ACCEPT':
        assert final == tmp_path/'initial_skill.md'
    before = len(h.actor_calls), len(h.calls)
    ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert before == (len(h.actor_calls), len(h.calls))


@pytest.mark.parametrize('corruption', ['duplicate', 'missing', 'mapping', 'implicit', 'hash', 'empty'])
def test_invalid_config_rejected_before_initialization(tmp_path, corruption):
    cfg = configured()
    if corruption == 'duplicate': cfg['batches'][1].append(cfg['batches'][1][0])
    if corruption == 'missing': cfg['batches'][1].pop()
    if corruption == 'mapping': cfg['epoch_schedule']['round_epochs'] = [2, 1]
    if corruption == 'implicit': del cfg['epoch_schedule']
    if corruption == 'hash': cfg['initial_skill']['sha256'] = 'wrong'
    if corruption == 'empty': cfg['initial_skill']['text'] = ''
    with pytest.raises(ValueError): ev.initialize(tmp_path, cfg)
    assert not (tmp_path/'state.json').exists()


@pytest.mark.parametrize('remove', [False, True])
def test_frozen_initial_skill_tampering_rejected_before_calls(tmp_path, remove):
    cfg = configured(); ev.initialize(tmp_path, cfg)
    path = tmp_path/'initial_skill.md'
    if remove: path.unlink()
    else: path.write_text('changed')
    h = Harness()
    with pytest.raises(ValueError, match='initial Skill'):
        ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert not h.calls and not h.actor_calls


def test_interrupt_before_publish_resumes_same_initial_parent(tmp_path):
    h = Harness('RETAIN')
    def crash(point):
        if point == 'before_publish': raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        ev.run_campaign(tmp_path, config=configured(), generate=h.generate, actor_runner=h.actor, hook=crash)
    before = len(h.actor_calls)
    ev.run_campaign(tmp_path, resume=True, generate=h.generate, actor_runner=h.actor)
    assert len(h.actor_calls) == before + 4
    assert ev.final_parent(tmp_path) == tmp_path/'initial_skill.md'
