"""Offline scheduling, publication, recovery and lightweight checkpoints; no provider calls."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v29 import evolution, stages, memory_operation
from src.skill_evolution.v29.campaign import CampaignAdapter
from src.skill_evolution.v29.config import campaign_config, validate_config
from src.skill_evolution.v29.benchmarks.docvqa import protocol as p
from src.skill_evolution.v29.benchmarks.docvqa.adapter import DocVQAActorAdapter
from src.skill_evolution.v29.benchmarks.docvqa.dataset import DocVQADataset
from .test_actor import Base
from .campaign_support import bind, Generator


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}


class CampaignTests(Base):
    def test_pilot_stops_after_first_round_and_resume_cannot_start_second(self):
        from scripts.runs.run_v29_pilot import run_pilot
        _, transport, adapter, config = bind(self.root / 'pilot_fixture')
        root = self.root / 'pilot'; generator = Generator()
        with adapter.using():
            first = run_pilot(root, config, generate=generator)
            count = (len(transport.seen), len(generator.calls))
            self.assertEqual(evolution.read(root / 'state.json')['next_round'], 2)
            self.assertEqual(run_pilot(root, config, generate=generator, resume=True), first)
            self.assertEqual((len(transport.seen), len(generator.calls)), count)
            self.assertFalse((root / 'rounds/R02').exists())
            self.reject(run_pilot, root, config, generate=generator)

    def test_pilot_resumes_interrupted_first_round(self):
        from scripts.runs.run_v29_pilot import run_pilot
        _, transport, adapter, config = bind(self.root / 'pilot_fixture')
        root = self.root / 'pilot'; generator = Generator()
        def interrupted(*args):
            raise KeyboardInterrupt('Synthetic interruption')
        with adapter.using():
            with self.assertRaises(KeyboardInterrupt):
                run_pilot(root, config, generate=interrupted)
            actor_calls = len(transport.seen)
            run_pilot(root, config, generate=generator, resume=True)
            self.assertEqual(len(transport.seen), actor_calls * 2)
            self.assertEqual(evolution.read(root / 'state.json')['next_round'], 2)
            self.assertFalse((root / 'rounds/R02').exists())

    def reject(self, fn, *args, **kwargs):
        with self.assertRaises((ValueError, KeyError, FileNotFoundError, stages.Stopped)):
            fn(*args, **kwargs)

    def test_real_schedule_has_pending_budgets_and_no_execution(self):
        adapter = CampaignAdapter(DocVQAActorAdapter(DocVQADataset()))
        with adapter.using():
            config = campaign_config(adapter)
            validate_config(config)
            self.assertEqual([len(b) for b in config['batches']], [15] * 10 + [10])
            self.assertEqual(config['initial_skill'], p.initial_skill())
            self.assertTrue(all(v['max_tokens'] is None and v['timeout_seconds'] is None
                                for v in config['module_calls'].values()))
            self.reject(validate_config, config, executable=True)
            for change in (lambda c: c['batches'].reverse(), lambda c: c['batches'].pop(),
                           lambda c: c['batches'][0].append(c['batches'][1][0]),
                           lambda c: c['batches'][0].__setitem__(0, adapter.dataset.splits['test'][0]),
                           lambda c: c.update(max_attempts=7), lambda c: c.update(continue_no_change=False),
                           lambda c: c.update(initial_skill='Other skill'),
                           lambda c: c['method'].update(knowledge_review='enabled')):
                bad = deepcopy(config); change(bad); self.reject(validate_config, bad)

    def test_pending_budgets_stop_before_actor_or_method_requests(self):
        _, transport, adapter, _ = bind(self.root / 'fixture', rounds=1)
        generator = Generator(); root = self.root / 'pending'
        with adapter.using():
            self.reject(evolution.run_campaign, root, config=campaign_config(adapter), generate=generator)
        self.assertEqual(transport.seen, [])
        self.assertEqual(generator.calls, [])
        self.assertFalse((root / 'rounds').exists())

    def test_accept_retain_and_fresh_read_only_final_checkpoint(self):
        for accept in (True, False):
            data, transport, adapter, config = bind(self.root / str(accept), accept=accept)
            root = self.root / f'chain_{accept}'; generator = Generator()
            with adapter.using():
                result = evolution.run_campaign(root, config=config, generate=generator)
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(result['state']['next_round'], 3)
                self.assertEqual(generator.calls, ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'] * 2)
                self.assertEqual(len(transport.seen), 8)
                first = stages.read(root / 'rounds/R01/gate/result.json')['result']['decision']
                self.assertEqual(first, 'ACCEPT' if accept else 'RETAIN')
                active = adapter.load_memory(root / result['state']['active_memory'])
                self.assertEqual(len(active['entries']), 2)
            before = snapshot(root)
            fresh = CampaignAdapter(DocVQAActorAdapter(data))
            with fresh.using():
                final = evolution.final_parent(root)
                self.assertIn('Compare the requested amount role.', final.read_text()) if accept else self.assertEqual(final.read_text(), p.initial_skill())
            self.assertEqual(snapshot(root), before)

    def test_all_no_change_branches_continue(self):
        for branch in ('diagnosis', 'preconditioner', 'editor'):
            _, transport, adapter, config = bind(self.root / f'fixture_{branch}')
            root = self.root / branch; generator = Generator(no_change=branch)
            with adapter.using():
                result = evolution.run_campaign(root, config=config, generate=generator)
                self.assertEqual(result['state'], {'next_round': 3, 'parent': 'initial_skill.md', 'active_memory': 'initial_memory'})
                self.assertEqual(len(transport.seen), 4)
                self.assertNotIn('replay', generator.calls)
                self.assertEqual(evolution.final_parent(root).read_text(), p.initial_skill())

    def test_all_eleven_synthetic_batches_preserve_order_and_tail(self):
        data, transport, adapter, config = bind(self.root / 'fixture', sizes=[15] * 10 + [10])
        generator = Generator(no_change='diagnosis'); root = self.root / 'full_schedule'
        with adapter.using():
            result = evolution.run_campaign(root, config=config, generate=generator)
            self.assertEqual(result['state']['next_round'], 12)
            self.assertEqual(len(transport.seen), 160)
            self.assertEqual(generator.calls.count('grouping'), 11)
            actual = [t for n in range(1, 12) for t in stages.read(root / f'rounds/R{n:02}/round_input.json')['tasks']]
            self.assertEqual(actual, data.splits['train'])
            self.assertFalse(set(actual) & set(data.splits['test']))

    def test_editor_null_stops_without_semantic_resampling(self):
        _, transport, adapter, config = bind(self.root / 'fixture', rounds=1)
        generator = Generator(semantic_stop=True); root = self.root / 'semantic'
        with adapter.using():
            self.reject(evolution.run_campaign, root, config=config, generate=generator)
            self.assertEqual(stages.read(root / 'stop.json')['kind'], 'semantic')
            self.reject(evolution.run_campaign, root, generate=generator, resume=True)
            self.assertEqual(generator.calls.count('editor'), 1)
            self.assertEqual(len(transport.seen), 2)
            self.reject(evolution.final_parent, root)

    def test_replay_failure_never_publishes_even_if_gate_accepts(self):
        _, transport, adapter, config = bind(self.root / 'fixture', rounds=1)
        generator = Generator(invalid_replay=True); root = self.root / 'failed_replay'
        with adapter.using():
            self.reject(evolution.run_campaign, root, config=config, generate=generator)
            self.assertEqual(stages.read(root / 'rounds/R01/gate/result.json')['result']['decision'], 'ACCEPT')
            self.assertEqual(stages.read(root / 'state.json')['next_round'], 1)
            self.assertEqual(stages.read(root / 'state.json')['active_memory'], 'initial_memory')
            self.assertEqual(generator.calls.count('replay'), 6)
            self.reject(evolution.run_campaign, root, generate=Generator(), resume=True)
            self.assertEqual(len(transport.seen), 4)
            self.assertFalse((root / 'rounds/R01/memory/active.json').exists())

    def test_resume_every_stage_and_publication_boundary(self):
        points = ('parent_runs', 'grouping', 'diagnosis', 'preconditioner', 'editor', 'candidate_runs',
                  'pairs', 'gate', 'replay', 'knowledge_review', 'memory', 'memory_prepared', 'before_publish', 'after_publish')
        for point in points:
            with self.subTest(point=point):
                data, transport, adapter, config = bind(self.root / f'fixture_{point}', rounds=1, batch_size=1)
                root = self.root / point; generator = Generator()
                def hook(stage):
                    if stage == point: raise KeyboardInterrupt()
                with adapter.using():
                    with self.assertRaises(KeyboardInterrupt):
                        evolution.run_campaign(root, config=config, generate=generator, hook=hook)
                    self.assertEqual(stages.read(root / 'state.json')['next_round'], 2 if point == 'after_publish' else 1)
                fresh = CampaignAdapter(DocVQAActorAdapter(data, transport))
                with fresh.using():
                    result = evolution.run_campaign(root, generate=generator, resume=True)
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(len(transport.seen), 2)
                self.assertEqual(generator.calls, ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'])

    def test_round_limit_and_corrupt_published_dependency_stop_before_requests(self):
        data, transport, adapter, config = bind(self.root / 'fixture')
        generator = Generator(); root = self.root / 'bounded'
        with adapter.using(): evolution.run_round(root, config=config, generate=generator)
        fresh = CampaignAdapter(DocVQAActorAdapter(data, transport))
        with fresh.using():
            evolution.run_campaign(root, generate=generator, resume=True)
            before = snapshot(root); calls = (len(transport.seen), len(generator.calls))
            for target in ('state.json', 'config.json'):
                value = stages.read(root / target); value['changed'] = True; stages.save(root / target, value)
                self.reject(evolution.run_campaign, root, generate=generator, resume=True)
                self.assertEqual(calls, (len(transport.seen), len(generator.calls)))
                (root / target).write_bytes(before[target])

    def test_actor_saved_response_recovers_without_new_requests(self):
        _, transport, adapter, config = bind(self.root / 'fixture', rounds=1, batch_size=1)
        original = transport.generate
        def interrupt(messages, slot):
            stages.save(slot / 'response.json', original(messages, slot)); raise KeyboardInterrupt()
        transport.generate = interrupt
        root = self.root / 'actor_interrupted'; generator = Generator(no_change='diagnosis')
        with adapter.using():
            with self.assertRaises(KeyboardInterrupt): evolution.run_campaign(root, config=config, generate=generator)
            transport.generate = original
            self.assertEqual(evolution.run_campaign(root, generate=generator, resume=True)['status'], 'complete')
        self.assertEqual(len(transport.seen), 1)

    def test_archive_only_recovery_rebuilds_completed_actor_batch(self):
        data, transport, adapter, config = bind(self.root / 'fixture', rounds=1)
        directory = self.root / 'batch'
        expected = adapter.actor_batch(data.batches[0], self.skill_file, directory, {'split': 'train', 'role': 'parent'})
        (directory / 'records.json').unlink()
        fresh = CampaignAdapter(DocVQAActorAdapter(data))
        with fresh.using():
            self.assertEqual(fresh.actor_batch(data.batches[0], self.skill_file, directory,
                                             {'split': 'train', 'role': 'parent'}), expected)
            self.assertEqual(len(transport.seen), 2)
            (directory / 'records.json').unlink(); (directory / 'actor/0001/result.json').unlink()
            self.reject(fresh.actor_batch, data.batches[0], self.skill_file, directory, {'split': 'train', 'role': 'parent'})

    def test_full_publication_reuses_history_through_preparation_and_state_switch(self):
        _, _, adapter, config = bind(self.root / 'fixture', rounds=2, batch_size=1)
        generator = Generator(); root = self.root / 'reuse'
        with adapter.using():
            evolution.run_round(root, config=config, generate=generator)
            with patch.object(memory, '_archive', wraps=memory._archive) as history, \
                 patch.object(adapter.actor_adapter, 'read_batch', wraps=adapter.actor_adapter.read_batch) as batches:
                def hook(stage):
                    if stage == 'knowledge_review': history.reset_mock(); batches.reset_mock()
                evolution.run_round(root, generate=generator, hook=hook)
                self.assertEqual(history.call_count, 0)
                self.assertEqual(batches.call_count, 2)
        self.assertIsNone(memory_operation.current(adapter))

    def test_mutated_prepared_publication_never_advances_official_state(self):
        for target in ('active', 'skill', 'result'):
            with self.subTest(target=target):
                _, _, adapter, config = bind(self.root / f'fixture_{target}', rounds=1, batch_size=1)
                root = self.root / target
                def hook(stage):
                    if stage != 'before_publish': return
                    rd = root / 'rounds/R01'
                    paths = {'active': rd / 'memory/active.json', 'view': rd / 'memory/view.json',
                             'commit': rd / f'memory/archive/{root.name}_R01.json', 'base': rd / 'memory/base.json',
                             'skill': rd / 'editor/attempts/001/candidate.md',
                             'response': rd / 'parent_runs/actor/0001/attempts/001/response.json',
                             'gate': rd / 'gate/result.json', 'result': rd / 'result.json'}
                    path = paths[target]
                    if target == 'active': stages.save(path, {'active_ids': [], 'commits': []})
                    elif target == 'result':
                        value = stages.read(path); value['outcome'] = 'changed'; stages.save(path, value)
                    else: path.write_bytes(path.read_bytes() + b' ')
                with adapter.using(): self.reject(evolution.run_campaign, root, config=config, generate=Generator(), hook=hook)
                self.assertEqual(stages.read(root / 'state.json')['next_round'], 1)

    def test_commit_active_interruption_recovers_without_replay_or_actor_resampling(self):
        data, transport, adapter, config = bind(self.root / 'fixture', rounds=1, batch_size=1)
        root = self.root / 'commit_interrupted'; generator = Generator(); original = memory.write_record
        def interrupt(path, value):
            if path.name == 'active.json': raise KeyboardInterrupt()
            return original(path, value)
        with adapter.using(), patch.object(memory, 'write_record', interrupt), self.assertRaises(KeyboardInterrupt):
            evolution.run_campaign(root, config=config, generate=generator)
        self.assertEqual(stages.read(root / 'state.json')['next_round'], 1)
        fresh = CampaignAdapter(DocVQAActorAdapter(data))
        with fresh.using():
            result = evolution.run_campaign(root, resume=True)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(transport.seen), 2)
        self.assertEqual(generator.calls.count('replay'), 1)

    def test_method_receipt_changed_during_memory_preparation_cannot_publish(self):
        _, _, adapter, config = bind(self.root / 'fixture', rounds=1, batch_size=1)
        root = self.root / 'changed_gate'
        def hook(stage):
            if stage == 'memory_prepared':
                path = root / 'rounds/R01/gate/result.json'
                value = stages.read(path); value['result']['decision'] = 'RETAIN'; stages.save(path, value)
        with adapter.using():
            self.reject(evolution.run_campaign, root, config=config, generate=Generator(), hook=hook)
        self.assertEqual(stages.read(root / 'state.json')['next_round'], 1)

    def test_final_checkpoint_does_not_reopen_historical_actor_or_replay_rounds(self):
        data, transport, adapter, config = bind(self.root / 'fixture', rounds=2, batch_size=1)
        root = self.root / 'light'; generator = Generator()
        with adapter.using(): evolution.run_campaign(root, config=config, generate=generator)
        before = snapshot(root)
        fresh = CampaignAdapter(DocVQAActorAdapter(data))
        with fresh.using(), patch.object(fresh.actor_adapter, 'read_batch', side_effect=AssertionError('Old Actor')), \
             patch.object(evolution, '_execute_round', side_effect=AssertionError('Old round')):
            final = evolution.final_parent(root)
            self.assertTrue(final.read_text().strip())
        self.assertEqual(snapshot(root), before)

    def test_next_round_does_not_replay_previously_published_round(self):
        data, transport, adapter, config = bind(self.root / 'fixture', rounds=2, batch_size=1)
        root = self.root / 'light_continue'; generator = Generator()
        with adapter.using(): evolution.run_round(root, config=config, generate=generator)
        original = evolution._execute_round
        def only_next(*args, **kwargs):
            self.assertEqual(args[2]['next_round'], 2)
            return original(*args, **kwargs)
        with CampaignAdapter(DocVQAActorAdapter(data, transport)).using(), \
             patch.object(evolution, '_execute_round', side_effect=only_next):
            evolution.run_campaign(root, generate=generator)
        self.assertEqual(generator.calls.count('replay'), 2)
