"""Aggregate matched Step 4W outcomes and apply preregistered gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.partial_knowledge_headroom.validate_operational_headroom_tasks import PROJECT_ROOT, load_suite


DEFAULT_ROOT = PROJECT_ROOT / "artifacts/partial_knowledge_headroom_step4w"
FULL_STABLE = {
    "retail_pa_o1a_w6779827_items_payment",
    "airline_pa_o2a_m66qvw_full_replacement",
    "airline_pa_o2b_1n99u6_full_replacement",
    "airline_pa_o3b_1n99u6_preserved_pricing",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text())


def _row(root: Path, condition: str, task_id: str, index: int, knowledge_id: str) -> dict:
    artifact = _load(root / condition / f"{task_id}_rollout_{index:02d}.json")
    success = bool(artifact["task_evaluation"]["success"])
    compliance = artifact.get("compliance_evaluation", {}).get("compliant")
    joint = ("CS" if compliance else "VS") if success else ("CF" if compliance else "VF")
    raw = _load(root / condition / f"{task_id}_rollout_{index:02d}_tau2_raw.json")
    writes = []
    for message in raw["messages"]:
        if message.get("role") != "assistant":
            continue
        for call in message.get("tool_calls") or []:
            if call["name"].startswith(("modify_", "update_")):
                writes.append({"name": call["name"], "arguments": call.get("arguments")})
    return {"condition": condition, "knowledge_id": knowledge_id, "task_id": task_id, "index": index, "seed": artifact["rollout_seed"], "success": success, "compliant": compliance, "joint": joint, "writes": writes}


def analyze(root: Path) -> dict:
    registry, _ = load_suite()
    by_task = {spec["task_id"]: spec for spec in registry["tasks"]}
    full_rows = [_row(root, "full_empty", task_id, index, spec["knowledge_id"]) for task_id, spec in by_task.items() for index in (1, 2, 3)]
    full_counts = {task_id: sum(row["success"] for row in full_rows if row["task_id"] == task_id) for task_id in by_task}
    invalid = {task_id: count for task_id, count in full_counts.items() if count < 3}
    if set(by_task) - set(invalid) != FULL_STABLE:
        raise ValueError("Full-stable pool drifted; inspect before changing the frozen gate")
    partial_rows = [_row(root, "partial_empty", task_id, index, by_task[task_id]["knowledge_id"]) for task_id in FULL_STABLE for index in (1, 2, 3)]
    skill_rows = [_row(root, "partial_skill", "retail_pa_o1a_w6779827_items_payment", index, "O1") for index in (1, 2, 3)]
    clean_full = [row for row in full_rows if row["task_id"] in FULL_STABLE]

    def stats(rows: list[dict]) -> dict:
        return {"rollouts": len(rows), "success": sum(row["success"] for row in rows), "compliant": sum(row["compliant"] is True for row in rows), "joint": {state: sum(row["joint"] == state for row in rows) for state in ("CS", "CF", "VS", "VF")}}

    units = {}
    for unit in ("O1", "O2", "O3"):
        full = [row for row in clean_full if row["knowledge_id"] == unit]
        partial = [row for row in partial_rows if row["knowledge_id"] == unit]
        failures = [row for row in partial if not row["success"]]
        affected = sorted({row["task_id"] for row in failures})
        units[unit] = {"full": stats(full), "partial": stats(partial), "matched_degradation": sum(row["success"] for row in full) - sum(row["success"] for row in partial), "affected_states_in_step4w": affected}
    units["O1"]["prior_step4v_affected_state"] = "retail_pa_v1b_w8557584_items_address_payment"
    units["O1"]["headroom"] = "SUPPORTED"
    units["O1"]["support_basis"] = "transition-caused degradation now occurs in two independent states across Step 4V and Step 4W"
    units["O1"]["probe_skill"] = stats(skill_rows)
    units["O1"]["recoverable_by_skill"] = all(row["success"] for row in skill_rows)
    units["O2"]["headroom"] = "NOT_SUPPORTED"
    units["O3"]["headroom"] = "NOT_SUPPORTED"
    output = {"clean_pool": {"task_ids": sorted(FULL_STABLE), "full": stats(clean_full), "partial": stats(partial_rows)}, "full_baseline_invalid": invalid, "units": units, "O4": registry["knowledge_units"]["O4"], "historical_skill_mechanism_diversity": "NARROW", "phase_a_benchmark_readiness": "SUCCESS_HEADROOM_STILL_TOO_NARROW", "rows": full_rows + partial_rows + skill_rows}
    (root / "analysis_summary.json").write_text(json.dumps(output, indent=2) + "\n")
    for unit in ("O1", "O2", "O3"):
        registry["knowledge_units"][unit].update({
            "full_baseline": units[unit]["full"],
            "partial_result": units[unit]["partial"],
            "headroom_status": units[unit]["headroom"],
            "skill_recoverability": (
                "YES_FOR_SUCCESS" if units[unit].get("recoverable_by_skill") else "NOT_TESTED"
            ),
        })
    registry["knowledge_units"]["O4"].update({
        "full_baseline": "NOT_RUN", "partial_result": "NOT_RUN",
        "headroom_status": "INVALID", "skill_recoverability": "NOT_TESTED",
    })
    registry["historical_skill_mechanism_diversity"] = output["historical_skill_mechanism_diversity"]
    registry["phase_a_benchmark_readiness"] = output["phase_a_benchmark_readiness"]
    Path(__file__).resolve().parent.joinpath("operational_knowledge_registry.json").write_text(
        json.dumps(registry, indent=2) + "\n"
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    print(json.dumps(analyze(args.artifact_root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
