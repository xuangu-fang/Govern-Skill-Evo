"""Offline acceptance through the native Trainer, LMB Actor journal and Best Test path."""
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import random
import socket
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx2 as httpx
from skillopt.prompts import load_prompt
from experiments.benchmark_record_refs.restore import ARCHIVE, Archive
from src.adapters.lmb import skilladam
from src.skill_evolution.shared.experiment_paths import resolve_experiment_path
from src.skill_evolution.v27_1.lmb import protocol as v27_actor
from src.skill_evolution.v27.transport import RequestFailure

from scripts.runs.skillopt.lmb import run


def check_schedule(cfg, adapter):
    loader = adapter.dataloader
    assert (cfg['num_epochs'], cfg['seed'], cfg['batch_size'], cfg['accumulation']) == (4, 42, 40, 1)
    assert (cfg['failure_only'], cfg['minibatch_size'], cfg['merge_batch_size'],
            cfg['analyst_workers'], cfg['max_analyst_rounds']) == (False, 8, 8, 16, 3)
    assert (cfg['lr_scheduler'], cfg['edit_budget'], cfg['min_edit_budget'],
            cfg['skill_update_mode']) == ('cosine', 4, 2, 'patch')
    assert cfg['use_gate'] and cfg['slow_update_gate_with_selection'] and cfg['use_meta_skill']
    assert cfg['use_slow_update'] and cfg['slow_update_samples'] == 20 and cfg['longitudinal_pair_policy'] == 'mixed'
    assert not any(cfg[k] for k in ('eval_test', 'failure_only', 'use_theorem', 'use_sketch'))
    schedule = []
    for epoch in range(1, 5):
        batch, = loader.plan_train_epoch(epoch=epoch, steps_per_epoch=1, accumulation=1, batch_size=40, seed=42)
        expected = list(loader.train_items)
        random.Random(42 + epoch * 1000).shuffle(expected)
        assert [r['id'] for r in batch.payload] == [r['id'] for r in expected]
        assert batch.seed == 43 + epoch * 1000 and batch.batch_size == 35
        for original, rendered in zip(expected, batch.payload):
            salt = f"{batch.seed}:{original['id']}".encode()
            ordered = list(original['choices'])
            random.Random(int(hashlib.sha256(salt).hexdigest()[:16], 16)).shuffle(ordered)
            assert rendered['choices'] == [dict(c, label=label) for label, c in zip('ABCDE', ordered)]
            assert rendered['correct_choice']['text'] == original['correct_choice']['text']
            assert rendered['correct_choice'] in rendered['choices']
        schedule.append([row['id'] for row in batch.payload])
    for split, expected in [('val', 18), ('test', 124)]:
        items = loader.build_eval_batch(expected, split, 42).payload
        assert [r['id'] for r in items] == run.read(run.COMMON_IDS)[split]
    return schedule


def verify_local_splits(cfg, adapter):
    ids = {s: [r['id'] for r in adapter.dataloader.get_split_items(s)] for s in ('train', 'val', 'test')}
    source = {s: [r['id'] for r in run.read(Path(cfg['split_dir']) / s / 'items.json')] for s in ids}
    moved = '202512:46'
    assert ids['train'] == source['train'] and ids['val'] == source['val'] + [moved]
    assert ids['test'] == [uid for uid in source['test'] if uid != moved]
    assert len(set(ids['train'] + ids['val'] + ids['test'])) == 177
    items = adapter.build_eval_env(cfg['test_env_num'], 'valid_unseen', cfg['seed'])
    cases = [(r['id'], r['question'], r['choices'], r['correct_choice']['label']) for r in items]
    archives = ('v27_12_lmb53_20261118_test_deepseek_flash', 'lmb53_skilladam_v27_5_official_flash_20261120_0020_test')
    archive = Archive('lmb') if (ARCHIVE / 'lmb' / 'manifest.sqlite3').is_file() else None
    try:
        for name in archives:
            source = Path('experiments/evaluations') / name / 'evaluation.json'
            evaluation = (json.loads(archive.read_bytes(source)) if archive
                          else run.read(resolve_experiment_path(source)))
            assert ids['test'] == evaluation['tasks'], name
            assert cases == [(r['id'], r['payload']['question'], r['payload']['choices'], r['reference']['label'])
                             for r in evaluation['cases']], name
    finally:
        if archive:
            archive.close()
    return {'verified_against': list(archives), 'matching_ordered_cases': len(cases),
            'test_ids_sha256': v27_actor.digest(ids['test']), 'moved_to_selection': moved}


def fixture_data(path, adapter):
    for split in ('train', 'val', 'test'):
        items = []
        for index, original in enumerate(adapter.dataloader.get_split_items(split)):
            choices = [{'label': label, 'text': f'fixture option {label}'} for label in 'ABCDE']
            items.append(dict(id=original['id'], question=f'Synthetic {split} problem {index}',
                              choices=choices, correct_choice=choices[0], theorem='HIDDEN_FIXTURE',
                              sketch='HIDDEN_FIXTURE', theorem_type=['math_mcq']))
        run.save(path / split / 'items.json', items)


class FixtureActor:
    def __init__(self, profile):
        self.profile = profile

    def metadata(self):
        return self.profile

    def __call__(self, messages, slot):
        request = run.read(slot / 'request.json')['body']
        assert request['max_tokens'] == 65536 and request['messages'] == messages
        signature = run.read(slot.parents[1] / 'signature.json')
        assert messages == v27_actor.messages(signature['payload'], signature['skill'])
        assert request['model'] == 'deepseek-flash' and request['thinking'] == {'type': 'enabled'}
        system, user = [m['content'] for m in messages]
        assert 'Synthetic ' in user and 'HIDDEN_FIXTURE' not in user and 'termination' not in user
        choices = user.split('## Choices\n')[1].splitlines()
        index = int(user.split(' problem ')[1].splitlines()[0])
        improved = 'OFFLINE EDIT' in system
        correct = index % 2 == 0 or (index == 1 and improved)
        label = next(c[0] for c in choices if c.endswith('option A') == correct)
        return {'choices': [{'message': {'role': 'assistant', 'content': f'<answer>{label}</answer>',
                                         'reasoning_content': 'PRIVATE_FIXTURE'}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 4, 'total_tokens': 14}}


def verify_real_actor_messages(root, cfg, adapter, profile):
    dataset = skilladam.load_dataset(cfg['split_dir'])
    adam = skilladam.NativeAdapter(dataset.root)
    skill = Path(cfg['skill_init']).read_text()
    # This Selection item is also in the local comparison methods' optimization pool.
    item = adapter.build_eval_env(cfg['sel_env_num'], 'valid_seen', cfg['seed'])[0]
    uid = item['id']
    case = next(case for case in skilladam.native_cases(dataset) if case.case_id == uid)
    request = adam.build_rollout_request(case, method='skilladam', split='train', skill=skill, seed=cfg['seed'])
    adam_messages = list(request.metadata['messages'])
    v27_messages = v27_actor.messages(dataset.case(uid).payload, skill)

    reply = {'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': '<answer>A</answer>'}}]}
    with patch.object(adapter, 'transport', FixtureActor(profile)), patch.object(FixtureActor, '__call__', return_value=reply):
        adapter.rollout([item], skill, root)
    sent = run.read(root / 'actor' / uid / 'attempts/001/request.json')['body']['messages']
    assert [m['role'] for m in sent] == ['system', 'user']
    assert sent == v27_messages == adam_messages, f'Actor messages differ for {uid}'
    return {'task_id': uid, 'skill_sha256': run.digest(Path(cfg['skill_init'])),
            'messages_sha256': v27_actor.digest(sent)}


def verify_retry(root, simulated, item):
    response = {'choices': [{'finish_reason': 'length', 'message': {'role': 'assistant',
                'content': '<answer>A</answer>'}}]}
    folder = root / 'truncated'
    with patch.object(FixtureActor, '__call__', return_value=response) as generate, patch.object(run.actor.time, 'sleep'):
        for _ in range(2):
            try:
                simulated.rollout([item], 'fixture', folder)
            except RequestFailure as error:
                assert 'budget exhausted' in str(error)
            else:
                raise AssertionError('A truncated answer received a score')
        assert generate.call_count == 6 and not list(folder.rglob('result.json'))
        assert not (folder / 'results.jsonl').exists()


def verify_final_promotion(root, local, simulated):
    # Construct the native end-of-training state in isolation. Normal training
    # above exercises ties; here the final candidate must overtake the incumbent.
    target = root / 'promotion'
    campaign = target / 'campaign'
    incumbent, final = campaign / 'incumbent.md', campaign / 'final.md'
    run.freeze_text(incumbent, 'old')
    run.freeze_text(final, 'OFFLINE EDIT final')
    run.save(campaign / 'summary.json', {'total_steps': 4})
    run.save(campaign / 'history.json', [{'step': n} for n in range(1, 5)])
    run.save(campaign / 'runtime_state.json', dict(last_completed_step=4, current_skill_path=str(final),
             best_skill_path=str(incumbent), best_score=9 / 18, best_step=1,
             current_origin='slow_update_epoch_04', best_origin='initial'))
    selected = run.train(target, dict(local, out_root=str(campaign)), simulated)
    assert selected['best_step'] == 4 and selected['best_selection_em'] == 10 / 18
    assert (target / 'best_skill.md').read_bytes() == final.read_bytes()


def verify(cfg, adapter, identity):
    schedule = check_schedule(cfg, adapter)
    split_parity = verify_local_splits(cfg, adapter)
    prompts = {load_prompt(k): k for k in ('merge_failure', 'merge_success', 'merge_final',
                                           'ranking', 'slow_update', 'meta_skill')}
    for k in ('analyst_error', 'analyst_success'):
        prompts[load_prompt(k, env='livemathematicianbench')] = k
    stages = Counter()
    errors = []
    edits = [{'op': 'append', 'content': f'OFFLINE EDIT {n}'} for n in range(6)]

    def reply(request):
        body = json.loads(request.content)
        system, user = [msg['content'] for msg in body['messages']]
        stage = prompts.get(system)
        try:
            assert stage, system[:100]
            assert str(request.url) == identity['actor']['endpoint']
            assert body['model'] == 'deepseek-flash' and body['max_tokens'] == 16384
            assert body['temperature'] == 1 and body['thinking'] == {'type': 'enabled'}
            assert body['reasoning_effort'] == 'medium' and body['stream'] is False
            for forbidden in ('PRIVATE_FIXTURE', 'HIDDEN_FIXTURE'):
                assert forbidden not in user, forbidden
            if stage.startswith('analyst'):
                for marker in ('Failure reason:', 'fail reason:', 'MCQ=0:'):
                    assert marker not in user, marker
                count = user.count('### Trajectory ')
                assert 1 <= count <= 8
                for field in ('termination', 'predicted_label', 'correct_label', 'correct_text', 'predicted_text', 'em'):
                    assert user.count(f'"{field}"') == count, field
                assert 'Synthetic train problem' in user
            if stage in ('slow_update', 'meta_skill'):
                assert 'Persistent Failures' in user and 'Synthetic train problem' in user
                assert '"answer_facts"' not in user and '"termination"' not in user
                assert '[verification] [EVALUATION RESULT]' in user and 'MCQ=0:' in user
                assert 'Predicted text:' in user and 'Correct text:' in user
                stable = user.split('### Stable Successes (right→right)', 1)[1]
                assert '[verification]' not in stable and 'Correct text:' not in stable
        except AssertionError as error:
            errors.append(str(error))
            raise
        stages[stage] += 1
        if stage.startswith('analyst'):
            payload = {'patch': {'edits': edits}, 'failure_summary': [{'failure_type': 'other', 'description': 'fixture'}]}
        elif stage.startswith('merge'):
            payload = {'edits': edits}
        elif stage == 'ranking':
            payload = {'selected_indices': [0, 1, 2, 3]}
        elif stage == 'slow_update':
            payload = {'slow_update_content': 'Fixture longitudinal guidance'}
        else:
            payload = {'meta_skill_content': 'Fixture optimizer memory'}
        return httpx.Response(200, json={'id': 'fixture', 'created': 1, 'object': 'chat.completion',
            'model': 'deepseek-flash', 'choices': [{'index': 0, 'finish_reason': 'stop', 'message':
                {'role': 'assistant', 'content': json.dumps(payload)}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 4, 'total_tokens': 14}})

    with TemporaryDirectory(prefix='lmb-skillopt-offline-') as temp, redirect_stdout(io.StringIO()), \
            patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline verification')) as network:
        root = Path(temp)
        parity = verify_real_actor_messages(root / 'prompt_parity', cfg, adapter, identity['actor'])
        fixture_data(root / 'data', adapter)
        local = dict(cfg, split_dir=str(root / 'data'), out_root=str(root / 'campaign'))
        simulated = run.LMBAdapter(local, adapter.test_workers)
        simulated.transport = FixtureActor(identity['actor'])
        run.freeze(root / 'optimizer.json', identity['optimizer'])
        with run.provider(root, api_key='offline', http_transport=httpx.MockTransport(reply)):
            selected = run.train(root, local, simulated)
        assert not errors, errors
        assert set(stages) >= {'analyst_error', 'analyst_success', 'ranking', 'merge_final', 'slow_update', 'meta_skill'}
        assert stages['slow_update'] == stages['meta_skill'] == 3
        history = run.read(root / 'campaign/history.json')
        assert len(history) == 4 and history[0]['action'].startswith('accept')
        assert all(not h['action'].startswith('accept') for h in history[1:])
        assert selected['selection_cases'] == 18 and selected['best_selection_em'] == 10 / 18 and selected['best_step'] == 1
        assert not (root / 'test').exists()
        for f in (root / 'campaign').rglob('binding.json'):
            ids = run.read(f)['ids']
            if 'selection' in f.parent.name:
                assert ids == run.read(run.COMMON_IDS)['val']
            else:
                assert all(simulated.split[uid] == 'train' for uid in ids)
        verify_final_promotion(root, local, simulated)
        verify_retry(root, simulated, simulated.dataloader.train_items[0])
        summary = simulated.test_best(root, local)
        assert summary['common_124']['completed'] == 124
        assert run.read(root / 'test/binding.json')['ids'] == run.read(run.COMMON_IDS)['test']
        assert summary['skill_sha256'] == selected['sha256'] and summary['actor_requests'] == 124
        with patch.object(FixtureActor, '__call__', side_effect=AssertionError('Unexpected repeated request')):
            assert simulated.test_best(root, local) == summary
        best_path = root / 'best_skill.md'
        best_path.write_text('changed after Selection')
        try:
            simulated.test_best(root, local)
        except ValueError as error:
            assert 'Best Skill differs' in str(error)
        else:
            raise AssertionError('Best Test accepted a different Skill')

        assert summary['actor_cost']['known_output_tokens'] == 124 * 4
        assert summary['actor_cost']['unknown_usage_slots'] == 0
        assert run.usage_summary(root)['optimizer']['http_requests'] == sum(stages.values())
        network.assert_not_called()
    return {'status': 'passed', 'mode': 'offline, synthetic Actor and optimizer', 'external_requests': 0,
            'configuration_sha256': run.digest(run.CONFIG), 'launcher_sha256': identity['launcher_sha256'],
            'actor_message_parity': parity, 'split_parity': split_parity,
            'actor': identity['actor'], 'optimizer': identity['optimizer'], 'input_checksums': identity['data'],
            'ordinary_updates': 4, 'selection_cases': 18, 'slow_update_cases': cfg['slow_update_samples'],
            'upstream': run.PIN, 'data_revision': identity['content_revision'],
            'split_counts': {'train': 35, 'selection': 18, 'test': 124}, 'native_epoch_ids': schedule,
            'mock_optimizer_calls': dict(stages), 'mock_selection': selected,
            'mock_best_test_coverage': 124, 'mock_strict_final_promotion': True,
            'actor_six_attempts_no_score_or_reset': True, 'ordinary_and_longitudinal_feedback_checked': True}
