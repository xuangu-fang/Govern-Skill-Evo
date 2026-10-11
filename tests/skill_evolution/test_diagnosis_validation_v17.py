import json
from dataclasses import replace

import pytest

from src.skill_evolution.diagnosis_validation_v17 import DiagnosisRejected, validate_diagnosis_response
from src.skill_evolution.information_boundary_v15 import _seal, unpack
from tests.skill_evolution.test_group_diagnosis_input_v17 import case, build
from tests.skill_evolution.test_diagnosis_contract_v17 import diagnosis


def valid(request):
    output = diagnosis('ADDRESSABLE')
    payload = request.learner_payload
    event = next(iter(payload['available_evidence_refs']))
    supervision = next(iter(payload['available_supervision_refs']))
    output['success_analysis']['evidence_refs'] = [event]
    output['success_analysis']['supervision_refs'] = [supervision]
    output['parent_skill_gaps'][0]['evidence_refs'] = [event]
    return output


@pytest.mark.parametrize('status', ['NO_ISSUE', 'NOT_ADDRESSABLE', 'ADDRESSABLE'])
def test_valid_states_preserve_exact_output(case, status):
    request = build(case)[0]
    if status == 'NO_ISSUE':
        payload = request.learner_payload
        for experience in payload['experiences']:
            experience['supervision'].update(success=True, compliant=True)
        request = replace(request, learner_view=_seal('V17_GROUP_DIAGNOSIS_INPUT', payload))
    output = valid(request) if status == 'ADDRESSABLE' else diagnosis(status)
    raw = json.dumps(output, indent=2)
    result = unpack(validate_diagnosis_response(raw, request=request), 'V17_VALIDATED_DIAGNOSIS')
    assert result['semantic'] == output
    assert result['raw_response'] == raw
    assert result['validation_status'] == 'VALID'
    assert result['semantic_origin'] == 'LEARNER_INFERRED'


@pytest.mark.parametrize('raw', [None, {}, '', '```json\n{}\n```', 'Here: {}', '{} {}',
                                  '{"x":1,"x":2}', '{"x":{"a":1,"a":2}}',
                                  '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'])
def test_parse_rejection_without_repair(case, raw):
    with pytest.raises(DiagnosisRejected) as error:
        validate_diagnosis_response(raw, request=build(case)[0])
    assert error.value.stage == 'PARSE'


@pytest.mark.parametrize('mutate', [
    lambda d: d.update(extra='ignored?'),
    lambda d: d['skill_addressability'].update(status='NO_ISSUE'),
    lambda d: d.update(parent_skill_gaps=[]),
    lambda d: d['parent_skill_gaps'][0].update(evidence_refs=[]),
    lambda d: d['parent_skill_gaps'][0].update(source_dimensions='SUCCESS'),
    lambda d: d['parent_skill_gaps'][0].update(kind='NEEDS_REVISION'),
])
def test_structure_rejects_instead_of_coercing(case, mutate):
    request = build(case)[0]
    output = valid(request)
    mutate(output)
    raw = json.dumps(output)
    with pytest.raises(DiagnosisRejected) as error:
        validate_diagnosis_response(raw, request=request)
    assert error.value.stage == 'STRUCTURE'
    assert json.dumps(output) == raw


@pytest.mark.parametrize('target', ['unknown', 'other_group', 'wrong_type', 'stale_rule'])
def test_reference_rejections(case, target):
    request, other = build(case)
    output = valid(request)
    gap = output['parent_skill_gaps'][0]
    if target == 'unknown':
        gap['evidence_refs'] = ['NOT_FOUND']
    elif target == 'other_group':
        gap['evidence_refs'] = [next(iter(other.learner_payload['available_evidence_refs']))]
    elif target == 'wrong_type':
        gap['evidence_refs'] = [next(iter(request.learner_payload['available_supervision_refs']))]
    else:
        gap.update(kind='NEEDS_REVISION', related_rule_refs=['RULE/old-parent/L1-1'])
    with pytest.raises(DiagnosisRejected) as error:
        validate_diagnosis_response(json.dumps(output), request=request)
    assert error.value.stage == 'REFERENCES'


def test_input_tampering_rejected(case):
    request = build(case)[0]
    raw = json.dumps(valid(request))
    changed = replace(request, learner_view=replace(request.learner_view, payload='{}'))
    with pytest.raises(DiagnosisRejected) as error:
        validate_diagnosis_response(raw, request=changed)
    assert error.value.stage == 'REFERENCES'


def test_gap_requires_source_analysis_binding(case):
    request = build(case)[0]
    output = valid(request)
    output['success_analysis']['evidence_refs'] = []
    with pytest.raises(DiagnosisRejected) as error:
        validate_diagnosis_response(json.dumps(output), request=request)
    assert error.value.stage == 'LINKAGE'


def test_both_dimensions_need_trajectory_overlap(case):
    request = build(case)[0]
    output = valid(request)
    output['parent_skill_gaps'][0]['source_dimensions'] = ['SUCCESS', 'COMPLIANCE']
    with pytest.raises(DiagnosisRejected) as error:
        validate_diagnosis_response(json.dumps(output), request=request)
    assert error.value.stage == 'LINKAGE'
    output['compliance_analysis']['evidence_refs'] = output['success_analysis']['evidence_refs'][:]
    validate_diagnosis_response(json.dumps(output), request=request)


def test_policy_only_gap_rejected_and_no_partial_acceptance(case):
    request = build(case)[0]
    output = valid(request)
    policy = next(iter(request.learner_payload['available_policy_refs']))
    output['parent_skill_gaps'].append({
        'kind': 'MISSING', 'gap': 'Unsupported by observed behavior.', 'evidence_refs': [policy],
        'related_rule_refs': [], 'source_dimensions': ['COMPLIANCE']})
    output['compliance_analysis']['evidence_refs'] = [policy]
    with pytest.raises(DiagnosisRejected) as error:
        validate_diagnosis_response(json.dumps(output), request=request)
    assert error.value.stage == 'REFERENCES'


def test_policy_and_current_rule_supported(case):
    request = build(case)[0]
    output = valid(request)
    policy = next(iter(request.learner_payload['available_policy_refs']))
    rule = next(iter(request.learner_payload['available_rule_refs']))
    output['success_analysis']['evidence_refs'].append(policy)
    output['parent_skill_gaps'][0]['evidence_refs'].append(policy)
    output['parent_skill_gaps'][0].update(kind='NEEDS_REVISION', related_rule_refs=[rule])
    validate_diagnosis_response(json.dumps(output), request=request)


@pytest.mark.parametrize('negative_dimension', ['success', 'compliant'])
def test_no_issue_rejects_any_negative_outcome_even_without_citation(case, negative_dimension):
    request = build(case)[0]
    payload = request.learner_payload
    for experience in payload['experiences']:
        experience['supervision'].update(success=True, compliant=True)
    payload['experiences'][-1]['supervision'][negative_dimension] = False
    request = replace(request, learner_view=_seal('V17_GROUP_DIAGNOSIS_INPUT', payload))
    raw = json.dumps(diagnosis('NO_ISSUE'))
    with pytest.raises(DiagnosisRejected) as error:
        validate_diagnosis_response(raw, request=request)
    assert error.value.stage == 'LINKAGE'
    assert 'NO_ISSUE' in error.value.reason
    # Unknown causes remain representable without inventing a gap.
    validate_diagnosis_response(json.dumps(diagnosis('NOT_ADDRESSABLE')), request=request)
