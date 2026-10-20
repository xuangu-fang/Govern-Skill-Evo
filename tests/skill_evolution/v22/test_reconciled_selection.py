"""Synthetic offline reconciliation/evaluation tests; no live API or environment."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from src.adapters.alfworld.skill_runtime import build_skill_messages, load_skill, make_record, write_record
from src.adapters.alfworld.verify_skill_run import verify_record
from src.skill_evolution.v22 import reconciled_selection as target
from tests.skill_evolution.v22.test_compact_update import editor, payload
from tests.skill_evolution.v22.test_consume_fixed_plan import read


class ReconciledSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.source = self.directory / "source"
        for name in ("outputs", "inputs", "raw_outputs"):
            (self.source / name).mkdir(parents=True)
        self.plan = {"actor_model": "fixture-model", "max_steps_per_episode": 1, "actor_workers": 1,
                     "selection_task_ids": ["val:0001", "val:0002"]}
        write_record(self.source / "plan.json", self.plan)
        write_record(self.source / "report.json", {"status": "frozen", "selection": [],
            "branches": {"direct": {"status": "candidate"}, "conditioned": {"status": "error"}}})
        for arm in target.trial.ARMS:
            value = editor()
            if arm == "conditioned":
                value["candidate_text"] = ("1. Use an exact current admissible action.\n"
                    "6. Preserve the first obligation.\n7. Continue the second obligation.")
                value["mappings"][1]["excerpt"] = "Preserve the first obligation. Continue the second obligation."
            write_record(self.source / "outputs" / f"{arm}_proposal.json", {"decision": "ready"})
            write_record(self.source / "inputs" / f"{arm}_editor.json", payload())
            write_record(self.source / "raw_outputs" / f"{arm}_editor.json", value)
        self.config = {"schema_version": "v22.reconciled_selection.v1", "semantic_calls": 0,
                       "episode_retries": 0, "source_run": str(self.source),
                       "selection_task_ids": self.plan["selection_task_ids"], "environment_episodes_max": 6}
        self.config_path = self.directory / "config.json"
        write_record(self.config_path, self.config)
        # The source verifier is already tested by the original trial integration
        # tests. Here its synthetic frozen contract isolates the new recovery path.
        patcher = mock.patch.object(target.trial, "verify", return_value={"status": "frozen", "cost": {
            "semantic_calls": 5, "environment_requests": 2, "fixture": True}})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.game, self.items = self.directory / "game.tw-pddl", self.directory / "items.json"
        self.game.write_text("Synthetic bytes; never executed.")
        write_record(self.items, [{"id": key, "gamefile": "fixture", "task_type": "synthetic"}
                                 for key in self.plan["selection_task_ids"]])

    def prepare(self, name="operation"):
        root = self.directory / name
        result = target.prepare(self.config_path, root)
        self.assertEqual(result["status"], "frozen")
        return root

    def batch(self, jobs, output_root, plan, env_file):
        rows = []
        for job in jobs:
            skill = load_skill(job["skill_path"])
            item = {"id": job["task_id"], "gamefile": "fixture", "task_type": "synthetic"}
            record = make_record(item=item, split=job["split"], purpose=job["purpose"], skill=skill,
                                 model=plan["actor_model"], max_steps=plan["max_steps_per_episode"],
                                 gamefile=self.game, manifest_path=self.items,
                                 versions={"alfworld": "synthetic"}, backend_id="synthetic")
            observation = "Your task is to: inspect the room."
            record.update(initial_observation=observation, initial_admissible_commands=["look"],
                          status="success", won=True, finished_at=target.timestamp())
            record["steps"] = [{"step": 1, "phase": "executed", "messages": build_skill_messages(
                observation, ["look"], "inspect the room.", [], skill), "admissible_commands": ["look"],
                "model_response": {"content": "<action>look</action>", "response_model": plan["actor_model"],
                                   "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}},
                "action": "look", "fallback": None, "action_in_admissible_commands": True,
                "observation": "Synthetic completion.", "reward": 1, "done": True, "won": True}]
            path = output_root / job["key"] / "skill_fixture/trajectory.json"
            path.parent.mkdir(parents=True)
            write_record(path, record)
            rows.append({**job, "trajectory": str(path), "status": "success", "audit": verify_record(record),
                         "steps": 1, "executed": True, "success": True, "invalid_action_count": 0})
        return rows

    def evaluate(self, root):
        with mock.patch.object(target, "execute_batch", side_effect=self.batch) as execute:
            result = target.evaluate(root, "unused.env")
        self.assertEqual(execute.call_count, 1)
        return result

    def test_prepare_preserves_raw_source_candidate_bytes_and_all_nonmapping_fields(self):
        original = {p: p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        root = self.prepare()
        self.assertEqual(original, {p: p.read_bytes() for p in original})
        self.assertEqual(read(root / "alignment.json")["conditioned"]["source_status"], "error")
        for arm in target.trial.ARMS:
            raw = read(self.source / "raw_outputs" / f"{arm}_editor.json")
            normalized = read(root / "candidates" / arm / "editor_normalized.json")
            self.assertEqual((root / "candidates" / arm / "SKILL.md").read_text(), raw["candidate_text"])
            self.assertEqual({k: v for k, v in raw.items() if k != "mappings"},
                             {k: v for k, v in normalized.items() if k != "mappings"})
        self.assertEqual(len(read(root / "candidates/conditioned/editor_normalized.json")["mappings"]), 3)
        self.assertFalse((root / "calls").exists())
        self.assertEqual(target.verify(root)["semantic_calls"], 0)
        self.assertEqual(target.verify(root)["selection_episodes"], 0)

    def test_evaluation_runs_declared_selection_once_and_leaves_source_frozen(self):
        root = self.prepare()
        original = {p: p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        result = self.evaluate(root)
        self.assertEqual(result["status"], "evaluated")
        self.assertEqual(result["semantic_calls"], 0)
        self.assertEqual(result["selection_episodes"], 6)
        self.assertEqual(result["cost"]["environment_requests"], 6)
        self.assertEqual(result["cost"]["semantic_calls"], 0)
        jobs = read(root / "schedule.json")
        self.assertTrue(all((j["split"], j["purpose"]) == ("val", "selection") for j in jobs))
        self.assertEqual({j["task_id"] for j in jobs}, set(self.plan["selection_task_ids"]))
        self.assertEqual(original, {p: p.read_bytes() for p in original})
        with mock.patch.object(target, "execute_batch") as execute:
            with self.assertRaisesRegex(ValueError, "single-use"):
                target.evaluate(root, "unused.env")
        execute.assert_not_called()

    def test_tampering_and_updater_directory_are_rejected_without_execution(self):
        root = self.prepare()
        paths = [root / "candidates/conditioned/SKILL.md", root / "execution_plan.json",
                 root / "freeze.json", self.source / "raw_outputs/conditioned_editor.json"]
        with mock.patch.object(target, "execute_batch") as execute:
            for path in paths:
                before = path.read_bytes()
                try:
                    path.write_bytes(before + b"\n")
                    with self.assertRaises(ValueError):
                        target.evaluate(root, "unused.env")
                finally:
                    path.write_bytes(before)
        execute.assert_not_called()
        (root / "calls").mkdir()
        with self.assertRaisesRegex(ValueError, "cannot call an updater"):
            target.verify(root)

    def test_rejects_expanded_budget_changed_selection_and_already_evaluated_source(self):
        for field, value in (("semantic_calls", 1), ("episode_retries", 1),
                             ("environment_episodes_max", 7), ("selection_task_ids", ["val:0003"])):
            config = deepcopy(self.config)
            config[field] = value
            write_record(self.config_path, config)
            with self.subTest(field=field), self.assertRaises(ValueError):
                target.prepare(self.config_path, self.directory / ("bad_" + field))
        write_record(self.config_path, self.config)
        write_record(self.source / "selection_schedule.json", [])
        with self.assertRaisesRegex(ValueError, "pre-evaluation"):
            target.prepare(self.config_path, self.directory / "already_evaluated")

    def test_nonformatting_mapping_changes_cannot_be_reconciled(self):
        path = self.source / "raw_outputs/conditioned_editor.json"
        raw = read(path)
        raw["mappings"][1]["excerpt"] = raw["mappings"][1]["excerpt"].replace("Preserve", "Discard")
        write_record(path, raw)
        with self.assertRaisesRegex(ValueError, "more than numbered-list formatting"):
            target.prepare(self.config_path, self.directory / "not_formatting")

    def test_evaluated_operation_requires_a_row_for_every_declared_job(self):
        root = self.prepare()
        with mock.patch.object(target, "execute_batch", return_value=[]):
            with self.assertRaises(ValueError):
                target.evaluate(root, "unused.env")

    def test_summary_fields_must_match_actual_trajectory_and_declared_job(self):
        root = self.prepare()
        self.evaluate(root)
        original = read(root / "report.json")
        for field, value in (("success", False), ("steps", 99), ("invalid_action_count", 99),
                             ("task_id", "val:0999"), ("arm", "invented")):
            report = deepcopy(original)
            report["selection"][0][field] = value
            write_record(root / "report.json", report)
            # Regenerating a matching summary must not conceal cached-field drift.
            write_record(root / "evaluation_summary.json", target.summarize_selection(report["selection"]))
            with self.subTest(field=field), self.assertRaises(ValueError):
                target.verify(root)
        write_record(root / "report.json", original)


if __name__ == "__main__":
    unittest.main()
