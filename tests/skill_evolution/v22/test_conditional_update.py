"""Evidence routing checks; prompt text checks do not establish model compliance."""

from copy import deepcopy
import json
import unittest

from src.skill_evolution.v22.compact_update import (
    DIAGNOSIS_SHAPE, EDITOR_SHAPE, FUSION_SHAPE, apply_fusion,
)
from src.skill_evolution.v22.conditional_update import (
    PROFILE, diagnosis_messages_conditional, proposal_messages, realization_messages,
)
from src.skill_evolution.v22.effective_update import (
    editor_messages_effective, fusion_messages_effective,
)
from tests.skill_evolution.v22.test_effective_update import increment, payload


class ConditionalUpdateTests(unittest.TestCase):
    def test_planner_arms_receive_byte_identical_complete_evidence_views(self):
        value = payload()
        before = deepcopy(value)
        direct = proposal_messages(value, "direct")
        conditioned = proposal_messages(value, "conditioned")
        self.assertEqual(direct[1], conditioned[1])
        self.assertNotEqual(direct[0], conditioned[0])
        view = json.loads(direct[1]["content"])
        for key in ("parent", "plan", "runs", "sources", "capabilities"):
            self.assertEqual(view[key], value[key])
        self.assertEqual(len(view["memory"][0]["limits"]), len(value["memory"][0]["limits"]))
        self.assertIn("counterexample", view["memory"][0]["limits"][0])
        self.assertTrue(view["memory"][0]["basis"][0]["sources"])
        self.assertTrue(view["historical_contexts"])
        self.assertEqual(value, before)

    def test_shared_editor_retains_all_memory_even_when_not_cited_by_requirements(self):
        value = payload()
        other = deepcopy(value["memory"][0])
        other["id"] = "uncited-effect"
        other["claim"] = "An earlier alternative has a limited scope."
        value["memory"].append(other)
        before = deepcopy(value)
        planner_view = json.loads(proposal_messages(value, "direct")[1]["content"])
        editor_view = json.loads(realization_messages(value)[1]["content"])
        self.assertEqual(editor_view, planner_view)
        self.assertEqual([row["id"] for row in editor_view["memory"]],
                         ["old-context:m1", "uncited-effect"])
        self.assertEqual(value, before)

    def test_empty_memory_has_a_valid_shared_path(self):
        value = payload()
        value["memory"] = []
        for builder in (lambda p: proposal_messages(p, "direct"),
                        lambda p: proposal_messages(p, "conditioned"), realization_messages):
            view = json.loads(builder(value)[1]["content"])
            self.assertEqual(view["memory"], [])
            self.assertEqual(view["runs"], value["runs"])
            self.assertEqual(view["plan"], value["plan"])

    def test_diagnosis_receives_current_input_and_separates_goal_from_route(self):
        current = payload()
        current.pop("memory")
        current.pop("plan")
        messages = diagnosis_messages_conditional(current)
        self.assertEqual(json.loads(messages[1]["content"]), current)
        self.assertIn("not a particular route for reaching it", messages[0]["content"])
        self.assertIn("a task actually requiring delivery", messages[0]["content"])

    def test_no_new_output_fields_and_old_compiler_accepts_both_routes(self):
        value = payload()
        for messages, shape in (
            (diagnosis_messages_conditional(value), DIAGNOSIS_SHAPE),
            (proposal_messages(value, "direct"), FUSION_SHAPE),
            (proposal_messages(value, "conditioned"), FUSION_SHAPE),
            (realization_messages(value), EDITOR_SHAPE),
        ):
            self.assertEqual(json.loads(messages[0]["content"].split("\nOutput shape:\n", 1)[1]), shape)
            self.assertIn(PROFILE, messages[0]["content"])
        identity = {"decision": "ready", "reason": "Already covers the supported branch.",
                    "changes": [], "watch_changes": [], "open": []}
        self.assertEqual(apply_fusion(identity, value), value["plan"])
        changed = apply_fusion(increment(), value)
        self.assertEqual(changed["intent"], value["plan"]["intent"])
        self.assertEqual(changed["requirements"][0], value["plan"]["requirements"][1])

    def test_conditioning_retains_other_state_continuation_without_task_hardcoding(self):
        prompt = proposal_messages(payload(), "conditioned")[0]["content"]
        for clause in ("relaxation only in the observed applicable conditions",
                       "known completion/recovery path outside that support",
                       "cannot erase known counterexamples", "When no completion is reported",
                       "Preserve the goal while replacing its strategy",
                       "Correcting a factual count", "Identity is legitimate"):
            self.assertIn(clause, prompt)
        for instance in ("train:0000", "train:0012", "u6", "alarmclock", "desklamp"):
            self.assertNotIn(instance, prompt)
        direct = proposal_messages(payload(), "direct")[0]["content"]
        self.assertIn("produce the best", direct)
        self.assertIn("change, coordinate or leave requirements unchanged", direct)
        self.assertIn("counterexamples and remaining limits", direct)

    def test_editor_inherits_watch_programmatically_without_mutating_old_prompts(self):
        value = payload()
        before = deepcopy(value)
        old = (fusion_messages_effective(value), editor_messages_effective(value))
        prompt = realization_messages(value)[0]["content"]
        self.assertIn("program automatically inherits plan.watch", prompt)
        self.assertIn("Never copy inherited watch entries", prompt)
        self.assertEqual(value, before)
        self.assertEqual(old, (fusion_messages_effective(value), editor_messages_effective(value)))

    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "direct or conditioned"):
            proposal_messages(payload(), "historical")


if __name__ == "__main__":
    unittest.main()
