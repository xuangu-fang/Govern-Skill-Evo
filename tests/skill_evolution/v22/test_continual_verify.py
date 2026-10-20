"""Offline campaign archive verification, using the runner's synthetic callbacks."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tests.skill_evolution.v22.test_continual_runner import PLAN, SyntheticCampaign
from src.skill_evolution.v22.continual_runner import run_campaign
from src.skill_evolution.v22.continual_runtime import load_bundle
from src.skill_evolution.v22.continual_verify import verify_campaign


class ContinualVerifyTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "campaign"
        self.bundle = load_bundle(PLAN)
        self.callbacks = SyntheticCampaign(self.root, self.bundle)

    def run_fixture(self):
        return run_campaign(self.bundle, self.output, self.callbacks.generate, self.callbacks.execute, offline=True)

    def test_completed_archive_replays_lineage_and_learning_without_live_dependencies(self):
        self.callbacks.override[("r1", "main_editor")] = lambda value, _: {**value, "watch": [
            {"id": "editor_watch", "about": ["u1"], "question": "Does the realized wording add interference?"}]}
        self.assertEqual(self.run_fixture()["status"], "completed")
        with patch("src.skill_evolution.v22.continual_runtime.check_runtime", side_effect=AssertionError("Do not inspect current sources")):
            result = verify_campaign(self.output)
        self.assertTrue(result["artifact_valid"])
        self.assertTrue(result["campaign_complete"])
        self.assertEqual(result["published_rounds"], 2)
        self.assertEqual(result["semantic_call_records"], 9)

    def test_interrupted_learning_retains_valid_prior_publication_and_is_incomplete(self):
        self.callbacks.interrupt_stage = ("r2", "post_gate_learning")
        self.assertEqual(self.run_fixture()["status"], "interrupted")
        result = verify_campaign(self.output)
        self.assertFalse(result["campaign_complete"])
        self.assertEqual(result["published_rounds"], 1)
        self.assertEqual(result["incomplete_rounds"], 1)

    def test_failed_semantic_validation_can_be_a_valid_incomplete_archive(self):
        self.callbacks.override[("r1", "post_gate_learning")] = {"findings": [], "open": [], "memory_delta": []}
        self.assertEqual(self.run_fixture()["status"], "error")
        self.assertTrue(verify_campaign(self.output)["artifact_valid"])
        self.assertEqual(verify_campaign(self.output)["published_rounds"], 0)

    def test_no_change_has_program_learning_and_no_candidate_scores(self):
        for round_id in ("r1", "r2"):
            self.callbacks.override[(round_id, "diagnosis")] = {"decision": "no_change", "reason": "No justified edit.", "plan": None}
        self.assertEqual(self.run_fixture()["status"], "completed")
        result = verify_campaign(self.output)
        self.assertEqual(result["semantic_call_records"], 4)
        self.assertTrue(result["campaign_complete"])

    def test_snapshot_and_frozen_gate_tampering_are_rejected(self):
        self.assertEqual(self.run_fixture()["status"], "completed")
        freeze = json.loads((self.output / "runtime_freeze.json").read_text())
        snapshot = Path(freeze["sources"][0]["snapshot"])
        original = snapshot.read_bytes()
        snapshot.write_bytes(original + b"\nchanged\n")
        with self.assertRaisesRegex(ValueError, "snapshot"):
            verify_campaign(self.output)
        snapshot.write_bytes(original)
        gate = self.output / "rounds/r1/gate.json"
        gate.write_text(gate.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "Frozen artifact"):
            verify_campaign(self.output)

    def test_publication_pointer_tampering_is_rejected_even_when_states_are_valid(self):
        self.assertEqual(self.run_fixture()["status"], "completed")
        report_path = self.output / "report.json"
        report = json.loads(report_path.read_text())
        report["latest_state"] = str((self.output / "state0.json").resolve())
        report_path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "Latest state"):
            verify_campaign(self.output)


if __name__ == "__main__":
    unittest.main()
