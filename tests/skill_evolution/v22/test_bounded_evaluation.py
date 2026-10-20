"""Scheduling and failure-accounting fixtures; no provider or environment calls."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

from src.adapters.alfworld.skill_runtime import build_skill_messages, load_skill, make_record, write_record
from src.skill_evolution.v22 import bounded_evaluation as target


class BoundedEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = {"actor_model": "fixture-model", "max_steps_per_episode": 1, "actor_workers": 3,
                     "selection_task_ids": ["val:0001", "val:0002", "val:0003"]}
        self.skill = self.root / "skill.md"
        self.skill.write_text("Inspect current state before continuing.\n")
        self.freeze = {"arms": {"parent": {"skill_file": None, "skill_id": "none"},
                                "direct": {"skill_file": "skill.md", "skill_id": load_skill(self.skill)["skill_id"]},
                                "conditioned": {"skill_file": "skill.md", "skill_id": load_skill(self.skill)["skill_id"]}}}

    def fake_process(self, command, **kwargs):
        def arg(name):
            return command[command.index(name) + 1]
        root = Path(arg("--output-root"))
        item = {"id": arg("--task-id"), "gamefile": "fixture", "task_type": "synthetic"}
        game, manifest = self.root / "game.tw-pddl", self.root / "items.json"
        # Created before worker launches, so independent fixture records share conditions.
        skill = load_skill(arg("--skill-file") if "--skill-file" in command else None)
        record = make_record(item=item, split=arg("--split"), purpose=arg("--purpose"), skill=skill,
                             model=arg("--model"), max_steps=int(arg("--max-steps")), gamefile=game,
                             manifest_path=manifest, versions={"alfworld": "fixture"}, backend_id="fixture")
        observation = "Your task is to: inspect the room."
        success = item["id"] != "val:0002"
        record.update(initial_observation=observation, initial_admissible_commands=["look"],
                      status="success" if success else "step_limit", won=success, finished_at="fixture")
        record["steps"] = [{"step": 1, "phase": "executed", "messages": build_skill_messages(
            observation, ["look"], "inspect the room.", [], skill), "admissible_commands": ["look"],
            "model_response": {"content": "<action>look</action>", "response_model": "fixture-model",
                               "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}},
            "action": "look", "fallback": None, "action_in_admissible_commands": True,
            "observation": "room", "reward": int(success), "won": success, "done": success}]
        path = root / "skill_fixture/trajectory.json"
        path.parent.mkdir()
        write_record(path, record)
        return SimpleNamespace(returncode=0)

    def fixture_files(self, task_ids):
        (self.root / "game.tw-pddl").write_text("synthetic game bytes; never executed")
        write_record(self.root / "items.json", [{"id": key, "gamefile": "fixture", "task_type": "synthetic"}
                                                for key in task_ids])

    def test_selection_rotates_ready_arms_and_binds_frozen_skill(self):
        jobs = target.selection_jobs(self.plan, self.freeze, self.root)
        self.assertEqual([job["arm"] for job in jobs],
                         ["parent", "direct", "conditioned", "direct", "conditioned", "parent",
                          "conditioned", "parent", "direct"])
        self.assertEqual(jobs[0]["key"], "val_0001_parent")
        self.assertTrue(all(job["split"] == "val" and job["purpose"] == "selection" for job in jobs))
        self.assertIsNone(jobs[0]["skill_path"])
        self.skill.write_text("Changed after freeze.")
        with self.assertRaises(ValueError):
            target.selection_jobs(self.plan, self.freeze, self.root)

    def test_missing_candidate_is_not_fabricated(self):
        del self.freeze["arms"]["conditioned"]
        jobs = target.selection_jobs(self.plan, self.freeze, self.root)
        self.assertEqual(len(jobs), 6)
        self.assertEqual({job["arm"] for job in jobs}, {"parent", "direct"})

    def test_episode_runs_once_and_retains_nonzero_trace(self):
        self.fixture_files(["val:0001"])
        def fail_after_trace(command, **kwargs):
            self.fake_process(command, **kwargs)
            return SimpleNamespace(returncode=1)
        out = self.root / "episode"
        with mock.patch.object(target.subprocess, "run", side_effect=fail_after_trace) as call, \
                mock.patch("src.adapters.alfworld.skill_runtime.implementation_metadata", return_value={"fixture": True}):
            path = target.execute_episode("val:0001", "val", "selection", None, out, self.plan, ".env")
            self.assertEqual(call.call_count, 1)
            with self.assertRaises(FileExistsError):
                target.execute_episode("val:0001", "val", "selection", None, out, self.plan, ".env")
            self.assertEqual(call.call_count, 1)
        self.assertTrue(path.is_file())
        process = json.loads((out / "process.json").read_text())
        self.assertEqual(process["exit_code"], 1)
        self.assertEqual(process["trajectories"], [str(path)])
        self.assertNotIn("--skill-file", process["command"])

    def test_launch_failure_has_safe_process_accounting(self):
        out = self.root / "failure"
        with mock.patch.object(target.subprocess, "run", side_effect=OSError("secret-provider-detail")) as call:
            with self.assertRaises(OSError):
                target.execute_episode("train:0002", "train", "learning", None, out, self.plan, ".env")
        self.assertEqual(call.call_count, 1)
        process = json.loads((out / "process.json").read_text())
        self.assertEqual(process["error_type"], "OSError")
        self.assertNotIn("secret-provider-detail", (out / "process.json").read_text())

    def test_batch_keeps_job_order_and_other_jobs_after_launch_failure(self):
        jobs = target.selection_jobs(self.plan, self.freeze, self.root)
        self.fixture_files(self.plan["selection_task_ids"])
        def process(command, **kwargs):
            if command[command.index("--output-root") + 1].endswith("val_0003_direct"):
                raise OSError("private")
            return self.fake_process(command, **kwargs)
        with mock.patch.object(target.subprocess, "run", side_effect=process) as call, \
                mock.patch("src.adapters.alfworld.skill_runtime.implementation_metadata", return_value={"fixture": True}):
            rows = target.execute_batch(jobs, self.root / "batch", self.plan, ".env")
        self.assertEqual(call.call_count, 9)
        self.assertEqual([row["key"] for row in rows], [job["key"] for job in jobs])
        errors = [row for row in rows if row["status"] == "error"]
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "OSError")
        self.assertIsNone(errors[0]["success"])
        self.assertEqual(sum(row["audit"] is not None for row in rows), 8)
        summary = target.summarize_selection(rows)
        self.assertEqual(summary["arms"]["direct"]["incomplete_or_invalid"], 1)
        self.assertEqual(summary["arms"]["conditioned"]["successes"], 2)
        self.assertEqual(summary["comparable_pairs"], 2)
        self.assertEqual(summary["conditioned_only_successes"], 0)

    def test_bad_batch_fails_preflight_without_launch(self):
        jobs = target.selection_jobs(self.plan, self.freeze, self.root)
        variants = [jobs + [jobs[0]], [{**jobs[0], "key": "../escape"}],
                    [{**jobs[0], "split": "test", "purpose": "final", "task_id": "test:0001"}]]
        with mock.patch.object(target.subprocess, "run") as call:
            for index, variant in enumerate(variants):
                root = self.root / f"refused_{index}"
                with self.assertRaises(ValueError):
                    target.execute_batch(variant, root, self.plan, ".env")
                self.assertFalse(root.exists())
        call.assert_not_called()

    def test_selection_never_accepts_train_or_test_task_ids(self):
        for task in ("train:0001", "test:0001"):
            plan = {**self.plan, "selection_task_ids": [task]}
            with self.assertRaises(ValueError):
                target.selection_jobs(plan, self.freeze, self.root)

    def test_batch_retains_trace_when_audit_rejects_wrong_job_identity(self):
        self.fixture_files(["val:0001"])
        jobs = target.selection_jobs({**self.plan, "selection_task_ids": ["val:0001"]}, self.freeze, self.root)[:1]
        with mock.patch.object(target.subprocess, "run", side_effect=self.fake_process), \
                mock.patch("src.adapters.alfworld.skill_runtime.implementation_metadata", return_value={"fixture": True}), \
                mock.patch.object(target, "verify_record", side_effect=ValueError("bad trace")):
            row = target.execute_batch(jobs, self.root / "bad_audit", self.plan, ".env")[0]
        self.assertEqual(row["status"], "error")
        self.assertEqual(row["error_type"], "ValueError")
        self.assertEqual(len(row["trajectories"]), 1)
        self.assertTrue(Path(row["trajectory"]).is_file())
        self.assertIsNone(row["success"])


if __name__ == "__main__":
    unittest.main()
