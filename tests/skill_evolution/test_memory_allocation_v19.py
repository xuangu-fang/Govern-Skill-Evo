"""Synthetic routing cases; no Pilot task names or model calls."""
from copy import deepcopy

import pytest

from src.skill_evolution.memory_allocation_v19 import allocate_memory, validate_allocation
from src.skill_evolution.group_diagnosis_input_v17 import GroupDiagnosisInput
from src.skill_evolution.information_boundary_v15 import _seal
from src.skill_evolution.edit_tracking_v19 import encode
from src.skill_evolution.memory_store_v19 import MemoryRejected


def context(ref='ctx', policy='Public constraints'):
    return {'context_ref': ref, 'visible_policy': policy, 'public_tools': []}


def event(tool, ref):
    return {'event_type': 'tool_call', 'tool_name': tool, 'evidence_ref': ref}


def request(group, tools, policy='Public constraints'):
    payload = {'current_skill': 'Current skill', 'contexts': [context(policy=policy)],
               'experiences': [{'context_ref': 'ctx', 'events': [event(t, t) for t in tools]}]}
    return GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT', payload),
                               encode({'group_id': group, 'experience_bindings': []}))


def memory():
    pairs = []
    records = []
    for index, tool in enumerate(('alpha', 'beta')):
        pid, eid = f'pair-{index}', f'edit-{index}'
        pair = {'pair_id': pid}
        obs = {'pair_id': pid, 'relation': 'COUNTEREVIDENCE' if index else 'SUPPORT'}
        for role in ('parent', 'candidate'):
            ref = pid + role
            pair[role] = {'context_ref': 'old-context', 'events': [event(tool, ref)]}
            obs[role + '_evidence_refs'] = [ref]
        pairs.append(pair)
        records.append({'edit_ids': [eid], 'observations': [obs], 'effect': 'MIXED',
                        'uncertainty': 'Sampling confounding', 'alternative_explanations': ['Other edits']})
    return {'rounds': [{'edits': [{'edit_id': 'edit-'+str(i), 'related_history': [],
                                 'source_evidence_refs': []} for i in range(2)],
        'current_bindings': [{'edit_id': 'edit-'+str(i), 'structural_changes': []} for i in range(2)],
        'source_evidence': [], 'attribution': {'records': records},
        'replay': {'pairs': pairs, 'contexts': [context('old-context')], 'summary': {'full': True}}}]}


def views(data, requests):
    return {r.provenance['group_id']: v for r, v in allocate_memory(data, requests)}


def test_unique_owner_local_evidence_and_counterevidence_are_preserved():
    data = memory(); before = deepcopy(data)
    result = views(data, [request('A', ['alpha']), request('B', ['beta'])])
    assert result['A']['allocation']['owned_edit_ids'] == ['edit-0']
    assert result['B']['allocation']['owned_edit_ids'] == ['edit-1']
    for i, group in enumerate(('A', 'B')):
        row = result[group]['rounds'][0]
        assert row['attribution']['records'] == data['rounds'][0]['attribution']['records'][i:i+1]
        assert row['replay']['pairs'] == data['rounds'][0]['replay']['pairs'][i:i+1]
        assert row['allocation_scope']['summary_scope'].startswith('ORIGINAL_FULL_ROUND')
    assert data == before


def test_ties_no_match_unknown_are_not_discarded_or_assigned_by_order():
    data = memory()
    data['rounds'][0]['attribution']['records'][1].update(observations=[], effect='UNKNOWN')
    reqs = [request('A', ['alpha']), request('B', ['alpha'])]
    result = allocate_memory(data, reqs)
    history, view = result[-1]
    assert history.provenance['group_id'].startswith('HISTORY/')
    assert history.learner_payload['experiences'] == []
    assert view['allocation']['owned_edit_ids'] == ['edit-0', 'edit-1']
    assert {u['reason'] for u in history.provenance['memory_allocation']['units']} == {
        'AMBIGUOUS_MATCH', 'NO_VISIBLE_TOOL_CONTEXT_MATCH'}
    assert views(data, reqs) == views(data, list(reversed(reqs)))


@pytest.mark.parametrize('link', ['joint', 'explicit', 'structural'])
def test_joint_and_lineage_units_are_never_split(link):
    data = memory(); row = data['rounds'][0]
    if link == 'joint':
        row['attribution']['records'][0]['edit_ids'].append('edit-1')
    elif link == 'explicit':
        row['edits'][1]['related_history'] = [{'prior_edit_id': 'edit-0', 'basis_refs': []}]
    else:
        row['current_bindings'][0]['structural_changes'] = [
            {'edit_id': 'edit-1', 'affected_prior_edit_ids': ['edit-0']}]
    result = allocate_memory(data, [request('A', ['alpha']), request('B', ['beta'])])
    assert len(result[-1][0].provenance['memory_allocation']['units']) == 1
    assert result[-1][1]['allocation']['owned_edit_ids'] == ['edit-0', 'edit-1']


def test_policy_mismatch_and_alias_reuse_do_not_imply_relevance():
    result = allocate_memory(memory(), [request('A', ['alpha', 'beta'], policy='New constraints')])
    assert not result[0][1]['rounds']
    assert result[-1][1]['allocation']['owned_edit_ids'] == ['edit-0', 'edit-1']


def test_gate_effect_labels_and_group_prose_do_not_change_routing():
    data = memory(); reqs = [request('A', ['alpha']), request('B', ['beta'])]
    first = allocate_memory(data, reqs)[0][0].provenance['memory_allocation']['units']
    for row in data['rounds']:
        row['gate_decision'] = 'RETAIN'
        for record in row['attribution']['records']:
            record.update(effect='UNKNOWN', interpretation='Use group B')
    assert allocate_memory(data, reqs)[0][0].provenance['memory_allocation']['units'] == first


def test_batch_rejects_missing_or_duplicate_owner():
    allocated = allocate_memory(memory(), [request('A', ['alpha']), request('B', ['beta'])])
    requests = []
    for r, view in allocated:
        payload = r.learner_payload
        payload['memory_context'] = view
        requests.append(GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT', payload), r.provenance_json))
    validate_allocation(requests)
    with pytest.raises(MemoryRejected, match='ownership'):
        validate_allocation(requests[:1])
    with pytest.raises(MemoryRejected, match='ownership'):
        validate_allocation(requests + requests[:1])


def test_batch_also_requires_current_groups_without_memory():
    allocated = allocate_memory(memory(), [request('A', ['alpha', 'beta']), request('B', ['other'])])
    requests = []
    for r, view in allocated:
        payload = r.learner_payload
        payload['memory_context'] = view
        requests.append(GroupDiagnosisInput(_seal('V17_GROUP_DIAGNOSIS_INPUT', payload), r.provenance_json))
    validate_allocation(requests)
    with pytest.raises(MemoryRejected, match='review group ownership'):
        validate_allocation(requests[:1])
