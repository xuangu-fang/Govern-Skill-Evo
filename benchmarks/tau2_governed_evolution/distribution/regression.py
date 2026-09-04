"""Offline compliance regression for all 144 saved calibration trajectories."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import TypeAdapter

from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle
from ..compliance.composite import evaluate_composed_compliance
from ..compliance.oracle import evaluate_target_compliance

ensure_tau2_importable()

from tau2.data_model.message import Message  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(__file__).resolve().parent / "final_v1/evaluator_regression_144.json"
ATOMIC_DATASETS = (
    (
        ROOT / "calibration/recalibration/rollout_records_rescored.jsonl",
        (
            ROOT / "compiler/examples/checked_baggage_tasks.yaml",
            ROOT / "compiler/examples/flight_change_cabin_tasks.yaml",
            ROOT / "compiler/examples/itinerary_identity_tasks.yaml",
        ),
    ),
    (
        ROOT / "calibration/outputs_explicit_confirmation/rollout_records.jsonl",
        (ROOT / "compiler/examples/explicit_confirmation_tasks.yaml",),
    ),
    (
        ROOT / "calibration/outputs_cancellation_reason/rollout_records.jsonl",
        (ROOT / "compiler/examples/cancellation_reason_tasks.yaml",),
    ),
    (
        ROOT / "calibration/outputs_delayed_compensation/rollout_records.jsonl",
        (ROOT / "compiler/examples/delayed_flight_compensation_tasks.yaml",),
    ),
)
COMPOSITION_DATASET = (
    ROOT / "calibration/outputs_composition_baggage_confirmation/rollout_records.jsonl",
    ROOT / "compiler/examples/composition_baggage_confirmation_tasks.yaml",
)


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _bundles(paths: tuple[Path, ...]) -> dict[str, CompiledTaskBundle]:
    result = {}
    for path in paths:
        for value in yaml.safe_load(path.read_text())["compiled_bundles"]:
            bundle = CompiledTaskBundle.from_dict(value)
            result[bundle.task.id] = bundle
    return result


def replay_all_calibration_compliance() -> dict[str, Any]:
    adapter = TypeAdapter(list[Message])
    changed = []
    checked = 0
    hashes_unchanged = True
    for records_path, bundle_paths in ATOMIC_DATASETS:
        bundles = _bundles(bundle_paths)
        for line in records_path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            before = _hash(record["trajectory"])
            result = evaluate_target_compliance(
                bundles[record["task_id"]], adapter.validate_python(record["trajectory"])
            )
            hashes_unchanged &= before == _hash(record["trajectory"])
            if result.compliant != record["target_compliance"]:
                changed.append({
                    "task_id": record["task_id"],
                    "rollout_index": record["rollout_index"],
                    "old": record["target_compliance"],
                    "new": result.compliant,
                })
            checked += 1

    records_path, bundles_path = COMPOSITION_DATASET
    bundles = _bundles((bundles_path,))
    for line in records_path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        before = _hash(record["trajectory"])
        result = evaluate_composed_compliance(
            bundles[record["task_id"]], adapter.validate_python(record["trajectory"])
        )
        hashes_unchanged &= before == _hash(record["trajectory"])
        old = {
            "baggage": record["baggage_compliance"],
            "confirmation": record["confirmation_compliance"],
            "joint": record["joint_compliance"],
            "pattern": record["violation_pattern"],
        }
        new = {
            "baggage": result.component_results[0].compliant,
            "confirmation": result.component_results[1].compliant,
            "joint": result.joint_compliant,
            "pattern": result.violation_pattern,
        }
        if old != new:
            changed.append({
                "task_id": record["task_id"],
                "rollout_index": record["rollout_index"],
                "old": old,
                "new": new,
            })
        checked += 1

    audit = {
        "schema_version": 1,
        "saved_trajectories_replayed": checked,
        "new_rollouts_executed": 0,
        "trajectory_hashes_unchanged": hashes_unchanged,
        "compliance_labels_unchanged": not changed,
        "changed_records": changed,
        "all_checks_passed": checked == 144 and hashes_unchanged and not changed,
    }
    if not audit["all_checks_passed"]:
        raise AssertionError(audit)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    return audit


if __name__ == "__main__":
    print(json.dumps(replay_all_calibration_compliance(), ensure_ascii=False, indent=2))

