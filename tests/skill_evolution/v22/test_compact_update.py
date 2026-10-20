"""Synthetic protocol tests, not evidence that an update improves real behavior."""

from copy import deepcopy
import json
import unittest

from src.skill_evolution.v22.compact_update import (
    apply_fusion, diagnosis_messages, editor_messages, fusion_messages,
    validate_diagnosis, validate_editor,
)


def payload():
    return {
        "parent": {"text": None}, "capabilities": {"history_pairs": 2},
        "runs": [{"ref": "P1", "steps": [{"step": 4, "action": "look"}]}],
        "sources": {"P1:4": {"run": "P1", "step": 4}, "P1:7": "Failed action", "skill:parent": None},
        "plan": {
            "intent": "Select useful legal actions, preserve recovery and stop when complete.",
            "requirements": [
                {"id": "u1", "text": "Use an exact current admissible action.", "basis": ["P1:4"]},
                {"id": "u2", "text": "Recover from temporary failures within the available budget.", "basis": ["P1:7"]},
            ],
            "watch": [
                {"id": "w1", "about": ["u1"], "question": "Do unavailable actions recur?"},
                {"id": "w2", "about": ["u2"], "question": "Is recovery still possible after temporary failure?"},
            ],
            "open": [],
        },
        "memory": [{"id": "m1", "claim": "A bundled update used current actions in this run.",
                    "limits": ["No isolated contribution or general guarantee."],
                    "basis": [{"context_id": "old-round", "finding": {"observation": "legal"}, "sources": {"C1:7": "done"}}],
                    "supersedes": []}],
    }


def identity():
    return {"decision": "ready", "reason": "Existing requirements already address the limited observation.",
            "changes": [], "watch_changes": [], "open": []}


def replacement():
    return {"decision": "ready", "reason": "Construct a bounded revision, not a proven effect.",
            "changes": [{"from": ["u1"], "to": [{"id": "u3", "text": "Choose an exact current command after checking its visible purpose."}],
                         "basis": ["m1"], "reason": "Apply the local observation with its limitations.", "disposition": "replace"}],
            "watch_changes": [{"from": ["w1"], "to": [{"id": "w3", "about": ["u3"], "question": "Do unsuitable or unavailable actions recur?"}]}],
            "open": []}


def editor():
    return {"decision": "candidate", "reason": "Realize both requirements, without claiming behavioral validation.",
            "candidate_text": "# Guidance\nUse an exact current admissible action.\nRecover within the available budget.",
            "mappings": [{"requirements": ["u1"], "side": "candidate", "excerpt": "Use an exact current admissible action."},
                         {"requirements": ["u2"], "side": "candidate", "excerpt": "Recover within the available budget."}],
            "issues": [], "watch": []}


class CompactUpdateTests(unittest.TestCase):
    def test_diagnosis_has_independent_source_boundary(self):
        p = payload()
        p["memory"] = []
        value = {"decision": "revise", "reason": "Inspect current failures and preserved behavior.", "plan": p["plan"]}
        self.assertEqual(validate_diagnosis(value, p), value)
        p["memory"] = payload()["memory"]
        with self.assertRaisesRegex(ValueError, "historical Memory"):
            validate_diagnosis(value, p)

    def test_diagnosis_missing_source_is_not_valid_unknown(self):
        p = payload()
        p["memory"] = []
        p["plan"]["requirements"][0]["basis"] = ["P1:999"]
        with self.assertRaisesRegex(ValueError, "unknown reference"):
            validate_diagnosis({"decision": "revise", "reason": "A guess", "plan": p["plan"]}, p)

    def test_semantic_stop_is_distinct_from_empty_revision(self):
        p = payload()
        p["memory"] = []
        for decision in ("no_change", "need_evidence"):
            value = {"decision": decision, "reason": "Specific supported stop or missing evidence.", "plan": None}
            self.assertEqual(validate_diagnosis(value, p), value)
        with self.assertRaises(ValueError):
            validate_diagnosis({"decision": "revise", "reason": "No plan", "plan": None}, p)

    def test_identity_is_an_explicit_reasoned_decision_and_nonmutating(self):
        p = payload()
        before = deepcopy(p)
        effective = apply_fusion(identity(), p)
        self.assertEqual(effective, p["plan"])
        effective["requirements"][0]["text"] = "Changed returned copy"
        self.assertEqual(p, before)
        broken = identity()
        del broken["reason"]
        with self.assertRaises(ValueError):
            apply_fusion(broken, p)

    def test_increment_inherits_untouched_obligations_and_source_lineage(self):
        p = payload()
        before = deepcopy(p)
        plan = apply_fusion(replacement(), p)
        self.assertEqual(plan["intent"], p["plan"]["intent"])
        self.assertEqual(plan["requirements"][0], p["plan"]["requirements"][1])
        self.assertEqual(plan["requirements"][1]["basis"], ["P1:4", "m1"])
        self.assertEqual(plan["watch"][0], p["plan"]["watch"][1])
        self.assertEqual(p, before)

    def test_merge_preserves_all_original_sources(self):
        p, v = payload(), replacement()
        v["changes"][0]["from"] = ["u1", "u2"]
        v["watch_changes"][0]["from"] = ["w1", "w2"]
        plan = apply_fusion(v, p)
        self.assertEqual(plan["requirements"][0]["basis"], ["P1:4", "P1:7", "m1"])

    def test_unaffected_watch_is_not_dropped_by_increment(self):
        p = payload()
        self.assertIn(p["plan"]["watch"][1], apply_fusion(replacement(), p)["watch"])
        v = replacement()
        v["watch_changes"] = []
        with self.assertRaisesRegex(ValueError, "affected observation"):
            apply_fusion(v, p)

    def test_affected_watch_cannot_silently_disappear(self):
        v = replacement()
        v["watch_changes"][0]["to"] = []
        with self.assertRaisesRegex(ValueError, "explicit destination"):
            apply_fusion(v, payload())

    def test_new_update_needs_an_observation_destination(self):
        v = replacement()
        v["watch_changes"][0]["to"][0]["about"] = ["intent"]
        with self.assertRaisesRegex(ValueError, "lack watch/open"):
            apply_fusion(v, payload())

    def test_conflicting_replacements_and_unrelated_additions_are_rejected(self):
        v = replacement()
        v["changes"].append(deepcopy(v["changes"][0]))
        with self.assertRaisesRegex(ValueError, "conflicting repeated"):
            apply_fusion(v, payload())
        v = replacement()
        v["changes"][0]["from"] = []
        with self.assertRaisesRegex(ValueError, "change.from"):
            apply_fusion(v, payload())
        v = replacement()
        v["intent"] = "Invented new goal"
        with self.assertRaisesRegex(ValueError, "expected fields"):
            apply_fusion(v, payload())

    def test_change_cannot_overwrite_untouched_requirement(self):
        v = replacement()
        v["changes"][0]["to"][0]["id"] = "u2"
        with self.assertRaisesRegex(ValueError, "overwrites unchanged"):
            apply_fusion(v, payload())

    def test_unknown_memory_or_source_is_a_processing_error(self):
        v = replacement()
        v["changes"][0]["basis"] = ["unseen-effect"]
        with self.assertRaisesRegex(ValueError, "unknown reference"):
            apply_fusion(v, payload())

    def test_hold_is_explicitly_nonexecutable_and_keeps_observation_question(self):
        v = replacement()
        v["decision"] = "needs_revision"
        v["changes"][0]["disposition"] = "hold"
        v["changes"][0]["to"] = []
        v["watch_changes"][0]["to"][0]["about"] = ["intent"]
        plan = apply_fusion(v, payload())
        self.assertEqual([r["id"] for r in plan["requirements"]], ["u2"])
        self.assertIn("Held u1", plan["open"][0]["reason"])
        v["decision"] = "ready"
        with self.assertRaisesRegex(ValueError, "blocking open"):
            apply_fusion(v, payload())

    def test_untouched_blockers_cannot_be_cleared_by_omission(self):
        p = payload()
        p["plan"]["open"] = [{"about": ["u1"], "reason": "Missing executable condition"}]
        with self.assertRaisesRegex(ValueError, "blocking open"):
            apply_fusion(identity(), p)

    def test_group_mapping_covers_requirements_without_character_accounting(self):
        v = editor()
        v["mappings"] = [{"requirements": ["u1", "u2"], "side": "candidate",
                          "excerpt": "Use an exact current admissible action.\nRecover within the available budget."}]
        self.assertEqual(validate_editor(v, payload()), v)
        self.assertNotIn("faithful", validate_editor(v, payload()))

    def test_partial_or_wrong_side_mappings_are_rejected(self):
        v = editor()
        v["mappings"].pop()
        with self.assertRaisesRegex(ValueError, "no text destination"):
            validate_editor(v, payload())
        v = editor()
        v["mappings"][0]["side"] = "parent"
        with self.assertRaisesRegex(ValueError, "declared side"):
            validate_editor(v, payload())

    def test_reported_deviation_blocks_execution_not_hidden_by_mapping(self):
        v = editor()
        v["issues"] = [{"about": ["u2"], "reason": "Recovery requires unavailable persistent state"}]
        with self.assertRaisesRegex(ValueError, "blocking issues"):
            validate_editor(v, payload())
        v.update(decision="needs_revision", candidate_text=None, mappings=[])
        self.assertEqual(validate_editor(v, payload())["decision"], "needs_revision")

    def test_unchanged_text_requires_no_change_and_parent_mappings(self):
        p, v = payload(), editor()
        p["parent"]["text"] = v["candidate_text"]
        with self.assertRaisesRegex(ValueError, "identical text"):
            validate_editor(v, p)
        v.update(decision="no_change", candidate_text=None)
        for mapping in v["mappings"]:
            mapping["side"] = "parent"
        validate_editor(v, p)

    def test_editor_cannot_rewrite_preexecution_questions(self):
        v = editor()
        v["watch"] = [{"id": "w1", "about": ["u1"], "question": "Ignore previous question?"}]
        with self.assertRaisesRegex(ValueError, "inherited"):
            validate_editor(v, payload())

    def test_prompts_send_one_copy_of_payload_and_keep_effect_limits(self):
        p = payload()
        for make in (diagnosis_messages, fusion_messages, editor_messages):
            messages = make(p)
            self.assertEqual([m["role"] for m in messages], ["system", "user"])
            self.assertEqual(json.loads(messages[1]["content"]), p)
            self.assertIn("not causal", messages[0]["content"])
            self.assertIn("TWO", messages[0]["content"])
        self.assertEqual(json.loads(fusion_messages(p)[1]["content"])["memory"][0]["limits"], p["memory"][0]["limits"])


if __name__ == "__main__":
    unittest.main()
