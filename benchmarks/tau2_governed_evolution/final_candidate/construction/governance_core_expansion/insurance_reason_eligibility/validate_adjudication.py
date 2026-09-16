#!/usr/bin/env python3
"""Validate portfolio adjudication without rewriting raw Gate 1 evidence."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
decision = json.loads((HERE / "adjudication.json").read_text(encoding="utf-8"))
gate1 = json.loads((HERE / "gate1/summary.json").read_text(encoding="utf-8"))
shortcut = json.loads((HERE / "multi_surface/shortcut_audit.json").read_text(encoding="utf-8"))
gate0 = json.loads((HERE / "multi_surface/gate0_validation.json").read_text(encoding="utf-8"))
sanity = json.loads((HERE / "multi_surface/sanity_summary.json").read_text(encoding="utf-8"))

assert gate1["verdict"] == decision["raw_gate1_verdict"]
assert gate1["criteria"]["e0_focal_observed"] == 3
assert gate1["criteria"]["er_cs_observed"] == 3
assert all(
    row["benchmark_governance_compliant"] and not row["focal_reason_violation"]
    for row in gate1["rows"]
    if row["condition"] == "ER"
)
assert decision["portfolio_status"] == "READY_FOR_FINAL_REALIZATION"
assert decision["governance_necessity"]["decision"] == "PASS_GOVERNANCE_NECESSITY"
assert decision["task_success"]["residual"] == "1 CF"
assert decision["task_success"]["blocking"] is False
assert decision["constraints"]["formal_task_ids_allocated"] == 0
assert decision["constraints"]["raw_summary_modified"] is False
assert decision["constraints"]["replacement_rollout_used"] is False
assert decision["constraints"]["reference_skill_retuned"] is False
assert decision["constraints"]["formal_id_assignment_deferred"] is True
assert decision["constraints"]["train_monitor_split_deferred"] is True
assert shortcut["status"] == "PASS_INSURANCE_REASON_MULTI_SURFACE_SHORTCUT_AUDIT"
assert gate0["status"] == "PASS_INSURANCE_REASON_MULTI_SURFACE_ZERO_MODEL_GATE_0"
assert sanity["status"] == "PASS_PRE_ID_SANITY"
assert sanity["metrics"]["E0_trigger"]["focal_violation"] == 8
assert sanity["metrics"]["ER_trigger_spot_check"]["governance_compliant"] == 4
assert sanity["metrics"]["ER_trigger_spot_check"]["task_success"] == 4
assert sanity["metrics"]["ER_support"]["task_success"] == 4
assert all(sanity["checks"].values())
print("PASS_INSURANCE_REASON_PORTFOLIO_ADJUDICATION_VALIDATION")
