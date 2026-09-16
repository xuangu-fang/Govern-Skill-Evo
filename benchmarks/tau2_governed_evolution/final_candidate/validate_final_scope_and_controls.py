#!/usr/bin/env python3
"""Validate final scope and all nine formal Protected Controls."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent / "audits" / "v2_72_task_screening" / "v2_72_task_audit.json"
PROTECTED_AUDIT = (
    HERE.parent
    / "audits"
    / "v2_72_task_screening"
    / "phase_v1_protected_control_audit"
    / "phase_v1_protected_control_results.json"
)

scope = json.loads((HERE / "final_benchmark_scope_contract.json").read_text())
controls = json.loads((HERE / "protected_control_portfolio.json").read_text())
audit = json.loads(AUDIT.read_text())
protected_audit = json.loads(PROTECTED_AUDIT.read_text())

assert scope["status"] == "SCOPE_CLOSED__C4_G3_CXG_CONTROLS"
assert scope["headline_metrics"] == [
    "Capability Success",
    "Governance Compliance",
]
assert scope["included_sections"]["capability_only"]["family_count"] == 4
assert scope["included_sections"]["governance_only"]["family_count"] == 3
assert scope["included_sections"]["joint"]["allowed_composition"] == (
    "CAPABILITY_X_GOVERNANCE"
)
assert set(scope["excluded_programs"]) == {
    "COMPOSITE_CAPABILITY",
    "COMPOSITE_GOVERNANCE",
    "CAPABILITY_X_CAPABILITY",
    "GOVERNANCE_X_GOVERNANCE",
}

keep_controls = {
    str(record["task_id"])
    for record in audit["records"]
    if record["classification"] == "KEEP_CONTROL"
}
audit_by_id = {str(record["task_id"]): record for record in audit["records"]}
selected = {str(row["task_id"]) for row in controls["selected_lineages"]}
not_selected = {str(task_id) for task_id in controls["not_selected"]["task_ids"]}

assert len(keep_controls) == controls["source_keep_control_count"] == 21
assert len(selected) == controls["selected_count"] == 7
assert len(not_selected) == controls["not_selected"]["count"] == 14
assert selected.isdisjoint(not_selected)
assert selected | not_selected == keep_controls
assert all(audit_by_id[task_id]["e0"]["counts"]["CS"] == 3 for task_id in selected)
assert sum(row["domain"] == "airline" for row in controls["selected_lineages"]) == 5
assert sum(row["domain"] == "retail" for row in controls["selected_lineages"]) == 2
assert sum(
    row["role"] == "EMPIRICAL_REGRESSION_DETECTOR"
    for row in controls["selected_lineages"]
) == 4
assert {
    row["task_id"]
    for row in controls["selected_lineages"]
    if row["role"] == "EMPIRICAL_REGRESSION_DETECTOR"
} == set(protected_audit["empirical_regression_detectors"])
assert controls["selection_is_lineage_only"] is False
assert controls["legacy_surfaces_directly_admitted"] is False
assert controls["formal_task_ids_allocated"] == controls["monitor_regression_guard_allocated"] == 9
assert controls["train_monitor_splits_allocated"] == 9
assert controls["control_split_allocated"] == 0
assert controls["v3_gap_lineage_count"] == controls["v3_gap_formal_realization_count"] == 2
assert controls["ready_for_formal_realization_count"] == 0
assert all(
    row["state"] == "FORMALLY_REALIZED__PASS_REGRESSION_AND_E0"
    for row in controls["v3_gap_lineages"]
)

print("PASS_FINAL_SCOPE__9_FORMAL_CONTROLS")
