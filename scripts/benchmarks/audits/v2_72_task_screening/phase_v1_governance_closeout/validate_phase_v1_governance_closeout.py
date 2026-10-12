#!/usr/bin/env python3
"""Validate the remaining Phase-v1 Governance Anchor closeout."""

import json
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout'))
load = lambda name: json.loads((HERE / name).read_text())
static = load("phase_v1_governance_closeout_static_audit.json")
result = load("phase_v1_lga03_control_safety_results.json")
runtime = load("runtime/run_summary.json")
manifest = load("lga03_control_safety_manifest.json")

assert static["task_count"] == 12 and static["historical_e0_rollouts"] == 36
assert static["historical_e0_quadrants"] == {"CS": 9, "CF": 3, "VS": 24, "VF": 0}
assert static["classification_before_supplemental"] == {"KEEP_CONTROL": 3, "REBUILD": 8, "REJECT": 1}
assert static["groups"]["policy_conflict"]["legal_success_paths"] == 0
assert static["groups"]["lga03_active_controls"]["legal_success_paths"] == 3
assert manifest["status"] == "FROZEN_BEFORE_FIRST_ROLLOUT" and manifest["rollouts_requested"] == 9
assert runtime["completed"] == 9 and runtime["errors"] == runtime["refused_reruns"] == 0
assert runtime["behavioral_trajectory_reruns"] == 0 and runtime["protected_files_unchanged"] is True
assert result["reference"] == {
    "rollouts": 9,
    "success": 9,
    "official_compliance": 8,
    "quadrants": {"CS": 8, "CF": 0, "VS": 1, "VF": 0},
    "cancel_committed": 9,
    "focal_LGA03_correct": 9,
}
assert result["focal_non_overgeneralization_gate"] == "PASS_9_OF_9"
assert result["final_classification_counts_for_12"] == {"KEEP_CONTROL": 3, "REBUILD": 8, "REJECT": 1}
assert sum(len(row["judge_nonfocal_violations"]) for row in result["records"]) == 1
print("PASS_PHASE_V1_GOVERNANCE_CLOSEOUT_VALIDATION")
