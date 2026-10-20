"""Authored generic contract examples; no model call or environment execution."""

from copy import deepcopy
import json
import unittest

from src.skill_evolution.v22 import contract_alignment, unified_dsc
from src.skill_evolution.v22.compact_update import FUSION_SHAPE
from src.skill_evolution.v22.effective_memory import EFFECTIVE_SHAPE, validate_effective_learning
from src.skill_evolution.v22.grouped_update import (
    accept_diagnosis, compile_update, grouped_messages, realize_editor, update_payload,
)
from tests.skill_evolution.v22 import test_unified_dsc_mechanism as fixtures


class ContractAlignmentShapeTests(unittest.TestCase):
    setUp = fixtures.UnifiedDscMechanismTests.setUp
    record = fixtures.UnifiedDscMechanismTests.record
    batch = fixtures.UnifiedDscMechanismTests.batch
    inputs = fixtures.UnifiedDscMechanismTests.inputs
    edit = fixtures.UnifiedDscMechanismTests.edit
    round_fixture = fixtures.UnifiedDscMechanismTests.round_fixture

    def fixture(self):
        return self.round_fixture(profile=contract_alignment.PROFILE)

    def test_actual_diagnosis_and_editor_shapes_share_normalized_update(self):
        fixture = self.fixture()
        current = fixture["current"]
        diagnosis_messages = grouped_messages("diagnosis", current)
        diagnosis = json.loads(diagnosis_messages[0]["content"].rsplit("Output shape: ", 1)[1])
        diagnosis["decision"] = "revise"
        diagnosis["plan"]["requirements"][0]["basis"] = ["P1:1"]
        diagnosis["plan"]["requirements"][0]["text"] = "Inspect the visible prerequisite when it is stale."
        diagnosis["plan"]["open"] = []  # This authored example has no construction blocker.
        raw = deepcopy(diagnosis)
        accepted = accept_diagnosis(diagnosis, current)
        group = current["runs"]["P1"]["decision_group"]
        self.assertEqual(accepted["plan"]["requirements"][0]["basis"], ["P1:1", group])
        self.assertEqual(diagnosis, raw)
        update = update_payload(fixture["context"], current, accepted["plan"])
        editor_messages = grouped_messages("editor", update)
        editor = json.loads(editor_messages[0]["content"].rsplit("Output shape: ", 1)[1])
        editor["decision"] = "candidate"
        editor["candidate_text"] = accepted["plan"]["requirements"][0]["text"]
        editor["mappings"][0]["side"] = "candidate"
        editor["mappings"][0]["excerpt"] = editor["candidate_text"]
        editor["issues"] = []  # The chosen executable requirement is fully realized.
        candidate, execution_plan = realize_editor(editor, update)
        self.assertEqual(candidate["text"], editor["mappings"][0]["excerpt"])
        self.assertEqual(execution_plan["requirements"], accepted["plan"]["requirements"])
        self.assertEqual(execution_plan["watch"][-1], editor["watch"][0])

    def test_actual_learning_message_append_shape_can_validate(self):
        payload = self.fixture()["payload"]
        messages = grouped_messages("learn", payload)
        shape = json.loads(messages[0]["content"].rsplit("Output shape: ", 1)[1])
        self.assertEqual(shape, contract_alignment.EFFECTIVE_SHAPE)
        self.assertEqual(shape["memory_delta"][0]["replace"], [])
        self.assertEqual(shape["memory_delta"][0]["retire_limits"], [])
        # Resolve illustrative references to the supplied synthetic evidence. The
        # append/retirement combination itself must require no correction.
        shape["findings"][0]["about"] = [row["id"] for row in payload["plan"]["watch"]]
        shape["findings"][0]["refs"] = ["P1:1", "C1:1"]
        shape["open"] = []
        self.assertEqual(validate_effective_learning(shape, payload), shape)
        # Older shape/message reconstruction remains intentionally untouched.
        self.assertTrue(EFFECTIVE_SHAPE["memory_delta"][0]["retire_limits"])
        self.assertEqual(set(shape["memory_delta"][0]), set(EFFECTIVE_SHAPE["memory_delta"][0]))

    def test_actual_fusion_message_distinguishes_operations_and_open_shape(self):
        update = self.fixture()["update"]
        messages = grouped_messages("fusion", update)
        system = messages[0]["content"]
        self.assertIn("changes.from is a nonempty list", system)
        self.assertIn("Only watch_changes.from=[]", system)
        self.assertIn('about=["intent"]', system)
        self.assertIn('"reason":"concrete unresolved blocker"', system)
        self.assertIn("full provenance", system)
        self.assertIn("NOT the Update's applicability", system)
        shape = json.loads(system.rsplit("Output shape: ", 1)[1])
        self.assertEqual(shape, FUSION_SHAPE)
        self.assertEqual(json.loads(messages[1]["content"])["plan"], update["plan"])
        # The shape uses illustrative IDs and enum alternatives; resolve those
        # placeholders without changing any object structure or operation rule.
        shape["decision"] = "ready"
        shape["changes"][0]["to"][0]["id"] = "u4"
        shape["changes"][0]["basis"] = ["P1:1"]
        shape["changes"][0]["disposition"] = "replace"
        shape["watch_changes"][0]["from"] = ["w_joint"]
        shape["watch_changes"][0]["to"][0].update(id="w4", about=["u4", "u2"])
        self.assertEqual(compile_update(shape, update)["requirements"][-1]["id"], "u4")

    def test_keep_add_watch_and_blocking_open_are_distinct_legal_routes(self):
        update = self.fixture()["update"]
        keep = {"decision": "ready", "reason": "Current conditional strategy already fits.",
                "changes": [], "watch_changes": [], "open": []}
        self.assertEqual(compile_update(keep, update), update["plan"])
        observe = deepcopy(keep)
        observe["watch_changes"] = [{"from": [], "to": [
            {"id": "w_new", "about": ["intent"], "question": "Is unrelated progress retained?"}]}]
        self.assertEqual(compile_update(observe, update)["watch"][-1]["id"], "w_new")
        blocked = deepcopy(keep)
        blocked.update(decision="needs_revision", open=[
            {"about": ["u1", "w_joint"], "reason": "A required distinction lacks visible evidence."}])
        self.assertEqual(compile_update(blocked, update)["open"], blocked["open"])

    def test_fusion_transformations_and_full_withdrawal_keep_observation_destinations(self):
        update = self.fixture()["update"]
        # These authored texts exercise the unchanged representational freedom;
        # they do not assert that a model will infer the transformations correctly.
        texts = [
            "Use an available alternative check when the original check cannot resolve the prerequisite.",
            "Check the prerequisite under either evidenced trigger, preserving unrelated progress.",
            "Check only the affected prerequisite when its visible evidence is stale.",
            "After the dependency-changing operation, revalidate before dependent work; preserve valid unrelated evidence.",
        ]
        for text in texts:
            with self.subTest(text=text):
                value = {"decision": "ready", "reason": "Authored D/S/C contract fixture.",
                         "changes": [{"from": ["u1", "u2"], "to": [{"id": "u4", "text": text}],
                                      "basis": ["P1:1", "P2:1"], "reason": "Comparable visible evidence.",
                                      "disposition": "replace"}],
                         "watch_changes": [{"from": ["w_joint"], "to": [
                             {"id": "w4", "about": ["u4"], "question": "Does the conditional choice work?"}]}],
                         "open": []}
                plan = compile_update(value, update)
                self.assertEqual(plan["requirements"][-1]["text"], text)
                bad = deepcopy(value)
                bad["changes"][0]["from"] = []
                with self.assertRaisesRegex(ValueError, "change.from"):
                    compile_update(bad, update)
        withdraw = {"decision": "ready", "reason": "Parent already satisfies this authored goal.",
                    "changes": [{"from": ["u1", "u2", "u3"], "to": [], "basis": ["P1:1"],
                                 "reason": "No effective update remains.", "disposition": "withdraw"}],
                    "watch_changes": [{"from": ["w_joint", "w_other"], "to": [
                        {"id": "w_goal", "about": ["intent"], "question": "What would justify another update?"}]}],
                    "open": []}
        plan = compile_update(withdraw, update)
        self.assertEqual(plan["requirements"], [])
        self.assertEqual(plan["watch"][0]["about"], ["intent"])

    def test_editor_authority_rules_remain_unchanged(self):
        system = grouped_messages("editor", self.fixture()["update"])[0]["content"]
        self.assertIn(unified_dsc.REALIZATION_RULES, system)
        self.assertIn("Do not strengthen a conditional permission into an obligation", system)
        self.assertIn("Unproven benefit alone is not an implementation blocker", system)


if __name__ == "__main__":
    unittest.main()
