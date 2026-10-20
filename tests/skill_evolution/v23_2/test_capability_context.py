"""Only the shared information-capability sentence changes from frozen V23."""
import json
from pathlib import Path

import pytest

from src.skill_evolution.v23_2 import local_validation as local
from tests.skill_evolution.v23_2.test_local_validation import saved, config, keep
from tests.skill_evolution.v23.test_diagnosis import answer


CONTEXT = Path('experiments/methods/v23_2/v23_2_capability_001/config/execution_context.md')
BEFORE = 'It cannot access the full execution history, write persistent notes, or inspect hidden evaluator state.'
AFTER = ('The Actor has no persistent record of search progress and cannot access the full execution history, '
         'write persistent notes, or inspect hidden evaluator state. Current action candidates and object states '
         'do not by themselves reveal which locations or categories were previously visited or exhausted. '
         'Such progress can only be used when supported by currently available information.')


@pytest.mark.parametrize('name', ['diagnosis', 'preconditioner'])
def test_frozen_v23_templates_only_context_change(name, saved):
    freeze = Path('artifacts/methods/v23/v23_alfworld_formal_001/S1/contract.json')
    if not freeze.exists(): pytest.skip('Formal frozen source unavailable')
    contract = json.loads(freeze.read_text())
    base = Path('src/skill_evolution/v23')
    prompt = base/f'{name}_prompt.md'
    assert prompt.read_text() == contract[str(prompt)]
    assert CONTEXT.read_text() == contract[str(base/'execution_context.md')].replace(BEFORE, AFTER)
    old = local.MODULES[name].messages_for(saved)
    new = local.messages_for(name, saved, prompt_path=prompt, context_path=CONTEXT)
    assert new[1] == old[1]
    assert old[0]['content'].count(BEFORE) == 1
    assert new[0]['content'] == old[0]['content'].replace(BEFORE, AFTER)


def test_explicit_context_archive_roundtrip(saved, config, tmp_path):
    prompt = Path('src/skill_evolution/v23/preconditioner_prompt.md')
    result = local.run_stage('preconditioner', saved, tmp_path/'new', config, prompt_path=prompt,
                             context_path=CONTEXT, generate=lambda *_: answer(keep()))
    assert result['effective_plan'] == saved['diagnosis']['plan']
    assert local.load_attempt(tmp_path/'new/attempts/001', prompt_path=prompt, context_path=CONTEXT) == result
    with pytest.raises(ValueError, match='Saved messages differ'):
        local.load_attempt(tmp_path/'new/attempts/001', prompt_path=prompt)
