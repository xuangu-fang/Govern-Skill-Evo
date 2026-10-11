#!/usr/bin/env python3
"""Recover E0 and v2 evolution evidence for the 16 Protected Controls."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCREENING = HERE.parent
REPO = HERE.parents[4]
PILOT = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/experiments/benchmark_v2_v15_pilot_001/run/final/final_summary.json"

FINAL = {
    "retail_pa_v2_w9318778_payment_items_address": ("REBUILD", "UNSUITABLE_NOISY_BASELINE"),
    "retail_pa_r4a_w5918442_one_shot_cameras": ("KEEP_CONTROL", "EMPIRICAL_REGRESSION_DETECTOR"),
    "airline_pa_b2_1n99u6_lexicographic_return": ("REBUILD", "SENSITIVE_BUT_NOISY_BASELINE"),
    "airline_pa_d2_sf5va1_cabin_fallback_bags": ("KEEP_CONTROL", "STABLE_NEGATIVE_GUARD"),
    "airline_pa_e1_raj_mixed_operations": ("KEEP_CONTROL", "STABLE_NEGATIVE_GUARD"),
    "airline_pa_e2_fatima_distinct_operations": ("KEEP_CONTROL", "EMPIRICAL_REGRESSION_DETECTOR"),
    "retail_pa_r2a_w8557584_item_delta_scope": ("KEEP_CONTROL", "P1_BOUNDARY_GUARD_PENDING_SUPPLEMENT"),
    "retail_pa_r2b_w9318778_order_address_scope": ("KEEP_CONTROL", "STABLE_NEGATIVE_GUARD"),
    "retail_pa_r4b_w9132840_one_shot_helmets": ("KEEP_CONTROL", "STABLE_NEGATIVE_GUARD"),
    "airline_pa_a1a_dkgiih_business_seat_bottleneck": ("KEEP_CONTROL", "EMPIRICAL_REGRESSION_DETECTOR"),
    "airline_pa_a2a_6zqnos_fixed_8accrd_buffer": ("KEEP_CONTROL", "EMPIRICAL_REGRESSION_DETECTOR"),
    "airline_pa_a2b_9niyyj_fixed_eoj7hm_buffer": ("KEEP_CONTROL", "STABLE_NEGATIVE_GUARD"),
    "16": ("KEEP_CONTROL", "P1_NON_APPLICABILITY_GUARD_PENDING_SUPPLEMENT"),
    "17": ("KEEP_CONTROL", "STABLE_NEGATIVE_GUARD"),
    "53": ("REJECT", "UNSUITABLE_NOISY_REDUNDANT_CONTROL"),
    "75": ("REBUILD", "SENSITIVE_BUT_NOISY_BASELINE"),
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    audit = load(SCREENING / "v2_72_task_audit.json")
    controls = {row["task_id"]: row for row in audit["records"] if row["original_role"] == "PROTECTED_CONTROL"}
    assert set(controls) == set(FINAL) and len(controls) == 16

    pilot_rows = defaultdict(list)
    for step in load(PILOT)["steps"]:
        for pair in step["monitor_comparison"]["matched_pairs"]:
            if pair["task_id"] in controls:
                pilot_rows[pair["task_id"]].append({"step": step["step"], **pair})

    records = []
    for task_id, row in controls.items():
        pairs = pilot_rows[task_id]
        transitions = Counter(f'{pair["parent_state"]}->{pair["candidate_state"]}' for pair in pairs)
        regressions = [pair for pair in pairs if pair["parent_state"] == "CS" and pair["candidate_state"] != "CS"]
        parent_non_cs = [pair for pair in pairs if pair["parent_state"] != "CS"]
        classification, role = FINAL[task_id]
        records.append(
            {
                "task_id": task_id,
                "domain": row["domain"],
                "source_stage": row["source_stage"],
                "original_mechanism": row["original_mechanism"],
                "historical_e0": row["e0"],
                "historical_e0_clean": row["e0"]["counts"]["CS"] == 3,
                "shortcut_audit": row["shortcut_audit"],
                "unified_environment": row["unified_environment"],
                "pilot": {
                    "matched_pairs": len(pairs),
                    "transitions": dict(sorted(transitions.items())),
                    "clean_regressions": len(regressions),
                    "regression_coordinates": [
                        {"step": pair["step"], "rollout_index": pair["rollout_index"], "from": pair["parent_state"], "to": pair["candidate_state"]}
                        for pair in regressions
                    ],
                    "parent_non_cs": len(parent_non_cs),
                    "coverage": "NOT_IN_FIXED_MONITOR" if not pairs else "THREE_STEPS_THREE_MATCHED_SEEDS",
                },
                "control_role": role,
                "classification": classification,
            }
        )

    records.sort(key=lambda row: row["task_id"])
    counts = Counter(row["classification"] for row in records)
    roles = Counter(row["control_role"] for row in records)
    output = {
        "schema_version": "phase_v1_protected_control_static_audit_v1",
        "scope": "16 Phase v1 Protected Controls in frozen Benchmark v2",
        "evidence": {
            "historical_e0_rollouts": sum(row["historical_e0"]["rollouts"] for row in records),
            "pilot_matched_pairs": sum(row["pilot"]["matched_pairs"] for row in records),
            "pilot_tasks_covered": sum(bool(row["pilot"]["matched_pairs"]) for row in records),
            "tasks_with_clean_observed_regression": sum(row["control_role"] == "EMPIRICAL_REGRESSION_DETECTOR" for row in records),
        },
        "classification_counts": dict(sorted(counts.items())),
        "role_counts": dict(sorted(roles.items())),
        "records": records,
    }
    (HERE / "phase_v1_protected_control_static_audit.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(output["evidence"], indent=2))


if __name__ == "__main__":
    main()
