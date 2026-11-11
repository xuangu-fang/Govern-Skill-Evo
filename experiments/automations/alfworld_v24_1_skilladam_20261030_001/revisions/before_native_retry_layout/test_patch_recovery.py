"""Mock HTTP tests: budgets, payload identity, saved evidence and terminal grants."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from openai import OpenAI, DefaultHttpxClient
import recover_iteration0_patch as recovery


class RecoveryTests(unittest.TestCase):
    def exercise(self, statuses, *, expect_success=False, consumed=0, mutate_payload=False):
        plan = recovery.read(recovery.HERE / 'plan.json')
        auth = recovery.read(recovery.HERE / 'patch_recovery_authorization.json')
        original = recovery.ROOT / auth['failed_call_directory']
        signature = recovery.read(original / 'request.json')
        cfg = recovery.read(recovery.ROOT / plan['jobs']['skilladam']['experiment'] / 'skilladam.json')
        empty = recovery.read(original / 'response.json')
        good = copy.deepcopy(empty)
        good['choices'][0]['finish_reason'] = 'stop'
        good['choices'][0]['message']['content'] = json.dumps({'reasoning': 'mock valid result', 'patch': ''})
        seen = []
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ledger = root / 'ledger.json'
            recovery.save(ledger, {'schema': 1, 'extra_requests_consumed': consumed, 'grants': {
                recovery.GRANT: {'limit': 3, 'consumed': consumed, 'status': 'authorized', 'requests': []}}})

            def handler(request):
                current = recovery.read(ledger)['grants'][recovery.GRANT]
                self.assertEqual(current['consumed'], len(seen) + 1)
                self.assertEqual(json.loads(request.content), recovery.read(original / 'http_request_01.json')['body'])
                status = statuses[len(seen)]
                seen.append(status)
                if status == 'good':
                    return httpx.Response(200, json=good)
                if status == 'empty':
                    return httpx.Response(200, json=empty)
                return httpx.Response(status, json={'error': {'message': 'mock error', 'type': 'mock'}})

            def factory(**options):
                self.assertEqual(options['max_retries'], 0)
                hooks = options['http_client'].event_hooks
                options['http_client'].close()
                options['http_client'] = DefaultHttpxClient(event_hooks=hooks, transport=httpx.MockTransport(handler))
                return OpenAI(**options)

            if mutate_payload:
                signature['payload']['max_tokens'] += 1
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-test-placeholder'}):
                if expect_success:
                    result = recovery.recover(signature, cfg, auth, ledger_path=ledger,
                        recovery_root=root / 'evidence', client_factory=factory)
                    self.assertTrue(result.text)
                    self.assertEqual(len(result.usage), len(seen) + 1)
                else:
                    with self.assertRaises((recovery.GrantExhausted, ValueError)):
                        recovery.recover(signature, cfg, auth, ledger_path=ledger,
                            recovery_root=root / 'evidence', client_factory=factory)
                # An already spent or terminal grant cannot receive another set.
                if seen:
                    with self.assertRaises(ValueError):
                        recovery.recover(signature, cfg, auth, ledger_path=ledger,
                            recovery_root=root / 'evidence', client_factory=factory)
            return seen, recovery.read(ledger)['grants'][recovery.GRANT]

    def test_success_stops_after_one(self):
        seen, grant = self.exercise(['good'], expect_success=True)
        self.assertEqual(seen, ['good']); self.assertEqual(grant['status'], 'succeeded')

    def test_empty_then_success(self):
        seen, grant = self.exercise(['empty', 'good'], expect_success=True)
        self.assertEqual(grant['consumed'], 2)

    def test_three_empty_responses_exhaust(self):
        seen, grant = self.exercise(['empty'] * 3)
        self.assertEqual(len(seen), 3); self.assertEqual(grant['status'], 'exhausted')

    def test_500_counts_physical_requests(self):
        seen, grant = self.exercise([500] * 3)
        self.assertEqual(len(seen), 3); self.assertEqual(grant['consumed'], 3)

    def test_auth_error_stops_immediately(self):
        seen, grant = self.exercise([401])
        self.assertEqual(seen, [401]); self.assertEqual(grant['status'], 'blocked')

    def test_previous_consumption_not_reset(self):
        seen, grant = self.exercise([], consumed=1)
        self.assertEqual(seen, []); self.assertEqual(grant['consumed'], 1)

    def test_changed_payload_refused(self):
        seen, grant = self.exercise([], mutate_payload=True)
        self.assertEqual(seen, []); self.assertEqual(grant['consumed'], 0)


if __name__ == '__main__':
    unittest.main()
