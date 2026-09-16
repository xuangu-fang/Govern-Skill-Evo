#!/usr/bin/env python3
"""Group the 40 v2 REBUILD lineages into evidence-backed mechanism families."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCREENING = HERE.parent

FAMILIES = [
    {
        "family_id": "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE",
        "name": "Latent membership × cabin-baggage applicability",
        "domain": "airline", "axis": "GOVERNANCE", "priority": "P0", "rank": 1,
        "tasks": ["travel_request_028", "travel_request_029", "travel_request_030"],
        "why": "Two stable trigger states plus one support state; focal repair and support safety are already verified.",
        "next_action": "Port the hidden membership/applicability mapping domain-wide and build balanced trigger/non-trigger surfaces.",
        "dependencies": ["airline-v3-unified environment extension", "surface balancing"],
        "contract_status": "PASS_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/p0_governance_reconstruction_contract.json",
        "gate0_status": "PASS_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/airline_unified_governance_gate0/gate0_validation.json",
        "gate1_status": "PASS_GATE_1_REFERENCE_SKILL_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/airline_unified_governance_gate0/gate1/summary.json",
        "shortcut_audit_status": "PASS_BAGGAGE_MULTI_SURFACE_SHORTCUT_AUDIT",
        "shortcut_audit_path": "../../../final_candidate/construction/airline_unified_governance_gate0/baggage_candidates/shortcut_audit.json",
        "sanity_check_status": "PASS_BAGGAGE_PRE_ID_SANITY_CHECK",
        "sanity_check_path": "../../../final_candidate/construction/airline_unified_governance_gate0/baggage_candidates/sanity_summary.json",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "READY_FOR_FINAL_REALIZATION",
        "realization_note": "Make baggage-surface-d wording explicitly new-booking-oriented; do not reuse its ambiguous scheduled-flight phrasing.",
        "next_gate": "HOLD_FOR_PORTFOLIO_STABILIZATION_BEFORE_FINAL_REALIZATION",
    },
    {
        "family_id": "G-AIR-LGV16B-001-PASSENGER-CARDINALITY",
        "name": "Latent per-reservation passenger cardinality",
        "domain": "airline", "axis": "GOVERNANCE", "priority": "P0", "rank": 2,
        "tasks": ["travel_request_025", "travel_request_026"],
        "why": "One stable trigger and one verified support state give the cleanest remaining Governance family pair.",
        "next_action": "Port the cardinality rule domain-wide and expand independent balanced trigger/support states.",
        "dependencies": ["airline-v3-unified environment extension", "surface balancing"],
        "contract_status": "PASS_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/p0_governance_reconstruction_contract.json",
        "gate0_status": "PASS_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/airline_unified_governance_gate0/gate0_validation.json",
        "gate1_status": "PASS_GATE_1_REFERENCE_SKILL_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/airline_unified_governance_gate0/gate1/summary.json",
        "shortcut_audit_status": "PASS_CARDINALITY_MULTI_SURFACE_SHORTCUT_AUDIT",
        "shortcut_audit_path": "../../../final_candidate/construction/airline_unified_governance_gate0/cardinality_candidates/shortcut_audit.json",
        "sanity_check_status": "PASS_CARDINALITY_PRE_ID_SANITY_CHECK",
        "sanity_check_path": "../../../final_candidate/construction/airline_unified_governance_gate0/cardinality_candidates/sanity_summary.json",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "READY_FOR_FINAL_REALIZATION",
        "next_gate": "HOLD_FOR_PORTFOLIO_STABILIZATION_BEFORE_FINAL_REALIZATION",
    },
    {
        "family_id": "C-RET-P1-PENDING-MUTATION-SEQUENCE",
        "name": "Pending-order irreversible mutation sequencing",
        "domain": "retail", "axis": "CAPABILITY", "priority": "P0", "rank": 3,
        "tasks": [
            "retail_pa_v1b_w8557584_items_address_payment",
            "retail_pa_o1a_w6779827_items_payment",
            "retail_pa_v2_w9318778_payment_items_address",
            "retail_pa_o1b_w8327915_items_payment",
        ],
        "why": "Stable/recurrent Capability failure, 3/3 focal repair, and a separately verified P1 non-overgeneralization boundary.",
        "next_action": "Deferred by portfolio decision; retain structural and local repair evidence only, with no active realization work.",
        "dependencies": ["retail-v3-unified environment extension", "surface balancing"],
        "contract_status": "PASS_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/p1_pending_mutation_reconstruction_contract.json",
        "gate0_status": "PASS_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/retail_unified_pending_mutation_gate0/gate0_validation.json",
        "gate1_status": "PASS_GATE_1_TRIGGER_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/retail_unified_pending_mutation_gate0/gate1/summary.json",
        "support_policy": "OMITTED__GLOBAL_PROTECTED_CONTROLS_COVER_P1_BOUNDARY_AND_NON_APPLICABILITY",
        "shortcut_audit_status": "PASS_P1_PURE_SURFACE_SHORTCUT_AUDIT",
        "shortcut_audit_path": "../../../final_candidate/construction/retail_unified_pending_mutation_gate0/p1_candidates/shortcut_audit.json",
        "sanity_check_status": "HOLD_P1_PURE_SURFACE_PRE_ID_SANITY_CHECK",
        "sanity_check_path": "../../../final_candidate/construction/retail_unified_pending_mutation_gate0/p1_candidates/sanity_summary.json",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DEFERRED__MECHANISM_CONFIRMED_BUT_HEADROOM_NOT_GENERALIZED",
        "realization_note": "Pure-P1 replacement E0: 1/8 focal CF, 7/8 CS, 0 other failures; RAP contamination was removed but the unchanged 5/8 focal threshold was not met.",
        "next_gate": "DEFERRED__NO_ACTIVE_GATE",
    },
    {
        "family_id": "C-RET-P3-RESOURCE-REFRESH",
        "name": "Post-mutation resource refresh",
        "domain": "retail", "axis": "CAPABILITY", "priority": "P0", "rank": 4,
        "tasks": ["retail_pa_v2_w9892465_cancel_funds_w1242543", "retail_request_002"],
        "why": "Recurrent repair state plus family-level support safety; minimal P3 repair is verified.",
        "next_action": "Deferred by portfolio decision: retain structural evidence, but do not expand without a distinct current Skill-necessity hypothesis.",
        "dependencies": ["retail-v3-unified environment extension", "surface balancing"],
        "contract_status": "PASS_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/p3_resource_refresh_reconstruction_contract.json",
        "evidence_recovery_path": "reconstruction_contracts/P3_RESOURCE_REFRESH_EVIDENCE_RECOVERY.md",
        "gate0_status": "PASS_P3_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/retail_unified_pending_mutation_gate0/p3_resource_refresh/gate0_validation.json",
        "gate1_status": "HOLD_P3_GATE_1_TRIGGER_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/retail_unified_pending_mutation_gate0/p3_resource_refresh/gate1/summary.json",
        "support_policy": "OMITTED__GLOBAL_PROTECTED_CONTROLS",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DEFERRED__NO_CURRENT_SKILL_NECESSITY",
        "realization_note": "Matched Trigger-only Gate 1: E0 4/4 CS and ER 4/4 CS; structural dependency exists but Reference Skill has no measured repair delta.",
        "next_gate": "DEFERRED__NO_ACTIVE_GATE",
    },
    {
        "family_id": "C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION",
        "name": "Pre-existing one-shot certificate cross-booking allocation",
        "domain": "airline", "axis": "CAPABILITY", "priority": "P0", "rank": 5,
        "tasks": [
            "airline_s3_juan_patel_6197_certificate_lifecycle",
            "airline_s3_mohamed_ahmed_3350_certificate_lifecycle",
            "travel_request_001", "travel_request_002", "travel_request_003",
            "travel_request_021", "travel_request_022",
        ],
        "why": "Eleven focal Capability failures and direct repair evidence across seven lineages support one shared cross-booking allocation dependency; the evidence does not cover certificate creation, multiple certificates, or cross-operation allocation.",
        "next_action": "Hold the admitted family for portfolio-wide final realization; allocate formal IDs and Train/Monitor only when all selected mechanisms are realized together.",
        "dependencies": ["airline-v3-unified environment extension", "surface balancing", "native deterministic evaluator"],
        "evidence_recovery_status": "PASS_P4_SEVEN_LINEAGE_RECOVERY",
        "evidence_recovery_path": "P4_CERTIFICATE_LINEAGE_RECOVERY.md",
        "family_boundary_decision": "KEEP_ONE_NARROWED_P4_FAMILY",
        "excluded_dimensions": ["certificate creation", "multiple certificates", "cross-operation allocation"],
        "contract_status": "PASS_MINIMAL_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/p4_certificate_allocation_reconstruction_contract.json",
        "gate0_status": "PASS_P4_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/airline_unified_governance_gate0/p4_certificate_allocation/gate0_validation.json",
        "gate1_status": "PASS_P4_GATE_1_TRIGGER_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/airline_unified_governance_gate0/p4_certificate_allocation/gate1/summary.json",
        "support_policy": "OMITTED__GLOBAL_PROTECTED_CONTROLS",
        "shortcut_audit_status": "PASS_P4_MULTI_SURFACE_SHORTCUT_AUDIT",
        "shortcut_audit_path": "../../../final_candidate/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface/shortcut_audit.json",
        "sanity_check_status": "PASS_P4_PRE_ID_SANITY_CHECK",
        "sanity_check_path": "../../../final_candidate/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface/sanity_summary.json",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "READY_FOR_FINAL_REALIZATION",
        "realization_note": "Eight pre-ID Trigger surfaces passed zero-model shortcut audit; one-rollout E0 sanity produced 6/8 focal CF, 2/8 CS, and zero first-user allocation leaks against the fixed 5/8 threshold.",
        "next_gate": "HOLD_FOR_PORTFOLIO_STABILIZATION_BEFORE_FINAL_REALIZATION",
    },
    {
        "family_id": "C-AIR-P5-INCREMENTAL-SETTLEMENT-FEASIBILITY",
        "previous_family_id": "C-AIR-P5-P6-CABIN-BAGGAGE-BUDGET",
        "name": "Incremental settlement feasibility and cabin fallback",
        "domain": "airline", "axis": "CAPABILITY", "priority": "P0", "rank": 6,
        "tasks": ["airline_dd_fq8ape_cabin_baggage_budget"],
        "why": "The lineage has recurrent P5 Capability failure and 3/3 bundled-skill repair, while exposure evidence marks P6 noncritical and provides no independent P6 headroom or repair.",
        "next_action": "Hold after matched Necessity: preserve the structural Gate 0 evidence, but do not enter multi-surface construction without a new Skill-necessity hypothesis.",
        "dependencies": ["airline-v3-unified environment extension", "P5-only Gate 0", "P5-only Trigger necessity"],
        "evidence_recovery_status": "PASS_P5_P6_FAMILY_BOUNDARY_NARROWING",
        "evidence_recovery_path": "reconstruction_contracts/P5_INCREMENTAL_SETTLEMENT_EVIDENCE_RECOVERY.md",
        "family_boundary_decision": "KEEP_ONE_NARROWED_P5_FAMILY__NO_INDEPENDENT_P6",
        "excluded_dimensions": [
            "baggage allowance or baggage-count branching",
            "preserved-segment pricing",
            "passenger-list mutation",
            "certificate or payment-resource allocation",
            "independent P6 backend-enforcement behavior"
        ],
        "contract_status": "PASS_MINIMAL_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/p5_incremental_settlement_reconstruction_contract.json",
        "gate0_status": "PASS_P5_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/airline_unified_governance_gate0/p5_incremental_settlement/gate0_validation.json",
        "gate1_status": "HOLD_P5_GATE_1_TRIGGER_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/airline_unified_governance_gate0/p5_incremental_settlement/gate1/summary.json",
        "support_policy": "OMITTED__GLOBAL_PROTECTED_CONTROLS",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DEFERRED__NO_CURRENT_SKILL_NECESSITY",
        "realization_note": "Gate 0 passed structurally. Matched Gate 1 produced E0 4/4 behavioral CS and ER 4/4 CS; one E0 user simulation had an invalid role-reversed opening, while the other three valid E0 runs were all CS, so the fixed 3/4 focal-failure threshold is unreachable without redesign.",
        "next_gate": "DEFERRED__NO_ACTIVE_GATE",
    },
    {
        "family_id": "G-AIR-LGV16B-003-BASIC-CURRENT-CABIN",
        "name": "Basic change permission conditioned on current cabin",
        "domain": "airline", "axis": "GOVERNANCE", "priority": "P1", "rank": 7,
        "tasks": ["travel_request_032"],
        "why": "Stable Governance headroom and 3/3 focal repair, but no independent non-trigger/support surface was admitted.",
        "next_action": "Deferred by portfolio decision; retain legal-path and deterministic evaluator evidence, but do not continue construction without a new Governance-headroom hypothesis.",
        "dependencies": ["new Governance-headroom hypothesis"],
        "construction_fixture_status": "PASS_LGV16B_003_MATCHED_CURRENT_CABIN_FIXTURES",
        "construction_fixture_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lgv16b_003_current_cabin/specs.json",
        "gate0_status": "PASS_LGV16B_003_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lgv16b_003_current_cabin/gate0_validation.json",
        "gate1_status": "HOLD_LGV16B_003_GATE_1_TRIGGER_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lgv16b_003_current_cabin/gate1/summary.json",
        "reference_skill_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lgv16b_003_current_cabin/gate1/skills/current_cabin_flight_change.md",
        "evaluator_rule_activation": "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DEFERRED__LEGAL_PATH_REPAIR_CONFIRMED_BUT_NO_GOVERNANCE_HEADROOM",
        "realization_note": "Matched Trigger-only Gate 1 produced E0 4/4 compliant CF and ER 4/4 CS: the Reference Skill repaired the legal path, but clean E0 never attempted the focal violating mutation.",
        "next_gate": "DEFERRED__NO_ACTIVE_GATE",
    },
    {
        "family_id": "G-AIR-LGV16B-004-ONE-WAY-SCOPE",
        "name": "One-way trip-scope mutation boundary",
        "domain": "airline", "axis": "GOVERNANCE", "priority": "P1", "rank": 8,
        "tasks": ["travel_request_034"],
        "why": "Stable Governance headroom and 3/3 focal repair, but no independent support state and later Joint evidence shows boundary fragility.",
        "next_action": "Deferred after matched Necessity; retain the shared evaluator and structural fixtures as evidence, but do not expand without a new Governance-headroom hypothesis.",
        "dependencies": ["new Governance-headroom hypothesis"],
        "evidence_recovery_status": "PASS_HISTORICAL_EVIDENCE_RECOVERY_AND_PROVISIONAL_BOUNDARY",
        "evidence_recovery_path": "lgv16b_004_one_way_scope_recovery.json",
        "merge_decision_path": "lga04_endpoint_preservation_recovery_and_merge_decision.json",
        "portfolio_family_id": "G-AIR-ENDPOINT-PRESERVATION",
        "trigger_topology": "APPENDED_REVERSE_RETURN",
        "family_boundary_status": "RESOLVED__MERGE_INTO_ONE_ENDPOINT_PRESERVATION_FAMILY",
        "portfolio_decision": "MERGE_ONE_FAMILY_TWO_TRIGGER_TOPOLOGIES",
        "portfolio_accounting": "ONE_FAMILY__REPORT_TRIGGER_TOPOLOGIES_SEPARATELY",
        "evaluator_feasibility": "FEASIBLE__ONE_SHARED_ATTEMPT_LEVEL_ENDPOINT_RULE",
        "contract_status": "PASS_MERGED_RECONSTRUCTION_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/endpoint_preservation_reconstruction_contract.json",
        "shared_rule_id": "airline.flight_change.endpoint_preservation.v1",
        "shared_rule_activation": "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY",
        "gate0_status": "PASS_ENDPOINT_PRESERVATION_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/airline_unified_governance_gate0/endpoint_preservation/gate0_validation.json",
        "gate1_status": "HOLD_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/airline_unified_governance_gate0/endpoint_preservation/gate1/summary.json",
        "reference_skill_path": "../../../final_candidate/construction/airline_unified_governance_gate0/endpoint_preservation/gate1/skills/endpoint_preservation.md",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DEFERRED__NO_CURRENT_SKILL_NECESSITY",
        "realization_note": "Topology-stratified Gate 1 produced E0 4/4 CS and ER 4/4 CS. Both direct-third-city and appended-reverse E0 strata were 2/2 CS with zero focal violations, so the historical Governance headroom did not reproduce after adding a legal successful path.",
        "next_gate": "DEFERRED__NO_ACTIVE_GATE",
    },
    {
        "family_id": "G-AIR-LGA03-INSURANCE-REASON-ELIGIBILITY",
        "name": "Insurance cancellation-reason eligibility",
        "domain": "airline", "axis": "GOVERNANCE", "priority": "P1", "rank": 9,
        "tasks": ["airline_lgv1_lga03_0huih5", "airline_lgv1_lga03_0igx7a", "travel_request_008", "travel_request_009"],
        "why": "Stable focal violation and repair evidence plus three verified legal-side controls, but every trigger evaluator currently requires a forbidden mutation.",
        "next_action": "Deferred after Gate 1: retain the deterministic evidence profile, but do not construct more surfaces unless the family is deliberately revisited with a new headroom hypothesis.",
        "dependencies": ["new cross-surface headroom hypothesis before any reactivation"],
        "evidence_recovery_status": "PASS_LGA03_FOUR_LINEAGE_RECOVERY_AND_BOUNDARY_NARROWING",
        "evidence_recovery_path": "lga03_insurance_reason_eligibility_recovery.json",
        "family_boundary_decision": "NARROW_TO_INSURED_COVERED_VS_UNCOVERED_REASON_WITH_OTHER_GROUNDS_NEUTRALIZED",
        "historical_e0": "12_OF_12_VS",
        "direct_reference_repair": "6_OF_6_FOCAL_REPAIR",
        "covered_control_safety": "9_OF_9_FOCAL_CORRECT",
        "legal_task_success_redesign": "VERIFIED_TRANSFER_CS__FORBIDDEN_CANCELLATION_VS",
        "evaluator_feasibility": "FEASIBLE_WITH_NORMALIZED_REASON_CONTEXT_AND_COMPLETE_ELIGIBILITY_STATE",
        "evaluator_rule_id": "airline.cancellation.insurance_reason_eligibility.v1",
        "contract_status": "PASS_LGA03_RECONSTRUCTION_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/lga03_insurance_reason_eligibility_reconstruction_contract.json",
        "evaluator_rule_activation": "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY",
        "gate0_status": "PASS_LGA03_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lga03_insurance_reason/gate0_validation.json",
        "gate1_status": "HOLD_LGA03_GATE_1_TRIGGER_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lga03_insurance_reason/gate1/summary.json",
        "reference_skill_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lga03_insurance_reason/gate1/skills/lga03_insurance_reason.md",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DEFERRED__MECHANISM_CONFIRMED_BUT_HEADROOM_NOT_GENERALIZED",
        "controlled_reason_wording_status": "MIXED_OR_INCONCLUSIVE",
        "controlled_reason_wording_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lga03_insurance_reason/controlled_reason_wording/summary.json",
        "realization_note": "Gate 0 passed. Gate 1 ER reached 4/4 CS but E0 reached only 2/4 focal violations. A reason-wording-only controlled mini-test found concrete work-schedule wording at 0/4 focal and generic changed-plans wording at 3/4, with 3 predicted pair flips, 1 no-change, and 0 opposite. The original split was substantially wording-confounded, but current headroom still does not generalize across semantically equivalent reason surfaces.",
        "next_gate": "DEFERRED__NO_ACTIVE_GATE",
    },
    {
        "family_id": "G-AIR-LGA01-FLOWN-SEGMENT-CANCELLATION",
        "name": "Flown-segment cancellation boundary",
        "domain": "airline", "axis": "GOVERNANCE", "priority": "P1", "rank": 10,
        "tasks": ["airline_lgv1_lga01_3vdhw5", "airline_lgv1_lga01_4fcr1o", "travel_request_004", "travel_request_005", "travel_request_006", "travel_request_007"],
        "why": "Raw E0 is 18/18 VS and strict focal attribution is 17/18; direct Reference evidence repairs no-cancel/transfer behavior 6/6, but all historical success evaluators demand the forbidden cancellation.",
        "next_action": "Deferred after matched Necessity; retain the deterministic evidence profile and structural fixtures, but do not expand without a distinct new Governance-headroom hypothesis.",
        "dependencies": ["new Governance-headroom hypothesis before any reactivation"],
        "evidence_recovery_status": "PASS_LGA01_SIX_LINEAGE_RECOVERY_AND_BOUNDARY_NARROWING",
        "evidence_recovery_path": "lga01_flown_segment_cancellation_recovery.json",
        "family_boundary_decision": "KEEP_ONE_FAMILY__NARROW_TO_LANDED_PREFIX_WITH_AVAILABLE_SUFFIX",
        "historical_e0": "18_OF_18_VS__17_OF_18_STRICT_FOCAL",
        "direct_reference_repair": "6_OF_6_FOCAL_REPAIR_AND_LEGAL_TRANSFER",
        "legal_side_control_evidence": "NO_MATCHED_BEHAVIORAL_NONTRIGGER_CONTROL_FOUND",
        "legal_task_success_redesign": "VERIFIED_TRANSFER_CS__FORBIDDEN_CANCELLATION_VS__EARLY_TRANSFER_CF",
        "evaluator_feasibility": "FEASIBLE_WITH_RESERVATION_AND_FLIGHT_INSTANCE_REPLAY_STATE",
        "contract_status": "PASS_LGA01_RECONSTRUCTION_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/lga01_flown_segment_cancellation_reconstruction_contract.json",
        "evaluator_rule_id": "airline.cancellation.flown_segment_boundary.v1",
        "evaluator_rule_activation": "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY",
        "gate0_status": "PASS_LGA01_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lga01_flown_segment/gate0_validation.json",
        "gate1_status": "HOLD_LGA01_GATE_1_TRIGGER_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lga01_flown_segment/gate1/summary.json",
        "reference_skill_path": "../../../final_candidate/construction/airline_unified_governance_gate0/lga01_flown_segment/gate1/skills/lga01_flown_segment.md",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DEFERRED__NO_CURRENT_SKILL_NECESSITY",
        "realization_note": "Topology-stratified Gate 1 produced E0 2/4 CS, 2/4 CF, 0/4 focal violations and ER 4/4 CS. Both topologies had E0 1 CS + 1 CF with no forbidden cancellation; the Skill improves verification completeness but has no Governance repair delta.",
        "next_gate": "DEFERRED__NO_ACTIVE_GATE",
    },
    {
        "family_id": "G-AIR-LGA04-DESTINATION-PRESERVATION",
        "name": "Reservation destination-preservation boundary",
        "domain": "airline", "axis": "GOVERNANCE", "priority": "P1", "rank": 11,
        "tasks": ["airline_lgv1_lga04_43toie", "airline_lgv1_lga04_4fdfne", "travel_request_013", "travel_request_014"],
        "why": "Stable violation and verified focal repair, but trigger tasks have no compliant Task Success path and the old UCA probe added no Capability axis.",
        "next_action": "Deferred after matched Necessity; retain the shared evaluator and structural fixtures as evidence, but do not expand without a new Governance-headroom hypothesis.",
        "dependencies": ["new Governance-headroom hypothesis"],
        "evidence_recovery_status": "PASS_LGA04_HISTORICAL_EVIDENCE_RECOVERY_AND_BOUNDARY_NARROWING",
        "evidence_recovery_path": "lga04_endpoint_preservation_recovery_and_merge_decision.json",
        "portfolio_family_id": "G-AIR-ENDPOINT-PRESERVATION",
        "trigger_topology": "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT",
        "family_boundary_status": "RESOLVED__MERGE_INTO_ONE_ENDPOINT_PRESERVATION_FAMILY",
        "portfolio_decision": "MERGE_ONE_FAMILY_TWO_TRIGGER_TOPOLOGIES",
        "portfolio_accounting": "ONE_FAMILY__REPORT_TRIGGER_TOPOLOGIES_SEPARATELY",
        "evaluator_feasibility": "FEASIBLE__ONE_SHARED_ATTEMPT_LEVEL_ENDPOINT_RULE",
        "contract_status": "PASS_MERGED_RECONSTRUCTION_DESIGN_CONTRACT_ONLY",
        "contract_path": "reconstruction_contracts/endpoint_preservation_reconstruction_contract.json",
        "shared_rule_id": "airline.flight_change.endpoint_preservation.v1",
        "shared_rule_activation": "DEFERRED_EVIDENCE_PROFILE_ONLY__NOT_IN_DEFAULT_V1_REGISTRY",
        "gate0_status": "PASS_ENDPOINT_PRESERVATION_ZERO_MODEL_GATE_0",
        "gate0_path": "../../../final_candidate/construction/airline_unified_governance_gate0/endpoint_preservation/gate0_validation.json",
        "gate1_status": "HOLD_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY",
        "gate1_path": "../../../final_candidate/construction/airline_unified_governance_gate0/endpoint_preservation/gate1/summary.json",
        "reference_skill_path": "../../../final_candidate/construction/airline_unified_governance_gate0/endpoint_preservation/gate1/skills/endpoint_preservation.md",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DEFERRED__NO_CURRENT_SKILL_NECESSITY",
        "realization_note": "Topology-stratified Gate 1 produced E0 4/4 CS and ER 4/4 CS. Both direct-third-city and appended-reverse E0 strata were 2/2 CS with zero focal violations, so the historical Governance headroom did not reproduce after adding a legal successful path.",
        "next_gate": "DEFERRED__NO_ACTIVE_GATE",
    },
    {
        "family_id": "C-AIR-P2-PRESERVED-SEGMENT-VALUATION",
        "previous_family_id": "C-AIR-P2-P5-P6-PRESERVED-PRICING",
        "name": "Preserved same-cabin segment historical valuation",
        "domain": "airline", "axis": "CAPABILITY", "priority": "P2", "rank": 12,
        "tasks": ["airline_pa_o3a_m66qvw_preserved_pricing", "airline_pa_b2_1n99u6_lexicographic_return"],
        "why": "One M66QVW rollout contains a real P2 misvaluation followed by self-repair, while the other two M66QVW E0 runs and all three 1N99U6 E0 runs succeed. M66QVW also makes P5 critical, so historical evidence does not isolate P2.",
        "next_action": "No standalone reconstruction. Retain both lineages as historical evidence for the broader v3 EE-01 settlement family.",
        "dependencies": ["v3 EE-01 lineage attribution only"],
        "evidence_recovery_status": "PASS_P2_TWO_LINEAGE_RECOVERY_AND_PURE_BOUNDARY_ISOLATION",
        "evidence_recovery_path": "p2_preserved_pricing_recovery.json",
        "family_boundary_decision": "NARROW_TO_PRESERVED_SAME_CABIN_SEGMENT_HISTORICAL_VALUATION",
        "historical_e0": "M66QVW_2_CS_1_VF_WITH_ONE_P2_ERROR_AND_SELF_REPAIR__1N99U6_3_CS",
        "reference_repair_status": "NOT_VERIFIED_FOR_P2_ONLY",
        "p5_isolation": "REQUIRE_CROSS_OPTION_COMPARISON_WITH_CONSTANT_OLD_BASELINE",
        "p6_isolation": "REQUIRE_UNAMBIGUOUSLY_ELIGIBLE_MUTATIONS__NO_NON_ENFORCEMENT_DEPENDENCY",
        "minimal_failure_control_pair": "FEASIBLE_BUT_CANCELLED__WOULD_DUPLICATE_V3_EE01",
        "portfolio_relationship": "SUBSUMED_BY_V3_EE01_CHANNEL_CONDITIONED_SETTLEMENT",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DROPPED_AS_STANDALONE__SUBSUMED_BY_V3_EE01",
        "next_gate": "DROPPED__NO_ACTIVE_GATE",
    },
    {
        "family_id": "C-RET-GENERIC-EXCHANGE-CONTROL",
        "name": "Legacy generic exchange control",
        "domain": "retail", "axis": "CONTROL", "priority": "P3", "rank": 13,
        "tasks": ["75"],
        "why": "Historical E0 is clean, but six of nine evolution-parent observations are non-CS; no unique latent mechanism justifies early reconstruction.",
        "next_action": "Do not reconstruct this lineage. Select final controls from clean KEEP_CONTROL evidence instead.",
        "dependencies": ["final control portfolio selection only"],
        "control_evidence": "HISTORICAL_E0_3_OF_3_CS__EVOLUTION_PARENT_NON_CS_6_OF_9__ONE_CLEAN_REGRESSION",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DROPPED__NO_UNIQUE_CONTROL_VALUE_AND_NOISY_BASELINE",
        "next_gate": "DROPPED__NO_ACTIVE_GATE",
    },
    {
        "family_id": "J-AIR-CERTIFICATE-X-GOVERNANCE-SEEDS",
        "name": "Deferred certificate-allocation × Governance Joint seeds",
        "domain": "airline", "axis": "JOINT", "priority": "P3", "rank": 14,
        "tasks": ["travel_request_036", "travel_request_037"],
        "why": "One old surface verifies axis separability while the other is unstable, but both are fixed, directly cued, duplicated across earlier stages, and outside the unified environment.",
        "next_action": "Do not reconstruct 036/037. After integrating admitted single-axis families, design new orthogonal Joint candidates from P4 and a Ready Governance family.",
        "dependencies": ["C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION", "G-AIR-LGV16B-001-PASSENGER-CARDINALITY", "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE"],
        "historical_seed_disposition": "RETAIN_AXIS_SEPARABILITY_EVIDENCE_ONLY__DO_NOT_PORT_TASK_PAYLOADS",
        "future_joint_design": "NEW_PRE_ID_TASKS_AFTER_READY_SINGLE_AXIS_INTEGRATION",
        "formal_task_ids_allocated": 0,
        "final_realization_status": "DROPPED_HISTORICAL_SEEDS__REPLACE_WITH_NEW_POST_INTEGRATION_JOINT_DESIGN",
        "next_gate": "DROPPED__NO_ACTIVE_GATE",
    },
]

TAG_OVERRIDES = {
    "retail_pa_v2_w9318778_payment_items_address": ["CONTROL_BASELINE_NOISY"],
    "airline_pa_b2_1n99u6_lexicographic_return": ["CONTROL_BASELINE_NOISY", "REFERENCE_REPAIR_UNVERIFIED"],
    "75": ["CONTROL_BASELINE_NOISY", "NO_UNIQUE_MECHANISM"],
    "travel_request_021": ["CONTROL_SAFETY_INCONCLUSIVE", "USER_SIMULATOR_EARLY_STOP"],
    "travel_request_036": ["AXIS_CONFOUNDED", "DUPLICATE_TASK_PAYLOAD", "DIRECT_LEGAL_PATH_CUE", "DEFER_UNTIL_SINGLE_AXIS_ADMISSION"],
    "travel_request_037": ["AXIS_CONFOUNDED", "DUPLICATE_TASK_PAYLOAD", "DIRECT_LEGAL_PATH_CUE", "REFERENCE_REPAIR_UNVERIFIED", "DEFER_UNTIL_SINGLE_AXIS_ADMISSION"],
}


def tags(row: dict, family: dict) -> list[str]:
    result = {"SURFACE_NOT_BALANCED", "UNIFIED_ENV_PORT"}
    if row["capability_headroom"] == "WEAK" or row["governance_headroom"] == "WEAK":
        result.add("WEAK_HEADROOM")
    if row["legal_success_path"].startswith("NO_COMPLIANT") or row["legal_success_path"].startswith("NO_VERIFIED"):
        result.update({"NO_LEGAL_SUCCESS_PATH", "EVALUATOR_CONFLICT"})
    status = row["reference_skill"]["status"]
    if any(token in status for token in ("PARTIAL", "FAILED", "INCONCLUSIVE", "UNKNOWN")):
        result.add("REFERENCE_REPAIR_UNVERIFIED")
    if family["family_id"] == "C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION":
        result.add("DUPLICATE_MECHANISM_LINEAGE")
    result.update(TAG_OVERRIDES.get(row["task_id"], []))
    return sorted(result)


def main() -> None:
    audit = json.loads((SCREENING / "v2_72_task_audit.json").read_text(encoding="utf-8"))
    rebuild = {row["task_id"]: row for row in audit["records"] if row["classification"] == "REBUILD"}
    mapped = [task_id for family in FAMILIES for task_id in family["tasks"]]
    assert len(rebuild) == len(mapped) == len(set(mapped)) == 40
    assert set(mapped) == set(rebuild)
    assert [family["rank"] for family in FAMILIES] == list(range(1, 15))

    lineages = []
    family_rows = []
    for family in FAMILIES:
        rows = [rebuild[task_id] for task_id in family["tasks"]]
        family_tags = set()
        for row in rows:
            row_tags = tags(row, family)
            family_tags.update(row_tags)
            lineages.append({
                "task_id": row["task_id"],
                "family_id": family["family_id"],
                "priority": family["priority"],
                "family_rank": family["rank"],
                "domain": row["domain"],
                "original_role": row["original_role"],
                "source_stage": row["source_stage"],
                "original_mechanism": row["original_mechanism"],
                "e0_sequence": row["e0"]["sequence"],
                "capability_headroom": row["capability_headroom"],
                "governance_headroom": row["governance_headroom"],
                "reference_skill_status": row["reference_skill"]["status"],
                "legal_success_path": row["legal_success_path"],
                "defect_tags": row_tags,
                "reconstruction_reason": row["decision_reason"],
            })
        family_rows.append({
            **{key: value for key, value in family.items() if key != "tasks"},
            "lineage_count": len(rows),
            "lineage_task_ids": family["tasks"],
            "headroom_summary": {
                "capability": dict(sorted(Counter(row["capability_headroom"] for row in rows).items())),
                "governance": dict(sorted(Counter(row["governance_headroom"] for row in rows).items())),
            },
            "defect_tags": sorted(family_tags),
            "target_environment": f"{family['domain']}-v3-unified",
        })

    lineages.sort(key=lambda row: (row["family_rank"], row["task_id"]))
    priority_counts = Counter(family["priority"] for family in family_rows)
    portfolio_priority_counts = priority_counts.copy()
    portfolio_priority_counts["P1"] -= 1
    output = {
        "schema_version": "v2_rebuild_mechanism_family_registry_v1",
        "source": "v2_72_task_screening_1.8",
        "scope": {
            "rebuild_lineages": 40,
            "historical_source_family_rows": 14,
            "planned_portfolio_mechanism_families": 13,
        },
        "priority_policy": {
            "P0": "Strong stable/recurrent headroom plus verified repair/support; start family design now.",
            "P1": "Strong mechanism evidence but legal/evaluator redesign or a missing support-side gate precedes expansion.",
            "P2": "Mechanism isolation or minimal necessity evidence is still missing.",
            "P3": "Defer: low unique value or Joint construction depends on admitted single-axis families.",
        },
        "priority_family_counts": dict(sorted(priority_counts.items())),
        "portfolio_priority_family_counts": dict(sorted(portfolio_priority_counts.items())),
        "portfolio_consolidations": [
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
        ],
        "portfolio_closeouts": {
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
        },
        "defect_tag_glossary": {
            "SURFACE_NOT_BALANCED": "No adequate counterfactual balance across entities, IDs, amounts, wording, or presentation/candidate order; this is a shortcut risk, not a claim that a shortcut was behaviorally proven.",
            "UNIFIED_ENV_PORT": "The mechanism is absent from the target v3 unified domain or is implemented through a legacy/task-specific context.",
            "WEAK_HEADROOM": "This lineage has only one focal failure; it cannot independently justify family admission.",
            "CONTROL_BASELINE_NOISY": "The supposed protected/control baseline is not stable in historical or matched-monitor evidence.",
            "NO_LEGAL_SUCCESS_PATH": "The frozen task has no verified state where Task Success and Governance Compliance can both hold.",
            "EVALUATOR_CONFLICT": "The success evaluator requires or rewards a mutation forbidden by the governing policy.",
            "REFERENCE_REPAIR_UNVERIFIED": "Task/family repair, support safety, or axis-specific repair remains incomplete.",
            "DUPLICATE_MECHANISM_LINEAGE": "Multiple historical construction stages instantiate the same underlying mechanism and must be consolidated.",
            "DUPLICATE_TASK_PAYLOAD": "The frozen task payload duplicates an earlier task after removing the ID.",
            "CONTROL_SAFETY_INCONCLUSIVE": "The available support-side experiment did not yield a conclusive full matched set.",
            "USER_SIMULATOR_EARLY_STOP": "A support-side run ended before the behavior needed for attribution occurred.",
            "AXIS_CONFOUNDED": "Capability and Governance effects are not both stable and independently attributable on this lineage.",
            "DIRECT_LEGAL_PATH_CUE": "Visible wording substantially discloses the intended workaround or legal path.",
            "DEFER_UNTIL_SINGLE_AXIS_ADMISSION": "Joint construction is blocked on independent source-family admission.",
            "NO_UNIQUE_MECHANISM": "The lineage adds no distinctive learnable mechanism beyond cleaner families or controls.",
        },
        "families": family_rows,
        "lineages": lineages,
    }
    (HERE / "mechanism_family_registry.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    columns = [
        "task_id", "family_id", "priority", "family_rank", "domain", "original_role", "source_stage",
        "original_mechanism", "e0_sequence", "capability_headroom", "governance_headroom",
        "reference_skill_status", "legal_success_path", "defect_tags", "reconstruction_reason",
    ]
    with (HERE / "rebuild_lineage_backlog.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in lineages:
            writer.writerow({**row, "e0_sequence": "/".join(row["e0_sequence"]), "defect_tags": ";".join(row["defect_tags"])})

    lines = [
        "# Benchmark v2 rebuild backlog grouping",
        "",
        "**Result: 40 `REBUILD` lineages occupy 14 historical source-family rows. After the endpoint-preservation consolidation, the planned portfolio has 13 mechanism families: P0=6, P1=4, P2=1, P3=2.**",
        "",
        "The table retains historical source-family rows for lineage traceability. `G-AIR-LGA04-DESTINATION-PRESERVATION` and `G-AIR-LGV16B-004-ONE-WAY-SCOPE` count as one planned portfolio family, `G-AIR-ENDPOINT-PRESERVATION`, with two separately reported Trigger topologies.",
        "",
        "Priority is assigned at family level. A low-quality lineage does not lower a family when stronger independent states already verify the mechanism; it is tagged and used only as design evidence.",
        "",
        "| Rank | Priority | Family | Axis | Lineages | Next action |",
        "|---:|---|---|---|---:|---|",
    ]
    for family in family_rows:
        lines.append(f"| {family['rank']} | `{family['priority']}` | `{family['family_id']}` | {family['axis']} | {family['lineage_count']} | {family['next_action']} |")
    lines += [
        "",
        "## Defect-tag interpretation",
        "",
        "`SURFACE_NOT_BALANCED` is intentionally weaker than saying a shortcut was proven: it records missing counterfactual coverage across entity, ID, amount, wording, or ordering. `NO_LEGAL_SUCCESS_PATH` and `EVALUATOR_CONFLICT` are hard blockers. `WEAK_HEADROOM`, `REFERENCE_REPAIR_UNVERIFIED`, and `CONTROL_BASELINE_NOISY` are evidence-quality blockers. `AXIS_CONFOUNDED` and `DEFER_UNTIL_SINGLE_AXIS_ADMISSION` keep old Joint surfaces out of the active build queue.",
        "",
        "## Execution boundary",
        "",
        "- P0 is already closed as three Ready and three Deferred families; formal realization remains portfolio-wide rather than incremental.",
        "- P1 Governance is closed with four portfolio families, all Deferred and with no active gate. The five historical source rows count as four because LGA04 and LGV16B-004 are one endpoint-preservation family.",
        "- P2 is narrowed to preserved same-cabin segment historical valuation, then dropped as a standalone family because the broader v3 EE-01 channel-conditioned settlement family already contains this capability. Its feasible pair is not built, and it has no active gate.",
        "- P3 is closed without new experiments: legacy control 75 is dropped for noisy baseline and no unique value; old Joint tasks 036/037 are retained only as evidence and replaced by future new Joint design after Ready single-axis integration.",
        "- The full 13-family mechanism portfolio is closed as 3 Ready, 7 Deferred, and 3 Dropped. Only the Ready batch may enter the next integrated pre-ID realization workspace.",
        "- The registry preserves lineage evidence but does not authorize changing the historical v2/v3 editions.",
        "",
        "Historical source rows remain separate for lineage traceability, but planned portfolio counts apply the endpoint-preservation consolidation. No task IDs have been allocated by this grouping step.",
        "",
        "Per-lineage defect tags and reasons are in `rebuild_lineage_backlog.csv`; the full machine-readable registry is `mechanism_family_registry.json`.",
    ]
    (HERE / "REBUILD_BACKLOG_GROUPING_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS_V2_REBUILD_FAMILY_REGISTRY")


if __name__ == "__main__":
    main()
