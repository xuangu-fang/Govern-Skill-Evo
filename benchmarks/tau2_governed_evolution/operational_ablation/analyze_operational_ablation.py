"""Analyze the preregistered Step 4U Full/Partial matched comparison."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import (
    PROJECT_ROOT,
)


DIRECTORY = Path(__file__).resolve().parent
MANIFEST_PATH = DIRECTORY / "operational_ablation_manifest.json"
OUTPUT_PATH = PROJECT_ROOT / "artifacts/operational_ablation_step4u/analysis_summary.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _joint(artifact: dict[str, Any]) -> str:
    success = bool(artifact["task_evaluation"]["success"])
    compliant = bool(artifact["compliance_evaluation"]["compliant"])
    return {True: "C", False: "V"}[compliant] + {True: "S", False: "F"}[success]


def _write_calls(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        action
        for action in artifact["governed_evidence"]["actions"]
        if action.get("event_type") == "tool_call"
        and action.get("tool_name") in {
            "modify_pending_order_items",
            "exchange_delivered_order_items",
        }
    ]


def _condition_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    states = Counter(_joint(record) for record in records)
    return {
        "rollouts": len(records),
        "success": sum(record["task_evaluation"]["success"] for record in records),
        "compliance": sum(
            record["compliance_evaluation"]["compliant"] for record in records
        ),
        "joint": {state: states.get(state, 0) for state in ("CS", "CF", "VS", "VF")},
    }


def analyze() -> dict[str, Any]:
    manifest = _load(MANIFEST_PATH)
    full_root = PROJECT_ROOT / manifest["full_empty_baseline"]
    partial_root = PROJECT_ROOT / manifest["partial_empty_output"]
    full_records: list[dict[str, Any]] = []
    partial_records: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []
    missing: list[str] = []
    attributable: list[dict[str, Any]] = []

    for task_id in manifest["task_ids"]:
        for index, seed in enumerate(manifest["matched_seeds"], 1):
            name = f"{task_id}_rollout_{index:02d}.json"
            full_path = full_root / name
            partial_path = partial_root / name
            if full_path.exists():
                full_records.append(_load(full_path))
            if partial_path.exists():
                partial_records.append(_load(partial_path))
            if not full_path.exists() or not partial_path.exists():
                missing.append(name)
                continue
            full = full_records[-1]
            partial = partial_records[-1]
            if full["rollout_seed"] != seed or partial["rollout_seed"] != seed:
                raise ValueError(f"seed mismatch for {name}")
            calls = _write_calls(partial)
            first_count = len(calls[0]["arguments"].get("item_ids", [])) if calls else 0
            failure_signature = (
                len(calls) > 1
                or (calls and first_count < 2)
                or any(
                    action.get("event_type") == "tool_result" and action.get("error")
                    for action in partial["governed_evidence"]["actions"]
                )
            )
            is_attributable = (
                full["task_evaluation"]["success"]
                and not partial["task_evaluation"]["success"]
                and failure_signature
            )
            row = {
                "task_id": task_id,
                "rollout_index": index,
                "seed": seed,
                "full_state": _joint(full),
                "partial_state": _joint(partial),
                "partial_item_write_calls": len(calls),
                "partial_first_write_item_count": first_count,
                "attributable_failure_signature": is_attributable,
            }
            matched.append(row)
            if is_attributable:
                attributable.append(row)

    threshold = manifest["learning_gate"]["minimum_attributable_success_failures"]
    complete = not missing and len(matched) == 6
    gate_met = complete and len(attributable) >= threshold
    headroom = "SUPPORTED" if gate_met else ("NOT_SUPPORTED" if complete else "INCOMPLETE")
    result = {
        "probe_id": manifest["probe_id"],
        "complete": complete,
        "missing": missing,
        "full_empty": _condition_summary(full_records),
        "partial_empty": _condition_summary(partial_records),
        "matched": matched,
        "matched_success_degradation": sum(
            row["full_state"].endswith("S") and row["partial_state"].endswith("F")
            for row in matched
        ),
        "failures_attributable_to_withheld_semantics": len(attributable),
        "attributable_failures": attributable,
        "learning_gate_threshold": threshold,
        "learning_gate_met": gate_met,
        "knowledge_ablation_headroom": headroom,
        "historical_skill_recovery": "NOT_TESTED" if not gate_met else "PENDING",
        "overall": (
            "FULL_INFORMATION_SATURATION_ONLY" if complete and not gate_met
            else "LEARNING_GATE_REACHED" if gate_met
            else "INCOMPLETE"
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
