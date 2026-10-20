"""Authored, offline update-flow checks for stable historical-reference ownership.

These fixtures test that the new identity profile preserves the existing algorithm's
expressive routes. They do not evaluate model reasoning, natural-language fidelity,
causal attribution or environment gains. No experiment API or environment is used.
"""

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.compact_learning import coverage_index
from src.skill_evolution.v22.continual_runner import run_campaign
from src.skill_evolution.v22.continual_runtime import load_bundle
from src.skill_evolution.v22.continual_verify import verify_campaign
from src.skill_evolution.v22.effective_memory import effective_consumption_payload
from src.skill_evolution.v22.grouped_update import (
    compile_update, grouped_messages, learn_grouped_memory, update_payload,
)
from src.skill_evolution.v22.memory_identity import PROFILE, VIEW_SCHEMA
from src.skill_evolution.v22.unified_dsc import PROFILE as V1_PROFILE
from tests.skill_evolution.v22.test_continual_runner import PLAN, SyntheticCampaign
from tests.skill_evolution.v22 import test_unified_dsc_mechanism as fixtures


class DscRefinementFlowTests(unittest.TestCase):
    # Reuse only record/fixture helpers, without inheriting any old test methods.
    setUp = fixtures.UnifiedDscMechanismTests.setUp
    record = fixtures.UnifiedDscMechanismTests.record
    batch = fixtures.UnifiedDscMechanismTests.batch
    edit = fixtures.UnifiedDscMechanismTests.edit
    response = fixtures.UnifiedDscMechanismTests.response
    next_context = fixtures.UnifiedDscMechanismTests.next_context

    def inputs(self, context, parents, profile=PROFILE):
        return fixtures.UnifiedDscMechanismTests.inputs(self, context, parents, profile)

    def round_fixture(self, context=None, *, profile=PROFILE, extra_watch=False):
        return fixtures.UnifiedDscMechanismTests.round_fixture(
            self, context, profile=profile, extra_watch=extra_watch)

    def test_keep_and_bounded_exploration_still_realize_candidates(self):
        parents = self.batch(self.context, self.context["parent"], [False] * 3)
        _, current, original = self.inputs(self.context, parents)
        for exploratory in (False, True):
            with self.subTest(exploratory=exploratory):
                update = deepcopy(original)
                if exploratory:
                    update["plan"]["requirements"][0]["text"] = (
                        "When visible prerequisite evidence is absent, try one available "
                        "status query; use its result for dependent work while preserving "
                        "already valid evidence. Benefit outside observed conditions is unknown.")
                    update["plan"]["watch"][0]["question"] = (
                        "When missing evidence permits a query, does the exploratory "
                        "query improve the next decision without losing valid evidence?")
                frozen = deepcopy(update)
                plan = compile_update({
                    "decision": "ready", "reason": "Authored bounded draft remains reasonable; "
                    "unproven benefit does not require withdrawal.",
                    "changes": [], "watch_changes": [], "open": [],
                }, update)
                self.assertEqual(plan, frozen["plan"])
                candidate, effective, editor = self.edit(update_payload(self.context, current, plan))
                self.assertIsNotNone(candidate)
                self.assertEqual(candidate["text"], editor["candidate_text"])
                self.assertEqual(effective["requirements"], plan["requirements"])
                self.assertEqual(update, frozen)

    def test_authored_direction_bidirectional_scale_and_coupling_are_realizable(self):
        first = self.round_fixture()
        memory, receipt = learn_grouped_memory(first["payload"], self.response(first["payload"]))
        context = self.next_context(first, memory, receipt)
        parents = self.batch(context, context["parent"], [False, True, False])
        _, current, update = self.inputs(context, parents)
        cases = (
            ("direction", ["u1"], "Use a fresh visible status receipt rather than another query "
             "to establish a prerequisite; query only when the receipt is absent or stale."),
            ("scale_narrow", ["u1"], "Query only the affected prerequisite when its visible "
             "evidence is stale; retain otherwise valid evidence."),
            ("scale_expand", ["u1"], "Query the affected prerequisite when its visible "
             "evidence is stale or absent before dependent work."),
            ("coupling", ["u1", "u2"], "Reuse valid visible evidence until a dependency "
             "changes; then refresh the affected prerequisite before dependent work."),
        )
        for name, replaced, text in cases:
            with self.subTest(case=name):
                watched = ["u2", "transformed"] if replaced == ["u1"] else ["transformed"]
                plan = compile_update({
                    "decision": "ready", "reason": "Authored generic response relation.",
                    "changes": [{"from": replaced, "to": [{"id": "transformed", "text": text}],
                                 "basis": [memory[0]["id"]], "disposition": "replace",
                                 "reason": "The fixture supplies conditions for this transformation."}],
                    "watch_changes": [{"from": ["w_joint"], "to": [
                        {"id": "w_transformed", "about": watched,
                         "question": "Does the changed choice work under its condition and retain dependencies?"}]}],
                    "open": [],
                }, update)
                candidate, effective, _ = self.edit(update_payload(context, current, plan))
                requirement = next(row for row in effective["requirements"] if row["id"] == "transformed")
                self.assertIn(memory[0]["id"], requirement["basis"])
                self.assertEqual(effective["intent"], update["plan"]["intent"])
                self.assertIn(update["plan"]["requirements"][2], effective["requirements"])
                self.assertIn(text, candidate["text"])
                self.assertEqual(effective["watch"][-1]["about"], watched)

    def test_missing_opportunity_and_nonexecution_do_not_require_negative_effects(self):
        payload = self.round_fixture()["payload"]
        for reason in (
            "No relevant prerequisite-change opportunity was established; the response remains untested.",
            "No prerequisite-refresh action was executed in these traces; execution of the proposed strategy remains untested.",
        ):
            with self.subTest(reason=reason):
                response = {"findings": [], "open": [
                    {"about": [row["id"]], "reason": reason} for row in payload["plan"]["watch"]
                ], "memory_delta": []}
                memory, _ = learn_grouped_memory(payload, response)
                self.assertEqual(memory, [])
                for entry in coverage_index(response, payload).values():
                    self.assertEqual(entry["status"], "addressed_with_limits")
                    self.assertEqual(entry["findings"], [])
                    self.assertEqual(set(entry["not_assessed_runs"]), set(payload["runs"]))

    def test_authored_partial_revision_expands_knowledge_without_erasing_remainder(self):
        first = self.round_fixture()
        memory, receipt = learn_grouped_memory(first["payload"], self.response(first["payload"]))
        old = deepcopy(memory[0])
        second = self.round_fixture(self.next_context(first, memory, receipt))
        response = self.response(second["payload"])
        response["memory_delta"][0].update(
            replace=[old["id"]],
            claim="The authored joint response now covers changed dependencies; unavailable evidence remains untested.",
            limits=["Unavailable evidence remains untested."],
            retire_limits=[{"effect_id": old["id"], "index": 0,
                            "reason": "New fixture evidence covers dependencies; the unresolved remainder is retained.",
                            "findings": ["f1"]}],
        )
        revised, _ = learn_grouped_memory(second["payload"], response)
        effect = revised[0]
        self.assertEqual(effect["limits"], [old["limits"][1], "Unavailable evidence remains untested."])
        self.assertEqual(effect["basis"][0], old["basis"][0])
        self.assertEqual(effect["retired_limits"][0]["limit"], old["limits"][0])
        self.assertEqual(effect["supersedes"], [old["id"]])
        view = effective_consumption_payload({**second["payload"], "memory": revised})
        self.assertEqual(set(view["historical_updates"]), {"H1", "H2"})
        self.assertNotEqual(view["historical_sources"]["H1::C1:1"]["run_id"],
                            view["historical_sources"]["H2::C1:1"]["run_id"])

    def test_identity_profile_keeps_stage_rules_and_output_shapes(self):
        round_ = self.round_fixture()
        prior_round = self.round_fixture(profile=V1_PROFILE)
        for stage, key in (("diagnosis", "current"), ("fusion", "update"),
                           ("editor", "update"), ("learn", "payload")):
            with self.subTest(stage=stage):
                previous = grouped_messages(stage, prior_round[key])[0]["content"]
                current = grouped_messages(stage, round_[key])[0]["content"]
                self.assertEqual(current, previous.replace("Profile: " + V1_PROFILE,
                                                           "Profile: " + PROFILE, 1))


class DscRefinementCampaignTests(unittest.TestCase):
    def test_two_round_identity_profile_keeps_nine_callbacks_and_update_response_chain(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = json.loads(PLAN.read_text())
            plan["data"]["task_manifest"] = str((PLAN.parent / plan["data"]["task_manifest"]).resolve())
            plan["classification"]["prompt_file"] = str((PLAN.parent / plan["classification"]["prompt_file"]).resolve())
            plan["update_profile"] = PROFILE
            plan_file = root / "plan.json"
            write_record(plan_file, plan)
            bundle = load_bundle(plan_file)
            callbacks = SyntheticCampaign(root, bundle)
            callbacks.override[("r1", "main_editor")] = lambda value, _: {**value, "watch": [
                {"id": "editor_watch", "about": ["u1"],
                 "question": "Does the realized condition interfere with preserved behavior?"}]}
            output = root / "campaign"
            report = run_campaign(bundle, output, callbacks.generate, callbacks.execute, offline=True)
            self.assertEqual(report["status"], "completed", report)
            self.assertEqual(len(callbacks.calls), 9)
            self.assertEqual(Counter(stage for _, stage, _ in callbacks.calls), {
                "classification": 2, "diagnosis": 2, "fusion": 1,
                "main_editor": 2, "post_gate_learning": 2})
            # These are fixture callbacks producing JSON, not environment episodes.
            self.assertEqual(len(callbacks.executions), 40)
            read = lambda relative: json.loads((output / relative).read_text())
            frozen = read("runtime_freeze.json")
            self.assertEqual(frozen["runtime"]["update_profile"], PROFILE)
            self.assertEqual(frozen["runtime"]["contracts"]["effective_memory_view"], VIEW_SCHEMA)
            for stage, prompt in frozen["system_prompts"].items():
                if stage != "classification":
                    self.assertIn("Profile: " + PROFILE, prompt["text"])
            for number in (1, 2):
                prefix = f"rounds/r{number}"
                learning = read(prefix + "/learning_input.json")
                editor = read(prefix + "/outputs/main_editor.json")
                effective = read(prefix + "/execution_plan.json")
                self.assertEqual(learning["plan"], effective)
                self.assertEqual(learning["update_context"]["editor"],
                                 {key: editor[key] for key in ("decision", "mappings", "issues")})
                basis = read(prefix + "/memory_after.json")[-1]["basis"][-1]
                self.assertEqual(basis["actual_update"]["update_context"], learning["update_context"])
                self.assertEqual(basis["actual_update"]["update_context"]["actual_diff"], learning["actual_diff"])
                for requirement in effective["requirements"]:
                    self.assertEqual(basis["sources"]["requirement:" + requirement["id"]], requirement)
                for watch in effective["watch"]:
                    self.assertEqual(basis["sources"]["watch:" + watch["id"]], watch)
            fusion = next(view for round_id, stage, view in callbacks.calls
                          if round_id == "r2" and stage == "fusion")
            shared = fusion["memory"][0]["basis"][0]["actual_update_ref"]
            self.assertEqual(fusion["historical_updates"][shared]["candidate_skill_id"],
                             fusion["parent"]["skill_id"])
            self.assertTrue(verify_campaign(output)["campaign_complete"])


if __name__ == "__main__":
    unittest.main()
