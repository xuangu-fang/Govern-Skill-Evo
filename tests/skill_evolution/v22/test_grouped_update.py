"""Synthetic two-round interface exercise; no model or environment is called."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import build_skill_messages, load_skill, make_record, write_record
from src.skill_evolution.v22.continual_state import (
    finish_round, gate_round, initial_state, open_round, read_state, write_state,
)
from src.skill_evolution.v22.evidence import prepare_evidence
from src.skill_evolution.v22.grouped_representation import build_grouping_input, freeze_grouping
from src.skill_evolution.v22.grouped_update import (
    accept_diagnosis, compile_update, diagnosis_payload, realize_editor, grouped_messages,
    identity_update, learn_grouped_memory, materialize_skill, prepare_current,
    prepare_grouped_learning, update_payload,
)


class GroupedUpdateTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.game = self.root / "game.tw-pddl"
        self.game.write_text("Synthetic fixture only")
        self.items = [{"id": f"train:{i:04}", "gamefile": "synthetic"} for i in range(6)]
        self.manifest = self.root / "items.json"
        write_record(self.manifest, self.items)
        self.serial = 0
        self.prompt = Path("experiments/methods/v22/08_grouped_continual/config/grouping_prompt.md").read_text()
        self.state = initial_state("synthetic")
        self.context = open_round(self.state, [row["id"] for row in self.items[:3]])

    def record(self, task_id, skill, won):
        item = next(row for row in self.items if row["id"] == task_id)
        record = make_record(item=item, split="train", purpose="learning", skill=deepcopy(skill),
                             model="offline", max_steps=1, gamefile=self.game, manifest_path=self.manifest,
                             versions={"alfworld": "synthetic"}, backend_id="fixture")
        self.serial += 1
        observation, commands = "Your task is to: inspect the room.", ["look"]
        record.update(run_id=f"fixture-{self.serial}", initial_observation=observation,
                      initial_admissible_commands=commands, won=won,
                      status="success" if won else "environment_ended", finished_at="fixture")
        record["steps"] = [{"step": 1, "phase": "executed", "messages": build_skill_messages(
            observation, commands, "inspect the room.", [], skill), "admissible_commands": commands,
            "model_response": {"content": "<action>look</action>", "response_model": "offline"},
            "action": "look", "fallback": None, "action_in_admissible_commands": True,
            "observation": "Synthetic visible outcome", "reward": int(won), "done": True, "won": won}]
        return record

    def batch(self, context, skill, wins):
        return [self.record(task, skill, won) for task, won in zip(context["task_ids"], wins)]

    def inputs(self, context, parents):
        current = prepare_current(context, parents)
        source = build_grouping_input(current, context["round_id"])
        grouping = freeze_grouping({"groups": [{"group_id": "G1", "decision_problem": "When to inspect",
            "members": [row["task_ref"] for row in source["model_input"]["experiences"]],
            "shared_basis": "Synthetic comparable visible decision", "important_differences": []}]}, source, self.prompt)
        current = diagnosis_payload(context, parents, grouping)
        group_ref = f"group:{context['round_id']}:G1"
        plan = {"intent": "Improve the relevant visible decision and preserve other behavior.",
                "requirements": [{"id": "u1", "text": "Inspect when relevant; preserve other obligations.",
                                  "basis": [group_ref, "P1:1"]}],
                "watch": [{"id": "w1", "about": ["u1"], "question": "What improves or regresses?"}], "open": []}
        value = {"decision": "revise", "reason": "Synthetic initial requirement.", "plan": plan}
        accept_diagnosis(value, current)
        return grouping, current, update_payload(context, current, plan)

    def candidate(self, payload, text):
        return realize_editor({"decision": "candidate", "reason": "Synthetic realization.",
            "candidate_text": text, "issues": [], "watch": [],
            "mappings": [{"requirements": [row["id"] for row in payload["plan"]["requirements"]],
                          "side": "candidate", "excerpt": text}]}, payload)[0]

    def learning(self, payload, claim="Synthetic bundle response, not an isolated effect."):
        ref = next(key for key in payload["sources"] if key.startswith("group:"))
        return {"findings": [{"id": "f1", "about": [row["id"] for row in payload["plan"]["watch"]],
                              "observation": claim, "refs": ["P1:1", "C1:1", ref]}],
                "open": [], "memory_delta": [{"replace": [], "claim": claim,
                    "limits": ["Synthetic fixture; no real behavior benefit or isolated attribution."],
                    "findings": ["f1"], "retire_limits": []}]}

    def first_round(self):
        parents = self.batch(self.context, self.context["parent"], [True, False, False])
        grouping, current, update = self.inputs(self.context, parents)
        identity, plan = identity_update(update)
        self.assertEqual(identity["changes"], [])
        candidate = self.candidate(update, "Inspect only when the visible decision calls for it.\n")
        candidates = self.batch(self.context, candidate, [False, True, True])
        gate = gate_round(self.context, candidate, parents, candidates)
        payload = prepare_grouped_learning(self.context, grouping, plan, candidate, parents, candidates, gate)
        memory, receipt = learn_grouped_memory(payload, self.learning(payload,
            "Synthetic bundle has one regression and two repairs; individual contributions unknown."))
        state = finish_round(self.state, self.context, candidate, gate, memory, receipt)
        return state, payload, parents

    def test_two_round_mainline_inherits_real_parent_and_consumes_effect(self):
        first, feedback, _ = self.first_round()
        self.assertEqual(first["last_round"]["gate"]["decision"], "ACCEPT")
        self.assertEqual(first["memory"][0]["basis"][0]["actual_update"]["update_context"], feedback["update_context"])
        state_file = self.root / "round1.json"
        write_state(state_file, first)
        second = open_round(read_state(state_file), [row["id"] for row in self.items[3:]])
        actor_file = materialize_skill(second["parent"], self.root / "round2-parent.md")
        self.assertEqual(load_skill(actor_file)["text"], first["parent"]["text"])
        parents = self.batch(second, load_skill(actor_file), [True, False, False])
        grouping, current, update = self.inputs(second, parents)
        self.assertNotIn("memory", current)
        self.assertEqual(update["memory"], first["memory"])
        messages = grouped_messages("fusion", update)
        self.assertIn("H1::", messages[1]["content"])
        self.assertIn("native_success_improvement.v1", messages[1]["content"])
        effect_id = first["memory"][0]["id"]
        transform = {"decision": "ready", "reason": "Use the synthetic limited response.",
            "changes": [{"from": ["u1"], "to": [{"id": "u2", "text": "Narrow inspection to its visible condition."}],
                         "basis": [effect_id], "reason": "The observed regression limits the prior scope.", "disposition": "replace"}],
            "watch_changes": [{"from": ["w1"], "to": [{"id": "w2", "about": ["u2"], "question": "Does the narrowed scope help?"}]}], "open": []}
        plan = compile_update(transform, update)
        edited = update_payload(second, current, plan)
        self.assertEqual(edited["parent"]["text"], first["parent"]["text"])
        candidate = self.candidate(edited, first["parent"]["text"] + "Continue only under the visible trigger.\n")
        candidates = self.batch(second, candidate, [False, True, False])
        gate = gate_round(second, candidate, parents, candidates)
        payload = prepare_grouped_learning(second, grouping, plan, candidate, parents, candidates, gate)
        self.assertIn("--- parent/SKILL.md", payload["actual_diff"])
        self.assertNotIn("parent/NoSkill", payload["actual_diff"])
        memory, receipt = learn_grouped_memory(payload, self.learning(payload, "Synthetic equal success; local change remains recorded."))
        final = finish_round(first, second, candidate, gate, memory, receipt)
        self.assertEqual(final["parent"], first["parent"])
        self.assertEqual(gate["decision"], "RETAIN")
        self.assertEqual(len(final["memory"]), 2)
        self.assertEqual(len(final["seen_task_ids"]), 6)
        self.assertEqual(self.state, initial_state("synthetic"))

    def test_actual_parent_evidence_entry_and_immutable_materialization(self):
        state, _, _ = self.first_round()
        context = open_round(state, ["train:0003"])
        path = materialize_skill(context["parent"], self.root / "parent.md")
        record = self.record("train:0003", load_skill(path), False)
        trace = self.root / "trace.json"
        write_record(trace, record)
        plan = {"model": "offline", "max_steps_per_episode": 1, "task_ids": context["task_ids"]}
        records, _, _ = prepare_evidence([trace], plan, parent_skill=context["parent"])
        self.assertEqual(records[0]["skill"]["text"], context["parent"]["text"])
        with self.assertRaisesRegex(ValueError, "No Skill"):
            prepare_evidence([trace], plan)
        with self.assertRaises(FileExistsError):
            materialize_skill(context["parent"], path)
        self.assertIsNone(materialize_skill(load_skill(), self.root / "none.md"))

    def test_wrong_gate_and_parent_fail_before_learning(self):
        parents = self.batch(self.context, self.context["parent"], [False] * 3)
        grouping, current, update = self.inputs(self.context, parents)
        candidate = self.candidate(update, "Inspect relevant visible conditions.\n")
        candidates = self.batch(self.context, candidate, [True] * 3)
        gate = gate_round(self.context, candidate, parents, candidates)
        with self.assertRaisesRegex(ValueError, "Learning Gate"):
            prepare_grouped_learning(self.context, grouping, update["plan"], candidate, parents, candidates,
                                     {**gate, "decision": "RETAIN"})
        wrong = deepcopy(current)
        wrong["parent"]["text"] = "Wrong parent"
        with self.assertRaisesRegex(ValueError, "different Parent"):
            update_payload(self.context, wrong, update["plan"])
        other_batch = open_round(self.state, ["train:0003", "train:0004", "train:0005"])
        with self.assertRaisesRegex(ValueError, "another round or task batch"):
            update_payload(other_batch, current, update["plan"])
        with self.assertRaisesRegex(ValueError, "Unknown grouped"):
            grouped_messages("direct", update)

    def test_no_candidate_can_publish_empty_learning_but_not_new_effect(self):
        parents = self.batch(self.context, self.context["parent"], [True] * 3)
        grouping, _, update = self.inputs(self.context, parents)
        plan = {"intent": "No justified change", "requirements": [], "watch": [], "open": []}
        gate = gate_round(self.context, None, parents, [])
        payload = prepare_grouped_learning(self.context, grouping, plan, None, parents, [], gate)
        self.assertIsNone(payload["candidate"]["skill_id"])
        value = {"findings": [], "open": [], "memory_delta": []}
        memory, receipt = learn_grouped_memory(payload, value)
        state = finish_round(self.state, self.context, None, gate, memory, receipt)
        self.assertEqual(state["parent"], self.state["parent"])
        value = self.learning({**payload, "plan": update["plan"]})
        value["findings"][0].update(about=["intent"], refs=["P1:1"])
        with self.assertRaisesRegex(ValueError, "new response"):
            learn_grouped_memory(payload, value)

    def test_missing_watch_response_cannot_produce_publication_receipt(self):
        _, feedback, _ = self.first_round()
        value = self.learning(feedback)
        value["findings"][0]["about"] = ["intent"]
        with self.assertRaisesRegex(ValueError, "Unassessed watch"):
            learn_grouped_memory(feedback, value)

    def test_learning_rejects_gate_or_memory_swapped_after_preparation(self):
        _, feedback, _ = self.first_round()
        for field in ("gate", "memory"):
            changed = deepcopy(feedback)
            if field == "gate":
                changed["update_context"]["gate"]["successes"]["candidate"] = 3
            else:
                changed["memory"] = [{"id": "unbound"}]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "Prepared learning input changed"):
                learn_grouped_memory(changed, self.learning(feedback))

    def test_editor_new_question_reaches_replay_without_mutating_effective_plan(self):
        parents = self.batch(self.context, self.context["parent"], [False] * 3)
        grouping, _, update = self.inputs(self.context, parents)
        value = {"decision": "candidate", "reason": "Synthetic realization.", "candidate_text": "Inspect conditionally.",
                 "issues": [], "watch": [{"id": "editor:w", "about": ["u1"], "question": "Does wording alter scope?"}],
                 "mappings": [{"requirements": ["u1"], "side": "candidate", "excerpt": "Inspect conditionally."}]}
        candidate, plan = realize_editor(value, update)
        self.assertEqual(len(update["plan"]["watch"]), 1)
        self.assertEqual(len(plan["watch"]), 2)
        candidates = self.batch(self.context, candidate, [True] * 3)
        gate = gate_round(self.context, candidate, parents, candidates)
        payload = prepare_grouped_learning(self.context, grouping, plan, candidate, parents, candidates, gate)
        learning = self.learning(payload)
        learning["findings"][0]["about"] = ["w1"]
        with self.assertRaisesRegex(ValueError, "editor:w"):
            learn_grouped_memory(payload, learning)

    def test_parent_only_feedback_can_revise_inherited_effect_without_new_edit(self):
        first, _, _ = self.first_round()
        context = open_round(first, ["train:0003", "train:0004", "train:0005"])
        parents = self.batch(context, context["parent"], [False] * 3)
        grouping, _, _ = self.inputs(context, parents)
        plan = {"intent": "No new executable change", "requirements": [], "watch": [], "open": []}
        gate = gate_round(context, None, parents, [])
        payload = prepare_grouped_learning(context, grouping, plan, None, parents, [], gate)
        effect_id = first["memory"][0]["id"]
        value = {"findings": [{"id": "f1", "about": [effect_id], "refs": ["P1:1"],
                              "observation": "Synthetic current behavior limits the earlier response."}],
                 "open": [], "memory_delta": [{"replace": [effect_id], "claim": "Narrowed synthetic response.",
                    "limits": ["No new Candidate was executed."], "findings": ["f1"], "retire_limits": []}]}
        memory, receipt = learn_grouped_memory(payload, value)
        state = finish_round(first, context, None, gate, memory, receipt)
        self.assertEqual(state["parent"], first["parent"])
        self.assertEqual(memory[0]["supersedes"], [effect_id])
        self.assertEqual(len(memory[0]["basis"]), 2)
        self.assertIsNone(memory[0]["basis"][-1]["actual_update"]["candidate_skill_id"])


if __name__ == "__main__":
    unittest.main()
