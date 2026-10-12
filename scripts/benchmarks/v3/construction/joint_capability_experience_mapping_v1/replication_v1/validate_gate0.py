#!/usr/bin/env python3
"""Static Gate 0 for fresh data, axis separation, and executable semantics."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.replication_v1.evaluator import evaluate
from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.replication_v1.fixture import build_replication_db
from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.tools import FareClassResourceTools


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/joint_capability_experience_mapping_v1/replication_v1')
FAMILY = HERE.parent
REPO = HERE.parents[5]
OUTPUT = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/gate0_validation.json')


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    specs = load(HERE / "specs.json")["candidates"]
    tasks = load(HERE / "tasks.json")
    config = load((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/config.json'))
    errors: list[str] = []
    if len(specs) != 8 or len(tasks) != 8:
        errors.append("exactly eight fresh variants are required")
    if {row["input_label"] for row in specs} != {row["id"] for row in tasks}:
        errors.append("task/spec membership mismatch")
    if config["seeds"] != [11701] or config["planned_trajectories"] != 32:
        errors.append("one-seed 32-trajectory design drift")
    for split in ("train", "monitor"):
        rows = [row for row in specs if row["split"] == split]
        if len(rows) != 4:
            errors.append(f"{split} must contain four variants")
        signatures = {(row["trips"][0]["cabin"], row["trips"][0]["price"] > row["trips"][1]["price"]) for row in rows}
        if signatures != {("basic_economy", True), ("basic_economy", False), ("economy", True), ("economy", False)}:
            errors.append(f"{split} does not counterbalance request order and price relation")
    old_specs = load(FAMILY / "joint_gate/specs.json")["candidates"] + load(FAMILY / "specs.json")["candidates"]
    old_values = {
        value
        for row in old_specs
        for value in ([row["user_id"], row.get("cancel_reservation_id", "")] + [trip["flight_number"] for trip in row["trips"]])
        if value
    }
    new_values = {
        value
        for row in specs
        for value in ([row["user_id"], row["cancel_reservation_id"]] + [trip["flight_number"] for trip in row["trips"]])
    }
    if old_values & new_values:
        errors.append("calibration or small-Gate entities were reused")
    for row in specs:
        prices = [trip["price"] for trip in row["trips"]]
        if min(row["certificate_amount"], row["gift_card_amount"]) < max(prices):
            errors.append(f"visible amount shortcut remains in {row['input_label']}")
        if max(row["certificate_amount"], row["gift_card_amount"]) >= sum(prices):
            errors.append(f"one resource can cover both fares in {row['input_label']}")
        if {trip["cabin"] for trip in row["trips"]} != {"basic_economy", "economy"}:
            errors.append(f"fare-class pair invalid in {row['input_label']}")
    cap = ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/capability.md')).read_text(encoding="utf-8").lower()
    gov = ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/governance.md')).read_text(encoding="utf-8").lower()
    joint = ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/joint.md')).read_bytes()
    if any(token in cap for token in ("insurance", "cancellation", "transfer_to_human", "health and weather")):
        errors.append("Capability Skill contains Governance semantics")
    if any(token in gov for token in ("certificate", "gift-card", "gift card", "fare class")):
        errors.append("Governance Skill contains Capability semantics")
    if joint != ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/capability.md')).read_bytes() + b"\n" + ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/skills/governance.md')).read_bytes():
        errors.append("Joint Skill is not exact component composition")
    db = build_replication_db()
    first = specs[0]
    toolkit = FareClassResourceTools(db)
    if first["user_id"] not in toolkit.db.users or first["cancel_reservation_id"] not in toolkit.db.reservations:
        errors.append("fixture did not materialize replication entities")
    if evaluate is None:
        errors.append("evaluator import failed")
    result = {
        "status": "PASS_JOINT_FAMILY_REPLICATION_V1_GATE_0" if not errors else "FAIL_JOINT_FAMILY_REPLICATION_V1_GATE_0",
        "errors": errors,
        "task_count": len(tasks), "split_counts": {name: sum(row["split"] == name for row in specs) for name in ("train", "monitor")},
        "planned_trajectories": config["planned_trajectories"],
        "skill_sha256": {name: sha(HERE / f"skills/{name}.md") for name in ("capability", "governance", "joint")},
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
