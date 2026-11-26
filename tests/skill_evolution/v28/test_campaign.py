"""Offline campaign dispatch, recovery, publication and independent Test."""
from copy import deepcopy
import json
import os
from unittest.mock import patch

from src.skill_evolution.v28 import evolution, stages, evaluation
from src.skill_evolution.v28.campaign import CampaignAdapter
from src.skill_evolution.v28.config import validate_config, campaign_config
from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
from src.skill_evolution.v28.benchmarks.searchqa import protocol as p
from .runtime_support import Base, Transport, SKILL, snapshot
from .campaign_support import bind, Generator


class CampaignTests(Base):
    def test_source_snapshot_is_audit_only_on_resume(self):
        _, transport, adapter, config = bind(rounds=1, batch_size=1)
        root = self.root / 'source_snapshot'
        generator = Generator()
        with adapter.using(), patch.object(adapter, 'source_snapshot', return_value={'v27/config.py': 'old source'}):
            evolution.run_campaign(root, config=config, generate=generator)
        calls = (transport.calls, len(generator.calls))
        with adapter.using(), patch.object(adapter, 'source_snapshot', side_effect=AssertionError('Do not reread sources on resume')):
            evolution.run_campaign(root, generate=generator, resume=True)
        self.assertEqual(calls, (transport.calls, len(generator.calls)))
        self.assertEqual(stages.read(root / 'contract.json'), {'v27/config.py': 'old source'})
        stage_identity = stages.read(root / 'rounds/R01/replay/identity.json')
        self.assertNotIn('source_sha256', stage_identity)
        self.assertNotIn('resources_sha256', stage_identity['prompt'])

    def reject(self, fn, *args, **kwargs):
        with self.assertRaises((ValueError, KeyError, FileNotFoundError, stages.Stopped)):
            fn(*args, **kwargs)

    def test_real_schedule_configuration_without_execution(self):
        adapter = CampaignAdapter(SearchQAActorAdapter(SearchQADataset()))
        with adapter.using():
            config = campaign_config(adapter, initial_skill={'source': 'offline validation fixture only', 'text': SKILL})
            validate_config(config)
            self.assertEqual(len(config['batches']), 40)
            self.assertTrue(all(len(b) == 15 for b in config['batches']))
            self.assertEqual(len({t for b in config['batches'] for t in b}), 600)
            for mutate in (lambda c: c['batches'].reverse(), lambda c: c['batches'].pop(),
                           lambda c: c['batches'][0].append(c['batches'][1][0]),
                           lambda c: c['batches'][0].__setitem__(0, adapter.dataset.splits['test'][0]),
                           lambda c: c.update(max_attempts=7), lambda c: c.update(retry_delay_seconds=0),
                           lambda c: c.update(initial_skill=None), lambda c: c.update(continue_no_change=False),
                           lambda c: c['method'].update(knowledge_review='enabled')):
                bad = deepcopy(config); mutate(bad); self.reject(validate_config, bad)
            self.assertEqual(list(self.root.iterdir()), [self.skill])

    def test_full_chain_two_rounds_and_fresh_archive_audit(self):
        for accept in (True, False):
            data, transport, adapter, config = bind(accept=accept)
            root = self.root / f'chain_{accept}'; generator = Generator()
            with adapter.using():
                result = evolution.run_campaign(root, config=config, generate=generator)
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(result['state']['next_round'], 3)
                self.assertEqual(generator.calls, ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'] * 2)
                self.assertEqual(transport.calls, 8)
                first = stages.read(root / 'rounds/R01/gate/result.json')['result']['decision']
                self.assertEqual(first, 'ACCEPT' if accept else 'RETAIN')
                active = adapter.load_memory(root / result['state']['active_memory'])
                self.assertEqual(len(active['entries']), 2)
            frozen = snapshot(root)
            fresh = CampaignAdapter(SearchQAActorAdapter(data))
            with fresh.using():
                final = evolution.final_parent(root)
                self.assertIn('Use the exact entity.', final.read_text()) if accept else self.assertEqual(final.read_text(), SKILL)
            self.assertEqual(frozen, snapshot(root))

    def test_no_change_branches_continue_all_batches(self):
        for branch in ('diagnosis', 'preconditioner', 'editor'):
            _, transport, adapter, config = bind()
            root = self.root / branch; generator = Generator(no_change=branch)
            with adapter.using():
                result = evolution.run_campaign(root, config=config, generate=generator)
                self.assertEqual(result['state'], {'next_round': 3, 'parent': 'initial_skill.md', 'active_memory': 'initial_memory'})
                self.assertEqual(transport.calls, 4)
                self.assertNotIn('replay', generator.calls)
                self.assertEqual(evolution.final_parent(root).read_text(), SKILL)

    def test_all_40_synthetic_batches_single_epoch(self):
        _, transport, adapter, config = bind(rounds=40, batch_size=15)
        generator = Generator(no_change='diagnosis'); root = self.root / 'full_schedule'
        with adapter.using():
            result = evolution.run_campaign(root, config=config, generate=generator)
            self.assertEqual(result['state']['next_round'], 41)
            self.assertEqual(transport.calls, 600)
            self.assertEqual(generator.calls.count('grouping'), 40)
            self.assertEqual(generator.calls.count('diagnosis'), 40)
            self.assertEqual(len(list((root / 'rounds').iterdir())), 40)

    def test_semantic_stop_cannot_resample(self):
        _, transport, adapter, config = bind(rounds=1)
        generator = Generator(semantic_stop=True); root = self.root / 'semantic'
        with adapter.using():
            self.reject(evolution.run_campaign, root, config=config, generate=generator)
            self.assertEqual(stages.read(root / 'stop.json')['kind'], 'semantic')
            self.reject(evolution.run_campaign, root, generate=generator, resume=True)
            self.assertEqual(generator.calls.count('editor'), 1)
            self.assertEqual(transport.calls, 2)
            self.reject(evolution.final_parent, root)

    def test_replay_exhaustion_keeps_skill_and_memory_unpublished(self):
        _, transport, adapter, config = bind(rounds=1)
        generator = Generator(invalid_replay=True); root = self.root / 'replay_fail'
        with adapter.using():
            self.reject(evolution.run_campaign, root, config=config, generate=generator)
            self.assertEqual(stages.read(root / 'rounds/R01/gate/result.json')['result']['decision'], 'ACCEPT')
            self.assertEqual(stages.read(root / 'state.json'), {'next_round': 1, 'parent': 'initial_skill.md', 'active_memory': 'initial_memory'})
            self.assertEqual(generator.calls.count('replay'), 6)
            self.reject(evolution.run_campaign, root, generate=Generator(), resume=True)
            self.assertEqual(transport.calls, 4)
            self.assertFalse((root / 'rounds/R01/memory/active.json').exists())

    def test_resume_at_stage_and_atomic_publication_boundaries(self):
        points = ('parent_runs', 'grouping', 'diagnosis', 'preconditioner', 'editor', 'candidate_runs',
                  'pairs', 'gate', 'replay', 'memory', 'memory_prepared', 'before_publish', 'after_publish')
        for point in points:
            with self.subTest(point=point):
                data, transport, adapter, config = bind(rounds=1, batch_size=1)
                root = self.root / point; generator = Generator()
                def hook(stage):
                    if stage == point:
                        raise KeyboardInterrupt()
                with adapter.using():
                    with self.assertRaises(KeyboardInterrupt):
                        evolution.run_campaign(root, config=config, generate=generator, hook=hook)
                    self.assertEqual(stages.read(root / 'state.json')['next_round'], 2 if point == 'after_publish' else 1)
                fresh = CampaignAdapter(SearchQAActorAdapter(data, transport))
                with fresh.using():
                    result = evolution.run_campaign(root, generate=generator, resume=True)
                    self.assertEqual(result['status'], 'complete')
                    self.assertEqual(transport.calls, 2)
                    self.assertEqual(generator.calls, ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'])

    def test_round_limit_then_resume_and_corruption_stops_before_requests(self):
        data, transport, adapter, config = bind()
        generator = Generator(); root = self.root / 'bounded'
        with adapter.using():
            evolution.run_round(root, config=config, generate=generator)
            self.assertEqual(stages.read(root / 'state.json')['next_round'], 2)
        fresh = CampaignAdapter(SearchQAActorAdapter(data, transport))
        with fresh.using():
            evolution.run_campaign(root, generate=generator, resume=True)
            frozen = snapshot(root); calls = (transport.calls, len(generator.calls))
            bad = stages.read(root / 'rounds/R01/gate/result.json'); bad['result']['decision'] = 'RETAIN'
            stages.save(root / 'rounds/R01/gate/result.json', bad)
            self.reject(evolution.run_campaign, root, generate=generator, resume=True)
            self.assertEqual(calls, (transport.calls, len(generator.calls)))
            (root / 'rounds/R01/gate/result.json').write_bytes(frozen['rounds/R01/gate/result.json'])
            config = stages.read(root / 'config.json'); config['max_attempts'] = 7
            stages.save(root / 'config.json', config)
            self.reject(evolution.run_campaign, root, generate=generator, resume=True)
            self.assertEqual(calls, (transport.calls, len(generator.calls)))

    def test_actor_partial_batch_resume_reuses_completed_tasks(self):
        _, transport, adapter, config = bind(rounds=1, batch_size=1)
        original = transport.fn
        def interrupt(messages, slot):
            raw = original(messages, slot)
            stages.save(slot / 'response.json', raw)
            raise KeyboardInterrupt()
        transport.fn = interrupt
        root = self.root / 'actor_interrupt'; generator = Generator(no_change='diagnosis')
        with adapter.using():
            with self.assertRaises(KeyboardInterrupt):
                evolution.run_campaign(root, config=config, generate=generator)
            transport.fn = original
            result = evolution.run_campaign(root, generate=generator, resume=True)
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(transport.calls, 1)

    def test_independent_test_resumes_and_has_no_optimizer_outputs(self):
        data, _, _, _ = bind(rounds=1)
        transport = Transport(); adapter = SearchQAActorAdapter(data, transport)
        root = self.root / 'evaluation'
        result = evaluation.run_evaluation(root, adapter=adapter, skill_file=self.skill)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['completed'], 2)
        self.assertEqual(transport.calls, 2)
        evaluation.run_evaluation(root, adapter=adapter, skill_file=self.skill, resume=True)
        self.assertEqual(transport.calls, 2)
        self.assertEqual(evaluation.report_evaluation(root, adapter=SearchQAActorAdapter(data)), result)
        self.assertFalse(result['optimization_updates'])
        self.assertFalse((root / 'memory').exists())
        self.assertFalse((root / 'state.json').exists())
        campaign = self.root / 'campaign'; campaign.mkdir()
        stages.save(campaign / 'state.json', {}); stages.save(campaign / 'config.json', {})
        self.reject(evaluation.run_evaluation, campaign / 'test', adapter=adapter, skill_file=self.skill)

    def test_cli_validation_does_not_read_credentials_or_create_campaign(self):
        from src.skill_evolution.v28.cli import main
        data, _, _, _ = bind(rounds=1)
        adapter = CampaignAdapter(SearchQAActorAdapter(data))
        config = campaign_config(adapter, initial_skill={'source': 'fixture', 'text': SKILL})
        path = self.root / 'config.json'; stages.save(path, config)
        with patch('src.skill_evolution.v28.benchmarks.searchqa.dataset.SearchQADataset', return_value=data), \
             patch('src.skill_evolution.v28.cli.os.environ.get', wraps=os.environ.get) as environment_get, \
             patch('builtins.print'):
            # The mocked constructor also appears in isinstance in validation;
            # validate via the real pure function and verify CLI routes safely.
            with patch('src.skill_evolution.v28.cli.sys.prefix', '/offline/envs/SearchQA'):
                main(['validate', '--config', str(path)])
            self.assertNotIn('OPENAI_API_KEY', [call.args[0] for call in environment_get.call_args_list])
        self.assertFalse((self.root / 'state.json').exists())

    def test_archive_only_reconstructs_completed_batch_without_transport(self):
        data, transport, adapter, _ = bind(rounds=1)
        directory = self.root / 'completed_batch'
        expected = adapter.actor_batch(data.batches[0], self.skill, directory, {'split': 'train', 'role': 'parent'})
        (directory / 'records.json').unlink()
        fresh = CampaignAdapter(SearchQAActorAdapter(data))
        restored = fresh.actor_batch(data.batches[0], self.skill, directory, {'split': 'train', 'role': 'parent'})
        self.assertEqual(restored, expected)
        self.assertEqual(transport.calls, 2)
        (directory / 'records.json').unlink()
        (directory / 'actor' / p.digest(data.batches[0][0]) / 'result.json').unlink()
        self.reject(fresh.actor_batch, data.batches[0], self.skill, directory, {'split': 'train', 'role': 'parent'})
