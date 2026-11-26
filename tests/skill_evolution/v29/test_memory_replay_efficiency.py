"""Regression checks for lossless Replay display and single-operation reuse."""
from collections import Counter
from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v29 import memory_operation, modules, replay, output_feedback
from src.skill_evolution.v29.benchmarks.docvqa import actor, evidence, prompting, replay_input_view
from src.skill_evolution.v29.storage import read, save
from tests.skill_evolution.v29.test_method import MethodBase, main_example, user


class ReplayDisplayTests(MethodBase):
    def test_complete_responses_appear_once_and_restore_losslessly(self):
        bundle = self.chain()
        full = evidence.model_input(bundle)
        # Exercise long text, Unicode, escapes, whitespace and valid empty content.
        contents = ['  A "quoted" {value}\\path\n中文\n' * 3000, '', '\n  \t', 'unique final ordinary response']
        for run, content in zip(full['runs'], contents):
            run['attempts'][0]['assistant']['content'] = content
            run['outcome']['answer']['raw_content'] = content
        original = deepcopy(full)
        compact = replay_input_view.model_input(full)
        self.assertEqual(full, original)
        for run, content in zip(compact['runs'], contents):
            self.assertEqual(run['attempts'][0]['assistant']['content'], content)
            self.assertNotIn('raw_content', run['outcome']['answer'])
        self.assertEqual(replay_input_view.restore_model_input(compact), full)
        # Compare only removal of the response copy, holding prior sharing fixed.
        before = deepcopy(compact)
        for run, content in zip(before['runs'], contents):
            run['outcome']['answer']['raw_content'] = content
        self.assertLess(len(json.dumps(compact)), len(json.dumps(before)))

    def test_real_call_uses_compact_view_but_keeps_audit_and_outputs(self):
        bundle = self.chain(); original = deepcopy(bundle)
        call = modules.replay_call(bundle)
        self.assertEqual(call.input, original)
        self.assertEqual(replay_input_view.restore_model_input(user(call)), evidence.model_input(bundle))
        self.assertEqual(call.complete(main_example('replay'))['replay'], main_example('replay'))
        self.assertEqual(bundle, original)
        for run in call.input['payload']['runs']:
            self.assertIn('raw_content', run['outcome']['answer'])
            self.assertIn('request_messages', run['attempts'][0])

    def test_mismatched_or_missing_response_copy_is_not_silently_dropped(self):
        full = evidence.model_input(self.chain())
        for mode in ('different', 'missing'):
            bad = deepcopy(full)
            answer = bad['runs'][0]['outcome']['answer']
            if mode == 'missing': answer.pop('raw_content')
            else: answer['raw_content'] = 'different ordinary response'
            with self.assertRaises(ValueError): replay_input_view.model_input(bad)
        bad = replay_input_view.model_input(full)
        bad['runs'][0]['outcome']['answer']['raw_content'] = 'unexpected duplicate'
        with self.assertRaises(ValueError): replay_input_view.restore_model_input(bad)


class ReplayValidationReuseTests(MethodBase):
    def assert_each_batch_once(self, spy, count):
        calls = Counter(Path(c.args[0]).resolve() for c in spy.call_args_list)
        self.assertEqual(len(calls), count)
        self.assertEqual(set(calls.values()), {1})

    def test_construction_and_completion_each_validate_two_batches_once(self):
        bundle = self.chain(); original = deepcopy(bundle)
        expected_messages = prompting.replay_messages(bundle)
        before = len(self.transport.seen)
        with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
            call = modules.replay_call(bundle)
        self.assert_each_batch_once(batches, 2)
        self.assertIsNone(memory_operation.current(self.method))
        self.assertEqual(call.messages, expected_messages)
        self.assertEqual(call.input, original)
        for _ in range(2):
            with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
                result = call.complete(main_example('replay'))
            self.assert_each_batch_once(batches, 2)
            self.assertEqual(result, {'replay': main_example('replay')})
            self.assertIsNone(memory_operation.current(self.method))
        self.assertEqual(bundle, original)
        self.assertEqual(len(self.transport.seen), before)

    def test_history_is_counted_by_distinct_batches(self):
        bundle = self.chain(self.history())
        with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
            call = modules.replay_call(bundle)
        self.assert_each_batch_once(batches, 2)
        with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
            call.complete({'entries': []})
        self.assert_each_batch_once(batches, 2)
        self.assertIsNone(memory_operation.current(self.method))

    def test_archive_change_between_steps_is_rechecked_without_stale_cache(self):
        call = modules.replay_call(self.chain())
        path = self.child_dir / 'actor/0001/attempts/001/response.json'
        original = path.read_bytes(); changed = read(path)
        changed['choices'][0]['message']['content'] = 'Changed after request construction'
        save(path, changed)
        with self.assertRaises(ValueError): call.complete(main_example('replay'))
        self.assertIsNone(memory_operation.current(self.method))
        path.write_bytes(original)
        with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
            self.assertEqual(call.complete(main_example('replay')), {'replay': main_example('replay')})
        self.assert_each_batch_once(batches, 2)

    def test_exceptions_and_interruptions_release_owned_scope(self):
        bundle = self.chain()
        original = prompting.replay_messages
        def interrupted(value):
            original(value)
            raise KeyboardInterrupt()
        with patch.object(prompting, 'replay_messages', interrupted), self.assertRaises(KeyboardInterrupt):
            modules.replay_call(bundle)
        self.assertIsNone(memory_operation.current(self.method))
        call = modules.replay_call(bundle)
        with self.assertRaises(ValueError): call.complete({'entries': 'invalid'})
        self.assertIsNone(memory_operation.current(self.method))
        with patch.object(replay, 'validate_result', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            call.complete({'entries': []})
        self.assertIsNone(memory_operation.current(self.method))

    def test_nested_scope_reuses_outer_session_without_closing_it(self):
        bundle = self.chain()
        with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
            with self.method.memory_operation() as outer:
                call = modules.replay_call(bundle)
                self.assertIs(memory_operation.current(self.method), outer)
                with self.assertRaises(ValueError): call.complete({'entries': 'invalid'})
                self.assertIs(memory_operation.current(self.method), outer)
                call.complete(main_example('replay'))
                self.assertIs(memory_operation.current(self.method), outer)
            self.assert_each_batch_once(batches, 2)
        self.assertIsNone(memory_operation.current(self.method))

    def test_scope_exit_does_not_snapshot_files_or_images(self):
        bundle = self.chain()
        with self.method.memory_operation() as operation:
            modules.replay_call(bundle).complete(main_example('replay'))
            for name in ('files', 'trees', 'cases', 'watch', 'watch_file', 'verify'):
                self.assertFalse(hasattr(operation, name), name)
        self.assertIsNone(memory_operation.current(self.method))


class EvidenceConstructionReuseTests(MethodBase):
    def builders(self, bundle):
        return {
            'grouping': lambda: modules.grouping_call(self.parents, 'R02'),
            'bundle': lambda: evidence.build_replay_from_editor(
                bundle['audit']['editor'], bundle['editor_directory'], self.parents, self.children,
                memory=bundle['payload']['memory']),
        }

    def test_local_steps_validate_each_batch_once_and_preserve_outputs(self):
        bundle = self.chain(); original = deepcopy(bundle)
        before = len(self.transport.seen)
        for name, build in self.builders(bundle).items():
            with patch.object(self.method, 'memory_operation', nullcontext):
                expected = build()
            for _ in range(2):
                with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches, \
                     patch.object(actor, 'read_completed', wraps=actor.read_completed) as actors:
                    result = build()
                counts = Counter(Path(c.args[0]).resolve() for c in batches.call_args_list)
                self.assertEqual(len(counts), 1 if name == 'grouping' else 2)
                self.assertEqual(set(counts.values()), {1})
                self.assertEqual(actors.call_count, 2 if name == 'grouping' else 4)
                self.assertIsNone(memory_operation.current(self.method))
                if name == 'grouping':
                    self.assertEqual(result.input, expected.input)
                    self.assertEqual(result.messages, expected.messages)
                    self.assertEqual(result.complete(main_example('grouping')),
                                     expected.complete(main_example('grouping')))
                else:
                    self.assertEqual(result, expected)
                    self.assertEqual(result, original)
        self.assertEqual(bundle, original)
        self.assertEqual(len(self.transport.seen), before)

    def test_nested_steps_reuse_outer_scope_without_closing_it(self):
        bundle = self.chain()
        with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
            with self.method.memory_operation() as outer:
                for build in self.builders(bundle).values():
                    build()
                    self.assertIs(memory_operation.current(self.method), outer)
                self.assertEqual(batches.call_count, 2)
        self.assertIsNone(memory_operation.current(self.method))

    def test_errors_and_interruptions_release_local_scopes(self):
        bundle = self.chain()
        for name, build in self.builders(bundle).items():
            target, attr = (prompting, 'grouping_messages') if name == 'grouping' else (evidence, 'validate_payload')
            for error in (ValueError('Synthetic invalid evidence'), KeyboardInterrupt()):
                with self.subTest(step=name, error=type(error).__name__):
                    with patch.object(target, attr, side_effect=error), self.assertRaises(type(error)):
                        build()
                    self.assertIsNone(memory_operation.current(self.method))
                    build()

    def test_operation_does_not_reread_files_on_exit(self):
        bundle = self.chain()
        with self.method.memory_operation():
            for build in self.builders(bundle).values():
                build()
            # Closing a cache scope cannot trigger another disk or image scan.
            guard = patch.object(Path, 'read_bytes', side_effect=AssertionError('No exit scan'))
            guard.start()
        guard.stop()
        self.assertIsNone(memory_operation.current(self.method))


    def test_next_call_rechecks_archives_and_supplied_records(self):
        bundle = self.chain()
        for build in self.builders(bundle).values():
            build()
        path = self.parent_dir / 'actor/0001/attempts/001/response.json'
        original = path.read_bytes(); changed = read(path)
        changed['choices'][0]['message']['content'] = 'Changed archive'
        try:
            save(path, changed)
            for build in self.builders(bundle).values():
                with self.assertRaises(ValueError): build()
                self.assertIsNone(memory_operation.current(self.method))
        finally:
            path.write_bytes(original)
        with self.method.memory_operation():
            modules.grouping_call(self.parents, 'R02')
            bad = deepcopy(self.parents)
            bad[0]['execution']['content'] = 'Changed supplied record'
            with self.assertRaises(ValueError): modules.grouping_call(bad, 'R02')
            with self.assertRaises(ValueError):
                evidence.build_replay_from_editor(bundle['audit']['editor'], bundle['editor_directory'],
                                                  bad, self.children)


class MemoryReuseTests(MethodBase):
    def prepared_commit(self):
        directory = self.root / 'memory'
        first = self.chain()
        self.method.commit_memory(directory, context_id='R1', context=first, result=main_example('replay'))
        active = self.method.load_memory(directory)
        second = self.chain(active)
        return directory, second

    def test_one_history_traversal_and_each_batch_validated_once_per_commit(self):
        directory, bundle = self.prepared_commit()
        model_calls = len(self.transport.seen)
        with patch.object(memory, '_archive', wraps=memory._archive) as history, \
             patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches, \
             patch.object(actor, 'read_completed', wraps=actor.read_completed) as completed:
            self.method.commit_memory(directory, context_id='R2', context=bundle, result={'entries': []})
        self.assertEqual(history.call_count, 0)
        counts = Counter(Path(c.args[0]).resolve() for c in batches.call_args_list)
        self.assertEqual(len(counts), 2)  # Only current Parent/Candidate batches.
        self.assertEqual(set(counts.values()), {1})
        self.assertEqual(completed.call_count, 4)  # Current executions only.
        self.assertEqual(len(self.transport.seen), model_calls)
        self.assertIsNone(memory_operation.current(self.method))

    def test_reuse_does_not_survive_a_new_call(self):
        directory, bundle = self.prepared_commit()
        for _ in range(2):
            with patch.object(memory, '_archive', wraps=memory._archive) as history, \
                 patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
                view = self.method.load_memory(directory)
            self.assertEqual(history.call_count, 0)
            self.assertEqual(batches.call_count, 0)
            view['entries'].clear()
        self.assertTrue(self.method.load_memory(directory)['entries'])
        path = directory / 'archive/R1.json'; changed = read(path)
        changed['after_active_ids'] = []
        save(path, changed)
        with self.assertRaises(ValueError): self.method.commit_memory(directory, context_id='R2', context=bundle, result={'entries': []})
        self.assertEqual(read(directory / 'active.json')['commits'], ['R1'])
        self.assertIsNone(memory_operation.current(self.method))

    def test_bytes_and_whole_entry_revisions_match_inherited_committer(self):
        directory = self.root / 'memory'; reference = self.root / 'reference'
        active = memory.empty_memory()
        for index in range(1, 4):
            bundle = self.chain(active)
            result = main_example('replay') if index < 3 else {'entries': []}
            if index == 2: result['entries'][0]['revises'] = ['M1']
            cid = f'R{index}'
            expected = memory.commit_memory(reference, context_id=cid, context=bundle, result=result,
                                            memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
            with patch.object(memory, '_archive', wraps=memory._archive) as history:
                actual = self.method.commit_memory(directory, context_id=cid, context=bundle, result=result)
            self.assertEqual(history.call_count, 0)
            self.assertEqual(actual, expected)
            for name in ('active.json', f'archive/{cid}.json'):
                self.assertEqual((directory / name).read_bytes(), (reference / name).read_bytes())
            active = self.method.load_memory(directory)
            self.assertEqual(active, memory.load_memory(reference, memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT))
        self.assertEqual([e['id'] for e in active['entries']], ['M2'])

    def test_active_index_change_is_rejected_before_publication(self):
        directory, bundle = self.prepared_commit()
        original = memory._view
        def changed_view(entries, contexts, active, contract):
            value = original(entries, contexts, active, contract)
            if 'R2' in contexts:
                save(directory / 'active.json', {'commits': [], 'active_ids': []})
            return value
        with patch.object(memory, '_view', changed_view), self.assertRaises(ValueError):
            self.method.commit_memory(directory, context_id='R2', context=bundle, result={'entries': []})
        self.assertFalse((directory / 'archive/R2.json').exists())
        self.assertIsNone(memory_operation.current(self.method))


    def test_batch_snapshot_returns_detached_records_and_rejects_changed_input(self):
        self.parent()
        with memory_operation.operation(self.method) as session:
            records = self.method.read_batch(self.parent_dir)
            records[0]['execution']['content'] = 'caller mutation'
            self.assertEqual(self.method.read_batch(self.parent_dir), self.parents)
            with self.assertRaises(ValueError): self.method.validate_record(records[0])
        self.assertIsNone(memory_operation.current(self.method))

    def test_pending_and_partial_write_recovery_keeps_inherited_rules(self):
        bundle = self.chain(); result = main_example('replay')
        reference = self.root / 'reference'
        expected = memory.commit_memory(reference, context_id='R1', context=bundle, result=result,
                                        memory_contract=memory.MULTI_KNOWLEDGE_CONTRACT)
        for mode in ('pending', 'temp', 'bad_pending', 'foreign_pending'):
            with self.subTest(mode=mode):
                directory = self.root / mode; (directory / 'archive').mkdir(parents=True)
                if mode == 'temp': (directory / 'archive/R1.tmp').write_text('partial')
                else:
                    proposal = deepcopy(expected)
                    if mode == 'bad_pending': proposal['after_active_ids'] = ['M999']
                    save(directory / 'archive' / ('foreign.json' if mode == 'foreign_pending' else 'R1.json'), proposal)
                if mode in ('bad_pending', 'foreign_pending'):
                    with self.assertRaises(ValueError):
                        self.method.commit_memory(directory, context_id='R1', context=bundle, result=result)
                    self.assertFalse((directory / 'active.json').exists())
                else:
                    self.assertEqual(self.method.commit_memory(directory, context_id='R1', context=bundle, result=result), expected)
        self.assertIsNone(memory_operation.current(self.method))

    def test_interrupt_after_active_write_discards_cache_and_recovers_idempotently(self):
        bundle = self.chain(); directory = self.root / 'memory'; result = main_example('replay')
        original = memory.write_record
        def interrupted(path, value):
            original(path, value)
            if path.name == 'active.json': raise KeyboardInterrupt()
        with patch.object(memory, 'write_record', interrupted), self.assertRaises(KeyboardInterrupt):
            self.method.commit_memory(directory, context_id='R1', context=bundle, result=result)
        self.assertIsNone(memory_operation.current(self.method))
        self.assertEqual(read(directory / 'active.json')['commits'], ['R1'])
        expected = read(directory / 'archive/R1.json')
        self.assertEqual(self.method.commit_memory(directory, context_id='R1', context=bundle, result=result), expected)
        self.assertEqual(read(directory / 'active.json')['commits'], ['R1'])

