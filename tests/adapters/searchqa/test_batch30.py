"""Batch-30 integration without provider calls or production run writes."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from openai import OpenAI
from skilladam.execution.contracts import GenerationRequest, GenerationResult, ToolCall
from skilladam.methods.skilladam import _profile_gate
from skilladam.types import MetricResult
from src.adapters.searchqa import skilladam as m
from src.skill_evolution.v28 import evolution
from src.skill_evolution.v28.benchmarks.searchqa import actor, prompting
from src.skill_evolution.v28.benchmarks.searchqa.dataset import SearchQADataset
from src.skill_evolution.v28.benchmarks.searchqa.adapter import SearchQAActorAdapter
from src.skill_evolution.v28.campaign import CampaignAdapter
from src.skill_evolution.v28.config import campaign_config, validate_config
from tests.adapters.searchqa.test_skilladam import SyntheticDataset, SKILL
from tests.skill_evolution.v28.runtime_support import Transport, response
from tests.skill_evolution.v28.campaign_support import CampaignDataset, Generator

CONFIG = m.ROOT / 'experiments/configs/searchqa_skilladam600_batch30_epoch1_deepseek_flash.json'


class Batch30Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.dataset, cls.initial, cls.native, cls.context, cls.snapshot = m.prepare(CONFIG)

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_schedule_data_prompt_and_identity(self):
        old = SearchQADataset()
        self.assertEqual(self.dataset.rows, old.rows)
        self.assertEqual(self.dataset.splits, old.splits)
        self.assertEqual(self.dataset.batches, [old.batches[i] + old.batches[i+1] for i in range(0, 40, 2)])
        self.assertNotEqual(self.dataset.snapshot()['schedule_sha256'], old.snapshot()['schedule_sha256'])
        self.assertEqual((self.native.feedback_loop.min_iterations, self.native.feedback_loop.max_iterations), (20, 20))
        adapter = CampaignAdapter(SearchQAActorAdapter(self.dataset))
        # Exercise the current v28 runtime with its own generated configuration;
        # the historical comparison config only supplies shared Actor/data settings.
        config = campaign_config(adapter, initial_skill={'source': self.cfg['initial_skill'], 'text': self.initial})
        with adapter.using():
            validate_config(config)
            for name in prompting.PROMPT_VERSIONS:
                rendered = prompting.render(name, self.cfg['actor'])
                archived = prompting.resource_path(name + '.md').read_text()
                self.assertEqual(rendered, archived.replace('49,152', '32,768'))
            bad = deepcopy(config); bad['batches'][0], bad['batches'][1] = bad['batches'][1], bad['batches'][0]
            with self.assertRaises(ValueError): validate_config(bad)
            bad = deepcopy(config); bad['module_calls']['editor']['max_tokens'] = 32768
            with self.assertRaises(ValueError): validate_config(bad)
        with self.assertRaises(ValueError): SearchQAActorAdapter(self.dataset, Transport())
        # prepare() checks both Actor prompt implementations for all 2,000 cases.
        self.assertEqual(self.cfg['actor'], m.p.actor_config(30))

    def test_gate_thresholds_remain_official_at_30(self):
        gate = _profile_gate(m.NativeAdapter(self.root), 'searchqa', None, 'main-result')
        self.assertEqual(gate.to_dict(), {'min_em_gain': .04, 'min_f1_gain': .025, 'max_em_drop': .04, 'max_f1_drop': .05})
        def metric(n, f1):
            return MetricResult(primary=n/30, metrics={'exact_match': n/30, 'token_f1': f1}, sample_count=30)
        base = metric(20, .8)
        self.assertFalse(gate.judge(base, metric(21, .8)).accepted)
        self.assertTrue(gate.judge(base, metric(22, .8)).accepted)
        self.assertTrue(gate.judge(base, metric(19, .83)).accepted)

    def test_wire_budgets_and_raw_length_response_before_parse_failure(self):
        bodies = []
        def handler(request):
            body = json.loads(request.content); bodies.append(body)
            raw = response('optimizer text')
            if len(bodies) == 3:
                raw = response(None, finish='length')
                raw['usage']['completion_tokens'] = 65536
                raw['usage']['total_tokens'] = raw['usage']['prompt_tokens'] + 65536
                raw['usage']['completion_tokens_details']['reasoning_tokens'] = 65536
            return httpx.Response(200, json=raw)
        def factory(**kwargs):
            client = OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
            self.addCleanup(client.close)
            return client
        generation = m.generation_transport(self.cfg, self.dataset, self.context, self.root,
            environ={'OPENAI_API_KEY': 'synthetic', 'OPENAI_BASE_URL': 'https://api.deepseek.com'}, client_factory=factory)
        req = GenerationRequest('iteration_patch', ({'role': 'user', 'content': 'fixture'},), self.context, {})
        generation.generate(req)
        generation.generate(replace(req, stage='momentum_update'))
        with self.assertRaisesRegex(Exception, 'text or tool calls'):
            generation.generate(replace(req, stage='momentum_update'))
        generation.generate(req)
        self.assertEqual([b['max_tokens'] for b in bodies], [32768, 65536, 65536, 32768])
        self.assertEqual(generation.backend._config.max_completion_tokens, 32768)
        summary = m.read(self.root/'raw_optimizer/response_0003/summary.json')
        self.assertEqual(summary['choices'][0]['finish_reason'], 'length')
        self.assertEqual(summary['usage']['completion_tokens'], 65536)
        self.assertEqual(len(list((self.root/'raw_optimizer').glob('response_*'))), 4)
        for body in bodies:
            for key in ('model', 'temperature', 'reasoning_effort', 'thinking'):
                self.assertEqual(body[key], self.cfg['actor'][key])

    def test_tracker_order_restore_rejects_changed_content(self):
        from src.adapters.searchqa.runtime import restore_problem_order
        from skilladam.core.momentum import MomentumTracker
        tracker = MomentumTracker()
        for label in ['z-last', 'a-first']:
            tracker.execute_tool_call('report_problem', {'label': label, 'description': 'original', 'evidence': 'fixture'})
        archived = '# Current Problem Tracker\n\n' + tracker.render_for_agent_input() + '\n\n# Ordered Condensed Training Trajectories'
        tracker.problems = dict(sorted(tracker.problems.items()))
        restore_problem_order(tracker, archived)
        self.assertEqual(list(tracker.problems), ['z-last', 'a-first'])
        tracker.problems['z-last'].description = 'changed'
        with self.assertRaisesRegex(ValueError, 'content differs'):
            restore_problem_order(tracker, archived)

    def test_independent_test_uses_new_actor_budget(self):
        from src.skill_evolution.v28.evaluation import run_evaluation
        data = SyntheticDataset(self.root/'data', count=30); data.batch_size = 30
        transport = Transport(); transport.config = deepcopy(self.cfg['actor'])
        adapter = SearchQAActorAdapter(data, transport)
        skill = self.root/'fixed.md'; skill.write_text(SKILL)
        report = run_evaluation(self.root/'test', adapter=adapter, skill_file=skill)
        self.assertEqual(report['status'], 'complete')
        self.assertFalse(report['optimization_updates'])
        self.assertEqual(m.read(self.root/'test/plan.json')['actor']['max_tokens'], 32768)
        run_evaluation(self.root/'test', adapter=adapter, skill_file=skill, resume=True)
        self.assertEqual(transport.calls, 1)

    def test_actor_retries_identical_32768_request_without_scoring_length(self):
        seen = []
        def call(messages, directory):
            seen.append(m.read(directory/'request.json')['body'])
            return response('ignored', finish='length') if len(seen) == 1 else response()
        transport = Transport(call); transport.config = deepcopy(self.cfg['actor'])
        case = self.dataset.case(self.dataset.splits['train'][0])
        with patch.object(actor.time, 'sleep'):
            result = actor.execute(case, self.initial, self.root/'actor', transport)
        self.assertEqual(seen[0], seen[1])
        self.assertEqual(seen[0]['max_tokens'], 32768)
        self.assertEqual(result['api_requests'], 2)
        self.assertEqual(result['termination'], 'stop')
        self.assertEqual(actor.read_completed(case, self.initial, self.root/'actor', self.cfg['actor']), result)

    def test_v28_full_chain_30_and_archive_only_resume(self):
        data = CampaignDataset(rounds=1, batch_size=30); data.batch_size = 30
        transport = Transport(lambda messages, _: response('<answer>New York City</answer>'
            if 'Use the exact entity.' in messages[0]['content'] else '<answer>New York</answer>'))
        transport.config = deepcopy(self.cfg['actor'])
        bound = CampaignAdapter(SearchQAActorAdapter(data, transport))
        cfg = campaign_config(bound, initial_skill={'source': None, 'text': SKILL})
        gen = Generator(); root = self.root/'v28'
        with bound.using():
            result = evolution.run_campaign(root, config=cfg, generate=gen)
            self.assertEqual(result['status'], 'complete')
            self.assertEqual(gen.calls, ['grouping', 'diagnosis', 'preconditioner', 'editor', 'replay'])
            self.assertEqual(transport.calls, 60)
        archive = CampaignAdapter(SearchQAActorAdapter(data))
        with archive.using():
            self.assertIn('Use the exact entity.', evolution.final_parent(root).read_text())
            evolution.run_campaign(root, config=cfg, resume=True, generate=None)
        self.assertEqual(transport.calls, 60)

    def test_pending_momentum_resume_preserves_request_and_does_not_repeat_actor_gate(self):
        data = SyntheticDataset(self.root, count=60); data.batch_size = 30
        transport = Transport(); transport.config = deepcopy(self.cfg['actor'])
        seen = []; failed = False
        class Generation:
            def generate(inner, request):
                nonlocal failed
                seen.append(request)
                if request.stage == 'iteration_patch':
                    return GenerationResult(json.dumps({'reasoning': 'No change in this fixture.', 'patch': ''}))
                if request.metadata['iteration'] == 1 and not failed:
                    failed = True
                    raise RuntimeError('synthetic Momentum interruption')
                labels = ['z-last', 'a-first'] if request.metadata['iteration'] == 0 else ['b-second']
                return GenerationResult('', tool_calls=tuple(ToolCall('report_problem', {
                    'label': label, 'description': 'Fixture.', 'evidence': 'Fixture.',
                    'failure_type': 'rule_missing', 'inherited_from_iteration': True}) for label in labels))
        backend = m.Backend(data, transport, Generation(), self.context, self.root/'rollouts', {'fixture': 'batch30'})
        native = replace(self.native, optimization_case_ids=tuple(data.splits['train']),
            feedback_loop=replace(self.native.feedback_loop, min_iterations=2, max_iterations=2))
        def runner():
            return m.Runner(config=native, adapter=m.NativeAdapter(self.root), backend=backend,
                            context=self.context, output_dir=self.root/'native')
        with self.assertRaisesRegex(RuntimeError, 'synthetic Momentum interruption'):
            runner().run(cases=m.native_cases(data), initial_skill=SKILL)
        calls = transport.calls
        self.assertEqual(calls, 180)
        original = seen[-1]
        # Native checkpoint serialization sorts tracker keys. Resume must recover
        # the original z/a order and still pass the full archived signature check.
        result = runner().run(cases=m.native_cases(data), initial_skill=SKILL, resume=True)
        self.assertEqual(result.final_skill, SKILL)
        self.assertEqual(transport.calls, calls)
        self.assertEqual(seen[-1], original)
        self.assertEqual(len(seen), 5)
