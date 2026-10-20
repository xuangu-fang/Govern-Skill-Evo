"""Narrow correction profile regression checks; no calls or environment execution."""

from copy import deepcopy
import json
import unittest

from src.skill_evolution.v22.effective_memory import validate_effective_learning
from src.skill_evolution.v22.effective_reconciliation import (
    apply_reconciled_memory, messages_reconciliation, reconciliation_payload,
    validate_reconciliation,
)
from tests.skill_evolution.v22 import test_effective_memory as memory_fixtures


class EffectiveReconciliationTests(unittest.TestCase):
    def setUp(self):
        fixture = memory_fixtures.EffectiveMemoryTests(methodName="test_empty_memory_consumption_is_supported")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.payload = fixture.payload
        self.value = fixture.correction()
        self.value["findings"][0]["about"] = ["old:m1"]

    def test_reconciliation_does_not_require_full_watch_replay(self):
        with self.assertRaisesRegex(ValueError, "Unassessed watch"):
            validate_effective_learning(self.value, self.payload)
        self.assertEqual(validate_reconciliation(self.value, self.payload), self.value)
        self.assertTrue(self.payload["plan"]["watch"])
        empty = {"findings": [], "open": [], "memory_delta": []}
        self.assertEqual(validate_reconciliation(empty, self.payload), empty)

    def test_new_effects_are_out_of_scope(self):
        self.value["memory_delta"][0].update(replace=[], retire_limits=[])
        with self.assertRaisesRegex(ValueError, "new effects are out of scope"):
            validate_reconciliation(self.value, self.payload)

    def test_full_actual_evidence_and_static_requirements_remain(self):
        view = reconciliation_payload(self.payload)
        for key in ("parent", "candidate", "actual_diff", "capabilities", "pairs"):
            self.assertEqual(view[key], self.payload[key])
        self.assertEqual(view["plan"]["intent"], self.payload["plan"]["intent"])
        self.assertEqual(view["plan"]["requirements"], self.payload["plan"]["requirements"])
        self.assertEqual(view["plan"]["watch"], [])
        self.assertFalse(any(source["kind"] == "watch" for source in view["sources"].values()))
        self.assertTrue(any(source["kind"] == "requirement" for source in view["sources"].values()))
        self.assertNotIn("command_sets", view)
        for alias, original in self.payload["runs"].items():
            expected = deepcopy(original)
            expected.pop("initial_commands")
            for event in expected["steps"]:
                event.pop("commands")
            self.assertEqual(view["runs"][alias], expected)
        self.assertEqual(len(view["historical_sources"]), 3)

    def test_retirement_validation_still_checks_version_and_finding(self):
        self.value["memory_delta"][0]["retire_limits"][0]["index"] = 100
        with self.assertRaisesRegex(ValueError, "out of bounds"):
            validate_reconciliation(self.value, self.payload)

    def test_removed_watch_sources_cannot_be_cited_via_hidden_original_input(self):
        old_watch_ref = next(key for key, source in self.payload["sources"].items() if source["kind"] == "watch")
        self.value["findings"][0]["refs"].append(old_watch_ref)
        with self.assertRaisesRegex(ValueError, "invalid sources"):
            validate_reconciliation(self.value, self.payload)

    def test_apply_keeps_original_input_and_supplied_original_context_identity(self):
        original, value = deepcopy(self.payload), deepcopy(self.value)
        result = apply_reconciled_memory(self.payload["memory"], self.value, "original-bound-context", self.payload)
        self.assertEqual(result[0]["claim_context_id"], "original-bound-context")
        self.assertNotIn("Wrong inherited factual assertion.", result[0]["limits"])
        self.assertIn("Untested scope must remain unknown.", result[0]["limits"])
        self.assertEqual(result[0]["retired_limits"][0]["limit"], "Wrong inherited factual assertion.")
        self.assertEqual(self.payload, original)
        self.assertEqual(self.value, value)
        self.assertTrue(self.payload["plan"]["watch"])

    def test_short_independent_messages_preserve_scope_warning(self):
        messages = messages_reconciliation(self.payload)
        self.assertIn("not a fresh execution", messages[0]["content"])
        self.assertIn("legal-action lists are", messages[0]["content"])
        self.assertIn("Do not re-answer original watch", messages[0]["content"])
        self.assertEqual(json.loads(messages[1]["content"]), reconciliation_payload(self.payload))
        self.assertNotIn("Every watch", messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
