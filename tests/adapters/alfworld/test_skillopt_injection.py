"""Exact parity with local SkillOpt source, and strict per-request evidence checks."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import List, Dict, Any, Tuple

import pytest

from src.adapters.alfworld import skill_runtime as rt
from src.adapters.alfworld.run_task_upstream import build_messages
from src.skill_evolution.v23.facts import build_facts
from tests.skill_evolution.v23.test_grouping import record

UPSTREAM = Path(__file__).resolve().parents[3]/'external/SkillOpt/skillopt/envs/alfworld'


def reference_functions():
    if not UPSTREAM.is_dir(): pytest.skip('Optional local SkillOpt checkout unavailable')
    wrapper = next(n for n in ast.parse((UPSTREAM/'rollout.py').read_text()).body
                   if isinstance(n, ast.FunctionDef) and n.name == '_build_skill_prompt')
    manager = next(n for n in ast.parse((UPSTREAM/'vendor/env_manager.py').read_text()).body
                   if isinstance(n, ast.ClassDef) and n.name == 'AlfWorldEnvironmentManager')
    render = next(n for n in manager.body if isinstance(n, ast.FunctionDef) and n.name == 'build_text_obs')
    memory = next(n for n in ast.parse((UPSTREAM/'vendor/memory.py').read_text()).body
                  if isinstance(n, ast.ClassDef) and n.name == 'SimpleMemory')
    memory.bases = []
    namespace = {'List': List, 'Dict': Dict, 'Any': Any, 'Tuple': Tuple,
                 'ALFWORLD_TEMPLATE_NO_HIS': (UPSTREAM/'prompts/rollout_no_history.md').read_text(),
                 'ALFWORLD_TEMPLATE': (UPSTREAM/'prompts/rollout_with_history.md').read_text()}
    exec(compile(ast.Module(body=[wrapper, memory, render], type_ignores=[]), str(UPSTREAM), 'exec'), namespace)
    return namespace


@pytest.mark.parametrize('history_length', [0, 1, 2, 4])
@pytest.mark.parametrize('skill_text', ['# Skill\nUse visible actions.\n', 'Exact whitespace.\r\n'])
def test_full_messages_match_skillopt_renderer(history_length, skill_text):
    ref = reference_functions()
    history = [{'observation': f"before '{i}'\nline two", 'action': 'look'} for i in range(history_length)]
    mem = ref['SimpleMemory'](); mem.reset(1)
    for h in history: mem.store({'text_obs': [h['observation']], 'action': [h['action']]})
    manager = SimpleNamespace(memory=mem, tasks=['inspect the room.'],
                              config=SimpleNamespace(env=SimpleNamespace(history_length=2)))
    observation = 'A room. Your task is to: inspect the room.'
    menus = ['help', 'look', 'Help', 'look']
    user = ref['build_text_obs'](manager, [observation], [menus], init=not history)[0]
    expected_user = ref['_build_skill_prompt'](skill_text) + '\n' + user
    actual = rt.build_skill_messages(observation, menus, manager.tasks[0], history,
                                    {'mode': 'fixed', 'text': skill_text}, rt.SKILLOPT_INJECTION)
    assert actual == [{'role': 'system', 'content': 'You are an expert agent operating in the ALFRED Embodied Environment.'},
                      {'role': 'user', 'content': expected_user}]


def aligned_record():
    r = record(parent='# Initial\nUse visible actions.\n')
    r['protocol'] = rt.execution_protocol(2, rt.SKILLOPT_INJECTION)
    observation, history = r['initial_observation'], []
    for event in r['steps']:
        event['messages'] = rt.build_skill_messages(observation, event['admissible_commands'], r['goal'], history,
                                                    r['skill'], rt.SKILLOPT_INJECTION)
        history.append({'observation': observation, 'action': event['action']})
        observation = event['observation']
    return r


def test_facts_accept_exact_protocol_and_reject_moved_or_changed_skill():
    r = aligned_record()
    assert build_facts([r])['facts']['parent'] == r['skill']['text']
    for mutation in ('system', 'newline', 'metadata'):
        bad = deepcopy(r)
        if mutation == 'system':
            bad['steps'][0]['messages'] = rt.build_skill_messages(r['initial_observation'],
                r['initial_admissible_commands'], r['goal'], [], r['skill'])
        elif mutation == 'newline': bad['steps'][0]['messages'][1]['content'] = bad['steps'][0]['messages'][1]['content'].lstrip()
        else: bad['protocol']['skill_prefix'] += 'changed'
        with pytest.raises(ValueError): build_facts([bad])


def test_legacy_default_and_no_skill_are_unchanged():
    args = ('now', ['look'], 'goal', [])
    assert rt.build_skill_messages(*args, rt.load_skill(), rt.SKILLOPT_INJECTION) == build_messages(*args)
    assert rt.execution_protocol(50)['protocol_id'] == rt.PROTOCOL
    with pytest.raises(ValueError): rt.execution_protocol(50, 'unknown')
