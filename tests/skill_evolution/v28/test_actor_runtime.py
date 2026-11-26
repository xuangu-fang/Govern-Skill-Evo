import ast
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import call, patch

from src.skill_evolution.v27.transport import RequestFailure
from src.skill_evolution.v28.storage import read, save
from src.skill_evolution.v28.benchmarks.searchqa import actor, protocol as p
from .runtime_support import Base, Dataset, Transport, SKILL, HIDDEN, response, http_archive, snapshot


class ActorRuntimeTests(Base):
    def setUp(self):
        super().setUp()
        self.case = Dataset(1).case('synthetic:000')

    def test_native_v27_transport_and_archive_rules_unchanged(self):
        upstream = ast.parse((p.ROOT / 'src/skill_evolution/v27/benchmarks/lmb/actor.py').read_text())
        current = ast.parse(Path(actor.__file__).read_text())
        a = {n.name: ast.dump(n) for n in upstream.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        b = {n.name: ast.dump(n) for n in current.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        for name in ('parse_response', 'usage_view', 'request_record', 'archive_hashes',
                     'locked'):
            self.assertEqual(a[name], b[name], name)
        # validate_slot accepts v28.1 plain receipts; archived_response and
        # ChatTransport opt v28.1 into 520 retries. Default v28 behavior is
        # exercised by the archive/retry tests and test_http520 below.

    def test_length_variants_retry_same_request_and_keep_hidden_private(self):
        for i, content in enumerate((None, '', '<answer>New York City</answer>', 'unfinished')):
            with self.subTest(content=content):
                t = Transport(lambda m, d: response(content, 'length') if d.name == '001' else response('New York'))
                root = self.root / str(i)
                result = actor.execute(self.case, SKILL, root, t)
                self.assertEqual(t.seen, [result['initial_messages']] * 2)
                self.assertEqual(result['metrics'], {'em': 0, 'f1': .8})
                self.assertEqual(result['api_requests'], 2)
                self.assertNotIn(HIDDEN, json.dumps(result))
                self.assertIn(HIDDEN, (root / 'attempts/001/response.json').read_text())
                self.assertEqual(actor.read_completed(self.case, SKILL, root, p.ACTOR), result)
                self.assertEqual(actor.execute(self.case, SKILL, root, t), result)
                self.assertEqual(t.calls, 2)

    def test_mixed_failures_share_six_slots_and_linear_wait(self):
        def generate(messages, slot):
            if slot.name in ('001', '003'):
                raise RequestFailure('ConnectionError')
            return response(None, 'length') if slot.name < '006' else response()
        t = Transport(generate)
        result = actor.execute(self.case, SKILL, self.root / 'mixed', t)
        self.assertEqual(result['api_requests'], 6)
        self.assertEqual(t.seen, [t.seen[0]] * 6)
        self.assertEqual(self.sleep.call_args_list, [call(float(n)) for n in range(1, 6)])
        self.assertEqual(len(result['usage_records']), 6)

    def test_exhaustion_resume_never_adds_seventh_request_or_zero_score(self):
        t = Transport(lambda m, d: response('New York City', 'length'))
        root = self.root / 'exhausted'
        for _ in range(3):
            with self.assertRaisesRegex(RequestFailure, 'budget exhausted'):
                actor.execute(self.case, SKILL, root, t)
            self.assertEqual(t.calls, 6)
            self.assertFalse((root / 'result.json').exists())
        self.assertEqual(len(list((root / 'attempts').glob('*/error.json'))), 6)

    def test_normal_stop_never_retries_based_on_score_or_format(self):
        for i, content in enumerate(('', 'Berlin', '<answer>New York City', 'Reasoning\nNew York City')):
            t = Transport(lambda m, d: response(content))
            result = actor.execute(self.case, SKILL, self.root / str(i), t)
            self.assertEqual(result['api_requests'], 1)
            self.assertEqual(t.calls, 1)

    def test_refusal_and_tools_remain_terminal_after_resume(self):
        for i, raw in enumerate((response('x', refusal='no'), response('x', tool_calls=[{}]), response('x', 'content_filter'))):
            t = Transport(lambda m, d: raw)
            root = self.root / str(i)
            with self.assertRaises(RequestFailure) as caught:
                actor.execute(self.case, SKILL, root, t)
            self.assertFalse(caught.exception.retryable)
            self.reject(actor.execute, self.case, SKILL, root, t)
            self.assertEqual(t.calls, 1)
            self.assertFalse((root / 'result.json').exists())

    def test_saved_response_or_http_recovers_without_resending(self):
        for kind in ('response', 'http'):
            def interrupt(messages, slot):
                if kind == 'http':
                    http_archive(slot, response())
                else:
                    save(slot / 'response.json', response())
                raise KeyboardInterrupt()
            root, t = self.root / kind, Transport(interrupt)
            with self.assertRaises(KeyboardInterrupt):
                actor.execute(self.case, SKILL, root, t)
            t.fn = None
            result = actor.execute(self.case, SKILL, root, t)
            self.assertEqual(t.calls, 1)
            self.assertEqual(result['api_requests'], 1)

    def test_saved_length_response_recovers_then_uses_next_slot(self):
        def interrupt(m, slot):
            http_archive(slot, response(None, 'length'))
            raise KeyboardInterrupt()
        t, root = Transport(interrupt), self.root / 'saved_length'
        with self.assertRaises(KeyboardInterrupt):
            actor.execute(self.case, SKILL, root, t)
        t.fn = None
        self.assertEqual(actor.execute(self.case, SKILL, root, t)['api_requests'], 2)
        self.assertEqual(t.calls, 2)
        self.assertTrue(read(root / 'attempts/001/error.json')['retryable'])

    def test_unknown_request_consumes_attempt_and_prepared_slot_does_not(self):
        def interrupt(m, d):
            raise KeyboardInterrupt()
        t, root = Transport(interrupt), self.root / 'unknown'
        with self.assertRaises(KeyboardInterrupt):
            actor.execute(self.case, SKILL, root, t)
        t.fn = None
        self.assertEqual(actor.execute(self.case, SKILL, root, t)['api_requests'], 2)
        self.assertEqual(read(root / 'attempts/001/error.json')['status'], 'unknown')
        t, root = Transport(), self.root / 'prepared'
        original = actor.save
        def before_started(path, value):
            if path.name == 'request_started.json':
                raise KeyboardInterrupt()
            return original(path, value)
        with patch.object(actor, 'save', side_effect=before_started), self.assertRaises(KeyboardInterrupt):
            actor.execute(self.case, SKILL, root, t)
        self.assertEqual(t.calls, 0)
        self.assertEqual(actor.execute(self.case, SKILL, root, t)['api_requests'], 1)
        self.assertEqual(t.calls, 1)

    def test_interrupted_wait_does_not_reset_attempt_budget(self):
        t, root = Transport(lambda m, d: response(None, 'length')), self.root / 'wait'
        with patch.object(actor.time, 'sleep', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            actor.execute(self.case, SKILL, root, t)
        t.fn = None
        self.assertEqual(actor.execute(self.case, SKILL, root, t)['api_requests'], 2)
        self.assertEqual(t.calls, 2)

    def test_recovery_rejects_task_skill_model_protocol_and_gold_drift(self):
        t, root = Transport(), self.root / 'identity'
        actor.execute(self.case, SKILL, root, t)
        case = deepcopy(self.case)
        case.reference[0] = 'Berlin'
        for altered, skill in ((case, SKILL), (self.case, SKILL + '\n')):
            self.reject(actor.execute, altered, skill, root, t)
        t.config['max_tokens'] = 1
        self.reject(actor.execute, self.case, SKILL, root, t)
        t.config = deepcopy(p.ACTOR)
        changed = p.implementation_identity()
        changed['scorer'] = 'other'
        with patch.object(p, 'implementation_identity', return_value=changed):
            self.reject(actor.execute, self.case, SKILL, root, t)
        self.assertEqual(t.calls, 1)

    def test_completed_marker_blocks_lost_response_and_orphan_signature(self):
        t, root = Transport(), self.root / 'lost'
        actor.execute(self.case, SKILL, root, t)
        save(root / 'trajectory.json', {'marker': 'completed'})
        (root / 'result.json').unlink()
        (root / 'attempts/001/response.json').unlink()
        before = snapshot(root)
        self.reject(actor.execute, self.case, SKILL, root, t)
        self.assertEqual(t.calls, 1)
        self.assertEqual(snapshot(root), before)
        (root / 'trajectory.json').unlink()
        (root / 'signature.json').unlink()
        self.reject(actor.execute, self.case, SKILL, root, t)
        self.assertEqual(t.calls, 1)

    def test_malformed_http_and_network_receipts_are_revalidated(self):
        for kind in ('http', 'json', 'network'):
            def generate(m, slot):
                if slot.name != '001':
                    return response()
                if kind == 'network':
                    raise RequestFailure('ConnectionError')
                status, body = (503, 'temporary failure') if kind == 'http' else (200, 'invalid JSON')
                (slot / 'http_response.txt').write_text(body)
                save(slot / 'http_status.json', {'status_code': status})
                raise RequestFailure('HTTP 503' if kind == 'http' else 'Malformed API JSON')
            root, t = self.root / kind, Transport(generate)
            result = actor.execute(self.case, SKILL, root, t)
            self.assertEqual(actor.read_completed(self.case, SKILL, root, p.ACTOR), result)
            self.assertEqual(t.calls, 2)
            receipt = read(root / 'attempts/001/error.json')
            receipt['retryable'] = False
            save(root / 'attempts/001/error.json', receipt)
            self.reject(actor.read_completed, self.case, SKILL, root, p.ACTOR)

    def test_http_transport_settings_with_fake_session(self):
        class Reply:
            status_code = 200
            content = json.dumps(response()).encode()
            def json(self): return response()
        class Session:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def mount(self, prefix, adapter):
                self_test.assertEqual(adapter.max_retries.total, 0)
            def post(self, endpoint, **kwargs):
                requests_seen.append((endpoint, kwargs))
                return Reply()
        self_test, requests_seen = self, []
        t = actor.ChatTransport('synthetic-key', session_factory=Session)
        root = self.root / 'http'
        result = actor.execute(self.case, SKILL, root, t)
        self.assertEqual(result['api_requests'], 1)
        endpoint, kwargs = requests_seen[0]
        self.assertEqual(endpoint, p.ACTOR['endpoint'])
        self.assertEqual(kwargs['timeout'], (10, 300))
        self.assertFalse(kwargs['allow_redirects'])
        self.assertEqual(kwargs['json']['max_tokens'], 49152)
        self.assertNotIn('synthetic-key', json.dumps({k: v.decode() for k, v in snapshot(root).items()}))

    def test_same_journal_cannot_be_executed_concurrently(self):
        root, t = self.root / 'locked', Transport()
        with actor.locked(root):
            with self.assertRaises(BlockingIOError):
                actor.execute(self.case, SKILL, root, t)
        self.assertEqual(t.calls, 0)
