"""Synthetic cross-round identity checks; no model or environment is called.

The authored observations test provenance, not the truth of behavioral learning.
"""

from copy import deepcopy
import json
import unittest

from src.skill_evolution.v22.effective_memory import (
    apply_effective_memory, effective_consumption_payload,
)
from src.skill_evolution.v22.memory_identity import (
    PROFILE, capture_reference_contexts, reference_contexts_by_origin,
    rebind_history_references,
)
from src.skill_evolution.v22.unified_dsc import PROFILE as V1


def payload(origin, memory, profile=PROFILE):
    """Small complete source directory with distinct run identities per origin."""
    parent = {"skill_id": origin + "-parent", "text": "Use the visible prerequisite."}
    candidate = {"skill_id": origin + "-candidate", "text": "Refresh stale prerequisites."}
    runs = {}
    for alias, skill in (("P1", parent), ("C1", candidate)):
        runs[alias] = {
            "run_id": origin + "-" + alias, "task_id": "synthetic-task",
            "skill_id": skill["skill_id"], "execution_fingerprint": origin,
            "status": "completed", "episode_complete": True, "native_success": True,
            "initial_observation": "Prerequisite is stale.",
            "steps": [{"step": 1, "phase": "executed", "action": "refresh",
                       "observation": "Prerequisite is current.", "commands": "a1",
                       "action_in_admissible_commands": True}],
        }
    return {
        "update_profile": profile, "parent": parent, "candidate": candidate,
        "actual_diff": "+ Refresh stale prerequisites.",
        "plan": {"intent": "Preserve valid prerequisites.", "requirements": [], "watch": []},
        "runs": runs, "command_sets": {"a1": ["refresh", "continue"]},
        "pairs": [{"parent": "P1", "candidate": "C1", "recorded_conditions_match": True}],
        "sources": {"P1:1": {"kind": "event", "run": "P1", "step": 1},
                    "C1:1": {"kind": "event", "run": "C1", "step": 1},
                    "skill:candidate": {"kind": "skill", "side": "candidate"},
                    "intent": {"kind": "intent"}, "diff": {"kind": "diff"}},
        "memory": deepcopy(memory),
        "update_context": {"actual_diff": "+ Refresh stale prerequisites."},
    }


def response(claim="C1:1 shows an authored joint response.", limits=None):
    return {
        "findings": [{"id": "f1", "about": ["intent"],
                      "observation": "An authored response under the visible prerequisite.",
                      "refs": ["P1:1", "C1:1", "skill:candidate", "diff"]}],
        "open": [],
        "memory_delta": [{"replace": [], "claim": claim,
                          "limits": limits or ["C1:1 does not establish untested conditions."],
                          "findings": ["f1"], "retire_limits": []}],
    }


def learn(origin, memory, value=None, profile=PROFILE):
    source = payload(origin, memory, profile)
    return apply_effective_memory(source["memory"], value or response(), origin, source)


def consume(memory, profile=PROFILE):
    return effective_consumption_payload({"memory": memory, "update_profile": profile})


class MemoryIdentityTests(unittest.TestCase):
    def test_reordering_rebinds_history_and_current_aliases_without_changing_v1(self):
        for profile in (V1, PROFILE):
            with self.subTest(profile=profile):
                memory = learn("alpha", [], profile=profile)
                memory = learn("beta", memory, response("H1::C1:1 compared with C1:1."), profile)
                before = consume(memory, profile)
                after = consume(list(reversed(memory)), profile)
                self.assertEqual(before["historical_contexts"], {"H1": "alpha", "H2": "beta"})
                self.assertEqual(after["historical_contexts"], {"H1": "beta", "H2": "alpha"})
                claim = after["memory"][0]["claim"]
                if profile == PROFILE:
                    self.assertEqual(claim, "H2::C1:1 compared with H1::C1:1.")
                    self.assertEqual(after["historical_sources"]["H2::C1:1"]["run_id"], "alpha-C1")
                    self.assertEqual(after["historical_sources"]["H1::C1:1"]["run_id"], "beta-C1")
                else:
                    # Preserve v1 reconstruction, including its known unstable prose.
                    self.assertEqual(claim, "H1::C1:1 compared with H1::C1:1.")
                    self.assertNotIn("reference_contexts", memory[-1]["basis"][0]["actual_update"])

    def test_each_inherited_limit_keeps_its_authoring_origin_after_partial_retirement(self):
        memory = learn("alpha", [], response(limits=["C1:1 has an untested boundary.", "Obsolete limit."]))
        value = response("H1::C1:1 compared with C1:1.",
                         ["H1::C1:1 contrasts with C1:1.", "A beta restriction to retire."])
        value["memory_delta"][0].update(replace=["alpha:m1"], retire_limits=[{
            "effect_id": "alpha:m1", "index": 1, "reason": "Current evidence revises this scope.",
            "findings": ["f1"],
        }])
        memory = learn("beta", memory, value)
        value = response("H2::C1:1 compared with C1:1.", ["H2::C1:1 and H1::C1:1 remain conditional."])
        value["memory_delta"][0].update(replace=["beta:m1"], retire_limits=[{
            "effect_id": "beta:m1", "index": 2, "reason": "H1::C1:1 supports revising only this restriction.",
            "findings": ["f1"],
        }])
        value["memory_delta"].append(response()["memory_delta"][0])
        memory = learn("gamma", memory, value)
        view = consume(list(reversed(memory)))
        self.assertEqual(view["historical_contexts"], {"H1": "gamma", "H2": "alpha", "H3": "beta"})
        revised = next(row for row in view["memory"] if row["id"] == "gamma:m1")
        self.assertEqual(revised["limit_contexts"], ["alpha", "beta", "gamma"])
        self.assertEqual(revised["limits"], [
            "H2::C1:1 has an untested boundary.",
            "H2::C1:1 contrasts with H3::C1:1.",
            "H3::C1:1 and H2::C1:1 remain conditional.",
        ])
        self.assertEqual(revised["claim"], "H3::C1:1 compared with H1::C1:1.")
        self.assertNotIn("A beta restriction to retire.", json.dumps(view))
        self.assertEqual(memory[0]["retired_limits"][-1]["retirement_context_id"], "gamma")

    def test_same_call_map_covers_finding_and_retirement_reason_without_rewriting_output(self):
        memory = learn("alpha", [])
        memory = learn("beta", memory)
        value = response()
        value["findings"][0]["observation"] = "H2::C1:1 is a historical comparison."
        value["memory_delta"][0].update(replace=["alpha:m1"], retire_limits=[{
            "effect_id": "alpha:m1", "index": 0,
            "reason": "H1::C1:1 supplies the earlier scope; current findings revise it.",
            "findings": ["f1"],
        }])
        value["memory_delta"].append(response()["memory_delta"][0])
        before = deepcopy(value)
        learned = learn("gamma", memory, value)
        maps = [basis["actual_update"]["reference_contexts"]
                for effect in learned for basis in effect["basis"] if basis["context_id"] == "gamma"]
        self.assertEqual(maps, [{"H1": "alpha", "H2": "beta"}] * 2)
        revised = next(row for row in learned if row["id"] == "gamma:m1")
        self.assertEqual(revised["basis"][-1]["finding"], value["findings"][0])
        self.assertEqual(revised["retired_limits"][-1]["reason"], value["memory_delta"][0]["retire_limits"][0]["reason"])
        self.assertEqual(value, before)

    def test_missing_or_unknown_reference_map_stays_unknown_without_blocking_learning(self):
        legacy = learn("alpha", [], profile=V1)
        legacy = learn("beta", legacy, response("H1::C1:1 was previously compared."), V1)
        view = consume(list(reversed(legacy)))
        self.assertEqual(view["memory"][0]["claim"], "history_unknown::C1:1 was previously compared.")
        learned = learn("gamma", legacy, response("H99::C1:1 is not a resolvable historical source."))
        self.assertEqual(learned[-1]["basis"][0]["actual_update"]["reference_contexts"], {})
        self.assertEqual(consume(learned)["memory"][-1]["claim"],
                         "history_unknown::C1:1 is not a resolvable historical source.")
        # A map whose target is absent must not accidentally point to today's H1.
        self.assertEqual(rebind_history_references("H1::C1:1", "writer", {"writer": {"H1": "absent"}},
                                                  {"different": "H1"}), "history_unknown::C1:1")

    def test_conflicting_maps_for_one_origin_are_rejected(self):
        memory = learn("alpha", [])
        memory = learn("beta", memory, response("H1::C1:1 was compared."))
        duplicate = deepcopy(memory[-1])
        duplicate["id"] = "beta:duplicate"
        duplicate["basis"][0]["actual_update"]["reference_contexts"] = {"H1": "other"}
        memory.append(duplicate)
        with self.assertRaisesRegex(ValueError, "Conflicting historical reference context maps"):
            reference_contexts_by_origin(memory)
        with self.assertRaisesRegex(ValueError, "Conflicting historical reference context maps"):
            consume(memory)

    def test_projection_preserves_literal_evidence_and_hides_bookkeeping(self):
        literal = "Literal H1::C1:1 label, not a model-authored reference."
        source = payload("alpha", [])
        source["candidate"]["text"] = literal
        source["runs"]["C1"]["steps"][0]["action"] = literal
        source["runs"]["C1"]["steps"][0]["observation"] = literal
        source["actual_diff"] = literal
        source["update_context"]["actual_diff"] = literal
        original = deepcopy(source)
        memory = apply_effective_memory([], response(), "alpha", source)
        memory = learn("beta", memory, response("H1::C1:1 compared with C1:1."))
        ordered = list(reversed(memory))
        before = deepcopy(ordered)
        view = consume(ordered)
        self.assertEqual(view["historical_sources"]["H2::C1:1"]["action"], literal)
        self.assertEqual(view["historical_sources"]["H2::C1:1"]["observation"], literal)
        self.assertEqual(view["historical_sources"]["H2::skill:candidate"]["text"], literal)
        self.assertEqual(view["historical_updates"]["H2"]["update_context"]["actual_diff"], literal)
        self.assertNotIn("reference_contexts", json.dumps(view))
        self.assertEqual(ordered, before)
        self.assertEqual(source, original)

    def test_capture_retains_only_used_names_and_rebinding_does_not_cascade(self):
        value = response("H1::C1:1 and H2::C1:1 are historical; H99::C1:1 is unavailable.")
        self.assertEqual(capture_reference_contexts(value, {"H1": "alpha", "H2": "beta", "H3": "unused"}),
                         {"H1": "alpha", "H2": "beta"})
        self.assertEqual(rebind_history_references("H1::C1:1 + H2::C1:1", "writer",
                         {"writer": {"H1": "alpha", "H2": "beta"}}, {"alpha": "H2", "beta": "H1"}),
                         "H2::C1:1 + H1::C1:1")


if __name__ == "__main__":
    unittest.main()
