"""Offline checks for the v25.7 entry point. All simulated results live in a temporary directory."""
from pathlib import Path
from copy import deepcopy
import hashlib
import socket
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.runs.v25_7 import run_v25_7_train_test as entry
from src.skill_evolution.v25_6 import stages as baseline
from src.skill_evolution.v25_7 import method, stages
from src.skill_evolution.v27.facts import require


def check_wiring(train, test, api_profile):
    manifest = stages.read(entry.ROOT / 'docs/methods/v25_7/baseline_sha256.json')
    for path, digest in manifest.items():
        require(hashlib.sha256((entry.ROOT / path).read_bytes()).hexdigest() == digest,
                f'v25.6 baseline changed: {path}')
    for name, config, workers in [('config.json', train, 15), ('evaluation/config.json', test, 40)]:
        old = entry.pipeline.read_config(entry.OFFICIAL / name)
        expected = dict(old, candidate='v25_7_spreadsheetbench', actor_max_workers=workers,
                        method=dict(old['method'], version='v25_7_selective_updates_prompt_v1'))
        if api_profile == 'internal':
            expected.update(actor_base_url=entry.INTERNAL_BASE_URL, actor_model=entry.INTERNAL_MODEL,
                            call_config={**old['call_config'], 'model': entry.INTERNAL_MODEL,
                                         'endpoint': entry.INTERNAL_BASE_URL + '/chat/completions'})
        require(config == expected, f'Official profile drift: {name}')
    for name in train['method']['stages']:
        profile = train['actor_profile']
        old = baseline.messages_for(name, {}, profile)
        new = stages.messages_for(name, {}, profile)
        path = entry.PACKAGE / 'prompts' / (name + '.md')
        old_path = baseline.PACKAGE / 'prompts' / path.name
        if name == 'editor':
            require(new == old, f'{name} messages changed')
        else:
            require(path.read_bytes() != old_path.read_bytes(), f'{name} prompt not updated')
            require(old[0]['content'].startswith(old_path.read_text()) and
                    new[0]['content'] == path.read_text() + old[0]['content'][len(old_path.read_text()):]
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


def check_replay_update_ids(directory):
    view = stages.read(directory / 'input.json')
    result = stages.read(directory / 'result.json')['parsed']
    event = result['entries'][0]['knowledge'][0]
    empty_id = next(edit['update_id'] for edit in view['edits'] if edit['patch'] == '')
    event['text'] = f'No change was applied for `Update:{empty_id}`.'
    method.knowledge(result, view)

    vote = event['update_id']
    for invalid_vote, explanation in ((empty_id, event['text']), (vote, 'See `Update:unknown`.')):
        event.update(update_id=invalid_vote, text=explanation)
        try:
            method.knowledge(result, view)
        except ValueError:
            continue
        raise AssertionError(f'Replay accepted an invalid vote or citation: {event}')


def check_campaign(train):
    """Exercise the real stages, selection, Memory, resume and final test with preset responses."""
    from tests.skill_evolution.v25 import support
    from tests.skill_evolution.v25_3.test_campaign import Fixture

    for mode in ('mixed', 'unknown'):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = deepcopy(train)
            data = support.config(root / 'data', test=1)
            for key in ('dataset', 'batches', 'task_items', 'test_tasks', 'initial_skill'):
                config[key] = data[key]
            config.update(actor_max_workers=1, retry_delay_seconds=0)
            fixture = Fixture(mode)
            campaign = root / 'campaign'
            state = entry.engine.prepare(campaign, config)
            entry.save_snapshot(root, state)
            original_run = entry.engine.run

            def simulate(folder, generate, **kwargs):
                return original_run(folder, generate, adapter=fixture.adapter, **kwargs)

            actor_run = entry.pipeline.actor.run

            def simulate_test(*args, **kwargs):
                return actor_run(*args, generate=fixture.adapter.generate,
                                 execute=support.fast_execute, **kwargs)

            with patch.object(entry.engine, 'run', side_effect=simulate), \
                 patch.object(entry.pipeline.actor, 'run', side_effect=simulate_test):
                with patch.object(entry.engine, '_publish', side_effect=InterruptedError):
                    try:
                        entry.train_and_test(root, config, config, fixture.generate)
                    except InterruptedError:
                        pass
                    else:
                        raise AssertionError('Expected interruption before commit')
                require(entry.engine.current(campaign)[1]['next_round'] == 1 and
                        not (root / 'test').exists(), 'Interrupted round was published or evaluated')
                entry.train_and_test(root, config, config, fixture.generate)
                require(fixture.calls == config['method']['stages'], 'Stages repeated on resume')
                calls = len(fixture.adapter.generate.calls)
                entry.train_and_test(root, config, config, fixture.generate)
                require(len(fixture.adapter.generate.calls) == calls, 'Completed evaluation repeated')
            state = entry.engine.current(campaign)[1]
            selected = state['selected'].encode()
            for path in (campaign / 'final_skill.md', root / 'snapshots/R01.md', root / 'test/final_skill.md'):
                require(path.read_bytes() == selected, 'Selected/final/evaluated Skill differs')
            record = state['memory']['rounds'][0]
            check_replay_update_ids(campaign / 'rounds/R01/replay')
            require(len(record['entries']) == 2, 'Replay events lost')
            expected = ['Retain', 'Defer', None] if mode == 'mixed' else ['Defer', 'Defer', None]
            require([u['gate_decision'] for u in record['source_updates']] == expected,
                    'Gate selection differs')
            if mode == 'unknown':
                require(all(e['knowledge']['update_id'] is None for e in record['entries']) and
                        state['selected'] == config['initial_skill']['text'], 'Null events cast votes')
            else:
                require(support.NEW in state['selected'] and 'Preserve all unrelated' not in state['selected'],
                        'Selected Skill includes a deferred patch')
            for name in config['method']['stages']:
                messages = stages.read(campaign / 'rounds/R01' / name / 'attempts/001/messages.json')
                prompt = (entry.PACKAGE / 'prompts' / (name + '.md')).read_text()
                require(messages[0]['content'].startswith(prompt), 'Campaign used a different prompt')


def verify(train, test, api_profile='public'):
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Unexpected network access')), \
         patch.object(subprocess, 'Popen', side_effect=AssertionError('Unexpected subprocess')):
        check_wiring(train, test, api_profile)
        check_final_only(train, test)
        check_campaign(train)
    return dict(official_config_match=True, api_profile=api_profile, rounds=len(train['batches']), test_tasks=len(test['test_tasks']),
                training_workers=train['actor_max_workers'], test_workers=test['actor_max_workers'],
                prompt_bindings_checked=True,
                round_snapshots_checked=True, final_only_evaluation_checked=True,
                synthetic_campaign_resume_checked=True, null_events_preserved=True,
                simulated_calls_network_and_subprocess_guarded=True)
