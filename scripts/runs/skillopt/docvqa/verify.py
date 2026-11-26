"""Network-blocked verification against published inputs and a full native mock campaign."""
from collections import Counter
from contextlib import redirect_stdout
import csv
import importlib
import io
import json
from pathlib import Path
import random
import socket
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from openai import DefaultHttpxClient
from PIL import Image
from skilladam.types import BenchmarkCase
from skillopt.envs.docvqa.evaluator import evaluate
from skillopt.envs.docvqa.rollout import _build_messages
from skillopt.prompts import load_prompt

from scripts.runs.skillopt.docvqa import run
from tests.skill_evolution.v29.test_actor import HIDDEN, Transport, response


def check_inputs(cfg, adapter):
    expected = dict(num_epochs=4, batch_size=40, accumulation=1, seed=42, minibatch_size=8,
                    merge_batch_size=8, analyst_workers=16, max_analyst_rounds=3, failure_only=False,
                    edit_budget=4, min_edit_budget=2, lr_scheduler='cosine', skill_update_mode='patch',
                    use_gate=True, gate_metric='hard', use_slow_update=True, slow_update_samples=20,
                    slow_update_gate_with_selection=True, use_meta_skill=True, longitudinal_pair_policy='mixed',
                    sel_env_num=53, test_env_num=374, eval_test=False, max_turns=1, workers=16,
                    image_detail='auto', target_backend='openai_compatible', optimizer_backend='openai_compatible')
    TestCase().assertDictEqual({k: cfg[k] for k in expected}, expected)
    data = adapter.shared.dataset
    ids = data.source_ids
    assert [len(ids[k]) for k in ('train', 'val', 'test')] == [107, 53, 374]
    assert len(set(ids['train'] + ids['val'] + ids['test'])) == 534
    for epoch in range(1, 5):
        order = list(ids['train'])
        random.Random(42 + epoch * 1000).shuffle(order)
        batches = adapter.dataloader.plan_train_epoch(epoch=epoch, steps_per_epoch=3, accumulation=1,
                                                       batch_size=40, seed=42)
        assert [b.batch_size for b in batches] == [40, 40, 27]
        assert [r['id'] for b in batches for r in b.payload] == order
    assert [r['id'] for r in adapter.build_eval_env(53, 'valid_seen', 42)] == ids['val']
    assert [r['id'] for r in adapter.build_eval_env(374, 'valid_unseen', 42)] == ids['test']
    skill = Path(cfg['skill_init']).read_text()
    for split in ids:
        for item in adapter.dataloader.get_split_items(split):
            case = data.case(item['id'])
            shared = run.protocol.messages_for_case(case, skill)
            assert shared == _build_messages(item, skill, 'auto')[0], item['id']
            for text in (f"<answer>{case.reference[0]}</answer>", '<answer>?</answer>'):
                native = evaluate(text, item['answers'])
                answer, metrics = run.scoring.score(text, case.reference)
                assert native['predicted_answer'] == answer['extracted_answer']
                assert metrics == {'hard': int(native['anls'] >= 0.999), 'anls': native['anls']}


def fixture(root, cfg, ids):
    # Exercise the real scale and split order, with tiny image/answer fixtures for durable I/O.
    image = root / 'page.png'
    Image.new('RGB', (3, 3), 'white').save(image)
    cases = {}
    for split, members in ids.items():
        directory = root / 'csv' / split
        directory.mkdir(parents=True)
        with (directory / 'items.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['questionId', 'question', 'image_path', 'answer'])
            writer.writeheader()
            for index, uid in enumerate(members):
                question = f'Synthetic {split} question {index}'
                answers = ['fixture answer']
                cases[uid] = BenchmarkCase(uid, {'image_path': image.name, 'question': question}, answers,
                    {'source_split': split, 'split': 'test' if split == 'test' else 'train', 'image_root': str(root)})
                writer.writerow(dict(questionId=uid, question=question, image_path=str(image), answer=repr(answers)))
    local = dict(cfg, split_dir=str(root / 'csv'), out_root=str(root / 'campaign'))
    dataset = SimpleNamespace(root=root, source_ids=ids, case=cases.__getitem__)
    adapter = run.SharedDocVQA(local, dataset)

    def answer(messages, slot):
        body = run.read(slot / 'request.json')['body']
        assert body['messages'] == messages and body['model'] == 'deepseek-flash'
        assert body['max_tokens'] == 32768 and body['temperature'] == 1 and body['stream'] is False
        assert body['reasoning_effort'] == 'medium' and body['thinking'] == {'type': 'enabled'}
        user = messages[1]['content']
        assert user[1]['image_url']['url'].startswith('data:image/png;base64,')
        assert 'fixture answer' not in user[0]['text']
        index = int(user[0]['text'].splitlines()[0].split()[-1])
        correct = index % 2 == 0 or (index == 1 and 'OFFLINE EDIT' in messages[0]['content'])
        return response('<answer>fixture answer</answer>' if correct else '<answer>fixture answe</answer>')

    adapter.shared.transport = Transport(answer)
    return local, adapter


def exercise(root, cfg, real, identity):
    local, adapter = fixture(root, cfg, real.shared.dataset.source_ids)
    stages = Counter()
    prompts = {load_prompt(k): k for k in ('merge_failure', 'merge_success', 'merge_final', 'ranking',
                                           'slow_update', 'meta_skill')}
    for name in ('analyst_error', 'analyst_success'):
        prompts[load_prompt(name, env='docvqa')] = name
    edits = [{'op': 'append', 'content': f'OFFLINE EDIT {i}'} for i in range(6)]
    http = importlib.import_module(DefaultHttpxClient.__mro__[1].__module__.split('.')[0])
    errors = []

    def reply(request):
        body = json.loads(request.content)
        system, user = [m['content'] for m in body['messages']]
        try:
            stage = prompts[system]
            assert str(request.url) == identity['actor']['endpoint'] and body['model'] == 'deepseek-flash'
            assert body['temperature'] == 1 and body['thinking'] == {'type': 'enabled'}
            assert body['max_tokens'] == 16384 and body['reasoning_effort'] == 'medium' and body['stream'] is False
            assert 'data:image/' not in user and HIDDEN not in user
            assert 'Synthetic val' not in user and 'Synthetic test' not in user
            if stage.startswith('analyst'):
                assert all(s in user for s in ('Synthetic train', 'Target System Prompt', 'Target User Prompt',
                                               'Gold answers:', 'ANLS:', '[image] page.png'))
        except (AssertionError, KeyError) as error:
            errors.append(str(error) or 'Unexpected optimizer request')
            raise
        stages[stage] += 1
        if stage.startswith('analyst'):
            payload = {'patch': {'edits': edits}, 'failure_summary': [{'failure_type': 'other', 'description': 'fixture'}]}
        elif stage.startswith('merge'):
            payload = {'edits': edits}
        elif stage == 'ranking':
            payload = {'selected_indices': [0, 1, 2, 3]}
        elif stage == 'slow_update':
            payload = {'slow_update_content': 'Offline longitudinal guidance'}
        else:
            payload = {'meta_skill_content': 'Offline teacher memory'}
        return http.Response(200, json={'id': 'offline', 'created': 1, 'object': 'chat.completion',
            'model': 'deepseek-flash', 'choices': [{'index': 0, 'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': json.dumps(payload)}}]})

    expect = TestCase()
    with expect.assertRaises(FileNotFoundError):
        run.test_best(root, adapter)
    with expect.assertRaisesRegex(ValueError, 'one Train or Val'):
        adapter.rollout(adapter.dataloader.test_items, 'fixture', root / 'forbidden')
    run.freeze(root / 'optimizer.json', identity['optimizer'])
    with run.optimizer_provider(root, 'offline', http_transport=http.MockTransport(reply)):
        selection = run.train(root, local, adapter)
    assert not errors, errors
    assert all(stages[k] > 0 for k in prompts.values()), stages
    assert stages['slow_update'] == stages['meta_skill'] == 3
    assert selection['best_step'] == 1 and selection['selection_hard'] == 28 / 53
    campaign = root / 'campaign'
    ids = adapter.shared.dataset.source_ids
    history = run.read(campaign / 'history.json')
    assert len(history) == 12 and history[0]['action'] == 'accept_new_best'
    assert all(row['action'] == 'reject' for row in history[1:])
    for epoch in range(1, 5):
        epoch_tasks = []
        for index, size in enumerate((40, 40, 27), 1):
            step = (epoch - 1) * 3 + index
            batch = run.read(campaign / f'steps/step_{step:04}/rollout/batch/batch.json')
            tasks = batch['signature']['tasks']
            assert len(tasks) == size
            epoch_tasks.extend(tasks)
        order = list(ids['train'])
        random.Random(42 + epoch * 1000).shuffle(order)
        assert order == epoch_tasks
        slow = campaign / f'slow_update/epoch_{epoch:02}'
        if epoch > 1:
            assert run.read(slow / 'slow_result.json')['action'] == 'reject'
            assert len(run.read(slow / 'comparison_pairs.json')) == 20
    for path in campaign.rglob('batch/batch.json'):
        tasks = run.read(path)['signature']['tasks']
        if 'selection' in str(path.relative_to(campaign)):
            assert tasks == ids['val']
        else:
            assert set(tasks) <= set(ids['train'])
    assert not (root / 'test').exists()
    calls = len(adapter.shared.transport.seen)
    assert run.train(root, local, adapter) == selection and len(adapter.shared.transport.seen) == calls
    report = run.test_best(root, adapter)
    assert report['sample_count'] == report['api_requests'] == 374 and report['success_count'] == 188
    assert abs(report['anls'] - (188 + 186 * 13 / 14) / 374) < 1e-9
    assert run.read(root / 'test/evaluation.json')['tasks'] == ids['test']
    calls = len(adapter.shared.transport.seen)
    assert run.test_best(root, adapter) == report and len(adapter.shared.transport.seen) == calls
    # A lost reply for the last ID of an independent replicate must leave the
    # first Test intact. On retry, the shared Actor reuses the other 373 results.
    transport = adapter.shared.transport
    generate = transport.generate

    def interrupted(messages, slot):
        if slot.parents[1].name == '0374':
            raise InterruptedError('Lost fixture reply')
        return generate(messages, slot)

    with patch.object(transport, 'generate', side_effect=interrupted):
        with expect.assertRaises(InterruptedError):
            run.test_best(root, adapter, repeat=2)
    assert not (root / 'test_repeat_2/summary.json').exists()
    assert run.read(root / 'test/summary.json') == report
    calls = len(transport.seen)
    with patch.object(run.actor.time, 'sleep'):
        resumed = run.test_best(root, adapter, repeat=2)
    assert resumed == {**report, 'api_requests': 375} and len(transport.seen) == calls + 1
    (root / 'best_skill.md').write_text('changed')
    with expect.assertRaisesRegex(ValueError, 'Best Skill differs'):
        run.test_best(root, adapter)
    return dict(epochs=4, regular_steps=12, regular_training_cases=428,
                held_out_selection_cases=53, frozen_test_cases=374, optimizer_mock_calls=dict(stages),
                accepted_and_tied_candidates_checked=True, completed_test_reused=True,
                interrupted_replicate_resumed=True, modified_best_rejected=True)


def verify(root):
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('External network disabled')) as network:
        cfg, adapter, identity = run.prepare(root)
        check_inputs(cfg, adapter)
        with TemporaryDirectory(prefix='docvqa-skillopt-offline-') as tmp, redirect_stdout(io.StringIO()):
            checks = exercise(Path(tmp).resolve(), cfg, adapter, identity)
        network.assert_not_called()
    return dict(status='passed', mode='offline', external_requests=0, formal_training_started=False,
                split_counts={k: len(v) for k, v in adapter.shared.dataset.source_ids.items()},
                config_sha256=run.sha(run.CONFIG), runner_sha256=run.sha(run.__file__),
                verifier_sha256=run.sha(__file__),
                official_messages_and_scores_checked=534, batch_sizes_per_epoch=[40, 40, 27],
                actor=identity['actor'], optimizer=identity['optimizer'], train_workers=adapter.workers,
                test_workers=adapter.shared.test_workers, synthetic=checks)
