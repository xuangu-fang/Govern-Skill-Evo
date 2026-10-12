#!/usr/bin/env python3
"""Validate coverage, priorities, tags, and deferred Joint dependencies."""

import csv
import json
from collections import Counter
from pathlib import Path


HERE = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/audits/v2_72_task_screening/rebuild_backlog_grouping')
data = json.loads((HERE / "mechanism_family_registry.json").read_text(encoding="utf-8"))
families = data["families"]
lineages = data["lineages"]
assert data["scope"] == {
    "rebuild_lineages": 40,
    "historical_source_family_rows": 14,
    "planned_portfolio_mechanism_families": 13,
}
assert len(lineages) == len({row["task_id"] for row in lineages}) == 40
assert len(families) == len({row["family_id"] for row in families}) == 14
assert sum(row["lineage_count"] for row in families) == 40
assert data["priority_family_counts"] == {"P0": 6, "P1": 5, "P2": 1, "P3": 2}
assert data["portfolio_priority_family_counts"] == {"P0": 6, "P1": 4, "P2": 1, "P3": 2}
assert Counter(row["priority"] for row in families) == {"P0": 6, "P1": 5, "P2": 1, "P3": 2}
assert data["portfolio_consolidations"] == [
    {
        "portfolio_family_id": "G-AIR-ENDPOINT-PRESERVATION",
        "decision": "MERGE_ONE_FAMILY_TWO_TRIGGER_TOPOLOGIES",
        "source_family_ids": [
            "G-AIR-LGA04-DESTINATION-PRESERVATION",
            "G-AIR-LGV16B-004-ONE-WAY-SCOPE",
        ],
        "trigger_topologies": [
            "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT",
            "APPENDED_REVERSE_RETURN",
        ],
        "decision_path": "lga04_endpoint_preservation_recovery_and_merge_decision.json",
        "contract_status": "PASS_MERGED_RECONSTRUCTION_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/endpoint_preservation_reconstruction_contract.json",
        "gate0_status": "PASS_ENDPOINT_PRESERVATION_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/airline_unified_governance_gate0/endpoint_preservation/gate0_validation.json",
        "gate1_status": "HOLD_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/airline_unified_governance_gate0/endpoint_preservation/gate1/summary.json",
        "final_realization_status": "DEFERRED__NO_CURRENT_SKILL_NECESSITY",
        "next_gate": "DEFERRED__NO_ACTIVE_GATE",
    }
]
assert (HERE / data["portfolio_consolidations"][0]["contract_path"]).resolve().is_file()
assert data["portfolio_closeouts"] == {
    "P0": {
        "status": "PASS_P0_PORTFOLIO_CLOSEOUT",
        "path": "p0_portfolio_closeout.json",
    },
    "P1": {
        "status": "P1_GOVERNANCE_PORTFOLIO_CLOSED",
        "path": "p1_governance_portfolio_closeout.json",
    },
    "P2": {
        "status": "P2_STANDALONE_FAMILY_CLOSED__SUBSUMED_BY_V3_EE01",
        "path": "p2_portfolio_closeout.json",
    },
    "P3": {
        "status": "P3_LIGHTWEIGHT_CLOSEOUT_COMPLETE",
        "path": "p3_portfolio_closeout.json",
    },
    "TOTAL": {
        "status": "MECHANISM_PORTFOLIO_CLOSED__READY_3_DEFERRED_7_DROPPED_3",
        "path": "mechanism_portfolio_closeout.json",
    },
}
assert all((HERE / row["path"]).is_file() for row in data["portfolio_closeouts"].values())
assert all({"SURFACE_NOT_BALANCED", "UNIFIED_ENV_PORT"}.issubset(row["defect_tags"]) for row in lineages)
joint = next(row for row in families if row["axis"] == "JOINT")
assert joint["priority"] == "P3"
assert len(joint["dependencies"]) == 3
assert joint["dependencies"] == [
    "C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION",
    "G-AIR-LGV16B-001-PASSENGER-CARDINALITY",
    "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE",
]
assert joint["formal_task_ids_allocated"] == 0
assert joint["final_realization_status"] == (
    "DROPPED_HISTORICAL_SEEDS__REPLACE_WITH_NEW_POST_INTEGRATION_JOINT_DESIGN"
)
assert joint["next_gate"] == "DROPPED__NO_ACTIVE_GATE"
p3 = next(row for row in families if row["family_id"] == "C-RET-P3-RESOURCE-REFRESH")
assert p3["final_realization_status"] == "DEFERRED__NO_CURRENT_SKILL_NECESSITY"
assert p3["next_gate"] == "DEFERRED__NO_ACTIVE_GATE"
p4 = next(row for row in families if row["family_id"] == "C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION")
assert p4["lineage_count"] == 7
assert p4["family_boundary_decision"] == "KEEP_ONE_NARROWED_P4_FAMILY"
assert p4["contract_status"] == "PASS_MINIMAL_DESIGN_CONTRACT_ONLY"
assert p4["gate0_status"] == "PASS_P4_ZERO_MODEL_GATE_0"
assert p4["gate1_status"] == "PASS_P4_GATE_1_TRIGGER_NECESSITY"
assert p4["shortcut_audit_status"] == "PASS_P4_MULTI_SURFACE_SHORTCUT_AUDIT"
assert p4["sanity_check_status"] == "PASS_P4_PRE_ID_SANITY_CHECK"
assert p4["formal_task_ids_allocated"] == 0
assert p4["final_realization_status"] == "READY_FOR_FINAL_REALIZATION"
assert p4["next_gate"] == "HOLD_FOR_PORTFOLIO_STABILIZATION_BEFORE_FINAL_REALIZATION"
p5 = next(row for row in families if row["family_id"] == "C-AIR-P5-INCREMENTAL-SETTLEMENT-FEASIBILITY")
assert p5["previous_family_id"] == "C-AIR-P5-P6-CABIN-BAGGAGE-BUDGET"
assert p5["family_boundary_decision"] == "KEEP_ONE_NARROWED_P5_FAMILY__NO_INDEPENDENT_P6"
assert p5["contract_status"] == "PASS_MINIMAL_DESIGN_CONTRACT_ONLY"
assert p5["gate0_status"] == "PASS_P5_ZERO_MODEL_GATE_0"
assert p5["gate1_status"] == "HOLD_P5_GATE_1_TRIGGER_NECESSITY"
assert p5["formal_task_ids_allocated"] == 0
assert p5["final_realization_status"] == "DEFERRED__NO_CURRENT_SKILL_NECESSITY"
assert p5["next_gate"] == "DEFERRED__NO_ACTIVE_GATE"
lgv03 = next(
    row
    for row in families
    if row["family_id"] == "G-AIR-LGV16B-003-BASIC-CURRENT-CABIN"
)
assert lgv03["construction_fixture_status"] == "PASS_LGV16B_003_MATCHED_CURRENT_CABIN_FIXTURES"
assert lgv03["gate0_status"] == "PASS_LGV16B_003_ZERO_MODEL_GATE_0"
assert lgv03["gate1_status"] == "HOLD_LGV16B_003_GATE_1_TRIGGER_NECESSITY"
assert lgv03["formal_task_ids_allocated"] == 0
assert (
    lgv03["final_realization_status"]
    == "DEFERRED__LEGAL_PATH_REPAIR_CONFIRMED_BUT_NO_GOVERNANCE_HEADROOM"
)
assert (
    lgv03["evaluator_rule_activation"]
    == "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY"
)
assert lgv03["next_gate"] == "DEFERRED__NO_ACTIVE_GATE"
for key in (
    "construction_fixture_path",
    "gate0_path",
    "gate1_path",
    "reference_skill_path",
):
    assert (HERE / lgv03[key]).resolve().is_file()
lgv04 = next(
    row
    for row in families
    if row["family_id"] == "G-AIR-LGV16B-004-ONE-WAY-SCOPE"
)
assert (
    lgv04["evidence_recovery_status"]
    == "PASS_HISTORICAL_EVIDENCE_RECOVERY_AND_PROVISIONAL_BOUNDARY"
)
assert (
    lgv04["family_boundary_status"]
    == "RESOLVED__MERGE_INTO_ONE_ENDPOINT_PRESERVATION_FAMILY"
)
assert (
    lgv04["evaluator_feasibility"]
    == "FEASIBLE__ONE_SHARED_ATTEMPT_LEVEL_ENDPOINT_RULE"
)
assert lgv04["formal_task_ids_allocated"] == 0
assert lgv04["portfolio_family_id"] == "G-AIR-ENDPOINT-PRESERVATION"
assert lgv04["trigger_topology"] == "APPENDED_REVERSE_RETURN"
assert lgv04["portfolio_decision"] == "MERGE_ONE_FAMILY_TWO_TRIGGER_TOPOLOGIES"
assert lgv04["contract_status"] == "PASS_MERGED_RECONSTRUCTION_DESIGN_CONTRACT_ONLY"
assert lgv04["shared_rule_id"] == "airline.flight_change.endpoint_preservation.v1"
assert lgv04["shared_rule_activation"] == "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY"
assert lgv04["gate0_status"] == "PASS_ENDPOINT_PRESERVATION_ZERO_MODEL_GATE_0"
assert lgv04["gate1_status"] == "HOLD_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY"
assert lgv04["final_realization_status"] == "DEFERRED__NO_CURRENT_SKILL_NECESSITY"
assert lgv04["next_gate"] == "DEFERRED__NO_ACTIVE_GATE"
assert (HERE / lgv04["evidence_recovery_path"]).resolve().is_file()
assert (HERE / lgv04["merge_decision_path"]).resolve().is_file()
assert (HERE / lgv04["contract_path"]).resolve().is_file()
assert (HERE / lgv04["gate0_path"]).resolve().is_file()
assert (HERE / lgv04["gate1_path"]).resolve().is_file()
assert (HERE / lgv04["reference_skill_path"]).resolve().is_file()
lga04 = next(
    row
    for row in families
    if row["family_id"] == "G-AIR-LGA04-DESTINATION-PRESERVATION"
)
assert lga04["evidence_recovery_status"] == "PASS_LGA04_HISTORICAL_EVIDENCE_RECOVERY_AND_BOUNDARY_NARROWING"
assert lga04["portfolio_family_id"] == "G-AIR-ENDPOINT-PRESERVATION"
assert lga04["trigger_topology"] == "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT"
assert lga04["family_boundary_status"] == "RESOLVED__MERGE_INTO_ONE_ENDPOINT_PRESERVATION_FAMILY"
assert lga04["portfolio_decision"] == "MERGE_ONE_FAMILY_TWO_TRIGGER_TOPOLOGIES"
assert lga04["portfolio_accounting"] == "ONE_FAMILY__REPORT_TRIGGER_TOPOLOGIES_SEPARATELY"
assert lga04["evaluator_feasibility"] == "FEASIBLE__ONE_SHARED_ATTEMPT_LEVEL_ENDPOINT_RULE"
assert lga04["contract_status"] == "PASS_MERGED_RECONSTRUCTION_DESIGN_CONTRACT_ONLY"
assert lga04["shared_rule_id"] == "airline.flight_change.endpoint_preservation.v1"
assert lga04["shared_rule_activation"] == "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY"
assert lga04["formal_task_ids_allocated"] == 0
assert lga04["gate0_status"] == "PASS_ENDPOINT_PRESERVATION_ZERO_MODEL_GATE_0"
assert lga04["gate1_status"] == "HOLD_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY"
assert lga04["final_realization_status"] == "DEFERRED__NO_CURRENT_SKILL_NECESSITY"
assert lga04["next_gate"] == "DEFERRED__NO_ACTIVE_GATE"
assert (HERE / lga04["evidence_recovery_path"]).resolve().is_file()
assert (HERE / lga04["contract_path"]).resolve().is_file()
assert (HERE / lga04["gate0_path"]).resolve().is_file()
assert (HERE / lga04["gate1_path"]).resolve().is_file()
assert (HERE / lga04["reference_skill_path"]).resolve().is_file()
assert sum(row.get("portfolio_family_id") == "G-AIR-ENDPOINT-PRESERVATION" for row in families) == 2
lga03 = next(
    row
    for row in families
    if row["family_id"] == "G-AIR-LGA03-INSURANCE-REASON-ELIGIBILITY"
)
assert lga03["lineage_count"] == 4
assert lga03["evidence_recovery_status"] == "PASS_LGA03_FOUR_LINEAGE_RECOVERY_AND_BOUNDARY_NARROWING"
assert lga03["historical_e0"] == "12_OF_12_VS"
assert lga03["direct_reference_repair"] == "6_OF_6_FOCAL_REPAIR"
assert lga03["covered_control_safety"] == "9_OF_9_FOCAL_CORRECT"
assert lga03["legal_task_success_redesign"] == "VERIFIED_TRANSFER_CS__FORBIDDEN_CANCELLATION_VS"
assert lga03["evaluator_feasibility"] == "FEASIBLE_WITH_NORMALIZED_REASON_CONTEXT_AND_COMPLETE_ELIGIBILITY_STATE"
assert lga03["contract_status"] == "PASS_LGA03_RECONSTRUCTION_DESIGN_CONTRACT_ONLY"
assert lga03["evaluator_rule_activation"] == "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY"
assert lga03["gate0_status"] == "PASS_LGA03_ZERO_MODEL_GATE_0"
assert lga03["gate1_status"] == "HOLD_LGA03_GATE_1_TRIGGER_NECESSITY"
assert lga03["controlled_reason_wording_status"] == "MIXED_OR_INCONCLUSIVE"
assert lga03["formal_task_ids_allocated"] == 0
assert lga03["final_realization_status"] == "DEFERRED__MECHANISM_CONFIRMED_BUT_HEADROOM_NOT_GENERALIZED"
assert lga03["next_gate"] == "DEFERRED__NO_ACTIVE_GATE"
assert (HERE / lga03["evidence_recovery_path"]).resolve().is_file()
assert (HERE / lga03["contract_path"]).resolve().is_file()
assert (HERE / lga03["gate0_path"]).resolve().is_file()
assert (HERE / lga03["gate1_path"]).resolve().is_file()
assert (HERE / lga03["reference_skill_path"]).resolve().is_file()
assert (HERE / lga03["controlled_reason_wording_path"]).resolve().is_file()
lga01 = next(
    row
    for row in families
    if row["family_id"] == "G-AIR-LGA01-FLOWN-SEGMENT-CANCELLATION"
)
assert lga01["lineage_count"] == 6
assert lga01["evidence_recovery_status"] == "PASS_LGA01_SIX_LINEAGE_RECOVERY_AND_BOUNDARY_NARROWING"
assert lga01["family_boundary_decision"] == "KEEP_ONE_FAMILY__NARROW_TO_LANDED_PREFIX_WITH_AVAILABLE_SUFFIX"
assert lga01["historical_e0"] == "18_OF_18_VS__17_OF_18_STRICT_FOCAL"
assert lga01["direct_reference_repair"] == "6_OF_6_FOCAL_REPAIR_AND_LEGAL_TRANSFER"
assert lga01["legal_side_control_evidence"] == "NO_MATCHED_BEHAVIORAL_NONTRIGGER_CONTROL_FOUND"
assert lga01["legal_task_success_redesign"] == "VERIFIED_TRANSFER_CS__FORBIDDEN_CANCELLATION_VS__EARLY_TRANSFER_CF"
assert lga01["evaluator_feasibility"] == "FEASIBLE_WITH_RESERVATION_AND_FLIGHT_INSTANCE_REPLAY_STATE"
assert lga01["contract_status"] == "PASS_LGA01_RECONSTRUCTION_DESIGN_CONTRACT_ONLY"
assert lga01["evaluator_rule_id"] == "airline.cancellation.flown_segment_boundary.v1"
assert lga01["evaluator_rule_activation"] == "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY"
assert lga01["gate0_status"] == "PASS_LGA01_ZERO_MODEL_GATE_0"
assert lga01["gate1_status"] == "HOLD_LGA01_GATE_1_TRIGGER_NECESSITY"
assert lga01["formal_task_ids_allocated"] == 0
assert lga01["final_realization_status"] == "DEFERRED__NO_CURRENT_SKILL_NECESSITY"
assert lga01["next_gate"] == "DEFERRED__NO_ACTIVE_GATE"
assert (HERE / lga01["evidence_recovery_path"]).resolve().is_file()
for key in ("contract_path", "gate0_path", "gate1_path", "reference_skill_path"):
    assert (HERE / lga01[key]).resolve().is_file()
assert all(row["formal_task_ids_allocated"] == 0 for row in families if row["priority"] == "P0")
assert all(row["formal_task_ids_allocated"] == 0 for row in families if row["priority"] == "P1")
p2 = next(row for row in families if row["priority"] == "P2")
assert p2["family_id"] == "C-AIR-P2-PRESERVED-SEGMENT-VALUATION"
assert p2["previous_family_id"] == "C-AIR-P2-P5-P6-PRESERVED-PRICING"
assert p2["evidence_recovery_status"] == "PASS_P2_TWO_LINEAGE_RECOVERY_AND_PURE_BOUNDARY_ISOLATION"
assert p2["family_boundary_decision"] == "NARROW_TO_PRESERVED_SAME_CABIN_SEGMENT_HISTORICAL_VALUATION"
assert p2["reference_repair_status"] == "NOT_VERIFIED_FOR_P2_ONLY"
assert p2["minimal_failure_control_pair"] == "FEASIBLE_BUT_CANCELLED__WOULD_DUPLICATE_V3_EE01"
assert p2["portfolio_relationship"] == "SUBSUMED_BY_V3_EE01_CHANNEL_CONDITIONED_SETTLEMENT"
assert p2["formal_task_ids_allocated"] == 0
assert p2["final_realization_status"] == "DROPPED_AS_STANDALONE__SUBSUMED_BY_V3_EE01"
assert p2["next_gate"] == "DROPPED__NO_ACTIVE_GATE"
assert (HERE / p2["evidence_recovery_path"]).resolve().is_file()
legacy_control = next(
    row for row in families if row["family_id"] == "C-RET-GENERIC-EXCHANGE-CONTROL"
)
assert legacy_control["formal_task_ids_allocated"] == 0
assert legacy_control["final_realization_status"] == (
    "DROPPED__NO_UNIQUE_CONTROL_VALUE_AND_NOISY_BASELINE"
)
assert legacy_control["next_gate"] == "DROPPED__NO_ACTIVE_GATE"
with ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/rebuild_lineage_backlog.csv')).open(encoding="utf-8") as handle:
    assert len(list(csv.DictReader(handle))) == 40
print("PASS_V2_REBUILD_FAMILY_REGISTRY_VALIDATION")
