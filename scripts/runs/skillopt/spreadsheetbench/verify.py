"""Offline acceptance using the two archived runs, synthetic workbooks and a simulated optimizer."""
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch


def no_network():
    return patch.object(socket.socket, 'connect', side_effect=AssertionError('Live network disabled'))


def verify_actor(root):
    # This part runs in the original SpreadsheetBench Python, separately from SkillOpt.
    from scripts.runs.skillopt.spreadsheetbench import worker
    from src.skill_evolution.shared.offline_records import offline_records
    from src.skill_evolution.skilladam.spreadsheetbench.aligned_actor.actor_runtime.benchmarks.spreadsheetbench import actor as adam
    from src.skill_evolution.v25_3.campaign import check_assets
    from tests.skill_evolution.v25 import support
    from src.skill_evolution.v25_3.stages import read
    from src.skill_evolution.v27.storage import write_record

    train, test = [read(root / f'{k}_actor.json') for k in ('train', 'test')]
    refs = read(root / 'verification_refs.json')
    with offline_records('spreadsheetbench') as path_type:
        contract_v, contract_a = [json.loads(path_type(p).read_bytes()) for p in refs['contracts']]
    names = ['actor.py', 'executor.py', 'scoring.py', 'protocol.py', 'transport.py', 'facts.py',
             'Dockerfile', 'prompts/actor_system.md', 'prompts/actor_initial.md',
             'prompts/actor_runtime_feedback.md', 'prompts/initial_skill.md']
    for name in names:
        suffix = '/benchmarks/spreadsheetbench/' + name
        a, = [content for path, content in contract_a.items() if path.endswith(suffix)]
        b, = [content for path, content in contract_v.items() if path.endswith(suffix)]
        assert a == b == (Path(worker.pipeline.actor.__file__).parent / name).read_text(), name
        assert a == (Path(adam.__file__).parent / name).read_text(), name
    check_assets(test)
    runtime = worker.pipeline.SpreadsheetBenchAdapter().runtime_snapshot(train)
    assert runtime == refs['docker']

    with TemporaryDirectory(dir=root) as temp, no_network():
        folder = Path(temp)
        fixture = support.config(folder / 'data', n=1, test=1)
        task, test_task = fixture['task_items'].values()
        skill = train['initial_skill']['text']
        train = {**train, 'task_items': fixture['task_items'], 'retry_delay_seconds': 0}
        responses = [support.response('BAD_FORMAT_FIXTURE'),
                     support.response('```python\n' + support.CODE % '' + '```')]
        def generator(log):
            def call(messages, directory, timeout, config):
                log.append((messages, timeout, config['call_config'], config['actor_profile']['actor_max_output_tokens']))
                return responses[len(log) - 1]
            return call
        logs = [[], [], []]
        destination = folder / 'rollout/predictions' / task['dataset_id']
        row = worker.rollout_case(task, skill, destination, train, generate=generator(logs[0]))
        for name, actor, log in [('v258', worker.pipeline.actor, logs[1]), ('skilladam', adam, logs[2])]:
            raw = read(actor.run(task, skill, folder / name, train, generate=generator(log)))
            assert raw['score'] == read(destination / 'actor/score.json')
        assert logs[0] == logs[1] == logs[2] and len(logs[0]) == 2
        assert row['hard'] == 0 and row['soft'] == 0.5 and row['n_cells_match'] == 1
        assert 'fail_reason' not in row
        assert row['n_cells_total'] == 2 and row['n_turns'] == 1
        evidence = (destination / 'conversation.json').read_text()
        outcome = json.loads(json.loads(evidence)[-1]['content'])['post_submission_outcome']
        assert outcome['termination'] == 'valid_workbook_submitted'
        assert outcome['score']['hard'] == 0 and outcome['score']['correct_cells'] == 1
        assert 'BAD_FORMAT_FIXTURE' not in evidence and 'post_submission_outcome' in evidence
        assert task['answer_path'] not in evidence and 'post_submission_outcome' not in str(logs[0])
        forbidden = Mock(side_effect=AssertionError('Repeated model request'))
        assert worker.rollout_case(task, skill, destination, train, generate=forbidden) == row
        # Dispatch the real batch subprocess over a completed synthetic Actor record.
        write_record(folder / 'train_actor.json', train)
        write_record(folder / 'rollout/binding.json', {'tasks': [task['id']], 'skill': skill})
        subprocess.run([sys.executable, worker.__file__, 'batch', str(folder), str(folder / 'rollout')],
                       cwd=worker.ROOT, env={**os.environ, 'OPENAI_API_KEY': ''}, check=True)
        assert json.loads((folder / 'rollout/results.jsonl').read_text()) == row
        # Exercise the normal evaluation writer and score aggregation with one synthetic Test task.
        test = {**test, 'test_tasks': [test_task['id']], 'task_items': fixture['task_items']}
        (folder / 'best_skill.md').write_text(skill)
        write_record(folder / 'selection.json', dict(best_step=3, sha256=hashlib.sha256(skill.encode()).hexdigest()))
        def correct(*args):
            return support.response('```python\n' + support.CODE % ' + 1' + '```')
        result = worker.test_best(folder, test, generate=correct)
        assert result['hard'] == result['per_cell_pass_rate'] == result['success'] == result['completed'] == 1
        assert worker.test_best(folder, test, generate=forbidden)['tasks'] == result['tasks']
        forbidden.assert_not_called()
    write_record(root / 'actor_verification.json', dict(status='passed', contracts=names, workbooks=800,
                 docker=runtime, equal_actor_requests=2, partial_score=[0, 0.5], synthetic_test_score=[1, 1]))


def verify(root, cfg, adapter):
    from scripts.runs.skillopt.spreadsheetbench import run
    from skillopt import model
    from skillopt.model import openai_compatible_backend as backend
    from openai.types.chat import ChatCompletion
    from src.skill_evolution.v25_3.stages import read, freeze
    from src.skill_evolution.v27.storage import write_record

    freeze(root / 'verification_refs.json', dict(contracts=[str(run.V25 / 'test/contract.json'),
           str(run.ADAM / 'test280/contract.json')], docker=read(run.V25 / 'runtime.json')['docker']))
    run.worker('verify', root)
    default = run.legacy.native_defaults()
    overrides = {k for k in cfg if cfg[k] != default[k]}
    assert overrides <= {'model_backend', 'optimizer_backend', 'target_backend', 'optimizer_model', 'target_model',
                         'skill_init', 'out_root', 'split_dir', 'data_root', 'workers', 'max_completion_tokens', 'eval_test',
                         'slow_update_gate_with_selection'}
    assert cfg['use_gate'] and cfg['slow_update_gate_with_selection']
    assert cfg['max_analyst_rounds'] == 3 and cfg['minibatch_size'] == cfg['merge_batch_size'] == 8
    schedule = []
    train_ids = {str(i['id']) for i in adapter.dataloader.train_items}
    for epoch in range(1, 5):
        batches = adapter.dataloader.plan_train_epoch(epoch=epoch, steps_per_epoch=2, accumulation=1,
                                                      batch_size=cfg['batch_size'], seed=cfg['seed'])
        parts = [[str(t['id']) for t in b.payload] for b in batches]
        assert list(map(len, parts)) == [40, 40] and set(parts[0] + parts[1]) == train_ids
        schedule.append(parts)
    shared = read(root / 'train_actor.json')
    stages = Counter()
    # Simulate the optimizer backend only. Native reflection, merge, ranking, gate and epoch updates execute.
    edits = [dict(op='append', content=f'Synthetic edit {n}') for n in range(6)]
    def reply(*, stage, system, user, max_completion_tokens, retries, **kwargs):
        stages[stage] += 1
        assert max_completion_tokens == 16384
        if stage == 'analyst':
            assert 'synthetic trajectory' in user
            assert system in (adapter.get_error_minibatch_prompt(), adapter.get_success_minibatch_prompt())
            data = {'patch': {'edits': edits}}
        else:
            if stage in ('slow_update', 'meta_skill'):
                assert 'synthetic trajectory' in user
            data = {'merge': {'edits': edits}, 'ranking': {'selected_indices': [0, 1, 2, 3]},
                    'slow_update': {'slow_update_content': f'Synthetic slow {stages[stage]}'},
                    'meta_skill': {'meta_skill_content': 'Synthetic teacher memory'}}[stage]
        return json.dumps(data), {}

    with TemporaryDirectory(dir=root) as temp, no_network():
        out = Path(temp)
        local = {**cfg, 'out_root': str(out / 'campaign')}
        bridge = run.SharedActor(out, local, shared)
        def simulate(action, root, directory):
            assert action == 'batch'
            request = read(directory / 'binding.json')
            rows = []
            for i, key in enumerate(request['tasks']):
                task = shared['task_items'][key]
                assert task['split'] in ('train', 'val')
                if task['split'] == 'val':
                    assert request['tasks'] == [f"val:{t['id']}" for t in bridge.dataloader.val_items]
                hard = int(i % 2 == 0)
                if task['split'] == 'val' and 'Synthetic edit 0' in request['skill'] and i == 1:
                    hard = 1
                if task['split'] == 'val' and 'Synthetic slow 3' in request['skill']:
                    hard = 1
                tid = task['dataset_id']
                pred = directory / 'predictions' / tid
                pred.mkdir(parents=True, exist_ok=True)
                write_record(pred / 'conversation.json', [dict(role='assistant', content='synthetic trajectory')])
                rows.append(dict(id=tid, hard=hard, soft=hard, task_type='cell_level', task_description='fixture'))
            (directory / 'results.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
        client = Mock()
        client.chat.completions.create.return_value = ChatCompletion.model_validate({
            'id': 'offline', 'object': 'chat.completion', 'created': 0, 'model': 'deepseek-flash',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'ok'}}]})
        with patch.dict(os.environ, OPENAI_API_KEY='synthetic', OPENAI_BASE_URL=shared['actor_base_url']), \
             patch('dotenv.load_dotenv'), patch.object(backend, '_get_client', return_value=client):
            run.legacy.configure_model(shared)
            model.set_optimizer_backend('openai_compatible')
            model.chat_optimizer('mock', 'mock', max_completion_tokens=16384)
            body = client.chat.completions.create.call_args.kwargs
            assert body['model'] == 'deepseek-flash' and body['max_tokens'] == 16384 and body['temperature'] == 1
            assert body['extra_body'] == {k: shared['call_config'][k] for k in ('thinking', 'reasoning_effort', 'stream')}
            assert backend.OPTIMIZER_CONFIG.base_url == shared['actor_base_url']
        with patch.object(run, 'worker', side_effect=simulate), patch.object(backend, 'chat_optimizer', side_effect=reply), \
             redirect_stdout(io.StringIO()):
            result = run.train(out, local, bridge)
            assert run.train(out, local, bridge) == result
        history = read(out / 'campaign/history.json')
        assert [h['action'] for h in history] == ['accept_new_best'] + ['reject'] * 7
        budgets = [h['edit_budget'] for h in history]
        assert budgets == [4, 4, 3, 3, 3, 2, 2, 2], budgets
        assert all(stages[k] for k in ('analyst', 'merge', 'ranking'))
        assert stages['slow_update'] == stages['meta_skill'] == 3
        assert result['best_step'] == 8 and result['best_selection_hard'] == 1.0
        from scripts.runs.skillopt.spreadsheetbench.worker import verify_slow_gate
        slow_actions = []
        for epoch in (2, 3, 4):
            verify_slow_gate(out / 'campaign', epoch, [f"val:{t['id']}" for t in bridge.dataloader.val_items])
            d = out / 'campaign/slow_update' / f'epoch_{epoch:02d}'
            slow = read(d / 'slow_result.json')
            assert slow['selection_hard'] == (1.0 if epoch == 4 else 0.525)
            assert len((d / 'selection_eval/results.jsonl').read_text().splitlines()) == 40
            slow_actions.append(slow['action'])
        assert slow_actions == ['reject', 'reject', 'accept_new_best']
        assert result['best_origin'] == 'slow_update_epoch_04' and not (out / 'test').exists()
        try:
            bridge.rollout(bridge.dataloader.test_items, 'fixture', out / 'forbidden')
        except ValueError:
            pass
        else:
            raise AssertionError('Training accepted Test inputs')
    report = dict(status='passed', upstream=run.PIN, actor=read(root / 'actor_verification.json'),
                  split_counts=[80, 40, 280], epoch_batches=schedule, synthetic_edit_budgets=budgets,
                  synthetic_optimizer_stages=dict(stages), synthetic_gate_actions=[h['action'] for h in history],
                  optimizer_backend='openai_compatible', synthetic_best=result, synthetic_slow_gate_actions=slow_actions,
                  model_api_requests=0, real_benchmark_rollouts=0)
    write_record(root / 'offline_verification.json', report)
    print('Offline verification passed:', root / 'offline_verification.json')
