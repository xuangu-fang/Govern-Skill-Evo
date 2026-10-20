"""Synthetic frozen-trial routing tests; no live model or environment calls."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.adapters.alfworld.skill_runtime import build_skill_messages, digest, load_skill, make_record, write_record
from src.skill_evolution.v22 import conditional_trial as trial
from tests.skill_evolution.v22.test_compact_cycle import draft, recorded_mock_call
from tests.skill_evolution.v22.test_consume_fixed_plan import edit, identity, read
from tests.skill_evolution.v22.test_compact_learning_view import fixture as history_fixture


class ConditionalTrialTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.repo = self.directory / "repository"
        self.split_root = self.repo / "manifest"
        for split, task in (("train", "train:0006"), ("val", "val:0001")):
            path = self.split_root / split / "items.json"
            path.parent.mkdir(parents=True)
            write_record(path, [{"id": task, "gamefile": "fixture", "task_type": "synthetic"}])
        self.game = self.repo / "game.tw-pddl"
        self.game.write_text("Synthetic game bytes; never executed.")
        self.memory = self.repo / "memory_source.json"
        write_record(self.memory, history_fixture()["memory"])
        self.plan = {
            "schema_version": "v22.conditional_trial.v1", "actor_model": "deepseek-v4-flash",
            "evolution_model": "deepseek-v4-pro", "train_task_ids": ["train:0006"],
            "selection_task_ids": ["val:0001"], "semantic_calls_max": 5, "semantic_retries": 0,
            "episode_retries": 0, "adoption": "staging_only", "max_steps_per_episode": 1,
            "actor_workers": 1, "evaluation_repeats": 1, "branch_order": list(trial.ARMS),
            "environment_episodes_max": 4, "memory_source": "memory_source.json",
            "memory_sha256": digest(self.memory.read_bytes()),
            "profile": "v22.conditional_update.v1", "transport_attempts_per_request_max": 6,
            "request_parameters": {"temperature": 1.0, "max_tokens": 16384, "reasoning_effort": "medium",
                                   "thinking": {"type": "enabled"}, "stream": False},
        }
        self.plan_path = self.repo / "config/plan.json"
        self.plan_path.parent.mkdir()
        write_record(self.plan_path, self.plan)
        for target, value in (("REPO_ROOT", self.repo), ("SPLIT_ROOT", self.split_root)):
            patcher = mock.patch.object(trial, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(trial.subprocess, "check_output", return_value="synthetic-git-head\n")
        patcher.start()
        self.addCleanup(patcher.stop)

    def episode(self, job, output_root, plan):
        """Produce fully recorded fixture evidence, through the real verifier."""
        split = job["split"]
        record = make_record(item={"id": job["task_id"], "gamefile": "fixture", "task_type": "synthetic"},
                             split=split, purpose=job["purpose"], skill=load_skill(job.get("skill_path")),
                             model=plan["actor_model"], max_steps=plan["max_steps_per_episode"],
                             gamefile=self.game, manifest_path=self.split_root / split / "items.json",
                             versions={"alfworld": "synthetic"}, backend_id="synthetic")
        observation, commands = "Your task is to: inspect the room.", ["look"]
        record.update(initial_observation=observation, initial_admissible_commands=commands,
                      status="success", won=True, finished_at=trial.timestamp())
        record["steps"] = [{"step": 1, "phase": "executed", "messages": build_skill_messages(
            observation, commands, "inspect the room.", [], record["skill"]), "admissible_commands": commands,
            "model_response": {"content": "<action>look</action>", "response_model": plan["actor_model"],
                               "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}},
            "action": "look", "fallback": None, "action_in_admissible_commands": True,
            "observation": "Synthetic fixture completion.", "reward": 1, "won": True, "done": True}]
        path = output_root / job["key"] / "skill_fixture/trajectory.json"
        path.parent.mkdir(parents=True)
        write_record(path, record)
        return {**job, "skill_path": str(job["skill_path"]) if job.get("skill_path") else None,
                "trajectory": str(path), "status": "success"}

    def batch(self, jobs, output_root, plan, env_file):
        return [self.episode(job, output_root, plan) for job in jobs]

    def operation(self, name="trial", *, fail_stage=None, stop_stage=None, echo=False,
                  changed_echo=False, diagnosis_stop=None):
        root = self.directory / name
        trial.initialize(self.plan_path, root)
        self.assertEqual(trial.collect(root, "unused.env", execute_batch=self.batch)["status"], "train_ready")
        calls, inputs = [], {}

        def generate(stage, messages, output):
            calls.append(stage)
            payload = json.loads(messages[1]["content"])
            inputs[stage] = deepcopy(payload)
            if stage == fail_stage:
                value = '{"incomplete":'
            elif stage == "diagnosis":
                value = draft()
                if diagnosis_stop:
                    value.update(decision=diagnosis_stop, plan=None)
            elif stage.endswith("_proposal"):
                value = identity()
                if stage == stop_stage:
                    value.update(decision="needs_revision", open=[{
                        "about": ["intent"], "reason": "Synthetic unavailable condition needs diagnosis."}])
            else:
                value = edit(payload, stop=stage == stop_stage)
                if echo and stage == "direct_editor":
                    value["watch"] = deepcopy(payload["plan"]["watch"])
                    if changed_echo:
                        value["watch"][0]["question"] += " Changed meaning."
            return recorded_mock_call(stage, messages, output, value, self.plan["evolution_model"])

        report = trial.construct(root, generate)
        return root, report, calls, inputs, generate

    def test_same_information_branches_and_frozen_selection_have_no_learning_route(self):
        root, report, calls, inputs, generate = self.operation()
        self.assertEqual(report["status"], "frozen", report)
        self.assertEqual(calls, list(trial.STAGES))
        self.assertNotIn("memory", inputs["diagnosis"])
        self.assertEqual(inputs["direct_proposal"], inputs["conditioned_proposal"])
        self.assertEqual(inputs["direct_editor"]["memory"], inputs["conditioned_editor"]["memory"])
        self.assertTrue(inputs["direct_editor"]["memory"])
        self.assertTrue(all(run["task_id"].startswith("train:") for run in inputs["diagnosis"]["runs"].values()))
        self.assertEqual(trial.verify(root)["status"], "frozen")
        frozen = {Path(row["path"]): Path(row["path"]).read_bytes() for row in read(root / "freeze.json")["files"]}
        result = trial.evaluate(root, "unused.env", execute_batch=self.batch)
        self.assertEqual(result["status"], "evaluated")
        self.assertEqual(trial.verify(root)["status"], "evaluated")
        self.assertEqual(len(result["selection"]), 3)
        self.assertEqual(calls, list(trial.STAGES))
        self.assertEqual(frozen, {path: path.read_bytes() for path in frozen})
        self.assertTrue(read(root / "evaluation_summary.json")["complete_three_arm_comparison"])
        for entry in result["selection"]:
            self.assertEqual((entry["split"], entry["purpose"]), ("val", "selection"))
        with self.assertRaisesRegex(ValueError, "single-use"):
            trial.construct(root, generate)
        with self.assertRaisesRegex(ValueError, "single-use"):
            trial.evaluate(root, "unused.env", execute_batch=self.batch)

    def test_raw_editor_text_survives_only_exact_inherited_watch_normalization(self):
        root, report, _, _, _ = self.operation(echo=True)
        self.assertEqual(report["branches"]["direct"]["removed_exact_watch_echoes"], 1)
        raw = read(root / "raw_outputs/direct_editor.json")
        normalized = read(root / "outputs/direct_editor.json")
        self.assertEqual(normalized["watch"], [])
        self.assertEqual({key: value for key, value in raw.items() if key != "watch"},
                         {key: value for key, value in normalized.items() if key != "watch"})
        self.assertEqual((root / "candidates/direct/SKILL.md").read_text(), raw["candidate_text"])
        self.assertEqual(trial.verify(root)["status"], "frozen")
        other, result, _, _, _ = self.operation(name="different_echo", echo=True, changed_echo=True)
        self.assertEqual(result["branches"]["direct"]["status"], "error")
        self.assertNotIn("direct", read(other / "freeze.json")["arms"])
        self.assertEqual(result["branches"]["conditioned"]["status"], "candidate")

    def test_branch_failure_or_semantic_stop_does_not_retry_or_cancel_other_branch(self):
        for stage, mode in (("direct_proposal", "fail"), ("direct_proposal", "stop"),
                            ("direct_editor", "stop"), ("conditioned_editor", "fail")):
            with self.subTest(stage=stage, mode=mode):
                root, report, calls, _, _ = self.operation(name=stage + mode,
                    fail_stage=stage if mode == "fail" else None,
                    stop_stage=stage if mode == "stop" else None)
                arm = stage.split("_", 1)[0]
                other = "conditioned" if arm == "direct" else "direct"
                self.assertEqual(report["branches"][arm]["status"], "error" if mode == "fail" else "needs_revision")
                self.assertEqual(report["branches"][other]["status"], "candidate")
                self.assertEqual(calls.count(stage), 1)
                self.assertNotIn(arm, read(root / "freeze.json")["arms"])
                self.assertFalse((root / "candidates" / arm / "SKILL.md").exists())
                if stage.endswith("_proposal"):
                    self.assertNotIn(arm + "_editor", calls)
                self.assertEqual(trial.verify(root)["status"], "frozen")

    def test_diagnosis_stop_prevents_candidate_construction_and_evaluation(self):
        for decision in ("no_change", "need_evidence"):
            with self.subTest(decision=decision):
                root, report, calls, _, _ = self.operation(name=decision, diagnosis_stop=decision)
                self.assertEqual(report["status"], decision)
                self.assertEqual(calls, ["diagnosis"])
                self.assertFalse((root / "freeze.json").exists())
                self.assertEqual(trial.verify(root)["status"], decision)

    def test_bound_source_and_frozen_candidate_changes_are_rejected_before_evaluation(self):
        root, _, _, _, _ = self.operation()
        calls = mock.Mock(side_effect=AssertionError("No episode may start after tampering."))
        for path in (root / "candidates/direct/SKILL.md", root / "freeze.json", self.memory):
            original = path.read_bytes()
            try:
                path.write_bytes(original + b"\n")
                with self.assertRaises(ValueError):
                    trial.evaluate(root, "unused.env", execute_batch=calls)
            finally:
                path.write_bytes(original)
        calls.assert_not_called()
        trial.check_freeze(root)

    def test_plan_rejects_wrong_split_old_tasks_and_extra_budget(self):
        for field, value in (("train_task_ids", ["val:0001"]), ("selection_task_ids", ["train:0006"]),
                             ("train_task_ids", ["train:0000"]), ("semantic_calls_max", 6),
                             ("episode_retries", 1), ("environment_episodes_max", 99)):
            with self.subTest(field=field, value=value):
                plan = deepcopy(self.plan)
                plan[field] = value
                with self.assertRaises(ValueError):
                    trial.validate_plan(plan)

    def test_valid_selection_trace_cannot_enter_train_learning(self):
        root = self.directory / "selection_rejected"
        trial.initialize(self.plan_path, root)
        trial.collect(root, "unused.env", execute_batch=self.batch)
        row = self.episode({"key": "val_fixture", "task_id": "val:0001", "split": "val",
                            "purpose": "selection", "skill_path": None}, root / "heldout_fixture", self.plan)
        path, record = Path(row["trajectory"]), read(Path(row["trajectory"]))
        self.assertTrue(trial.verify_record(record)["episode_complete"])
        with self.assertRaisesRegex(ValueError, "cannot be exported as learning feedback"):
            trial.build_learning_payload(load_skill(), load_skill(), "", draft()["plan"], [record], [])
        # Rebind only this synthetic fixture to test routing after valid provenance.
        report = read(root / "report.json")
        report["train"] = [row]
        write_record(root / "report.json", report)
        write_record(root / "train_sources.json", trial.bindings([path]))
        with self.assertRaisesRegex(ValueError, "Train order differs"):
            trial.current_input(root)

    def test_incomplete_train_cannot_begin_construction_or_retry_collection(self):
        root = self.directory / "incomplete"
        trial.initialize(self.plan_path, root)
        report = trial.collect(root, "unused.env", execute_batch=lambda jobs, *args: [
            {"key": job["key"], "trajectory": None, "status": "error"} for job in jobs])
        self.assertEqual(report["status"], "train_incomplete")
        calls = mock.Mock()
        with self.assertRaisesRegex(ValueError, "completed fresh Train"):
            trial.construct(root, calls)
        with self.assertRaisesRegex(ValueError, "single-use"):
            trial.collect(root, "unused.env", execute_batch=self.batch)
        calls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
