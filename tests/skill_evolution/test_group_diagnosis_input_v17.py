from dataclasses import replace
import hashlib

import pytest

from src.skill_evolution.experience_cards_v17 import build_experience_cards
from src.skill_evolution.experience_grouping_contract_v17 import (
    EvolutionExperienceRef, GroupingContractError, GroupingScope, bind_grouping_result,
)
from src.skill_evolution.experience_grouping_v17 import prepare_grouping_request
from src.skill_evolution.group_diagnosis_input_v17 import build_group_diagnosis_inputs
from src.skill_evolution.information_boundary_v15 import BoundaryError, _seal, unpack
from tests.skill_evolution.test_experience_cards_v17 import captured


@pytest.fixture
def case():
    parent = '# Skill\n保留用户授权范围。\n'
    digest = hashlib.sha256(parent.encode()).hexdigest()
    refs = tuple(EvolutionExperienceRef(f'T{i}', f'C{i}', f'R{i}') for i in (1, 2, 3))
    scope = GroupingScope('round-1', digest, refs)
    sources = tuple(replace(captured(ref, policy=f'Policy {i}', success=i == 1),
                            parent_skill_digest=digest) for i, ref in enumerate(refs, 1))
    groups = [{'group_id': 'G1', 'decision_problem': 'When to act?', 'members': ['T1', 'T2'],
               'shared_basis': 'Observed authorization expressions.', 'important_differences': []},
              {'group_id': 'G2', 'decision_problem': 'Other decision', 'members': ['T3'],
               'shared_basis': 'Singleton.', 'important_differences': []}]
    batch = build_experience_cards(sources, scope=scope)
    result = bind_grouping_result(batch.payload, {'groups': groups}, scope=scope)
    return sources, scope, result, parent


def build(case):
    sources, scope, result, parent = case
    return build_group_diagnosis_inputs(sources, scope=scope, grouping_result=result, parent_skill=parent)


def test_group_local_full_evidence_and_singleton(case):
    sources, scope, result, parent = case
    requests = build(case)
    assert len(requests) == 2
    all_refs = []
    for request, group in zip(requests, result['groups']):
        payload = request.learner_payload
        assert payload['current_skill'] == parent
        assert payload['grouping_hint']['origin'] == 'LEARNER_INFERRED_GROUPING'
        assert [e['task_ref'] for e in payload['experiences']] == group['members']
        assert len(payload['contexts']) == len(group['members'])
        assert len(payload['available_supervision_refs']) == len(group['members'])
        for experience in payload['experiences']:
            source = next(s for s in sources if s.ref.task_ref == experience['task_ref'])
            observed = unpack(source.experience, 'TRAJECTORY_DERIVED')
            restored = [{k: v for k, v in event.items() if k != 'evidence_ref'}
                        for event in experience['events']]
            assert restored == observed['trajectory']
            assert experience['supervision']['success'] == observed['supervision']['success']
            assert experience['supervision']['compliant'] == observed['supervision']['compliant']
            for event in experience['events']:
                ref = payload['available_evidence_refs'][event['evidence_ref']]
                assert ref == {'task_ref': experience['task_ref'],
                               'trajectory_ref': experience['trajectory_ref'],
                               'rollout_index': 1, 'step': event['step']}
                all_refs.append(event['evidence_ref'])
        assert request.provenance['round_id'] == scope.round_id
    assert len(all_refs) == len(set(all_refs)) == 15
    assert 'Policy 3' not in str(requests[0].learner_payload)
    assert 'Policy 1' not in str(requests[1].learner_payload)
    payload['experiences'].clear()
    assert len(requests[1].learner_payload['experiences']) == 1


def test_grouper_aliases_remain_resolvable_and_group_local(case):
    sources, scope, result, parent = case
    result['alias_to_source'] = prepare_grouping_request(
        build_experience_cards(sources, scope=scope), scope=scope)['alias_to_source']
    result['groups'][0]['shared_basis'] = 'Compare opaque aliases, not source IDs.'
    request = build(case)[0]
    payload = request.learner_payload
    bindings = request.provenance['experience_bindings']
    assert len(bindings) == 2
    assert 'alias_to_source' not in payload
    for binding, experience in zip(bindings, payload['experiences']):
        assert result['alias_to_source']['task_ref'][experience['task_ref']] == binding['source']['task_ref']
    assert payload['grouping_hint']['members'] == [e['task_ref'] for e in payload['experiences']]


@pytest.mark.parametrize('field,value', [
    ('round_id', 'old'), ('parent_skill_digest', 'other'), ('origin', 'ORACLE'),
    ('schema_version', 'unknown'), ('experience_refs', []), ('monitor_role', 'guard'),
])
def test_reject_wrong_result_binding(case, field, value):
    case[2][field] = value
    with pytest.raises(GroupingContractError):
        build(case)


@pytest.mark.parametrize('members', [['T1'], ['T1', 'T1', 'T2'], ['T1', 'MONITOR']])
def test_reject_invalid_partition(case, members):
    case[2]['groups'][0]['members'] = members
    with pytest.raises(GroupingContractError):
        build(case)


def test_reject_wrong_parent_and_bad_alias_map(case):
    sources, scope, result, parent = case
    with pytest.raises(GroupingContractError, match='digest'):
        build_group_diagnosis_inputs(sources, scope=scope, grouping_result=result, parent_skill=parent + ' ')
    result['alias_to_source'] = {}
    with pytest.raises(GroupingContractError, match='alias'):
        build(case)


def test_reject_monitor_source_and_bad_supervision(case):
    sources, scope, result, parent = case
    monitor = replace(sources[0], ref=EvolutionExperienceRef('MONITOR', 'C1', 'R1'))
    with pytest.raises(GroupingContractError):
        build(( (monitor, *sources[1:]), scope, result, parent))
    observed = unpack(sources[0].experience, 'TRAJECTORY_DERIVED')
    observed['supervision']['reason'] = 'HIDDEN EVALUATOR EXPLANATION'
    bad = replace(sources[0], experience=_seal('TRAJECTORY_DERIVED', observed))
    with pytest.raises(GroupingContractError, match='Level-0'):
        build(((bad, *sources[1:]), scope, result, parent))


def test_seal_tamper_rejected(case):
    request = build(case)[0]
    request = replace(request, learner_view=replace(request.learner_view, payload='{}'))
    with pytest.raises(BoundaryError):
        _ = request.learner_payload


def test_group_explanations_not_evidence(case):
    case[2]['groups'][0]['shared_basis'] = 'UNVERIFIED_HYPOTHESIS'
    payload = build(case)[0].learner_payload
    assert 'UNVERIFIED_HYPOTHESIS' not in str(payload['available_evidence_refs'])
    assert 'UNVERIFIED_HYPOTHESIS' not in str(payload['experiences'])
    assert payload['grouping_hint']['shared_basis'] == 'UNVERIFIED_HYPOTHESIS'
