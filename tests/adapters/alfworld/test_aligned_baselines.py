"""Offline integration checks: no benchmark episodes and no provider calls."""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'external/SkillOpt')]
from scripts.runs.alfworld import alfworld_aligned_common as common
from scripts.runs.alfworld import run_alfworld_aligned as launcher
from skillopt.config import load_config, flatten_config


class PreparedBaselineTests(unittest.TestCase):
    def test_configs_and_default_launcher_are_offline(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
             patch.object(common.subprocess, 'run', side_effect=AssertionError('process forbidden')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.main([]), 0)
            self.assertEqual(launcher.main(['noskill']), 0)
            self.assertEqual(launcher.main(['skillopt']), 0)

    def test_same_actor_command_only_skill_differs(self):
        actor = common.read(common.EXPERIMENT / 'actor.json')
        item = common.read(common.EXPERIMENT / 'splits/test/items.json')[0]
        no = common.actor_command(actor, item, Path('/tmp/output'))
        skill = common.actor_command(actor, item, Path('/tmp/output'), Path('/tmp/skill.md'))
        self.assertEqual(skill, no + ['--skill-file', '/tmp/skill.md'])
        self.assertNotIn('--skill-file', no)
        self.assertEqual(no[no.index('--request-attempts') + 1], '6')
        self.assertIn('--action-feedback', no)
        self.assertEqual(no[no.index('--purpose') + 1], 'final')

    def test_real_dataloader_plans_39_18_134_without_environment(self):
        cfg = flatten_config(load_config(str(common.EXPERIMENT / 'skillopt.yaml')))
        cfg['split_dir'] = str(ROOT / cfg['split_dir'])
        actor = common.read(common.EXPERIMENT / 'actor.json')
        with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
            adapter = launcher.build_adapter(cfg, actor)
            adapter.setup(cfg)
            loader = adapter.get_dataloader()
            with tempfile.TemporaryDirectory() as tmp:
                batches = loader.plan_train_epoch(epoch=1, steps_per_epoch=1, accumulation=1,
                                                 batch_size=40, seed=42, out_root=tmp)
                self.assertEqual([b.batch_size for b in batches], [39])
                self.assertEqual(loader.build_eval_batch(env_num=0, split='valid_seen', seed=42).batch_size, 18)
                self.assertEqual(loader.build_eval_batch(env_num=0, split='valid_unseen', seed=42).batch_size, 134)
                batch = adapter.build_env_from_batch(batches[0])
                with patch.object(launcher, 'run_batch', return_value=[]) as run:
                    adapter.rollout(batch, 'skill', tmp)
                    self.assertEqual(len(run.call_args.args[1]), 39)
                    self.assertEqual(run.call_args.args[2], 'skill')

    def test_existing_incomplete_episode_is_not_silently_retried(self):
        actor = common.read(common.EXPERIMENT / 'actor.json')
        item = common.read(common.EXPERIMENT / 'splits/test/items.json')[0]
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'episodes' / item['id'].replace(':', '_')).mkdir(parents=True)
            with patch.object(common.subprocess, 'run', side_effect=AssertionError('must not retry')):
                with self.assertRaisesRegex(ValueError, 'Incomplete episode'):
                    common.run_batch(actor, [item], None, tmp)

    def test_saved_shared_actor_trace_converts_to_skillopt_without_new_requests(self):
        from skillopt.gradient.reflect import fmt_minibatch_trajectories
        from skillopt.model.common import TokenTracker
        actor = common.read(common.EXPERIMENT / 'actor.json')
        reference = ROOT / 'artifacts/methods/v23_5/alfworld_verified_feedback_001/evaluation/final/summary.json'
        path = Path(common.read(reference)['tasks'][0]['trajectory'])
        record = common.read(path)
        item, skill = record['task'], record['skill']['text']
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'episodes' / item['id'].replace(':', '_') / path.parent.name
            shutil.copytree(path.parent, destination)
            tracker = TokenTracker()
            with patch.object(common.subprocess, 'run', side_effect=AssertionError('no resampling')), \
                 patch('socket.socket.connect', side_effect=AssertionError('network forbidden')):
                rows = common.run_batch(actor, [item], skill, tmp, tracker)
            self.assertEqual(rows[0]['hard'], int(record['won']))
            self.assertEqual(rows[0]['n_turns'], len(record['steps']))
            prompt = fmt_minibatch_trajectories(rows, str(Path(tmp) / 'predictions'))
            self.assertIn(record['steps'][0]['action'], prompt)
            self.assertIn(record['steps'][0]['observation'], prompt)
            self.assertNotIn('think] None', prompt)
            usage = common.read(Path(tmp) / 'actor_usage.json')
            expected_calls = sum(len(s.get('transport_attempts', [])) for s in record['steps'])
            self.assertEqual(usage['requests'], expected_calls)


class FinalTestPolicyTests(unittest.TestCase):
    def run_actual_evaluation_block(self, final_flag, directory):
        # Execute the real trainer's complete final evaluation branch against a
        # fake rollout adapter. This covers Initial, Best and final Selection,
        # and prevents a config-only flag from silently leaving Final enabled.
        trainer = ROOT / 'external/SkillOpt/skillopt/engine/trainer.py'
        tree = ast.parse(trainer.read_text())
        blocks = [n for n in ast.walk(tree) if isinstance(n, ast.If)
                  and ast.unparse(n.test) == "cfg['eval_test']"]
        self.assertEqual(len(blocks), 1)
        calls = []
        def rollout(env, skill, output):
            calls.append((env, skill, Path(output).name))
            return [{'task_type': 'test', 'hard': 1, 'soft': 1}]
        cfg = {'eval_test': True, 'test_env_num': 0, 'sel_env_num': 0}
        if final_flag is not None:
            cfg['eval_final_skill'] = final_flag
        scope = dict(cfg=cfg, adapter=SimpleNamespace(get_task_types=lambda: ['test'], rollout=rollout),
                     skill_hash=lambda s: s, current_skill='last', best_skill='best', skill_init='initial',
                     best_score=1.0, global_step=4, seed=42, out_root=directory,
                     _build_eval_env=lambda **k: (k['split'], 1),
                     compute_score=lambda rows: (1.0, 1.0),
                     select_gate_score=lambda *a, **k: 1.0,
                     gate_metric='hard', gate_mixed_weight=0.5, use_semantic_density=False,
                     semantic_density_weight=0.05, leading_words=None,
                     _compute_task_type_buckets=lambda rows, types: {'overall': {'total': 1, 'hard': 1}},
                     final_test_hard=None, final_test_soft=None, os=os, json=json)
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(ast.Module(body=blocks, type_ignores=[]), str(trainer), 'exec'), scope)
        return calls, scope

    def test_disabled_final_keeps_selection_initial_and_best(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls, scope = self.run_actual_evaluation_block(False, tmp)
            self.assertEqual([c[2] for c in calls], ['final_selection_eval', 'test_eval_baseline', 'test_eval'])
            self.assertIsNone(scope['final_test_hard'])
            self.assertFalse((Path(tmp) / 'test_eval_final').exists())

    def test_legacy_default_still_evaluates_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls, scope = self.run_actual_evaluation_block(None, tmp)
            self.assertEqual(calls[-1][2], 'test_eval_final')
            self.assertEqual(scope['final_test_hard'], 1.0)


if __name__ == '__main__':
    unittest.main()
