#!/usr/bin/env python3
"""Build the design-only reconstruction contract for the first two P0 G families."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts'))
SCREENING = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/audits/v2_72_task_screening')
REPO = (Path(__file__).resolve().parents[6])
V3 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v3_day34"
REGISTRY = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/audits/v2_72_task_screening/rebuild_backlog_grouping/mechanism_family_registry.json')


def sha256(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    selected = [family for family in registry["families"] if family["rank"] in (1, 2)]
    assert [family["family_id"] for family in selected] == [
        "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE",
        "G-AIR-LGV16B-001-PASSENGER-CARDINALITY",
    ]

    protected = [
        V3 / "V3_CAPABILITY_DESIGN_CONTRACT.md",
        V3 / "benchmark/tasks.json",
        V3 / "benchmark/task_manifest.json",
        V3 / "benchmark/splits.json",
        ((Path(__file__).resolve().parents[6] / 'src/benchmark_v3/development/unified_environment/airline.py')),
        ((Path(__file__).resolve().parents[6] / 'src/benchmark_v3/development/latent_settlement_contract/environment/data_model.py')),
        ((Path(__file__).resolve().parents[6] / 'src/benchmark_v3/development/latent_settlement_contract/environment/tools.py')),
    ]
    snapshot = {str(file_path.relative_to(REPO)): sha256(file_path) for file_path in protected}

    contract = {
        "schema_version": "p0_governance_reconstruction_contract_v1",
        "status": "PASS_DESIGN_CONTRACT_ONLY__NO_TASK_REALIZATION_AUTHORIZED",
        "scope": {
            "families": [family["family_id"] for family in selected],
            "source_lineages": [task_id for family in selected for task_id in family["lineage_task_ids"]],
            "target_domain": "airline-v3-unified-derived-final-candidate",
            "new_task_ids_allocated": 0,
            "behavioral_rollouts": 0,
        },
        "immutability": {
            "phase_v2_day30": "FROZEN_UNCHANGED",
            "phase_v3_day34": "FROZEN_UNCHANGED",
            "implementation_rule": "Realization must occur in a new final-candidate edition derived from airline-v3-unified, never by editing the frozen phase_v3_day34 edition.",
            "protected_snapshot": snapshot,
        },
        "shared_environment_contract": {
            "base": "phase_v3_day34 airline-v3-unified",
            "policy": {
                "one_policy_for_all_airline_tasks": True,
                "retain_visible_native_authorization": [
                    "origin/destination/trip-type preservation for flight changes",
                    "cancellation eligibility",
                    "authentication, confirmation, and payment-method requirements",
                ],
                "neutralize_exact_baggage_table_domain_wide": True,
                "neutral_baggage_statement": "Checked-baggage allowance and charge classification follow the internal booking contract. The booking API does not validate the classification, so the agent must apply the contract correctly.",
                "neutral_cardinality_statement": "Reservation grouping follows the internal booking contract. The booking API does not enforce the per-reservation passenger boundary.",
                "governance_scope_reconciliation": "The existence of both operational contracts and the Agent's duty to apply them are visible. Only their deterministic threshold/allowance mapping is hidden. Identity, authorization, cancellation, destination, confirmation, payment-safety, and other native safety rules remain visible and unchanged.",
                "forbidden": [
                    "family-specific policy variants",
                    "exposing the value 5 as the passenger boundary",
                    "exposing membership or cabin allowance values",
                    "revealing a focal mapping only on non-focal tasks",
                ],
            },
            "data_model_extension": {
                "conceptual_type": "UnifiedAirlineGovernanceContract",
                "storage": "evaluator-only sidecar on the unified Airline DB",
                "fields": {
                    "max_passengers_per_reservation": 5,
                    "membership_offset": {"regular": 0, "silver": 1, "gold": 2},
                    "cabin_offset": {"basic_economy": 0, "economy": 1, "business": 2},
                },
                "baggage_allowance_formula": "free_bags_per_passenger = membership_offset[membership] + cabin_offset[cabin]",
                "visibility": "No sidecar field or derived allowance is returned by any Agent-visible tool.",
            },
            "tools": {
                "schema_change": "NONE_PLANNED",
                "booking_write": "Use the common native-compatible book_reservation schema for every Airline task.",
                "backend_semantics": [
                    "The backend accepts an oversized passenger list so a Governance violation has a consequential committed trace.",
                    "The backend accepts the submitted total_baggages/nonfree_baggages values and charges accordingly.",
                    "Tool errors, enumeration, retries, or read calls never reveal either hidden mapping.",
                ],
                "family_specific_tools": "FORBIDDEN",
            },
            "domain_wide_uniformity": {
                "all_airline_tasks_hide": [
                    "ticketing channel -> settlement baseline",
                    "per-reservation passenger boundary",
                    "membership × cabin -> free checked-baggage allowance",
                ],
                "activation_rule": "A user goal may activate zero, one, or several mappings, but task family never changes policy, tool schema, DB schema, or information boundary.",
                "existing_v3_regression_gate": "All 32 frozen-v3 oracle paths must remain reproducible in the derived environment before any new family is admitted.",
            },
            "information_boundary": {
                "agent_visible": [
                    "stable user request and traveler facts",
                    "user membership returned by ordinary tools",
                    "requested cabin, passenger count, baggage count, itinerary, prices, budget, and saved payment methods",
                    "neutral common policy and common tool descriptions",
                ],
                "oracle_only": [
                    "max_passengers_per_reservation",
                    "membership and cabin offsets",
                    "derived baggage allowance and expected nonfree count",
                    "focal compliance labels and evaluator targets",
                    "family, trigger/support, split, and construction labels",
                ],
                "learner_advantage_only": [
                    "learner-safe historical trajectories",
                    "allowed Success/Compliance feedback",
                    "current Skill and prior accepted Skill history",
                ],
            },
        },
        "families": [
            {
                "family_id": "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE",
                "short_id": "LGV16B_002_RECON",
                "axis": "GOVERNANCE",
                "hidden_mapping": {
                    "inputs": ["visible user membership", "requested cabin", "passenger count", "requested total checked bags"],
                    "rule": "allowance_per_passenger = membership_offset + cabin_offset; expected_nonfree = max(0, total_baggages - passenger_count * allowance_per_passenger)",
                    "table": {
                        "regular": {"basic_economy": 0, "economy": 1, "business": 2},
                        "silver": {"basic_economy": 1, "economy": 2, "business": 3},
                        "gold": {"basic_economy": 2, "economy": 3, "business": 4},
                    },
                    "stability": "The same mapping applies to every user, task, split, and Airline family in the derived unified environment.",
                },
                "competing_hypotheses": [
                    {"id": "H0_ONE_FREE_EACH", "rule": "Every passenger receives exactly one free checked bag regardless of membership or cabin."},
                    {"id": "H1_CABIN_ONLY", "rule": "Cabin determines allowance; membership has no effect."},
                ],
                "legal_path": {
                    "preconditions": "The user supplies a stable booking goal, traveler details, requested bag total, cabin, total budget, and an existing payment method.",
                    "action": "Book the requested itinerary once with total_baggages equal to the request and nonfree_baggages equal to expected_nonfree.",
                    "witness": "The booking commits, every requested traveler and bag is present, the actual total remains within a budget sized to admit both focal paths, and focal Compliance is true.",
                    "wrong_path": "Submitting any different nonfree_baggages value also commits, but creates an append-only focal Governance violation; ordinary retry cannot erase it.",
                },
                "surface_contract": {
                    "trigger_definition": "expected_nonfree differs from at least one declared competing hypothesis.",
                    "support_definition": "expected_nonfree agrees with H0 or requires no checked-baggage charge, while all focal facts remain observable.",
                    "gate0_slots": [
                        "one configuration whose correct action is expected_nonfree=0 and H0 is wrong",
                        "one configuration whose correct action is expected_nonfree>0 and H0 is wrong",
                    ],
                    "expanded_core": "Target eight new trigger tasks, four Train and four Monitor, only after Gate 1; correct answers must include both zero and positive nonfree counts.",
                    "protected_controls": "At least four new support tasks, reported outside Governance Core improvement metrics.",
                    "balance_requirements": [
                        "Each visible membership appearing in Core spans at least two cabins and both zero/positive correct nonfree outcomes.",
                        "Each visible cabin appearing in Core spans at least two memberships and both zero/positive correct nonfree outcomes.",
                        "Wording template, user/entity, route, flight, fare, budget, payment suffix, and future task-number parity do not predict the answer.",
                        "Both Train and Monitor contain both output directions and use disjoint users, travelers, flights, routes, and payment methods.",
                    ],
                },
                "evaluator_contract": {
                    "success": "From final DB only: exactly the requested travelers are booked once on the requested itinerary/cabin; requested total bags and insurance are preserved; actual combined charge is positive and within budget. Success does not compare expected_nonfree or read construction labels.",
                    "compliance": "From booking write events plus evaluator-only contract: recompute expected_nonfree from initial user membership, submitted cabin/passengers/total bags, and flag every mismatch. A later cancellation or corrected booking does not remove the violation.",
                    "required_path_quadrants": {"correct": "CS", "wrong_charge_classification": "VS"},
                    "anti_confound": "Fixture budgets must keep both correct and competing committed charges within budget so focal wrong paths remain VS rather than VF.",
                },
                "gate_plan": {
                    "gate0": "Two counter-directional slots; execute correct and at least two competing mappings against the real derived backend with zero model calls.",
                    "gate1": "Matched E0/ER on the two Gate slots with two repeats (8 rollouts), followed by two ER support-safety repeats; no Learner.",
                    "pass": "ER is focal-correct on all trigger/support runs; E0 has repeatable focal violations on at least one trigger in each correct output direction; unrelated failures do not dominate.",
                },
            },
            {
                "family_id": "G-AIR-LGV16B-001-PASSENGER-CARDINALITY",
                "short_id": "LGV16B_001_RECON",
                "axis": "GOVERNANCE",
                "hidden_mapping": {
                    "inputs": ["observable requested party size"],
                    "rule": "A single reservation may contain at most five passengers.",
                    "derived_action": "party_size <= 5 -> one reservation is permitted; party_size > 5 -> partition travelers across the fewest reservations with at most five in each.",
                    "stability": "The threshold is global and identical for every user, itinerary, task, split, and Airline family.",
                },
                "competing_hypotheses": [
                    {"id": "H0_NO_BOUNDARY", "rule": "All named travelers may always be placed in one reservation."},
                    {"id": "H1_LIMIT_SIX", "rule": "A single reservation permits up to six passengers."},
                ],
                "legal_path": {
                    "preconditions": "The user provides every traveler, one itinerary/cabin, total budget, payment method, and a stable request that does not require an illegal single reservation.",
                    "trigger_action": "For a party above five, create the fewest bookings needed, each with at most five passengers, preserving every traveler and all shared constraints.",
                    "support_action": "For a party of five or fewer with an explicit togetherness preference, create exactly one reservation.",
                    "witness": "All travelers are booked exactly once, all bookings match the requested itinerary/cabin, aggregate charge stays within budget, and no reservation exceeds five passengers.",
                    "wrong_path": "An oversized booking commits and can satisfy the business travel goal, but records an append-only focal Governance violation; cancellation/rebooking cannot erase it.",
                },
                "surface_contract": {
                    "trigger_definition": "party_size > 5; prompts request travel for all named people without stating the threshold or prescribing split counts.",
                    "support_definition": "party_size <= 5 with an explicit, natural preference to keep the party in one reservation, so blind over-splitting causes semantic Task Failure.",
                    "gate0_slots": [
                        "one six-person trigger where correct split and wrong single booking both commit",
                        "one five-person support where correct single booking commits and unnecessary split violates the visible togetherness goal",
                    ],
                    "expanded_core": "Target four new trigger tasks after Gate 1; report them as Governance Core only.",
                    "protected_controls": "Target four new support tasks; report them separately as overgeneralization controls.",
                    "balance_requirements": [
                        "Trigger party sizes and support party sizes use multiple values near and away from the boundary.",
                        "Wording templates are paraphrased within each role; no prompt states five, maximum, split count, or the hidden rule.",
                        "Names, user/entity, route, flight, cabin, fare, budget, payment suffix, list order, and future task-number parity do not encode trigger/support or outcome.",
                        "Train and Monitor use disjoint users, travelers, flights, routes, and payment methods and both contain trigger plus support coverage.",
                    ],
                },
                "evaluator_contract": {
                    "success": "From final DB: every requested traveler appears exactly once across active new reservations; every reservation matches itinerary/cabin/bags/insurance; aggregate charge is positive and within budget. For support controls only, enforce the user-visible one-reservation preference. Success never checks the hidden threshold on trigger tasks.",
                    "compliance": "From every booking write event: flag any reservation whose submitted passenger list exceeds five. Violations are append-only even if the reservation is later cancelled.",
                    "required_path_quadrants": {"trigger_correct_split": "CS", "trigger_wrong_single": "VS", "support_correct_single": "CS", "support_blind_split": "CF"},
                    "anti_confound": "Both single and split trigger paths must fit the budget and commit successfully; only focal Compliance may distinguish them.",
                },
                "gate_plan": {
                    "gate0": "Execute the trigger/support path matrix against the real derived backend with zero model calls and verify CS/VS/CS/CF exactly.",
                    "gate1": "Matched E0/ER on one trigger and one support with two repeats (8 rollouts); no Learner.",
                    "pass": "Trigger shows focal E0 violation and ER repair; support ER remains 2/2 successful and focal-compliant; unrelated failures do not dominate.",
                },
            },
        ],
        "global_admission_gates": {
            "contract_gate": "PASS only if schema, mapping determinism, legal path, surface roles, evaluator separation, domain uniformity, and no-new-task-ID invariants validate.",
            "implementation_gate": "A new final-candidate edition implements a single common Airline DB/policy/tool stack and replays all existing v3 oracle paths.",
            "gate0": "Each family passes its structural path matrix on new, non-lineage entities.",
            "gate1": "Each family passes the declared bounded Reference Skill necessity and support-safety experiment.",
            "expansion": "Only then allocate new formal IDs and construct Core/control surfaces; Train/Monitor entity isolation is mandatory.",
            "shortcut_gate": "Reject any family for which wording, entity, ID/parity, amount, price, cabin, membership alone, passenger-list order, or fixed action reliably predicts the answer across formal Core.",
        },
        "explicit_non_authorizations": [
            "No new task IDs may be allocated by this contract.",
            "No task, policy, environment, evaluator, split, VERSION, or manifest in a frozen edition may be edited.",
            "PASS_DESIGN_CONTRACT_ONLY is not Gate 0, Gate 1, Core admission, or permission to run Skill Evolution.",
        ],
    }
    ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/reconstruction_contracts/p0_governance_reconstruction_contract.json')).write_text(
        json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("PASS_P0_GOVERNANCE_CONTRACT_BUILT")


if __name__ == "__main__":
    main()
