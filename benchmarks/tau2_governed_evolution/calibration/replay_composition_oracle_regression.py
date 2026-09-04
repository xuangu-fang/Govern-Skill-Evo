"""Offline regression check for all 108 pre-composition compliance labels."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from pydantic import TypeAdapter

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from ..compliance.oracle import evaluate_target_compliance

ensure_tau2_importable()

from tau2.data_model.message import Message  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "calibration/outputs_composition_baggage_confirmation/oracle_regression_108.json"
DATASETS = (
    (ROOT / "calibration/recalibration/rollout_records_rescored.jsonl", (
        ROOT / "compiler/examples/checked_baggage_tasks.yaml",
        ROOT / "compiler/examples/flight_change_cabin_tasks.yaml",
        ROOT / "compiler/examples/itinerary_identity_tasks.yaml",
    )),
    (ROOT / "calibration/outputs_explicit_confirmation/rollout_records.jsonl", (ROOT / "compiler/examples/explicit_confirmation_tasks.yaml",)),
    (ROOT / "calibration/outputs_cancellation_reason/rollout_records.jsonl", (ROOT / "compiler/examples/cancellation_reason_tasks.yaml",)),
    (ROOT / "calibration/outputs_delayed_compensation/rollout_records.jsonl", (ROOT / "compiler/examples/delayed_flight_compensation_tasks.yaml",)),
)


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def replay_regression() -> dict:
    adapter = TypeAdapter(Message)
    checked = 0
    changed = []
    hashes_unchanged = True
    for records_path, bundle_paths in DATASETS:
        bundles = {}
        for path in bundle_paths:
            for value in yaml.safe_load(path.read_text())["compiled_bundles"]:
                item = CompiledTaskBundle.from_dict(value)
                bundles[item.task.id] = item
        for line in records_path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            before = _hash(record["trajectory"])
            messages = [adapter.validate_python(item) for item in record["trajectory"]]
            result = evaluate_target_compliance(bundles[record["task_id"]], messages)
            after = _hash(record["trajectory"])
            hashes_unchanged = hashes_unchanged and before == after
            if result.compliant != record["target_compliance"]:
                changed.append({
                    "task_id": record["task_id"],
                    "rollout_index": record["rollout_index"],
                    "old": record["target_compliance"],
                    "new": result.compliant,
                })
            checked += 1
    audit = {
        "schema_version": 1,
        "rollouts_replayed": checked,
        "new_rollouts_executed": 0,
        "trajectory_hashes_unchanged": hashes_unchanged,
        "compliance_labels_unchanged": not changed,
        "changed_records": changed,
    }
    if checked != 108 or changed or not hashes_unchanged:
        raise AssertionError(audit)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(audit, indent=2) + "\n")
    return audit


if __name__ == "__main__":
    print(json.dumps(replay_regression(), indent=2))
