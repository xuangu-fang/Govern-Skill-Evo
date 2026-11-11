import json

import pytest

from scripts.runs.v24_2.run_v24_2_test import published_skill
from src.skill_evolution import v24_7, v24_8
from src.skill_evolution.v24_7 import campaign as previous
from src.skill_evolution.v24_8 import campaign
from tests.skill_evolution.v24_2 import fixture


def test_version_binding_and_publication(tmp_path):
    changed = {name for name in v24_8.STAGES
               if v24_8.system_prompt(name) != v24_7.system_prompt(name)}
    assert changed == {'diagnosis', 'preconditioner'}
    assert campaign.gate is previous.gate
    assert dict(campaign.configuration(), method=previous.VERSION) == previous.configuration()
    config = dict(fixture.fixture_config(), method=campaign.VERSION)
    initial = campaign.prepare(tmp_path, config)
    assert initial['memory'] == {'rounds': []}
    assert initial['selected'] == config['initial_skill']['text']

    stages = []

    def generate(name, messages, directory, call):
        assert messages[0]['content'] == v24_8.system_prompt(name)
        stages.append(name)
        reply = fixture.generate(name, messages, directory, call)
        if name == 'replay':
            # The shared Gate requires explicit references to both sides of each pair.
            value = json.loads(reply['content'])
            pairs = json.loads(messages[1]['content'])['pairs']
            for event, pair in zip(value['entries'][0]['knowledge'], pairs):
                event['text'] = f"{pair['parent']}:1 and {pair['candidate']}:1. " + event['text']
            reply['content'] = json.dumps(value)
        return reply

    state = campaign.run_round(tmp_path, actor=fixture.actor, generate=generate)
    assert stages == ['diagnosis', 'preconditioner', 'editor', 'replay']
    assert fixture.DESTINATION in state['selected']
    assert (tmp_path / 'final_skill.md').read_text() == state['selected']
    assert published_skill(tmp_path, config, campaign)[1] == state['selected']
    with pytest.raises(ValueError, match='Expected V24.7'):
        published_skill(tmp_path, config, previous)
