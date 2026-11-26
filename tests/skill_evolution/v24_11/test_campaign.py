import json

import pytest

from src.skill_evolution.v24_2.storage import read
from src.skill_evolution.v24_11 import campaign, system_prompt
from tests.skill_evolution.v24_2 import fixture
from tests.skill_evolution.v24_6.test_campaign import scripted_success


def run(root, actor, generate):
    config = dict(fixture.fixture_config(), method=campaign.VERSION)
    campaign.prepare(root, config)
    return campaign.run_round(root, actor=actor, generate=generate)


def test_efficiency_only_skips_replay(tmp_path):
    def generate(name, *args):
        assert name != 'replay'
        return fixture.generate(name, *args)

    state = run(tmp_path, scripted_success, generate)
    rd = tmp_path / 'rounds/R01'
    audit = read(rd / 'pair_audit.json')['audit']
    assert {row['parent']['steps'] - row['candidate']['steps'] for row in audit} >= {-10, 10}
    assert not (rd / 'replay').exists()
    assert state['memory']['rounds'][0]['entries'] == []
    assert state['selected_execution_source'] == 'parent'
    assert read(rd / 'gate.json')['decisions'] == [
        dict(update_id=uid, G=0, L=0, gate_decision='Defer') for uid in ('u1', 'u2')]


@pytest.mark.parametrize(('loss_id', 'expected'), [
    ('u1', [(0, 1, 'Reject'), (1, 0, 'Retain')]),
    ('u2', [(0, 0, 'Defer'), (1, 1, 'Defer')]),
])
def test_only_attributed_flips_vote(tmp_path, loss_id, expected):
    def actor(task, *args):
        # Task 1 improves by ten steps; tasks 2-4 flip; task 5 fails twice.
        record_task = scripted_success if task == fixture.TASKS[0] else fixture.actor
        return record_task(task, *args)

    def generate(name, messages, slot, call):
        if name != 'replay':
            return fixture.generate(name, messages, slot, call)
        assert messages[0]['content'] == system_prompt('replay')
        payload = json.loads(messages[1]['content'])
        assert [pair['task_id'] for pair in payload['pairs']] == fixture.TASKS[1:4]
        assert {run['ref'] for run in payload['runs']} == {'P2', 'Q2', 'P3', 'Q3', 'P4', 'Q4'}
        descriptions = [
            "Parent completed the task. Candidate chose a different action at Q2:1 and failed.",
            "Parent completed the task. Candidate failed, and the responsible edit is unclear.",
            "Parent failed after the choice at P4:1. Candidate completed the task.",
        ]
        events = [dict(task_id=pair['task_id'], update_id=uid, text=description)
                  for pair, uid, description in zip(payload['pairs'], [loss_id, None, 'u2'], descriptions)]
        return dict(content=json.dumps({'entries': [{'knowledge': events}]}), finish_reason='stop')

    state = run(tmp_path, actor, generate)
    assert read(tmp_path / 'rounds/R01/replay/result.json')['attempt'] == 1
    gate = read(tmp_path / 'rounds/R01/gate.json')
    assert gate['decisions'] == [
        dict(update_id=uid, G=g, L=l, gate_decision=choice)
        for uid, (g, l, choice) in zip(('u1', 'u2'), expected)]
    assert gate['selection']['selected_update_ids'] == (['u2'] if loss_id == 'u1' else [])
    assert [(e['direction'], e['knowledge']['update_id']) for e in state['memory']['rounds'][0]['entries']] == [
        ('loss', loss_id), ('loss', None), ('gain', 'u2')]
    assert campaign.run_round(tmp_path) == state


def test_empty_patches_have_no_decision(tmp_path):
    def generate(name, *args):
        if name == 'editor':
            edits = [dict(update_id=uid, patch='', reason='Already covered.') for uid in ('u1', 'u2')]
            return dict(content=json.dumps({'edits': edits}), finish_reason='stop')
        assert name != 'replay'
        return fixture.generate(name, *args)

    state = run(tmp_path, fixture.actor, generate)
    record, = state['memory']['rounds']
    assert [u['gate_decision'] for u in record['source_updates']] == [None, None]
    assert record['entries'] == []


def test_reversed_output_arrays_publish_the_same_round(tmp_path):
    def reversed_output(name, messages, slot, call):
        response = fixture.generate(name, messages, slot, call)
        value = json.loads(response['content'])
        if name == 'preconditioner':
            value['adjustments'].reverse()
        elif name == 'editor':
            value['edits'].reverse()
        elif name == 'replay':
            value['entries'][0]['knowledge'].reverse()
        return {**response, 'content': json.dumps(value)}

    ordered = tmp_path / 'ordered'
    reversed_run = tmp_path / 'reversed'
    expected = run(ordered, fixture.actor, fixture.generate)
    assert run(reversed_run, fixture.actor, reversed_output) == expected
    rd = reversed_run / 'rounds/R01'
    original = ordered / 'rounds/R01'
    assert read(rd / 'gate.json') == read(original / 'gate.json')
    for stage in ('preconditioner', 'editor', 'replay'):
        receipt = read(rd / stage / 'result.json')
        assert receipt['attempt'] == 1
        ordered_receipt = read(original / stage / 'result.json')
        assert receipt['parsed'] != ordered_receipt['parsed']
        assert receipt['result'] == ordered_receipt['result']
