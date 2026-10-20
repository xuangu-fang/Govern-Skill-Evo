"""Offline transport fixtures: no provider or ALFWorld environment is contacted."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.adapters.alfworld.response_archive import verify_response_archive
from src.adapters.alfworld.run_task_skill import RecordingSession
from src.adapters.alfworld.run_task_upstream import chat
from src.skill_evolution.v22.model_call import request_profile, semantic_call
from src.skill_evolution.v22.run_round import cost_summary
from src.skill_evolution.v22.verify_round import verify_call


MESSAGES = [{"role": "system", "content": "Synthetic transport fixture."}]


def response(status=200, payload=None, raw=None):
    result = mock.Mock()
    result.status_code, result.ok = status, 200 <= status < 400
    result.content = raw if raw is not None else json.dumps(payload).encode()
    result.json.side_effect = lambda: json.loads(result.content)
    return result


def completion(content='{"ok":true}', finish="stop", usage=None):
    return {"model": "fixture", "choices": [{"message": {"content": content,
            "reasoning_content": "synthetic reasoning"}, "finish_reason": finish}],
            "usage": usage or {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8,
                               "completion_tokens_details": {"reasoning_tokens": 2}}}


class StreamTransportTests(unittest.TestCase):
    def invoke(self, output, session, stage="diagnosis"):
        return semantic_call(stage, MESSAGES, session=session, endpoint="https://fixture.invalid",
                             key="secret-not-for-archive", model="fixture", output=output,
                             max_tokens=65536 if stage == "post_gate_learning" else 32768,
                             timeout_seconds=600, transport_policy="single_attempt")

    def check(self, output, document=None):
        verify_call(output, "diagnosis", "fixture", MESSAGES, document,
                    max_tokens=32768, timeout_seconds=600, transport_policy="single_attempt")

    def test_explicit_budgets_do_not_relax_legacy(self):
        for stage in ("classification", "diagnosis", "fusion", "main_editor", "post_gate_learning"):
            limit = 65536 if stage == "post_gate_learning" else 32768
            self.assertEqual(request_profile(stage, limit, 600, transport_policy="single_attempt"),
                             {"max_tokens": limit, "timeout_seconds": 600})
        with self.assertRaises(ValueError):
            request_profile("diagnosis", 32768, 600)
        with self.assertRaises(ValueError):
            request_profile("post_gate_learning", 32768, 600, transport_policy="single_attempt")
        self.assertEqual(request_profile("diagnosis"), {"max_tokens": 16384, "timeout_seconds": 300})

    def test_single_success_archives_raw_and_refuses_overwrite(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "call.json"
            raw = response(payload=completion())
            session = mock.Mock(); session.post.return_value = raw
            self.assertEqual(self.invoke(output, session), '{"ok":true}')
            self.check(output, {"ok": True})
            kwargs = session.post.call_args.kwargs
            self.assertFalse(kwargs["allow_redirects"])
            self.assertEqual(kwargs["timeout"], (10, 600))
            self.assertEqual(kwargs["json"]["max_tokens"], 32768)
            record = json.loads(output.read_text())
            attempt = record["steps"][0]["transport_attempts"][0]
            saved = output.parent / attempt["raw_response"]["path"]
            self.assertEqual(saved.read_bytes(), raw.content)
            self.assertEqual(attempt["usage"]["completion_tokens_details"]["reasoning_tokens"], 2)
            self.assertNotIn("secret-not-for-archive", output.read_text())
            with self.assertRaises(FileExistsError):
                self.invoke(output, session)
            self.assertEqual(session.post.call_count, 1)
            saved.write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "changed"):
                self.check(output, {"ok": True})

    def test_http_failure_is_single_attempt_and_usage_is_accounted(self):
        for status in (429, 500):
            with self.subTest(status=status), TemporaryDirectory() as directory:
                root = Path(directory); (root / "calls").mkdir()
                output = root / "calls" / "diagnosis.json"
                usage = {"prompt_tokens": 7, "completion_tokens": 2, "total_tokens": 9}
                session = mock.Mock(); session.post.return_value = response(status, {"error": "fixture", "usage": usage})
                with self.assertRaises(RuntimeError):
                    self.invoke(output, session)
                self.assertEqual(session.post.call_count, 1)
                self.check(output)
                totals = cost_summary([], [], root)
                self.assertEqual(totals["reported_usage"], usage)
                self.assertEqual(totals["requests_with_unknown_usage"], 0)

    def test_malformed_provider_json_preserves_body_and_unknown_cost(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); (root / "calls").mkdir()
            output = root / "calls" / "diagnosis.json"
            session = mock.Mock(); session.post.return_value = response(raw=b"<failed upstream>")
            with self.assertRaises(json.JSONDecodeError):
                self.invoke(output, session)
            self.check(output)
            self.assertEqual(session.post.call_count, 1)
            record = json.loads(output.read_text()); attempt = record["steps"][0]["transport_attempts"][0]
            self.assertEqual((output.parent / attempt["raw_response"]["path"]).read_bytes(), b"<failed upstream>")
            totals = cost_summary([], [], root)
            self.assertEqual(totals["requests_with_unknown_usage"], 1)
            self.assertEqual(totals["http_attempts_with_unknown_usage"], 1)
            self.assertEqual(totals["reported_usage"], {})

    def test_truncation_and_invalid_visible_json_are_not_retried(self):
        for finish in ("stop", "length"):
            with self.subTest(finish=finish), TemporaryDirectory() as directory:
                output = Path(directory) / "call.json"
                session = mock.Mock(); session.post.return_value = response(payload=completion('{"partial":', finish))
                if finish == "length":
                    with self.assertRaisesRegex(ValueError, "truncated"):
                        self.invoke(output, session)
                else:
                    self.assertEqual(self.invoke(output, session), '{"partial":')
                self.assertEqual(session.post.call_count, 1)
                self.check(output)
                record = json.loads(output.read_text())
                self.assertEqual(record["steps"][0]["model_response"]["content"], '{"partial":')

    def test_actor_retries_archive_each_usage_without_double_counting(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); (root / "calls").mkdir()
            output = root / "trajectory.json"
            record = {"steps": [{"messages": MESSAGES}]}
            failure_usage = {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}
            session = mock.Mock(); session.post.side_effect = [
                response(429, {"usage": failure_usage}), response(500, {"usage": failure_usage}),
                response(payload=completion())]
            recording = RecordingSession(session, record, output, archive_responses=True)
            with mock.patch("src.adapters.alfworld.run_task_upstream.time.sleep"):
                result = chat(recording, "https://fixture.invalid", "secret", "fixture", MESSAGES)
            record["steps"][0]["model_response"] = result
            self.assertEqual(result["api_attempts"], 3)
            self.assertEqual(record["response_archival"], "raw_http_body_v1")
            for attempt in record["steps"][0]["transport_attempts"]:
                verify_response_archive(output, attempt)
            self.assertTrue(all(call.kwargs["allow_redirects"] is False for call in session.post.call_args_list))
            totals = cost_summary([record], [], root)
            self.assertEqual(totals["reported_usage"], {"prompt_tokens": 7, "completion_tokens": 7,
                                                       "total_tokens": 14, "reasoning_tokens": 2})
            self.assertEqual(totals["http_attempts"], 3)
            self.assertEqual(totals["requests_with_unknown_usage"], 0)

    def test_reasoning_subset_is_new_mode_only_and_missing_is_not_zero(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); (root / "calls").mkdir()
            reported = completion()["usage"]
            legacy = {"steps": [{"model_response": {"usage": reported},
                                  "transport_attempts": [{"usage": reported}]}]}
            self.assertNotIn("reasoning_tokens", cost_summary([legacy], [], root)["reported_usage"])
            archived = {"steps": [{"response_archive": True,
                "transport_attempts": [{"usage": reported}, {"usage": reported}, {"usage": None}]}]}
            total = cost_summary([archived], [], root)
            self.assertEqual(total["reported_usage"]["reasoning_tokens"], 4)
            self.assertEqual(total["reported_usage"]["completion_tokens"], 10)
            self.assertEqual(total["reported_usage"]["total_tokens"], 16)
            self.assertEqual(total["http_attempts_with_unknown_usage"], 1)

    def test_new_recording_rejects_redirect_and_network_failure_stays_unknown(self):
        for reply in (response(302, {"redirect": True}), TimeoutError("private transport error")):
            with self.subTest(reply=type(reply).__name__), TemporaryDirectory() as directory:
                output = Path(directory) / "call.json"
                session = mock.Mock()
                if isinstance(reply, Exception):
                    session.post.side_effect = reply
                else:
                    session.post.return_value = reply
                with self.assertRaises((RuntimeError, TimeoutError)):
                    self.invoke(output, session)
                self.check(output)
                self.assertEqual(session.post.call_count, 1)
                self.assertNotIn("private transport error", output.read_text())


if __name__ == "__main__":
    unittest.main()
