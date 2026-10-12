#!/usr/bin/env python3
"""Validate LGA04 recovery and the endpoint-preservation merge decision."""

import json
from pathlib import Path


HERE = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/audits/v2_72_task_screening/rebuild_backlog_grouping')
data = json.loads(
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/lga04_endpoint_preservation_recovery_and_merge_decision.json')).read_text(
        encoding="utf-8"
    )
)

assert data["status"] == "PASS_LGA04_RECOVERY_BOUNDARY_NARROWING_AND_PORTFOLIO_MERGE_DECISION"
assert data["model_calls"] == 0
assert data["formal_task_ids_allocated"] == 0

history = data["historical_evidence"]
assert len(history["lineages"]) == 4
assert len({row["task_id"] for row in history["lineages"]}) == 4
assert history["aggregate_e0"]["rollouts"] == 12
assert history["aggregate_e0"]["quadrants"] == {"CS": 0, "CF": 0, "VS": 12, "VF": 0}
assert history["aggregate_e0"]["governance_headroom"] == "STABLE"
assert history["excluded_contextual_probe"]["task_id"] == "travel_request_017"

boundary = data["narrowed_lga04_boundary"]
assert boundary["historically_observed_topology"] == "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT"
assert "trip-type-only mutation as an independent mechanism" in boundary["not_established_by_lga04_history"]

decision = data["portfolio_decision"]
assert decision["selected_option"] == 1
assert decision["verdict"] == "MERGE_ONE_FAMILY_TWO_TRIGGER_TOPOLOGIES"
assert decision["portfolio_family_id"] == "G-AIR-ENDPOINT-PRESERVATION"
assert decision["family_count"] == 1
assert decision["source_lineage_count"] == 5
assert len(decision["source_lineages"]) == len(set(decision["source_lineages"])) == 5
assert decision["trigger_topologies"] == [
    "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT",
    "APPENDED_REVERSE_RETURN",
]

evaluator = data["deterministic_evaluator"]
assert evaluator["verdict"] == "FEASIBLE__ONE_SHARED_ATTEMPT_LEVEL_ENDPOINT_RULE"
assert evaluator["default_registry_changed"] is False
assert len(evaluator["required_gate0_cases"]) == 8
assert data["next_gate"]["name"] == "BUILD_MERGED_ENDPOINT_PRESERVATION_RECONSTRUCTION_CONTRACT"

print("PASS_LGA04_ENDPOINT_PRESERVATION_MERGE_DECISION_VALIDATION")
