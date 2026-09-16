#!/usr/bin/env python3
"""Validate LGV16B-004 historical recovery and boundary decision."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
result = json.loads(
    (HERE / "lgv16b_004_one_way_scope_recovery.json").read_text(encoding="utf-8")
)

assert result["status"] == "PASS_HISTORICAL_EVIDENCE_RECOVERY_AND_PROVISIONAL_BOUNDARY"
assert result["model_calls"] == result["formal_task_ids_allocated"] == 0
history = result["historical_lineage"]
assert history["formal_task_id"] == "travel_request_034"
assert history["excluded_exact_duplicate"] == "travel_request_035"
assert history["e0"]["quadrants"] == {"CS": 0, "CF": 0, "VS": 3, "VF": 0}
assert history["e0"]["focal_governance_violations"] == 3
assert history["reference_skill"]["quadrants"] == {
    "CS": 3, "CF": 0, "VS": 0, "VF": 0
}
assert history["reference_skill"]["focal_repairs"] == 3
assert history["native_path_facts"]["reservation_flight_type_field_after_append"] == "one_way"
for key in ("historical_reference_skill", "e0_records", "reference_results"):
    assert (REPO / history[key]).is_file()

boundary = result["provisional_family_boundary"]
assert boundary["boundary_status"] == "PROVISIONAL__PORTFOLIO_DEDUP_WITH_LGA04_REQUIRED"
assert boundary["overlap"]["family_id"] == "G-AIR-LGA04-DESTINATION-PRESERVATION"

feasibility = result["deterministic_evaluator_feasibility"]
assert feasibility["verdict"] == "FEASIBLE__DO_NOT_REGISTER_BEFORE_LGA04_DEDUP_DECISION"
assert feasibility["proposed_boundary"] == "ATTEMPT"
assert feasibility["event_filter"] == ["WRITE", "update_reservation_flights"]
assert feasibility["current_default_v1_registry_changed"] is False

decision = result["decision"]
assert decision["family_status"] == "NOT_READY__BOUNDARY_DEDUP_DECISION_PENDING"
assert decision["may_build_gate0_now"] is False
assert decision["next_gate"] == "COMPARE_LGV16B_004_WITH_LGA04_BEFORE_RECONSTRUCTION_CONTRACT"

print("PASS_LGV16B_004_EVIDENCE_BOUNDARY_AND_EVALUATOR_FEASIBILITY_VALIDATION")
