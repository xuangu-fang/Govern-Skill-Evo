import hashlib
from dataclasses import replace

import pytest

from src.skill_evolution.v17.diagnosis_contract_v17 import DiagnosisContractError
from src.skill_evolution.v17.diagnosis_references_v17 import build_reference_catalogs, resolve_reference, resolve_diagnosis_references
from src.skill_evolution.v15.information_boundary_v15 import _seal
from tests.skill_evolution.v17.test_group_diagnosis_input_v17 import case, build
from tests.skill_evolution.v17.test_diagnosis_contract_v17 import diagnosis


def test_exact_spans_determinism_and_empty_parent():
    text = '# Skill\r\n\r\n## Rules\r\n- First rule.\r\n  continuation.\r\n- Second.\r\n'
    data = {'current_skill': text, 'contexts': [
        {'context_ref': 'C1', 'visible_policy': '授权条件\n\nDo not exceed approval.\n'}]}
    catalogs = build_reference_catalogs(data)
    assert catalogs == build_reference_catalogs(data)
    rules = list(catalogs['available_rule_refs'].values())
    assert len(rules) == 2
    assert rules[0]['text'] == '- First rule.\r\n  continuation.\r\n'
    assert rules[0]['start_line'] == 4 and rules[0]['end_line'] == 5
    assert rules[0]['section'] == 'Rules'
    assert len(catalogs['available_policy_refs']) == 2
    for parent in ('', '# Operational Skill\n\n## Planning and navigation\n'):
        assert build_reference_catalogs({**data, 'current_skill': parent})['available_rule_refs'] == {}
    assert set(catalogs['available_rule_refs']).isdisjoint(
        build_reference_catalogs({**data, 'current_skill': text + '\n'})['available_rule_refs'])


def test_typed_resolution_and_locality(case):
    first, second = build(case)
    p = first.learner_payload
    e = next(iter(p['available_evidence_refs']))
    s = next(iter(p['available_supervision_refs']))
    policy = next(iter(p['available_policy_refs']))
    rule = next(iter(p['available_rule_refs']))
    assert resolve_reference(first, e, reference_type='TRAJECTORY')['event']['step'] == 1
    assert type(resolve_reference(first, s, reference_type='SUPERVISION')['supervision']['success']) is bool
    assert resolve_reference(first, policy, reference_type='VISIBLE_POLICY', context_ref='C1', quote='Policy 1')['text'] == 'Policy 1'
    assert resolve_reference(first, rule, reference_type='PARENT_SKILL_RULE', quote='保留用户授权范围')['text'].strip() == '保留用户授权范围。'
    with pytest.raises(DiagnosisContractError):
        resolve_reference(second, e, reference_type='TRAJECTORY')
    with pytest.raises(DiagnosisContractError):
        resolve_reference(second, policy, reference_type='VISIBLE_POLICY')
    with pytest.raises(DiagnosisContractError):
        resolve_reference(first, policy, reference_type='VISIBLE_POLICY', context_ref='C2')
    with pytest.raises(DiagnosisContractError):
        resolve_reference(first, policy, reference_type='VISIBLE_POLICY', quote='invented rule')
    with pytest.raises(DiagnosisContractError):
        resolve_reference(first, rule, reference_type='TRAJECTORY')


def test_output_resolves_without_new_gap_fields(case):
    request = build(case)[0]
    p = request.learner_payload
    event = next(iter(p['available_evidence_refs']))
    policy = next(iter(p['available_policy_refs']))
    rule = next(iter(p['available_rule_refs']))
    output = diagnosis('ADDRESSABLE')
    output['compliance_analysis']['evidence_refs'] = [event, policy]
    output['compliance_analysis']['supervision_refs'] = [next(iter(p['available_supervision_refs']))]
    gap = output['parent_skill_gaps'][0]
    gap.update(kind='NEEDS_REVISION', evidence_refs=[event, policy], related_rule_refs=[rule])
    resolved = resolve_diagnosis_references(output, request=request)
    assert resolved['parent_skill_gaps'][0]['related_rule_refs'][0]['text']
    gap['evidence_refs'] = [policy]
    with pytest.raises(DiagnosisContractError, match='trajectory'):
        resolve_diagnosis_references(output, request=request)


def test_stale_parent_reference(case):
    sources, scope, groups, parent = case
    old_ref = next(iter(build(case)[0].learner_payload['available_rule_refs']))
    parent += '\n'
    digest = hashlib.sha256(parent.encode()).hexdigest()
    scope = replace(scope, parent_skill_digest=digest)
    sources = tuple(replace(s, parent_skill_digest=digest) for s in sources)
    groups['parent_skill_digest'] = digest
    request = build((sources, scope, groups, parent))[0]
    with pytest.raises(DiagnosisContractError):
        resolve_reference(request, old_ref, reference_type='PARENT_SKILL_RULE')


def test_stale_catalog_and_grouping_hint_cannot_resolve(case):
    request = build(case)[0]
    with pytest.raises(DiagnosisContractError):
        resolve_reference(request, 'G1', reference_type='TRAJECTORY')
    payload = request.learner_payload
    payload['contexts'][0]['visible_policy'] += ' changed'
    malformed = replace(request, learner_view=_seal('V17_GROUP_DIAGNOSIS_INPUT', payload))
    with pytest.raises(DiagnosisContractError, match='stale'):
        resolve_reference(malformed, 'anything', reference_type='VISIBLE_POLICY')
