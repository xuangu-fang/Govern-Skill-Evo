"""Scoped-history projection regression tests; no model or environment calls."""

from copy import deepcopy
import json
import unittest

from src.skill_evolution.v22.compact_learning_view import (
    current_run_facts, learning_messages_scoped, scoped_learning_payload,
)


def fixture():
    event = {"run_id": "old-clean", "task_id": "train:0012", "skill_id": "old-skill", "step": 8,
             "episode_complete": True, "phase": "executed", "action": "look",
             "action_in_admissible_commands": True, "observation_before": "Old room.",
             "observation": "Old final observation.", "reward": 0, "done": False, "won": False,
             "admissible_commands": ["long legal command " + str(i) for i in range(200)],
             "execution_fingerprint": "old-fingerprint"}
    basis = {"context_id": "old-context", "finding": {"id": "f1", "about": ["w1", "p1"],
             "observation": "C2 took eight steps; C2:8 was look and P1:4 was invalid.", "refs": ["C2:8"]},
             "sources": {"C2:8": event, "requirement:p1": {"id": "p1", "text": "Keep valid actions.", "basis": ["P1:4"]},
                         "skill:candidate": {"skill_id": "old-skill", "text": "Retained exact static Skill."}},
             "actual_update": {"parent_skill_id": "none", "candidate_skill_id": "old-skill",
                               "comparisons": [{"parent": "P1", "candidate": "C2", "recorded_conditions_match": True}]}}
    return {"schema_version": "fixture", "runs": {"C2": {"run_id": "new-clean", "task_id": "train:0012",
              "skill_id": "new-skill", "status": "error", "episode_complete": False, "native_success": None,
              "steps": [{"step": 1, "phase": "executed", "action": "go to sink", "action_in_admissible_commands": True,
                         "observation": "At sink."},
                        {"step": 2, "phase": "executed", "action": "look", "action_in_admissible_commands": False,
                         "observation": "Nothing happens."},
                        {"step": 3, "phase": "responded", "action": "look", "action_in_admissible_commands": False},
                        {"step": 4, "phase": "requesting"}]}},
            "sources": {"C2:1": {"kind": "event", "run": "C2", "step": 1}}, "pairs": [],
            "memory": [{"id": "old-context:m1", "claim": "C2:8 showed look.",
                        "limits": ["P1:4 is a counterexample; not universal.", "Second limitation kept verbatim."],
                        "supersedes": ["earlier:m1"], "attribution": "joint only", "basis": [basis]}]}


class CompactLearningViewTests(unittest.TestCase):
    def test_aliases_are_scoped_in_fields_prose_and_static_requirements(self):
        payload = fixture()
        view = scoped_learning_payload(payload)
        effect = view["memory"][0]
        self.assertEqual(view["historical_contexts"], {"H1": "old-context"})
        self.assertEqual(effect["historical_contexts"], ["H1"])
        self.assertEqual(effect["id"], "old-context:m1")
        self.assertEqual(effect["supersedes"], ["earlier:m1"])
        self.assertEqual(effect["claim"], "H1::C2:8 showed look.")
        basis = effect["basis"][0]
        self.assertEqual(basis["finding"]["refs"], ["H1::C2:8"])
        self.assertEqual(basis["finding"]["about"], ["H1::w1", "H1::p1"])
        self.assertIn("H1::C2 took eight steps", basis["finding"]["observation"])
        self.assertEqual(basis["actual_update"]["comparisons"][0]["parent"], "H1::P1")
        self.assertEqual(view["historical_sources"]["H1::requirement:p1"]["basis"],
                         ["H1::P1:4"])
        self.assertEqual(view["sources"], payload["sources"])
        self.assertEqual(view["runs"], payload["runs"])

    def test_identical_aliases_in_different_contexts_remain_distinct(self):
        payload = fixture()
        another = deepcopy(payload["memory"][0]["basis"][0])
        another["context_id"] = "other-context"
        another["sources"]["C2:8"]["action"] = "take item"
        payload["memory"][0]["basis"].append(another)
        view = scoped_learning_payload(payload)
        self.assertEqual(view["historical_sources"]["H1::C2:8"]["action"], "look")
        self.assertEqual(view["historical_sources"]["H2::C2:8"]["action"], "take item")
        self.assertIn("history[H1,H2]::C2:8", view["memory"][0]["claim"])

    def test_limits_static_sources_and_event_content_are_retained(self):
        view = scoped_learning_payload(fixture())
        self.assertEqual(len(view["memory"][0]["limits"]), 2)
        self.assertIn("counterexample; not universal", view["memory"][0]["limits"][0])
        self.assertEqual(view["memory"][0]["limits"][1], "Second limitation kept verbatim.")
        static = view["historical_sources"]["H1::skill:candidate"]
        self.assertEqual(static, {"skill_id": "old-skill", "text": "Retained exact static Skill."})
        event = view["historical_sources"]["H1::C2:8"]
        self.assertEqual(event["observation_before"], "Old room.")
        self.assertEqual(event["observation"], "Old final observation.")
        self.assertEqual(event["run_id"], "old-clean")
        self.assertNotIn("admissible_commands", event)
        self.assertNotIn("execution_fingerprint", event)

    def test_facts_count_only_executed_events_and_keep_incomplete_status(self):
        facts = current_run_facts(fixture())["C2"]
        self.assertEqual(facts["executed_actions"], 2)
        self.assertEqual(facts["non_admissible_steps"], [2])
        self.assertEqual(facts["look_steps"], [2])
        self.assertEqual(facts["nothing_happens_steps"], [2])
        self.assertFalse(facts["episode_complete"])
        self.assertIsNone(facts["native_success"])

    def test_namespacing_does_not_rewrite_literal_action_observation_or_skill(self):
        payload = fixture()
        sources = payload["memory"][0]["basis"][0]["sources"]
        sources["C2:8"]["action"] = "inspect C2 label"
        sources["C2:8"]["observation"] = "A literal label P1 is visible."
        sources["skill:candidate"]["text"] = "Literal task label C2 must not be renamed."
        view = scoped_learning_payload(payload)["historical_sources"]
        self.assertEqual(view["H1::C2:8"]["action"], "inspect C2 label")
        self.assertEqual(view["H1::C2:8"]["observation"], "A literal label P1 is visible.")
        self.assertEqual(view["H1::skill:candidate"]["text"],
                         "Literal task label C2 must not be renamed.")

    def test_projection_does_not_mutate_payload_and_is_smaller(self):
        payload = fixture()
        original = deepcopy(payload)
        view = scoped_learning_payload(payload)
        self.assertEqual(payload, original)
        self.assertLess(len(json.dumps(view)), len(json.dumps(payload)))
        messages = learning_messages_scoped(payload)
        self.assertIn("replace that effect", messages[0]["content"])
        self.assertIn("ONLY keys in the current sources", messages[0]["content"])
        self.assertEqual(json.loads(messages[1]["content"]), view)

    def test_duplicate_historical_sources_are_stored_once(self):
        payload = fixture()
        payload["memory"][0]["basis"].append(deepcopy(payload["memory"][0]["basis"][0]))
        view = scoped_learning_payload(payload)
        self.assertEqual(len(view["historical_sources"]), 3)
        self.assertEqual(len(view["memory"][0]["basis"]), 2)

    def test_conflicting_same_context_snapshot_is_not_silently_overwritten(self):
        payload = fixture()
        duplicate = deepcopy(payload["memory"][0]["basis"][0])
        duplicate["sources"]["C2:8"]["action"] = "contradictory"
        payload["memory"][0]["basis"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "Conflicting historical"):
            scoped_learning_payload(payload)


if __name__ == "__main__":
    unittest.main()
