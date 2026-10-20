"""Rate-limit recovery must preserve the original model request."""

from unittest import TestCase, mock
from src.adapters.alfworld.run_task import chat_action


class RetryTests(TestCase):
    def test_rate_limit_retries_identical_messages_and_records_attempts(self):
        limited = mock.Mock(status_code=429, ok=False)
        success = mock.Mock(status_code=200, ok=True)
        success.json.return_value = {"choices": [{"message": {"content": "<action>look</action>"}, "finish_reason": "stop"}], "model": "test"}
        session = mock.Mock()
        session.post.side_effect = [limited, success]
        messages = [{"role": "user", "content": "task observation"}]
        with mock.patch("src.adapters.alfworld.run_task.time.sleep"):
            result = chat_action(session, "http://localhost/chat/completions", "test-key", "test", messages, 1024)
        self.assertEqual(result["api_attempts"], 2)
        self.assertEqual(session.post.call_args_list[0], session.post.call_args_list[1])

    def test_authentication_error_does_not_retry(self):
        session = mock.Mock()
        session.post.return_value = mock.Mock(status_code=401, ok=False)
        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            chat_action(session, "http://localhost/chat/completions", "test-key", "test", [], 1024)
        self.assertEqual(session.post.call_count, 1)
