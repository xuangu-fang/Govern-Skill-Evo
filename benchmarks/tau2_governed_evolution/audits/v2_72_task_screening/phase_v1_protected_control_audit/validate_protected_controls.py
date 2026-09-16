#!/usr/bin/env python3
"""Validate Protected Control closeout invariants."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "phase_v1_protected_control_results.json").read_text(encoding="utf-8"))
assert data["verdict"] == "PASS_PROTECTED_CONTROL_AUDIT"
assert data["evidence_totals"] == {
    "historical_e0_rollouts": 48,
    "pilot_matched_pairs": 117,
    "pilot_tasks_covered": 13,
    "tasks_with_clean_observed_regression": 4,
    "supplemental_rollouts": 6,
    "total_evidence_units": 171,
}
assert data["supplemental_P1"]["focal_boundary_safe"] == 6
assert data["runtime_integrity"]["behavioral_trajectory_reruns"] == 0
assert data["runtime_integrity"]["protected_files_unchanged"] is True
assert data["classification_counts_for_16"] == {"KEEP_CONTROL": 12, "REBUILD": 3, "REJECT": 1}
assert len(data["empirical_regression_detectors"]) == 4
assert len(data["verified_or_stable_negative_guards"]) == 8
assert len(data["records"]) == 16
print("PASS_PHASE_V1_PROTECTED_CONTROL_VALIDATION")
