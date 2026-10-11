#!/usr/bin/env python3
"""Validate the P5-only family boundary and minimal reconstruction contract."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
boundary = json.loads((HERE / "p5_incremental_settlement_family_boundary.json").read_text(encoding="utf-8"))
contract = json.loads((HERE / "p5_incremental_settlement_reconstruction_contract.json").read_text(encoding="utf-8"))

assert boundary["status"] == "PASS_P5_P6_FAMILY_BOUNDARY_NARROWING"
assert boundary["decision"] == "KEEP_ONE_NARROWED_P5_FAMILY__NO_INDEPENDENT_P6"
assert boundary["target_family_id"] == "C-AIR-P5-INCREMENTAL-SETTLEMENT-FEASIBILITY"
assert len(boundary["lineages"]) == 2
assert sum(row["e0_counts"]["CF"] for row in boundary["lineages"]) == 2
assert all(row["p5_exposure"] == "EXPOSED_CRITICAL" for row in boundary["lineages"])
assert all(row["p6_exposure"] == "EXPOSED_NONCRITICAL" for row in boundary["lineages"])
assert boundary["p6_status"] == "NOT_ESTABLISHED__INDEPENDENT_HEADROOM_AND_REPAIR_UNVERIFIED"
assert boundary["formal_task_ids_allocated"] == boundary["new_rollouts_run"] == 0

assert contract["family_id"] == boundary["target_family_id"]
assert contract["status"] == "PASS_MINIMAL_DESIGN_CONTRACT_ONLY"
assert contract["environment"] == "airline-final-candidate-construction"
assert contract["environment_extension"] == "FIXTURE_ONLY"
assert not contract["new_domain"] and not contract["new_tool"] and not contract["new_oracle_sidecar"]
assert contract["mechanism"]["operation"] == "update_reservation_flights"
assert contract["mechanism"]["replacement_scope"] == "COMPLETE_ITINERARY_REPLACEMENT"
assert len(contract["trigger_inputs"]) == 2
assert {row["direction"] for row in contract["trigger_inputs"]} == {
    "PRIMARY_CABIN_FEASIBLE_ONLY_BY_DELTA",
    "FALLBACK_CABIN_FEASIBLE_ONLY_BY_DELTA",
}
assert "partially preserved itinerary or preserved-segment repricing" in contract["excluded_dimensions"]
assert "baggage allowance, baggage count, or baggage fee as a decision branch" in contract["excluded_dimensions"]
assert "standalone P6 backend-enforcement behavior" in contract["excluded_dimensions"]
assert contract["information_boundary"]["evaluator_only_hidden_mapping"] is False
assert contract["support_policy"] == "OMITTED__GLOBAL_PROTECTED_CONTROLS"
assert contract["gate0"]["correct_paths_required_cs"] == 2
assert contract["gate0"]["gross_fare_competing_paths_required_cf"] == 2
assert contract["gate0"]["v3_oracle_regression_required"] == 32
assert contract["future_gate1"] == {
    "design": "TRIGGER_ONLY_MATCHED_E0_ER",
    "triggers": 2,
    "seeds": 2,
    "planned_rollouts": 8,
    "e0_focal_settlement_failure_min": 3,
    "er_cs_required": 4,
    "first_user_answer_leak_allowed": 0,
    "post_hoc_retuning_allowed": False,
}
assert contract["formal_task_ids_allocated"] == 0
assert contract["current_scope"] == "CONTRACT_ONLY__NO_ENVIRONMENT_IMPLEMENTATION_OR_MODEL_ROLLOUT"
print("PASS_P5_INCREMENTAL_SETTLEMENT_BOUNDARY_AND_MINIMAL_CONTRACT")
