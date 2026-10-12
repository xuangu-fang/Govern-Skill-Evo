#!/usr/bin/env python3
"""Validate the Phase 13-15 nine-task audit and supplemental experiment."""

import json
from pathlib import Path

HERE=((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit'))
load=lambda name:json.loads((HERE/name).read_text())
audit=load("phase13_15_static_evidence_audit.json")
result=load("phase13_15_certificate_reference_results.json")
runtime=load("runtime/run_summary.json")
manifest=load("certificate_reference_manifest.json")
assert audit["task_count"]==9 and audit["historical_e0_rollouts"]==27
assert audit["historical_e0_quadrants"]=={"CS":20,"CF":2,"VS":1,"VF":4}
assert audit["classification_before_supplemental_experiment"]=={"REJECT":7,"REBUILD":2}
assert len(audit["cross_phase_exact_payload_duplicates"])==2
assert audit["surface_verdict"].startswith("FAIL") and audit["unified_environment_verdict"].startswith("FAIL")
assert manifest["status"]=="FROZEN_BEFORE_FIRST_ROLLOUT" and manifest["rollouts_requested"]==6
assert runtime["completed"]==6 and runtime["errors"]==runtime["refused_reruns"]==0
assert runtime["behavioral_trajectory_reruns"]==0 and runtime["protected_files_unchanged"] is True
assert result["travel_request_022"]["repair_gate"] is True
assert result["travel_request_022"]["metrics"]["quadrants"]["CS"]==3
assert result["travel_request_021"]["support_safety_gate"] is False
assert sum(r["premature_user_simulator_stop_after_confirmation"] for r in result["records"])==1
print("PASS_PHASE13_15_NINE_TASK_AUDIT_VALIDATION")
