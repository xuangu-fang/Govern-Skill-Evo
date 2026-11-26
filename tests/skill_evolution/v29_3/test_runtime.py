"""Lightweight checkpoints preserve execution/recovery, not historical replays."""
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v29 import memory_operation as old_operation
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29_2 import memory as old_memory
from src.skill_evolution.v29_3 import evolution as ev, evaluation, memory
from src.skill_evolution.v29_3.campaign import CampaignAdapter, RUNTIME_VERSION
from tests.skill_evolution.v29.test_actor import Base
from tests.skill_evolution.v29.test_campaign import snapshot
from tests.skill_evolution.v29_2.test_editor import offline
from tests.skill_evolution.v29_2.campaign_support import Generator
from .test_offline import bind


class RuntimeTests(Base):
    def setUp(self):
        super().setUp()
        offline(self)

    def complete(self, name='run'):
        data, actor, adapter, config = bind(self.root / (name + '_data'), sizes=(1,), mode='gain')
        root = self.root / name
        with adapter.using(), patch.object(old_operation.MemoryOperation, '__init__',
                                          side_effect=AssertionError('No file snapshots')):
            ev.run_campaign(root, config=config, generate=Generator(count=1))
        return data, actor, root

    def test_complete_and_test_readiness_do_not_reopen_historical_execution_or_sources(self):
        data, actor, root = self.complete()
        before = snapshot(root)
        fresh = CampaignAdapter(DocVQAActorAdapter(data))
        with fresh.using(), patch.object(fresh.actor_adapter, 'read_batch',
                                        side_effect=AssertionError('No historical execution')):
            with patch.object(old_memory, '_prepare', side_effect=AssertionError('No historical Gate replay')):
                state = memory.load_memory(root / 'memory')
                skill = ev.final_parent(root)
                identity = evaluation.prepare_test(root, self.root / 'test')
        self.assertEqual(state['selection']['selected_text'], skill.read_text())
        self.assertEqual(identity['skill'], skill.read_text())
        self.assertEqual(identity['runtime_version'], RUNTIME_VERSION)
        self.assertEqual(snapshot(root), before)

    def test_selected_cursor_export_and_commit_corruption_still_rejected(self):
        data, _, root = self.complete()
        selected = ev.read(root / 'state.json')['parent']
        head = ev.read(root / 'state.json')['memory_head']
        for name in [selected, 'state.json', f'memory/commits/{head}.json']:
            path = root / name; original = path.read_bytes()
            path.write_text('corrupt')
            with self.subTest(name=name), CampaignAdapter(DocVQAActorAdapter(data)).using():
                with self.assertRaises((ValueError, KeyError)):
                    evaluation.prepare_test(root, self.root / 'test')
            path.write_bytes(original)
        (root / 'final_skill.md').write_text('wrong export')
        with CampaignAdapter(DocVQAActorAdapter(data)).using(), self.assertRaises(ValueError):
            evaluation.prepare_test(root, self.root / 'test')

    def test_completed_legacy_source_provenance_is_not_rewritten_or_required_for_test(self):
        data, _, root = self.complete()
        path = root / 'implementation.json'; old = ev.read(path)
        old['sources'] = {'previous_runtime.py': 'old hash'}
        ev.save(path, old)
        before = snapshot(root)
        with CampaignAdapter(DocVQAActorAdapter(data)).using():
            evaluation.prepare_test(root, self.root / 'test')
        self.assertEqual(snapshot(root), before)
        old['prompts']['diagnosis'] = 'wrong method prompt'
        ev.save(path, old)
        with CampaignAdapter(DocVQAActorAdapter(data)).using(), self.assertRaises(ValueError):
            evaluation.prepare_test(root, self.root / 'test')

    def test_no_replay_of_published_rounds_when_continuing(self):
        data, actor, adapter, config = bind(self.root / 'fixture', mode='gain')
        root = self.root / 'continue'; generator = Generator(count=1)
        with adapter.using():
            ev.run_round(root, config=config, generate=generator)
        first_calls = len(generator.calls)
        with CampaignAdapter(DocVQAActorAdapter(data, actor)).using():
            original = ev._execute_round
            def only_next(*args, **kwargs):
                self.assertEqual(args[2]['next_round'], 2)
                return original(*args, **kwargs)
            with patch.object(ev, '_execute_round', side_effect=only_next):
                ev.run_campaign(root, generate=generator)
        self.assertEqual(generator.calls[first_calls:], ['grouping', 'diagnosis', 'preconditioner', 'editor'])
        self.assertEqual(len(actor.seen), 8)

    def test_resume_at_all_publication_and_execution_boundaries(self):
        points = ('parent_runs', 'grouping', 'diagnosis', 'preconditioner', 'editor', 'candidate_runs',
                  'pairs', 'replay', 'gate', 'memory', 'memory_prepared', 'before_memory_commit',
                  'after_memory_commit', 'before_publish', 'after_publish')
        for point in points:
            with self.subTest(point=point):
                data, actor, adapter, config = bind(self.root / (point+'_data'), sizes=(1,), mode='gain')
                root = self.root / point; generator = Generator(count=1)
                def hook(stage):
                    if stage == point: raise KeyboardInterrupt()
                with adapter.using(), self.assertRaises(KeyboardInterrupt):
                    ev.run_campaign(root, config=config, generate=generator, hook=hook)
                with CampaignAdapter(DocVQAActorAdapter(data, actor)).using():
                    self.assertEqual(ev.run_campaign(root, resume=True, generate=generator)['status'], 'complete')
                    self.assertEqual(len(memory.load_memory(root/'memory')['memory']['rounds']), 1)
                self.assertEqual(len(actor.seen), 2)
                self.assertEqual(generator.calls, ['grouping','diagnosis','preconditioner','editor','replay'])

    def test_failed_replay_budget_and_semantic_stop_do_not_reset(self):
        for mode in ['invalid', 'null']:
            data, actor, adapter, config = bind(self.root/(mode+'_data'), sizes=(1,), mode='gain')
            generator = Generator(count=1, invalid_replay=mode=='invalid', null=mode=='null')
            root = self.root/mode
            with adapter.using(), self.assertRaises((ValueError, ev.Stopped)):
                ev.run_campaign(root, config=config, generate=generator)
            counts = (len(actor.seen), len(generator.calls))
            with CampaignAdapter(DocVQAActorAdapter(data, actor)).using(), self.assertRaises((ValueError, ev.Stopped)):
                ev.run_campaign(root, resume=True, generate=generator)
            self.assertEqual(counts, (len(actor.seen),len(generator.calls)))

    def test_cli_does_not_call_prepare_twice_before_test(self):
        from scripts.runs import run_v29_3_campaign as cli
        data, _, adapter, config = bind(self.root/'fixture', sizes=(1,))
        root = self.root/'cli'; ev.save(root/'config.json', config)
        with patch.object(cli, 'DocVQADataset', return_value=data), \
             patch.object(cli, 'read_credentials', return_value={'OPENAI_API_KEY':'offline'}), \
             patch.object(cli, 'prepare_test', side_effect=AssertionError('Duplicate preflight')), \
             patch.object(cli, 'run_test', return_value={'status':'offline'}) as run:
            cli.main(['test',str(root),'--output',str(self.root/'test')])
        run.assert_called_once()
