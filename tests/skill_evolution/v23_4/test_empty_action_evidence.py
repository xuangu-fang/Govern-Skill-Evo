"""Keep failed empty commands as observed evidence, including Memory reloads."""
from copy import deepcopy
import pytest

from src.skill_evolution.v23 import facts, memory, editor
from tests.skill_evolution.v23.test_grouping import record


def empty_command_record():
    value = record(status='step_limit', menus=[['look']])
    value['protocol']['max_steps'] = 1
    # The only message was built before the action and is unaffected by its value.
    value['steps'][0].update(action='', action_in_admissible_commands=False,
                             observation='Nothing happens.')
    return value


def test_empty_command_survives_facts_and_memory_roundtrip(tmp_path):
    value = empty_command_record(); before = deepcopy(value)
    built = facts.build_facts([value]); f = built['facts']; run = f['runs'][0]
    assert value == before and run['steps'][0]['action'] == ''
    assert run['steps'][0]['feedback']['action_in_admissible_commands'] is False
    assert run['outcome']['success'] is False
    memory.validate_run(run, f['command_sets'])
    candidate = 'Use visible actions.\n'
    payload = {'parent': None, 'diff': editor.actual_diff(None, candidate),
               'plan': {'goal': 'Avoid ineffective commands.', 'updates': [{'id': 'u1', 'text': candidate}], 'checks': []},
               'command_sets': f['command_sets'], 'runs': [run, {**deepcopy(run), 'ref': 'Q1'}],
               'pairs': [{'parent': 'P1', 'candidate': 'Q1'}], 'memory': memory.empty_memory()}
    payload['runs'][1]['steps'][0]['step'] = 'Q1:1'
    result = {'entries': [{'revises': [], 'knowledge': 'Both synthetic runs executed an empty command without progress.',
                           'evidence': ['diff', 'P1:1', 'Q1:1']}]}
    context = {'payload': payload, 'execution_context': {'background': built['background']}}
    memory.commit_memory(tmp_path, context_id='empty_action_test', context=context, result=result)
    loaded = memory.load_memory(tmp_path)
    assert loaded['sources']['empty_action_test/P1']['run']['steps'][0]['action'] == ''


@pytest.mark.parametrize('action', [None, 0, [], {}])
def test_nonstring_actions_still_rejected(action):
    value = empty_command_record(); value['steps'][0]['action'] = action
    with pytest.raises(ValueError, match='Invalid executed action'):
        facts.build_facts([value])
    built = facts.build_facts([empty_command_record()])
    run = built['facts']['runs'][0]; run['steps'][0]['action'] = action
    with pytest.raises(ValueError, match='Invalid action'):
        memory.validate_run(run, built['facts']['command_sets'])
