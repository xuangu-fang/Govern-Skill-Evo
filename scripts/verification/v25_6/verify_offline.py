"""Offline checks for the v25.6 entry point. All simulated results live in a temporary directory."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.runs.v25_6 import run_v25_6_train_test as entry
from src.skill_evolution.v25_5 import stages as baseline
from src.skill_evolution.v25_6 import stages
from src.skill_evolution.v27.facts import require


def check_wiring(train, test):
    for name, config, workers in [('config.json', train, 15), ('evaluation/config.json', test, 40)]:
        old = entry.pipeline.read_config(entry.OFFICIAL / name)
        expected = dict(old, candidate='v25_6_spreadsheetbench', actor_max_workers=workers,
                        method=dict(old['method'], version='v25_6_selective_updates_prompt_v1'))
        require(config == expected, f'Official profile drift: {name}')
    for name in train['method']['stages']:
        profile = train['actor_profile']
        old = baseline.messages_for(name, {}, profile)
        new = stages.messages_for(name, {}, profile)
        path = entry.PACKAGE / 'prompts' / (name + '.md')
        old_path = baseline.PACKAGE / 'prompts' / path.name
        if name == 'replay':
            require(new == old, 'Replay messages changed')
        else:
            draft = entry.ROOT / 'docs/methods/v25_6/prompt_draft' / path.name
            require(path.read_bytes() == draft.read_bytes() != old_path.read_bytes(), f'{name} draft differs')
            require(old[0]['content'].startswith(old_path.read_text()) and
                    new[0]['content'] == draft.read_text() + old[0]['content'][len(old_path.read_text()):]
                    and new[1:] == old[1:], f'{name} runtime message binding differs')


def check_final_only(train, test):
    """Simulate gate selections and capture the single test dispatch; no Actor is invoked."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        campaign = root / 'campaign'
        state = entry.engine.prepare(campaign, train)
        entry.save_snapshot(root, state)
        snapshots = [state['selected']]

        def publish(folder, generate, *, limit, expected_config):
            number = len(snapshots)
            # Include a round that retained its parent.
            selected = snapshots[-1] if number == 2 else f'Selected after round {number}\n'
            snapshots.append(selected)
            if number == len(train['batches']):
                (folder / 'final_skill.md').write_bytes(selected.encode())
            return dict(next_round=number + 1, selected=selected)

        def capture(folder, *, runner, bundle, resume):
            require(len(snapshots) == len(train['batches']) + 1, 'Test started before the last gate')
            require(bundle['skill_text'] == snapshots[-1] and folder == root / 'test',
                    'Expected the final Skill and one test directory')
            require(bundle['actor_config'] == test and [t['id'] for t in bundle['tasks']] == test['test_tasks'],
                    'Incorrect test configuration or cohort')
            return {'status': 'complete'}

        with patch.object(entry.engine, 'run', side_effect=publish), \
             patch.object(entry.pipeline.evaluation, 'run', side_effect=capture) as evaluation:
            entry.train_and_test(root, train, test, None)
            evaluation.assert_called_once()
        for number, text in enumerate(snapshots):
            require((root / 'snapshots' / f'R{number:02}.md').read_bytes() == text.encode(),
                    'Snapshot differs from gate selection')


def verify(train, test):
    check_wiring(train, test)
    check_final_only(train, test)
    return dict(official_config_match=True, rounds=len(train['batches']), test_tasks=len(test['test_tasks']),
                training_workers=train['actor_max_workers'], test_workers=test['actor_max_workers'],
                prompt_bindings_checked=True,
                round_snapshots_checked=True, final_only_evaluation_checked=True)
