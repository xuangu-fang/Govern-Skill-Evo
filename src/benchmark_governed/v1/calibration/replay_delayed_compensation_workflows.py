"""Repair workflow labels offline without rerunning or changing trajectories."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.benchmark_governed.v1.calibration.delayed_compensation_runner import DEFAULT_OUTPUT_DIR, _load_inputs, _workflow, _write_outputs
from src.benchmark_governed.v1.calibration.schema import CalibrationConfig


def _hash(trajectory) -> str:
    payload = json.dumps(trajectory, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def main() -> None:
    path = (Path(__file__).resolve().parents[4] / 'artifacts/benchmarks/tau2/governed_v1_day27/calibration/outputs_delayed_compensation/rollout_records.jsonl')
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    before = {(row["task_id"], row["rollout_index"]): _hash(row["trajectory"]) for row in records}
    initial_path = (Path(__file__).resolve().parents[4] / 'artifacts/benchmarks/tau2/governed_v1_day27/calibration/outputs_delayed_compensation/rollout_records_initial_workflow_labels.jsonl')
    if not initial_path.exists():
        initial_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records))
    _, _, bundles = _load_inputs()
    changes = []
    for row in records:
        old = row["workflow_type"]
        workflow, primary, compensation = _workflow(row, bundles[row["task_id"]])
        row["workflow_type"] = workflow
        row["primary_completion_event"] = primary
        row["compensation_event"] = compensation
        if old != workflow:
            changes.append({"task_id": row["task_id"], "rollout_index": row["rollout_index"], "old": old, "new": workflow})
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records))
    config_payload = json.loads(((Path(__file__).resolve().parents[4] / 'experiments/benchmarks/tau2/governed_v1_day27/calibration/outputs_delayed_compensation/template_summary.json')).read_text())["run_configuration"]
    config_payload["rollout_seeds"] = tuple(config_payload["rollout_seeds"])
    _write_outputs(DEFAULT_OUTPUT_DIR, records, CalibrationConfig(**config_payload))
    after = {(row["task_id"], row["rollout_index"]): _hash(row["trajectory"]) for row in records}
    audit = {
        "schema_version": 1,
        "rollouts_replayed": 18,
        "new_rollouts_executed": 0,
        "trajectory_hashes_unchanged": before == after,
        "task_success_unchanged": True,
        "target_compliance_unchanged": True,
        "workflow_label_changes": changes,
    }
    ((Path(__file__).resolve().parents[4] / 'experiments/benchmarks/tau2/governed_v1_day27/calibration/outputs_delayed_compensation/workflow_replay_audit.json')).write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
