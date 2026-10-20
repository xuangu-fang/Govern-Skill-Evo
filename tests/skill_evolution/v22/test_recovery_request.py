"""Explicit classification recovery budgets; all requests use a fake session."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import object_digest, write_record
from src.skill_evolution.v22.continual_verify import _calls
from src.skill_evolution.v22.model_call import semantic_call
from src.skill_evolution.v22.verify_round import verify_call


class FakeResponse:
    ok, status_code = True, 200

    def __init__(self, finish_reason="stop"):
        self.finish_reason = finish_reason

    def json(self):
        return {"model": "deepseek-v4-pro", "choices": [{"finish_reason": self.finish_reason,
                "message": {"content": "{}"}}], "usage": {"total_tokens": 3}}


class FakeSession:
    def __init__(self, finish_reason="stop"):
        self.calls, self.finish_reason = [], finish_reason

    def post(self, endpoint, **kwargs):
        self.calls.append((endpoint, deepcopy(kwargs)))
        return FakeResponse(self.finish_reason)


class RecoveryRequestTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "call.json"
        self.messages = [{"role": "system", "content": "Frozen classification prompt."},
                         {"role": "user", "content": "{}"}]
        self.session = FakeSession()

    def call(self, stage="classification", **budget):
        return semantic_call(stage, self.messages, session=self.session,
            endpoint="https://fixture.invalid", key="synthetic", model="deepseek-v4-pro",
            output=self.path, **budget)

    def verify(self, stage="classification", document=None, **budget):
        return verify_call(self.path, stage, "deepseek-v4-pro", self.messages, document, **budget)

    def test_default_parameters_remain_16384_and_300_and_old_archives_still_verify(self):
        self.assertEqual(self.call(stage="diagnosis"), "{}")
        request = self.session.calls[0][1]
        self.assertEqual(request["json"]["max_tokens"], 16384)
        self.assertEqual(request["timeout"], (10, 300))
        self.verify(stage="diagnosis", document={})
        record = json.loads(self.path.read_text())
        record.pop("request_profile")
        write_record(self.path, record)
        self.verify(stage="diagnosis", document={})

    def test_classification_override_is_recorded_before_request_hashing(self):
        self.call(max_tokens=32768, timeout_seconds=600)
        request = self.session.calls[0][1]
        self.assertEqual(request["timeout"], (10, 600))
        self.assertEqual(request["json"]["max_tokens"], 32768)
        record = json.loads(self.path.read_text())
        self.assertEqual(record["request_profile"], {"max_tokens": 32768, "timeout_seconds": 600})
        attempt = record["steps"][0]["transport_attempts"][0]
        self.assertEqual(attempt["request_sha256"], object_digest(request["json"]))
        self.assertEqual(attempt["request_parameters"],
                         {key: value for key, value in request["json"].items() if key != "messages"})
        self.verify(document={}, max_tokens=32768, timeout_seconds=600)
        with self.assertRaisesRegex(ValueError, "profile"):
            self.verify(document={})
        with self.assertRaisesRegex(ValueError, "profile"):
            self.verify(document={}, max_tokens=32768, timeout_seconds=300)

    def test_unsupported_budget_or_other_stage_override_stops_before_dispatch(self):
        for stage, budget in (("classification", {"max_tokens": 65536}),
                              ("classification", {"timeout_seconds": 601}),
                              ("classification", {"max_tokens": 32768.0}),
                              ("diagnosis", {"max_tokens": 32768}),
                              ("main_editor", {"timeout_seconds": 600})):
            with self.subTest(stage=stage, budget=budget), self.assertRaisesRegex(ValueError, "budget"):
                self.call(stage=stage, **budget)
        self.assertEqual(self.session.calls, [])
        self.assertFalse(self.path.exists())

    def test_nondefault_missing_profile_and_tampered_request_are_rejected(self):
        self.call(max_tokens=32768, timeout_seconds=600)
        original = json.loads(self.path.read_text())
        missing = deepcopy(original)
        missing.pop("request_profile")
        write_record(self.path, missing)
        with self.assertRaisesRegex(ValueError, "profile"):
            self.verify(document={}, max_tokens=32768, timeout_seconds=600)
        changed = deepcopy(original)
        changed["steps"][0]["transport_attempts"][0]["request_parameters"]["max_tokens"] = 16384
        write_record(self.path, changed)
        with self.assertRaisesRegex(ValueError, "parameters/body"):
            self.verify(document={}, max_tokens=32768, timeout_seconds=600)

    def test_truncated_response_is_still_rejected_and_preserved_without_retry(self):
        self.session = FakeSession("length")
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.call(max_tokens=32768, timeout_seconds=600)
        self.assertEqual(len(self.session.calls), 1)
        record = json.loads(self.path.read_text())
        self.assertEqual(record["status"], "error")
        self.assertEqual(record["steps"][0]["model_response"]["finish_reason"], "length")
        self.verify(max_tokens=32768, timeout_seconds=600)  # Failed transport evidence remains auditable.
        with self.assertRaises(ValueError):
            self.verify(document={}, max_tokens=32768, timeout_seconds=600)

    def test_call_archive_requires_explicit_classification_budget(self):
        self.path = self.root / "calls/classification.json"
        self.path.parent.mkdir()
        self.call(max_tokens=32768, timeout_seconds=600)
        for directory in ("messages", "inputs", "raw_outputs"):
            (self.root / directory).mkdir()
        write_record(self.root / "messages/classification.json", self.messages)
        write_record(self.root / "inputs/classification.json", {})
        write_record(self.root / "grouping_input.json", {"model_input": {}})
        write_record(self.root / "raw_outputs/classification.json", {})
        (self.root / "raw_outputs/classification.txt").write_text("{}")
        plan = {"rounds": [{"stage_calls_max": {"classification": 1}, "semantic_calls_max": 1}],
                "models": {"evolution": "deepseek-v4-pro"},
                "budget": {"evolution_input_unicode_chars_max": 400000}}
        frozen = {"system_prompts": {"classification": {"text": self.messages[0]["content"]}}}
        row = {"round": 1, "stages": ["classification"]}
        with self.assertRaisesRegex(ValueError, "profile"):
            _calls(self.root, row, plan, frozen, True)
        self.assertEqual(_calls(self.root, row, plan, frozen, True,
            classification_max_tokens=32768, classification_timeout_seconds=600), 1)

    def test_memory_recovery_uses_declared_64k_budget_without_changing_messages(self):
        self.call(stage="post_gate_learning", max_tokens=65536, timeout_seconds=600)
        request = self.session.calls[0][1]
        self.assertEqual(request["json"]["max_tokens"], 65536)
        self.assertEqual(request["json"]["messages"], self.messages)
        self.assertEqual(request["timeout"], (10, 600))
        self.verify(stage="post_gate_learning", document={}, max_tokens=65536, timeout_seconds=600)
        with self.assertRaises(ValueError):
            self.verify(stage="post_gate_learning", document={})

    def test_memory_recovery_truncation_remains_a_failure_without_semantic_retry(self):
        self.session = FakeSession("length")
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.call(stage="post_gate_learning", max_tokens=65536, timeout_seconds=600)
        self.assertEqual(len(self.session.calls), 1)
        with self.assertRaises(ValueError):
            self.verify(stage="post_gate_learning", document={}, max_tokens=65536, timeout_seconds=600)


if __name__ == "__main__":
    unittest.main()
