"""Per-module preparation/completion use separate short-lived batch caches."""
from collections import Counter
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v29 import memory_operation, modules, output_feedback
from src.skill_evolution.v29.benchmarks.docvqa import actor
from .test_method import MethodBase, main_example


class ModuleValidationReuseTests(MethodBase):
    def setUp(self):
        super().setUp()
        self.parent()
        self.prepare_inputs(memory.empty_memory())

    def prepare_inputs(self, active):
        self.active = active
        self.grouped = modules.grouping_call(self.parents, 'R02').complete(main_example('grouping'))
        self.diagnosed = modules.diagnosis_call(self.grouped).complete(main_example('diagnosis'))
        self.prepared = modules.preconditioner_call(self.diagnosed, active).complete(main_example('preconditioner'))
        self.builders = {
            'grouping': lambda: modules.grouping_call(self.parents, 'R02'),
            'diagnosis': lambda: modules.diagnosis_call(self.grouped),
            'preconditioner': lambda: modules.preconditioner_call(self.diagnosed, self.active),
            'editor': lambda: modules.editor_call(self.prepared),
        }

    def assert_batches_once(self, spy, count):
        counts = Counter(Path(call.args[0]).resolve() for call in spy.call_args_list)
        self.assertEqual(len(counts), count)
        self.assertEqual(set(counts.values()), {1})

    def test_each_local_entry_checks_one_batch_and_preserves_inputs_and_outputs(self):
        before = deepcopy((self.parents, self.grouped, self.diagnosed, self.prepared))
        model_calls = len(self.transport.seen)
        for name, build in self.builders.items():
            with self.subTest(module=name):
                with patch.object(self.method, 'memory_operation', side_effect=lambda: nullcontext()):
                    baseline = build()
                    expected = baseline.complete(main_example(name))
                for _ in range(2):
                    with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches, \
                         patch.object(actor, 'read_completed', wraps=actor.read_completed) as actors:
                        call = build()
                    self.assert_batches_once(batches, 1)
                    self.assertEqual(actors.call_count, 2)
                    self.assertIsNone(memory_operation.current(self.method))
                    self.assertEqual(call.messages, baseline.messages)
                    self.assertEqual(call.input, baseline.input)
                    # Completion must validate afresh, including repeated calls.
                    for _ in range(2):
                        with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
                            self.assertEqual(call.complete(main_example(name)), expected)
                        self.assert_batches_once(batches, 1)
                        self.assertIsNone(memory_operation.current(self.method))
        self.assertEqual((self.parents, self.grouped, self.diagnosed, self.prepared), before)
        self.assertEqual(len(self.transport.seen), model_calls)

    def test_history_reuse_is_per_distinct_batch(self):
        self.prepare_inputs(self.history())
        for name in ('preconditioner', 'editor'):
            with self.subTest(module=name):
                with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
                    call = self.builders[name]()
                self.assert_batches_once(batches, 1)
                with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
                    call.complete(main_example(name))
                self.assert_batches_once(batches, 1)
                self.assertIsNone(memory_operation.current(self.method))

    def test_changed_archive_between_steps_is_not_trusted(self):
        path = self.parent_dir / 'actor/0001/attempts/001/response.json'
        original = path.read_bytes()
        for name, build in self.builders.items():
            with self.subTest(module=name):
                call = build()
                try:
                    path.write_text('{}')
                    with self.assertRaises((ValueError, KeyError)):
                        call.complete(main_example(name))
                    self.assertIsNone(memory_operation.current(self.method))
                finally:
                    path.write_bytes(original)
                with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
                    call.complete(main_example(name))
                self.assert_batches_once(batches, 1)

    def test_nested_calls_keep_the_outer_scope(self):
        with patch.object(self.adapter, 'read_batch', wraps=self.adapter.read_batch) as batches:
            with self.method.memory_operation() as outer:
                for name, build in self.builders.items():
                    call = build()
                    call.complete(main_example(name))
                    self.assertIs(memory_operation.current(self.method), outer)
            self.assert_batches_once(batches, 1)
        self.assertIsNone(memory_operation.current(self.method))

    def test_local_validation_failures_release_scopes_and_remain_technical(self):
        path = self.parent_dir / 'actor/0001/attempts/001/response.json'
        original = path.read_bytes()
        read_batch = self.adapter.read_batch
        for name, build in self.builders.items():
            call = build()
            actions = (build, lambda: output_feedback.output_call(
                name + ' output', call.complete, main_example(name)))
            for action in actions:
                for failure in (ValueError, KeyboardInterrupt):
                    with self.subTest(module=name, action=action, failure=failure):
                        def after_validation(*args, **kwargs):
                            result = read_batch(*args, **kwargs)
                            raise failure('interrupted local validation')
                        try:
                            error = failure
                            with patch.object(self.adapter, 'read_batch', side_effect=after_validation), \
                                 self.assertRaises(error) as caught:
                                action()
                            self.assertNotIsInstance(caught.exception, output_feedback.OutputValidationError)
                            self.assertIsNone(memory_operation.current(self.method))
                        finally:
                            path.write_bytes(original)
