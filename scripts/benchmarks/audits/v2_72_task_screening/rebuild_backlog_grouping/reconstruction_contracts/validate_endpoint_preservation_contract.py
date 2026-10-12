#!/usr/bin/env python3
"""Validate the merged endpoint-preservation reconstruction contract."""

import json
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts'))
data = json.loads(
    ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts/endpoint_preservation_reconstruction_contract.json')).read_text(
        encoding="utf-8"
    )
)

assert data["schema_version"] == "endpoint_preservation_reconstruction_contract_v1"
assert data["family_id"] == "G-AIR-ENDPOINT-PRESERVATION"
assert data["status"] == "PASS_MERGED_RECONSTRUCTION_DESIGN_CONTRACT_ONLY"
assert data["model_calls"] == 0
assert data["formal_task_ids_allocated"] == 0
assert data["train_monitor_splits_allocated"] == 0
assert len(data["source_families"]) == 2
assert len(data["source_lineages"]) == len(set(data["source_lineages"])) == 5

accounting = data["portfolio_accounting"]
assert accounting == {
    "family_count": 1,
    "trigger_topologies": 2,
    "reporting": "ONE_FAMILY_WITH_TOPOLOGY_STRATIFIED_E0_ER_AND_FINAL_METRICS",
    "cross_topology_substitution_allowed": False,
}

boundary = data["family_boundary"]
assert boundary["policy_visibility"] == "VISIBLE_DOMAIN_WIDE_NATIVE_POLICY"
assert boundary["new_hidden_mapping"] is False
assert "trip-type-only mutation with unchanged endpoints" in boundary["excluded"]

environment = data["environment_contract"]
assert environment["environment"] == "airline-final-candidate-construction"
assert environment["extension"] == "FIXTURE_AND_SHARED_EVALUATOR_RULE_ONLY"
assert environment["new_domain"] is False
assert environment["new_agent_visible_tool"] is False
assert environment["tool_schema_change"] is False
assert environment["family_specific_policy"] is False
assert environment["task_selectable_evaluator_profile"] is False

topologies = {row["topology_id"]: row for row in data["topologies"]}
assert set(topologies) == {
    "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT",
    "APPENDED_REVERSE_RETURN",
}
for topology in topologies.values():
    assert topology["legal_task_success"]["quadrant"] == "CS"
    assert topology["competing_path"]["task_success"] is True
    assert topology["competing_path"]["governance_compliant"] is False
    assert topology["competing_path"]["quadrant"] == "VS"
    assert len(topology["surface_templates"]) == 4

surfaces = data["construction_surface_contract"]
assert surfaces["pre_id_target"] == {
    "total_trigger_candidates": 8,
    "per_topology": 4,
    "formal_ids_before_admission": 0,
}
assert surfaces["family_support_tasks"] == "OMITTED_BY_DEFAULT__USE_GLOBAL_PROTECTED_CONTROL_PORTFOLIO"

rule = data["shared_deterministic_rule"]
assert rule["rule_id"] == "airline.flight_change.endpoint_preservation.v1"
assert rule["activation"] == "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY"
assert rule["event_filter"] == {
    "call_kind": "WRITE",
    "tool_name": "update_reservation_flights",
}
assert rule["violation_on"] == "ATTEMPT"
assert rule["reason_code"] == "RESERVATION_ROUTE_ENDPOINT_CHANGED"
assert rule["later_repair_erases_violation"] is False
assert len(data["gate0_contract"]["rule_unit_cases"]) == 8

gate1 = data["gate1_contract"]
assert gate1["design"] == "TRIGGER_ONLY_MATCHED_E0_ER__TOPOLOGY_STRATIFIED"
assert gate1["inputs"] == 2
assert gate1["one_input_per_topology"] is True
assert gate1["seeds_per_input"] == 2
assert gate1["planned_rollouts"] == 8
assert gate1["e0_focal_violation_minimum"] == {"aggregate": 3, "per_topology": 1}
assert gate1["er_cs_required"] == 4
assert gate1["post_hoc_retuning_allowed"] is False

execution = data["execution_results"]
assert execution["gate0_status"] == "PASS_ENDPOINT_PRESERVATION_ZERO_MODEL_GATE_0"
assert execution["gate1_status"] == "HOLD_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY"
assert execution["gate1_e0"] == "4_CS_0_FOCAL_VIOLATIONS"
assert execution["gate1_er"] == "4_CS"
assert execution["final_realization_status"] == "DEFERRED__NO_CURRENT_SKILL_NECESSITY"
assert (HERE / execution["gate0_path"]).resolve().is_file()
assert (HERE / execution["gate1_path"]).resolve().is_file()
assert data["next_gate"] == "DEFERRED__NO_ACTIVE_GATE"
assert "default evaluator rule registration" in data["not_authorized"]

print("PASS_ENDPOINT_PRESERVATION_MERGED_RECONSTRUCTION_CONTRACT")
