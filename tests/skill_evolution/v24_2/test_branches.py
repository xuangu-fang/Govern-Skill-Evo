"""Failures and no-change branches at the V24.2 publication boundary."""
import json

import pytest

from src.skill_evolution.v24_2.campaign import current, prepare, run_round
from src.skill_evolution.v24_2.storage import read, save
from .fixture import TASKS, actor, fixture_config, generate


def response(value):
    return dict(content=json.dumps(value), finish_reason='stop')


@pytest.mark.parametrize('branch', ['no_change', 'withdraw', 'empty_patches', 'blocked', 'conflict'])
def test_plan_branches(tmp_path, branch):
    prepare(tmp_path, fixture_config())
    original = current(tmp_path)
    calls = []

    def scripted(name, messages, slot, call):
        calls.append(name)
        if name == 'diagnosis' and branch == 'no_change':
            return response(dict(decision='no_change', reason='No supported revision.', plan=None))
        if name == 'preconditioner' and branch == 'withdraw':
            return response(dict(adjustments=[dict(target=uid, action='WITHDRAW', text=None,
                                                  reason='Existing Parent covers it.') for uid in ('u1', 'u2')]))
        value = generate(name, messages, slot, call)
        if name == 'editor':
            edits = json.loads(value['content'])['edits']
            if branch == 'conflict':
                edits[1]['patch'] = edits[0]['patch']
            else:
                for edit in edits:
                    edit.update(patch='', reason='Already satisfied by the corresponding Parent clause.')
                if branch == 'blocked':
                    edits[1].update(patch=None, reason='Cannot faithfully express the required condition.')
            return response(dict(edits=edits))
        return value

    if branch in ('blocked', 'conflict'):
        with pytest.raises((RuntimeError, ValueError), match='blocked faithful|exhausted'):
            run_round(tmp_path, actor=actor, generate=scripted)
        assert original == current(tmp_path)
        assert calls.count('editor') == (1 if branch == 'blocked' else fixture_config()['max_attempts'])
    else:
        state = run_round(tmp_path, actor=actor, generate=scripted)
        assert state['selected'] == original[1]['selected']
        rounds = state['memory']['rounds']
        if branch == 'empty_patches':
            assert [u['gate_decision'] for u in rounds[0]['source_updates']] == [None, None]
            assert rounds[0]['entries'] == []
        else:
            assert rounds == []
    assert 'replay' not in calls
    assert not (tmp_path / 'rounds/R01/candidate_runs').exists()


def test_no_flips(tmp_path):
    prepare(tmp_path, fixture_config())

    def no_flip_actor(task, skill, directory, config):
        dest = actor(task, skill, directory, config)
        if directory.parents[2].name == 'candidate_runs':
            rec = read(dest)
            parent_dir = tmp_path / 'rounds/R01/parent_runs' / task.replace(':', '_')
            rec['won'] = read(parent_dir / read(parent_dir / 'record.json')['trajectory'])['won']
            rec['steps'][-1].update(won=rec['won'], done=True)
            rec['status'] = 'success' if rec['won'] else 'environment_ended'
            save(dest, rec)
        return dest

    state = run_round(tmp_path, generate=generate, actor=no_flip_actor)
    record, = state['memory']['rounds']
    assert record['entries'] == []
    assert [u['gate_decision'] for u in record['source_updates']] == ['Defer', 'Defer']
    assert state['selected_execution_source'] == 'parent'
    assert not (tmp_path / 'rounds/R01/replay').exists()


def test_replay_rejects_other_task_evidence_and_retries(tmp_path):
    prepare(tmp_path, fixture_config())
    def mistaken(name, messages, slot, call):
        raw = generate(name, messages, slot, call)
        if name == 'replay' and slot.name == '001':
            out = json.loads(raw['content'])
            out['entries'][0]['knowledge'][0]['text'] = 'Unsupported attribution from Q2:1.'
            return response(out)
        if name == 'replay':
            assert 'Unavailable execution references' in messages[-1]['content']
        return raw
    state = run_round(tmp_path, actor=actor, generate=mistaken)
    assert len(state['memory']['rounds'][0]['entries']) == 4
    assert read(tmp_path / 'rounds/R01/replay/result.json')['attempt'] == 2


def test_next_round_reads_selected_and_published_memory(tmp_path):
    config = fixture_config()
    fresh = 'train:fixture6'
    config['batches'].append([fresh])
    config['task_items'][fresh] = {'id': fresh}
    prepare(tmp_path, config)
    first = run_round(tmp_path, actor=actor, generate=generate)

    def next_actor(task, skill, directory, cfg):
        assert task == fresh and skill.read_text() == first['selected']
        path = actor(TASKS[0], skill, directory, cfg)
        data = read(path)
        data.update(task=cfg['task_items'][fresh], run_id='second-batch-parent')
        save(path, data)
        return path

    def next_model(name, messages, slot, call):
        payload = json.loads(messages[1]['content'])
        assert payload['parent'] == first['selected']
        if name == 'diagnosis':
            return response(dict(decision='revise', reason='Inspect the missed search opportunity.',
                                 plan=dict(goal='Search efficiently.', updates=[
                                     dict(id='u1', text='Inspect the cabinet.', basis=['P1:1'])])))
        assert name == 'preconditioner' and payload['memory'] == first['memory']
        return response(dict(adjustments=[dict(target='u1', action='WITHDRAW', text=None,
                                               reason='M2 records a regression under a comparable condition.')]))
    second = run_round(tmp_path, actor=next_actor, generate=next_model)
    assert second['selected'] == first['selected'] and second['memory'] == first['memory']
    assert second['next_round'] == 3
