"""Offline contracts and scripted handoff cases for the executable-search prompts."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.runs.v24_2.run_v24_2_test import prepare_test
from src.skill_evolution.v24_2.storage import read, save
from src.skill_evolution.v24_6 import campaign as previous, gate
from src.skill_evolution import v24_7
from src.skill_evolution.v24_7 import PROMPTS, ROOT, STAGES, campaign, system_prompt
from tests.skill_evolution.v24_2 import fixture


def test_contract_isolates_prompts_and_freezes_the_shared_gate(tmp_path):
    config = campaign.configuration()
    assert dict(config, method=previous.VERSION) == previous.configuration()
    assert [len(tasks) for tasks in config['batches']] == [10, 10, 10, 10, 10, 7]
    state = campaign.prepare(tmp_path)
    assert state['selected'] == config['initial_skill']['text']
    assert state['memory'] == {'rounds': []}
    contract = read(tmp_path / 'contract.json')
    assert campaign.gate is gate
    for path in [Path(gate.__file__), *(PROMPTS / f'{s}.md' for s in STAGES)]:
        assert contract['files'][str(path.relative_to(ROOT))] == hashlib.sha256(path.read_bytes()).hexdigest()
    for stage in STAGES:
        assert system_prompt(stage) != previous.system_prompt(stage)

    original = campaign.current(tmp_path)
    with pytest.raises(ValueError):
        previous.run_round(tmp_path)
    with pytest.raises(ValueError, match='incomplete'):
        prepare_test(tmp_path, campaign.ALFWorldAdapter(), version=campaign)
    assert campaign.current(tmp_path) == original


def test_prompt_drift_stops_before_an_actor_call(tmp_path, monkeypatch):
    cfg = dict(fixture.fixture_config(), method=campaign.VERSION)
    root = tmp_path / 'campaign'
    prompts = tmp_path / 'prompts'
    prompts.mkdir()
    for stage in STAGES:
        (prompts / f'{stage}.md').write_text(system_prompt(stage))
    # Keep contract paths stable before and after changing a single prompt.
    monkeypatch.setattr(campaign, 'ROOT', Path('/'))
    monkeypatch.setattr(campaign, 'PROMPTS', prompts)
    monkeypatch.setattr(v24_7, 'PROMPTS', prompts)
    campaign.prepare(root, cfg)
    with (prompts / 'diagnosis.md').open('a') as stream:
        stream.write('Changed after preparation.')
    with pytest.raises(ValueError, match='Frozen artifact differs'):
        campaign.run_round(root, actor=pytest.fail, generate=pytest.fail)
    assert not (root / 'rounds').exists()


def test_search_update_survives_interruption_and_next_round(tmp_path):
    cfg = dict(fixture.fixture_config(), method=campaign.VERSION)
    extra = 'train:next'
    cfg['batches'].append([extra])
    cfg['task_items'][extra] = {'id': extra}
    campaign.prepare(tmp_path, cfg)
    original = 'Use a list of everything inspected so far when deciding whether to leave a closed cabinet.'
    local = fixture.OPEN_FIRST + ' Resume the task when the required object becomes visible.'
    section = '## Search during acquisition'
    parent_state = campaign.current(tmp_path)
    calls = []

    def generate(name, messages, directory, call):
        assert messages[0]['content'] == system_prompt(name)
        view = json.loads(messages[1]['content'])
        calls.append(name)
        if name == 'diagnosis':
            assert 'memory' not in view and len(view['runs']) == 5
            reply = fixture.generate(name, messages, directory, call)
            value = json.loads(reply['content'])
            update = value['plan']['updates'][0]
            update.update(text=original, basis=['P1:1', 'P1:4', 'P2:1', 'P2:2'])
        elif name == 'preconditioner':
            assert [r['ref'] for r in view['runs']] == ['P1', 'P2', 'P4']
            assert view['plan']['updates'][0]['text'] == original
            assert view['runs'][0]['steps'][3]['step'] == 'P1:4'
            value = dict(adjustments=[
                dict(target='u1', action='REPLACE', text=local,
                     reason='P1:4 cannot reveal the whole visit history. At P1:1 the reachable closed cabinet distinguishes a local choice. P2:2 supports exiting upon discovery.'),
                dict(target='u2', action='KEEP', text=None,
                     reason='At P4:1 opening the destination advances delivery.')])
        elif name == 'editor':
            assert set(view) == {'parent', 'plan'}
            assert view['plan']['updates'][0] == dict(id='u1', text=local)
            value = json.loads(fixture.generate(name, messages, directory, call)['content'])
            old = next(line for line in view['parent'].splitlines() if line.startswith('2. **Systematic exploration'))
            # Two hunks owned by one ID: reference and its stand-alone section.
            value['edits'][0]['patch'] = (
                '--- a/SKILL.md\n+++ b/SKILL.md\n@@\n-' + old + '\n+' + old
                + ' See Search during acquisition.\n@@\n+' + section + '\n+\n+' + local
                + '\n+\n ## Common Mistakes to Avoid\n')
        else:
            assert name == 'replay'
            assert [pair['direction'] for pair in view['pairs']] == ['gain', 'loss', 'loss', 'gain']
            value = dict(entries=[dict(knowledge=[
                dict(task_id=fixture.TASKS[0], update_id='u1', text='P1:1 left; Q1:1 opened the cabinet, revealing the mug acquired at Q1:2.'),
                dict(task_id=fixture.TASKS[1], update_id=None, text='P2:1 led to the apple. Q2:1 opened an empty cabinet; the later failure at Q2:2 cannot be assigned to the inspection alone.'),
                dict(task_id=fixture.TASKS[2], update_id=None, text='P3:1 and Q3:1 already held the key. Search had ended and neither patch explains the later regression.'),
                dict(task_id=fixture.TASKS[3], update_id='u2', text='P4:1 left the drawer. Q4:1 opened it and Q4:2 delivered the spoon.')])])
        return dict(finish_reason='stop', content=json.dumps(value))

    def interrupt(name, *args):
        if name == 'replay':
            raise RuntimeError('fixture interruption')
        return generate(name, *args)

    with pytest.raises(RuntimeError, match='fixture interruption'):
        campaign.run_round(tmp_path, generate=interrupt, actor=fixture.actor)
    assert campaign.current(tmp_path) == parent_state
    published = campaign.run_round(tmp_path, generate=generate, actor=pytest.fail)
    assert calls == ['diagnosis', 'preconditioner', 'editor', 'replay']
    assert published['selected_execution_source'] == 'candidate'
    assert section in published['selected'] and local in published['selected']
    decisions = read(tmp_path / 'rounds/R01/gate.json')['decisions']
    assert [(d['gate_decision'], d['G'], d['L']) for d in decisions] == [('Retain', 1, 0)] * 2
    memory = published['memory']['rounds'][0]['entries']
    assert [(e['direction'], e['knowledge']['update_id']) for e in memory] == [
        ('gain', 'u1'), ('loss', None), ('loss', None), ('gain', 'u2')]

    def next_actor(task, skill, directory, config):
        assert task == extra and skill.read_text() == published['selected']
        path = fixture.actor(fixture.TASKS[0], skill, directory, config)
        record = read(path)
        record['task'] = config['task_items'][task]
        save(path, record)
        return path

    def next_model(name, messages, directory, call):
        view = json.loads(messages[1]['content'])
        if name == 'diagnosis':
            value = dict(decision='revise', reason='Check an overlapping search instruction.', plan=dict(
                goal='Review the local inspection choice.', updates=[dict(id='u1', text=local, basis=['P1:1'])]))
        else:
            assert name == 'preconditioner' and view['memory'] == published['memory']
            value = dict(adjustments=[dict(target='u1', action='WITHDRAW', text=None,
                                           reason='The selected Parent already makes the same choice at P1:1.')])
        return dict(finish_reason='stop', content=json.dumps(value))

    final = campaign.run_round(tmp_path, actor=next_actor, generate=next_model)
    assert final['outcome'] == 'all_withdrawn' and final['memory'] == published['memory']
    assert (tmp_path / 'final_skill.md').read_text() == published['selected'] == final['selected']
    assert campaign.run_round(tmp_path) == final


def test_cli_and_official_test_entry_are_version_bound(tmp_path, monkeypatch, capsys):
    import runpy
    import sys

    from scripts.runs.v24_2.run_v24_2_test import published_skill
    from src.skill_evolution.v24_7 import __main__ as cli

    root = tmp_path / 'official'
    for command in ('prepare', 'status'):
        monkeypatch.setattr(sys, 'argv', ['v24_7', command, '--campaign', str(root)])
        cli.main()
    assert 'next_round=1 memory_rounds=0' in capsys.readouterr().out
    evaluation = tmp_path / 'evaluation'
    script = ROOT / 'scripts/runs/v24_7/run_v24_7_test.py'
    monkeypatch.setattr(sys, 'argv', [str(script), '--validate-only', '--campaign', str(root),
                                     '--evaluation', str(evaluation)])
    with pytest.raises(ValueError, match='Training is incomplete'):
        runpy.run_path(str(script), run_name='__main__')
    assert not evaluation.exists()

    # Construct the six chained publications in temporary storage to check the
    # official test loader's source selection without running the live Actor.
    config = read(root / 'config.json')
    for n, tasks in enumerate(config['batches'], 1):
        head, state = campaign.current(root)
        rd = root / 'rounds' / f'R{n:02}'
        published = dict(state, next_round=n+1, selected=f'Offline selected text {n}', previous=head)
        save(rd / 'round_input.json', dict(previous=head, tasks=tasks))
        save(rd / 'publication.json', published)
        campaign.publish(root, head, published)
    assert published_skill(root, config, campaign) == (campaign.current(root)[0], published['selected'])
    with pytest.raises(ValueError, match='Expected V24.6'):
        published_skill(root, config, previous)
