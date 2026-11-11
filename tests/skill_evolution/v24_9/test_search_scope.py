"""Scripted regressions for the search-only candidate and selected Skill."""
import json

import pytest

from scripts.runs.v24_2.run_v24_2_test import published_skill
from src.skill_evolution import v24_7, v24_9
from src.skill_evolution.v24_2.storage import read
from src.skill_evolution.v24_7 import campaign as baseline
from src.skill_evolution.v24_9 import campaign, search_scope
from tests.skill_evolution.v24_2 import fixture


@pytest.mark.parametrize('prefix', ['| Pick Two & Place', '5. **Direct delivery', '- **Premature termination'])
def test_candidate_rejects_changes_outside_search(prefix):
    parent = campaign.configuration()['initial_skill']['text']
    line = next(s for s in parent.splitlines() if s.startswith(prefix))
    patch = f'--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-{line}\n+{line} Changed.\n'
    view = dict(parent=parent, plan=dict(goal='Search', updates=[dict(id='u1', text='Search')]))
    with pytest.raises(ValueError, match='Edit only the body'):
        search_scope.edit(dict(edits=[dict(update_id='u1', patch=patch, reason='fixture')]), view)


def test_round_corrects_bad_patch_and_publishes_only_retained_search_edit(tmp_path, monkeypatch):
    assert campaign.gate is baseline.gate
    assert dict(campaign.configuration(), method=baseline.VERSION) == baseline.configuration()
    assert {s for s in v24_9.STAGES if v24_9.system_prompt(s) != v24_7.system_prompt(s)} == {
        'diagnosis', 'preconditioner', 'editor'}
    config = dict(fixture.fixture_config(), method=campaign.VERSION)
    initial = campaign.prepare(tmp_path, config)
    parent = config['initial_skill']['text']
    assert initial['selected'] == parent and initial['memory'] == {'rounds': []}
    # The shared scripted Actor expects both effective fixture strings in its Candidate.
    continuation = 'After a miss, use an available search action to inspect a different location.'
    monkeypatch.setattr(fixture, 'DESTINATION', continuation)

    def generate(name, messages, slot, call):
        assert messages[0]['content'] == v24_9.system_prompt(name)
        reply = fixture.generate(name, messages, slot, call)
        result = json.loads(reply['content'])
        if name == 'editor' and slot.name == '002':
            assert 'Edit only the body' in messages[-1]['content']
            anchor = next(line for line in parent.splitlines() if line.startswith('3. **Grab immediately'))
            result['edits'][1]['patch'] = (
                f'--- a/SKILL.md\n+++ b/SKILL.md\n@@\n+{continuation}\n {anchor}\n')
        if name == 'replay':
            for pair, event in zip(json.loads(messages[1]['content'])['pairs'], result['entries'][0]['knowledge']):
                event['text'] = f"{pair['parent']}:1 and {pair['candidate']}:1. " + event['text']
        reply['content'] = json.dumps(result)
        return reply

    state = campaign.run_round(tmp_path, generate=generate, actor=fixture.actor)
    rd = tmp_path / 'rounds/R01'
    assert read(rd / 'editor/result.json')['attempt'] == 2
    assert read(rd / 'gate.json')['selection']['selected_update_ids'] == ['u2']
    expected = parent.replace('\n3. **Grab immediately', f'\n{continuation}\n3. **Grab immediately')
    assert state['selected'] == expected == (tmp_path / 'final_skill.md').read_text()
    assert published_skill(tmp_path, config, campaign)[1] == expected
    assert campaign.run_round(tmp_path) == state
