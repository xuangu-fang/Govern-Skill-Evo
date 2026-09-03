"""Offline replay of the deterministic cancellation-reason oracle."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from ..compiler.resolvers import ensure_tau2_importable
from ..compliance.oracle import classify_behavior_state, evaluate_target_compliance
from .cancellation_reason_report import render_five_pilot_portfolio
from .cancellation_reason_runner import BENCHMARK_ROOT, DEFAULT_OUTPUT_DIR, _load_config, _load_inputs, _write_outputs

ensure_tau2_importable()

from tau2.data_model.message import Message  # noqa: E402


def _trajectory_hash(trajectory: Any) -> str:
    encoded = json.dumps(trajectory, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def replay_saved_cancellation_reason_oracle(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    records_path = output_dir / "rollout_records.jsonl"
    records = [json.loads(line) for line in records_path.read_text().splitlines() if line.strip()]
    if len(records) != 18:
        raise ValueError("Oracle replay requires exactly 18 saved trajectories")
    _, _, bundles = _load_inputs()
    _, config = _load_config(6)
    adapter = TypeAdapter(Message)
    initial_path = output_dir / "rollout_records_initial_oracle.jsonl"
    if not initial_path.exists():
        initial_path.write_text(records_path.read_text())
    initial = [json.loads(line) for line in initial_path.read_text().splitlines() if line.strip()]
    initial_by_key = {(row["task_id"], row["rollout_index"]): row for row in initial}
    before_hashes = [_trajectory_hash(row["trajectory"]) for row in records]
    old_states = Counter(row["behavior_state"] for row in initial)
    changed = []
    for record in records:
        messages = [adapter.validate_python(item) for item in record["trajectory"]]
        result = evaluate_target_compliance(bundles[record["task_id"]], messages)
        old = initial_by_key[(record["task_id"], record["rollout_index"])]
        record["target_compliance"] = result.compliant
        record["behavior_state"] = classify_behavior_state(bool(record["task_success"]), result.compliant)
        record["compliance_result"] = result.to_dict()
        record["violation_evidence"] = result.violation_evidence
        record["cancellation_reason_event"] = [item for item in result.checked_events if item.get("event_type") == "cancellation_reason_event"]
        record["commit_event"] = [item for item in result.checked_events if item.get("event_type") == "tool_call" and item.get("tool_name") == "cancel_reservation"]
        if old["target_compliance"] != result.compliant or old["behavior_state"] != record["behavior_state"]:
            changed.append({"task_id": record["task_id"], "rollout_index": record["rollout_index"], "old_compliant": old["target_compliance"], "new_compliant": result.compliant, "old_behavior_state": old["behavior_state"], "new_behavior_state": record["behavior_state"]})
    after_hashes = [_trajectory_hash(row["trajectory"]) for row in records]
    if before_hashes != after_hashes:
        raise AssertionError("Trajectory content changed during oracle replay")
    records.sort(key=lambda row: (row["task_id"], row["rollout_index"]))
    records_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records))
    _write_outputs(output_dir, records, config)
    step10_path = BENCHMARK_ROOT / "calibration/recalibration/rollout_records_rescored.jsonl"
    confirmation_path = BENCHMARK_ROOT / "calibration/outputs_explicit_confirmation/rollout_records.jsonl"
    step10 = [json.loads(line) for line in step10_path.read_text().splitlines() if line.strip()]
    confirmation = [json.loads(line) for line in confirmation_path.read_text().splitlines() if line.strip()]
    (BENCHMARK_ROOT / "calibration/portfolio_summary.md").write_text(render_five_pilot_portfolio(step10, confirmation, records))
    audit = {
        "schema_version": 1,
        "rollouts_replayed": 18,
        "new_rollouts_executed": 0,
        "trajectory_hashes_unchanged": before_hashes == after_hashes,
        "task_success_unchanged": True,
        "old_behavior_states": dict(old_states),
        "new_behavior_states": dict(Counter(row["behavior_state"] for row in records)),
        "changed_oracle_records": changed,
    }
    (output_dir / "oracle_replay_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    return audit


if __name__ == "__main__":
    print(json.dumps(replay_saved_cancellation_reason_oracle(), indent=2))
