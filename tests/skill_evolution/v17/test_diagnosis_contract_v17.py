import copy

import pytest

from src.skill_evolution.v17.diagnosis_contract_v17 import DiagnosisContractError, build_diagnosis_response_format, validate_diagnosis_output


def diagnosis(status='NO_ISSUE'):
    analysis = {'finding': 'No supported issue observed.', 'evidence_refs': [],
                'supervision_refs': [], 'unresolved': ['Coverage is limited.']}
    return {'success_analysis': copy.deepcopy(analysis),
            'compliance_analysis': copy.deepcopy(analysis),
            'skill_addressability': {'status': status, 'reason': 'Evidence-based judgment.'},
            'parent_skill_gaps': [] if status != 'ADDRESSABLE' else [{
                'kind': 'MISSING', 'gap': 'Preserve the requested time constraint during search.',
                'evidence_refs': ['T1/R1/R1/E0001'], 'related_rule_refs': [],
                'source_dimensions': ['SUCCESS']}]}


@pytest.mark.parametrize('status', ['NO_ISSUE', 'NOT_ADDRESSABLE', 'ADDRESSABLE'])
def test_valid_states_without_mutation(status):
    value = diagnosis(status)
    before = copy.deepcopy(value)
    assert validate_diagnosis_output(value) is None
    assert value == before


def test_multiple_independently_bound_gaps():
    value = diagnosis('ADDRESSABLE')
    value['parent_skill_gaps'].append({
        'kind': 'NEEDS_REVISION', 'gap': 'Narrow confirmation to unapproved actions.',
        'evidence_refs': ['T2/R2/R1/E0004'], 'related_rule_refs': ['RULE1'],
        'source_dimensions': ['SUCCESS', 'COMPLIANCE']})
    validate_diagnosis_output(value)


@pytest.mark.parametrize('status', ['NO_ISSUE', 'NOT_ADDRESSABLE'])
def test_inactive_state_rejects_gaps(status):
    value = diagnosis('ADDRESSABLE')
    value['skill_addressability']['status'] = status
    with pytest.raises(DiagnosisContractError):
        validate_diagnosis_output(value)


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(parent_skill_gaps=[]),
    lambda d: d.update(mechanism_synthesis='not allowed'),
    lambda d: d['success_analysis'].update(finding=' '),
    lambda d: d['compliance_analysis'].pop('unresolved'),
    lambda d: d['success_analysis'].update(unresolved='unknown'),
    lambda d: d['success_analysis'].update(evidence_refs=['E1', 'E1']),
    lambda d: d['compliance_analysis'].update(supervision_refs=[None]),
    lambda d: d['skill_addressability'].update(status='MAYBE'),
    lambda d: d['skill_addressability'].update(reason=''),
    lambda d: d['parent_skill_gaps'][0].update(evidence_refs=[]),
    lambda d: d['parent_skill_gaps'][0].update(evidence_refs=['E1', 'E1']),
    lambda d: d['parent_skill_gaps'][0].update(source_dimensions=[]),
    lambda d: d['parent_skill_gaps'][0].update(source_dimensions=['SUCCESS', 'SUCCESS']),
    lambda d: d['parent_skill_gaps'][0].update(source_dimensions=['BOTH']),
    lambda d: d['parent_skill_gaps'][0].update(kind='ADD'),
    lambda d: d['parent_skill_gaps'][0].update(gap=''),
    lambda d: d['parent_skill_gaps'][0].update(related_rule_refs=['RULE1']),
    lambda d: d['parent_skill_gaps'][0].update(kind='NEEDS_REVISION'),
    lambda d: d['parent_skill_gaps'][0].update(supervision_refs=['S1']),
    lambda d: d['parent_skill_gaps'][0].update(operation='ADD'),
])
def test_invalid_contract(mutation):
    value = diagnosis('ADDRESSABLE')
    mutation(value)
    with pytest.raises(DiagnosisContractError):
        validate_diagnosis_output(value)


def test_schema_copy_isolation():
    first = build_diagnosis_response_format()
    first['json_schema']['schema']['properties'].clear()
    second = build_diagnosis_response_format()
    assert len(second['json_schema']['schema']['properties']) == 4
    assert second['json_schema']['strict'] is True


def test_reference_resolution_is_explicitly_deferred():
    value = diagnosis('ADDRESSABLE')
    value['parent_skill_gaps'][0]['evidence_refs'] = ['opaque-ref-not-yet-resolved']
    validate_diagnosis_output(value)
