"""Offline only: mocked HTTP, synthetic episodes, and recorded historical evidence."""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.skillopt_alfworld_native import project as p
from src.skillopt_alfworld_native.actor import build_adapter, command, convert_record, run_episode, ActorInterrupted
from src.skillopt_alfworld_native.transport import provider, usage_summary


@contextlib.contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix='skillopt_native_offline_') as temp:
        root = Path(temp)
        for name in ('actor.json', 'optimizer.json', 'initial_skill.md'):
            shutil.copyfile(p.DEFAULT / name, root / name)
        shutil.copytree(p.DEFAULT / 'splits', root / 'splits')
        cfg = p.read(p.DEFAULT / 'skillopt.json')
        cfg.update(split_dir=str(root / 'splits'), out_root=str(root / 'campaign'), skill_init=str(root / 'initial_skill.md'))
        p.write(root / 'skillopt.json', cfg)
        p.write(root / 'manifest.json', {'offline_fixture': True})
        yield root


def response(content):
    return {'id': 'offline', 'object': 'chat.completion', 'created': 0, 'model': 'deepseek-flash',
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18}}


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p.select_upstream(p.DEFAULT)

    def setUp(self):
        self.network = patch('socket.socket.connect', side_effect=AssertionError('network forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_offline_default_and_run_without_start(self):
        spec = importlib.util.spec_from_file_location('native_cli', ROOT / 'scripts/runs/run_skillopt_alfworld_native.py')
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with patch.object(p, 'actor_runtime', return_value=p.read(p.DEFAULT / 'actor_runtime.json')), \
             patch('subprocess.run', side_effect=AssertionError('process forbidden')), \
             patch.object(cli, 'run', side_effect=AssertionError('live run forbidden')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main([]), 0)
            self.assertEqual(cli.main(['run']), 0)
        self.assertFalse((p.DEFAULT / 'campaign').exists())

    def test_pinned_source_and_only_evaluation_patch(self):
        source = p.read(p.DEFAULT / 'upstream_source.json')
        for rel, digest in source['original_files'].items():
            if rel != 'skillopt/engine/trainer.py':
                self.assertEqual(p.sha(p.DEFAULT / 'upstream' / rel), digest, rel)
        import subprocess
        original = subprocess.check_output(['git', '-C', str(p.SOURCE), 'show',
            p.COMMIT + ':skillopt/engine/trainer.py'], text=True)
        actual = (p.DEFAULT / 'upstream/skillopt/engine/trainer.py').read_text()
        self.assertEqual(actual, p.best_only_trainer(original))
        marker = '        # ── Final test evaluation'
        self.assertEqual(original.split(marker)[0], actual.split(marker)[0])

    def test_actor_alignment_and_native_schedule_prompts(self):
        from src.adapters.alfworld import skill_runtime as a
        from src.skill_evolution.v24_1.benchmarks.alfworld.actor import skill_runtime as b
        actor = p.read(p.DEFAULT / 'actor.json')
        self.assertNotIn('optimizer_request_attempts', actor)
        self.assertEqual((p.DEFAULT / 'initial_skill.md').read_bytes(), (p.ADAM / 'initial_skill.md').read_bytes())
        for length in (0, 1, 2, 3, 50):
            history = [{'observation': f'obs {i}', 'action': 'look'} for i in range(length)]
            args = ('Your task is to: place mug', ['help', 'look'], 'place mug', history)
            kw = {'injection': 'skillopt_user_v1', 'output_format': 'action_only_v1'}
            self.assertEqual(a.build_skill_messages(*args, a.load_skill(p.DEFAULT / 'initial_skill.md'), **kw),
                             b.build_skill_messages(*args, b.load_skill(p.DEFAULT / 'initial_skill.md'), **kw))
        item = p.read(p.DEFAULT / 'splits/train/items.json')[0]
        cmd = command(actor, item, Path('/unused'), Path('/unused.md'))
        self.assertEqual(cmd[cmd.index('--request-attempts') + 1], '6')
        self.assertTrue({'--strict-response', '--retry-invalid-actions', '--action-feedback', '--archive-responses'} <= set(cmd))
        adapter = build_adapter(p.DEFAULT)
        adapter.setup(p.read(p.DEFAULT / 'skillopt.json'))
        loader = adapter.get_dataloader()
        for epoch in range(1, 5):
            batches = loader.plan_train_epoch(epoch=epoch, steps_per_epoch=1, accumulation=1, batch_size=40, seed=42)
            self.assertEqual([x.batch_size for x in batches], [39])
            self.assertEqual({x['id'] for x in batches[0].payload}, {x['id'] for x in loader.train_items})
        for kind in ('success', 'error'):
            self.assertEqual(getattr(adapter, f'get_{kind}_minibatch_prompt')(),
                (p.DEFAULT / f'upstream/skillopt/envs/alfworld/prompts/analyst_{kind}.md').read_text())

    def test_actor_six_attempts_and_feedback_match_v24(self):
        from src.adapters.alfworld.run_task_upstream import chat as shared
        from src.skill_evolution.v24_1.benchmarks.alfworld.actor.run_task_upstream import chat as v24
        def exercise(chat, succeed):
            calls = []
            def post(*args, **kwargs):
                calls.append(json.loads(json.dumps(kwargs['json'])))
                content = '<action>look</action>' if succeed and len(calls) == 6 else f'<action>invalid {len(calls)}</action>'
                return SimpleNamespace(ok=True, status_code=200, json=lambda: response(content))
            with patch('time.sleep'):
                try:
                    value = chat(SimpleNamespace(post=post), 'https://unused', 'fake', 'deepseek-flash',
                        [{'role': 'user', 'content': 'look'}], max_attempts=6, strict_response=True,
                        action_candidates=['look'], action_feedback=True)
                except ValueError:
                    value = None
            return calls, value
        for succeeds in (True, False):
            left, result = exercise(shared, succeeds)
            right, other = exercise(v24, succeeds)
            self.assertEqual(left, right)
            self.assertEqual(len(left), 6)
            self.assertEqual(result, other)
            self.assertEqual(result is not None, succeeds)
            self.assertIn('invalid 5', left[-1]['messages'][-2]['content'])

    def test_native_sdk_and_application_retries(self):
        import httpx
        from skillopt.model import openai_compatible_backend as backend
        for status, expected, success in ((503, 9, True), (503, 9, False), (400, 3, False)):
            with self.subTest(status=status, success=success), fixture() as root:
                calls = []
                def handler(request):
                    calls.append(json.loads(request.content))
                    if success and len(calls) == expected:
                        return httpx.Response(200, json=response('valid'))
                    return httpx.Response(status, json={'error': {'message': 'offline fixture'}})
                with patch('time.sleep'), provider(root, api_key='offline-test-key', http_transport=httpx.MockTransport(handler)):
                    if success:
                        self.assertEqual(backend.chat_optimizer('system', 'user', retries=3)[0], 'valid')
                    else:
                        with self.assertRaises(RuntimeError):
                            backend.chat_optimizer('system', 'user', retries=3)
                self.assertEqual(len(calls), expected)
                self.assertTrue(all(c['model'] == 'deepseek-flash' and c['max_tokens'] == 16384
                                    and c['thinking'] == {'type': 'enabled'} and c['reasoning_effort'] == 'medium'
                                    and c['stream'] is False for c in calls))
                audit = usage_summary(root)['optimizer']
                self.assertEqual(audit['logical_calls'], 1)
                self.assertEqual(audit['http_requests'], expected)
                self.assertEqual(audit['unknown_usage_requests'], expected - int(success))

    def test_native_parse_failure_keeps_merge_fallback(self):
        import httpx
        from skillopt.gradient.aggregate import _merge_batch
        from skillopt.model import set_optimizer_backend
        set_optimizer_backend('openai_compatible')
        with fixture() as root:
            calls = []
            def handler(request):
                calls.append(request)
                return httpx.Response(200, json=response('not JSON'))
            edits = [{'op': 'append', 'content': 'offline'}]
            with provider(root, api_key='offline', http_transport=httpx.MockTransport(handler)):
                result = _merge_batch('skill', [{'edits': edits}], 'system', 'patch')
            self.assertEqual(len(calls), 1)
            self.assertEqual(result['reasoning'], 'fallback concatenation')
            self.assertEqual(result['edits'][0]['content'], 'offline')

    def test_gate_strictly_requires_improvement(self):
        from skillopt.evaluation.gate import evaluate_gate
        for score, accepted in ((0.0, False), (0.5, False), (1.0, True)):
            decision = evaluate_gate('candidate', score, 'parent', .5, 'best', .5, 0, 1)
            self.assertEqual(decision.action.startswith('accept'), accepted)

    def test_best_only_real_evaluation_branch_promotes_final(self):
        from skillopt.engine import trainer
        tree = ast.parse(Path(trainer.__file__).read_text())
        block = [n for n in ast.walk(tree) if isinstance(n, ast.If) and ast.unparse(n.test) == "cfg['eval_test']"]
        self.assertEqual(len(block), 1)
        for fail in (False, True):
            with fixture() as root, contextlib.redirect_stdout(io.StringIO()):
                calls = []
                def rollout(env, skill, output):
                    calls.append((env, skill, Path(output).name))
                    if fail:
                        raise ValueError('incomplete selection')
                    return [{'task_type': 'pick_and_place', 'hard': 1, 'soft': 1}]
                scope = dict(cfg={'eval_test': True, 'eval_initial_skill': False, 'eval_final_skill': False,
                                  'require_final_selection': True, 'sel_env_num': 0, 'test_env_num': 0},
                    adapter=SimpleNamespace(get_task_types=lambda: ['pick_and_place'], rollout=rollout),
                    skill_hash=lambda x: x, current_skill='final', best_skill='previous best', skill_init='initial',
                    best_score=.5, best_step=1, global_step=4, seed=42, current_origin='slow', out_root=str(root),
                    _build_eval_env=lambda **kw: (kw['split'], 134), compute_score=lambda x: (1., 1.),
                    select_gate_score=lambda *a, **k: 1., gate_metric='hard', gate_mixed_weight=.5,
                    use_semantic_density=False, semantic_density_weight=.05, leading_words=None,
                    _persist_runtime_state=lambda step: None, _compute_task_type_buckets=trainer._compute_task_type_buckets,
                    baseline_test_hard=None, baseline_test_soft=None, final_test_hard=None, final_test_soft=None,
                    os=trainer.os, json=json)
                code = compile(ast.Module(body=block, type_ignores=[]), trainer.__file__, 'exec')
                if fail:
                    with self.assertRaisesRegex(ValueError, 'incomplete selection'):
                        exec(code, scope)
                    self.assertEqual(len(calls), 1)
                else:
                    exec(code, scope)
                    self.assertEqual(calls, [('valid_seen', 'final', 'final_selection_eval'), ('valid_unseen', 'final', 'test_eval')])
                    self.assertIsNone(scope['baseline_test_hard'])
                    self.assertIsNone(scope['final_test_hard'])
                    self.assertFalse((root / 'test_eval_baseline').exists())
                    self.assertFalse((root / 'test_eval_final').exists())

    def test_incomplete_episode_not_restarted_and_test_is_gated(self):
        actor = p.read(p.DEFAULT / 'actor.json')
        with fixture() as root, patch('subprocess.run', side_effect=AssertionError('Actor forbidden')):
            directory = root / 'incomplete'
            directory.mkdir()
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                run_episode(actor, p.read(root / 'splits/train/items.json')[0], directory, root / 'initial_skill.md')
            adapter = build_adapter(root, episode_runner=lambda *a: self.fail('premature test'))
            adapter.setup(p.read(root / 'skillopt.json'))
            batch = adapter.build_eval_env(0, 'valid_unseen', 42)
            for output in ('test_eval_baseline', 'test_eval_final', 'test_eval'):
                with self.assertRaises(ActorInterrupted):
                    adapter.rollout(batch, 'skill', root / 'campaign' / output)

    def test_recorded_completed_actor_trajectory_reuses_without_requests(self):
        from src.skillopt_alfworld_native.actor import validate_record
        summary = p.read(p.ADAM / 'evaluation/final/summary.json')
        # Locate the actual saved record rather than assume a summary schema.
        paths = list((p.ADAM / 'evaluation/final').glob('**/trajectory.json'))
        self.assertTrue(paths)
        record = p.read(paths[0])
        actor = p.read(p.DEFAULT / 'actor.json')
        with fixture() as root, patch('subprocess.run', side_effect=AssertionError('no resampling')):
            destination = root / 'episode' / paths[0].parent.name
            shutil.copytree(paths[0].parent, destination)
            skill_file = root / 'recorded_skill.md'
            skill_file.write_text(record['skill']['text'])
            actual, path = run_episode(actor, record['task'], destination.parent, skill_file)
            row, conversation = convert_record(actual, record['task'], path)
            self.assertEqual(row['hard'], int(record['won']))
            self.assertEqual(row['n_turns'], len(conversation))
            self.assertTrue(all(s['reasoning'] is None for s in conversation))

    def test_four_epoch_native_pipeline_with_mock_http_and_episodes(self):
        import httpx
        from skillopt.engine.trainer import ReflACTTrainer
        with fixture() as root, patch('subprocess.run', side_effect=AssertionError('real Actor forbidden')), \
             contextlib.redirect_stdout(io.StringIO()):
            episodes = []
            def episode(actor, item, directory, skill_file):
                skill = skill_file.read_text()
                threshold = 8 if 'OFFLINE_SLOW' in skill else 6 if 'OFFLINE_PATCH' in skill else 2
                won = int(item['id'].split(':')[1]) % 10 < threshold
                episodes.append(item['id'])
                return {'won': won, 'status': 'success' if won else 'step_limit', 'gamefile': item['gamefile'],
                        'goal': 'offline synthetic fixture', 'steps': [{'phase': 'executed', 'step': 1,
                        'action': 'look', 'model_response': {'content': '<action>look</action>'},
                        'observation': 'offline observation', 'reward': int(won), 'done': True}]}, directory / 'synthetic.json'
            def handler(request):
                edits = [{'op': 'append', 'content': '\nOFFLINE_PATCH\n'}]
                content = {'patch': {'reasoning': 'offline', 'edits': edits}, 'edits': edits,
                           'reasoning': 'offline', 'slow_update_content': 'OFFLINE_SLOW',
                           'meta_skill_content': 'OFFLINE_META'}
                return httpx.Response(200, json=response(json.dumps(content)))
            cfg = p.read(root / 'skillopt.json')
            with provider(root, api_key='offline', http_transport=httpx.MockTransport(handler)):
                summary = ReflACTTrainer(cfg, build_adapter(root, episode_runner=episode)).train()
            self.assertEqual(summary['total_steps'], 4)
            self.assertEqual(summary['test_roles'], ['best'])
            self.assertIsNone(summary['baseline_test_hard'])
            self.assertIsNone(summary['final_test_hard'])
            self.assertIsNone(summary['test_delta_hard'])
            self.assertEqual(sum(x.startswith('test:') for x in episodes), 134)
            self.assertFalse((root / 'campaign/test_eval_baseline').exists())
            self.assertFalse((root / 'campaign/test_eval_final').exists())
            for e in range(2, 5):
                slow = p.read(root / f'campaign/slow_update/epoch_{e:02d}/slow_result.json')
                self.assertIn(slow['action'], ('accept', 'accept_new_best', 'reject'))
                self.assertIn('selection_hard', slow)
            self.assertGreater(usage_summary(root)['optimizer']['http_requests'], 0)


if __name__ == '__main__':
    unittest.main()
