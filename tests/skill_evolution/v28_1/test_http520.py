"""520 recovery keeps the six-slot budget and reuses completed Test journals."""
from unittest.mock import Mock

from src.skill_evolution.v27.transport import RequestFailure, http_failure as legacy_http_failure
from src.skill_evolution.v28 import evaluation, stages
from src.skill_evolution.v28.benchmarks.searchqa import actor
from tests.skill_evolution.v28.runtime_support import Base, response, snapshot
from tests.skill_evolution.v28_1.test_offline import bind, no_hashes


class HTTP520Tests(Base):
    def test_only_opted_in_520_is_retryable_and_quota_stays_terminal(self):
        self.assertFalse(actor.http_failure(520, '').retryable)
        self.assertTrue(actor.http_failure(520, '', retry_http_520=True).retryable)
        for body in ('insufficient_quota', 'quota_exceeded'):
            self.assertFalse(actor.http_failure(520, body, retry_http_520=True).retryable)
        self.assertFalse(actor.http_failure(403, '', retry_http_520=True).retryable)
        for status in (400, 401, 403, 408, 429, 500, 501, 502, 503, 504, 520, 521):
            for body in ('', 'insufficient_quota', 'quota_exceeded'):
                self.assertEqual(actor.http_failure(status, body).retryable,
                                 legacy_http_failure(status, body).retryable)

    def test_live_and_archived_http_classification_agree(self):
        session = Mock()
        session.post.return_value = Mock(status_code=520, text='', content=b'')
        factory = Mock()
        factory.return_value.__enter__ = Mock(return_value=session)
        factory.return_value.__exit__ = Mock(return_value=False)
        transport = actor.ChatTransport('synthetic-key', session_factory=factory, retry_http_520=True)
        slot = self.root / 'slot'; slot.mkdir()
        with self.assertRaises(RequestFailure) as live:
            transport([], slot)
        self.assertTrue(live.exception.retryable)
        with self.assertRaises(RequestFailure) as archived:
            actor.archived_response(slot, verify_hashes=False)
        self.assertTrue(archived.exception.retryable)
        with self.assertRaises(RequestFailure) as legacy:
            actor.archived_response(slot)
        self.assertFalse(legacy.exception.retryable)
        transport = actor.ChatTransport('synthetic-key', session_factory=factory)
        with self.assertRaises(RequestFailure) as legacy_live:
            transport([], slot)
        self.assertFalse(legacy_live.exception.retryable)

    def test_corrected_receipt_resumes_only_missing_task(self):
        data, transport, adapter, _ = bind(rounds=1, size=1, test_size=3)
        pending = data.splits['test'][-1]
        query = data.case(pending).payload['question']
        root = self.root / 'test'

        def fail_one(messages, slot):
            if query in messages[-1]['content']:
                (slot / 'http_response.txt').write_bytes(b'')
                stages.save(slot / 'http_status.json', {'status_code': 520})
                raise actor.http_failure(520, '')  # Original misclassification.
            return response()

        transport.fn = fail_one
        with no_hashes(), self.assertRaises(RequestFailure):
            evaluation.run_evaluation(root, adapter=adapter.actor_adapter, skill_file=None)
        folder = root / 'batch/actor' / adapter.actor_adapter.task_key(pending)
        completed = {p: snapshot(p) for p in folder.parent.iterdir()
                     if p.is_dir() and (p / 'result.json').exists()}
        self.assertEqual(len(completed), 2)
        error_file = folder / 'attempts/001/error.json'
        error = stages.read(error_file); self.assertFalse(error['retryable'])
        error['retryable'] = True; stages.save(error_file, error)
        before_calls = transport.calls
        transport.fn = None
        with no_hashes():
            report = evaluation.run_evaluation(root, adapter=adapter.actor_adapter, skill_file=None, resume=True)
        self.assertEqual(transport.calls - before_calls, 1)
        self.assertEqual(report['completed'], 3)
        self.assertEqual(stages.read(folder / 'result.json')['api_requests'], 2)
        for p, original in completed.items():
            self.assertEqual(snapshot(p), original)

    def test_repeated_520_does_not_reset_or_exceed_six_attempts(self):
        data, transport, _, _ = bind(rounds=1, size=1)
        case = data.case(data.batches[0][0])

        def fail(messages, slot):
            (slot / 'http_response.txt').write_bytes(b'')
            stages.save(slot / 'http_status.json', {'status_code': 520})
            raise actor.http_failure(520, '', retry_http_520=True)

        transport.fn = fail
        with no_hashes():
            for _ in range(2):
                with self.assertRaisesRegex(RequestFailure, 'budget exhausted'):
                    actor.execute(case, None, self.root / 'task', transport, verify_hashes=False)
                self.assertEqual(transport.calls, 6)
