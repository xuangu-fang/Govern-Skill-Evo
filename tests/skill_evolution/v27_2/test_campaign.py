"""Exercise the actual campaign entry points with synthetic LMB responses."""
import json
import shutil
from unittest.mock import patch

from scripts.runs import run_v27_2_campaign as cli
from src.skill_evolution.v27_1 import config as old_config, evolution as old_engine
from src.skill_evolution.v27_1.actor_io import ActorAdapter
from src.skill_evolution.v27_2 import config, evolution as engine, prompts
from src.skill_evolution.v27_2.campaign import CampaignAdapter
from src.skill_evolution.v27_2.evaluation import run_test
from tests.skill_evolution.v27_1.runtime_support import Base, HIDDEN, snapshot
from tests.skill_evolution.v27_1.support import Generator, bind
from tests.skill_evolution.v27_1.test_editor import offline


class CampaignTests(Base):
    def setUp(self):
        super().setUp()
        offline(self)

    def test_formal_config_and_credential_free_preflight(self):
        previous = engine.read(old_config.DEFAULT_CONFIG)
        current = engine.read(config.DEFAULT_CONFIG)
        previous['method']['version'] = config.METHOD_VERSION
        previous['method']['prompts'] = config.prompt_versions()
        self.assertEqual(previous, current)
        self.assertTrue(set(config.prompt_versions().values()).isdisjoint(old_config.prompt_versions().values()))
        root = self.root / 'unused'
        with patch.object(cli, 'read_credentials', side_effect=AssertionError('No credentials')):
            cli.main(['train', str(root), '--config', str(config.DEFAULT_CONFIG), '--validate-only'])
        self.assertFalse(root.exists())

    def test_actual_requests_gate_memory_resume_and_final_test(self):
        data, actor, _, _ = bind(self.root, rounds=1, size=2, mode='mixed')
        secret = 'SEPARATELY_STORED_REFERENCE_SENTINEL'
        for row in data.rows.values():
            row.update(theorem=secret, sketch=secret)
        adapter = CampaignAdapter(ActorAdapter(data, actor))
        root = self.root / 'run'
        generator = Generator(count=2)
        expected_text = {name: (prompts.DIRECTORY / f'{name}.md').read_text()
                         for name in config.MODEL_MODULES}

        def generate(name, messages, directory, settings):
            self.assertEqual(messages[0], {'role': 'system', 'content': expected_text[name]})
            for unavailable in (secret, HIDDEN, data.splits['test'][0]):
                self.assertNotIn(unavailable, json.dumps(messages))
            return generator(name, messages, directory, settings)

        with adapter.using():
            cfg = config.campaign_config(adapter)
            result = cli.run_training(root, cfg, generate=generate)
            self.assertEqual(result['method'], config.METHOD_VERSION)
            self.assertEqual(engine.read(root / 'implementation.json')['prompts'], expected_text)
            self.assertEqual(generator.calls, list(config.MODEL_MODULES))
            rd = root / 'rounds/R01'
            for name in generator.calls:
                stage = rd / name
                self.assertEqual(engine.read(stage / 'identity.json')['prompt'], config.prompt_versions()[name])
                self.assertEqual((stage / 'attempts/001/prompt.md').read_text(), expected_text[name])
            decisions = engine.read(rd / 'gate/result.json')['decisions']
            self.assertEqual([d['gate_decision'] for d in decisions], ['Retain', 'Reject'])
            self.assertEqual(len(adapter.load_memory(root / 'memory')['memory']['rounds'][0]['entries']), 2)
            selected = (root / 'final_skill.md').read_text()
            self.assertIn('rule u1', selected)
            self.assertNotIn('rule u2', selected)
            calls = actor.calls
            self.assertEqual(cli.run_training(root, cfg, resume=True), result)
            self.assertEqual(actor.calls, calls)
            report = run_test(root, self.root / 'heldout')
            self.assertEqual(report['method'], config.METHOD_VERSION)
            self.assertEqual(actor.calls, calls + len(data.splits['test']))
            self.assertNotIn(secret, json.dumps(actor.seen))

    def test_resume_rejects_other_versions_and_prompt_drift(self):
        data, actor, old, old_cfg = bind(self.root, rounds=1, size=1)
        new = CampaignAdapter(ActorAdapter(data, actor))
        first, second = self.root / 'first', self.root / 'second'
        with old.using():
            old_engine.initialize(first, old_cfg)
        before = snapshot(first)
        with new.using():
            engine.initialize(second, config.campaign_config(new))
            self.reject(engine.run_campaign, first, resume=True)
            self.assertEqual(snapshot(first), before)
            frozen = snapshot(second)
            changed = self.root / 'prompts'
            shutil.copytree(prompts.DIRECTORY, changed)
            with (changed / 'diagnosis.md').open('a') as prompt:
                prompt.write('\nChanged domain guidance.\n')
            with patch.object(prompts, 'DIRECTORY', changed):
                self.reject(engine.run_campaign, second, resume=True)
            self.assertEqual(snapshot(second), frozen)
        with old.using():
            self.reject(old_engine.run_campaign, second, resume=True)
        self.assertEqual(snapshot(second), frozen)
        self.assertEqual(actor.calls, 0)

    def test_interrupted_round_reuses_completed_requests(self):
        data, actor, _, _ = bind(self.root, rounds=1, size=1, mode='gain')
        adapter = CampaignAdapter(ActorAdapter(data, actor))
        root, generator = self.root / 'interrupted', Generator(count=1)

        def interrupt(stage):
            if stage == 'candidate_runs':
                raise KeyboardInterrupt()

        with adapter.using():
            cfg = config.campaign_config(adapter)
            with self.assertRaises(KeyboardInterrupt):
                engine.run_campaign(root, config=cfg, generate=generator, hook=interrupt)
            self.assertEqual(generator.calls, ['diagnosis', 'preconditioner', 'editor'])
            self.assertEqual(actor.calls, 1)
            result = cli.run_training(root, cfg, generate=generator, resume=True)
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(generator.calls, list(config.MODEL_MODULES))
            self.assertEqual(actor.calls, 2)

    def test_replay_skip_keeps_new_prompt_identity_without_a_request(self):
        data, actor, _, _ = bind(self.root, rounds=1, size=1, mode='none')
        adapter = CampaignAdapter(ActorAdapter(data, actor))
        root, generator = self.root / 'skip', Generator(count=1)
        with adapter.using():
            cli.run_training(root, config.campaign_config(adapter), generate=generator)
        branch = engine.read(root / 'rounds/R01/replay/branch.json')
        self.assertEqual(branch['branch'], 'skip')
        self.assertEqual(branch['prompt'], config.prompt_versions()['replay'])
        self.assertEqual(generator.calls, ['diagnosis', 'preconditioner', 'editor'])
        self.assertFalse((root / 'rounds/R01/replay/attempts').exists())
