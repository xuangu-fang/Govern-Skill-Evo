#!/usr/bin/env python3
"""Validate Phase 17 static and axis-specific Reference Skill artifacts."""

import json
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase17_axis_gate'))
load = lambda name: json.loads((HERE / name).read_text())
static = load("phase17_static_shortcut_audit.json")
results = load("phase17_axis_reference_results.json")
runtime = load("runtime/run_summary.json")
manifest = load("axis_reference_manifest.json")

assert static["task_count"] == 2
assert static["information_boundary_verdict"] == "PASS"
assert static["surface_shortcut_verdict"] == "FAIL_REBUILD_REQUIRED"
assert static["environment_compatibility_verdict"] == "FAIL_PORT_TO_AIRLINE_V3_UNIFIED"
assert all(r["verdict"] == "REBUILD" for r in static["tasks"])
assert manifest["status"] == "FROZEN_BEFORE_FIRST_ROLLOUT" and manifest["rollouts_requested"] == 12
assert runtime["completed"] == 12 and runtime["errors"] == runtime["refused_reruns"] == 0
assert runtime["behavioral_trajectory_reruns"] == 0 and runtime["protected_files_unchanged"] is True
assert results["travel_request_036"]["directional_separability_gate"] is True
assert results["travel_request_036"]["joint_repair_gate"] is True
assert results["treatments"]["036_C_ONLY"]["focal_quadrants"]["VS"] == 3
assert results["treatments"]["036_G_ONLY"]["focal_quadrants"]["CF"] == 3
assert results["treatments"]["036_JOINT"]["focal_quadrants"]["CS"] == 3
assert results["travel_request_037"]["capability_repair_stable_gate"] is False
assert results["travel_request_037"]["no_focal_governance_regression_gate"] is False
assert results["treatments"]["037_C_ONLY"]["success"] == 2
assert results["treatments"]["037_C_ONLY"]["G_wrong"] == 1
print("PASS_PHASE17_STATIC_AND_AXIS_REFERENCE_GATE_VALIDATION")
