"""Effective knowledge retirement and provenance tests; fixtures are synthetic."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.skill_evolution.v22.compact_learning import apply_memory, prepare_legacy
from src.skill_evolution.v22.effective_memory import (
    apply_effective_memory, effective_consumption_payload, learning_messages_effective,
    validate_effective_learning,
)
from tests.skill_evolution.v22.test_verify_round import make_round


class EffectiveMemoryTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = make_round(Path(temporary.name))()
        payload, _, _ = prepare_legacy(source)
        self.finding = {"id": "f1", "about": ["intent"] + [row["id"] for row in payload["plan"]["watch"]],
                        "observation": "Obsolete interpretation must not be an active fact oracle.",
                        "refs": ["P1:1", "C1:1", "skill:candidate"]}
        first = {"findings": [self.finding], "open": [], "memory_delta": [{
            "replace": [], "claim": "C1:1 is a historical fixture event.",
            "limits": ["Wrong inherited factual assertion.", "Untested scope must remain unknown."], "findings": ["f1"]}]}
        self.memory = apply_memory([], first, "old", payload)
        self.payload = deepcopy(payload)
        self.payload["memory"] = self.memory

    def correction(self):
        finding = deepcopy(self.finding)
        finding["observation"] = "Current fixture corrects the previous interpretation, not a new trial."
        return {"findings": [finding], "open": [], "memory_delta": [{
            "replace": ["old:m1"], "claim": "C1:1 supports only this corrected fixture statement.",
            "limits": ["Same feedback reread; no new independent support."], "findings": ["f1"],
            "retire_limits": [{"effect_id": "old:m1", "index": 0,
                               "reason": "Current f1 contradicts this particular assertion.", "findings": ["f1"]}]}]}

    def test_explicit_retirement_archives_error_and_inherits_other_unknown(self):
        result = apply_effective_memory(self.memory, self.correction(), "new", self.payload)
        effect = result[0]
        self.assertEqual(effect["limits"], ["Untested scope must remain unknown.", "Same feedback reread; no new independent support."])
        self.assertEqual(effect["limit_contexts"], ["old", "new"])
        self.assertEqual(effect["claim_context_id"], "new")
        self.assertEqual(effect["retired_limits"][0]["limit"], "Wrong inherited factual assertion.")
        self.assertEqual(effect["retired_limits"][0]["effect_id"], "old:m1")
        self.assertEqual(effect["retired_limits"][0]["retirement_context_id"], "new")
        self.assertEqual(effect["retired_limits"][0]["findings"], ["f1"])
        self.assertEqual(effect["basis"][0], self.memory[0]["basis"][0])

    def test_no_retirement_never_implicitly_discards_an_old_limit(self):
        value = self.correction()
        value["memory_delta"][0]["retire_limits"] = []
        result = apply_effective_memory(self.memory, value, "new", self.payload)
        self.assertIn("Wrong inherited factual assertion.", result[0]["limits"])
        self.assertIn("Untested scope must remain unknown.", result[0]["limits"])
        self.assertEqual(result[0]["retired_limits"], [])

    def test_invalid_retirement_reference_index_and_nonreplacement_fail_closed(self):
        for mutate in (
            lambda d: d["retire_limits"][0].update(index=2),
            lambda d: d["retire_limits"][0].update(index=-1),
            lambda d: d["retire_limits"][0].update(index=True),
            lambda d: d["retire_limits"][0].update(effect_id="missing:m1"),
            lambda d: d["retire_limits"][0].update(findings=["missing"]),
            lambda d: d.update(replace=[]),
            lambda d: d["retire_limits"].append(deepcopy(d["retire_limits"][0])),
        ):
            value = self.correction()
            mutate(value["memory_delta"][0])
            with self.assertRaises(ValueError):
                validate_effective_learning(value, self.payload)

    def test_retirement_findings_must_be_part_of_saved_revision_basis(self):
        value = self.correction()
        additional = deepcopy(value["findings"][0])
        additional["id"] = "f2"
        value["findings"].append(additional)
        value["memory_delta"][0]["retire_limits"][0]["findings"] = ["f2"]
        with self.assertRaisesRegex(ValueError, "included in this delta"):
            validate_effective_learning(value, self.payload)

    def test_consumption_excludes_retired_assertion_and_old_explanation_but_keeps_sources(self):
        payload = deepcopy(self.payload)
        payload["memory"] = apply_effective_memory(self.memory, self.correction(), "new", self.payload)
        view = effective_consumption_payload(payload)
        serialized = json.dumps(view)
        self.assertNotIn("Wrong inherited factual assertion.", serialized)
        self.assertNotIn("Obsolete interpretation must not be an active fact oracle.", serialized)
        self.assertNotIn("retired_limits", serialized)
        self.assertEqual(view["historical_sources"]["H1::C1:1"]["action"], "look")
        self.assertEqual(view["historical_sources"]["H1::skill:candidate"]["text"], self.payload["candidate"]["text"])
        self.assertEqual(view["memory"][0]["basis"][0]["actual_update"]["candidate_skill_id"], self.payload["candidate"]["skill_id"])
        self.assertIn("finding_id", view["memory"][0]["basis"][0])

    def test_active_claim_and_each_limit_use_own_context(self):
        value = self.correction()
        value["memory_delta"][0]["limits"] = ["P1:1 is current evidence only."]
        self.memory[0]["limits"][1] = "C1:1 historical uncertainty remains."
        payload = deepcopy(self.payload)
        payload["memory"] = apply_effective_memory(self.memory, value, "new", self.payload)
        view = effective_consumption_payload(payload)
        self.assertEqual(view["historical_contexts"], {"H1": "old", "H2": "new"})
        self.assertTrue(view["memory"][0]["claim"].startswith("H2::C1:1"))
        self.assertTrue(view["memory"][0]["limits"][0].startswith("H1::C1:1"))
        self.assertTrue(view["memory"][0]["limits"][1].startswith("H2::P1:1"))

    def test_mixed_legacy_context_is_unknown_not_all_contexts(self):
        payload = deepcopy(self.payload)
        other = deepcopy(payload["memory"][0]["basis"][0])
        other["context_id"] = "other"
        payload["memory"][0]["basis"].append(other)
        view = effective_consumption_payload(payload)
        self.assertIsNone(view["memory"][0]["claim_context_id"])
        self.assertEqual(view["memory"][0]["limit_contexts"], [None, None])
        self.assertTrue(view["memory"][0]["claim"].startswith("history_unknown::C1:1"))

    def test_source_snapshots_and_inputs_are_unchanged(self):
        payload, value = deepcopy(self.payload), self.correction()
        before_payload, before_value = deepcopy(payload), deepcopy(value)
        apply_effective_memory(payload["memory"], value, "new", payload)
        effective_consumption_payload(payload)
        messages = learning_messages_effective(payload)
        self.assertEqual(payload, before_payload)
        self.assertEqual(value, before_value)
        self.assertIn("retire_limits", messages[0]["content"])
        self.assertIn("SAME real feedback", messages[0]["content"])

    def test_parent_fact_can_correct_existing_response_but_not_create_new_effect(self):
        value = self.correction()
        value["findings"][0]["refs"] = ["P1:1"]
        self.assertEqual(validate_effective_learning(value, self.payload), value)
        value["memory_delta"][0].update(replace=[], retire_limits=[])
        with self.assertRaisesRegex(ValueError, "new response needs Candidate"):
            validate_effective_learning(value, self.payload)

    def test_empty_memory_consumption_is_supported(self):
        self.assertEqual(effective_consumption_payload({"memory": []})["memory"], [])


if __name__ == "__main__":
    unittest.main()
