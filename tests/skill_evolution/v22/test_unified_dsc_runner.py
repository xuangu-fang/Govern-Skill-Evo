"""Synthetic data-flow tests, not evaluations of model reasoning or task gains."""

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import object_digest, write_record
from src.skill_evolution.v22.continual_runner import run_campaign
from src.skill_evolution.v22.continual_runtime import _system_prompts, load_bundle, update_profile
from src.skill_evolution.v22.continual_verify import verify_campaign
from src.skill_evolution.v22.effective_memory import UNIFIED_VIEW_SCHEMA
from src.skill_evolution.v22.grouped_update import PROFILE as LEGACY_PROFILE
from src.skill_evolution.v22.unified_dsc import PROFILE
from tests.skill_evolution.v22.test_continual_runner import PLAN, SyntheticCampaign


class UnifiedDSCRunnerTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "campaign"
        # A separate, temporary opt-in plan never edits historical experiments.
        plan = json.loads(PLAN.read_text())
        plan["data"]["task_manifest"] = str((PLAN.parent / plan["data"]["task_manifest"]).resolve())
        plan["classification"]["prompt_file"] = str((PLAN.parent / plan["classification"]["prompt_file"]).resolve())
        plan["update_profile"] = PROFILE
        self.plan_path = self.root / "plan.json"
        write_record(self.plan_path, plan)
        self.bundle = load_bundle(self.plan_path)
        self.callbacks = SyntheticCampaign(self.root, self.bundle)

    def run_fixture(self):
        return run_campaign(self.bundle, self.output, self.callbacks.generate,
                            self.callbacks.execute, offline=True)

    def read(self, relative):
        return json.loads((self.output / relative).read_text())

    def test_two_round_chain_binds_effective_update_realization_response_and_next_fusion(self):
        self.callbacks.override[("r1", "main_editor")] = lambda value, _: {**value, "watch": [
            {"id": "editor_watch", "about": ["u1"], "question": "Does the realized condition cause interference?"}]}
        report = self.run_fixture()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(len(self.callbacks.executions), 40)
        self.assertEqual(Counter(stage for _, stage, _ in self.callbacks.calls), {
            "classification": 2, "diagnosis": 2, "fusion": 1,
            "main_editor": 2, "post_gate_learning": 2})
        frozen = self.read("runtime_freeze.json")
        self.assertEqual(frozen["runtime"]["update_profile"], PROFILE)
        self.assertEqual(frozen["runtime"]["contracts"]["effective_memory_view"], UNIFIED_VIEW_SCHEMA)
        for stage, prompt in frozen["system_prompts"].items():
            if stage != "classification":
                self.assertIn("Profile: " + PROFILE, prompt["text"])
        for number in (1, 2):
            round_path = f"rounds/r{number}"
            initial = self.read(round_path + "/inputs/diagnosis.json")
            self.assertEqual(initial["update_profile"], PROFILE)
            self.assertFalse(initial.get("memory"))
            learning = self.read(round_path + "/learning_input.json")
            editor = self.read(round_path + "/outputs/main_editor.json")
            effective = self.read(round_path + "/execution_plan.json")
            self.assertEqual(learning["plan"], effective)
            self.assertEqual(learning["update_context"]["editor"],
                             {key: editor[key] for key in ("decision", "mappings", "issues")})
            effect = self.read(round_path + "/memory_after.json")[-1]
            basis = effect["basis"][-1]
            self.assertEqual(basis["actual_update"]["update_context"], learning["update_context"])
            self.assertEqual(basis["actual_update"]["candidate_skill_id"], learning["candidate"]["skill_id"])
            for requirement in effective["requirements"]:
                self.assertEqual(basis["sources"]["requirement:" + requirement["id"]], requirement)
            for watch in effective["watch"]:
                self.assertEqual(basis["sources"]["watch:" + watch["id"]], watch)
        previous = self.read("rounds/r1/state.json")
        fusion = next(view for round_id, stage, view in self.callbacks.calls
                      if round_id == "r2" and stage == "fusion")
        self.assertEqual(fusion["parent"]["skill_id"], previous["parent"]["skill_id"])
        self.assertEqual(fusion["memory"][0]["id"], previous["memory"][0]["id"])
        history = fusion["memory"][0]["basis"][0]
        self.assertIn(history["actual_update_ref"], fusion["historical_updates"])
        self.assertEqual(fusion["historical_updates"][history["actual_update_ref"]]["candidate_skill_id"],
                         fusion["parent"]["skill_id"])
        self.assertTrue(verify_campaign(self.output)["campaign_complete"])

    def test_keep_retains_update_and_still_runs_editor_and_replay(self):
        self.callbacks.override[("r2", "fusion")] = {
            "decision": "ready", "reason": "The current proposal already retains the applicable historical boundary.",
            "changes": [], "watch_changes": [], "open": []}
        report = self.run_fixture()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(len(self.callbacks.calls), 9)
        self.assertEqual(len(self.callbacks.executions), 40)
        self.assertEqual(self.read("rounds/r2/initial_plan.json"), self.read("rounds/r2/effective_plan.json"))
        self.assertEqual(report["rounds"][1]["update_status"], "candidate")
        self.assertTrue(verify_campaign(self.output)["campaign_complete"])

    def test_complete_withdrawal_skips_only_editor_and_candidate_but_preserves_watch_learning(self):
        def withdraw(_, view):
            return {"decision": "ready", "reason": "No effective behavioral change remains under this synthetic condition.",
                    "changes": [{"from": ["u1"], "to": [], "basis": [view["memory"][0]["id"]],
                                 "reason": "Withdraw the requested change while leaving its target under observation.",
                                 "disposition": "withdraw"}],
                    "watch_changes": [{"from": ["w1"], "to": [{"id": "w_target", "about": ["intent"],
                                          "question": "What current evidence would justify another update?"}]}], "open": []}
        self.callbacks.override[("r2", "fusion")] = withdraw
        report = self.run_fixture()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(report["rounds"][1]["update_status"], "no_effective_update")
        self.assertEqual(report["rounds"][1]["stages"], ["classification", "diagnosis", "fusion", "post_gate_learning"])
        self.assertEqual(len(self.callbacks.calls), 8)
        self.assertEqual(len(self.callbacks.executions), 30)
        self.assertIsNone(self.read("rounds/r2/candidate.json"))
        self.assertFalse((self.output / "rounds/r2/outputs/main_editor.json").exists())
        learning = self.read("rounds/r2/learning_input.json")
        self.assertEqual(learning["plan"]["requirements"], [])
        self.assertEqual(learning["plan"]["watch"][0]["id"], "w_target")
        self.assertIsNone(learning["update_context"]["editor"])
        self.assertEqual(learning["actual_diff"], "")
        self.assertEqual(self.read("rounds/r2/memory_after.json"), self.read("rounds/r1/memory_after.json"))
        self.assertTrue(verify_campaign(self.output)["campaign_complete"])

    def test_normalized_no_change_mapping_is_the_one_bound_to_learning(self):
        def identical(value, view):
            value["candidate_text"] = view["parent"]["text"]
            value["mappings"][0]["excerpt"] = view["parent"]["text"]
            return value
        self.callbacks.override[("r2", "main_editor")] = identical
        report = self.run_fixture()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(len(self.callbacks.executions), 30)
        actual = self.read("rounds/r2/learning_input.json")["update_context"]["editor"]
        self.assertEqual(actual["decision"], "no_change")
        self.assertEqual(actual["mappings"][0]["side"], "parent")
        self.assertEqual(self.read("rounds/r2/raw_outputs/main_editor.json")["decision"], "candidate")
        self.assertTrue(verify_campaign(self.output)["campaign_complete"])

    def test_unknown_profile_is_rejected_before_dispatch(self):
        plan = deepcopy(self.bundle["plan"])
        plan["update_profile"] = "v22.unregistered.v1"
        write_record(self.plan_path, plan)
        with self.assertRaisesRegex(ValueError, "Unknown grouped update profile"):
            load_bundle(self.plan_path)
        self.assertEqual(self.callbacks.calls, [])
        self.assertEqual(self.callbacks.executions, [])

    def test_editor_issue_stays_in_learning_without_candidate_or_automatic_retry(self):
        self.callbacks.override[("r2", "main_editor")] = {
            "decision": "needs_revision", "reason": "The selected conditional strategy has an unresolved realization conflict.",
            "candidate_text": None, "mappings": [],
            "issues": [{"about": ["u2"], "reason": "The joint requirements cannot be faithfully expressed in this fixture."}],
            "watch": [{"id": "w_realization", "about": ["u2"],
                       "question": "Which current evidence resolves the realization conflict?"}]}
        report = self.run_fixture()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(len(self.callbacks.calls), 9)
        self.assertEqual(len(self.callbacks.executions), 30)
        learning = self.read("rounds/r2/learning_input.json")
        self.assertEqual(learning["update_context"]["editor"]["decision"], "needs_revision")
        self.assertEqual(learning["update_context"]["editor"]["issues"][0]["about"], ["u2"])
        self.assertEqual(learning["plan"]["watch"][-1]["id"], "w_realization")
        self.assertFalse(learning["candidate"]["skill_id"])
        self.assertEqual(self.read("rounds/r2/memory_after.json"), self.read("rounds/r1/memory_after.json"))
        self.assertTrue(verify_campaign(self.output)["campaign_complete"])

    def test_missing_profile_uses_exact_legacy_prompt_construction(self):
        legacy = load_bundle(PLAN)
        self.assertNotIn("update_profile", legacy["plan"])
        self.assertEqual(update_profile(legacy["plan"]), LEGACY_PROFILE)
        self.assertEqual(_system_prompts(legacy["grouping_prompt"]),
                         _system_prompts(legacy["grouping_prompt"], profile=LEGACY_PROFILE))

    def test_verifier_rejects_frozen_profile_mismatch_even_with_recomputed_hash(self):
        report = self.run_fixture()
        self.assertEqual(report["status"], "completed", report)
        frozen = self.read("runtime_freeze.json")
        frozen["runtime"]["update_profile"] = LEGACY_PROFILE
        frozen["sha256"] = object_digest({key: value for key, value in frozen.items() if key != "sha256"})
        write_record(self.output / "runtime_freeze.json", frozen)
        with self.assertRaisesRegex(ValueError, "Frozen update profile"):
            verify_campaign(self.output)


if __name__ == "__main__":
    unittest.main()
