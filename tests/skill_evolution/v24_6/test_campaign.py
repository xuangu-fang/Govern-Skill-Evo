import json
from collections import Counter
from copy import deepcopy
from itertools import product
import socket
import subprocess

import pytest

from src.skill_evolution.v24_1.benchmarks.alfworld.actor.actor_prompt import render_messages
from src.skill_evolution.v24_1.benchmarks.alfworld.actor.skill_runtime import inject_skill
from src.skill_evolution.v24_2.storage import read, save
from src.skill_evolution.v24_6 import campaign, gate, system_prompt
from tests.skill_evolution.v24_2 import fixture


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Unexpected network, subprocess or real Actor call')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(campaign.ALFWorldAdapter, 'actor_task', staticmethod(forbidden))


@pytest.mark.parametrize(('parent_won', 'child_won', 'delta', 'expected'), [
    (True, True, 10, 'efficiency_gain'), (True, True, -10, 'efficiency_loss'),
    (True, True, 9, None), (True, True, -9, None), (True, True, 0, None),
    (False, False, 25, None), (False, True, -20, 'gain'), (True, False, 30, 'loss'),
])
def test_event_direction(parent_won, child_won, delta, expected):
    assert gate.event_direction(parent_won, child_won, delta) == expected


@pytest.mark.parametrize(('g', 'l', 'faster', 'slower'), list(product((0, 1), repeat=4)))
def test_gate_precedence(g, l, faster, slower):
    # Row = completion evidence (none, loss, gain, both);
    # column = efficiency evidence (none, slower, faster, both).
    expected = [
        ['Defer', 'Defer', 'Retain', 'Defer'],
        ['Reject'] * 4,
        ['Retain'] * 4,
        ['Defer'] * 4,
    ][2 * g + l][2 * faster + slower]
    assert gate.decision(Counter(gain=g, loss=l, efficiency_gain=faster, efficiency_loss=slower)) == expected


def scripted_success(task, skill_file, directory, config):
    # Reuse the fixture's frozen Actor envelope. Replace the actions with a
    # scripted search followed by delivery, rendering each actual request.
    path = fixture.actor(task, skill_file, directory, config)
    record = read(path)
    child = directory.parents[2].name == 'candidate_runs'
    i = fixture.TASKS.index(task)
    lengths = (5, 14, 5, 5, 4) if child else (15, 4, 14, 15, 4)
    steps = lengths[i]
    observation = record['initial_observation']
    goal = fixture.GOALS[i]
    protocol = record['protocol']
    history = []
    template = record['steps'][0]
    record.update(steps=[], won=True, status='success')
    for n in range(1, steps + 1):
        menu = record['initial_admissible_commands'] if n == 1 else ['look']
        final = n == steps
        if final:
            menu = ['put object 1 in/on drawer 1']
        action = menu[0]
        messages = render_messages(observation, menu, goal, history, **{
            k: protocol[k] for k in ('initial_template', 'history_template', 'system_prompt')})
        inject_skill(messages, record['skill']['text'], config['actor_skill_injection'])
        feedback = 'Goal reached.' if final else 'Searching.'
        step = deepcopy(template)
        step.update(step=n, messages=messages, admissible_commands=menu, action=action,
                    observation=feedback, won=final, done=final)
        step['model_response']['content'] = f'<action>{action}</action>'
        step['transport_attempts'][0]['messages'] = messages
        record['steps'].append(step)
        history.append(dict(observation=observation, action=action))
        observation = feedback
    save(path, record)
    return path


def fixture_config():
    return dict(fixture.fixture_config(), method=campaign.VERSION)


def test_efficiency_round_and_resume(tmp_path):
    cfg = fixture_config()
    # One new task in round two to exercise actual inter-round handoff.
    extra = 'train:next'
    cfg['batches'].append([extra])
    cfg['task_items'][extra] = {'id': extra}
    campaign.prepare(tmp_path, cfg)
    calls = []
    def generate(name, messages, slot, call):
        calls.append(name)
        assert messages[0]['content'] == system_prompt(name)
        if name != 'replay':
            return fixture.generate(name, messages, slot, call)
        payload = json.loads(messages[1]['content'])
        pairs = payload['pairs']
        assert [(p['task_id'], p['steps_saved'], p['direction']) for p in pairs] == [
            (fixture.TASKS[0], 10, 'efficiency_gain'), (fixture.TASKS[1], -10, 'efficiency_loss'),
            (fixture.TASKS[3], 10, 'efficiency_gain')]
        assert [p['candidate'] for p in pairs] == ['Q1', 'Q2', 'Q4']
        for run in payload['runs']:
            assert run['initial']['commands_ref'] in payload['command_sets']
            assert run['steps'][-1]['step'].startswith(run['ref'] + ':')
        events = [dict(task_id=p['task_id'], update_id=uid,
                       text=f"Recorded decisions at {p['parent']}:1 and {p['candidate']}:1.")
                  for p, uid in zip(pairs, ['u1', 'u2', None])]
        return dict(finish_reason='stop', content=json.dumps(dict(entries=[dict(knowledge=events)])))

    def interrupt(name, *args):
        if name == 'replay':
            raise RuntimeError('offline interruption')
        return generate(name, *args)

    before = campaign.current(tmp_path)
    with pytest.raises(RuntimeError, match='offline interruption'):
        campaign.run_round(tmp_path, generate=interrupt, actor=scripted_success)
    assert campaign.current(tmp_path) == before

    def forbidden(*args):
        raise AssertionError('Completed episode executed twice')
    state = campaign.run_round(tmp_path, generate=generate, actor=forbidden)
    assert calls == ['diagnosis', 'preconditioner', 'editor', 'replay']
    result = read(tmp_path / 'rounds/R01/gate.json')
    assert result['decisions'] == [
        dict(update_id='u1', G=0, L=0, efficiency_gain=1, efficiency_loss=0, gate_decision='Retain'),
        dict(update_id='u2', G=0, L=0, efficiency_gain=0, efficiency_loss=1, gate_decision='Defer')]
    assert result['selected_execution_source'] is None
    assert fixture.OPEN_FIRST in state['selected'] and fixture.DESTINATION not in state['selected']
    entries = state['memory']['rounds'][0]['entries']
    assert [(e['id'], e['direction'], e['steps_saved'], e['knowledge']['update_id']) for e in entries] == [
        ('M1', 'efficiency_gain', 10, 'u1'), ('M2', 'efficiency_loss', -10, 'u2'),
        ('M3', 'efficiency_gain', 10, None)]

    def next_actor(task, skill, directory, config):
        assert task == extra and skill.read_text() == state['selected']
        path = fixture.actor(fixture.TASKS[0], skill, directory, config)
        record = read(path)
        record['task'] = config['task_items'][extra]
        save(path, record)
        return path

    def next_generate(name, messages, slot, call):
        payload = json.loads(messages[1]['content'])
        if name == 'diagnosis':
            value = dict(decision='revise', reason='Review the search choice.', plan=dict(
                goal='Shorten search.', updates=[dict(id='u1', text='Inspect the cabinet.', basis=['P1:1'])]))
        else:
            assert name == 'preconditioner' and payload['memory'] == state['memory']
            value = dict(adjustments=[dict(target='u1', action='WITHDRAW', text=None,
                                           reason='M1 already supports the selected instruction.')])
        return dict(finish_reason='stop', content=json.dumps(value))
    final = campaign.run_round(tmp_path, actor=next_actor, generate=next_generate)
    assert final['outcome'] == 'all_withdrawn' and final['memory'] == state['memory']
    assert final['selected'] == (tmp_path / 'final_skill.md').read_text() == state['selected']
    assert campaign.run_round(tmp_path) == final


def test_flip_regression_and_invalid_associations(tmp_path):
    campaign.prepare(tmp_path, fixture_config())
    def generate(name, messages, slot, call):
        response = fixture.generate(name, messages, slot, call)
        if name == 'replay':
            parsed = json.loads(response['content'])
            for i, event in enumerate(parsed['entries'][0]['knowledge'], 1):
                event['text'] += f' See P{i}:1 and Q{i}:1.'
            response['content'] = json.dumps(parsed)
        return response
    state = campaign.run_round(tmp_path, generate=generate, actor=fixture.actor)
    entries = state['memory']['rounds'][0]['entries']
    assert [e['direction'] for e in entries] == ['gain', 'loss', 'loss', 'gain']
    rd = tmp_path / 'rounds/R01'
    assert read(rd / 'gate.json')['selection']['selected_update_ids'] == ['u2']
    payload = read(rd / 'replay/input.json')
    result = read(rd / 'replay/result.json')['parsed']
    for key, invalid in [('update_id', 'missing'), ('task_id', 'wrong'), ('text', 'Wrong task Q2:1.'),
                         ('text', 'Only P1:1 cited.')]:
        wrong = deepcopy(result)
        wrong['entries'][0]['knowledge'][0][key] = invalid
        with pytest.raises(ValueError):
            gate.knowledge(wrong, payload)
    payload['edits'][0]['patch'] = ''
    with pytest.raises(ValueError, match='Ineligible'):
        gate.knowledge(result, payload)


def test_no_eligible_pair_skips_replay(tmp_path):
    campaign.prepare(tmp_path, fixture_config())
    def both_failed(task, skill, directory, config):
        path = fixture.actor(task, skill, directory, config)
        record = read(path)
        record.update(won=False, status='environment_ended')
        record['steps'][-1].update(won=False, done=True)
        save(path, record)
        return path
    def generate(name, *args):
        assert name != 'replay'
        return fixture.generate(name, *args)
    state = campaign.run_round(tmp_path, actor=both_failed, generate=generate)
    assert state['selected_execution_source'] == 'parent'
    assert not (tmp_path / 'rounds/R01/replay').exists()
    assert state['memory']['rounds'][0]['entries'] == []
    assert all(d['gate_decision'] == 'Defer' for d in read(tmp_path / 'rounds/R01/gate.json')['decisions'])


def test_official_test_entry_rejects_incomplete_campaign(tmp_path):
    from scripts.runs.v24_2.run_v24_2_test import prepare_test
    campaign.prepare(tmp_path)
    with pytest.raises(ValueError, match='Training is incomplete'):
        prepare_test(tmp_path, campaign.ALFWorldAdapter(), version=campaign)
