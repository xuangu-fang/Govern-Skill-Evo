"""Local request preparation reuses archives without changing module inputs."""
from contextlib import nullcontext
from copy import deepcopy
import unittest
from unittest.mock import patch

from src.skill_evolution.v27.contracts import memory
from src.skill_evolution.v28 import modules, validation
from src.skill_evolution.v28.benchmarks.searchqa import actor, prompting, protocol
from . import test_method as support


class ModuleValidationReuseTests(unittest.TestCase):
    def setUp(self):
        self.fixture = support.MethodTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.diagnosed = self.fixture.diagnosed()
        self.grouped = self.fixture.calls[1].input
        self.prepared = modules.preconditioner_call(
            self.diagnosed, memory.empty_memory()).complete(support.keep())
        self.builders = {
            'diagnosis': lambda: modules.diagnosis_call(self.grouped),
            'preconditioner': lambda: modules.preconditioner_call(self.diagnosed, memory.empty_memory()),
            'editor': lambda: modules.editor_call(self.prepared),
        }
        self.outputs = {
            'diagnosis': support.diagnosis(), 'preconditioner': support.keep(),
            'editor': {'patch': support.unnumbered(support.SKILL, self.fixture.candidate_text),
                       'reason': 'Implement the entity checks.'},
        }

    def test_each_preparation_checks_each_execution_and_batch_once(self):
        before = deepcopy((self.grouped, self.diagnosed, self.prepared))
        model_calls = self.fixture.transport.calls
        for name, build in self.builders.items():
            with self.subTest(module=name):
                with patch.object(validation, 'operation', side_effect=lambda _: nullcontext()):
                    baseline = build()
                    expected = baseline.complete(self.outputs[name])
                for _ in range(2):
                    with patch.object(actor, 'read_completed', wraps=actor.read_completed) as actors, \
                         patch.object(self.fixture.adapter, '_signature',
                                      wraps=self.fixture.adapter._signature) as batches:
                        call = build()
                    self.assertEqual((actors.call_count, batches.call_count), (2, 1))
                    self.assertIsNone(validation.current())
                    self.assertEqual(call.messages, baseline.messages)
                    self.assertEqual(call.input, baseline.input)
                    self.assertEqual(call.complete(self.outputs[name]), expected)
        self.assertEqual((self.grouped, self.diagnosed, self.prepared), before)
        self.assertEqual(self.fixture.transport.calls, model_calls)

    def test_preparation_exit_checks_files_and_releases_scope_on_errors(self):
        path = self.fixture.parent_dir / 'actor' / protocol.digest(self.fixture.tasks[0]) / 'attempts/001/response.json'
        original = path.read_bytes()
        for name, build in self.builders.items():
            render = getattr(prompting, name + '_messages')
            for failure in ('mutation', ValueError, KeyboardInterrupt):
                with self.subTest(module=name, failure=failure):
                    def after_validation(*args, **kwargs):
                        result = render(*args, **kwargs)
                        if failure == 'mutation':
                            path.write_bytes(original + b' ')
                            return result
                        raise failure('interrupted local preparation')
                    try:
                        error = ValueError if failure == 'mutation' else failure
                        with patch.object(prompting, name + '_messages', side_effect=after_validation), \
                             self.assertRaises(error):
                            build()
                        self.assertIsNone(validation.current())
                    finally:
                        path.write_bytes(original)

    def test_nested_preparations_keep_the_outer_scope(self):
        with patch.object(actor, 'read_completed', wraps=actor.read_completed) as actors:
            with validation.operation(self.fixture.adapter) as outer:
                for build in self.builders.values():
                    build()
                    self.assertIs(validation.current(self.fixture.adapter), outer)
            self.assertEqual(actors.call_count, 2)
        self.assertIsNone(validation.current())
