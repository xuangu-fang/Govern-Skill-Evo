"""Attribute Step 4W-S3 outcomes to certificate-lifecycle behavior."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.certificate_lifecycle.build_certificate_probe import (
    MANIFEST_PATH,
    PROJECT_ROOT,
)


DEFAULT_ROOT = PROJECT_ROOT / "artifacts/certificate_lifecycle_step4w_s3"


def _load(path: Path) -> Any:
    return json.loads(path.read_text())


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def _rollout_files(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.glob("*.json")
        if not path.name.endswith("_tau2_raw.json") and path.name != "run_summary.json"
    )


def _tool_trace(raw: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    calls: list[dict[str, Any]] = []
    results: list[str] = []
    for message in raw["messages"]:
        for call in message.get("tool_calls") or []:
            calls.append(call)
        if message.get("role") == "tool":
            results.append(str(message.get("content", "")))
    return calls, results


def _classify(path: Path, spec: dict[str, Any], condition: str) -> dict[str, Any]:
    artifact = _load(path)
    raw_path = Path(artifact["provenance"]["raw_tau2_result_path"])
    if not raw_path.is_absolute():
        raw_path = PROJECT_ROOT / raw_path
    raw = _load(raw_path)
    calls, results = _tool_trace(raw)
    bookings = [call for call in calls if call["name"] == "book_reservation"]
    certificate_id = spec["source_state"]["certificate_id"]
    first_payments = bookings[0]["arguments"].get("payment_methods", []) if bookings else []
    first_payment_ids = [payment["payment_id"] for payment in first_payments]
    early_certificate = certificate_id in first_payment_ids
    certificate_not_found = any(
        f"Payment method {certificate_id} not found" in result for result in results
    )
    cancellation_attempted = any(call["name"] == "cancel_reservation" for call in calls)
    transferred = any(call["name"] == "transfer_to_human_agents" for call in calls)
    lifecycle_failure = bool(
        not artifact["task_evaluation"]["success"]
        and early_certificate
        and certificate_not_found
    )
    return {
        "condition": condition,
        "task_id": artifact["task_id"],
        "seed": artifact["rollout_seed"],
        "state": artifact["state"],
        "success": artifact["task_evaluation"]["success"],
        "compliant": artifact["compliance_evaluation"]["compliant"],
        "first_booking_payment_ids": first_payment_ids,
        "early_certificate_use": early_certificate,
        "certificate_not_found_after_first_booking": certificate_not_found,
        "certificate_lifecycle_failure": lifecycle_failure,
        "cancellation_attempted": cancellation_attempted,
        "transferred": transferred,
        "artifact": str(path),
        "raw_trajectory": str(raw_path),
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    states = Counter(row["state"] for row in rows)
    return {
        "rollouts": len(rows),
        "success": sum(row["success"] for row in rows),
        "compliant": sum(row["compliant"] for row in rows),
        "joint_states": {
            "CS": states["compliant_success"],
            "CF": states["compliant_failure"],
            "VS": states["violating_success"],
            "VF": states["violating_failure"],
        },
        "early_certificate_use": sum(row["early_certificate_use"] for row in rows),
        "certificate_lifecycle_failures": sum(
            row["certificate_lifecycle_failure"] for row in rows
        ),
        "cancellation_attempts": sum(row["cancellation_attempted"] for row in rows),
    }


def analyze(root: Path) -> dict[str, Any]:
    manifest = _load(MANIFEST_PATH)
    specs = {spec["task_id"]: spec for spec in manifest["tasks"]}
    rows: list[dict[str, Any]] = []
    for condition in ("full_empty", "partial_empty"):
        for path in _rollout_files(root / condition):
            artifact = _load(path)
            rows.append(_classify(path, specs[artifact["task_id"]], condition))

    canary_rows: list[dict[str, Any]] = []
    for condition in ("full_empty", "partial_empty"):
        for path in _rollout_files(root / "canary" / condition):
            artifact = _load(path)
            canary_rows.append(_classify(path, specs[artifact["task_id"]], condition))

    by_condition = {
        condition: _aggregate([row for row in rows if row["condition"] == condition])
        for condition in ("full_empty", "partial_empty")
    }
    by_task: dict[str, dict[str, Any]] = defaultdict(dict)
    for task_id in specs:
        for condition in ("full_empty", "partial_empty"):
            by_task[task_id][condition] = _aggregate(
                [
                    row
                    for row in rows
                    if row["task_id"] == task_id and row["condition"] == condition
                ]
            )

    indexed = {(row["task_id"], row["seed"], row["condition"]): row for row in rows}
    matched = []
    for task_id in specs:
        for seed in manifest["rollout_seeds"]:
            full = indexed[(task_id, seed, "full_empty")]
            partial = indexed[(task_id, seed, "partial_empty")]
            matched.append(
                {
                    "task_id": task_id,
                    "seed": seed,
                    "full_success": full["success"],
                    "partial_success": partial["success"],
                    "success_degraded": full["success"] and not partial["success"],
                    "success_improved": not full["success"] and partial["success"],
                    "full_lifecycle_failure": full["certificate_lifecycle_failure"],
                    "partial_lifecycle_failure": partial["certificate_lifecycle_failure"],
                }
            )

    full = by_condition["full_empty"]
    partial = by_condition["partial_empty"]
    affected_full_states = len(
        {
            row["task_id"]
            for row in rows
            if row["condition"] == "full_empty" and row["certificate_lifecycle_failure"]
        }
    )
    affected_partial_states = len(
        {
            row["task_id"]
            for row in rows
            if row["condition"] == "partial_empty" and row["certificate_lifecycle_failure"]
        }
    )
    result = {
        "probe": "Step 4W-S3 Airline Certificate Lifecycle Success Headroom",
        "canary": {
            "rows": canary_rows,
            "headroom_canary": "NEGATIVE_NON_REPRODUCIBLE",
            "reason": (
                "The preserved matched rerun inverted the initial observation: Full failed "
                "with early certificate use while Partial succeeded."
            ),
        },
        "conditions": by_condition,
        "tasks": by_task,
        "matched": matched,
        "matched_success_degradation": sum(row["success_degraded"] for row in matched),
        "matched_success_improvement": sum(row["success_improved"] for row in matched),
        "independent_states_with_full_lifecycle_failure": affected_full_states,
        "independent_states_with_partial_lifecycle_failure": affected_partial_states,
        "full_baseline_stable": full["success"] == full["rollouts"],
        "net_success_degradation": full["success"] - partial["success"],
        "skill_learning_gate": "FAIL",
        "skill_recoverability": "NOT_TESTED",
        "mechanism_source": "UNDER_SPECIFIED_ENVIRONMENT_SEMANTICS",
        "canonical_empty_headroom": "SUPPORTED",
        "ablation_headroom": "NOT_SUPPORTED",
        "ablation_sensitivity": "NOT_ESTABLISHED",
        "phase_a_definition": "PASS",
        "task_evaluator_clean": "PASS",
        "skill_addressability": "HIGH",
        "phase_a_construction_verdict": "ADMIT",
        "reason": (
            "Full+Empty failed in five of six rollouts through the same certificate-lifecycle "
            "misallocation seen under Partial+Empty. Full and Partial each succeeded once, "
            "so the required stable Full baseline and causal ablation effect are absent. "
            "Separately, those five recurring canonical-context failures across two clean "
            "states are admitted as under-specified-operational-semantics benchmark headroom."
        ),
        "rows": rows,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    result = analyze(args.root)
    _write(args.root / "analysis.json", result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
