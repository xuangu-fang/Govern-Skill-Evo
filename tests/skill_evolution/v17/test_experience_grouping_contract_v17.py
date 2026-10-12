import copy

import pytest

from src.skill_evolution.v17.experience_grouping_contract_v17 import EvolutionExperienceRef, GroupingContractError, GroupingScope, bind_grouping_result, validate_grouping_input, validate_grouping_output


@pytest.fixture
def case():
    scope = GroupingScope('round-1', 'parent-digest', tuple(
        EvolutionExperienceRef(f'T{i}', 'C1', f'R{i}') for i in (1, 2)))
    payload = {
        'contexts': [{'context_ref': 'C1', 'visible_policy': 'Ask before changes.',
                      'public_tools': [{'type': 'function', 'function': {
                          'name': 'change', 'description': 'Change booking.',
                          'parameters': {'type': 'object'}}}]}],
        'cards': [{'task_ref': ref.task_ref, 'context_ref': ref.context_ref,
                   'trajectory_ref': ref.trajectory_ref, 'events': [
                       {'step': 1, 'actor': 'user', 'event_type': 'message',
                        'content': 'Show the price first.'},
                       {'step': 2, 'actor': 'assistant', 'event_type': 'tool_call',
                        'tool_name': 'change', 'arguments': {'booking': 'B1'}},
                       {'step': 3, 'actor': 'tool', 'event_type': 'tool_result',
                        'tool_name': 'change', 'content': {'success': True}},
                   ]} for ref in scope.experiences],
    }
    output = {'groups': [{'group_id': 'G1', 'decision_problem': 'Authorization before changes',
                          'members': ['T1', 'T2'], 'shared_basis': 'Both perform changes.',
                          'important_differences': []}]}
    return scope, payload, output


def test_valid_partition_and_runtime_binding(case):
    scope, payload, output = case
    result = bind_grouping_result(payload, output, scope=scope)
    assert result['round_id'] == 'round-1'
    assert result['origin'] == 'LEARNER_INFERRED_GROUPING'
    output['groups'][0]['members'].clear()
    assert result['groups'][0]['members'] == ['T1', 'T2']


def test_singletons(case):
    scope, payload, output = case
    group = output['groups'][0]
    output['groups'] = [{**group, 'group_id': f'G{i}', 'members': [f'T{i}']}
                        for i in (1, 2)]
    bind_grouping_result(payload, output, scope=scope)


@pytest.mark.parametrize('field', [
    'family', 'hidden_mapping', 'expected_action', 'oracle_path',
    'evaluator_truth', 'success', 'compliant', 'quadrant', 'monitor_role',
])
@pytest.mark.parametrize('location', ['root', 'card', 'event', 'context'])
def test_forbidden_metadata(case, field, location):
    scope, payload, _ = case
    target = {'root': payload, 'card': payload['cards'][0],
              'event': payload['cards'][0]['events'][0],
              'context': payload['contexts'][0]}[location]
    target[field] = 'private'
    with pytest.raises(GroupingContractError):
        validate_grouping_input(payload, scope=scope)


@pytest.mark.parametrize('mutation', [
    lambda p: p['cards'].pop(),
    lambda p: p['cards'].append(copy.deepcopy(p['cards'][0])),
    lambda p: p['cards'][0].update(task_ref='MONITOR'),
    lambda p: p['cards'][0].update(trajectory_ref='old-round-trajectory'),
    lambda p: p['cards'][0].update(context_ref='other-policy'),
    lambda p: p['cards'][0]['events'][1].update(step=1),
    lambda p: p['cards'][0]['events'][1].update(tool_name='private_tool'),
    lambda p: p['cards'][0]['events'][1].update(actor='tool'),
    lambda p: p['cards'][0]['events'][1].update(arguments=[]),
    lambda p: p['cards'][0]['events'][0].update(step=True),
])
def test_input_provenance_and_structure(case, mutation):
    scope, payload, _ = case
    mutation(payload)
    with pytest.raises(GroupingContractError):
        validate_grouping_input(payload, scope=scope)


@pytest.mark.parametrize('members', [[], ['T1'], ['T1', 'T1', 'T2'], ['T1', 'UNKNOWN']])
def test_bad_members(case, members):
    _, _, output = case
    output['groups'][0]['members'] = members
    with pytest.raises(GroupingContractError):
        validate_grouping_output(output, task_refs=('T1', 'T2'))


@pytest.mark.parametrize('mutation', [
    lambda o: o.update(round_id='model-supplied'),
    lambda o: o.update(groups=[]),
    lambda o: o['groups'][0].update(repair_operator='ADD'),
    lambda o: o['groups'][0].update(decision_problem=' '),
    lambda o: o['groups'][0].update(important_differences='not a list'),
    lambda o: o['groups'].append(copy.deepcopy(o['groups'][0])),
])
def test_bad_output(case, mutation):
    _, _, output = case
    mutation(output)
    with pytest.raises(GroupingContractError):
        validate_grouping_output(output, task_refs=('T1', 'T2'))


def test_cross_context_group_is_allowed(case):
    scope, payload, output = case
    second = copy.deepcopy(payload['contexts'][0])
    second.update(context_ref='C2', visible_policy='Different public policy.')
    payload['contexts'].append(second)
    payload['cards'][1]['context_ref'] = 'C2'
    scope = GroupingScope(scope.round_id, scope.parent_skill_digest,
                          (scope.experiences[0], EvolutionExperienceRef('T2', 'C2', 'R2')))
    bind_grouping_result(payload, output, scope=scope)


def test_empty_or_duplicate_manifest_is_rejected(case):
    scope, payload, _ = case
    for refs in ((), (scope.experiences[0], scope.experiences[0])):
        with pytest.raises(GroupingContractError):
            validate_grouping_input(payload, scope=GroupingScope('r', 's', refs))
