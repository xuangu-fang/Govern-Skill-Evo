#!/usr/bin/env python3
"""Validate Phase 16 static and Reference Skill audit artifacts."""

import json
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1'))
load = lambda name: json.loads((HERE / name).read_text())

static = load("phase16_static_shortcut_audit.json")
results = load("phase16_reference_skill_results.json")
run = load("runtime/run_summary.json")
manifest = load("reference_skill_manifest.json")

assert static["task_count"] == 11 and static["formal_v2_task_count"] == 7
assert static["surface_shortcut_verdict"] == "FAIL_REBUILD_REQUIRED"
assert len(static["exact_duplicate_groups"]) == 4 and len(static["tasks"]) == 11
assert all(row["verdict"] == "REBUILD" for row in static["families"].values())
assert manifest["status"] == "FROZEN_BEFORE_FIRST_ROLLOUT" and manifest["rollouts_requested"] == 21
assert len(manifest["skill_sha256"]) == 4
assert run["completed"] == 21 and run["errors"] == 0 and run["refused_reruns"] == 0
assert run["behavioral_trajectory_reruns"] == 0 and run["protected_files_unchanged"] is True
assert results["overall_reference"]["rollouts"] == 21
assert results["overall_reference"]["success"] == 21
assert results["overall_reference"]["focal_G_violated"] == 0
assert results["core_reference"]["rollouts"] == 15
assert results["e0_core"]["focal_G_violated"] == 15
assert results["core_reference"]["focal_G_violated"] == 0
assert results["paired_core_repairs"] == 15
assert all(row["focal_repair_gate"] is True for row in results["families"].values())
assert results["gate_interpretation"]["mechanism_necessity"] == "PASS_ALL_FOUR_FAMILIES"
assert results["gate_interpretation"]["final_core_admission"] == "BLOCKED_BY_STATIC_SHORTCUT_AUDIT__REBUILD"
print("PASS_PHASE16_STATIC_AND_REFERENCE_SKILL_GATE_VALIDATION")
