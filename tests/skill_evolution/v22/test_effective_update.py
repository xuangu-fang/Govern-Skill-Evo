"""Synthetic prompt/contract checks, not model behavior or preconditioning evidence."""

from copy import deepcopy
import json
import unittest

from src.skill_evolution.v22.compact_update import (
    EDITOR_SHAPE, FUSION_SHAPE, apply_fusion, editor_messages, fusion_messages,
    validate_editor,
)
from src.skill_evolution.v22.effective_update import (
    editor_messages_effective, fusion_messages_effective,
)
from tests.skill_evolution.v22.test_compact_learning_view import fixture as history_fixture


def payload():
    value = history_fixture()
    effect = value["memory"][0]
    effect["claim_context_id"] = "old-context"
    effect["limit_contexts"] = ["old-context", "old-context"]
    value.update(parent={"text": None}, capabilities="Current observation plus two recent pairs.",
                 plan={"intent": "Reach the goal using visible legal actions while retaining recovery.",
                       "requirements": [
                           {"id": "u1", "text": "When an action is available, choose a useful exact current command; preserve recovery and stop at the goal.",
                            "basis": ["C2:1"]},
                           {"id": "u2", "text": "Treat incomplete observations as unknown, not as negative facts.", "basis": ["C2:1"]},
                       ],
                       "watch": [{"id": "w1", "about": ["u1"], "question": "Are useful alternatives or recovery opportunities lost?"}],
                       "open": []})
    return value


def increment():
    return {"decision": "ready", "reason": "Synthetic conditional exploration; no measured gain claimed.",
            "changes": [{"from": ["u1"],
                         "to": [{"id": "u3", "text": "When a useful action is currently available, choose its exact command without a redundant mandatory check; preserve recovery and stop at the goal."}],
                         "basis": ["old-context:m1"],
                         "reason": "A bounded alternative challenges only the proposed universal checking obligation; other contexts remain unknown.",
                         "disposition": "replace"}],
            "watch_changes": [{"from": ["w1"], "to": [{"id": "w3", "about": ["u3"],
                               "question": "Does omitting the redundant check miss needed information, useful alternatives or recovery?"}]}],
            "open": []}


class EffectiveUpdateTests(unittest.TestCase):
    def test_two_branches_preserve_the_same_frozen_draft_and_current_evidence(self):
        full = payload()
        original = deepcopy(full)
        empty = deepcopy(full)
        empty["memory"] = []
        without = json.loads(fusion_messages_effective(empty)[1]["content"])
        with_memory = json.loads(fusion_messages_effective(full)[1]["content"])
        for field in ("plan", "sources", "runs", "parent"):
            self.assertEqual(without[field], with_memory[field])
            self.assertEqual(with_memory[field], full[field])
        self.assertFalse(without["memory"])
        self.assertTrue(with_memory["memory"])
        self.assertEqual(with_memory["memory"][0]["id"], "old-context:m1")
        self.assertNotIn("observation", with_memory["memory"][0]["basis"][0])
        self.assertNotIn("finding", with_memory["memory"][0]["basis"][0])
        self.assertEqual(full, original)

    def test_editor_receives_only_effects_cited_by_effective_requirements(self):
        value = payload()
        value["plan"]["requirements"][0]["basis"].append("old-context:m1")
        unused = deepcopy(value["memory"][0])
        unused["id"] = "unused-effect"
        unused["claim"] = "Irrelevant historical suggestion must not reach Editor."
        value["memory"].append(unused)
        original = deepcopy(value)
        view = json.loads(editor_messages_effective(value)[1]["content"])
        self.assertEqual([row["id"] for row in view["memory"]], ["old-context:m1"])
        self.assertEqual(len(view["memory"][0]["limits"]), 2)
        self.assertIn("counterexample", view["memory"][0]["limits"][0])
        self.assertEqual(view["plan"], value["plan"])
        self.assertEqual(value, original)

    def test_rules_require_specific_decisions_without_forcing_or_forbidding_exploration(self):
        prompt = fusion_messages_effective(payload())[0]["content"]
        for boundary in (
            "SPECIFIC decision", "initial Plan already handles", "direction/ordering",
            "strength or scope", "coordinate overlapping/dependent", "what would falsify",
            "do NOT automatically prohibit bounded exploration", "new universal mandatory sequence",
            "Correcting an event count", "does not by itself justify strengthening an action filter",
            "Identity is legitimate", "generic 'causality is unproven' is not",
            "COMPLETE valid obligations", "Do not force any requirement",
        ):
            self.assertIn(boundary, prompt)
        self.assertNotIn("u5", prompt)

    def test_output_shapes_stay_compact_and_old_validators_accept_identity_or_increment(self):
        value = payload()
        for builder, shape in ((fusion_messages_effective, FUSION_SHAPE), (editor_messages_effective, EDITOR_SHAPE)):
            system = builder(value)[0]["content"]
            self.assertEqual(json.loads(system.split("\nOutput shape:\n", 1)[1]), shape)
        identity = {"decision": "ready", "reason": "u1 already requires an exact currently available useful action; the observed bundle does not locate another current mismatch.",
                    "changes": [], "watch_changes": [], "open": []}
        self.assertEqual(apply_fusion(identity, value), value["plan"])
        actual = apply_fusion(increment(), value)
        self.assertEqual(actual["intent"], value["plan"]["intent"])
        self.assertIn(value["plan"]["requirements"][1], actual["requirements"])
        changed = next(row for row in actual["requirements"] if row["id"] == "u3")
        self.assertEqual(changed["basis"], ["C2:1", "old-context:m1"])
        self.assertIn("preserve recovery and stop at the goal", changed["text"])
        self.assertEqual(value["plan"], payload()["plan"])

    def test_revision_cannot_drop_observation_destinations_or_use_historical_alias_as_basis(self):
        value = payload()
        missing = increment()
        missing["watch_changes"] = []
        with self.assertRaisesRegex(ValueError, "observation question"):
            apply_fusion(missing, value)
        wrong_ref = increment()
        wrong_ref["changes"][0]["basis"] = ["H1::C2:8"]
        with self.assertRaisesRegex(ValueError, "unknown reference"):
            apply_fusion(wrong_ref, value)

    def test_editor_important_exception_still_blocks_a_candidate(self):
        value = payload()
        text = "Choose exact current commands. Preserve recovery. Unknown is not false."
        result = {"decision": "candidate", "reason": "Synthetic construction only", "candidate_text": text,
                  "mappings": [{"requirements": ["u1", "u2"], "side": "candidate", "excerpt": text}],
                  "issues": [{"about": ["u1"], "reason": "Visible trigger cannot be determined with available state."}], "watch": []}
        with self.assertRaisesRegex(ValueError, "blocking issues"):
            validate_editor(result, value)
        result.update(decision="needs_revision", candidate_text=None, mappings=[])
        self.assertEqual(validate_editor(result, value)["decision"], "needs_revision")
        prompt = editor_messages_effective(value)[0]["content"]
        self.assertIn("not permission to", prompt)
        self.assertIn("not semantic equivalence established", prompt)

    def test_new_consumption_does_not_mutate_old_messages_or_frozen_input(self):
        value = payload()
        before = deepcopy(value)
        old_fusion, old_editor = fusion_messages(value), editor_messages(value)
        fusion_messages_effective(value)
        editor_messages_effective(value)
        self.assertEqual(value, before)
        self.assertEqual(fusion_messages(value), old_fusion)
        self.assertEqual(editor_messages(value), old_editor)


if __name__ == "__main__":
    unittest.main()
