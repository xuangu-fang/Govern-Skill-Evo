"""Offline replay the Step 14 composite oracle on the saved 36 trajectories."""

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
from ..compliance.oracle import classify_behavior_state
from .composition_report import analyze_composition, render_report

ensure_tau2_importable()

from tau2.data_model.message import Message  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "calibration/outputs_composition_baggage_confirmation"
BUNDLES_PATH = ROOT / "compiler/examples/composition_baggage_confirmation_tasks.yaml"
RECORDS_PATH = OUTPUT_DIR / "rollout_records.jsonl"


def _hash_trajectory(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def replay_saved_composition() -> dict[str, Any]:
    records = [json.loads(line) for line in RECORDS_PATH.read_text().splitlines() if line.strip()]
    if len(records) != 36:
        raise ValueError(f"Expected 36 saved trajectories, got {len(records)}")
    bundles = {
        item["task"]["id"]: CompiledTaskBundle.from_dict(item)
        for item in yaml.safe_load(BUNDLES_PATH.read_text())["compiled_bundles"]
    }
    adapter = TypeAdapter(list[Message])
    changed: list[dict[str, Any]] = []
    for record in records:
        original_hash = _hash_trajectory(record["trajectory"])
        result = evaluate_composed_compliance(
            bundles[record["task_id"]], adapter.validate_python(record["trajectory"])
        )
        baggage, confirmation = result.component_results
        old = {
            "baggage_compliance": record["baggage_compliance"],
            "confirmation_compliance": record["confirmation_compliance"],
            "joint_compliance": record["joint_compliance"],
            "violation_pattern": record["violation_pattern"],
            "behavior_state": record["behavior_state"],
        }
        record.setdefault("initial_composite_oracle_result", old)
        record.update(
            baggage_compliance=baggage.compliant,
            confirmation_compliance=confirmation.compliant,
            joint_compliance=result.joint_compliant,
            target_compliance=result.joint_compliant,
            behavior_state=classify_behavior_state(record["task_success"], result.joint_compliant),
            violation_pattern=result.violation_pattern,
            component_results=[item.to_dict() for item in result.component_results],
            composite_compliance_result=result.to_dict(),
            trajectory_sha256=original_hash,
            oracle_replayed_offline=True,
        )
        if _hash_trajectory(record["trajectory"]) != original_hash:
            raise AssertionError("Offline oracle replay changed trajectory content")
        new = {key: record[key] for key in old}
        if old != new:
            changed.append({"task_id": record["task_id"], "rollout_index": record["rollout_index"], "old": old, "new": new})

    records.sort(key=lambda row: (row["task_id"], row["rollout_index"]))
    RECORDS_PATH.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records))
    analysis = analyze_composition(records)
    config = json.loads((OUTPUT_DIR / "world_summary.json").read_text())["run_configuration"]
    atomic = json.loads((OUTPUT_DIR / "atomic_vs_composition.json").read_text())["atomic_reference"]
    common = {"schema_version": 1, "run_configuration": config, "offline_oracle_replay": True}
    payloads = {
        "task_summary.json": {**common, "task_count": 12, "tasks": analysis["tasks"]},
        "world_summary.json": {**common, "world_count": 4, "worlds": analysis["worlds"]},
        "factor_summary.json": {**common, "factors": analysis["factors"]},
        "violation_pattern_summary.json": {**common, "overall": analysis["overall"], "violation_patterns": analysis["violation_patterns"]},
        "replication_summary.json": {**common, **analysis["replication"]},
        "atomic_vs_composition.json": {**common, "atomic_reference": atomic, "composition": analysis},
    }
    for name, payload in payloads.items():
        (OUTPUT_DIR / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (OUTPUT_DIR / "calibration_report.md").write_text(render_report(analysis, config, atomic))
    replay_path = OUTPUT_DIR / "oracle_replay_36.json"
    prior_replay = json.loads(replay_path.read_text()) if replay_path.exists() else {}
    historical_changes = prior_replay.get("oracle_changes", [])
    reported_changes = changed or historical_changes
    replay = {
        "schema_version": 1,
        "saved_trajectories_replayed": 36,
        "new_rollouts_executed": 0,
        "trajectory_hashes_unchanged": True,
        "oracle_changes": reported_changes,
        "changed_count": len(reported_changes),
        "latest_replay_changes": changed,
        "all_current_labels_match": not changed,
        "overall_after_replay": analysis["overall"],
    }
    replay_path.write_text(json.dumps(replay, ensure_ascii=False, indent=2) + "\n")
    return replay


if __name__ == "__main__":
    print(json.dumps(replay_saved_composition(), ensure_ascii=False, indent=2))
