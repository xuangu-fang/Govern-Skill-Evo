"""Offline orchestration tests. Synthetic outcomes are not experiment evidence."""

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import (
    build_skill_messages, load_skill, make_record, object_digest, write_record,
)
from src.skill_evolution.v22.continual_runner import run_campaign
from src.skill_evolution.v22.continual_runtime import load_bundle
from src.skill_evolution.v22.continual_state import read_state


REPO = Path(__file__).resolve().parents[3]
PLAN = REPO / "experiments/methods/v22/08_grouped_continual/config/plan.json"


class SyntheticCampaign:
    """Recorded local callbacks implementing the same boundary as real adapters."""

    def __init__(self, root, bundle):
        self.root, self.bundle = root, bundle
        self.game = root / "synthetic.tw-pddl"
        self.game.write_text("Offline fixture; never an ALFWorld execution.")
        self.manifest = REPO / "benchmarks/alfworld/editions/skillopt_39_18_134/train/items.json"
        self.calls, self.executions = [], []
        self.round_slots = Counter()
        self.override = {}
        self.oversized = False
        self.incomplete_candidate = False
        self.tamper_candidate = False
        self.interrupt_stage = None

    @staticmethod
    def round_name(path):
        return next(part for part in Path(path).parts if part in ("r1", "r2"))

    def execute(self, task_item, skill_file, output_root):
        output_root = Path(output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        round_id = self.round_name(output_root)
        slot = self.round_slots[round_id]
        self.round_slots[round_id] += 1
        side = "parent" if slot < 10 else "candidate"
        index = slot % 10
        skill = load_skill(skill_file)
        self.executions.append((round_id, side, task_item["id"], deepcopy(skill)))
        won = index == 0 if side == "parent" else index in ({1, 2} if round_id == "r1" else {1})
        record = make_record(item=task_item, split="train", purpose="learning", skill=skill,
                             model="deepseek-v4-flash", max_steps=50, gamefile=self.game,
                             manifest_path=self.manifest, versions={"alfworld": "synthetic-fixture"},
                             backend_id="synthetic-fixture")
        observation = "Your task is to: inspect the visible room."
        if self.oversized:
            observation += "x" * 400001
        commands = ["look"]
        record.update(run_id=f"offline-{round_id}-{slot}", initial_observation=observation,
                      initial_admissible_commands=commands, won=won,
                      status="success" if won else "environment_ended", finished_at="synthetic")
        record["steps"] = [{
            "step": 1, "phase": "executed", "messages": build_skill_messages(
                observation, commands, observation.split("Your task is to: ", 1)[1], [], skill),
            "admissible_commands": commands,
            "model_response": {"content": "<action>look</action>", "response_model": "deepseek-v4-flash"},
            "action": "look", "fallback": None, "action_in_admissible_commands": True,
            "observation": "Synthetic visible outcome.", "reward": int(won), "done": True, "won": won,
        }]
        if self.incomplete_candidate and side == "candidate":
            record.update(status="error", won=False)
            record["steps"] = []
        output = output_root / "trajectory.json"
        write_record(output, record)
        if self.tamper_candidate and side == "candidate":
            Path(skill_file).write_text("Changed after the frozen Candidate was selected.\n")
            self.tamper_candidate = False
        return output

    def generate(self, stage, messages, output_path):
        output_path = Path(output_path)
        round_id = self.round_name(output_path)
        view = json.loads(messages[-1]["content"])
        self.calls.append((round_id, stage, deepcopy(view)))
        if self.interrupt_stage == (round_id, stage):
            raise KeyboardInterrupt()
        if stage == "classification":
            value = {"groups": [{"group_id": "G1", "decision_problem": "When is a further visible inspection useful?",
                "members": [row["task_ref"] for row in view["experiences"]],
                "shared_basis": "The observed requests and interactions expose an inspection decision.",
                "important_differences": ["The synthetic native outcomes differ."]}]}
        elif stage == "diagnosis":
            group_ref = next(ref for ref in view["sources"] if ref.startswith("group:"))
            value = {"decision": "revise", "reason": "Synthetic current evidence supports a bounded update.",
                "plan": {"intent": "Improve relevant inspection while retaining useful behavior.",
                    "requirements": [{"id": "u1", "text": "Inspect when current visible evidence is insufficient.",
                        "basis": [group_ref, "P1:1"]}],
                    "watch": [{"id": "w1", "about": ["u1"], "question": "Does conditional inspection help or interfere?"}],
                    "open": []}}
        elif stage == "fusion":
            effect_id = view["memory"][0]["id"] if view["memory"] else None
            value = {"decision": "ready", "reason": "Use the prior measured bundle's scope limitation.",
                "changes": [{"from": ["u1"], "to": [{"id": "u2", "text": "Inspect only when the available observation is insufficient for the relevant decision."}],
                    "basis": [effect_id], "reason": "The observed local regression motivates narrowing the visible trigger.",
                    "disposition": "replace"}],
                "watch_changes": [{"from": ["w1"], "to": [{"id": "w2", "about": ["u2"], "question": "Does the narrowed scope retain useful behavior?"}]}],
                "open": []}
            if effect_id is None:
                value = {"decision": "ready", "reason": "No applicable measured history; Keep the current draft.",
                         "changes": [], "watch_changes": [], "open": []}
        elif stage == "main_editor":
            text = (view["parent"].get("text") or "") + (
                "Inspect when the visible evidence does not support the required decision.\n" if round_id == "r1"
                else "Narrow further inspection to the relevant unresolved visible condition.\n")
            value = {"decision": "candidate", "reason": "Synthetic faithful realization.",
                "candidate_text": text, "mappings": [{"requirements": [row["id"] for row in view["plan"]["requirements"]],
                    "side": "candidate", "excerpt": text}], "issues": [], "watch": []}
        elif stage == "post_gate_learning":
            round_root = output_path.parent.parent
            assert (round_root / "gate.json").is_file(), "Gate must precede Memory learning"
            assert not (round_root / "state.json").exists(), "State must wait for valid Memory"
            group_ref = next(ref for ref in view["sources"] if ref.startswith("group:"))
            refs = ["P1:1", "C1:1", group_ref]
            value = {"findings": [{"id": "f1", "about": [row["id"] for row in view["plan"]["watch"]],
                "observation": "Synthetic paired bundle includes a local regression; isolated contributions are unknown.",
                "refs": refs}], "open": [], "memory_delta": [{"replace": [],
                    "claim": "The synthetic joint update changes inspection behavior under the observed conditions.",
                    "limits": ["Synthetic test only; bundled observations do not identify individual effects."],
                    "findings": ["f1"], "retire_limits": []}]}
            if not view["candidate"].get("skill_id"):
                value["findings"][0].update(
                    about=[row["id"] for row in view["plan"]["watch"]] or ["intent"],
                    observation="Current Parent observations add no measured new editing response.",
                    refs=["P1:1", group_ref])
                value["memory_delta"] = []
        else:
            raise AssertionError(f"Unexpected stage: {stage}")
        replacement = self.override.get((round_id, stage))
        if replacement is not None:
            value = replacement(value, view) if callable(replacement) else deepcopy(replacement)
        raw = json.dumps(value, ensure_ascii=False)
        parameters = {"model": "deepseek-v4-pro", **self.bundle["plan"]["models"]["request_parameters"]}
        usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        response = {"content": raw, "response_model": "deepseek-v4-pro", "finish_reason": "stop",
                    "usage": usage, "api_attempts": 1, "transport_retries": 0}
        call = {"schema_version": "v22_semantic_call_v1", "stage": stage, "model": "deepseek-v4-pro",
                "messages_sha256": object_digest(messages), "status": "responded",
                "started_at": "synthetic", "finished_at": "synthetic", "steps": [{"messages": messages,
                    "phase": "responded", "model_response": response, "transport_attempts": [{"attempt": 1,
                        "request_parameters": parameters, "request_sha256": object_digest({**parameters, "messages": messages}),
                        "status": "responded", "http_status": 200, "usage": usage}]}]}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_record(output_path, call)
        return raw


class ContinualRunnerTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "campaign"
        self.bundle = load_bundle(PLAN)
        self.callbacks = SyntheticCampaign(self.root, self.bundle)

    def run_campaign(self):
        return run_campaign(self.bundle, self.output, self.callbacks.generate,
                            self.callbacks.execute, offline=True)

    def read(self, relative):
        return json.loads((self.output / relative).read_text())

    def assert_stopped(self, report, published):
        self.assertEqual(report["status"], "error", report)
        self.assertEqual(report["published_rounds"], published)
        self.assertEqual(read_state(Path(report["latest_state"]))["round_index"], published)

    def test_two_round_mainline_accepts_then_retains_real_parent_and_memory(self):
        report = self.run_campaign()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(report["published_rounds"], 2)
        self.assertEqual(len(self.callbacks.executions), 40)
        self.assertEqual(Counter(row[1] for row in self.callbacks.calls), {
            "classification": 2, "diagnosis": 2, "main_editor": 2, "post_gate_learning": 2, "fusion": 1})
        first = read_state(self.output / "rounds/r1/state.json")
        final = read_state(Path(report["latest_state"]))
        self.assertEqual(first["last_round"]["gate"]["decision"], "ACCEPT")
        self.assertEqual(final["last_round"]["gate"]["decision"], "RETAIN")
        self.assertEqual(first["parent"], final["parent"])
        self.assertEqual(len(final["memory"]), 2)
        self.assertEqual(len(set(final["seen_task_ids"])), 20)
        for round_id, side, _, skill in self.callbacks.executions:
            if round_id == "r2" and side == "parent":
                self.assertEqual(skill["text"], first["parent"]["text"])
                self.assertEqual(skill["skill_id"], first["parent"]["skill_id"])
        diagnosis = next(view for r, stage, view in self.callbacks.calls if r == "r2" and stage == "diagnosis")
        fusion = next(view for r, stage, view in self.callbacks.calls if r == "r2" and stage == "fusion")
        self.assertFalse(diagnosis.get("memory"))
        self.assertEqual(fusion["memory"][0]["id"], first["memory"][0]["id"])
        effective = self.read("rounds/r2/effective_plan.json")
        self.assertEqual(effective["requirements"][0]["id"], "u2")
        for round_id in ("r1", "r2"):
            root = self.output / "rounds" / round_id
            for artifact in ("context.json", "grouping_input.json", "grouping.json", "initial_plan.json",
                             "effective_plan.json", "candidate.json", "candidate/SKILL.md", "execution_plan.json",
                             "replay_freeze.json", "gate.json", "learning_input.json", "memory_after.json",
                             "memory_receipt.json", "state.json", "report.json"):
                self.assertTrue((root / artifact).is_file(), (round_id, artifact))
            for directory in ("inputs", "messages", "calls", "outputs", "raw_outputs"):
                self.assertTrue((root / directory).is_dir(), directory)
            self.assertFalse(list(root.rglob("*direct*")))
        self.assertTrue((self.output / "runtime_freeze.json").is_file())

    def test_semantic_no_change_publishes_no_skill_without_fabricated_replay_or_learning(self):
        for round_id in ("r1", "r2"):
            self.callbacks.override[(round_id, "diagnosis")] = {
                "decision": "no_change", "reason": "No justified synthetic update.", "plan": None}
        report = self.run_campaign()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(report["published_rounds"], 2)
        self.assertEqual(len(self.callbacks.executions), 20)
        self.assertEqual(Counter(row[1] for row in self.callbacks.calls), {"classification": 2, "diagnosis": 2})
        state = read_state(Path(report["latest_state"]))
        self.assertEqual(state["parent"], load_skill())
        self.assertEqual(state["memory"], [])
        self.assertEqual(state["last_round"]["gate"]["reason"], "no_change")

    def test_empty_learned_memory_allows_second_round_keep(self):
        def no_effect(value, _):
            value["memory_delta"] = []
            return value
        for round_id in ("r1", "r2"):
            self.callbacks.override[(round_id, "post_gate_learning")] = no_effect
        report = self.run_campaign()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(len(self.callbacks.executions), 40)
        self.assertEqual(len(self.callbacks.calls), 9)
        self.assertEqual(self.read("rounds/r2/outputs/fusion.json")["changes"], [])
        self.assertEqual(self.read("rounds/r2/initial_plan.json"), self.read("rounds/r2/effective_plan.json"))
        self.assertEqual(read_state(Path(report["latest_state"]))["memory"], [])

    def test_identical_editor_text_becomes_no_change_and_retains_learned_memory(self):
        def identical(value, view):
            text = view["parent"]["text"]
            value["candidate_text"] = text
            value["mappings"][0]["excerpt"] = text
            return value
        self.callbacks.override[("r2", "main_editor")] = identical
        report = self.run_campaign()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(len(self.callbacks.executions), 30)
        first = read_state(self.output / "rounds/r1/state.json")
        final = read_state(Path(report["latest_state"]))
        self.assertEqual(final["parent"], first["parent"])
        self.assertEqual(final["memory"], first["memory"])
        self.assertEqual(self.read("rounds/r2/outputs/main_editor.json")["decision"], "no_change")
        self.assertEqual(self.read("rounds/r2/raw_outputs/main_editor.json")["decision"], "candidate")
        self.assertEqual(final["last_round"]["gate"]["reason"], "no_change")

    def test_editor_blocker_is_semantic_retain_and_does_not_retry(self):
        self.callbacks.override[("r1", "main_editor")] = {
            "decision": "needs_revision", "reason": "A required observable condition remains unresolved.",
            "candidate_text": None, "mappings": [], "issues": [{"about": ["u1"],
                "reason": "The required visible trigger is not expressible."}], "watch": []}
        self.callbacks.override[("r2", "diagnosis")] = {
            "decision": "need_evidence", "reason": "Current evidence cannot resolve the trigger.", "plan": None}
        report = self.run_campaign()
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(report["published_rounds"], 2)
        self.assertEqual(len(self.callbacks.executions), 20)
        self.assertEqual(sum(stage == "main_editor" for _, stage, _ in self.callbacks.calls), 1)
        self.assertIn("needs_revision", report["rounds"][0]["update_status"])
        self.assertIn("need_evidence", report["rounds"][1]["update_status"])
        self.assertEqual(read_state(Path(report["latest_state"]))["parent"], load_skill())

    def test_invalid_partition_stops_without_diagnosis_or_second_round(self):
        def duplicate(value, _):
            value["groups"][0]["members"].append(value["groups"][0]["members"][0])
            return value
        self.callbacks.override[("r1", "classification")] = duplicate
        report = self.run_campaign()
        self.assert_stopped(report, 0)
        self.assertEqual(len(self.callbacks.executions), 10)
        self.assertEqual([stage for _, stage, _ in self.callbacks.calls], ["classification"])
        self.assertTrue((self.output / "rounds/r1/raw_outputs/classification.txt").is_file())
        self.assertFalse((self.output / "rounds/r2").exists())

    def test_oversized_input_stops_before_any_semantic_call(self):
        self.callbacks.oversized = True
        report = self.run_campaign()
        self.assert_stopped(report, 0)
        self.assertEqual(self.callbacks.calls, [])
        self.assertEqual(len(self.callbacks.executions), 10)

    def test_diagnosis_cannot_rebind_tampered_parent_evidence_or_grouping(self):
        for target in ("trajectory", "grouping"):
            with self.subTest(target=target):
                self.output = self.root / f"tamper-{target}"
                self.callbacks = SyntheticCampaign(self.root, self.bundle)

                def tamper(value, _):
                    directory = self.output / "rounds/r1"
                    if target == "trajectory":
                        path = next((directory / "parent_runs").rglob("trajectory.json"))
                        record = json.loads(path.read_text())
                        record["steps"][0]["observation"] = "Rewritten after classification consumed the original event."
                        write_record(path, record)
                    else:
                        path = directory / "grouping.json"
                        grouping = json.loads(path.read_text())
                        grouping["groups"][0]["decision_problem"] = "Rewritten after grouping was frozen."
                        write_record(path, grouping)
                    return value

                self.callbacks.override[("r1", "diagnosis")] = tamper
                report = self.run_campaign()
                self.assert_stopped(report, 0)
                self.assertEqual([stage for _, stage, _ in self.callbacks.calls], ["classification", "diagnosis"])
                self.assertEqual(len(self.callbacks.executions), 10)
                self.assertFalse((self.output / "rounds/r1/outputs/fusion.json").exists())
                self.assertFalse((self.output / "rounds/r1/gate.json").exists())
                self.assertFalse((self.output / "rounds/r2").exists())

    def test_incomplete_candidate_cannot_reach_gate_learning_or_publication(self):
        self.callbacks.incomplete_candidate = True
        report = self.run_campaign()
        self.assert_stopped(report, 0)
        self.assertFalse((self.output / "rounds/r1/gate.json").exists())
        self.assertFalse(any(stage == "post_gate_learning" for _, stage, _ in self.callbacks.calls))
        self.assertFalse((self.output / "rounds/r2").exists())

    def test_invalid_memory_after_accept_preserves_initial_publication(self):
        self.callbacks.override[("r1", "post_gate_learning")] = {"findings": [], "open": [], "memory_delta": []}
        report = self.run_campaign()
        self.assert_stopped(report, 0)
        self.assertEqual(self.read("rounds/r1/gate.json")["decision"], "ACCEPT")
        self.assertFalse((self.output / "rounds/r1/state.json").exists())
        self.assertFalse((self.output / "rounds/r2").exists())
        self.assertEqual(len(self.callbacks.executions), 20)

    def test_second_round_learning_failure_preserves_previous_skill_and_memory(self):
        self.callbacks.override[("r2", "post_gate_learning")] = {"findings": [], "open": [], "memory_delta": []}
        report = self.run_campaign()
        self.assert_stopped(report, 1)
        self.assertEqual(read_state(Path(report["latest_state"])), read_state(self.output / "rounds/r1/state.json"))
        self.assertFalse((self.output / "rounds/r2/state.json").exists())

    def test_candidate_file_drift_stops_further_execution_and_publication(self):
        self.callbacks.tamper_candidate = True
        report = self.run_campaign()
        self.assert_stopped(report, 0)
        candidates = [row for row in self.callbacks.executions if row[1] == "candidate"]
        self.assertLessEqual(len(candidates), self.bundle["plan"]["budget"]["actor_workers_max"])
        self.assertFalse((self.output / "rounds/r2").exists())
        self.assertFalse(any(stage == "post_gate_learning" for _, stage, _ in self.callbacks.calls))

    def test_interruption_keeps_pending_artifacts_without_publishing(self):
        self.callbacks.interrupt_stage = ("r1", "post_gate_learning")
        report = self.run_campaign()
        self.assertEqual(report["status"], "interrupted", report)
        self.assertEqual(report["published_rounds"], 0)
        self.assertEqual(self.read("rounds/r1/gate.json")["decision"], "ACCEPT")
        self.assertFalse((self.output / "rounds/r1/state.json").exists())

    def test_existing_output_directory_is_never_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / "previous.txt"
        sentinel.write_text("Preserve existing evidence.")
        with self.assertRaises(FileExistsError):
            self.run_campaign()
        self.assertEqual(sentinel.read_text(), "Preserve existing evidence.")
        self.assertFalse(self.callbacks.calls)
        self.assertFalse(self.callbacks.executions)


if __name__ == "__main__":
    unittest.main()
