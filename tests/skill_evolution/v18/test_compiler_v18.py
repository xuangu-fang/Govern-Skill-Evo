import copy
import hashlib
import json
from dataclasses import replace
from itertools import permutations

import pytest

from src.skill_evolution.v18.compiler_contract_v18 import CompilerInput, CompilerDiagnosisSource, CompilerRejected
from src.skill_evolution.v18.compiler_v18 import compile_edit_plan
from src.skill_evolution.v18.diagnosis_validation_v18 import validate_diagnosis_response
from src.skill_evolution.v18.diagnosis_references_v18 import build_reference_catalogs
from src.skill_evolution.v15.information_boundary_v15 import _seal, unpack
from tests.skill_evolution.v17.test_group_diagnosis_input_v17 import case, build
from tests.skill_evolution.v18.test_diagnosis_validation_v18 import valid
from tests.skill_evolution.v18.test_diagnosis_contract_v18 import diagnosis


def source(request, output):
    envelope = validate_diagnosis_response(json.dumps(output), request=request)
    return CompilerDiagnosisSource('DIAGNOSIS/' + hashlib.sha256(envelope.payload.encode()).hexdigest(), request, envelope)


def batch(request, sources):
    parent = request.learner_payload['current_skill']
    return CompilerInput('round-1', parent, hashlib.sha256(parent.encode()).hexdigest(), tuple(sources))


def test_add_noop_and_input_order(case):
    first, second = build(case)
    a = source(first, valid(first))
    b = source(second, diagnosis('NOT_ADDRESSABLE'))
    original = batch(first, [a, b])
    plan = compile_edit_plan(original)
    assert plan == compile_edit_plan(replace(original, diagnoses=(b, a)))
    assert len(plan.edit_units) == len(plan.noop_records) == 1
    assert plan.edit_units[0].operation == 'ADD'
    assert plan.edit_units[0].target_rule_refs == ()
    assert plan.noop_records[0].reason == diagnosis('NOT_ADDRESSABLE')['skill_addressability']['reason']
    assert original == batch(first, [a, b])


@pytest.mark.parametrize('kind,operation', [('NEEDS_REVISION', 'REPLACE'), ('SHOULD_REMOVE', 'DELETE')])
def test_transitive_targets_and_stable_rule_order(case, kind, operation):
    request = build(case)[0]
    payload = request.learner_payload
    payload['current_skill'] = '# Skill\n- A\n- B\n- C\n- D\n'
    payload.update(build_reference_catalogs(payload))
    provenance = request.provenance
    provenance['parent_skill_digest'] = hashlib.sha256(payload['current_skill'].encode()).hexdigest()
    request = replace(request, learner_view=_seal('V17_GROUP_DIAGNOSIS_INPUT', payload), provenance_json=json.dumps(provenance))
    rules = list(payload['available_rule_refs'])
    sources = []
    for i, targets in enumerate([[rules[0]], [rules[2], rules[1]], [rules[1], rules[0]], [rules[3]]]):
        local = replace(request, provenance_json=json.dumps(dict(provenance, group_id=f'G{i}')))
        output = valid(local)
        output['parent_skill_gaps'][0].update(kind=kind, related_rule_refs=targets, gap=f'Gap {i}')
        sources.append(source(local, output))
    plans = [compile_edit_plan(batch(request, order)) for order in permutations(sources)]
    assert all(p == plans[0] for p in plans)
    assert [u.target_rule_refs for u in plans[0].edit_units] == [tuple(rules[:3]), (rules[3],)]
    assert len(plans[0].edit_units[0].supporting_gap_refs) == 3
    assert sum(len(u.supporting_gap_refs) for u in plans[0].edit_units) == 4
    assert all(u.operation == operation for u in plans[0].edit_units)


def test_all_noop_and_no_semantic_dedup(case):
    request = build(case)[0]
    no = compile_edit_plan(batch(request, [source(request, diagnosis('NOT_ADDRESSABLE'))]))
    assert no.edit_units == () and len(no.noop_records) == 1
    payload = request.learner_payload
    for experience in payload['experiences']:
        experience['supervision'].update(success=True, compliant=True)
    positive = replace(request, learner_view=_seal('V17_GROUP_DIAGNOSIS_INPUT', payload))
    assert compile_edit_plan(batch(positive, [source(positive, diagnosis('NO_ISSUE'))])).noop_records[0].status == 'NO_ISSUE'
    output = valid(request)
    output['parent_skill_gaps'].append(copy.deepcopy(output['parent_skill_gaps'][0]))
    plan = compile_edit_plan(batch(request, [source(request, output)]))
    assert len(plan.edit_units) == 2
    assert [u.supporting_gap_refs[0].gap_index for u in plan.edit_units] == [0, 1]


@pytest.mark.parametrize('mutation,stage', [
    (lambda v: replace(v, diagnoses=()), 'INPUT'),
    (lambda v: replace(v, diagnoses=v.diagnoses * 2), 'INPUT'),
    (lambda v: replace(v, round_id='wrong'), 'BINDING'),
    (lambda v: replace(v, parent_skill=v.parent_skill + 'x'), 'BINDING'),
    (lambda v: replace(v, diagnoses=(replace(v.diagnoses[0], diagnosis_ref='wrong'),)), 'BINDING'),
    (lambda v: replace(v, diagnoses=(replace(v.diagnoses[0], validated={}),)), 'INPUT'),
])
def test_rejects_whole_input(case, mutation, stage):
    request = build(case)[0]
    with pytest.raises(CompilerRejected) as exc:
        compile_edit_plan(mutation(batch(request, [source(request, valid(request))])))
    assert exc.value.stage == stage


def test_rejects_resealed_inconsistent_validated_contents(case):
    request = build(case)[0]
    original = source(request, valid(request))
    saved = unpack(original.validated, 'V18_VALIDATED_DIAGNOSIS')
    saved['semantic']['parent_skill_gaps'][0]['gap'] = 'Changed without revalidation'
    envelope = _seal('V18_VALIDATED_DIAGNOSIS', saved)
    changed = replace(original, validated=envelope, diagnosis_ref='DIAGNOSIS/' + hashlib.sha256(envelope.payload.encode()).hexdigest())
    with pytest.raises(CompilerRejected) as exc:
        compile_edit_plan(batch(request, [changed]))
    assert exc.value.stage == 'BINDING'


def multi_rule_request(case):
    request = build(case)[0]
    payload = request.learner_payload
    payload['current_skill'] = '# Skill\r\n- A\r\n- B\r\n- C\r\n- D\r\n'
    payload.update(build_reference_catalogs(payload))
    provenance = request.provenance
    provenance['parent_skill_digest'] = hashlib.sha256(payload['current_skill'].encode()).hexdigest()
    return replace(request, learner_view=_seal('V17_GROUP_DIAGNOSIS_INPUT', payload),
                   provenance_json=json.dumps(provenance))


def targeted_source(request, kind, targets):
    output = valid(request)
    output['parent_skill_gaps'][0].update(kind=kind, related_rule_refs=targets)
    return source(request, output)


def test_mixed_operations_order_coverage_and_unchanged_semantics(case):
    request = multi_rule_request(case)
    rules = list(request.learner_payload['available_rule_refs'])
    sources = []
    for i, (kind, targets) in enumerate([
        ('NEEDS_REVISION', [rules[2]]), ('MISSING', []),
        ('SHOULD_REMOVE', [rules[0], rules[3]]), ('NEEDS_REVISION', [rules[1]]),
    ]):
        local = replace(request, provenance_json=json.dumps(dict(request.provenance, group_id=f'G{i}')))
        sources.append(targeted_source(local, kind, targets))
    original_payloads = [s.validated.payload for s in sources]
    plans = [compile_edit_plan(batch(request, order)) for order in permutations(sources)]
    assert all(plan == plans[0] for plan in plans)
    plan = plans[0]
    assert plan.schema_version == 'compiler_edit_plan_v18.1'
    assert [u.operation for u in plan.edit_units] == ['DELETE', 'REPLACE', 'REPLACE', 'ADD']
    assert plan.edit_units[0].target_rule_refs == (rules[0], rules[3])
    actual = [(r.diagnosis_ref, r.gap_index) for u in plan.edit_units for r in u.supporting_gap_refs]
    assert sorted(actual) == sorted((s.diagnosis_ref, 0) for s in sources)
    assert [s.validated.payload for s in sources] == original_payloads


@pytest.mark.parametrize('same_group', [True, False])
def test_mixed_target_conflict_rejects_whole_plan(case, same_group):
    request = multi_rule_request(case)
    rules = list(request.learner_payload['available_rule_refs'])
    output = valid(request)
    output['parent_skill_gaps'][0].update(kind='NEEDS_REVISION', related_rule_refs=rules[:2])
    delete = copy.deepcopy(output['parent_skill_gaps'][0])
    delete.update(kind='SHOULD_REMOVE', related_rule_refs=rules[1:3])
    if same_group:
        output['parent_skill_gaps'].append(delete)
        sources = [source(request, output)]
    else:
        other = replace(request, provenance_json=json.dumps(dict(request.provenance, group_id='Other')))
        sources = [source(request, output), targeted_source(other, 'SHOULD_REMOVE', rules[1:3])]
    for order in permutations(sources):
        with pytest.raises(CompilerRejected) as exc:
            compile_edit_plan(batch(request, order))
        assert (exc.value.stage, exc.value.reason) == ('PLAN', 'MIXED_OPERATION_TARGET_CONFLICT')


def test_delete_all_rules_is_an_edit_not_noop_and_does_not_change_parent(case):
    request = multi_rule_request(case)
    rules = list(request.learner_payload['available_rule_refs'])
    data = batch(request, [targeted_source(request, 'SHOULD_REMOVE', rules)])
    parent = data.parent_skill
    plan = compile_edit_plan(data)
    assert len(plan.edit_units) == 1 and plan.noop_records == ()
    assert plan.edit_units[0].operation == 'DELETE'
    assert plan.edit_units[0].target_rule_refs == tuple(rules)
    assert data.parent_skill == parent  # Text application belongs to Editor step 5.


def test_legacy_envelope_is_not_accepted(case):
    from src.skill_evolution.v17.diagnosis_validation_v17 import validate_diagnosis_response as old_validate
    request = build(case)[0]
    legacy = old_validate(json.dumps(valid(request)), request=request)
    item = CompilerDiagnosisSource('DIAGNOSIS/' + hashlib.sha256(legacy.payload.encode()).hexdigest(), request, legacy)
    with pytest.raises(CompilerRejected) as exc:
        compile_edit_plan(batch(request, [item]))
    assert exc.value.stage == 'INPUT'


def test_stale_delete_target_in_raw_response_rejected_during_revalidation(case):
    request = multi_rule_request(case)
    rules = list(request.learner_payload['available_rule_refs'])
    original = targeted_source(request, 'SHOULD_REMOVE', rules[:1])
    saved = unpack(original.validated, 'V18_VALIDATED_DIAGNOSIS')
    raw = json.loads(saved['raw_response'])
    raw['parent_skill_gaps'][0]['related_rule_refs'] = ['RULE/old/L1-1']
    saved['raw_response'] = json.dumps(raw)
    envelope = _seal('V18_VALIDATED_DIAGNOSIS', saved)
    bad = replace(original, validated=envelope, diagnosis_ref='DIAGNOSIS/' + hashlib.sha256(envelope.payload.encode()).hexdigest())
    with pytest.raises(CompilerRejected) as exc:
        compile_edit_plan(batch(request, [bad]))
    assert exc.value.stage == 'BINDING'
