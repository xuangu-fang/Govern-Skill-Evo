"""Actor truncation is a durable technical failure, never optimization evidence."""
from copy import deepcopy
import json
from unittest.mock import call, patch

from src.skill_evolution.v27 import stages
from src.skill_evolution.v27_1.lmb import actor, protocol as p
from src.skill_evolution.v27.transport import RequestFailure
from .runtime_support import Base
from .runtime_support import HIDDEN, SKILL, Transport, response
from .support import PlainDataset
from .test_editor import offline

def Dataset(root, size): return PlainDataset(rounds=1, size=size)


class LengthRetryTests(Base):
    def setUp(self):
        super().setUp(); offline(self)

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
                result = actor.execute(data.case('train:000'), SKILL, root, transport)
                self.assertEqual(seen, [result['initial_messages']] * 2)
                self.assertEqual(result['api_requests'], 2)
                self.assertEqual(result['termination'], 'stop')
                self.assertEqual(result['metrics']['em'], 0)  # Correct truncated answer was not selected.
                self.assertEqual(result['content'], '<answer>B</answer>')
                self.assertEqual(len(result['usage_records']), 2)
                self.assertNotIn(HIDDEN, json.dumps(result))
                self.assertEqual(stages.read(root / 'attempts/001/response.json')['choices'][0]['finish_reason'], 'length')
                self.assertTrue(stages.read(root / 'attempts/001/error.json')['retryable'])
                self.assertEqual(actor.read_completed(data.case('train:000'), SKILL, root, p.ACTOR), result)
                actor.execute(data.case('train:000'), SKILL, root, transport)
                self.assertEqual(transport.calls, 2)

    def test_mixed_technical_errors_and_length_share_six_slots(self):
        case = Dataset(self.root / 'data', 1).case('train:000')
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
        case = Dataset(self.root / 'data', 1).case('train:000')
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
        case = Dataset(self.root / 'data', 1).case('train:000')
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
        case = Dataset(self.root / 'data', 1).case('train:000')
        root = self.root / 'wait'
        transport = Transport(fn=lambda m, d: response(None, 'length'))
        with patch.object(actor.time, 'sleep', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                actor.execute(case, SKILL, root, transport)
        transport.fn = None
        self.assertEqual(actor.execute(case, SKILL, root, transport)['api_requests'], 2)
        self.assertEqual(transport.calls, 2)

    def test_old_actor_policy_is_rejected_before_any_request(self):
        case = Dataset(self.root / 'data', 1).case('train:000')
        root = self.root / 'old'
        transport = Transport()
        actor.execute(case, SKILL, root, transport)
        signature = stages.read(root / 'signature.json')
        signature['actor'].pop('retry_policy')
        stages.save(root / 'signature.json', signature)
        self.reject(actor.execute, case, SKILL, root, transport)
        self.assertEqual(transport.calls, 1)

