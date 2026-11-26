from copy import deepcopy
from dataclasses import replace
import difflib
import json
from pathlib import Path
import tempfile
import unittest

import httpx
from openai import OpenAI
from skilladam.execution.contracts import BatchExecution, GenerationRequest, GenerationResult, ToolCall
from skilladam.execution.evaluate import CaseEvaluation
from skilladam.types import MetricResult
from src.adapters.searchqa import skilladam as m
from tests.skill_evolution.v28.runtime_support import Dataset, HIDDEN, Transport, response

SKILL = "## Strategy\nUse the supplied passages.\n"


class SyntheticDataset(Dataset):
    def __init__(self, root, count=15):
        super().__init__(count)
        self.root = root
        self.splits = {'train': list(self.rows), 'test': ['synthetic:test']}
        self.rows['synthetic:test'] = {'question': 'Test question', 'context': 'Test context',
                                     'answers': ['New York City'], 'source_split': 'test'}


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.production, cls.initial, cls.native, cls.context, cls.snapshot = m.prepare()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dataset = SyntheticDataset(self.root)
        self.adapter = m.NativeAdapter(self.root)

    def requests(self, cases=None):
        return tuple(self.adapter.build_rollout_request(c, method='skilladam', split='train',
            skill=SKILL, seed=42) for c in (cases or m.native_cases(self.dataset)))

    def backend(self, transport=None, generation=None):
        result = m.Backend(self.dataset, transport or Transport(), generation, self.context,
                            self.root / 'rollouts', {'fixture': True})
        result.stage_directory = result.output_dir / 'iter_001' / 'training'
        return result

    def test_shared_prompt_for_all_2000_cases(self):
        for split in ('train', 'test'):
            for case in m.native_cases(self.production, split):
                request = self.adapter.build_rollout_request(case, method='skilladam', split=split,
                                                             skill=self.initial, seed=42)
                self.assertEqual(list(request.metadata['messages']), m.p.messages(case.payload, self.initial))
                self.assertEqual(request.case.reference, case.reference)

    def test_native_profile_and_schedule(self):
        upstream = m.read(m.ROOT / 'external/SkillAdam/skilladam/experiments/main_results.json')['benchmarks']['searchqa']['skilladam']
        for field in ('seed', 'prompt_profile', 'trajectory_compression', 'optimizer_context_limit',
                      'sampling_strategy', 'shuffle_optimization_pool', 'include_partial_final_batch'):
            self.assertEqual(getattr(self.native, field), upstream[field])
        self.assertEqual(self.native.train_size, upstream['batch_size'])
        for field in ('max_iterations', 'min_iterations', 'max_consecutive_failures'):
            self.assertEqual(getattr(self.native.feedback_loop, field), upstream[field])
        budget = self.native.feedback_loop.edit_budget
        for field in ('base', 'minimum', 'beta', 'v_max'):
            self.assertEqual(getattr(budget, field), upstream['adaptive_edit_budget'][field])
        self.assertEqual(budget.metric_key, upstream['adaptive_edit_budget']['metric'])
        self.assertEqual([len(b) for b in self.snapshot['batches']], [15]*40)
        self.assertEqual(len(self.production.splits['test']), 1400)
        self.assertFalse(set(self.production.splits['train']) & set(self.production.splits['test']))
        self.assertEqual(self.initial, (m.ROOT / self.cfg['initial_skill']).read_text())

    def test_content_only_score_usage_and_archive_recovery(self):
        transport = Transport()
        backend = self.backend(transport)
        execution = BatchExecution(self.requests(), self.context, 'training_rollout')
        raw = backend.execute_batch(execution)
        self.assertEqual(transport.calls, 15)
        for case, item in zip(m.native_cases(self.dataset), raw):
            self.assertNotIn(HIDDEN, repr(item.result))
            parsed = self.adapter.parse_result(case, item.result)
            self.assertEqual(self.adapter.evaluate(parsed).primary, 1)
            self.assertEqual(parsed.usage[0].requests, 1)
            self.assertEqual(parsed.usage[0].reasoning_tokens, 5)
        backend.execute_batch(execution)
        self.assertEqual(transport.calls, 15)
        # A corrupted completed task cannot trigger new calls for any task.
        result = next(backend.stage_directory.glob('actor/actor/*/result.json'))
        result.unlink()
        with self.assertRaises(ValueError):
            backend.execute_batch(execution)
        self.assertEqual(transport.calls, 15)

    def test_only_batch60_adds_full_evidence_after_native_compression(self):
        case = self.dataset.case(self.dataset.splits['train'][0])
        case = replace(case, payload={**case.payload, 'context': 'A "clue"\n' * 600 + '末尾'},
                       reference=['NYC', 'New York City'])
        parsed = self.adapter.parse_result(case, {'response': '<answer>Berlin</answer>',
                                                 'messages': m.p.messages(case.payload, SKILL)})
        evaluated = CaseEvaluation(case.case_id, parsed, self.adapter.evaluate(parsed))
        for size in (15, 30, 60):
            runner = m.Runner(config=replace(self.native, train_size=size, validation_size=size), adapter=self.adapter,
                              backend=None, context=self.context, output_dir=self.root / 'unused')
            original = m.SkillAdamRunner._condense(runner, case, evaluated, allow_llm=True)
            actual = runner._condense(case, evaluated, allow_llm=True)
            if size == 60:
                trace, evidence = actual.markdown.rsplit('\n\n## Training evidence\n\n', 1)
                self.assertEqual(trace, original.markdown)
                self.assertEqual(json.loads(evidence), {'initial': {'task': {'context': case.payload['context']}},
                                                        'outcome': {'reference_answers': case.reference}})
                with self.assertRaisesRegex(ValueError, 'training case'):
                    runner._condense(self.dataset.case('synthetic:test'), evaluated, allow_llm=True)
            else:
                self.assertEqual(actual, original)

    def test_partial_batch_resumes_only_pending(self):
        missing = m.p.digest(self.dataset.splits['train'][-1])
        def interrupted(messages, directory):
            if missing in str(directory):
                raise RuntimeError('Synthetic interruption before response')
            return response()
        transport = Transport(fn=interrupted)
        backend = self.backend(transport)
        execution = BatchExecution(self.requests(), self.context, 'training_rollout')
        with self.assertRaises(RuntimeError):
            backend.execute_batch(execution)
        transport.fn = None
        from unittest.mock import patch
        with patch('src.skill_evolution.v28.benchmarks.searchqa.actor.time.sleep'):
            backend.execute_batch(execution)
        self.assertEqual(transport.calls, 16)

    def test_invalid_stop_answer_not_resampled(self):
        for index, (content, finish) in enumerate((('invalid', 'stop'), ('', 'stop'))):
            with self.subTest(finish=finish):
                transport = Transport(fn=lambda messages, directory: response(content, finish))
                backend = self.backend(transport)
                backend.stage_directory = backend.output_dir / f'iter_{index:03d}' / 'training'
                request = self.requests()[:1]
                raw = backend.execute_batch(BatchExecution(request, self.context, 'training_rollout'))
                self.assertEqual(self.adapter.evaluate(self.adapter.parse_result(request[0].case, raw[0].result)).primary, 0)
                self.assertEqual(transport.calls, 1)

    def test_shared_actor_length_retry_and_cached_resume(self):
        from unittest.mock import patch
        transport = Transport(fn=lambda m, d: response(None, 'length') if d.name == '001' else response())
        backend = self.backend(transport)
        execution = BatchExecution(self.requests()[:1], self.context, 'training_rollout')
        with patch('src.skill_evolution.v28.benchmarks.searchqa.actor.time.sleep'):
            result = backend.execute_batch(execution)
        self.assertEqual(transport.calls, 2)
        self.assertEqual(backend.execute_batch(execution), result)
        self.assertEqual(transport.calls, 2)
        backend.recovery.validate()
        # Corrupt the accepted response: preflight must fail without issuing another request.
        accepted = next(backend.output_dir.rglob('attempts/002/response.json'))
        accepted.unlink()
        with self.assertRaises(ValueError):
            backend.recovery.validate()
        self.assertEqual(transport.calls, 2)

    def test_shared_actor_length_exhaustion_never_completes_rollout(self):
        from unittest.mock import patch
        from src.skill_evolution.v27.transport import RequestFailure
        transport = Transport(fn=lambda m, d: response('<answer>A</answer>', 'length'))
        backend = self.backend(transport)
        execution = BatchExecution(self.requests()[:1], self.context, 'training_rollout')
        with patch('src.skill_evolution.v28.benchmarks.searchqa.actor.time.sleep'):
            for _ in range(2):
                with self.assertRaises(RequestFailure):
                    backend.execute_batch(execution)
                self.assertEqual(transport.calls, 6)
        self.assertTrue(all(entry['completion'] is None for entry in backend.recovery.index('rollouts').values()))
        self.assertFalse(list(backend.output_dir.rglob('result.json')))

    def test_test_set_and_prompt_drift_rejected_before_actor(self):
        transport = Transport()
        backend = self.backend(transport)
        request = self.requests()[0]
        for changed in (replace(request, split='test'),
                        replace(request, metadata={**request.metadata, 'messages': []})):
            with self.assertRaises(ValueError):
                backend.execute_batch(BatchExecution((changed,), self.context, 'training_rollout'))
        self.assertEqual(transport.calls, 0)

    def test_f1_mapping_and_fixed_skill_test_are_isolated(self):
        from src.skill_evolution.v28.evaluation import run_evaluation
        from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
        transport = Transport(fn=lambda messages, directory: response('New York'))
        backend = self.backend(transport)
        request = self.requests()[0]
        raw = backend.execute_batch(BatchExecution((request,), self.context, 'training_rollout'))[0]
        score = self.adapter.evaluate(self.adapter.parse_result(request.case, raw.result))
        self.assertEqual(score.metrics, {'exact_match': 0, 'token_f1': .8})
        skill = self.root / 'fixed.md'
        skill.write_text(SKILL)
        # The synthetic data root must be separate from the evaluation output.
        self.dataset.root = self.root / 'dataset'
        actor = SearchQAActorAdapter(self.dataset, transport)
        self.assertEqual((actor.workers, actor.test_workers), (15, 15))
        result = run_evaluation(self.root / 'test', adapter=actor, skill_file=skill)
        self.assertFalse(result['optimization_updates'])
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['total'], 1)
        self.assertEqual(transport.calls, 2)
        self.assertEqual(result, run_evaluation(self.root / 'test', adapter=actor, skill_file=skill, resume=True))
        self.assertEqual(transport.calls, 2)

    def test_native_dual_metric_gate_main_result_not_v28(self):
        from skilladam.methods.skilladam import _profile_gate
        gate = _profile_gate(self.adapter, 'searchqa', None, 'main-result')
        def metric(em, f1):
            return MetricResult(primary=em, metrics={'exact_match': em, 'token_f1': f1}, sample_count=15)
        baseline = metric(.4, .6)
        self.assertTrue(gate.judge(baseline, metric(.4, .625)).accepted)  # EM tie, F1 gain.
        self.assertFalse(gate.judge(baseline, metric(.4 + 1/15, .55)).accepted)  # EM up, F1 drop boundary.
        self.assertTrue(gate.judge(baseline, metric(.4 + 1/15, .6)).accepted)
        self.assertFalse(gate.judge(baseline, baseline).accepted)

    def test_native_generation_payload_and_tools_with_mock_http(self):
        bodies = []
        def handler(request):
            bodies.append(json.loads(request.content))
            self.assertEqual(str(request.url), 'https://api.deepseek.com/chat/completions')
            raw = response('ordinary optimizer output')
            if 'tools' in bodies[-1]:
                raw['choices'][0]['message'].update(content=None, tool_calls=[{
                    'id': 'synthetic_call', 'type': 'function',
                    'function': {'name': 'synthetic_tool', 'arguments': '{"value":1}'}}])
                raw['choices'][0]['finish_reason'] = 'tool_calls'
            return httpx.Response(200, json=raw)
        def factory(**kwargs):
            self.assertEqual(kwargs['max_retries'], 2)
            self.assertEqual(kwargs['timeout'], 600)
            client = OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
            self.addCleanup(client.close)
            return client
        generation = m.generation_transport(self.cfg, self.dataset, self.context, self.root,
            environ={'OPENAI_API_KEY': 'synthetic', 'OPENAI_BASE_URL': 'https://api.deepseek.com'}, client_factory=factory)
        request = GenerationRequest('iteration_patch', ({'role': 'user', 'content': 'fixture'},), self.context, {})
        self.assertEqual(generation.generate(request).text, 'ordinary optimizer output')
        tool = {'type': 'function', 'function': {'name': 'synthetic_tool', 'description': 'fixture',
                'parameters': {'type': 'object', 'properties': {'value': {'type': 'integer'}}}}}
        result = generation.generate(replace(request, stage='momentum_update', metadata={'tools': [tool]}))
        self.assertEqual(result.tool_calls[0].arguments['value'], 1)
        for body in bodies:
            self.assertEqual(body['max_tokens'], 16384)
            self.assertEqual(self.cfg['actor']['max_tokens'], 49152)
            for key in ('model', 'temperature', 'reasoning_effort', 'thinking'):
                self.assertEqual(body[key], self.cfg['actor'][key])
        self.assertNotIn(HIDDEN, repr(result))

    def test_actor_budget_increase_does_not_change_native_optimizer(self):
        self.assertEqual(self.cfg['actor']['max_tokens'], 49152)
        self.assertEqual(self.cfg['actor']['request_attempts_total'], 6)
        self.assertEqual(self.cfg['actor']['sdk_retries'], 0)
        self.assertEqual(self.cfg['native']['feedback_loop']['patch_attempts'], 3)
        changed = deepcopy(self.cfg)
        changed['optimizer']['backend_config']['max_completion_tokens'] = 49152
        path = self.root/'invalid_optimizer_budget.json'
        path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'Frozen optimizer transport settings differ'):
            m.prepare(path)

    def test_native_full_iteration_and_completed_resume(self):
        self._full_iteration('Berlin', 'New York City', accepted=True)

    def test_native_runner_accepts_f1_only_gain(self):
        self._full_iteration('New', 'New York', accepted=True)

    def test_native_runner_retains_tie_and_updates_momentum(self):
        self._full_iteration('Berlin', 'Berlin', accepted=False)

    def _full_iteration(self, before, after, *, accepted):
        candidate = SKILL + 'Check answer boundaries.\n'
        patch = ''.join(difflib.unified_diff(SKILL.splitlines(True), candidate.splitlines(True),
                                            fromfile='a/SKILL.md', tofile='b/SKILL.md'))
        requests = []
        class Generation:
            def generate(inner, request):
                requests.append(request)
                if request.stage == 'iteration_patch':
                    return GenerationResult(json.dumps({'reasoning': 'Synthetic regression check.', 'patch': patch}))
                if request.stage == 'momentum_update':
                    return GenerationResult('', tool_calls=(ToolCall('report_problem', {
                        'label': 'synthetic-condition', 'description': 'Synthetic condition check.',
                        'evidence': 'Synthetic fixture only.', 'failure_type': 'rule_missing',
                        'inherited_from_iteration': True}),))
                raise AssertionError(request.stage)
        transport = Transport(fn=lambda messages, directory: response(
            after if 'validation_candidate' in str(directory) else before))
        backend = self.backend(transport, Generation())
        native = replace(self.native, optimization_case_ids=tuple(self.dataset.splits['train']),
            feedback_loop=replace(self.native.feedback_loop, max_iterations=1, min_iterations=1))
        def runner():
            return m.Runner(config=native, adapter=self.adapter, backend=backend,
                            context=self.context, output_dir=self.root / 'native')
        result = runner().run(cases=m.native_cases(self.dataset), initial_skill=SKILL)
        expected = candidate if accepted else SKILL
        self.assertEqual(result.final_skill, expected)
        self.assertIsNone(result.stage0)
        self.assertIn('synthetic-condition', result.momentum.problems)
        self.assertEqual(transport.calls, 45)  # Native training + Gate parent + Gate candidate.
        self.assertEqual([r.stage for r in requests], ['iteration_patch', 'momentum_update'])
        # Inspect both actual optimizer requests, not only the context object.
        base_protocol = m.p.messages(self.dataset.case(self.dataset.splits['train'][0]).payload, '')[0]['content'].strip()
        from skilladam.benchmarks.searchqa.rollout import SKILLADAM_SYSTEM_PROMPT
        upstream_protocol = SKILLADAM_SYSTEM_PROMPT.format(skill_section='').strip()
        for request in requests:
            system = request.messages[0]['content']
            self.assertEqual(request.messages[0]['role'], 'system')
            self.assertEqual(system.count(f'```\n{base_protocol}\n```'), 1)
            self.assertNotIn(upstream_protocol, system)
        self.assertNotIn(HIDDEN, repr(requests))
        self.assertEqual(runner().run(cases=m.native_cases(self.dataset), initial_skill=SKILL, resume=True).final_skill, expected)
        self.assertEqual(transport.calls, 45)
        self.assertEqual(len(requests), 2)
