"""Offline grouping/source checks; synthetic trajectories are not experiment data."""

from copy import deepcopy
import json
import unittest

from src.adapters.alfworld.skill_runtime import digest, load_skill, object_digest
from src.skill_evolution.v22.compact_learning import resolve_source
from src.skill_evolution.v22.grouped_representation import (
    attach_grouping, build_grouping_input, freeze_grouping, validate_frozen_grouping,
    validate_grouped_plan,
)


PROMPT = "Profile: v22.decision_grouping.v1\nSynthetic fixed classifier instructions.\n"


def current_fixture():
    current = {
        "parent": {key: value for key, value in load_skill().items() if key != "source"},
        "capabilities": "Current observation plus two recent observation/action pairs.",
        "base_protocol": {"system_prompt": "Visible actor policy.", "initial_template": "Visible initial tools.",
                          "history_template": "Visible recent history.", "secret": "HIDDEN_PROTOCOL_METADATA"},
        "command_sets": {"old1": ["look", "open cabinet 1"], "unused": ["HIDDEN_CANDIDATE_ONLY_COMMAND"]},
        "runs": {}, "sources": {"skill:parent": {"kind": "skill", "side": "parent"}},
        "memory": [{"id": "old", "claim": "HIDDEN_HISTORY"}], "plan": {"intent": "HIDDEN_OLD_PLAN"},
        "candidate": {"text": "HIDDEN_CANDIDATE"},
    }
    for number in range(1, 4):
        alias = f"P{number}"
        current["runs"][alias] = {
            "task_id": f"train:{number:04}", "run_id": f"synthetic-{number}", "skill_id": "none",
            "execution_fingerprint": f"fingerprint-{number}", "episode_complete": True,
            "native_success": number == 1, "status": "success" if number == 1 else "step_limit",
            "initial_observation": f"Your task is to: inspect visible area {number}.",
            "initial_commands": "old1", "task_type": "HIDDEN_FAMILY", "gamefile": "HIDDEN_GAMEFILE",
            "selection_reason": "HIDDEN_SELECTION_REASON",
            "steps": [{"step": 1, "phase": "executed", "action": "look", "commands": "old1",
                       "action_in_admissible_commands": True, "observation": "Visible cabinet.",
                       "reward": 1 if number == 1 else 0, "done": number == 1, "won": number == 1,
                       "reasoning": "HIDDEN_REASONING"}],
        }
        current["sources"][f"{alias}:0"] = {"kind": "event", "run": alias, "step": 0}
        current["sources"][f"{alias}:1"] = {"kind": "event", "run": alias, "step": 1}
    return current


def partition(grouping_input):
    refs = [row["task_ref"] for row in grouping_input["model_input"]["experiences"]]
    return {"groups": [
        {"group_id": "G1", "decision_problem": "When is another observation useful?", "members": refs[:2],
         "shared_basis": "The supplied interactions expose the same observable inspection choice.",
         "important_differences": ["Only one observed sequence completes its request."]},
        {"group_id": "G2", "decision_problem": "When should inspection stop?", "members": refs[2:],
         "shared_basis": "This experience exposes a stopping choice.", "important_differences": []},
    ]}


class GroupedRepresentationTests(unittest.TestCase):
    def setUp(self):
        self.current = current_fixture()
        self.input = build_grouping_input(self.current, "r1")
        self.result = partition(self.input)
        self.frozen = freeze_grouping(self.result, self.input, PROMPT)

    def test_export_keeps_parent_facts_and_omits_private_sources(self):
        model = self.input["model_input"]
        body = json.dumps(model)
        self.assertNotIn("HIDDEN", body)
        self.assertNotIn("train:", body)
        self.assertNotIn("synthetic-", body)
        self.assertEqual(len(model["experiences"]), 3)
        self.assertEqual(len(model["command_sets"]), 1)
        self.assertEqual(sum(row["outcome"]["native_success"] for row in model["experiences"]), 1)
        for row in model["experiences"]:
            self.assertTrue(row["task_request"].startswith("inspect visible area"))
            self.assertEqual(row["steps"][0]["observation"], "Visible cabinet.")
            self.assertEqual(model["command_sets"][row["steps"][0]["commands"]], ["look", "open cabinet 1"])

    def test_aliasing_is_reproducible_and_does_not_mutate_input(self):
        before = deepcopy(self.current)
        self.assertEqual(build_grouping_input(self.current, "r1"), self.input)
        self.assertEqual(self.current, before)
        self.assertEqual(set(self.input["bindings"]), {"T1", "T2", "T3"})
        self.assertNotEqual(build_grouping_input(self.current, "r1", seed=201), self.input)

    def test_incomplete_nontrain_duplicate_or_wrong_parent_is_rejected(self):
        mutations = [lambda run: run.update(episode_complete=False),
                     lambda run: run.update(task_id="test:0001"),
                     lambda run: run.update(task_id="train:0002"),
                     lambda run: run.update(skill_id="different"),
                     lambda run: run.update(native_success=None)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                current = deepcopy(self.current)
                mutate(current["runs"]["P1"])
                with self.assertRaises(ValueError):
                    build_grouping_input(current, "r1")

    def test_grouping_is_exact_exclusive_partition_and_allows_singleton(self):
        self.assertEqual(validate_frozen_grouping(self.frozen), self.frozen)
        for kind in ("duplicate", "missing", "unknown", "duplicate_group", "empty"):
            with self.subTest(kind=kind):
                value = deepcopy(self.result)
                if kind == "duplicate":
                    value["groups"][1]["members"].append(value["groups"][0]["members"][0])
                elif kind == "missing":
                    value["groups"][0]["members"].pop()
                elif kind == "unknown":
                    value["groups"][0]["members"][0] = "unseen"
                elif kind == "duplicate_group":
                    value["groups"][1]["group_id"] = "G1"
                else:
                    value["groups"][1]["members"] = []
                with self.assertRaises(ValueError):
                    freeze_grouping(value, self.input, PROMPT)

    def test_freeze_binds_prompt_input_parent_and_rejects_tampering(self):
        self.assertEqual(self.frozen["prompt_sha256"], digest(PROMPT.encode()))
        self.assertEqual(self.frozen["input_sha256"], object_digest(self.input))
        for key in ("groups", "bindings", "parent_sha256", "input_sha256", "prompt_sha256"):
            with self.subTest(key=key):
                value = deepcopy(self.frozen)
                value[key] = None
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    validate_frozen_grouping(value)
        for prompt in ("Profile: old\n", ""):
            with self.assertRaises(ValueError):
                freeze_grouping(self.result, self.input, prompt)

    def test_attach_resolves_sources_and_binds_candidate_by_task(self):
        replay = deepcopy(self.current)
        replay["runs"]["C1"] = deepcopy(replay["runs"]["P1"])
        replay["runs"]["C1"].update(run_id="candidate-run", skill_id="candidate")
        replay["runs"]["C1"]["steps"][0].update(action="open cabinet 1", observation="Candidate-only feedback.")
        replay["command_sets"]["extra"] = ["Candidate-only command"]
        attached = attach_grouping(replay, self.frozen)
        self.assertEqual(attached["runs"]["C1"]["decision_group"], attached["runs"]["P1"]["decision_group"])
        ref = attached["runs"]["P1"]["decision_group"]
        snapshot = resolve_source(attached, ref)
        self.assertEqual(snapshot["grouping_sha256"], self.frozen["sha256"])
        self.assertTrue(any(row["task_id"] == "train:0001" for row in snapshot["members"]))
        self.assertNotIn("decision_group", replay["runs"]["P1"])
        self.assertEqual(attach_grouping(attached, self.frozen), attached)

    def test_attach_rejects_changed_parent_evidence_and_foreign_run(self):
        for mutate in (lambda current: current["runs"]["P1"]["steps"][0].update(observation="changed"),
                       lambda current: current["runs"]["P1"].update(run_id="new-execution"),
                       lambda current: current["base_protocol"].update(system_prompt="changed")):
            value = deepcopy(self.current)
            mutate(value)
            with self.assertRaisesRegex(ValueError, "no longer matches"):
                attach_grouping(value, self.frozen)
        value = deepcopy(self.current)
        value["runs"]["C1"] = deepcopy(value["runs"]["P1"])
        value["runs"]["C1"]["task_id"] = "train:9999"
        with self.assertRaisesRegex(ValueError, "no frozen decision group"):
            attach_grouping(value, self.frozen)

    def test_plan_requires_matching_group_and_real_parent_events(self):
        payload = attach_grouping(self.current, self.frozen)
        group = payload["runs"]["P1"]["decision_group"]
        plan = {"intent": "Improve a visible decision while preserving useful behavior.",
                "requirements": [{"id": "u1", "text": "When the observation is insufficient, inspect before proceeding.",
                                  "basis": [group, "P1:1"]}], "watch": [], "open": []}
        self.assertEqual(validate_grouped_plan(plan, payload), plan)
        other_group = next(ref for ref in payload["sources"] if ref.startswith("group:") and ref != group)
        for basis in ([group], ["P1:1"], [other_group, "P1:1"], [group, other_group, "P1:1"]):
            invalid = deepcopy(plan)
            invalid["requirements"][0]["basis"] = basis
            with self.assertRaisesRegex(ValueError, "matching Parent event"):
                validate_grouped_plan(invalid, payload)
        other_alias = next(alias for alias, run in payload["runs"].items() if run["decision_group"] == other_group)
        plan["requirements"][0]["basis"].extend([other_group, f"{other_alias}:1"])
        self.assertEqual(validate_grouped_plan(plan, payload), plan)

    def test_fixed_parent_survives_export_and_future_parent_cannot_reuse_groups(self):
        text = "Inspect when current visible evidence is insufficient.\n"
        checksum = digest(text.encode())
        fixed = deepcopy(self.current)
        fixed["parent"] = {"mode": "fixed", "text": text, "skill_id": "sha256:" + checksum, "sha256": checksum}
        for run in fixed["runs"].values():
            run["skill_id"] = fixed["parent"]["skill_id"]
        grouped_input = build_grouping_input(fixed, "r2")
        self.assertEqual(grouped_input["model_input"]["parent"]["text"], text)
        with self.assertRaisesRegex(ValueError, "no longer matches"):
            attach_grouping(fixed, self.frozen)


if __name__ == "__main__":
    unittest.main()
