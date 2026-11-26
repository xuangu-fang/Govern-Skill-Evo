"""Run with SkillOpt Python: offline contracts and native Trainer wiring."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/runs'))
import run_skillopt_spreadsheetbench_aligned as bridge
from skillopt.engine import trainer
from skillopt.gradient.reflect import fmt_minibatch_trajectories


class Contracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ('shared_config.json', 'skillopt.json', 'initial_skill.md'):
            shutil.copyfile(bridge.DEFAULT / name, self.root / name)
        shutil.copytree(bridge.DEFAULT / 'splits', self.root / 'splits')
        cfg = bridge.read(self.root / 'skillopt.json')
        cfg.update(bridge.overrides(self.root, bridge.read(self.root / 'shared_config.json')))
        bridge.write(self.root / 'skillopt.json', cfg)
        self.cfg = cfg
        self.adapter = bridge.SharedActorAdapter(self.root)
        self.adapter.setup(cfg)

    def tearDown(self):
        self.temp.cleanup()

    def test_native_defaults_and_prompt_dispatch(self):
        defaults = bridge.native_defaults()
        for field in ('num_epochs', 'batch_size', 'train_size', 'seed', 'accumulation', 'edit_budget',
                      'min_edit_budget', 'lr_scheduler', 'use_gate', 'use_meta_skill', 'use_slow_update',
                      'slow_update_gate_with_selection', 'slow_update_samples', 'minibatch_size', 'merge_batch_size'):
            self.assertEqual(self.cfg[field], defaults[field], field)
        native = bridge.SpreadsheetBenchAdapter(split_dir=str(self.root / 'splits'), split_mode='split_dir')
        native.setup(self.cfg)
        self.assertEqual(self.adapter.get_error_minibatch_prompt(), native.get_error_minibatch_prompt())
        self.assertEqual(self.adapter.get_success_minibatch_prompt(), native.get_success_minibatch_prompt())

    def test_no_test_before_training_and_no_mixed_batches(self):
        loader = self.adapter.get_dataloader()
        with self.assertRaisesRegex(ValueError, 'forbidden|No such file'):
            self.adapter.rollout(loader.test_items, 'skill', self.root / 'test')
        with self.assertRaisesRegex(ValueError, 'Mixed'):
            self.adapter.rollout([loader.train_items[0], loader.val_items[0]], 'skill', self.root / 'mixed')

    def test_no_live_run_without_start(self):
        result = subprocess.run([sys.executable, str(Path(bridge.__file__)), 'run'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('require explicit --start', result.stderr)
        self.assertFalse((bridge.DEFAULT / 'campaign').exists())

    def test_optimizer_payload_matches_official_route_without_network(self):
        from openai.types.chat import ChatCompletion
        from skillopt import model
        from skillopt.model import openai_compatible_backend as backend
        from unittest.mock import Mock
        client = Mock()
        client.chat.completions.create.return_value = ChatCompletion.model_validate({
            'id': 'synthetic', 'object': 'chat.completion', 'created': 0, 'model': 'deepseek-flash',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'synthetic'}}],
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}})
        shared = bridge.read(self.root / 'shared_config.json')
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic-only', 'OPENAI_BASE_URL': shared['actor_base_url']}), \
             patch('dotenv.load_dotenv'), patch.object(backend, '_get_client', return_value=client), \
             patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')):
            bridge.configure_model(shared)
            model.set_optimizer_backend('openai_compatible')
            result, _ = model.chat_optimizer('synthetic', 'synthetic', max_completion_tokens=16384)
        self.assertEqual(result, 'synthetic')
        body = client.chat.completions.create.call_args.kwargs
        self.assertEqual(body['model'], 'deepseek-flash')
        self.assertEqual(body['max_tokens'], 16384)
        self.assertEqual(body['temperature'], 1)
        self.assertEqual(body['extra_body'], {'thinking': {'type': 'enabled'}, 'reasoning_effort': 'medium', 'stream': False})
        self.assertEqual(backend.OPTIMIZER_CONFIG.base_url, shared['actor_base_url'])

    def test_native_trainer_dry_wiring(self):
        """Fake results and optimizer responses exercise real 4-epoch orchestration."""
        events = []
        def runner(folder):
            request = bridge.read(folder / 'input.json')
            task = request['shared']['task_items'][request['task']]
            events.append(task['split'])
            bridge.write(folder / 'conversation.json', [{'role': 'assistant', 'content': 'synthetic dry evidence'}])
            return {'id': task['dataset_id'], 'hard': 1, 'soft': 1, 'n_turns': 1,
                    'task_description': 'synthetic dry evidence', 'task_type': 'cell_level'}
        adapter = bridge.SharedActorAdapter(self.root, runner=runner)
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')), \
             patch.object(adapter, 'reflect', return_value=[]), \
             patch.object(trainer, 'run_slow_update', return_value=None) as slow, \
             patch.object(trainer, 'run_meta_skill', return_value=None) as meta, \
             redirect_stdout(io.StringIO()):
            summary = trainer.ReflACTTrainer(deepcopy(self.cfg), adapter).train()
        self.assertEqual(summary['total_steps'], 8)
        self.assertEqual(summary['test_hard'], 1)
        self.assertEqual(summary['baseline_test_hard'], 1)
        self.assertIsNone(summary['final_test_hard'])
        self.assertIsNone(summary['final_test_soft'])
        self.assertTrue(summary['final_test_skipped'])
        self.assertFalse((self.root / 'campaign/test_eval_final').exists())
        self.assertEqual(events.count('test'), 560)  # Initial + Best, 280 tasks each.
        self.assertTrue((self.root / 'campaign/final_selection_eval').exists())
        self.assertTrue(slow.called and meta.called)
        first_test = events.index('test')
        self.assertNotIn('train', events[first_test:])
        self.assertNotIn('val', events[first_test:])
        self.assertIn('val', events[:first_test])


if __name__ == '__main__':
    unittest.main()
