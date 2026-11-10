import json
from pathlib import Path
from unittest.mock import patch
import pytest

from src.skill_evolution.v24_2.campaign import current, prepare, run_round
from src.skill_evolution.v24_2.stages import trajectory_view
from src.skill_evolution.v24_2.storage import read, save
from .fixture import actor, fixture_config, generate, OPEN_FIRST, DESTINATION, TASKS


def run_fixture(root):
    with patch('socket.socket.connect', side_effect=AssertionError('offline network access')), \
         patch('subprocess.Popen', side_effect=AssertionError('offline subprocess')):
        prepare(root, fixture_config())
        state = run_round(root, generate=generate, actor=actor)
        record, = state['memory']['rounds']
        events = record['entries']
        gate = read(root / 'rounds/R01/gate.json')
        assert gate['decisions'] == [dict(update_id='u1', G=1, L=1, gate_decision='Defer'),
                                     dict(update_id='u2', G=1, L=0, gate_decision='Retain')]
        assert [e['id'] for e in events] == ['M1', 'M2', 'M3', 'M4']
        assert [e['knowledge']['update_id'] for e in events] == ['u1', 'u1', None, 'u2']
        assert [e['direction'] for e in events] == ['gain', 'loss', 'loss', 'gain']
        assert [e['knowledge']['task_id'] for e in events] == TASKS[:4]
        assert state['selected_execution_source'] is None
        assert DESTINATION in state['selected'] and OPEN_FIRST not in state['selected']
        assert gate['selection']['selected_update_ids'] == ['u2']
        assert (root / 'final_skill.md').read_text() == state['selected']
        # Repeat the public entry point after publication. No new event or execution.
        assert run_round(root) == state
        return dict(mode='offline_fixture', paired_tasks=len(TASKS), flip_events=len(events),
                    decisions=gate['decisions'], selected_execution_source=state['selected_execution_source'],
                    memory_ids=[e['id'] for e in events], selected_update_ids=['u2'], live_requests=0,
                    environment_episodes=0, published_head=current(root)[0])


def test_round(tmp_path):
    run_fixture(tmp_path)
    # Inspect the archived messages at the actual request boundary.
    phrases = {
        'goal': 'how many distinct objects are needed',
        'decision': 'earliest observable decision relevant to the explanation',
        'cleaning': 'two failed cleaning tasks',
        'visibility': 'at most the two most recent pre-action observation/action pairs',
        'completion': 'There is no partial credit.',
        'correction': 'A single clear case can support a scoped correction.',
        'wording': 'Express the authorized behavior in terms the Actor can apply across episodes.',
    }
    expected = {
        'diagnosis': {'goal', 'decision', 'cleaning', 'visibility', 'completion', 'correction'},
        'preconditioner': {'goal', 'visibility', 'correction'},
        'editor': {'wording'},
        'replay': {'goal', 'decision', 'cleaning', 'visibility', 'completion'},
    }
    for name, sections in expected.items():
        messages = read(tmp_path / 'rounds/R01' / name / 'attempts/001/messages.json')
        prompt = messages[0]['content']
        assert ('immediately preceding step' in prompt) == (name != 'editor')
        original = read(tmp_path / 'rounds/R01' / name / 'input.json')
        displayed = json.loads(messages[1]['content'])
        for run in displayed.get('runs', []):
            previous = run['initial']
            for step in run['steps']:
                assert 'before' not in step  # All transitions in this fixture are continuous.
                step['before'] = previous
                previous = step['after']
        assert displayed == original
        assert '{{domain:' not in prompt
        assert {key for key, phrase in phrases.items() if phrase in prompt} == sections
        if name == 'preconditioner':
            assert 'different adjustments to this Original' in prompt
    assert 'src/skill_evolution/v24_2/prompts/alfworld_domain.md' in read(tmp_path / 'contract.json')['files']


def test_distinct_pre_action_state_remains_explicit():
    initial = {'observation': 'At the cabinet.', 'commands_ref': 'C1'}
    open_menu = {**initial, 'commands_ref': 'C2'}
    moved = {**open_menu, 'observation': 'At the table.'}
    payload = {'runs': [{'initial': initial, 'steps': [
        {'before': open_menu, 'after': open_menu},
        {'before': moved, 'after': moved},
        {'before': moved, 'after': moved},
    ]}]}
    assert trajectory_view(payload)['runs'][0]['steps'] == [
        {'before': open_menu, 'after': open_menu},
        {'before': moved, 'after': moved},
        {'after': moved},
    ]
    assert payload['runs'][0]['steps'][2]['before'] == moved


def test_interruption_and_resume(tmp_path):
    prepare(tmp_path, fixture_config())
    head, before = current(tmp_path)

    def interrupted(task, skill, directory, config):
        result = actor(task, skill, directory, config)
        if task == TASKS[-1] and directory.parents[2].name == 'candidate_runs':
            value = read(result)
            value['status'] = 'interrupted'
            save(result, value)
        return result

    with pytest.raises(ValueError, match='Incomplete Actor task'):
        run_round(tmp_path, generate=generate, actor=interrupted)
    assert current(tmp_path) == (head, before)
    assert not (tmp_path / 'rounds/R01/gate.json').exists()
    def replay_only(name, *args):
        assert name == 'replay'
        return generate(name, *args)
    resumed = run_round(tmp_path, generate=replay_only, actor=actor)
    assert len(resumed['memory']['rounds'][0]['entries']) == 4


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run the V24.2 offline acceptance fixture')
    parser.add_argument('--campaign', type=Path, required=True)
    root = parser.parse_args().campaign.resolve()
    summary = run_fixture(root)
    save(root / 'offline_report.json', summary)
    print(summary)
