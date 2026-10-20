"""Checks for the fixed-denominator NoSkill evaluation report."""

import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

from src.adapters.alfworld.eval_test import summarize, retryable_runtime_failure, run_one


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.items = [{"id": f"test:{i}", "task_type": "pick_and_place_simple"} for i in range(3)]

    def test_errors_and_pending_cases_do_not_inflate_success_rate(self):
        results = {
            "test:0": {"status": "success", "won": True, "usage": {"total_tokens": 7}},
            "test:1": {"status": "error", "won": False},
        }
        report = summarize(self.items, results)
        self.assertEqual(report["success_rate_all_tasks"], 1 / 3)
        self.assertEqual(report["success_rate_normal_episodes"], 1)
        self.assertEqual(report["pending_tasks"], 1)
        self.assertFalse(report["evaluation_valid"])
        self.assertEqual(report["usage"]["total_tokens"], 7)

    def test_complete_evaluation_includes_normal_task_failures(self):
        results = {"test:0": {"status": "success", "won": True},
                   "test:1": {"status": "step_limit", "won": False},
                   "test:2": {"status": "environment_ended", "won": False}}
        report = summarize(self.items, results)
        self.assertTrue(report["evaluation_valid"])
        self.assertEqual(report["successes"], 1)
        self.assertEqual(report["by_task_type"]["pick_and_place_simple"]["tasks"], 3)

    def test_duplicate_or_extra_tasks_are_rejected(self):
        with self.assertRaises(ValueError):
            summarize([self.items[0], self.items[0]], {})
        with self.assertRaises(ValueError):
            summarize(self.items, {"train:0": {"status": "success", "won": True}})

    def test_invalid_model_actions_are_failures_not_missing_evaluations(self):
        results = {item["id"]: {"status": "error", "won": False,
                   "error_type": "ValueError", "error": "Model must return exactly one single-line <action> command."}
                   for item in self.items}
        report = summarize(self.items, results)
        self.assertTrue(report["evaluation_valid"])
        self.assertEqual(report["model_output_failures"], 3)
        self.assertEqual(report["runtime_errors"], 0)
        self.assertEqual(report["success_rate_all_tasks"], 0)

    def test_retry_scope_excludes_model_and_normal_task_failures(self):
        self.assertTrue(retryable_runtime_failure({"error": "Model API returned HTTP 429."}))
        self.assertFalse(retryable_runtime_failure({"status": "step_limit"}))
        self.assertFalse(retryable_runtime_failure({"status": "error", "error_type": "ValueError"}))
        self.assertFalse(retryable_runtime_failure({"error": "Model API returned HTTP 401."}))

    def test_retried_api_attempt_usage_is_not_lost_or_scored_twice(self):
        result = {"status": "success", "won": True, "usage": {"total_tokens": 7},
                  "previous_attempts": [{"status": "error", "won": False, "usage": {"total_tokens": 5}}]}
        report = summarize(self.items, {"test:0": result})
        self.assertEqual(report["usage"]["total_tokens"], 12)
        self.assertEqual(report["successes"], 1)
        self.assertEqual(report["infrastructure_attempts_retried"], 1)

    def test_interrupted_retry_preserves_original_and_partial_logs(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            item = {"id": "test:0", "task_type": "pick_and_place_simple"}
            task_dir = root / "tasks/test_0"
            task_dir.mkdir(parents=True)
            paths = [task_dir / f"llm_{index}/trajectory.json" for index in ["001", "002", "999"]]
            for path in paths[:2]:
                path.parent.mkdir()
            old_record = {"task": item, "split": "test", "model": "test", "won": False, "steps": [], "status": "error"}
            paths[0].write_text(json.dumps(old_record))
            paths[1].write_text(json.dumps({**old_record, "status": "running"}))
            original_log = str(paths[0]) + " original limit failure"
            (task_dir / "run_attempt_001.log").write_text(original_log)
            (task_dir / "run.log").write_text(str(paths[1]) + " interrupted retry")
            (task_dir / "result.json").write_text(json.dumps({"status": "error", "won": False, "trajectory": str(paths[0]), "log": str(task_dir / "run.log")}))

            def fake_process(*args, **kwargs):
                paths[2].parent.mkdir()
                paths[2].write_text(json.dumps({**old_record, "status": "success", "won": True}))
                return SimpleNamespace(returncode=0)

            args = SimpleNamespace(model="test", max_steps=50, max_tokens=1024, env_file=root / ".env")
            with mock.patch("src.adapters.alfworld.eval_test.subprocess.run", side_effect=fake_process):
                result = run_one(item, root, args)
            self.assertEqual((task_dir / "run_attempt_001.log").read_text(), original_log)
            self.assertTrue((task_dir / "run_attempt_002.log").exists())
            self.assertEqual(result["previous_attempts"][0]["log"], str(task_dir / "run_attempt_001.log"))
            self.assertEqual(result["previous_attempts"][1]["status"], "interrupted")
            self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
