"""General v24.9 protects Pick Two while retaining edits outside principle 2."""
import json

import pytest

from scripts.runs.v24_2.run_v24_2_test import published_skill
from src.skill_evolution.v24_2.storage import read
from src.skill_evolution.v24_9 import campaign as specialized
from src.skill_evolution.v24_9.general import campaign, pick_two, system_prompt
from tests.skill_evolution.v24_2 import fixture


@pytest.mark.parametrize('prefix', pick_two.PREFIXES)
def test_protected_text(prefix):
    parent = campaign.configuration()['initial_skill']['text']
    original = next(line for line in parent.splitlines() if line.startswith(prefix))
    with pytest.raises(ValueError, match='Preserve the original Pick Two rule'):
        pick_two.check_scope(parent, parent.replace(original, original + ' Except when searching.'))


def test_general_round_and_resume(tmp_path, monkeypatch):
    config = dict(fixture.fixture_config(), method=campaign.VERSION)
    assert campaign.gate is specialized.gate
    initial = campaign.prepare(tmp_path, config)
    assert initial['selected'] == config['initial_skill']['text']
    assert initial['memory'] == {'rounds': []}
    monkeypatch.setattr(fixture, 'DESTINATION', 'Prefer the next numbered location after a miss.')

    def generate(name, messages, slot, call):
        assert messages[0]['content'] == system_prompt(name)
        reply = fixture.generate(name, messages, slot, call)
        value = json.loads(reply['content'])
        if name == 'editor' and slot.name == '002':
            assert 'Preserve the original Pick Two rule' in messages[-1]['content']
            line = next(s for s in initial['selected'].splitlines() if s.startswith('7. **Avoid loops'))
            value['edits'][1]['patch'] = (
                f'--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-{line}\n+{line} {fixture.DESTINATION}\n')
        if name == 'replay':
            for pair, event in zip(json.loads(messages[1]['content'])['pairs'], value['entries'][0]['knowledge']):
                event['text'] = f"{pair['parent']}:1 and {pair['candidate']}:1. " + event['text']
        reply['content'] = json.dumps(value)
        return reply

    result = campaign.run_round(tmp_path, generate=generate, actor=fixture.actor)
    assert read(tmp_path / 'rounds/R01/editor/result.json')['attempt'] == 2
    assert read(tmp_path / 'rounds/R01/gate.json')['selection']['selected_update_ids'] == ['u2']
    selected = published_skill(tmp_path, config, campaign)[1]
    assert selected == result['selected'] == (tmp_path / 'final_skill.md').read_text()
    assert fixture.DESTINATION in selected
    pick_two.check_scope(initial['selected'], selected)
    assert campaign.run_round(tmp_path) == result
    with pytest.raises(ValueError):
        specialized.run_round(tmp_path)
