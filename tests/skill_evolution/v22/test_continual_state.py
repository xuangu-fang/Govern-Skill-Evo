"""Offline synthetic tests; outcomes here are fixtures, never experiment results."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import (
    build_skill_messages, context_fingerprint, execution_fingerprint, load_skill,
    make_record, object_digest, write_record,
)
from src.skill_evolution.v22.continual_state import (
    RECEIPT_SCHEMA, finish_round, gate_round, initial_state, open_round, read_state,
    validate_gate, validate_round, validate_state, write_state,
)


class ContinualStateTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.game = self.root / "game.tw-pddl"
        self.game.write_text("synthetic fixture")
        self.items = [{"id": f"train:{index:04}", "gamefile": "synthetic"} for index in range(8)]
        self.manifest = self.root / "items.json"
        write_record(self.manifest, self.items)
        self.skill_file = self.root / "skill.md"
        self.skill_file.write_text("Inspect the relevant available receptacle before searching elsewhere.\n")
        self.skill = load_skill(self.skill_file)
        self.state = initial_state("offline-stream")
        self.context = open_round(self.state, [item["id"] for item in self.items[:3]])
        self.serial = 0

    def record(self, task_id, skill, won=False):
        item = next(row for row in self.items if row["id"] == task_id)
        record = make_record(item=item, split="train", purpose="learning", skill=deepcopy(skill),
                             model="offline-model", max_steps=1, gamefile=self.game,
                             manifest_path=self.manifest, versions={"alfworld": "fixture"}, backend_id="fixture")
        self.serial += 1
        observation = "Your task is to: inspect the room."
        admissible = ["look"]
        record.update(run_id=f"fixture-{self.serial}", initial_observation=observation,
                      initial_admissible_commands=admissible, won=won,
                      status="success" if won else "environment_ended", finished_at="fixture")
        record["steps"] = [{"step": 1, "phase": "executed", "messages": build_skill_messages(
            observation, admissible, "inspect the room.", [], skill), "admissible_commands": admissible,
            "model_response": {"content": "<action>look</action>", "response_model": "offline-model"},
            "action": "look", "fallback": None, "action_in_admissible_commands": True,
            "observation": "Synthetic observation", "reward": int(won), "won": won, "done": True}]
        return record

    def records(self, context, candidate, parent_wins, candidate_wins):
        return ([self.record(task, context["parent"], won) for task, won in zip(context["task_ids"], parent_wins)],
                [self.record(task, candidate, won) for task, won in zip(context["task_ids"], candidate_wins)])

    def receipt(self, context, gate, memory_after):
        return {"schema_version": RECEIPT_SCHEMA, "round_id": context["round_id"],
                "gate_sha256": object_digest(gate), "memory_before_sha256": object_digest(context["memory"]),
                "memory_after_sha256": object_digest(memory_after),
                "learning_payload_sha256": object_digest({"synthetic": "input"}),
                "learning_output_sha256": object_digest({"synthetic": "validated output"})}

    def completed(self, parent_wins, candidate_wins, memory=None):
        parents, candidates = self.records(self.context, self.skill, parent_wins, candidate_wins)
        gate = gate_round(self.context, self.skill, parents, candidates)
        memory = memory if memory is not None else [{"id": "r1:m1", "claim": "Synthetic evidence only"}]
        receipt = self.receipt(self.context, gate, memory)
        return finish_round(self.state, self.context, self.skill, gate, memory, receipt), gate

    def test_overall_improvement_accepts_even_with_one_regression(self):
        state, gate = self.completed([True, False, False], [False, True, True])
        self.assertEqual(gate["decision"], "ACCEPT")
        self.assertEqual(gate["successes"], {"parent": 1, "candidate": 2})
        self.assertTrue(gate["pairs"][0]["parent"]["won"])
        self.assertFalse(gate["pairs"][0]["candidate"]["won"])
        self.assertEqual(state["parent"], self.skill)
        self.assertEqual(validate_state(state), state)

    def test_equal_or_lower_success_retains_parent_and_learns_memory(self):
        for wins in ([False, True, False], [False, False, False]):
            with self.subTest(wins=wins):
                state, gate = self.completed([True, False, False], wins)
                self.assertEqual(gate["decision"], "RETAIN")
                self.assertEqual(state["parent"], load_skill())
                self.assertEqual(state["memory"][0]["id"], "r1:m1")

    def test_second_round_inherits_snapshot_and_memory_without_repeated_train(self):
        state, _ = self.completed([True, False, False], [False, True, True])
        self.skill_file.write_text("Changed external path must not change inherited bytes.")
        second = open_round(state, [row["id"] for row in self.items[3:6]])
        self.assertEqual(second["parent"], self.skill)
        self.assertEqual(second["memory"], state["memory"])
        self.assertEqual(second["round_index"], 2)
        second["memory"][0]["claim"] = "Caller mutation"
        self.assertNotEqual(second["memory"], state["memory"])
        with self.assertRaisesRegex(ValueError, "repeated Train"):
            open_round(state, ["train:0002", "train:0003"])

    def test_no_change_retains_and_still_requires_post_gate_learning(self):
        parents = [self.record(task, self.context["parent"]) for task in self.context["task_ids"]]
        gate = gate_round(self.context, None, parents, [])
        self.assertEqual(gate["reason"], "no_change")
        with self.assertRaisesRegex(ValueError, "receipt"):
            finish_round(self.state, self.context, None, gate, [], None)
        state = finish_round(self.state, self.context, None, gate, [], self.receipt(self.context, gate, []))
        self.assertEqual(state["parent"], load_skill())
        self.assertEqual(state["round_index"], 1)

    def test_two_completed_rounds_retain_nonempty_parent_and_new_memory(self):
        first, _ = self.completed([False] * 3, [True] * 3)
        second = open_round(first, [row["id"] for row in self.items[3:6]])
        path = self.root / "second-candidate.md"
        path.write_text(self.skill["text"] + "Only broaden search when local information is insufficient.\n")
        candidate = load_skill(path)
        parents, candidates = self.records(second, candidate, [True, False, False], [False, True, False])
        gate = gate_round(second, candidate, parents, candidates)
        memory = first["memory"] + [{"id": "r2:m1", "claim": "Synthetic second-round limitation"}]
        result = finish_round(first, second, candidate, gate, memory, self.receipt(second, gate, memory))
        self.assertEqual(result["round_index"], 2)
        self.assertEqual(gate["decision"], "RETAIN")
        self.assertEqual(result["parent"], first["parent"])
        self.assertNotEqual(result["parent"], load_skill())
        self.assertEqual(result["memory"], memory)
        self.assertEqual(result["seen_task_ids"], [row["id"] for row in self.items[:6]])
        self.assertEqual(validate_state(result), result)

    def test_failed_learning_or_unbound_receipt_cannot_publish(self):
        parents, candidates = self.records(self.context, self.skill, [False] * 3, [True] * 3)
        gate = gate_round(self.context, self.skill, parents, candidates)
        memory = [{"id": "r1:m1", "claim": "Fixture"}]
        receipt = self.receipt(self.context, gate, memory)
        for changed in (None, {**receipt, "memory_after_sha256": object_digest([])},
                        {**receipt, "gate_sha256": object_digest({})},
                        {**receipt, "learning_output_sha256": None}):
            with self.subTest(receipt=changed), self.assertRaises(ValueError):
                finish_round(self.state, self.context, self.skill, gate, memory, changed)
        self.assertEqual(self.state, initial_state("offline-stream"))

    def test_missing_duplicate_incomplete_or_wrong_skill_records_rejected(self):
        parents, candidates = self.records(self.context, self.skill, [False] * 3, [True] * 3)
        variants = [candidates[:2], [candidates[0], candidates[0], candidates[2]]]
        partial = deepcopy(candidates)
        partial[0].update(status="error", won=False)
        partial[0]["steps"] = []
        variants.append(partial)
        wrong_skill = deepcopy(candidates)
        wrong_skill[0] = self.record("train:0000", load_skill())
        variants.append(wrong_skill)
        for rows in variants:
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                gate_round(self.context, self.skill, parents, rows)

    def test_incomparable_execution_conditions_rejected(self):
        parents, candidates = self.records(self.context, self.skill, [False] * 3, [True] * 3)
        candidates[0]["versions"]["alfworld"] = "different"
        candidates[0]["context_fingerprint"] = context_fingerprint(candidates[0])
        candidates[0]["execution_fingerprint"] = execution_fingerprint(candidates[0])
        with self.assertRaisesRegex(ValueError, "Incomparable"):
            gate_round(self.context, self.skill, parents, candidates)

    def test_unchanged_candidate_is_not_replayed_as_new_version(self):
        parents = [self.record(task, load_skill()) for task in self.context["task_ids"]]
        with self.assertRaisesRegex(ValueError, "unchanged Candidate"):
            gate_round(self.context, load_skill(), parents, parents)
        with self.assertRaisesRegex(ValueError, "No-change"):
            gate_round(self.context, None, parents, parents)

    def test_checksums_detect_state_context_and_gate_drift(self):
        state, gate = self.completed([False] * 3, [True] * 3)
        state["parent"]["text"] += " drift"
        with self.assertRaisesRegex(ValueError, "checksum"):
            validate_state(state)
        context = deepcopy(self.context)
        context["task_ids"].reverse()
        with self.assertRaisesRegex(ValueError, "checksum"):
            validate_round(context)
        gate["decision"] = "RETAIN"
        with self.assertRaisesRegex(ValueError, "checksum"):
            validate_gate(gate, self.context, self.skill)

    def test_all_operations_preserve_inputs_and_publish_exclusively(self):
        before = deepcopy((self.state, self.context, self.skill))
        parents, candidates = self.records(self.context, self.skill, [False] * 3, [True] * 3)
        records_before = deepcopy((parents, candidates))
        gate = gate_round(self.context, self.skill, parents, candidates)
        memory = [{"id": "r1:m1", "claim": "Synthetic only"}]
        receipt = self.receipt(self.context, gate, memory)
        inputs = deepcopy((gate, memory, receipt))
        state = finish_round(self.state, self.context, self.skill, gate, memory, receipt)
        self.assertEqual((self.state, self.context, self.skill), before)
        self.assertEqual((parents, candidates), records_before)
        self.assertEqual((gate, memory, receipt), inputs)
        path = self.root / "round-1.state.json"
        write_state(path, state)
        self.assertEqual(read_state(path), state)
        with self.assertRaises(FileExistsError):
            write_state(path, self.state)
        self.assertEqual(read_state(path), state)
        self.assertFalse(list(self.root.glob(".continual-state-*")))

    def test_stale_round_cannot_finish_against_a_new_state(self):
        state, gate = self.completed([False] * 3, [True] * 3)
        with self.assertRaises(ValueError):
            finish_round(state, self.context, self.skill, gate, state["memory"],
                         self.receipt(self.context, gate, state["memory"]))


if __name__ == "__main__":
    unittest.main()
