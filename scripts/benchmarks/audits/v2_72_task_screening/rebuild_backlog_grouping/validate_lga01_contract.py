#!/usr/bin/env python3
"""Validate the LGA01 reconstruction design before implementation."""

import json
from pathlib import Path


HERE = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/audits/v2_72_task_screening/rebuild_backlog_grouping')
path = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts/lga01_flown_segment_cancellation_reconstruction_contract.json')
data = json.loads(path.read_text(encoding="utf-8"))

assert data["status"] == "PASS_LGA01_RECONSTRUCTION_DESIGN_CONTRACT_ONLY"
assert data["family_id"] == "G-AIR-LGA01-FLOWN-SEGMENT-CANCELLATION"
assert data["model_calls"] == data["formal_task_ids_allocated"] == 0
assert (((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts')) / data["evidence_recovery_path"]).resolve().is_file()
boundary = data["family_boundary"]
assert boundary["decision"] == "KEEP_ONE_FAMILY__NARROW_TO_LANDED_PREFIX_WITH_AVAILABLE_SUFFIX"
assert set(boundary["topology_strata"]) == {
    "TWO_SEGMENT_OUT_AND_BACK",
    "MULTI_SEGMENT_OUT_AND_BACK",
}
assert data["environment_contract"]["new_domain"] is False
assert data["environment_contract"]["tool_schema_change"] is False
rule = data["deterministic_rule"]
assert rule["activation"] == "EVIDENCE_PROFILE_ONLY__NOT_DEFAULT_V1"
assert rule["violation_on"] == "ATTEMPT"
assert rule["llm_judge_required"] is False
assert "dates as a substitute for status" in rule["forbidden_inputs"]
assert data["trigger_task_success"]["legal_path"]["quadrant"] == "CS"
assert data["trigger_task_success"]["competing_path"]["quadrant"] == "VS"
gate1 = data["gate1_contract"]
assert gate1["planned_rollouts"] == 8
assert gate1["topology_strata"] == 2
assert gate1["post_hoc_retuning_allowed"] is False
assert data["design_audit"]["status"] == "PASS_LGA01_DESIGN_AUDIT"
results = data["execution_results"]
assert results["gate0_status"] == "PASS_LGA01_ZERO_MODEL_GATE_0"
assert results["gate1_status"] == "HOLD_LGA01_GATE_1_TRIGGER_NECESSITY"
assert results["final_realization_status"] == "DEFERRED__NO_CURRENT_SKILL_NECESSITY"
assert data["next_gate"] == "DEFERRED__NO_ACTIVE_GATE"
assert (((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts')) / results["gate0_path"]).resolve().is_file()
assert (((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts')) / results["gate1_path"]).resolve().is_file()
print("PASS_LGA01_RECONSTRUCTION_CONTRACT_VALIDATION")
