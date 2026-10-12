import copy
import hashlib
import json
from dataclasses import replace

import pytest
from src.skill_evolution.v17.compiler_contract_v17 import CompilerRejected
from src.skill_evolution.v17.compiler_v17 import compile_edit_plan
from src.skill_evolution.v17.compiler_validation_v17 import validate_edit_plan, plan_payload
from src.skill_evolution.v17.compiler_audit_v17 import run_compiler
from tests.skill_evolution.v17.test_compiler_v17 import case, build, source, batch, valid, diagnosis


@pytest.mark.parametrize('mutation', [
    lambda p: p.update(extra=1),
    lambda p: p.update(edit_units=[]),
    lambda p: p['edit_units'][0].update(operation='DELETE'),
    lambda p: p['edit_units'][0]['supporting_gap_refs'][0].update(gap_index=True),
    lambda p: p['edit_units'][0]['supporting_gap_refs'][0].update(gap_index=99),
    lambda p: p['edit_units'][0].update(target_rule_refs=['RULE/stale']),
    lambda p: p.update(parent_skill_digest='wrong'),
    lambda p: p['noop_records'][0].update(reason='rewritten'),
    lambda p: p['source_diagnosis_refs'].reverse(),
])
def test_reject_modified_plan_without_repair(case, mutation):
    a,b=build(case)
    data=batch(a,[source(a,valid(a)),source(b,diagnosis('NOT_ADDRESSABLE'))])
    plan=plan_payload(compile_edit_plan(data))
    mutation(plan)
    before=copy.deepcopy(plan)
    with pytest.raises(CompilerRejected) as exc:
        validate_edit_plan(plan,compiler_input=data)
    assert exc.value.stage=='PLAN'
    assert plan==before


def test_audit_deterministic_bytes_and_no_overwrite(case,tmp_path):
    a,b=build(case)
    data=batch(a,[source(a,valid(a)),source(b,diagnosis('NOT_ADDRESSABLE'))])
    first=run_compiler(data,artifact_dir=tmp_path/'a')
    second=run_compiler(replace(data,diagnoses=data.diagnoses[::-1]),artifact_dir=tmp_path/'b')
    assert first==second and first['status']=='VALID'
    for name in ['input.json','edit_plan.json','validation.json']:
        assert (tmp_path/'a'/name).read_bytes()==(tmp_path/'b'/name).read_bytes()
    assert first['plan_sha256']==hashlib.sha256((tmp_path/'a'/'edit_plan.json').read_bytes()).hexdigest()
    validate_edit_plan(json.loads((tmp_path/'a'/'edit_plan.json').read_text()),compiler_input=data)
    with pytest.raises(FileExistsError):run_compiler(data,artifact_dir=tmp_path/'a')


def test_invalid_input_only_rejection_and_all_noop(case,tmp_path):
    a=build(case)[0]
    data=batch(a,[source(a,diagnosis('NOT_ADDRESSABLE'))])
    bad=run_compiler(replace(data,parent_skill_digest='wrong'),artifact_dir=tmp_path/'bad')
    assert bad['status']=='REJECTED' and bad['stage']=='BINDING'
    assert sorted(p.name for p in (tmp_path/'bad').iterdir())==['validation.json']
    good=run_compiler(data,artifact_dir=tmp_path/'good')
    assert good['status']=='VALID' and good['edit_unit_count']==0
