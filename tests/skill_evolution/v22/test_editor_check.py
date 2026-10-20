"""An isolated Editor check cannot ingest old Candidate outcomes or release one."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.skill_evolution.v22.editor_check import prepare_check, run_check, verify_check
from src.skill_evolution.v22.model_call import semantic_call
from tests.skill_evolution.v22.test_editor_preservation import build_editor_v1, mark_revision
from tests.skill_evolution.v22.test_verify_round import make_round


class EditorCheckTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = make_round(self.root)()
        self.output = self.root / "check"

    def execute(self, *, revision=False, raw=None):
        payload, _, model = prepare_check(self.source)
        value = build_editor_v1(payload["diagnosis"])
        if revision:
            mark_revision(value)
        session = mock.Mock()
        session.post.return_value.status_code = 200
        session.post.return_value.ok = True
        session.post.return_value.json.return_value = {
            "model": model, "choices": [{"message": {"content": json.dumps(value) if raw is None else raw}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
        def generate(stage, request, output):
            return semantic_call(stage, request, session=session, endpoint="https://offline.invalid", key="secret", model=model, output=output)
        result = run_check(self.source, self.output, generate)
        return result, session

    def test_input_is_only_bound_pre_execution_material(self):
        before = prepare_check(self.source)
        self.assertEqual(set(before[0]), {"parent", "diagnosis", "evidence"})
        self.assertTrue(all(Path(row["path"]).relative_to(self.source).parts[0] not in {"candidate", "candidate_runs", "report.json"}
                            for row in before[1] if self.source in Path(row["path"]).parents))
        # Deliberately corrupt only outputs; construction-check input must not read them.
        (self.source / "candidate/SKILL.md").write_text("PRIVATE_OUTCOME_MARKER")
        (self.source / "report.json").write_text("not a report")
        self.assertEqual(before, prepare_check(self.source))
        self.assertNotIn("PRIVATE_OUTCOME_MARKER", json.dumps(before[0]))

    def test_revision_is_normal_stop_and_no_candidate_is_released(self):
        result, session = self.execute(revision=True)
        self.assertEqual(result["status"], "needs_revision")
        self.assertEqual(session.post.call_count, 1)
        self.assertTrue(verify_check(self.output)["check_complete"])
        self.assertFalse((self.output / "candidate").exists())
        self.assertEqual(result["incremental_cost"]["environment_requests"], 0)

    def test_successful_draft_stays_unexecuted_and_tampering_is_detected(self):
        result, _ = self.execute()
        self.assertEqual(result["status"], "candidate_unexecuted")
        self.assertTrue(verify_check(self.output)["artifact_valid"])
        path = self.output / "editor.json"
        value = json.loads(path.read_text())
        value["requirements_sha256"] = "changed"
        path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            verify_check(self.output)

    def test_invalid_response_is_preserved_without_retry(self):
        result, session = self.execute(raw="not JSON")
        self.assertEqual(result["status"], "error")
        self.assertEqual(session.post.call_count, 1)
        self.assertFalse(verify_check(self.output)["check_complete"])
        self.assertFalse((self.output / "editor.json").exists())


if __name__ == "__main__":
    unittest.main()
