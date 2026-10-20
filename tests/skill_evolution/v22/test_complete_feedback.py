"""Explicit final-feedback completion, using mock HTTP and synthetic executions.

No tests in this file call a model service or run an Agent environment.
"""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.adapters.alfworld.skill_runtime import digest
from src.skill_evolution.v22 import complete_feedback
from src.skill_evolution.v22.compact_cycle import run_cycle, verify_cycle
from src.skill_evolution.v22.model_call import semantic_call
from tests.skill_evolution.v22.test_compact_cycle import (
    cycle_plan, draft, editor_output, execute_fixture, fusion_output,
    learning_output, legacy_source, read, recorded_mock_call,
)
from tests.skill_evolution.v22.test_verify_round import change


class FeedbackCompletionTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        # Completion plans use repository-relative paths; isolate that root only.
        patcher = mock.patch.object(complete_feedback, "REPO_ROOT", self.directory)
        patcher.start()
        self.addCleanup(patcher.stop)
        source = legacy_source(self.directory / "source")
        self.executions = []

        def execute(parent, skill, root):
            self.executions.append(str(root))
            return execute_fixture(parent, skill, root)

        def failed_request(stage, messages, output):
            session = mock.Mock()
            session.post.side_effect = TimeoutError("synthetic transport failure")
            return semantic_call(stage, messages, session=session, endpoint="https://fixture.invalid",
                                 key="fixture-not-a-secret", model="deepseek-v4-pro", output=output)

        self.first = self.directory / "first_unknown_attempt"
        first = run_cycle(source, self.first, cycle_plan(), failed_request, execute)
        self.assertEqual(first["status"], "error")
        self.assertEqual(first["cost"]["requests_with_unknown_usage"], 1)
        self.assertEqual(first["cost"]["reported_usage"], {})
        self.assertTrue(verify_cycle(self.first)["artifact_valid"])

        def fail_only_final(stage, messages, output):
            payload = json.loads(messages[1]["content"])
            if stage == "learn_final":
                value = '{"unfinished":'
            elif stage == "learn_initial":
                value = learning_output(payload)
            elif stage == "diagnosis":
                value = draft()
            elif stage == "fusion":
                value = fusion_output(payload)
            else:
                value = editor_output(payload)
            return recorded_mock_call(stage, messages, output, value, "deepseek-v4-pro")

        self.source = self.directory / "five_call_recovery"
        failed = run_cycle(source, self.source, cycle_plan(), fail_only_final, execute)
        self.assertEqual(failed["status"], "error", failed)
        self.assertEqual(failed["active_stage"], "learn_final")
        self.assertEqual(failed["cost"]["semantic_calls"], 5)
        self.assertEqual(len(self.executions), 2)
        self.assertTrue(verify_cycle(self.source)["artifact_valid"])
        prior_paths = [self.first / "report.json", self.source / "report.json"]
        self.plan = {
            "schema_version": "v22.feedback_completion_plan.v1",
            "source_cycle": str(self.source.relative_to(self.directory)), "semantic_calls_max": 1,
            "cumulative_semantic_calls_max": 7,
            "new_environment_episodes": 0, "semantic_retries": 0, "evolution_model": "deepseek-v4-pro",
            "prior_reports": [{"path": str(path.relative_to(self.directory)), "sha256": digest(path.read_bytes())}
                              for path in prior_paths],
        }

    def complete(self, name="completion", invalid_ref=False):
        payload = read(self.source / "inputs/learn_final.json")
        value = learning_output(payload, final=True)
        if invalid_ref:
            value["findings"][0]["refs"] = ["C1:999"]
        calls = []

        def generate(stage, messages, output):
            calls.append(stage)
            return recorded_mock_call(stage, messages, output, value, "deepseek-v4-pro")

        root = self.directory / name
        result = complete_feedback.run_completion(self.source, root, deepcopy(self.plan), generate)
        self.assertEqual(calls, [complete_feedback.STAGE])
        return root, result

    def test_success_is_separate_from_failed_cycle_and_cost_keeps_every_attempt(self):
        original = {path: path.read_bytes() for path in self.source.rglob("*") if path.is_file()}
        root, result = self.complete()
        self.assertEqual(result["status"], "feedback_ready", result)
        self.assertTrue(complete_feedback.verify_completion(root)["feedback_ready"])
        self.assertEqual(original, {path: path.read_bytes() for path in original})
        self.assertEqual(read(self.source / "report.json")["status"], "error")
        self.assertFalse((self.source / "memory_final.json").exists())
        self.assertFalse(verify_cycle(self.source)["cycle_complete"])
        self.assertEqual(len(self.executions), 2)
        incremental, cumulative = result["cost"]["incremental"], result["cost"]["cumulative"]
        self.assertEqual(incremental["semantic_calls"], 1)
        self.assertEqual(incremental["environment_requests"], 0)
        self.assertEqual(cumulative["semantic_calls"], 7)  # unknown first + five-call recovery + completion
        self.assertEqual(cumulative["environment_requests"], 2)
        self.assertEqual(cumulative["requests_with_unknown_usage"], 1)
        self.assertEqual(cumulative["http_attempts_with_unknown_usage"], 1)
        self.assertEqual(cumulative["reported_usage"]["total_tokens"], 6 * 18 + 2 * 5)

    def test_reference_failure_stops_without_memory_and_cannot_claim_ready(self):
        root, result = self.complete(invalid_ref=True)
        self.assertEqual(result["status"], "error", result)
        self.assertFalse((root / "output.json").exists())
        self.assertFalse((root / "memory_final.json").exists())
        self.assertEqual(len(self.executions), 2)
        self.assertTrue(complete_feedback.verify_completion(root)["artifact_valid"])
        self.assertFalse(complete_feedback.verify_completion(root)["feedback_ready"])
        change(root / "report.json", lambda value: value.update(status="feedback_ready"))
        with self.assertRaisesRegex(ValueError, "Unvalidated completion"):
            complete_feedback.verify_completion(root)

    def test_completion_input_tampering_is_rejected(self):
        root, result = self.complete()
        self.assertEqual(result["status"], "feedback_ready", result)
        change(root / "input.json", lambda value: value["plan"].update(intent="Changed after observed outcome"))
        with self.assertRaisesRegex(ValueError, "input differs"):
            complete_feedback.verify_completion(root)

    def test_source_and_prior_cost_report_are_immutable_bindings(self):
        for kind in ("source", "prior_cost"):
            with self.subTest(kind=kind):
                root, result = self.complete(name="tamper_" + kind)
                self.assertEqual(result["status"], "feedback_ready", result)
                path = self.source / "outputs/diagnosis.json" if kind == "source" else self.first / "report.json"
                before = path.read_bytes()
                path.write_bytes(before + b"\n")
                try:
                    with self.assertRaises(ValueError):
                        complete_feedback.verify_completion(root)
                finally:
                    path.write_bytes(before)


if __name__ == "__main__":
    unittest.main()
