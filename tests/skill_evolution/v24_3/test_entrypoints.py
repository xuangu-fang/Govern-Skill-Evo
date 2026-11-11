import pytest

from scripts.runs.v24_2.run_v24_2_test import prepare_test
from src.skill_evolution.v24_2 import campaign as old, system_prompt as old_prompt
from src.skill_evolution.v24_3 import campaign, system_prompt
from tests.skill_evolution.v24_2.fixture import actor, fixture_config, generate


def test_offline_round_routes_only_new_prompts(tmp_path):
    cfg = dict(fixture_config(), method=campaign.VERSION)
    campaign.prepare(tmp_path, cfg)
    def recorded(name, messages, *args):
        assert messages[0]['content'] == system_prompt(name)
        assert (messages[0]['content'] != old_prompt(name)) == (name in ('diagnosis', 'preconditioner'))
        return generate(name, messages, *args)
    state = campaign.run_round(tmp_path, generate=recorded, actor=actor)
    assert state['next_round'] == 2
    assert (tmp_path / 'final_skill.md').read_text() == state['selected']
    with pytest.raises(ValueError, match='Wrong method version'):
        old.run_round(tmp_path)
    with pytest.raises(ValueError, match='official'):
        prepare_test(tmp_path, campaign.ALFWorldAdapter(), version=campaign)


def test_test_entry_binds_correct_contract(tmp_path):
    campaign.prepare(tmp_path)
    with pytest.raises(ValueError, match='incomplete'):
        prepare_test(tmp_path, campaign.ALFWorldAdapter(), version=campaign)
    with pytest.raises(ValueError, match='Wrong method version'):
        prepare_test(tmp_path, campaign.ALFWorldAdapter())
    old_dir = tmp_path / 'old-campaign'
    old.prepare(old_dir)
    with pytest.raises(ValueError, match='Expected V24.3 method'):
        prepare_test(old_dir, campaign.ALFWorldAdapter(), version=campaign)
