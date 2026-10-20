"""A single historical-support replacement preserves V23 execution and contracts."""
import json
from pathlib import Path

from src.skill_evolution.v23_2 import local_validation as local
from tests.skill_evolution.v23_2.test_local_validation import saved, config, keep
from tests.skill_evolution.v23.test_diagnosis import answer

PROMPT = Path('experiments/methods/v23_2/v23_2_response_alignment_001/config/preconditioner_prompt.md')
BEFORE = ('Examine whether each Update is appropriate relative to the Parent Skill and executable '
          'using information and actions available to the Actor at decision time.')
AFTER = ('Examine each Update against the Parent Skill and the specific edits, conditions, observed effects, '
         'and limitations supported by relevant historical evidence. Examine whether each Update is executable '
         'using information and actions available to the Actor at decision time.\n\n'
         'Support for an improvement goal does not automatically support a different strategy, scope, or strength; '
         'assess the difference using current evidence and historical counterexamples before deciding to keep, adjust, or withdraw.')


def test_only_historical_support_rule_changes(saved):
    frozen = json.loads(Path('artifacts/methods/v23/v23_alfworld_formal_001/S1/contract.json').read_text())
    original = frozen['src/skill_evolution/v23/preconditioner_prompt.md']
    assert local.PROMPTS['preconditioner'].read_text() == original
    assert original.count(BEFORE) == 1 and PROMPT.read_text() == original.replace(BEFORE, AFTER)
    old = local.messages_for('preconditioner', saved)
    new = local.messages_for('preconditioner', saved, prompt_path=PROMPT)
    assert new[1:] == old[1:]
    assert new[0]['content'] == old[0]['content'].replace(BEFORE, AFTER)
    for name in ('diagnosis', 'preconditioner'):
        assert local.messages_for(name, saved) == local.MODULES[name].messages_for(saved)


def test_explicit_template_keeps_original_contract(saved, config, tmp_path):
    result = local.run_stage('preconditioner', saved, tmp_path/'p', config, prompt_path=PROMPT,
                             generate=lambda *_:answer(keep()))
    assert result['effective_plan'] == saved['diagnosis']['plan']
    assert result['memory'] == saved['memory']
    assert local.load_attempt(tmp_path/'p/attempts/001',prompt_path=PROMPT) == result
