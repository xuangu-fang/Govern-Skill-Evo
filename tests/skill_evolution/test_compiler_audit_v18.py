import copy
import hashlib
import json
from dataclasses import replace

import pytest
from src.skill_evolution.compiler_contract_v18 import CompilerRejected
from src.skill_evolution.compiler_v18 import compile_edit_plan
from src.skill_evolution.compiler_validation_v18 import validate_edit_plan, plan_payload
from src.skill_evolution.compiler_audit_v18 import run_compiler
from tests.skill_evolution.test_compiler_v18 import case, build, source, batch, valid, diagnosis
from tests.skill_evolution.test_compiler_v18 import multi_rule_request, targeted_source


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


@pytest.mark.parametrize('mutate', [
    lambda p: p['edit_units'][0].update(operation='REPLACE'),
    lambda p: p['edit_units'][0].update(operation='ERASE'),
    lambda p: p['edit_units'][0].update(target_rule_refs=[]),
    lambda p: p['edit_units'][0]['target_rule_refs'].pop(),
    lambda p: p['edit_units'][0]['target_rule_refs'].reverse(),
    lambda p: p['edit_units'][0].update(supporting_gap_refs=[]),
    lambda p: p['edit_units'].append(copy.deepcopy(p['edit_units'][0])),
    lambda p: p.update(schema_version='compiler_edit_plan_v17.1'),
])
def test_delete_plan_cannot_change_operation_targets_or_coverage(case, mutate):
    request = multi_rule_request(case)
    rules = list(request.learner_payload['available_rule_refs'])
    data = batch(request, [targeted_source(request, 'SHOULD_REMOVE', rules)])
    payload = plan_payload(compile_edit_plan(data))
    mutate(payload)
    before = copy.deepcopy(payload)
    with pytest.raises(CompilerRejected) as exc:
        validate_edit_plan(payload, compiler_input=data)
    assert exc.value.stage == 'PLAN' and payload == before


def test_pure_delete_audit_keeps_source_prose_and_has_no_candidate(case, tmp_path):
    request = multi_rule_request(case)
    rules = list(request.learner_payload['available_rule_refs'])
    output = valid(request)
    # Deliberately questionable semantics must not be repaired by the Compiler.
    output['parent_skill_gaps'][0].update(kind='SHOULD_REMOVE', related_rule_refs=rules,
                                        gap='Remove this; transfer fallback remains uncertain.')
    data = batch(request, [source(request, output)])
    result = run_compiler(data, artifact_dir=tmp_path / 'delete')
    assert result['status'] == 'VALID' and result['edit_unit_count'] == 1
    assert sorted(p.name for p in (tmp_path / 'delete').iterdir()) == ['edit_plan.json', 'input.json', 'validation.json']
    saved = json.loads((tmp_path / 'delete/input.json').read_text())
    assert saved['schema_version'] == 'compiler_input_audit_v18.1'
    assert saved['parent_skill'] == data.parent_skill
    assert saved['sources'][0]['validated_payload'] == data.diagnoses[0].validated.payload
    assert result['input_sha256'] == hashlib.sha256((tmp_path / 'delete/input.json').read_bytes()).hexdigest()


def test_conflict_audit_publishes_only_rejection(case, tmp_path):
    request = multi_rule_request(case)
    rule = next(iter(request.learner_payload['available_rule_refs']))
    output = valid(request)
    output['parent_skill_gaps'][0].update(kind='SHOULD_REMOVE', related_rule_refs=[rule])
    replacement = copy.deepcopy(output['parent_skill_gaps'][0])
    replacement['kind'] = 'NEEDS_REVISION'
    output['parent_skill_gaps'].append(replacement)
    data = batch(request, [source(request, output)])
    result = run_compiler(data, artifact_dir=tmp_path / 'conflict')
    assert result == {'status': 'REJECTED', 'stage': 'PLAN', 'reason': 'MIXED_OPERATION_TARGET_CONFLICT'}
    assert sorted(p.name for p in (tmp_path / 'conflict').iterdir()) == ['validation.json']


def test_delete_schema_is_detached_from_v17():
    from src.skill_evolution.compiler_contract_v17 import build_edit_plan_schema as old
    from src.skill_evolution.compiler_contract_v18 import build_edit_plan_schema
    schema = build_edit_plan_schema()
    assert schema['properties']['edit_units']['items']['properties']['operation']['enum'] == ['ADD', 'REPLACE', 'DELETE']
    schema['properties'].clear()
    assert build_edit_plan_schema()['properties']
    assert old()['properties']['edit_units']['items']['properties']['operation']['enum'] == ['ADD', 'REPLACE']
