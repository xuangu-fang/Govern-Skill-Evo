#!/usr/bin/env python3
"""Validate Phase-v1 latent-G static, legal-path, and Reference Skill artifacts."""

import json
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate'))
load = lambda name: json.loads((HERE / name).read_text())
static = load("phase_v1_latent_g_static_legal_audit.json")
result = load("phase_v1_latent_g_reference_results.json")
runtime = load("runtime/run_summary.json")
manifest = load("reference_skill_manifest.json")

assert static["task_count"] == 6 and static["family_count"] == 3
assert static["historical_e0"] == {"rollouts": 18, "CS": 0, "CF": 0, "VS": 18, "VF": 0}
assert static["surface_shortcut_verdict"] == "FAIL_REBUILD_REQUIRED"
assert static["legal_path_verdict"] == "FAIL_NO_COMPLIANT_TASK_SUCCESS_PATH_ALL_6"
assert all(not row["legal_task_success_path"] and row["classification"] == "REBUILD" for row in static["tasks"])
assert manifest["status"] == "FROZEN_BEFORE_FIRST_ROLLOUT" and manifest["rollouts_requested"] == 18
assert runtime["completed"] == 18 and runtime["errors"] == runtime["refused_reruns"] == 0
assert runtime["behavioral_trajectory_reruns"] == 0 and runtime["protected_files_unchanged"] is True
assert result["paired_focal_repairs"] == 18
assert result["overall_reference"]["focal_G_violated"] == 0
assert result["overall_reference"]["legal_terminal_behavior"] == 18
assert result["overall_reference"]["success"] == 0
assert result["overall_reference"]["official_compliance"] == 17
assert result["overall_reference"]["quadrants"] == {"CS": 0, "CF": 17, "VS": 0, "VF": 1}
assert all(row["focal_repair_gate"] for row in result["families"].values())
assert sum(len(row["judge_nonfocal_violations"]) for row in result["records"]) == 1
print("PASS_PHASE_V1_LATENT_G_GATE_VALIDATION")
