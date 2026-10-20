"""Bounded archive verification of an explicit scheduling-only continuation."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from src.adapters.alfworld.skill_runtime import digest, write_record
from src.skill_evolution.v22.continual_runtime import load_bundle
from src.skill_evolution.v22.continual_runner import run_campaign
from src.skill_evolution.v22.continual_verify import _schedule, verify_campaign
from tests.skill_evolution.v22.test_continual_runner import PLAN, SyntheticCampaign


def bind_amendment(root, frozen, report):
    directory = root.parent / "scheduling_amendment"
    directory.mkdir()
    source = directory / "continuation.py"
    source.write_text("# Synthetic archived continuation; never executed.\n")
    replay = directory / "remaining_replay.py"
    replay.write_text("# Synthetic archived Replay dispatcher; never executed.\n")
    runtime_sha = digest((root / "runtime_freeze.json").read_bytes())
    amendment = directory / "amendment.json"
    write_record(amendment, {"schema": "v22.user_authorized_schedule_amendment.v1",
        "authorization": "Synthetic fixture representing an explicit scheduling amendment.",
        "original_root": frozen["artifact_root"], "original_runtime_freeze_sha256": runtime_sha,
        "original_protocol": "v22.grouped_continual.v2", "changes": {
            "actor_workers_max": {"before": 3, "after": 8},
            "actual_schedule": {"before": "sequential_one_worker", "after": "parallel_max_8"}},
        "remaining_replay_source_sha256": digest(replay.read_bytes())})
    authority = directory / "continuation_freeze.json"
    write_record(authority, {"schema": "v22.authorized_schedule_continuation.v1",
        "artifact_root": frozen["artifact_root"], "source_sha256": digest(source.read_bytes()),
        "amendment_path": str(amendment), "amendment_sha256": digest(amendment.read_bytes()),
        "original_runtime_freeze_sha256": runtime_sha, "actor_workers_max": 8,
        "method_change": False, "retries_or_repeated_prior_work": False})
    report.update(actor_schedule="serial_then_user_authorized_parallel_8",
        scheduling_amendment={"path": str(amendment), "sha256": digest(amendment.read_bytes())},
        continuation={"path": str(source), "sha256": digest(source.read_bytes()),
                      "authority": str(authority), "authority_sha256": digest(authority.read_bytes())})
    return directory


class ContinualAmendmentTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name).resolve()
        self.root = self.parent / "campaign"
        self.root.mkdir()
        self.plan = load_bundle(PLAN)["plan"]
        self.frozen = {"artifact_root": str(self.root)}
        write_record(self.root / "runtime_freeze.json", self.frozen)
        self.report = {}
        self.amendment = bind_amendment(self.root, self.frozen, self.report)

    def test_bound_amendment_and_same_parent_relocation_are_accepted_and_disclosed(self):
        self.assertTrue(_schedule(self.root, self.plan, self.frozen, self.report)["amended"])
        with TemporaryDirectory() as destination:
            destination = Path(destination).resolve()
            shutil.copytree(self.root, destination / self.root.name)
            shutil.copytree(self.amendment, destination / self.amendment.name)
            result = _schedule(destination / self.root.name, self.plan, self.frozen, self.report)
            self.assertEqual(result["declared_schedule"], "sequential_one_worker")
            self.assertEqual(result["actual_schedule"], "serial_then_user_authorized_parallel_8")
            self.assertEqual(result["actor_workers_max_after_amendment"], 8)

    def test_unamended_or_unknown_schedule_cannot_use_the_amendment_path(self):
        for actual in ("parallel_max_8", "sequential_one_worker", "bounded_parallel_eight_workers"):
            with self.subTest(actual=actual), self.assertRaises(ValueError):
                _schedule(self.root, self.plan, self.frozen, self.report | {"actor_schedule": actual})
        with self.assertRaises(ValueError):
            _schedule(self.root, load_bundle(PLAN.with_name("plan_parallel8.json"))["plan"], self.frozen, self.report)

    def test_hash_campaign_source_and_external_path_mismatches_are_rejected(self):
        source = self.amendment / "continuation.py"
        original = source.read_bytes()
        source.write_bytes(original + b"changed")
        with self.assertRaisesRegex(ValueError, "hash"):
            _schedule(self.root, self.plan, self.frozen, self.report)
        source.write_bytes(original)
        for filename, field, value, message in (
            ("amendment.json", "original_root", "/different/campaign", "campaign/runtime"),
            ("continuation_freeze.json", "method_change", True, "authority"),
            ("continuation_freeze.json", "source_sha256", "wrong", "authority"),
        ):
            with self.subTest(filename=filename, field=field):
                path = self.amendment / filename
                original = path.read_bytes()
                data = json.loads(original)
                data[field] = value
                write_record(path, data)
                report = deepcopy(self.report)
                if filename == "amendment.json":
                    report["scheduling_amendment"]["sha256"] = digest(path.read_bytes())
                else:
                    report["continuation"]["authority_sha256"] = digest(path.read_bytes())
                with self.assertRaisesRegex(ValueError, message):
                    _schedule(self.root, self.plan, self.frozen, report)
                path.write_bytes(original)
        report = deepcopy(self.report)
        report["scheduling_amendment"]["path"] = "/outside/unbound/amendment.json"
        with self.assertRaisesRegex(ValueError, "outside"):
            _schedule(self.root, self.plan, self.frozen, report)
        (self.amendment / "remaining_replay.py").write_text("changed")
        with self.assertRaisesRegex(ValueError, "Replay source"):
            _schedule(self.root, self.plan, self.frozen, self.report)

    def test_completed_lineage_still_verified_after_bound_schedule_amendment(self):
        output = self.parent / "full" / "campaign"
        output.parent.mkdir()
        bundle = load_bundle(PLAN)
        callbacks = SyntheticCampaign(output.parent, bundle)
        report = run_campaign(bundle, output, callbacks.generate, callbacks.execute, offline=True)
        self.assertEqual(report["status"], "completed", report)
        frozen = json.loads((output / "runtime_freeze.json").read_text())
        bind_amendment(output, frozen, report)
        write_record(output / "report.json", report)
        result = verify_campaign(output)
        self.assertTrue(result["artifact_valid"])
        self.assertEqual(result["published_rounds"], 2)
        self.assertTrue(result["scheduling"]["amended"])
        # Scheduling permission cannot excuse tampering in the original method evidence.
        gate = output / "rounds/r1/gate.json"
        gate.write_bytes(gate.read_bytes() + b"\nchanged")
        with self.assertRaisesRegex(ValueError, "Frozen artifact"):
            verify_campaign(output)


if __name__ == "__main__":
    unittest.main()
