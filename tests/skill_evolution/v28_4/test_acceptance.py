"""Frozen real configuration preflight and remaining SearchQA boundary cases."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from unittest.mock import patch

from scripts.runs import run_v28_4_campaign as cli
from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
from src.skill_evolution.v28_4 import config as settings, evolution as ev, memory, replay
from tests.skill_evolution.v28.runtime_support import Base, snapshot, response
from .support import bind, fresh, Generator, no_hashes
from .test_editor import offline


class AcceptanceTests(Base):
    def setUp(self):
        super().setUp(); offline(self); self.enterContext(no_hashes())

    def test_real_config_schedule_actor_and_exact_design_prompts(self):
        data = SearchQADataset(batch_size=30, verify_hashes=False)
        config = ev.read(settings.DEFAULT_CONFIG)
        baseline = ev.read(p.ROOT / 'experiments/configs/v28_1_searchqa_train600_batch30_20261103.json')
        with fresh(data).using(): settings.validate_config(config, executable=True)
        for key in ('batches', 'actor', 'initial_skill', 'optimization_pool'):
            self.assertEqual(config[key], baseline[key])
        self.assertEqual(len(config['initial_skill']['text']), 104)
        self.assertEqual([len(b) for b in config['batches']], [30] * 20)
        self.assertEqual(len(data.splits['test']), 1400)
        self.assertEqual({k:v['max_tokens'] for k,v in config['module_calls'].items()},
                         dict(diagnosis=65536, preconditioner=65536, editor=32768, replay=65536))
        self.assertTrue(all(c['timeout_seconds'] == 600 for c in config['module_calls'].values()))
        self.assertEqual(config['actor']['max_tokens'], 32768)
        self.assertNotIn('context_window_tokens', config)
        for name, prompt in settings.render_prompts().items():
            self.assertEqual(prompt, (p.ROOT / 'docs/methods/v28_4/prompts' / f'{name}.md').read_bytes().decode())
        output = self.root / 'never_started'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('No credentials')), redirect_stdout(io.StringIO()) as log:
            cli.main(['train', str(output), '--config', str(settings.DEFAULT_CONFIG), '--env-file', '/missing', '--validate-only'])
        self.assertEqual(json.loads(log.getvalue())['status'], 'valid')
        self.assertFalse(output.exists())

    def test_f1_only_change_produces_no_replay_or_votes(self):
        _, transport, adapter, config = bind(self.root, rounds=1, mode='f1')
        root = self.root / 'f1'; generator = Generator(count=1)
        with adapter.using():
            ev.run_campaign(root, config=config, generate=generator)
            bundle = ev.read(root / 'rounds/R01/pairs/input.json')
            self.assertTrue(all(x['parent_result']['em'] == x['candidate_result']['em'] == 0 for x in bundle['payload']['pairs']))
            self.assertTrue(all(x['parent_result']['f1'] != x['candidate_result']['f1'] for x in bundle['payload']['pairs']))
            self.assertEqual(memory.load_memory(root / 'memory')['memory']['rounds'][0]['entries'], [])
            self.assertEqual(ev.read(root / 'rounds/R01/gate/result.json')['decisions'],
                             [{'update_id': 'u1', 'G': 0, 'L': 0, 'gate_decision': 'Defer'}])
            self.assertNotIn('replay', generator.calls)
            self.assertFalse((root / 'rounds/R01/replay/attempts').exists())
            # Even unchanged tasks must remain verified before filtering.
            folder = root / 'rounds/R01/parent_runs/actor' / adapter.actor_adapter.task_key(config['batches'][0][1])
            (folder / 'trajectory.json').unlink()
            self.reject(replay.replay_call, bundle)
        self.assertEqual(transport.calls, 4)

    def test_test_is_never_accepted_as_optimization_evidence(self):
        data, _, adapter, config = bind(self.root, rounds=1)
        with adapter.using():
            cli.run_training(self.root / 'campaign', config, generate=Generator(no_change='diagnosis'))
            cli.run_test(self.root / 'campaign', self.root / 'evaluation')
            self.reject(adapter.register_archive, self.root / 'evaluation/runs')

    def test_actor_completed_tasks_recover_without_new_request(self):
        data, transport, adapter, config = bind(self.root, rounds=1)
        root = self.root / 'archive_recovery'; generator = Generator(no_change='diagnosis')
        with adapter.using():
            ev.run_campaign(root, config=config, generate=generator)
        rd = root / 'rounds/R01'
        # Exercise the lower-level recovery of a missing aggregate after all task journals completed.
        folder = rd / 'parent_runs'
        expected = ev.read(folder / 'records.json')
        (folder / 'records.json').unlink()
        with fresh(data).using() as unused:
            from src.skill_evolution.v27.benchmark import current
            actual = current().actor_batch(config['batches'][0], rd / 'parent.md', folder, {'split': 'train', 'role': 'parent'})
        self.assertEqual(actual, expected)
        self.assertEqual(transport.calls, 2)

    def test_test_identity_freezes_payload_and_references(self):
        data, transport, adapter, config = bind(self.root, rounds=1)
        root = self.root / 'campaign'; output = self.root / 'evaluation'
        with adapter.using():
            cli.run_training(root, config, generate=Generator(no_change='diagnosis'))
            cli.run_test(root, output)
            before = transport.calls
            data.rows[data.splits['test'][0]]['context'] += ' changed'
            self.reject(cli.run_test, root, output, resume=True)
            self.assertEqual(transport.calls, before)

    def test_worker_limits_cannot_drift_before_execution(self):
        _, transport, adapter, config = bind(self.root, rounds=1)
        for field, value in (('workers', 1), ('test_workers', 16), ('workers', True)):
            setattr(adapter.actor_adapter, field, value)
            self.reject(adapter._bound)
            setattr(adapter.actor_adapter, field, 15)
        self.assertEqual(transport.calls, 0)
