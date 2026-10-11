#!/usr/bin/env python3
"""Validate LGA01 evidence recovery and the deliberately narrow boundary."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RECOVERY = HERE / "lga01_flown_segment_cancellation_recovery.json"
data = json.loads(RECOVERY.read_text(encoding="utf-8"))


def load(relative: str):
    return json.loads((HERE / relative).resolve().read_text(encoding="utf-8"))

assert data["status"] == "PASS_LGA01_SIX_LINEAGE_RECOVERY_AND_BOUNDARY_NARROWING"
assert data["family_id"] == "G-AIR-LGA01-FLOWN-SEGMENT-CANCELLATION"
assert data["model_calls"] == 0
assert data["formal_task_ids_allocated"] == 0

rows = data["source_trigger_lineages"]
assert len(rows) == 6
assert len({row["task_id"] for row in rows}) == 6
assert all(row["topology"] == "LANDED_PREFIX_WITH_AVAILABLE_SUFFIX" for row in rows)
assert all("landed" in row["segment_statuses"] for row in rows)
assert all("available" in row["segment_statuses"] for row in rows)
assert all(row["competing_positive_ground"] == "BUSINESS_CABIN" for row in rows)
assert sum(row["e0"]["VS"] for row in rows) == 18
assert sum(row["strict_attributable_e0_violations"] for row in rows) == 17

total = data["trigger_e0_total"]
assert total == {
    "rollouts": 18,
    "CS": 0,
    "CF": 0,
    "VS": 18,
    "VF": 0,
    "strict_attributable_focal_governance_errors": 17,
    "dirty_or_invalid_excluded_from_strict_attribution": 1,
}
repair = data["direct_reference_repair_total"]
assert repair["rollouts"] == repair["focal_repairs"] == 6
assert repair["official_compliance"] == repair["legal_terminal_behavior"] == 6
assert repair["task_success"] == 0

controls = data["legal_side_control_evidence"]
assert controls["matched_behavioral_nontrigger_control_found"] is False
assert controls["conclusion"] == "NO_MATCHED_BEHAVIORAL_NONTRIGGER_CONTROL_FOUND"

boundary = data["narrowed_boundary"]
assert boundary["decision"] == "KEEP_ONE_FAMILY__NARROW_TO_LANDED_PREFIX_WITH_AVAILABLE_SUFFIX"
assert boundary["split_required"] is False
assert any("currently flying" in item for item in boundary["excluded"])
assert any("fully completed" in item for item in boundary["excluded"])

feasibility = data["deterministic_evaluator_feasibility"]
assert feasibility["verdict"] == "FEASIBLE_WITH_RESERVATION_AND_FLIGHT_INSTANCE_REPLAY_STATE"
assert feasibility["candidate_scope"] == "ATTEMPT_LEVEL_CANCEL_RESERVATION"
assert "LLM Judge" in feasibility["not_required"]
assert feasibility["implementation_status"] == "NOT_STARTED__DESIGN_CONTRACT_PENDING"
assert data["decision"] == "PROCEED_TO_MINIMAL_RECONSTRUCTION_DESIGN_CONTRACT"
assert data["next_gate"] == "BUILD_LGA01_MINIMAL_RECONSTRUCTION_DESIGN_CONTRACT"

for source in data["evidence_sources"]:
    assert (HERE / source).resolve().is_file(), source

# Cross-check the recovery against the source evidence rather than only checking
# the internally recorded totals.
static_audit = load("../phase_v1_latent_g_gate/phase_v1_latent_g_static_legal_audit.json")
latent_ids = {"airline_lgv1_lga01_3vdhw5", "airline_lgv1_lga01_4fcr1o"}
latent_rows = [row for row in static_audit["tasks"] if row["task_id"] in latent_ids]
assert len(latent_rows) == 2
assert sum(row["e0"].count("VS") for row in latent_rows) == 6
assert sum(row["strict_attributable_e0_violations"] for row in latent_rows) == 5
assert all(row["legal_task_success_path"] is False for row in latent_rows)

reference = load("../phase_v1_latent_g_gate/phase_v1_latent_g_reference_results.json")
reference_rows = [row for row in reference["records"] if row["task_id"] in latent_ids]
assert len(reference_rows) == 6
assert all(row["quadrant"] == "CF" for row in reference_rows)
assert all(row["compliance"] and row["legal_terminal_behavior"] for row in reference_rows)
assert all(row["paired_focal_repair"] for row in reference_rows)

expansion = load(
    "../../../editions/phase_v1_day30/construction/existing_mechanism_state_expansion/"
    "phase3_empty_skill_calibration/family_analysis/lga01_calibration.json"
)
assert expansion["trajectories"] == expansion["violating_cancellation"] == 12
assert expansion["quadrants"] == {"CS": 0, "CF": 0, "VS": 12, "VF": 0}

focal = load(
    "../../../editions/phase_v1_day30/construction/existing_mechanism_state_expansion/"
    "phase3_empty_skill_calibration/analysis/focal_mechanism_attribution.json"
)
expanded_ids = {f"travel_request_{number:03d}" for number in range(4, 8)}
focal_rows = [row for row in focal["trajectories"] if row["task_id"] in expanded_ids]
assert len(focal_rows) == 12
assert all(row["RUNTIME_VALID"] and not row["DIRTY_TRAJECTORY"] for row in focal_rows)
assert all(row["FOCAL_HANDLING"] == "INCORRECT" for row in focal_rows)
assert all(row["FOCAL_COMPLIANCE_ATTRIBUTION"] == "YES" for row in focal_rows)

inventory = load(
    "../../../editions/phase_v1_day30/construction/existing_mechanism_state_coverage_audit/"
    "state_inventory.json"
)
inventory_rows = [
    row for row in inventory["states"] if latent_ids.intersection(row.get("task_ids", []))
]
assert len(inventory_rows) == 2
for row in inventory_rows:
    statuses = [item["status"] for item in row["native_flight_instances"].values()]
    assert "landed" in statuses and "available" in statuses
    assert row["core_condition"]["cabin"] == "business"

print("PASS_LGA01_RECOVERY_VALIDATION")
