import hashlib
import json
from dataclasses import replace

import pytest
from src.skill_evolution.v18.editor_contract_v18 import EditorInput, EditorRejected
from src.skill_evolution.v18.editor_input_v18 import build_editor_input, editor_payload
from src.skill_evolution.v18.editor_prompt_v18 import build_editor_request
from src.skill_evolution.v18.compiler_v18 import compile_edit_plan
from tests.skill_evolution.v18.test_compiler_v18 import case, build, source, batch, valid, diagnosis


def test_local_packets_and_stable_prompt(case):
    a,b=build(case)
    data=batch(a,[source(a,valid(a)),source(b,valid(b))])
    value=EditorInput(data,compile_edit_plan(data))
    prepared=build_editor_request(value)
    assert prepared==build_editor_request(value)
    assert prepared==build_editor_request(replace(value,compiler_input=replace(data,diagnoses=data.diagnoses[::-1])))
    payload=json.loads(prepared['user_prompt'])
    assert prepared['input_sha256']==hashlib.sha256(prepared['user_prompt'].encode()).hexdigest()
    units=payload['edit_units']
    assert len(units)==2
    for unit in units:
        assert len(unit['backing_gaps'])==1 and len(unit['analyses'])==1
        analysis=unit['analyses'][0]
        expected=set()
        for name in ['success_analysis','compliance_analysis']:
            expected.update(analysis[name]['evidence_refs'])
            expected.update(analysis[name]['supervision_refs'])
        assert set(unit['evidence_catalog'])==expected
        assert unit['target_rules']==[]
    assert set(units[0]['evidence_catalog']).isdisjoint(units[1]['evidence_catalog'])
    assert 'provenance_json' not in prepared['user_prompt']


def test_noop_omitted_and_all_noop_skips(case):
    a,b=build(case)
    data=batch(a,[source(a,valid(a)),source(b,diagnosis('NOT_ADDRESSABLE'))])
    value=EditorInput(data,compile_edit_plan(data))
    assert len(build_editor_input(value).edit_units)==1
    data=batch(b,[source(b,diagnosis('NOT_ADDRESSABLE'))])
    assert build_editor_request(EditorInput(data,compile_edit_plan(data))) is None


def test_target_rule_and_policy_resolved(case):
    a=build(case)[0]
    output=valid(a)
    rule=next(iter(a.learner_payload['available_rule_refs']))
    policy=next(iter(a.learner_payload['available_policy_refs']))
    output['parent_skill_gaps'][0].update(kind='NEEDS_REVISION',related_rule_refs=[rule])
    output['parent_skill_gaps'][0]['evidence_refs'].append(policy)
    output['success_analysis']['evidence_refs'].append(policy)
    data=batch(a,[source(a,output)])
    packet=editor_payload(build_editor_input(EditorInput(data,compile_edit_plan(data))))['edit_units'][0]
    assert packet['target_rules'][0]['ref']==rule
    assert packet['evidence_catalog'][policy]['reference_type']=='VISIBLE_POLICY'
    assert packet['evidence_catalog'][rule]['text']==a.learner_payload['available_rule_refs'][rule]['text']


def test_reject_plan_or_parent_tampering(case):
    a=build(case)[0]; data=batch(a,[source(a,valid(a))]); plan=compile_edit_plan(data)
    for value in [EditorInput(data,replace(plan,edit_units=())),EditorInput(replace(data,parent_skill='changed'),plan),{}]:
        with pytest.raises(EditorRejected):build_editor_request(value)


def test_delete_units_stay_runtime_only_and_original_indices_are_retained(case):
    from tests.skill_evolution.v18.test_editor_apply_v18 import mixed, editing_input
    value = mixed(case)
    packed = build_editor_input(value)
    assert [u.operation for u in packed.edit_units] == ['DELETE', 'REPLACE', 'DELETE', 'ADD']
    prepared = build_editor_request(value)
    payload = json.loads(prepared['user_prompt'])
    assert [u['edit_unit_index'] for u in payload['edit_units']] == [1, 3]
    assert [u['operation'] for u in payload['edit_units']] == ['REPLACE', 'ADD']
    assert prepared['response_format']['json_schema']['name'] == 'v18_bounded_editor'
    assert payload['schema_version'] == 'editor_request_v18.1'
    assert prepared['prompt_version'] == 'v18-bounded-editor-1'
    pure = editing_input(case, '- A', [('SHOULD_REMOVE', [0])])
    assert build_editor_request(pure) is None
    assert len(build_editor_input(pure).edit_units) == 1
