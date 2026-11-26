"""Offline contract checks plus a small end-to-end native run with synthetic providers."""
from collections import Counter
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import random
import re
import socket
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import httpx as http
from skillopt.prompts import load_prompt
from scripts.runs.skillopt.searchqa import run
from src.skill_evolution.v28.storage import save
from src.skill_evolution.v27.transport import RequestFailure
from tests.skill_evolution.v28.runtime_support import Dataset, Transport, response, HIDDEN


def check_config(cfg, adapter, identity):
    expected = {
        'train_size': 400, 'num_epochs': 4, 'batch_size': 40, 'accumulation': 1, 'seed': 42,
        'minibatch_size': 8, 'merge_batch_size': 8, 'analyst_workers': 16, 'max_analyst_rounds': 3,
        'failure_only': False, 'edit_budget': 4, 'min_edit_budget': 2, 'lr_scheduler': 'cosine',
        'lr_control_mode': 'fixed', 'skill_update_mode': 'patch', 'use_gate': True, 'gate_metric': 'hard',
        'use_slow_update': True, 'slow_update_samples': 20, 'slow_update_gate_with_selection': True,
        'use_meta_skill': True, 'longitudinal_pair_policy': 'mixed', 'sel_env_num': 200,
        'test_env_num': 1400, 'eval_test': False, 'max_turns': 1,
        'optimizer_backend': 'openai_compatible', 'target_backend': 'openai_compatible',
    }
    TestCase().assertDictEqual({k: cfg[k] for k in expected}, expected)
    loader = adapter.dataloader
    ids = {s: [r['id'] for r in loader.get_split_items(s)] for s in ('train', 'val', 'test')}
    assert [len(v) for v in ids.values()] == [400, 200, 1400]
    assert len(set(ids['train'] + ids['val'] + ids['test'])) == 2000
    for epoch in range(1, 5):
        batches = loader.plan_train_epoch(epoch=epoch, steps_per_epoch=10, accumulation=1, batch_size=40, seed=42)
        expected_order = ids['train'].copy()
        random.Random(42 + epoch * 1000).shuffle(expected_order)
        assert [r['id'] for b in batches for r in b.payload] == expected_order
        assert [b.batch_size for b in batches] == [40] * 10
    assert [r['id'] for r in adapter.build_eval_env(200, 'valid_seen', 42)] == ids['val']
    assert [r['id'] for r in adapter.build_eval_env(1400, 'valid_unseen', 42)] == ids['test']
    v28 = 'v28_16_searchqa600_batch60_20261112_132531'
    adam = 'v28_11_aligned_batch60_20261116_123000'
    ex = run.ROOT / 'experiments'
    frozen = run.read(ex / 'baselines/searchqa_skilladam' / adam / 'frozen.json')
    config = run.read(ex / 'campaigns' / v28 / 'config.json')
    initial = Path(cfg['skill_init']).read_text()
    assert initial == config['initial_skill']['text'] == frozen['initial_skill']
    assert config['actor'] == identity['actor'] == frozen['config']['actor']
    assert frozen['native']['optimization_case_ids'] == ids['train'] + ids['val']
    for path in [ex / 'evaluations' / (v28 + '_test1400/evaluation.json'),
                 ex / 'evaluations/searchqa_skilladam' / adam / 'plan.json']:
        plan = run.read(path)
        assert plan['tasks'] == ids['test'] and plan['workers'] == identity['test_workers'] == 15
        assert plan['actor'] == identity['actor']
    return {k: len(v) for k, v in ids.items()}


def fixture(root, cfg):
    data = Dataset(size=0)
    data.batch_size = 60  # Shared Actor budget selector, independent of SkillOpt's rollout batch.
    data.splits = {'train': [], 'test': []}
    for split, count in [('train', 20), ('val', 4), ('test', 4)]:
        items = []
        for n in range(count):
            uid = f'{split}-{n}'
            item = dict(id=uid, question=f'Synthetic {split} item {n}', context='[DOC] Synthetic passage.',
                        answers=['New York City'])
            items.append(item)
            data.rows[uid] = dict(item, source_split=split)
            data.splits['test' if split == 'test' else 'train'].append(uid)
        save(root / 'data' / split / 'items.json', items)
    local = dict(cfg, split_dir=str(root / 'data'), out_root=str(root / 'campaign'),
                 train_size=20, sel_env_num=4, test_env_num=4)
    adapter = run.SharedSearchQA(local, data)

    def answer(messages, slot):
        body = run.read(slot / 'request.json')['body']
        sig = run.read(slot.parents[1] / 'signature.json')
        assert messages == body['messages'] == run.protocol.messages(sig['payload'], sig['skill'])
        assert body['model'] == 'deepseek-flash' and body['max_tokens'] == 32768
        assert body['reasoning_effort'] == 'medium' and body['thinking'] == {'type': 'enabled'}
        assert body['temperature'] == 1 and body['stream'] is False
        assert 'New York City' not in json.dumps(messages)
        index = int(sig['payload']['question'].split()[-1])
        correct = index % 2 == 0 or (index == 1 and 'OFFLINE EDIT' in sig['skill'])
        return response('<answer>New York City</answer>' if correct else '<answer>New York</answer>')

    mock_actor = Transport(answer)
    mock_actor.config = run.protocol.actor_config(60)
    adapter.shared.transport = mock_actor
    return local, adapter


def exercise(root, cfg, identity):
    local, adapter = fixture(root, cfg)
    stages = Counter()
    prompts = {load_prompt(k): k for k in ('merge_failure', 'merge_success', 'merge_final',
                                           'ranking', 'slow_update', 'meta_skill')}
    for k in ('analyst_error', 'analyst_success'):
        prompts[load_prompt(k, env='searchqa')] = k
    edits = [{'op': 'append', 'content': f'OFFLINE EDIT {i}'} for i in range(6)]
    errors = []

    def reply(request):
        body = json.loads(request.content)
        system, user = [msg['content'] for msg in body['messages']]
        try:
            stage = prompts[system]
            assert str(request.url) == identity['actor']['endpoint']
            assert body['model'] == 'deepseek-flash' and body['temperature'] == 1
            assert body['thinking'] == {'type': 'enabled'} and body['reasoning_effort'] == 'medium'
            assert body['stream'] is False and body['max_tokens'] == 16384
            assert HIDDEN not in user and 'Synthetic test' not in user and 'Synthetic val' not in user
            if stage.startswith('analyst'):
                assert '[EVALUATION RESULT]' in user and 'Synthetic train' in user
                assert 'Target System Prompt' in user and 'Target User Prompt' in user
        except (AssertionError, KeyError) as error:
            errors.append(repr(error))
            raise
        stages[stage] += 1
        if stage.startswith('analyst'):
            payload = {'patch': {'edits': edits}, 'failure_summary': [{'failure_type': 'other', 'description': 'fixture'}]}
        elif stage.startswith('merge'):
            payload = {'edits': edits}
        elif stage == 'ranking':
            budget = int(re.search(r'budget=(\d+)\)', user)[1])
            payload = {'selected_indices': list(range(budget))}
        elif stage == 'slow_update':
            payload = {'slow_update_content': 'Offline longitudinal guidance'}
        else:
            payload = {'meta_skill_content': 'Offline teacher memory'}
        return http.Response(200, json={'id': 'fixture', 'created': 1, 'object': 'chat.completion',
            'model': 'deepseek-flash', 'choices': [{'index': 0, 'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': json.dumps(payload)}}]})

    expect = TestCase()
    with expect.assertRaises(FileNotFoundError):
        run.test_best(root, adapter)
    with expect.assertRaisesRegex(ValueError, 'non-Test split'):
        adapter.rollout(adapter.dataloader.test_items, 'fixture', root / 'forbidden')
    save(root / 'optimizer.json', identity['optimizer'])
    with patch.dict(run.os.environ, {'OPTIMIZER_OPENAI_COMPATIBLE_EXTRA_BODY': '{"temperature":0}'}):
        with run.optimizer_provider(root, 'offline', http_transport=http.MockTransport(reply)):
            selection = run.train(root, local, adapter)
    assert not errors, errors
    assert stages['slow_update'] == stages['meta_skill'] == 3
    assert all(stages[k] for k in ('analyst_error', 'analyst_success', 'merge_final', 'ranking'))
    assert selection['best_step'] == 1 and selection['selection_em'] == 0.75
    history = run.read(root / 'campaign/history.json')
    assert len(history) == 4 and history[0]['action'] == 'accept_new_best'
    assert all(row['action'] == 'reject' for row in history[1:])
    for epoch in range(2, 5):
        slow = root / 'campaign/slow_update' / f'epoch_{epoch:02}'
        assert run.read(slow / 'slow_result.json')['action'] == 'reject'
        assert len(run.read(slow / 'comparison_pairs.json')) == 20
    assert not (root / 'test').exists()
    for path in (root / 'campaign').rglob('batch/batch.json'):
        ids = run.read(path)['signature']['tasks']
        if 'selection' in str(path.relative_to(root / 'campaign')):
            assert ids == [r['id'] for r in adapter.dataloader.val_items]
        else:
            assert all(uid.startswith('train-') for uid in ids)

    item = adapter.dataloader.train_items[:1]
    transport = adapter.shared.transport
    before = transport.calls
    with patch.object(transport, 'fn', return_value=response(finish='length')), patch.object(run.actor.time, 'sleep'):
        for _ in range(2):
            with expect.assertRaises(RequestFailure):
                adapter.rollout(item, 'fixture', root / 'truncated')
        assert transport.calls == before + 6 and not (root / 'truncated/results.jsonl').exists()

    report = run.test_best(root, adapter)
    assert report['status'] == 'complete' and report['summary']['success_count'] == 3
    assert abs(report['summary']['f1'] - 0.95) < 1e-9 and report['actor_requests'] == report['completed'] == 4
    assert report['optimization_updates'] is False
    before = transport.calls
    assert run.test_best(root, adapter) == report and transport.calls == before
    (root / 'best_skill.md').write_text('changed')
    with expect.assertRaisesRegex(ValueError, 'Best Skill differs'):
        run.test_best(root, adapter)
    return dict(epochs=4, regular_steps=len(history), optimizer_stages=dict(stages),
                held_out_gate_checked=True, best_test_cases=4, six_attempt_limit_checked=True,
                completed_test_reused=True, modified_best_rejected=True)


def verify(cfg, adapter, identity):
    from scripts.runs.skillopt.searchqa.verify_retry import verify_archives

    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network disabled')) as network:
        splits = check_config(cfg, adapter, identity)
        with TemporaryDirectory(prefix='searchqa-skillopt-offline-') as tmp, redirect_stdout(io.StringIO()):
            result = exercise(Path(tmp), cfg, identity)
            archives = verify_archives(Path(tmp), identity)
        network.assert_not_called()
    return dict(status='passed', mode='offline', external_requests=0, formal_training_started=False,
                train_workers=adapter.shared.workers, analyst_workers=cfg['analyst_workers'],
                split_counts=splits, verified_training_schedule='4 epochs x 10 batches x 40 cases',
                actor=identity['actor'], optimizer=identity['optimizer'], test_workers=identity['test_workers'],
                config_sha256=run.protocol.file_digest(run.CONFIG),
                sources_sha256=run.protocol.digest(identity['source_sha256']), synthetic=result,
                optimizer_retry=identity['optimizer_retry'], archive_replay=archives)
