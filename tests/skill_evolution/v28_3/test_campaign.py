"""Offline full-loop and recovery acceptance with authored responses only."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v28_3.actor_io import ActorAdapter
from src.skill_evolution.v28.benchmarks.searchqa import protocol
from src.skill_evolution.v28_3 import evolution as ev, config as settings, memory, stages
from src.skill_evolution.v28_3.campaign import CampaignAdapter
from tests.skill_evolution.v28.runtime_support import Base
from tests.skill_evolution.v28.runtime_support import snapshot
from tests.skill_evolution.v28_3.test_editor import offline
from .support import bind, Generator, no_hashes


class CampaignTests(Base):
    def setUp(self):
        super().setUp(); offline(self); self.enterContext(no_hashes())

    def reject(self, fn, *args, **kwargs):
        with self.assertRaises((ValueError, KeyError, FileNotFoundError, stages.Stopped)):
            fn(*args, **kwargs)

    def test_selective_gate_updates_next_parent_and_passes_full_history(self):
        data, actor, adapter, config = bind(self.root / 'fixture')
        root = self.root / 'selective'; generate = Generator()
        with adapter.using():
            result = ev.run_campaign(root, config=config, generate=generate)
            first = ev.read(root / 'rounds/R01/result.json')
            self.assertIsNone(first['selected_execution_source'])
            self.assertEqual(first['selection']['selected_update_ids'], ['u1'])
            decisions = ev.read(root / 'rounds/R01/gate/result.json')['decisions']
            self.assertEqual([(d['G'], d['L'], d['gate_decision']) for d in decisions], [(1, 0, 'Retain'), (0, 1, 'Reject')])
            second = ev.read(root / 'rounds/R02/round_input.json')
            self.assertEqual(second['parent'], first['selection']['selected_text'])
            self.assertIn('rule u1', second['parent']); self.assertNotIn('rule u2', second['parent'])
            inputs = [value for name, value in generate.inputs if name == 'preconditioner']
            self.assertEqual(inputs[0]['memory'], {'rounds': []})
            self.assertEqual(inputs[1]['memory'], second['memory'])
            self.assertEqual(len(inputs[1]['memory']['rounds'][0]['source_updates']), 2)
            state = memory.load_memory(root / 'memory')
            self.assertEqual(result['state']['memory_head'], state['head'])
            self.assertEqual([e['id'] for r in state['memory']['rounds'] for e in r['entries']], ['M1', 'M2', 'M3'])
            self.assertEqual(len(actor.seen), 8)
            self.assertEqual(generate.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'] * 2)
        before = snapshot(root)
        with CampaignAdapter(ActorAdapter(data)).using():
            self.assertEqual(ev.final_parent(root).read_text(), first['selection']['selected_text'])
        self.assertEqual(snapshot(root), before)

    def test_all_retain_uses_candidate_exact_text_and_all_reject_retains_parent(self):
        for mode, decision, source in (('gain', 'Retain', 'candidate'), ('loss', 'Reject', 'parent')):
            _, actor, adapter, config = bind(self.root / mode, sizes=(1,), mode=mode)
            root = self.root / f'run_{mode}'; generate = Generator(count=1)
            with adapter.using():
                ev.run_campaign(root, config=config, generate=generate)
                gate = ev.read(root / 'rounds/R01/gate/result.json')
                self.assertEqual(gate['decisions'][0]['gate_decision'], decision)
                self.assertEqual(gate['selected_execution_source'], source)
                self.assertEqual(ev.final_parent(root).read_text(), gate['selection']['selected_text'])
                self.assertEqual(len(actor.seen), 2)

    def test_no_change_and_withdraw_do_not_commit_but_empty_editor_does(self):
        for branch in ('diagnosis', 'preconditioner', 'editor'):
            _, actor, adapter, config = bind(self.root / f'fixture_{branch}')
            root = self.root / branch; generate = Generator(no_change=branch)
            with adapter.using():
                result = ev.run_campaign(root, config=config, generate=generate)
                self.assertEqual(result['state']['next_round'], 3)
                self.assertEqual(ev.final_parent(root).read_text(), settings.initial_skill()['text'])
                state = memory.load_memory(root / 'memory')
                self.assertEqual(len(state['memory']['rounds']), 2 if branch == 'editor' else 0)
                if branch == 'editor':
                    self.assertEqual(state['memory']['rounds'][0]['entries'], [])
                    self.assertTrue(all(u['gate_decision'] is None for u in state['memory']['rounds'][0]['source_updates']))
                self.assertEqual(len(actor.seen), 4)
                self.assertNotIn('replay', generate.calls)
                self.assertFalse((root / 'rounds/R01/candidate_runs').exists())

    def test_no_transitions_skip_replay_but_record_all_deferred_updates(self):
        _, actor, adapter, config = bind(self.root / 'fixture', sizes=(2,), mode='none')
        root = self.root / 'skip'; generate = Generator()
        with adapter.using():
            ev.run_campaign(root, config=config, generate=generate)
            record = memory.load_memory(root / 'memory')['memory']['rounds'][0]
            self.assertEqual(record['entries'], [])
            self.assertEqual([u['gate_decision'] for u in record['source_updates']], ['Defer', 'Defer'])
            self.assertFalse((root / 'rounds/R01/replay/attempts').exists())
            self.assertNotIn('replay', generate.calls)
            self.assertEqual(len(actor.seen), 4)

    def test_unresolved_and_conflicting_evidence_are_deferred(self):
        for attribution in ('unresolved', 'conflict'):
            _, _, adapter, config = bind(self.root / attribution, sizes=(2,))
            root = self.root / f'run_{attribution}'
            with adapter.using():
                ev.run_campaign(root, config=config, generate=Generator(attribution=attribution))
                gate = ev.read(root / 'rounds/R01/gate/result.json')
                self.assertEqual([d['gate_decision'] for d in gate['decisions']], ['Defer', 'Defer'])
                self.assertEqual(gate['selection']['selected_text'], settings.initial_skill()['text'])
                self.assertEqual(len(memory.load_memory(root / 'memory')['memory']['rounds'][0]['entries']), 2)

    def test_null_editor_stops_before_candidate_and_never_resamples(self):
        _, actor, adapter, config = bind(self.root / 'fixture', sizes=(1,))
        root = self.root / 'null'; generate = Generator(null=True)
        with adapter.using():
            self.reject(ev.run_campaign, root, config=config, generate=generate)
            self.assertEqual(ev.read(root / 'stop.json')['kind'], 'semantic')
            self.reject(ev.run_campaign, root, generate=generate, resume=True)
            self.assertEqual(ev.read(root / 'state.json'), ev._initial_state())
            self.assertIsNone(memory.load_memory(root / 'memory')['head'])
        self.assertEqual(generate.calls.count('editor'), 1)
        self.assertEqual(len(actor.seen), 1)
        self.assertFalse((root / 'rounds/R01/candidate_runs').exists())

    def test_invalid_replay_exhausts_shared_budget_without_gate_or_publication(self):
        _, actor, adapter, config = bind(self.root / 'fixture', sizes=(1,), mode='gain')
        root = self.root / 'failed'; generate = Generator(count=1, invalid_replay=True)
        with adapter.using():
            self.reject(ev.run_campaign, root, config=config, generate=generate)
            self.reject(ev.run_campaign, root, generate=generate, resume=True)
            self.assertEqual(ev.read(root / 'state.json'), ev._initial_state())
            self.assertIsNone(memory.load_memory(root / 'memory')['head'])
        self.assertEqual(generate.calls.count('replay'), 6)
        self.assertEqual(len(actor.seen), 2)
        self.assertFalse((root / 'rounds/R01/gate').exists())

    def test_resume_stage_and_publication_boundaries_without_duplicate_execution(self):
        points = ('parent_runs', 'diagnosis', 'preconditioner', 'editor', 'candidate_runs',
                  'pairs', 'replay', 'gate', 'memory', 'memory_prepared', 'before_memory_commit',
                  'after_memory_commit', 'before_publish', 'after_publish')
        for point in points:
            with self.subTest(point=point):
                data, actor, adapter, config = bind(self.root / f'fixture_{point}', sizes=(1,), mode='gain')
                root = self.root / point; generate = Generator(count=1)
                def hook(stage):
                    if stage == point: raise KeyboardInterrupt()
                with adapter.using(), self.assertRaises(KeyboardInterrupt):
                    ev.run_campaign(root, config=config, generate=generate, hook=hook)
                with CampaignAdapter(ActorAdapter(data, actor)).using():
                    if point != 'after_publish': self.reject(ev.run_campaign, root, generate=generate)
                    result = ev.run_campaign(root, generate=generate, resume=True)
                    self.assertEqual(result['status'], 'complete')
                    self.assertEqual(len(memory.load_memory(root / 'memory')['memory']['rounds']), 1)
                self.assertEqual(len(actor.seen), 2)
                self.assertEqual(generate.calls, ['diagnosis', 'preconditioner', 'editor', 'replay'])

    def test_memory_head_published_cursor_lag_recovers_without_transports(self):
        data, actor, adapter, config = bind(self.root / 'fixture', sizes=(1,), mode='gain')
        root = self.root / 'committed'; generate = Generator(count=1)
        def hook(stage):
            if stage == 'after_memory_commit': raise KeyboardInterrupt()
        with adapter.using(), self.assertRaises(KeyboardInterrupt):
            ev.run_campaign(root, config=config, generate=generate, hook=hook)
        self.assertEqual(ev.read(root / 'state.json')['next_round'], 1)
        self.assertFalse((root / 'rounds/R01/memory_receipt.json').exists())
        with CampaignAdapter(ActorAdapter(data)).using():
            self.assertEqual(ev.run_campaign(root, resume=True)['status'], 'complete')
            self.assertEqual(len(memory.load_memory(root / 'memory')['memory']['rounds']), 1)
        self.assertEqual(len(actor.seen), 2)
        self.assertEqual(generate.calls.count('replay'), 1)

    def test_interrupted_memory_head_write_reuses_immutable_objects(self):
        data, actor, adapter, config = bind(self.root / 'fixture', sizes=(1,), mode='gain')
        root = self.root / 'head_failure'; generate = Generator(count=1)
        original = memory._publish_head
        def fail(directory, head):
            if head is not None: raise OSError('Synthetic disk failure before HEAD')
            return original(directory, head)
        with adapter.using(), patch.object(memory, '_publish_head', fail), self.assertRaises(OSError):
            ev.run_campaign(root, config=config, generate=generate)
        with CampaignAdapter(ActorAdapter(data)).using():
            self.assertEqual(ev.run_campaign(root, resume=True)['status'], 'complete')
        self.assertEqual(len(list((root / 'memory/commits').glob('*.json'))), 1)
        self.assertEqual(len(actor.seen), 2)
        self.assertEqual(generate.calls.count('replay'), 1)

    def test_pending_budget_and_old_config_stop_before_execution(self):
        _, actor, adapter, config = bind(self.root / 'fixture', sizes=(1,))
        generate = Generator()
        with adapter.using():
            bad = deepcopy(config); bad['module_calls']['editor']['max_tokens'] = 16384
            self.reject(ev.run_campaign, self.root / 'pending', config=bad, generate=generate)
            old = deepcopy(config); old['method']['version'] = 'v28_1_campaign_v1'
            self.reject(ev.run_campaign, self.root / 'old', config=old, generate=generate)
        self.assertEqual(actor.seen, []); self.assertEqual(generate.calls, [])
        self.assertFalse((self.root / 'pending/rounds').exists())

    def test_round_limit_preserves_fresh_next_batch_and_rejects_invalid_checkpoint(self):
        data, actor, adapter, config = bind(self.root / 'fixture')
        root = self.root / 'limited'; generate = Generator()
        with adapter.using():
            ev.run_round(root, config=config, generate=generate)
            self.assertFalse((root / 'rounds/R02').exists())
            self.reject(ev.final_parent, root)
        with CampaignAdapter(ActorAdapter(data, actor)).using():
            ev.run_campaign(root, generate=generate)
            baseline = snapshot(root); counts = len(actor.seen), len(generate.calls)
            for target in ('rounds/R02/result.json', 'state.json', 'config.json'):
                path = root / target
                path.write_text('corrupt')
                self.reject(ev.run_campaign, root, generate=generate, resume=True)
                path.write_bytes(baseline[target])
                self.assertEqual((len(actor.seen), len(generate.calls)), counts)

    def test_mutation_before_commit_or_publish_never_advances_cursor(self):
        for point in ('before_memory_commit', 'before_publish'):
            _, _, adapter, config = bind(self.root / point, sizes=(1,), mode='gain')
            root = self.root / f'run_{point}'
            def hook(stage):
                if stage == point:
                    path = root / 'rounds/R01/selected.md'
                    path.write_text(path.read_text() + 'changed')
            with adapter.using():
                self.reject(ev.run_campaign, root, config=config, generate=Generator(count=1), hook=hook)
                self.assertEqual(ev.read(root / 'state.json')['next_round'], 1)
                if point == 'before_memory_commit': self.assertIsNone(memory.load_memory(root / 'memory')['head'])

    def test_actor_saved_response_recovers_without_resampling(self):
        _, actor, adapter, config = bind(self.root / 'fixture', sizes=(1,))
        original = actor.generate; root = self.root / 'actor_saved'; generate = Generator(no_change='diagnosis')
        def fail(messages, slot):
            ev.save(slot / 'response.json', original(messages, slot)); raise KeyboardInterrupt()
        actor.generate = fail
        with adapter.using():
            with self.assertRaises(KeyboardInterrupt): ev.run_campaign(root, config=config, generate=generate)
            actor.generate = original
            self.assertEqual(ev.run_campaign(root, generate=generate, resume=True)['status'], 'complete')
        self.assertEqual(len(actor.seen), 1)

    def test_full_synthetic_schedule_and_training_export(self):
        from scripts.runs.run_v28_3_campaign import run_training, run_test
        data, actor, adapter, config = bind(self.root / 'fixture', sizes=(30,) * 20, test_size=1400)
        root = self.root / 'full'; generate = Generator(no_change='diagnosis')
        with adapter.using():
            summary = run_training(root, config, generate=generate)
            self.assertEqual(summary['rounds_completed'], 20)
            self.assertEqual(summary['optimization_count'], 600)
            self.assertFalse(summary['test_started'])
            self.assertEqual(summary['selected_execution_source'], 'parent')
            self.assertEqual((root / 'final_skill.md').read_text(), settings.initial_skill()['text'])
            self.assertEqual(len(actor.seen), 600)
            self.assertEqual(generate.calls.count('diagnosis'), 20)
            ordered = [t for i in range(1, 21) for t in ev.read(root / f'rounds/R{i:02}/round_input.json')['tasks']]
            self.assertEqual(ordered, data.splits['train'])
            self.assertTrue(set(ordered).isdisjoint(data.splits['test']))
            before = snapshot(root)
            calls = list(generate.calls)
            evaluated = run_test(root, self.root / 'synthetic_test')
            self.assertEqual(evaluated['sample_count'], 1400)
            self.assertEqual(len(actor.seen), 2000)
            self.assertEqual(generate.calls, calls)
            self.assertEqual(snapshot(root), before)

    def test_export_does_not_claim_subset_was_executed(self):
        from scripts.runs.run_v28_3_campaign import run_training
        data, _, adapter, config = bind(self.root / 'fixture', sizes=(2,))
        root = self.root / 'export'
        with adapter.using(): summary = run_training(root, config, generate=Generator())
        self.assertIsNone(summary['selected_execution_source'])
        self.assertNotIn('em', summary); self.assertNotIn('f1', summary)
        before = snapshot(root)
        with CampaignAdapter(ActorAdapter(data)).using():
            self.assertEqual(run_training(root, config, resume=True), summary)
        self.assertEqual(snapshot(root), before)

    def test_cli_validate_only_reads_no_credentials_and_creates_no_campaign(self):
        from scripts.runs import run_v28_3_campaign as cli
        data, _, adapter, config = bind(self.root / 'fixture', sizes=(1,))
        # Match the explicit production worker choice without executing anything.
        adapter.actor_adapter.workers = 15
        root = self.root / 'cli'; path = self.root / 'config.json'; ev.save(path, config)
        with patch.object(cli, 'SearchQADataset', return_value=data), \
             patch.object(cli, 'read_credentials', side_effect=AssertionError('No credentials in preflight')), \
             patch.object(cli, 'run_training', side_effect=AssertionError('No execution in preflight')):
            cli.main(['train', str(root), '--config', str(path), '--validate-only'])
        self.assertFalse(root.exists())

    def test_rounds_without_memory_do_not_confuse_memory_sequence_or_validation(self):
        data, actor, adapter, config = bind(self.root / 'fixture', sizes=(2, 2, 2))
        root = self.root / 'sparse'
        with adapter.using():
            ev.run_round(root, config=config, generate=Generator(no_change='diagnosis'))
            self.assertIsNone(ev.read(root / 'state.json')['memory_head'])
            ev.run_round(root, generate=Generator())
            second = ev.read(root / 'rounds/R02/result.json')
            self.assertIsNone(second['selected_execution_source'])
            head = second['after']['memory_head']
            self.assertTrue(head == '000001')
            ev.run_round(root, generate=Generator(no_change='preconditioner'))
            last = ev.read(root / 'rounds/R03/result.json')
            self.assertEqual(last['after']['memory_head'], head)
            self.assertEqual(last['selected_execution_source'], 'parent')
            state = memory.load_memory(root / 'memory')
            self.assertEqual([r['round_id'] for r in state['memory']['rounds']], ['sparse_R02'])
            self.assertIsNone(state['selected_execution_source'])  # Historical joint selection remains historical.
            self.assertEqual(len(actor.seen), 8)
        with CampaignAdapter(ActorAdapter(data)).using():
            self.assertEqual(ev.final_parent(root).read_text(), second['selection']['selected_text'])

    def test_committed_recovery_requires_existing_model_results(self):
        data, actor, adapter, config = bind(self.root / 'fixture', sizes=(1,), mode='gain')
        root = self.root / 'missing_result'; generate = Generator(count=1)
        def hook(stage):
            if stage == 'after_memory_commit': raise KeyboardInterrupt()
        with adapter.using(), self.assertRaises(KeyboardInterrupt):
            ev.run_campaign(root, config=config, generate=generate, hook=hook)
        (root / 'rounds/R01/replay/result.json').unlink()
        with CampaignAdapter(ActorAdapter(data, actor)).using():
            self.reject(ev.run_campaign, root, generate=generate, resume=True)
        self.assertEqual(ev.read(root / 'state.json')['next_round'], 1)
        self.assertEqual(len(actor.seen), 2)
        self.assertEqual(generate.calls.count('replay'), 1)

    def test_missing_official_state_is_not_reinitialized_over_completed_rounds(self):
        _, _, adapter, config = bind(self.root / 'fixture', sizes=(1,))
        root = self.root / 'missing_cursor'
        with adapter.using():
            ev.run_campaign(root, config=config, generate=Generator(no_change='diagnosis'))
            (root / 'state.json').unlink()
            self.reject(ev.run_campaign, root, config=config, generate=Generator(), resume=True)
        self.assertFalse((root / 'state.json').exists())

    def test_writer_lock_prevents_second_campaign_execution(self):
        _, actor, adapter, config = bind(self.root / 'fixture', sizes=(1,))
        root = self.root / 'locked'; generate = Generator()
        with adapter.using():
            ev.initialize(root, config)
            with ev._lock(root), self.assertRaises(BlockingIOError):
                ev.run_campaign(root, generate=generate)
        self.assertEqual(actor.seen, []); self.assertEqual(generate.calls, [])

    def test_changed_cursor_at_actor_boundary_stops_before_execution(self):
        _, actor, adapter, config = bind(self.root / 'fixture', sizes=(1,))
        root = self.root / 'cursor_change'; generate = Generator()
        def hook(stage):
            if stage == 'parent_runs':
                value = ev.read(root / 'state.json'); value['next_round'] = 2
                ev.save(root / 'state.json', value)
        with adapter.using():
            self.reject(ev.run_campaign, root, config=config, generate=generate, hook=hook)
        self.assertEqual(actor.seen, []); self.assertEqual(generate.calls, [])

    def test_no_change_publication_recovers_without_synthetic_replay(self):
        for branch in ('diagnosis', 'preconditioner', 'editor'):
            data, actor, adapter, config = bind(self.root / f'fixture_{branch}', sizes=(1,))
            root = self.root / f'recover_{branch}'; generate = Generator(no_change=branch)
            def hook(stage):
                if stage == 'before_publish': raise KeyboardInterrupt()
            with adapter.using(), self.assertRaises(KeyboardInterrupt):
                ev.run_campaign(root, config=config, generate=generate, hook=hook)
            with CampaignAdapter(ActorAdapter(data)).using():
                self.assertEqual(ev.run_campaign(root, resume=True)['status'], 'complete')
                count = len(memory.load_memory(root / 'memory')['memory']['rounds'])
                self.assertEqual(count, 1 if branch == 'editor' else 0)
            self.assertEqual(len(actor.seen), 1)
            self.assertEqual(generate.calls.count(branch), 1)
            self.assertNotIn('replay', generate.calls)
