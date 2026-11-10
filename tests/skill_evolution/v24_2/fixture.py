"""Scripted ALFWorld-format executions and predetermined English model outputs.

This is an orchestration fixture, not a simulator or a measure of agent performance.
"""
import json
from pathlib import Path

from src.skill_evolution.v24_1.benchmarks.alfworld.actor.actor_prompt import render_messages
from src.skill_evolution.v24_1.benchmarks.alfworld.actor.skill_runtime import execution_protocol, inject_skill, load_skill
from src.skill_evolution.v24_2.campaign import configuration
from src.skill_evolution.v24_2.storage import save


TASKS = [f'train:fixture{i}' for i in range(1, 6)]
OPEN_FIRST = 'When the target is not visible and a closed cabinet is within reach, inspect it before leaving.'
DESTINATION = 'When holding the ready object at its requested closed destination, open it before placing the object.'
GOALS = ['put the mug on the table', 'put the apple on the table', 'put the key in the drawer',
         'put the spoon in the drawer', 'clean the plate and put it on the table']
MENUS = [
    ('open cabinet 1', 'go to countertop 1'), ('open cabinet 1', 'go to countertop 1'),
    ('go to drawer 1', 'go to cabinet 1'), ('open drawer 1', 'go to countertop 1'),
    ('clean plate 1 with sinkbasin 1', 'go to table 1'),
]
# Script at a shared opportunity followed by a side-specific continuation.
OPENINGS = ['A closed cabinet is here.', 'A closed cabinet is here.',
            'You hold the key.', 'You hold the spoon at its closed target drawer.',
            'You hold the plate at the sink.']
P_SUCCESS = (False, True, True, False, False)
Q_SUCCESS = (True, False, False, True, False)
P_ACTION = (1, 1, 0, 1, 1)
Q_ACTION = (0, 0, 1, 0, 0)


def fixture_config():
    config = configuration()
    config.update(mode='offline_fixture', batches=[TASKS], task_items={t: {'id': t} for t in TASKS},
                  retry_delay_seconds=0, actor_max_workers=2)
    return config


def actor(task, skill_file, directory, config):
    i = TASKS.index(task)
    parent_or_candidate = load_skill(skill_file)
    skill = parent_or_candidate['text']
    child = directory.parents[2].name == 'candidate_runs'
    if child:
        assert OPEN_FIRST in skill and DESTINATION in skill
    success = (Q_SUCCESS if child else P_SUCCESS)[i]
    choice = (Q_ACTION if child else P_ACTION)[i]
    goal = GOALS[i]
    initial = OPENINGS[i] + '\nYour task is to: ' + goal
    protocol = execution_protocol(config['max_steps'], config['actor_skill_injection'],
                                  output_format=config['actor_output_format'],
                                  retry_invalid_actions=config['actor_retry_invalid_actions'],
                                  action_feedback=config['actor_action_feedback'])
    record = dict(task=config['task_items'][task], run_id=('q-' if child else 'p-')+task, skill=parent_or_candidate,
                  split='train', model=config['actor_model'], gamefile='fixture/'+task, versions={'fixture': '1'},
                  backend_id='offline_fixture', implementation={'files': ['scripted_actor']}, protocol=protocol,
                  request_policy={'max_attempts': config['actor_request_attempts'], 'strict_response': True},
                  initial_observation=initial, initial_admissible_commands=list(MENUS[i]), steps=[], won=success)
    steps = [(list(MENUS[i]), MENUS[i][choice], [
        ('The open cabinet contains a mug.' if child else 'The countertop is empty.'),
        ('The cabinet is empty.' if child else 'There is an apple here.'),
        ('The key is still held.' if child else 'The requested drawer is open.'),
        ('The drawer is open.' if child else 'You have moved away from the drawer.'),
        ('The plate is now clean.' if child else 'You reach the table with the unwashed plate.'),
    ][i])]
    if success and i in (0, 1):
        obj = 'mug' if i == 0 else 'apple'
        source = 'cabinet' if i == 0 else 'countertop'
        steps.extend([([a], a, obs) for a, obs in [
            (f'take {obj} 1 from {source} 1', f'You hold the {obj}.'),
            ('go to table 1', 'You reach the table.'),
            (f'put {obj} 1 in/on table 1', 'You place the requested object.')]])
    elif success:
        a = 'put ' + ('spoon' if i == 3 else 'key') + ' 1 in/on drawer 1'
        steps.append(([a], a, 'You place the requested object.'))
    elif i == 0:
        # A genuine full-length, nonterminal 50-step trace exercises step_limit.
        steps += [(['look'], 'look', 'The countertop is empty.')] * 49
    else:
        steps.append((['look'], 'look', 'The episode ends without the requested placement.'))
    history, observation = [], initial
    for number, (menu, action, after) in enumerate(steps, 1):
        messages = render_messages(observation, menu, goal, history, **{
            k: protocol[k] for k in ('initial_template', 'history_template', 'system_prompt')})
        inject_skill(messages, skill, config['actor_skill_injection'])
        final = number == len(steps)
        content = f'<action>{action}</action>'
        record['steps'].append(dict(step=number, phase='executed', admissible_commands=menu, messages=messages,
                                    action=action, observation=after, won=success and final,
                                    done=final and (success or i != 0), action_in_admissible_commands=True,
                                    model_response={'finish_reason': 'stop', 'content': content}, fallback=None,
                                    transport_attempts=[{'attempt': 1, 'messages': messages,
                                                         'feedback_from_attempt': None}]))
        history.append(dict(observation=observation, action=action))
        observation = after
    record['status'] = 'success' if success else 'step_limit' if i == 0 else 'environment_ended'
    path = directory / 'trajectory.json'
    save(path, record)
    return path


def generate(name, messages, directory, call):
    payload = json.loads(messages[1]['content'])
    if name == 'diagnosis':
        value = dict(decision='revise', reason='Parent bypassed a cabinet and a closed destination.',
                     plan=dict(goal='Use observable opportunities to search or finish delivery.', updates=[
                         dict(id='u1', text='Inspect reachable closed cabinets before leaving when searching.',
                              basis=['P1:1', 'P2:1']),
                         dict(id='u2', text=DESTINATION, basis=['P4:1'])]))
    elif name == 'preconditioner':
        assert [r['ref'] for r in payload['runs']] == ['P1', 'P2', 'P4']
        value = dict(adjustments=[
            dict(target='u1', action='REPLACE', text=OPEN_FIRST,
                 reason='P1:1 supports inspection; P2:1 shows why moving elsewhere can still be useful.'),
            dict(target='u2', action='KEEP', text=None, reason='Makes the closed-destination prerequisite explicit.')])
    elif name == 'editor':
        assert set(payload) == {'parent', 'plan'}
        edits = []
        for update, prefix in zip(payload['plan']['updates'], ('2. **Systematic exploration', '5. **Direct delivery')):
            old = next(line for line in payload['parent'].splitlines() if line.startswith(prefix))
            patch = '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-' + old + '\n+' + old + ' ' + update['text'] + '\n'
            edits.append(dict(update_id=update['id'], patch=patch, reason='Add the condition to the relevant rule.'))
        value = dict(edits=edits)
    else:
        assert name == 'replay'
        assert [p['task_id'] for p in payload['pairs']] == TASKS[:4]
        value = dict(entries=[dict(knowledge=[
            dict(task_id=TASKS[0], update_id='u1', text='Q1:1 opened the cabinet and found the mug. Parent left and exhausted its steps; failure became success.'),
            dict(task_id=TASKS[1], update_id='u1', text='Q2:1 opened an empty cabinet where Parent went directly to the apple. Success became failure.'),
            dict(task_id=TASKS[2], update_id=None, text='The key was delivered by Parent. Candidate moved to another location and failed; the observed move does not distinguish an edit.'),
            dict(task_id=TASKS[3], update_id='u2', text='Candidate opened the requested drawer before placing the spoon, unlike Parent, which left. Failure became success.')])])
    return dict(finish_reason='stop', content=json.dumps(value))
