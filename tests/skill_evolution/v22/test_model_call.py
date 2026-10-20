"""Method calls preserve failed and truncated attempts without semantic retry."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.skill_evolution.v22.model_call import semantic_call


class SemanticCallTests(unittest.TestCase):
    def test_truncated_output_is_preserved_but_not_released(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "call.json"
            session = mock.Mock()
            session.post.return_value.status_code = 200
            session.post.return_value.ok = True
            session.post.return_value.json.return_value = {
                "model": "test", "choices": [{"message": {"content": '{"partial":'}, "finish_reason": "length"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8}}
            with self.assertRaisesRegex(ValueError, "truncated"):
                semantic_call("diagnosis", [{"role": "system", "content": "test"}], session=session,
                              endpoint="https://private.invalid", key="private-secret", model="test", output=output)
            record = json.loads(output.read_text())
            self.assertEqual(record["status"], "error")
            self.assertEqual(record["steps"][0]["model_response"]["content"], '{"partial":')
            self.assertEqual(record["steps"][0]["transport_attempts"][0]["usage"]["total_tokens"], 8)
            self.assertEqual(session.post.call_count, 1)
            self.assertNotIn("private-secret", output.read_text())
            self.assertNotIn("private.invalid", output.read_text())

    def test_network_failure_retains_exact_request_and_unknown_usage(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "call.json"
            messages = [{"role": "system", "content": "test"}, {"role": "user", "content": "observations"}]
            session = mock.Mock()
            session.post.side_effect = TimeoutError("private transport contents")
            with self.assertRaises(TimeoutError):
                semantic_call("editor", messages, session=session, endpoint="https://private.invalid",
                              key="private-secret", model="test", output=output)
            record = json.loads(output.read_text())
            self.assertEqual(record["steps"][0]["messages"], messages)
            self.assertNotIn("model_response", record["steps"][0])
            self.assertIsNone(record["steps"][0]["transport_attempts"][0]["usage"])
            self.assertNotIn("private transport contents", output.read_text())
            self.assertEqual(session.post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
