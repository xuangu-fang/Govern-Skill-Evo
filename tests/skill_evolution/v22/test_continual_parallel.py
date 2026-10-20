"""Parallel Actor scheduling tests; all callbacks and outcomes are synthetic."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Lock, get_ident
import time
import unittest
from unittest.mock import patch

from src.adapters.alfworld.skill_runtime import write_record
from src.skill_evolution.v22.continual_runner import DEFAULT_PLAN, run_campaign
from src.skill_evolution.v22.continual_runtime import actor_workers, load_bundle
from src.skill_evolution.v22.continual_verify import verify_campaign
from tests.skill_evolution.v22.test_continual_runner import PLAN, SyntheticCampaign


class ParallelCampaign(SyntheticCampaign):
    def __init__(self, root, bundle, fail=None):
        super().__init__(root, bundle)
        self.lock, self.barriers = Lock(), {}
        self.active, self.maximum = 0, 0
        self.finished, self.fail = [], fail
        self.main_thread = get_ident()

    def execute(self, task_item, skill_file, output_root):
        round_id = self.round_name(output_root)
        side = "parent" if "parent_runs" in Path(output_root).parts else "candidate"
        ids = self.bundle["plan"]["data"][f"round{round_id[1:]}_task_ids"]
        index = ids.index(task_item["id"])
        with self.lock:
            self.active += 1
            self.maximum = max(self.maximum, self.active)
            barrier = self.barriers.setdefault((round_id, side), Barrier(8))
        try:
            if index < 8:
                barrier.wait(timeout=15)
            failure_slot = self.fail and round_id == "r1" and side == "parent" and index == 0
            # Different completion order must not change the source/task order.
            time.sleep(0 if failure_slot else (0.35 if self.fail else (8 - index % 8) * 0.01))
            with self.lock:
                output = super().execute(task_item, skill_file, output_root)
            if failure_slot:
                if self.fail == "exception":
                    raise RuntimeError("Synthetic callback failure after saving a paid trajectory")
                record = json.loads(output.read_text())
                record.update(status="error", won=False, steps=[])
                write_record(output, record)
            return output
        finally:
            with self.lock:
                self.finished.append((round_id, side, task_item["id"]))
                self.active -= 1

    def generate(self, stage, messages, output_path):
        assert get_ident() == self.main_thread
        assert self.active == 0, "Semantic stages must wait for complete batches"
        return super().generate(stage, messages, output_path)


class ContinualParallelTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bundle = load_bundle(PLAN.with_name("plan_parallel8.json"))

    def run_case(self, name, fail=None):
        callbacks = ParallelCampaign(self.root, self.bundle, fail)
        output = self.root / name
        report = run_campaign(self.bundle, output, callbacks.generate, callbacks.execute, offline=True)
        return output, callbacks, report

    def test_future_default_is_eight_and_v2_remains_serial(self):
        self.assertEqual(DEFAULT_PLAN.name, "plan_parallel8.json")
        self.assertEqual(actor_workers(self.bundle["plan"]), 8)
        self.assertEqual(actor_workers(load_bundle(PLAN)["plan"]), 1)
        invalid = deepcopy(self.bundle["plan"])
        invalid["scheduling"]["actor_workers"] = 9
        with self.assertRaisesRegex(ValueError, "scheduling"):
            actor_workers(invalid)

    def test_full_two_rounds_overlap_eight_preserve_order_and_wait_before_semantics(self):
        output, callbacks, report = self.run_case("complete")
        self.assertEqual(report["status"], "completed", report)
        self.assertEqual(callbacks.maximum, 8)
        self.assertEqual(len(callbacks.finished), 40)
        self.assertEqual(len(callbacks.calls), 9)
        self.assertEqual(report["actor_schedule"], "bounded_parallel_eight_workers")
        for number in (1, 2):
            for side in ("parent", "candidate"):
                sources = json.loads((output / f"rounds/r{number}/{side}_sources.json").read_text())
                ids = self.bundle["plan"]["data"][f"round{number}_task_ids"]
                self.assertEqual([row["task_id"] for row in sources], ids)
                self.assertTrue(all(row["settled_at"] for row in sources))
        self.assertTrue(verify_campaign(output)["campaign_complete"])

    def test_failure_stops_replacement_drains_every_dispatched_slot_and_keeps_cost(self):
        for fail in ("partial", "exception"):
            with self.subTest(fail=fail):
                output, callbacks, report = self.run_case(fail, fail)
                self.assertEqual(report["status"], "error", report)
                self.assertEqual(callbacks.maximum, 8)
                self.assertEqual(len(callbacks.finished), 8)
                self.assertEqual(callbacks.calls, [])
                self.assertEqual(report["cost"]["episodes_dispatched"], 8)
                self.assertEqual(report["cost"]["episodes_without_readable_trace"], 0)
                self.assertEqual(report["cost"]["environment_requests"], 7 if fail == "partial" else 8)
                sources = json.loads((output / "rounds/r1/parent_sources.json").read_text())
                self.assertEqual(len(sources), 8)
                self.assertTrue(all(row["settled_at"] for row in sources))
                self.assertEqual(sum(bool(row.get("validation_error")) for row in sources), 1)
                self.assertFalse((output / "rounds/r1/gate.json").exists())
                self.assertTrue(verify_campaign(output)["artifact_valid"])

    def test_interruption_drains_started_slots_without_new_dispatch_or_publication(self):
        with patch("src.skill_evolution.v22.continual_runner.wait", side_effect=KeyboardInterrupt):
            output, callbacks, report = self.run_case("interrupt")
        self.assertEqual(report["status"], "interrupted", report)
        self.assertEqual(len(callbacks.finished), 8)
        self.assertEqual(report["cost"]["episodes_dispatched"], 8)
        self.assertEqual(report["cost"]["environment_requests"], 8)
        self.assertEqual(report["published_rounds"], 0)
        self.assertEqual(callbacks.calls, [])
        self.assertTrue(verify_campaign(output)["artifact_valid"])


if __name__ == "__main__":
    unittest.main()
