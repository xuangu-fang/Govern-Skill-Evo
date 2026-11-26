from copy import deepcopy
from dataclasses import replace
import difflib
import json
from pathlib import Path
import tempfile
import unittest

import httpx
from openai import OpenAI
from skilladam.benchmarks.lmb.choices import shuffle_choices
from skilladam.execution.contracts import BatchExecution, GenerationRequest, GenerationResult, ToolCall
from skilladam.types import MetricResult
from src.adapters.lmb import skilladam as m
from src.skill_evolution.v27.training import Case
from tests.skill_evolution.v27.support import Dataset, CHOICES, HIDDEN, SKILL, Transport, response


class SyntheticDataset(Dataset):
    def __init__(self, root, count=10):
        super().__init__(root, count)
        for uid, row in self.rows.items():
            correct = next(c for c in CHOICES if shuffle_choices(CHOICES, c['label'], seed=42, item_id=uid)[1] == 'A')
            row['correct_choice'] = correct

    def case(self, uid):
        row = self.rows[uid]
        choices, label = shuffle_choices(CHOICES, row['correct_choice']['label'], seed=42, item_id=uid)
        return Case(uid, {'question': row['question'], 'choices': choices}, {'label': label},
                    {'split': 'train', 'source_split': 'train'})


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

    def test_shared_prompt_avoids_literal_tags_and_preserves_native_task(self):
        from skilladam.benchmarks.lmb.adapter import LMBAdapter as Upstream
        upstream = Upstream(self.production.root)
        adapted = m.NativeAdapter(self.production.root)
        for split in ('train', 'test'):
            for case in m.native_cases(self.production, split):
                kwargs = dict(method='skilladam', split=split, skill=self.initial, seed=42)
                old = upstream.build_rollout_request(case, **kwargs)
                new = adapted.build_rollout_request(case, **kwargs)
                self.assertEqual(old.metadata['messages'][1], new.metadata['messages'][1])
                self.assertEqual(old.metadata['evaluation_choices'], new.metadata['evaluation_choices'])
                self.assertEqual(old.metadata['correct_label'], new.metadata['correct_label'])
                self.assertEqual(new.metadata['messages'], tuple(m.p.messages(
                    self.production.case(case.case_id).payload, self.initial)))
                for tag in ('<answer>', '</answer>', '<think>', '</think>'):
                    self.assertNotIn(tag, new.metadata['messages'][0]['content'])
        for path in (m.ROOT / 'src/skill_evolution/v27/benchmarks/lmb/prompts').glob('*.md'):
            for tag in ('<answer>', '</answer>', '<think>', '</think>'):
                self.assertNotIn(tag, path.read_text())

    def test_native_profile_and_schedule(self):
        upstream = m.read(m.ROOT / 'external/SkillAdam/skilladam/experiments/main_results.json')['benchmarks']['lmb']['skilladam']
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
        self.assertEqual([len(b) for b in self.snapshot['batches']], [10]*5+[3])
        self.assertEqual(len(self.production.splits['test']), 124)
        self.assertFalse(set(self.production.splits['train']) & set(self.production.splits['test']))
        self.assertEqual(self.initial, (m.ROOT / self.cfg['initial_skill']).read_text())

    def test_content_only_score_usage_and_archive_recovery(self):
        transport = Transport()
        backend = self.backend(transport)
        execution = BatchExecution(self.requests(), self.context, 'training_rollout')
        raw = backend.execute_batch(execution)
        self.assertEqual(transport.calls, 10)
        for case, item in zip(m.native_cases(self.dataset), raw):
            self.assertNotIn(HIDDEN, repr(item.result))
            parsed = self.adapter.parse_result(case, item.result)
            self.assertEqual(self.adapter.evaluate(parsed).primary, 1)
            self.assertEqual(parsed.usage[0].requests, 1)
            self.assertEqual(parsed.usage[0].reasoning_tokens, 15)
        backend.execute_batch(execution)
        self.assertEqual(transport.calls, 10)
        # A corrupted completed task cannot trigger new calls for any task.
        result = next(backend.stage_directory.glob('actor/actor/*/result.json'))
        result.unlink()
        with self.assertRaises(ValueError):
            backend.execute_batch(execution)
        self.assertEqual(transport.calls, 10)

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
        with patch('src.skill_evolution.v27.benchmarks.lmb.actor.time.sleep'):
            backend.execute_batch(execution)
        self.assertEqual(transport.calls, 11)

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
        with patch('src.skill_evolution.v27.benchmarks.lmb.actor.time.sleep'):
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
        with patch('src.skill_evolution.v27.benchmarks.lmb.actor.time.sleep'):
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

    def test_native_gate_boundary(self):
        def metric(value):
            return MetricResult(primary=value, metrics={'exact_match': value}, sample_count=10)
        self.assertFalse(self.adapter.gate(metric(.5), metric(.5)).accepted)
        self.assertFalse(self.adapter.gate(metric(.5), metric(.57)).accepted)
        self.assertTrue(self.adapter.gate(metric(.5), metric(.58)).accepted)

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
        with self.assertRaisesRegex(ValueError, 'Frozen optimizer settings differ'):
            m.prepare(path)

    def test_native_full_iteration_and_completed_resume(self):
        candidate = SKILL + 'Check equality conditions.\n'
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
                        'evidence': 'Synthetic fixture only.', 'failure_type': 'condition_miss',
                        'inherited_from_iteration': True}),))
                raise AssertionError(request.stage)
        transport = Transport(fn=lambda messages, directory: response(
            '<answer>A</answer>' if 'validation_candidate' in str(directory) else '<answer>B</answer>'))
        backend = self.backend(transport, Generation())
        native = replace(self.native, optimization_case_ids=tuple(self.dataset.splits['train']),
            feedback_loop=replace(self.native.feedback_loop, max_iterations=1, min_iterations=1))
        def runner():
            return m.Runner(config=native, adapter=self.adapter, backend=backend,
                            context=self.context, output_dir=self.root / 'native')
        result = runner().run(cases=m.native_cases(self.dataset), initial_skill=SKILL)
        self.assertEqual(result.final_skill, candidate)
        self.assertIsNone(result.stage0)
        self.assertIn('synthetic-condition', result.momentum.problems)
        self.assertEqual(transport.calls, 30)  # Native training + Gate parent + Gate candidate.
        self.assertEqual([r.stage for r in requests], ['iteration_patch', 'momentum_update'])
        # Inspect both actual optimizer requests, not only the context object.
        base_protocol = m.p.messages(self.dataset.case(self.dataset.splits['train'][0]).payload, '')[0]['content'].strip()
        from skilladam.benchmarks.lmb.rollout import VENDOR_PROMPT
        upstream_protocol = VENDOR_PROMPT.format(skill_section='').strip()
        for request in requests:
            system = request.messages[0]['content']
            self.assertEqual(request.messages[0]['role'], 'system')
            self.assertEqual(system.count(f'```\n{base_protocol}\n```'), 1)
            self.assertNotIn(upstream_protocol, system)
        self.assertNotIn(HIDDEN, repr(requests))
        self.assertEqual(runner().run(cases=m.native_cases(self.dataset), initial_skill=SKILL, resume=True).final_skill, candidate)
        self.assertEqual(transport.calls, 30)
        self.assertEqual(len(requests), 2)
