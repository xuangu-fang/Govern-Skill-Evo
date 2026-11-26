"""Actor truncation is a durable technical failure, never optimization evidence."""
from copy import deepcopy
import json
from unittest.mock import call, patch

from src.skill_evolution.v27 import stages
from src.skill_evolution.v27.benchmarks.lmb import actor, facts, protocol as p
from src.skill_evolution.v27.transport import RequestFailure
from .test_offline import Base
from .support import Dataset, HIDDEN, SKILL, Transport, record, response


class LengthRetryTests(Base):
    def test_length_variants_retry_identical_messages_and_keep_content_private(self):
        data = Dataset(self.root / 'data', 1)
        for i, content in enumerate((None, '', '<answer>A</answer>', 'partial proof')):
            with self.subTest(content=content):
                seen = []
                def generate(messages, directory):
                    seen.append(deepcopy(messages))
                    return response(content, 'length') if len(seen) == 1 else response('<answer>B</answer>')
                transport = Transport(fn=generate)
                root = self.root / str(i)
                result = actor.execute(data.case('synthetic:000'), SKILL, root, transport)
                self.assertEqual(seen, [result['initial_messages']] * 2)
                self.assertEqual(result['api_requests'], 2)
                self.assertEqual(result['termination'], 'stop')
                self.assertEqual(result['metrics']['em'], 0)  # Correct truncated answer was not selected.
                self.assertEqual(result['content'], '<answer>B</answer>')
                self.assertEqual(len(result['usage_records']), 2)
                self.assertNotIn(HIDDEN, json.dumps(result))
                self.assertEqual(stages.read(root / 'attempts/001/response.json')['choices'][0]['finish_reason'], 'length')
                self.assertTrue(stages.read(root / 'attempts/001/error.json')['retryable'])
                self.assertEqual(actor.read_completed(data.case('synthetic:000'), SKILL, root, p.ACTOR), result)
                actor.execute(data.case('synthetic:000'), SKILL, root, transport)
                self.assertEqual(transport.calls, 2)

    def test_mixed_technical_errors_and_length_share_six_slots(self):
        case = Dataset(self.root / 'data', 1).case('synthetic:000')
        seen = []
        def generate(messages, directory):
            seen.append(deepcopy(messages))
            if len(seen) in (1, 3):
                raise RequestFailure('Synthetic network error')
            return response(None, 'length') if len(seen) < 6 else response()
        transport = Transport(fn=generate)
        with patch.object(actor.time, 'sleep') as waiting:
            result = actor.execute(case, SKILL, self.root / 'mixed', transport)
        self.assertEqual(result['api_requests'], 6)
        self.assertEqual(seen, [seen[0]] * 6)
        self.assertEqual(waiting.call_args_list, [call(float(n)) for n in range(1, 6)])
        self.assertEqual(len(result['usage_records']), 6)

    def test_exhaustion_and_resume_never_issue_seventh_request_or_score(self):
        case = Dataset(self.root / 'data', 1).case('synthetic:000')
        root = self.root / 'exhausted'
        transport = Transport(fn=lambda m, d: response('<answer>A</answer>', 'length'))
        for _ in range(2):
            with self.assertRaisesRegex(RequestFailure, 'budget exhausted'):
                actor.execute(case, SKILL, root, transport)
            self.assertEqual(transport.calls, 6)
            self.assertFalse((root / 'result.json').exists())
            self.assertFalse((root / 'trajectory.json').exists())
        self.assertEqual(len(list((root / 'attempts').glob('*/error.json'))), 6)

    def test_saved_length_response_recovers_without_resending_used_slot(self):
        case = Dataset(self.root / 'data', 1).case('synthetic:000')
        for kind in ('response', 'http'):
            root = self.root / kind
            raw = response(None, 'length')
            def interrupt(messages, slot):
                if kind == 'http':
                    stages.save(slot / 'http_status.json', {'status_code': 200})
                    (slot / 'http_response.txt').write_text(json.dumps(raw))
                else:
                    stages.save(slot / 'response.json', raw)
                raise KeyboardInterrupt()
            transport = Transport(fn=interrupt)
            with self.assertRaises(KeyboardInterrupt):
                actor.execute(case, SKILL, root, transport)
            transport.fn = None
            result = actor.execute(case, SKILL, root, transport)
            self.assertEqual(transport.calls, 2)
            self.assertEqual(result['api_requests'], 2)
            self.assertTrue(stages.read(root / 'attempts/001/error.json')['retryable'])
            self.assertEqual(result['usage_records'][0], actor.usage_view(raw))

    def test_interrupted_retry_wait_preserves_spent_slots(self):
        case = Dataset(self.root / 'data', 1).case('synthetic:000')
        root = self.root / 'wait'
        transport = Transport(fn=lambda m, d: response(None, 'length'))
        with patch.object(actor.time, 'sleep', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                actor.execute(case, SKILL, root, transport)
        transport.fn = None
        self.assertEqual(actor.execute(case, SKILL, root, transport)['api_requests'], 2)
        self.assertEqual(transport.calls, 2)

    def test_length_cannot_enter_fact_or_pair_contract(self):
        truncated = record(finish='length', content='<answer>A</answer>')
        self.reject(facts.validate_envelope, truncated)
        run = facts.build_facts([record()])['facts']['runs'][0]
        run['outcome']['termination'] = 'length'
        self.reject(facts.validate_run, run)

    def test_old_actor_policy_is_rejected_before_any_request(self):
        case = Dataset(self.root / 'data', 1).case('synthetic:000')
        root = self.root / 'old'
        transport = Transport()
        actor.execute(case, SKILL, root, transport)
        signature = stages.read(root / 'signature.json')
        signature['actor'].pop('retry_policy')
        stages.save(root / 'signature.json', signature)
        self.reject(actor.execute, case, SKILL, root, transport)
        self.assertEqual(transport.calls, 1)

    def test_campaign_and_synthetic_test_use_final_stop_response_only(self):
        from . import test_offline as original
        from .test_actor_recovery import TestDataset
        from .support import config
        from src.skill_evolution.v27 import evolution, evaluation
        from src.skill_evolution.v27.benchmark import using_benchmark
        from src.skill_evolution.v27.benchmarks.lmb.adapter import LMBAdapter

        def generate(messages, directory):
            if directory.name == '001' and directory.parent.parent.name == p.digest('synthetic:000'):
                return response('<answer>A</answer>', 'length')
            return response('<answer>B</answer>')
        transport = Transport(fn=generate)
        adapter = LMBAdapter(Dataset(self.root / 'train_data', 1), transport, gate_metric=p.EM_GATE)
        method, _ = original.CampaignTests.generator(self, no_change='diagnosis')
        root = self.root / 'campaign'
        with using_benchmark(adapter):
            evolution.run_campaign(root, config=config(adapter), generate=method)
            self.assertEqual(transport.calls, 2)
            archived = stages.read(next((root / 'rounds/R01/parent_runs').rglob('trajectory.json')))
            self.assertEqual(archived['execution']['content'], '<answer>B</answer>')
            self.assertEqual(archived['execution']['metrics']['em'], 0)
            evolution.run_campaign(root, generate=method, resume=True)
            self.assertEqual(transport.calls, 2)

        dataset = TestDataset(self.root / 'test_data')
        transport = Transport(fn=generate)
        adapter = LMBAdapter(dataset, transport)
        skill = self.root / 'skill.md'; skill.write_text(SKILL)
        with using_benchmark(adapter), patch.object(evaluation, 'TEST_IDS', tuple(dataset.rows)):
            report = evaluation.run_evaluation(self.root / 'test', adapter=adapter, skill_file=skill)
            self.assertEqual(report['completed'], 124)
            self.assertEqual(report['actor_requests'], 125)
            self.assertEqual(transport.calls, 125)
            self.assertEqual(evaluation.run_evaluation(self.root / 'test', adapter=adapter,
                skill_file=skill, resume=True), report)
            self.assertEqual(transport.calls, 125)
