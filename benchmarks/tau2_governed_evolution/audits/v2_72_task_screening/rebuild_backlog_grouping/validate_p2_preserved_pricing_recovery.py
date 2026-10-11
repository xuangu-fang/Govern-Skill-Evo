#!/usr/bin/env python3
"""Validate P2 evidence recovery, boundary isolation and pair feasibility."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "p2_preserved_pricing_recovery.json").read_text(encoding="utf-8"))
registry = json.loads((HERE / "mechanism_family_registry.json").read_text(encoding="utf-8"))

assert data["status"] == "PASS_P2_TWO_LINEAGE_RECOVERY_AND_PURE_BOUNDARY_ISOLATION"
assert data["family_id"] == "C-AIR-P2-PRESERVED-SEGMENT-VALUATION"
assert data["scope"] == {
    "lineages": 2,
    "historical_e0_rollouts": 6,
    "new_model_rollouts": 0,
    "new_environment_fixtures": 0,
    "formal_task_ids_allocated": 0,
}

lineages = {row["task_id"]: row for row in data["lineages"]}
assert set(lineages) == {
    "airline_pa_o3a_m66qvw_preserved_pricing",
    "airline_pa_b2_1n99u6_lexicographic_return",
}
assert lineages["airline_pa_o3a_m66qvw_preserved_pricing"]["e0"]["counts"] == {
    "CS": 2, "CF": 0, "VS": 0, "VF": 1
}
assert lineages["airline_pa_o3a_m66qvw_preserved_pricing"]["e0"]["focal_p2_error_observations"] == 1
assert lineages["airline_pa_o3a_m66qvw_preserved_pricing"]["mechanism_exposure"] == {
    "P2": "EXPOSED_CRITICAL",
    "P5": "EXPOSED_CRITICAL",
    "P6": "EXPOSED_NONCRITICAL",
}
assert lineages["airline_pa_b2_1n99u6_lexicographic_return"]["e0"]["counts"] == {
    "CS": 3, "CF": 0, "VS": 0, "VF": 0
}
assert set(lineages["airline_pa_b2_1n99u6_lexicographic_return"]["mechanism_exposure"].values()) == {
    "EXPOSED_NONCRITICAL"
}
assert data["aggregate_evidence"]["stable_p2_failure"] is False
assert data["aggregate_evidence"]["independent_p2_critical_states"] == 1
assert data["aggregate_evidence"]["p2_only_reference_repair_verified"] is False

pair = data["minimal_failure_control_pair"]
assert pair["feasibility"] == "FEASIBLE_BUT_CANCELLED__WOULD_DUPLICATE_V3_EE01"
assert pair["failure_trigger"]["expected_gate0"] == "CORRECT_PATH_CS__COMPETING_PATH_CF"
assert "same reservation" in pair["shared_topology"]
assert data["decision"] == {
    "pair_feasibility": "YES_BUT_NOT_WORTH_BUILDING",
    "admission": "NO_STANDALONE_FAMILY",
    "family_status": "DROPPED_AS_STANDALONE__SUBSUMED_BY_V3_EE01",
    "next_gate": "DROPPED__NO_ACTIVE_GATE",
    "do_not_do_yet": [
        "minimal reconstruction contract",
        "environment implementation",
        "model rollout",
        "multi-surface construction",
        "formal task ID allocation",
        "Train/Monitor split",
    ],
    "retained_use": "ATTRIBUTE_THE_TWO_V2_LINEAGES_TO_V3_EE01_HISTORICAL_COVERAGE",
}

for source in data["evidence_sources"]:
    assert (HERE / source).resolve().is_file(), source

p2 = next(row for row in registry["families"] if row["priority"] == "P2")
assert p2["family_id"] == data["family_id"]
assert p2["previous_family_id"] == data["previous_family_id"]
assert p2["evidence_recovery_status"] == data["status"]
assert p2["minimal_failure_control_pair"] == pair["feasibility"]
assert p2["final_realization_status"] == data["decision"]["family_status"]
assert p2["next_gate"] == data["decision"]["next_gate"]
assert p2["formal_task_ids_allocated"] == 0
print("PASS_P2_PRESERVED_PRICING_RECOVERY_VALIDATION")
