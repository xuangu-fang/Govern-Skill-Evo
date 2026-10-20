"""Offline compact learning contracts; synthetic fixtures are not real evidence."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.skill_evolution.v22.compact_learning import (
    apply_memory, build_learning_payload, coverage_index, learning_messages,
    prepare_legacy, resolve_source, validate_learning,
)
from tests.skill_evolution.v22.test_verify_round import make_round


class CompactLearningTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = make_round(self.root)()
        self.payload, self.bindings, self.parents = prepare_legacy(self.source)

    def response(self):
        return {"findings": [{"id": "f1", "about": ["intent"] + [row["id"] for row in self.payload["plan"]["watch"]],
                              "observation": "Synthetic Parent and Candidate each execute look; no semantic benefit inferred.",
                              "refs": ["P1:1", "C1:1", "skill:candidate"]}],
                "open": [], "memory_delta": [{"replace": [], "claim": "Synthetic joint update has a look action on one fixture task.",
                                               "limits": ["Synthetic fixture; no causal or generalized effect."], "findings": ["f1"]}]}

    def test_compact_source_roundtrip_and_no_duplicate_trace_text(self):
        self.assertTrue(self.bindings)
        self.assertEqual(self.payload["watch_origin"], "reconstructed_from_frozen_pre_execution_artifacts")
        self.assertEqual(self.parents[0]["run_id"], "run-a")
        self.assertEqual(len(self.payload["command_sets"]), 1)
        self.assertEqual(resolve_source(self.payload, "P1:1")["admissible_commands"], ["look"])
        self.assertEqual(resolve_source(self.payload, "P1:1")["observation_before"], "Your task is to: inspect the room.")
        self.assertNotIn("observation_before", self.payload["runs"]["P1"]["steps"][0])
        self.assertEqual(resolve_source(self.payload, "skill:candidate")["text"], self.payload["candidate"]["text"])
        self.assertEqual(resolve_source(self.payload, "requirement:p1"), self.payload["plan"]["requirements"][0])
        self.assertIn("Preserve:", self.payload["plan"]["requirements"][0]["text"])
        self.assertEqual(self.payload["plan"]["requirements"][0]["basis"], ["P1:1"])

    def test_filtering_parent_sources_does_not_break_aliases(self):
        filtered = deepcopy(self.payload)
        filtered["runs"] = {key: row for key, row in filtered["runs"].items() if key.startswith("P")}
        filtered["sources"] = {key: row for key, row in filtered["sources"].items() if key.startswith("P") or key == "skill:parent"}
        self.assertEqual(resolve_source(filtered, "P1:1")["action"], "look")

    def test_view_excludes_messages_hidden_state_paths_and_reasoning(self):
        parent = deepcopy(self.parents[0])
        parent["hidden_evaluator_state"] = "HIDDEN"
        parent["steps"][0]["model_response"]["reasoning_content"] = "PRIVATE"
        candidate = json.loads(next((self.source / "candidate_runs").glob("*/skill_*/trajectory.json")).read_text())
        payload = build_learning_payload(self.payload["parent"], self.payload["candidate"], "diff",
                                         self.payload["plan"], [parent], [candidate])
        body = json.dumps(payload)
        for forbidden in ("HIDDEN", "PRIVATE", "model_response", "messages", str(self.root)):
            self.assertNotIn(forbidden, body)
        self.assertEqual(len(learning_messages(payload)), 2)

    def test_nonlearning_trace_is_rejected_before_export(self):
        parent = deepcopy(self.parents[0])
        parent["purpose"] = "selection"
        with self.assertRaises(ValueError):
            build_learning_payload(self.payload["parent"], self.payload["candidate"], "", self.payload["plan"], [parent], [])

    def test_missing_question_is_not_silently_preserved(self):
        value = self.response()
        missing = value["findings"][0]["about"].pop()
        self.assertEqual(coverage_index(value, self.payload)[missing]["status"], "not_assessed")
        with self.assertRaisesRegex(ValueError, "Unassessed watch"):
            validate_learning(value, self.payload)
        value["open"].append({"about": [missing], "reason": "The one-step fixture does not expose this boundary; no claim made."})
        self.assertEqual(validate_learning(value, self.payload), value)

    def test_sources_and_memory_dependencies_fail_closed(self):
        for mutate in (lambda v: v["findings"][0]["refs"].append("C1:99"),
                       lambda v: v["memory_delta"][0].update(findings=["missing"]),
                       lambda v: v["memory_delta"][0].update(replace=["unknown-effect"])):
            value = self.response()
            mutate(value)
            with self.assertRaises(ValueError):
                validate_learning(value, self.payload)

    def test_unexecuted_requirements_cannot_be_memory_effects(self):
        value = self.response()
        value["findings"][0]["refs"] = ["requirement:p1"]
        with self.assertRaisesRegex(ValueError, "unexecuted requirements"):
            validate_learning(value, self.payload)

    def test_parent_only_observation_is_not_an_edit_response(self):
        value = self.response()
        value["findings"][0]["refs"] = ["P1:1"]
        with self.assertRaisesRegex(ValueError, "unexecuted requirements"):
            validate_learning(value, self.payload)
        value["findings"][0]["refs"] = ["skill:candidate", "requirement:p1", "capabilities"]
        value["memory_delta"][0]["claim"] = "Synthetic text realization limitation; no behavior regression claimed."
        self.assertEqual(validate_learning(value, self.payload), value)

    def test_memory_revision_retains_counterevidence_and_exact_sources(self):
        first = apply_memory([], self.response(), "first", self.payload)
        self.assertEqual(first[0]["id"], "first:m1")
        self.assertEqual(first[0]["basis"][0]["sources"]["P1:1"]["action"], "look")
        payload = deepcopy(self.payload)
        payload["memory"] = first
        value = self.response()
        value["memory_delta"][0].update(replace=["first:m1"], claim="Narrower revised fixture claim.", limits=["New bounded uncertainty."])
        revised = apply_memory(first, value, "second", payload)
        self.assertEqual(revised[0]["id"], "second:m1")
        self.assertEqual(revised[0]["supersedes"], ["first:m1"])
        self.assertIn("Synthetic fixture; no causal or generalized effect.", revised[0]["limits"])
        self.assertEqual(len(revised[0]["basis"]), 2)
        self.assertEqual(first[0]["claim"], "Synthetic joint update has a look action on one fixture task.")
        self.assertEqual(self.payload["memory"], [])

    def test_new_context_prevents_id_collision_and_repeated_claim_is_versioned(self):
        first = apply_memory([], self.response(), "first", self.payload)
        payload = deepcopy(self.payload)
        payload["memory"] = first
        second = apply_memory(first, self.response(), "second", payload)
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["id"], "second:m1")
        self.assertEqual(second[0]["supersedes"], ["first:m1"])
        with self.assertRaisesRegex(ValueError, "already used"):
            apply_memory(first, self.response(), "first", payload)

    def test_failed_coverage_never_changes_memory(self):
        value = self.response()
        value["findings"][0]["about"] = ["intent"]
        with self.assertRaises(ValueError):
            apply_memory([], value, "failed", self.payload)
        self.assertEqual(self.payload["memory"], [])


if __name__ == "__main__":
    unittest.main()
