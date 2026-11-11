"""Offline bridge integration tests: native gate, condenser, and checkpoint."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/runs'))
import run_skilladam_aligned as app
from skilladam.core.trajectory_condenser import condense_trajectory_md
from skilladam.core.feedback_loop import ResumeMismatchError
from skilladam.execution.contracts import GenerationRequest, GenerationResult, RawRollout
from skilladam.types import MetricResult


class SkillAdamBridgeTests(unittest.TestCase):
    def test_default_is_offline_and_exact_batch_plan(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
             patch.object(app, 'configure_runtime', side_effect=AssertionError('credentials forbidden')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(app.main([]), 0)
            self.assertEqual(app.main(['smoke']), 0)
            self.assertEqual(app.main(['formal']), 0)
        self.assertEqual(app.check()['batch_sizes'], [10, 10, 10, 10, 10, 7])

    def test_native_gate_accepts_tie_and_improvement_rejects_regression(self):
        def metric(values):
            return MetricResult(sum(values)/len(values), {'hard': sum(values)/len(values)},
                                {str(i): {'hard': v} for i, v in enumerate(values)}, len(values))
        gate = app.ALFWorldAdapter(app.EXPERIMENT / 'splits')
        baseline = metric([1, 0])
        self.assertTrue(gate.gate(baseline, metric([1, 0])).accepted)
        self.assertTrue(gate.gate(baseline, metric([1, 1])).accepted)
        self.assertFalse(gate.gate(baseline, metric([0, 0])).accepted)
        with self.assertRaises(ValueError):
            gate.gate(baseline, metric([1]))

    def test_conversion_preserves_actions_feedback_and_unknown_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'trace.json'
            app.write(path, {'goal': 'put apple on table', 'initial_observation': 'a room',
                             'steps': [{'phase': 'executed', 'step': 1, 'action': 'take apple 1 from table 1',
                                        'observation': 'Nothing happens.', 'reward': 0, 'done': False,
                                        'transport_attempts': [{'usage': None}, {'usage': {
                                            'prompt_tokens': 20, 'completion_tokens': 3, 'total_tokens': 23}}]}]})
            raw = app.convert_record({'id': 'train:0000', 'trajectory': str(path), 'hard': 0,
                                      'soft': 0, 'n_turns': 1, 'task_description': 'put apple on table'})
            case = app.cases_for(app.configuration('smoke'))[0]
            parsed = app.ALFWorldAdapter(app.EXPERIMENT / 'splits').parse_result(case, raw)
            self.assertEqual(len(parsed.usage), 2)
            self.assertIsNone(parsed.usage[0].input_tokens)
            self.assertEqual(parsed.usage[1].input_tokens, 20)
            self.assertEqual(parsed.output, 'take apple 1 from table 1')
            markdown = condense_trajectory_md(messages=list(parsed.trajectory), outcome_label='failure')
            self.assertIn('take apple 1 from table 1', markdown)
            self.assertIn('Nothing happens.', markdown)
            self.assertIn('put apple on table', markdown)
            self.assertNotIn('**Reasoning:**', markdown)

    def test_transport_archives_truncation_then_reuses_completed_generation(self):
        actor = app.read(app.EXPERIMENT / 'actor.json')
        cfg = app.configuration('smoke')
        calls = []
        def create(**payload):
            calls.append(payload)
            raw = {'choices': [{'finish_reason': 'length' if len(calls) == 1 else 'stop',
                                'message': {'content': 'valid text', 'tool_calls': None}}],
                   'usage': {'prompt_tokens': 5, 'completion_tokens': 7, 'total_tokens': 12}}
            return SimpleNamespace(model_dump=lambda **kw: raw)
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        context = app.BackendContext('alfworld', 'skilladam', actor['model'], 'medium', 8, 42)
        request = GenerationRequest('trajectory_compression', ({'role': 'user', 'content': 'trace'},), context, {})
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            backend = app.SharedBackend(actor, cfg, tmp, client=client)
            result = backend.generate(request)
            self.assertEqual(len(calls), 2)
            self.assertEqual(sum(u.requests for u in result.usage), 2)
            backend.generate(request)
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0]['max_tokens'], 16384)
            self.assertEqual(calls[0]['extra_body'], {'thinking': {'type': 'enabled'}})
            self.assertEqual(calls[0]['reasoning_effort'], 'medium')

    def test_native_gate_checkpoint_resume_skips_completed_rollouts(self):
        class FakeBackend:
            iteration = 0
            def __init__(self, pause):
                self.pause, self.rollouts, self.stages = pause, 0, []
            def execute_batch(self, execution):
                self.rollouts += 1
                return tuple(RawRollout(r.case.case_id, {'hard': 1, 'soft': 1, 'n_turns': 1,
                    'task_description': 'put apple on table', 'conversation': [
                        {'role': 'assistant', 'content': '', 'action': 'look'},
                        {'role': 'tool', 'content': 'Task complete', 'action': 'look'}]}) for r in execution.requests)
            def generate(self, request):
                self.stages.append(request.stage)
                if request.stage == 'momentum_update' and self.pause:
                    raise app.SmokePause()
                if request.stage == 'iteration_patch':
                    return GenerationResult(json.dumps({'reasoning': 'test patch',
                        'patch': '--- a/skill.md\n+++ b/skill.md\n@@ -1 +1 @@\n-Original\n+Updated\n'}))
                return GenerationResult('No additional issues.')
        cfg = app.configuration('smoke')
        context = app.BackendContext('alfworld', 'skilladam', 'fake', 'medium', 8, 42)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'run'
            backend = FakeBackend(True)
            def runner(b):
                return app.AlignedRunner(config=app.native_config(cfg), adapter=app.ALFWorldAdapter(app.EXPERIMENT / 'splits'),
                                         backend=b, context=context, output_dir=output)
            with self.assertRaises(app.SmokePause):
                runner(backend).run(cases=app.cases_for(cfg), initial_skill='Original\n')
            checkpoint = app.read(output / 'checkpoint.json')
            self.assertTrue(checkpoint['iterations'][0]['accepted'])
            self.assertEqual(checkpoint['next_iteration'], 1)
            self.assertIsNotNone(checkpoint['pending_post_decision'])
            self.assertEqual(backend.rollouts, 3)
            resumed = FakeBackend(False)
            result = runner(resumed).run(cases=app.cases_for(cfg), initial_skill='Original\n', resume=True)
            self.assertEqual(resumed.rollouts, 0)
            self.assertEqual(resumed.stages, ['momentum_update'])
            self.assertEqual(result.final_skill, 'Updated\n')
            self.assertIsNone(app.read(output / 'checkpoint.json')['pending_post_decision'])
            with self.assertRaises(ResumeMismatchError):
                runner(FakeBackend(False)).run(cases=app.cases_for(cfg), initial_skill='Changed\n', resume=True)


if __name__ == '__main__':
    unittest.main()
