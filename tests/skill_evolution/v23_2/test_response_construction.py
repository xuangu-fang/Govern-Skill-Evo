"""One scoped requirement replacement, unchanged original assembly and contracts."""
import json
from pathlib import Path
from src.skill_evolution.v23_2 import local_validation as local
from tests.skill_evolution.v23_2.test_local_validation import saved,config,keep
from tests.skill_evolution.v23.test_diagnosis import answer
from tests.skill_evolution.v23_2.test_response_alignment import BEFORE,AFTER

EXP=Path('experiments/methods/v23_2/v23_2_response_construction_001')
PROMPT=EXP/'config/preconditioner_prompt.md'


def test_only_existing_requirement_is_replaced(saved):
    frozen=json.loads(Path('artifacts/methods/v23/v23_alfworld_formal_001/S1/contract.json').read_text())
    original=frozen['src/skill_evolution/v23/preconditioner_prompt.md']
    previous=Path('experiments/methods/v23_2/v23_2_response_alignment_001/config/preconditioner_prompt.md').read_text()
    replacement=(EXP/'config/replacement.txt').read_text().rstrip('\n')
    assert previous==original.replace(BEFORE,AFTER)
    assert PROMPT.read_text()==original.replace(BEFORE,replacement)==previous.replace(AFTER,replacement)
    old=local.messages_for('preconditioner',saved)
    new=local.messages_for('preconditioner',saved,prompt_path=PROMPT)
    assert new[1:]==old[1:] and new[0]['content']==old[0]['content'].replace(BEFORE,replacement)
    for name in ('diagnosis','preconditioner'):
        assert local.messages_for(name,saved)==local.MODULES[name].messages_for(saved)


def test_original_keep_contract_and_compiler(saved,config,tmp_path):
    out=local.run_stage('preconditioner',saved,tmp_path/'p',config,prompt_path=PROMPT,generate=lambda *_:answer(keep()))
    assert out['effective_plan']==saved['diagnosis']['plan'] and out['memory']==saved['memory']
    assert local.load_attempt(tmp_path/'p/attempts/001',prompt_path=PROMPT)==out
