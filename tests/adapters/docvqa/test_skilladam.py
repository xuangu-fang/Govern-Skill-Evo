from copy import deepcopy
from dataclasses import replace
import difflib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from openai import OpenAI
from skilladam.execution.contracts import BatchExecution, GenerationRequest, GenerationResult, ToolCall
from skilladam.methods.skilladam import _profile_gate
from skilladam.types import MetricResult
from src.adapters.docvqa import skilladam as m
from tests.skill_evolution.v29.campaign_support import CampaignDataset
from tests.skill_evolution.v29.test_actor import Transport, response, HIDDEN


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = m.prepare()
        cls.cfg, cls.production, cls.initial, cls.native, cls.context = cls.prepared

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dataset = CampaignDataset(self.root / 'data', [2])
        self.adapter = m.NativeAdapter(self.dataset.root)
        self.enterContext(patch.object(m.actor.time, 'sleep'))

    def small_prepared(self, sizes=None):
        if sizes:
            self.dataset = CampaignDataset(self.root / 'other-data', sizes)
        sizes = sizes or [2]
        native = replace(self.native, train_size=sizes[0], validation_size=sizes[0], stage0_size=sizes[0],
            optimization_case_ids=tuple(self.dataset.splits['train']), feedback_loop=replace(
                self.native.feedback_loop, max_iterations=len(sizes), min_iterations=len(sizes)))
        return self.cfg, self.dataset, self.initial, native, self.context

    def backend(self, transport=None, generation=None):
        result = m.Backend(self.dataset, transport or Transport(), generation, self.context, self.root / 'execution')
        result.stage_directory = result.output_dir / 'rollouts/iter_000/training'
        return result

    def execution(self, skill=None):
        requests = tuple(self.adapter.build_rollout_request(c, method='skilladam', split='train',
            skill=skill or self.initial, seed=42) for c in m.native_cases(self.dataset))
        return BatchExecution(requests, self.context, 'training_rollout')

    def generation(self, *, interrupt=None):
        outer = self
        class Generation:
            def __init__(self):
                self.requests = []
                self.interrupt = interrupt
            def generate(self, request):
                if self.interrupt == request.stage:
                    self.interrupt = None
                    raise RuntimeError('synthetic interruption')
                self.requests.append(request)
                if request.stage == 'momentum_update':
                    return GenerationResult('', tool_calls=(ToolCall('report_problem', {
                        'label': 'synthetic-condition', 'description': 'Synthetic only.',
                        'evidence': 'Synthetic fixture.', 'failure_type': 'near_match_confusion',
                        'inherited_from_iteration': True}),))
                # Add the first rule, then use native empty-patch handling in later rounds.
                delta = ''.join(difflib.unified_diff(outer.initial.splitlines(True),
                    (outer.initial + 'Check amount boundaries.\n').splitlines(True),
                    fromfile='a/SKILL.md', tofile='b/SKILL.md')) if request.metadata['iteration'] == 0 else ''
                return GenerationResult(json.dumps({'reasoning': 'Synthetic only.', 'patch': delta}))
        return Generation()

    def test_frozen_data_initial_and_schedule(self):
        upstream = m.read(m.ROOT / 'external/SkillAdam/skilladam/data/profiles/docvqa_main_results.json')
        self.assertEqual(upstream['splits'], self.production.source_ids)
        self.assertEqual(upstream['source_revision'], m.p.REVISION)
        self.assertEqual([len(b) for b in self.production.batches], [15] * 10 + [10])
        self.assertEqual(len(self.production.splits['test']), 374)
        self.assertFalse(set(self.production.splits['test']) & set(self.production.splits['train']))
        self.assertEqual(self.initial, m.p.initial_skill())
        self.assertEqual(self.native.feedback_loop.edit_budget.metric_key, 'hard')
        self.assertEqual(self.native.feedback_loop.edit_budget.v_max, .04)
        self.assertEqual(self.native.optimizer_context_limit, 110000)
        self.assertEqual(self.native.trajectory_compression, 'deterministic')

    def test_all_534_actor_messages_identical(self):
        from PIL import Image
        images = set()
        for split in ('train', 'test'):
            for case in m.native_cases(self.production, split):
                request = self.adapter.build_rollout_request(case, method='skilladam', split=split,
                    skill=self.initial, seed=42)
                self.assertEqual(m.plain(request.metadata['messages']), m.p.messages_for_case(case, self.initial))
                images.add(Path(case.metadata['image_root']) / case.payload['image_path'])
        for path in images:
            with Image.open(path) as im:
                im.verify()
        self.assertEqual(len(images), 439)

    def test_preflight_no_credentials_or_output(self):
        from scripts.runs.run_docvqa_skilladam import main
        with patch('scripts.runs.run_v29_pilot.read_credentials', side_effect=AssertionError('credentials read')):
            with patch('sys.stdout', new_callable=io.StringIO) as output:
                main(['preflight', '--env-file', '/missing'])
            self.assertEqual(json.loads(output.getvalue())['model_requests'], 0)

    def test_changed_native_profile_rejected(self):
        for section, key, value in [('native', 'gate_profile', 'default'),
                                    ('actor', 'max_tokens', 16384), ('optimizer', 'model', 'other')]:
            cfg = deepcopy(self.cfg); cfg[section][key] = value
            path = self.root / 'config.json'; m.save(path, cfg)
            with self.assertRaises(ValueError): m.prepare(path)

    def test_v2_gate_boundaries(self):
        gate = _profile_gate(self.adapter, 'docvqa', None, self.native.gate_profile)
        def metric(hard, soft):
            return MetricResult(primary=hard, metrics={'hard': hard, 'soft': soft}, sample_count=15)
        baseline = metric(.5, .7)
        for h, s, accepted in [(.5, .71, True), (.51, .7, True), (.5, .7, False),
                               (.51, .65, False), (.45, .71, False), (.46, .71, True)]:
            self.assertEqual(gate.judge(baseline, metric(h, s)).accepted, accepted)
        self.assertEqual(gate.profile, 'v2')

    def test_prompt_changes_only_initial_skill_structure_contract(self):
        from skilladam.methods.skilladam_prompts import (
            load_benchmark_prompt_context, IterationPromptBuilder, IterationPromptContext, CondensedTrajectory)
        original = load_benchmark_prompt_context('docvqa', trajectory_count=15,
            benchmark_domain_info_md='Training trajectories are supplied per iteration.',
            prompt_profile=self.native.prompt_profile)
        runner = m.Runner(config=self.native, adapter=self.adapter, backend=None,
            context=self.context, output_dir=self.root / 'unused')
        runner._prompt_context = original
        adapted = runner._prompts
        self.assertEqual(adapted.skill_writing_policy.split('### 3. Edit Balance', 1)[1],
                         original.skill_writing_policy.split('### 3. Edit Balance', 1)[1])
        self.assertEqual(replace(adapted, skill_writing_policy=original.skill_writing_policy,
                                stage0=original.stage0), original)
        rendered = IterationPromptBuilder(adapted.iteration_template_path).build(IterationPromptContext(
            adapted, self.initial, (CondensedTrajectory('fixture', 'Synthetic evidence.'),), '', edit_budget=4))
        self.assertIn('valid without YAML frontmatter', rendered.system_prompt)
        self.assertIn('Visual Evidence Discipline', rendered.system_prompt)
        self.assertIn('Exact Answer Discipline', rendered.system_prompt)
        self.assertNotIn('The skill body has exactly two sections', rendered.system_prompt)
        self.assertNotIn('No other top-level sections are permitted', rendered.system_prompt)
        self.assertNotIn('```yaml', rendered.system_prompt)
        self.assertIn(self.initial.strip(), rendered.user_prompt)

    def test_actor_scoring_text_projection_and_reuse(self):
        transport = Transport()
        backend = self.backend(transport)
        execution = self.execution()
        results = backend.execute_batch(execution)
        for request, raw in zip(execution.requests, results):
            parsed = self.adapter.parse_result(request.case, raw.result)
            metric = self.adapter.evaluate(parsed)
            self.assertEqual(metric.metrics, {'hard': 1., 'soft': 1.})
            self.assertNotIn(HIDDEN, repr(parsed))
            self.assertNotIn('data:image', repr(parsed))
            self.assertIn('[image: amount.png]', repr(parsed))
            self.assertEqual(parsed.usage[0].requests, 1)
        backend.execute_batch(execution)
        self.assertEqual(len(transport.seen), 2)

    def test_wrong_stop_response_is_scored_without_retry(self):
        transport = Transport(lambda *_: response('ordinary wrong answer'))
        backend = self.backend(transport)
        for request, raw in zip(self.execution().requests, backend.execute_batch(self.execution())):
            self.assertEqual(self.adapter.evaluate(self.adapter.parse_result(request.case, raw.result)).primary, 0)
        self.assertEqual(len(transport.seen), 2)

    def test_partial_actor_recovery_and_six_attempt_budget(self):
        def interrupted(messages, slot):
            if '0002' in str(slot): raise RuntimeError('synthetic interruption')
            return response()
        transport = Transport(interrupted)
        backend = self.backend(transport)
        with self.assertRaises(RuntimeError): backend.execute_batch(self.execution())
        transport.generate = lambda *_: response()
        backend.execute_batch(self.execution())
        self.assertEqual(len(transport.seen), 3)
        exhausted = Transport(lambda *_: response('partial', 'length'))
        backend.stage_directory = backend.output_dir / 'rollouts/iter_001/training'
        backend.actor.transport = exhausted
        with self.assertRaisesRegex(Exception, 'budget exhausted'): backend.execute_batch(self.execution())
        count = len(exhausted.seen)
        self.assertEqual(count, 12)
        with self.assertRaisesRegex(Exception, 'budget exhausted'): backend.execute_batch(self.execution())
        self.assertEqual(len(exhausted.seen), count)

    def test_test_case_cannot_enter_optimizer(self):
        case = self.dataset.case('synthetic:test')
        request = self.adapter.build_rollout_request(case, method='skilladam', split='test', skill=self.initial, seed=42)
        backend = self.backend()
        with self.assertRaises(ValueError): backend.execute_batch(BatchExecution((request,), self.context, 'training_rollout'))
        self.assertFalse(backend.output_dir.exists())

    def test_optimizer_payload_tools_and_raw_recording(self):
        bodies = []
        def handler(request):
            bodies.append(json.loads(request.content))
            self.assertEqual(str(request.url), 'https://api.deepseek.com/chat/completions')
            raw = response('optimizer text')
            if 'tools' in bodies[-1]:
                raw['choices'][0]['message'].update(content=None, tool_calls=[{'id': 'fixture', 'type': 'function',
                    'function': {'name': 'fixture', 'arguments': '{"x":1}'}}])
                raw['choices'][0]['finish_reason'] = 'tool_calls'
            return httpx.Response(200, json=raw)
        def factory(**kwargs):
            self.assertEqual(kwargs['max_retries'], 2)
            self.assertEqual(kwargs['timeout'].connect, 10)
            self.assertEqual(kwargs['timeout'].read, 300)
            client = OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
            self.addCleanup(client.close)
            return client
        generation = m.generation_transport(self.cfg, self.dataset, self.context, self.root,
            environ={'OPENAI_API_KEY': 'synthetic-secret', 'OPENAI_BASE_URL': 'https://api.deepseek.com'}, client_factory=factory)
        request = GenerationRequest('iteration_patch', ({'role': 'user', 'content': 'fixture'},), self.context, {})
        self.assertEqual(generation.generate(request).text, 'optimizer text')
        tool = {'type': 'function', 'function': {'name': 'fixture', 'parameters': {'type': 'object'}}}
        result = generation.generate(replace(request, stage='momentum_update', metadata={'tools': [tool]}))
        self.assertEqual(result.tool_calls[0].arguments['x'], 1)
        for body in bodies:
            self.assertEqual(body['max_tokens'], 16384)
            for key in ('model', 'temperature', 'thinking', 'reasoning_effort'):
                self.assertEqual(body[key], self.cfg['actor'][key])
        for path in (self.root / 'raw_optimizer').rglob('*.json'):
            self.assertNotIn('synthetic-secret', path.read_text())
        self.assertNotIn(HIDDEN, repr(result))

    def full_run(self, *, before='1,200', after='1,320', interrupt=None, sizes=None):
        prepared = self.small_prepared(sizes)
        transport = Transport(lambda messages, slot: response('<answer>' + (
            after if 'Check amount boundaries.' in messages[0]['content'] else before) + '</answer>'))
        generation = self.generation(interrupt=interrupt)
        root = self.root / 'campaign'
        if interrupt:
            with self.assertRaisesRegex(RuntimeError, 'synthetic interruption'):
                m.run_training(root, prepared, actor_transport=transport, generation=generation)
        result = m.run_training(root, prepared, actor_transport=transport, generation=generation, resume=bool(interrupt))
        counts = len(transport.seen), len(generation.requests)
        ledger = (root / 'native/usage.jsonl').read_text()
        m.run_training(root, prepared, actor_transport=transport, generation=generation, resume=True)
        self.assertEqual(counts, (len(transport.seen), len(generation.requests)))
        self.assertEqual(ledger, (root / 'native/usage.jsonl').read_text())
        self.assertNotIn(HIDDEN, repr(generation.requests))
        self.assertNotIn('data:image', repr(generation.requests))
        for request in generation.requests:
            self.assertIn(m.p.actor_base_protocol().strip(), request.messages[0]['content'])
        state = m.read(root / 'native/checkpoint.json')
        self.assertIn('synthetic-condition', repr(state))
        self.assertFalse((root / 'native/stage0.json').exists())
        return root, result, prepared, transport, state

    def test_native_accept_momentum_budget_and_resume(self):
        root, result, _, transport, state = self.full_run()
        self.assertEqual(result['accepted'], 1)
        self.assertEqual(len(transport.seen), 6)  # Native training, baseline and candidate are independent.
        self.assertIn('Check amount boundaries.', (root / 'final_skill.md').read_text())
        self.assertEqual(state['iterations'][0]['edit_budget'], 4)

    def test_training_evidence_reaches_patch_and_momentum(self):
        self.dataset.rows['synthetic:001'] = ('Which amount?', ['1,320', '1 320'], 'train')
        root, _, _, _, _ = self.full_run()
        traces = m.read(root / 'native/iterations/iter_000/training_trajectories.json')
        inputs = root / 'execution/optimizer/iter_000'
        prompts = [m.read(inputs / name)['messages'][-1]['content'] for name in
                   ('iteration_patch_01.input.json', 'momentum_update_00.input.json')]
        self.assertEqual([item['case_id'] for item in traces], self.dataset.splits['train'])
        for item in traces:
            case = self.dataset.case(item['case_id'])
            evidence = json.loads(item['markdown'].split('\n\n## Training evidence\n\n')[1])
            self.assertEqual(evidence, {'initial': {'task': {'image_path': case.payload['image_path']}},
                                        'outcome': {'reference_answers': case.reference}})
            for prompt in prompts:
                self.assertIn(item['markdown'], prompt)

    def test_resume_cannot_mix_legacy_training_evidence(self):
        root, _, prepared, _, _ = self.full_run()
        identity = root / 'execution/run.json'
        legacy = m.read(identity)
        del legacy['training_evidence_fields']
        m.save(identity, legacy)
        with self.assertRaisesRegex(ValueError, 'Existing record differs'):
            m.run_training(root, prepared, actor_transport=None, generation=None, resume=True)

    def test_native_soft_only_acceptance(self):
        _, result, _, _, _ = self.full_run(before='abc', after='1,32')
        self.assertEqual(result['accepted'], 1)

    def test_native_retain_still_updates_momentum(self):
        root, result, _, _, _ = self.full_run(before='abc', after='abc')
        self.assertEqual(result['accepted'], 0)
        self.assertEqual((root / 'final_skill.md').read_text(), self.initial)

    def test_resume_interrupted_first_patch(self):
        self.full_run(interrupt='iteration_patch')

    def test_resume_interrupted_pending_momentum(self):
        self.full_run(interrupt='momentum_update')

    def test_resume_candidate_reuses_completed_patch_and_actor_tasks(self):
        prepared = self.small_prepared()
        generation = self.generation()
        interrupted = [False]
        def respond(messages, slot):
            if 'validation_candidate' in str(slot) and '0002' in str(slot) and not interrupted[0]:
                interrupted[0] = True
                raise RuntimeError('synthetic candidate interruption')
            return response()
        transport = Transport(respond)
        root = self.root / 'campaign'
        with self.assertRaisesRegex(RuntimeError, 'candidate interruption'):
            m.run_training(root, prepared, actor_transport=transport, generation=generation)
        m.run_training(root, prepared, actor_transport=transport, generation=generation, resume=True)
        self.assertEqual(len(transport.seen), 7)
        self.assertEqual([r.stage for r in generation.requests], ['iteration_patch', 'momentum_update'])

    def test_variance_budget_and_history_survive_between_rounds(self):
        prepared = self.small_prepared([2, 2])
        generation = self.generation()
        generate = generation.generate
        interrupted = [False]
        def interrupt_second(request):
            if request.stage == 'iteration_patch' and request.metadata['iteration'] == 1 and not interrupted[0]:
                interrupted[0] = True
                raise RuntimeError('synthetic second iteration')
            return generate(request)
        generation.generate = interrupt_second
        def respond(messages, slot):
            # Parent hard=[1,0], candidate=[0,1]: mean ties, nonzero per-case variance.
            correct = ('0001' in str(slot)) != ('validation_candidate' in str(slot))
            return response('<answer>1,320</answer>' if correct else '<answer>wrong</answer>')
        transport = Transport(respond)
        root = self.root / 'campaign'
        with self.assertRaisesRegex(RuntimeError, 'second iteration'):
            m.run_training(root, prepared, actor_transport=transport, generation=generation)
        state = m.read(root / 'native/checkpoint.json')
        self.assertAlmostEqual(state['v_ema'], .2)
        self.assertEqual(state['next_iteration'], 1)
        m.run_training(root, prepared, actor_transport=transport, generation=generation, resume=True)
        state = m.read(root / 'native/checkpoint.json')
        self.assertEqual([r['edit_budget'] for r in state['iterations']], [4, 1])
        second = next(r for r in generation.requests if r.stage == 'iteration_patch' and r.metadata['iteration'] == 1)
        self.assertGreater(len(second.messages), 2)
        self.assertEqual(second.metadata['edit_budget'], 1)

    def test_eleven_batches_with_partial_final_batch(self):
        _, result, _, transport, state = self.full_run(sizes=[15] * 10 + [10])
        self.assertEqual(result['iterations'], 11)
        self.assertEqual(result['optimization_count'], 160)
        self.assertEqual(state['next_iteration'], 11)  # SkillAdam iterations are zero-based.
        self.assertEqual(len(transport.seen), 480)
        self.assertEqual([len(r['training_case_ids']) for r in state['iterations']], [15] * 10 + [10])

    def test_final_test_uses_fixed_skill_and_completed_resume(self):
        root, _, prepared, _, _ = self.full_run()
        protected = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        transport = Transport(lambda *_: response('<answer>secret</answer>'))
        output = self.root / 'test'
        result = m.run_test(root, output, prepared, actor_transport=transport)
        self.assertEqual(result['sample_count'], 1)
        self.assertEqual(result['success_count'], 1)
        m.run_test(root, output, prepared, actor_transport=transport, resume=True)
        self.assertEqual(len(transport.seen), 1)
        self.assertEqual(protected, {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_test_blocked_before_training(self):
        transport = Transport()
        with self.assertRaises(FileNotFoundError):
            m.run_test(self.root / 'missing', self.root / 'test', self.small_prepared(), actor_transport=transport)
        self.assertFalse(transport.seen)
        self.assertFalse((self.root / 'test').exists())

    def test_interrupted_test_resumes_with_same_final_skill(self):
        root, _, prepared, _, _ = self.full_run()
        transport = Transport(lambda *_: (_ for _ in ()).throw(RuntimeError('synthetic Test interruption')))
        output = self.root / 'test'
        with self.assertRaises(RuntimeError):
            m.run_test(root, output, prepared, actor_transport=transport)
        self.assertFalse((output / 'summary.json').exists())
        transport.generate = lambda *_: response('<answer>secret</answer>')
        result = m.run_test(root, output, prepared, actor_transport=transport, resume=True)
        self.assertEqual(result['api_requests'], 2)
        self.assertEqual(result['sample_count'], 1)
