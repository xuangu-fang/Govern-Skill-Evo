"""Exact inherited-watch deduplication only; synthetic calls, no live execution."""

from copy import deepcopy
import json
import unittest

from src.skill_evolution.v22 import consume_fixed_plan as consumption
from src.skill_evolution.v22.editor_watch_reconciliation import (
    NORMALIZATION, normalize_inherited_watch, recover, verify,
)
from tests.skill_evolution.v22.test_compact_cycle import recorded_mock_call
from tests.skill_evolution.v22 import test_consume_fixed_plan as consumption_fixtures
from tests.skill_evolution.v22.test_consume_fixed_plan import edit, identity, knowledge_output, read
from tests.skill_evolution.v22.test_effective_update import payload as update_payload
from tests.skill_evolution.v22.test_verify_round import change


class EditorWatchReconciliationTests(unittest.TestCase):
    def setUp(self):
        # Reuse the synthetic upstream-source binding, while exercising the real
        # fixed-consumption runner, raw-call verifier and offline recovery below.
        consumption_fixtures.FixedConsumptionTests.setUp(self)

    def operation(self, *, changed=False, name="operation", complete=True):
        def generate(stage, messages, output):
            payload = json.loads(messages[1]["content"])
            if stage == "memory":
                value = knowledge_output()
            elif stage.endswith("fusion"):
                value = identity()
            else:
                value = edit(payload)
                if stage == "current_editor":
                    value["watch"] = deepcopy(payload["plan"]["watch"])
                    if changed:
                        value["watch"][0]["question"] += " Silently alter the inherited question."
            return recorded_mock_call(stage, messages, output, value, "deepseek-v4-pro")

        root = self.directory / name
        report = consumption.learn(self.source, root, deepcopy(self.plan), generate)
        if complete:
            report = consumption.construct(root, generate)
            self.assertEqual(report["status"], "comparison_incomplete", report)
            self.assertEqual(report["branches"]["current"]["status"], "error")
            self.assertEqual(report["branches"]["history"]["status"], "candidate")
        return root, report

    def test_only_identical_inherited_questions_are_removed(self):
        payload = update_payload()
        value = edit(payload)
        added = {"id": "new_question", "about": ["u2"], "question": "Does uncertainty remain explicit?"}
        value["watch"] = deepcopy(payload["plan"]["watch"]) + [added]
        original, original_payload = deepcopy(value), deepcopy(payload)
        normalized = normalize_inherited_watch(value, payload)
        self.assertEqual(normalized["watch"], [added])
        self.assertEqual({k: v for k, v in normalized.items() if k != "watch"},
                         {k: v for k, v in value.items() if k != "watch"})
        self.assertEqual(value, original)
        self.assertEqual(payload, original_payload)

    def test_changed_inherited_question_and_other_invalid_fields_still_fail(self):
        payload = update_payload()
        for field, new_value in (("question", "A different question"), ("about", ["u2"]), ("extra", "not inherited")):
            with self.subTest(field=field):
                value = edit(payload)
                value["watch"] = deepcopy(payload["plan"]["watch"])
                value["watch"][0][field] = new_value
                with self.assertRaisesRegex(ValueError, "differs"):
                    normalize_inherited_watch(value, payload)
        value = edit(payload)
        value["watch"] = deepcopy(payload["plan"]["watch"])
        value["mappings"][0]["excerpt"] = "Not in the Candidate"
        with self.assertRaisesRegex(ValueError, "declared side"):
            normalize_inherited_watch(value, payload)

    def test_recovery_keeps_original_error_raw_call_and_exact_candidate_text(self):
        source, report = self.operation()
        frozen = {path: path.read_bytes() for path in source.rglob("*") if path.is_file()}
        root = self.directory / "current_offline"
        recovered = recover(source, "current", root)
        self.assertEqual(recovered["status"], "offline_reconciled")
        self.assertEqual(recovered["model_calls"], 0)
        self.assertEqual(recovered["environment_executions"], 0)
        self.assertEqual(recovered["derived_from"]["removed_inherited_watch"], ["w1"])
        self.assertEqual(recovered["derived_from"]["normalization"], NORMALIZATION)
        self.assertEqual(frozen, {path: path.read_bytes() for path in frozen})
        self.assertEqual(read(source / "report.json"), report)
        self.assertEqual(consumption.verify(source)["status"], "comparison_incomplete")
        self.assertEqual(verify(root)["original_status"], "comparison_incomplete")
        self.assertFalse(verify(root)["executed"])
        raw = json.loads(read(source / "calls/current_editor.json")["steps"][0]["model_response"]["content"])
        self.assertEqual((root / "SKILL.md").read_text(), raw["candidate_text"])
        self.assertFalse(read(root / "lineage.json")["executed"])
        self.assertFalse((source / "current/SKILL.md").exists())

    def test_same_policy_accepts_already_valid_opposite_branch_without_changes(self):
        source, _ = self.operation()
        root = self.directory / "history_offline"
        report = recover(source, "history", root)
        self.assertEqual(report["derived_from"]["removed_inherited_watch"], [])
        self.assertEqual((root / "SKILL.md").read_bytes(), (source / "history/SKILL.md").read_bytes())
        self.assertTrue(verify(root)["artifact_valid"])

    def test_nonidentical_raw_question_and_nonterminal_source_are_rejected(self):
        source, _ = self.operation(changed=True)
        output = self.directory / "rejected"
        with self.assertRaisesRegex(ValueError, "differs"):
            recover(source, "current", output)
        self.assertFalse(output.exists())
        pending, _ = self.operation(complete=False, name="pending")
        with self.assertRaisesRegex(ValueError, "terminal"):
            recover(pending, "current", self.directory / "pending_recovery")

    def test_bound_sources_text_and_derived_output_tampering_are_rejected(self):
        source, _ = self.operation()
        for kind in ("editor", "text", "lineage", "source"):
            with self.subTest(kind=kind):
                root = self.directory / ("tamper_" + kind)
                recover(source, "current", root)
                source_path = None
                if kind == "editor":
                    change(root / "editor.json", lambda value: value.update(reason="Changed interpretation"))
                elif kind == "text":
                    (root / "SKILL.md").write_text("A new obligation")
                elif kind == "lineage":
                    change(root / "lineage.json", lambda value: value.update(executed=True))
                else:
                    source_path = source / "calls/current_editor.json"
                    original = source_path.read_bytes()
                    source_path.write_bytes(original + b"\n")
                try:
                    with self.assertRaises(ValueError):
                        verify(root)
                finally:
                    if source_path is not None:
                        source_path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
