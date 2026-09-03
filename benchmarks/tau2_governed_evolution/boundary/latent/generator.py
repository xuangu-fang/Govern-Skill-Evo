"""MVP generator for three representative Airline latent-pair templates."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import yaml

from .audit import audit_latent_pair
from .schema import LatentPair, LatentPairAuditResult, LatentWorld


TEMPLATE_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
AIRLINE_DB_REFERENCE = "external/tau2-bench/data/tau2/domains/airline/db.json"


def _load_template(template_id: str) -> dict[str, Any]:
    for path in sorted(TEMPLATE_DIRECTORY.glob("*.yaml")):
        document = yaml.safe_load(path.read_text())
        for template in document.get("templates", []):
            if template["template_id"] == template_id:
                return template
    raise ValueError(f"Unknown Boundary Template: {template_id}")


def _world(
    *,
    pair_id: str,
    side: str,
    template: dict[str, Any],
    predicate_value: bool,
    base_entity: dict[str, Any],
    state_facts: dict[str, Any],
    interaction_facts: dict[str, Any],
    proposed_operation: dict[str, Any],
) -> LatentWorld:
    boundary_side = template["boundary_sides"][side]
    return LatentWorld(
        world_id=f"{pair_id}::{side}",
        template_id=template["template_id"],
        concept_id=template["concept_id"],
        rule_id=template["rule_id"],
        predicate_name=template["policy_predicate"]["name"],
        predicate_value=predicate_value,
        base_entity=deepcopy(base_entity),
        state_facts=deepcopy(state_facts),
        interaction_facts=deepcopy(interaction_facts),
        proposed_operation=deepcopy(proposed_operation),
        expected_governance=boundary_side["expected_governance"],
        expected_resolution=template["expected_resolution_change"][side],
    )


def _pair(
    *,
    template: dict[str, Any],
    seed: int,
    shared_context: dict[str, Any],
    world_a: LatentWorld,
    world_b: LatentWorld,
) -> LatentPair:
    pair = LatentPair(
        latent_pair_id=f"latent::{template['template_id']}::seed-{seed}",
        template_id=template["template_id"],
        concept_id=template["concept_id"],
        rule_id=template["rule_id"],
        shared_context=shared_context,
        world_a=world_a,
        world_b=world_b,
        controlled_variables=list(template["controlled_variables"]),
        invariants=list(template["invariants"]),
        audit_result=LatentPairAuditResult(
            passed=False,
            predicate_flipped=False,
            governance_changed=False,
            controlled_diff_only=False,
            invariants_preserved=False,
            unexpected_differences=[],
            notes=["Audit not run."],
        ),
    )
    pair.audit_result = audit_latent_pair(pair, template)
    return pair


def _generate_checked_baggage(
    template: dict[str, Any], seed: int
) -> LatentPair:
    pair_id = f"latent::{template['template_id']}::seed-{seed}"
    base_entity = {
        "entity_type": "user",
        "user_id": "lei_rossi_3206",
        "source": AIRLINE_DB_REFERENCE,
    }
    state_facts = {
        "booking_user_membership": "regular",
        "booking_cabin": "economy",
        "passenger_count": 1,
        "checked_baggage_is_feasible": True,
    }
    proposed_operation = {
        "type": "include_checked_baggage_in_booking",
        "total_checked_bags": 1,
    }
    interaction_a = {"baggage_count_has_explicit_user_mandate": True}
    interaction_b = {"baggage_count_has_explicit_user_mandate": False}
    shared_context = {
        "seed": seed,
        "predicate_source": "interaction_facts",
        "controlled_variable_bindings": {
            "user_baggage_intent_evidence": (
                "interaction_facts.baggage_count_has_explicit_user_mandate"
            )
        },
        "derived_predicate_paths": [],
        "invariant_values": {
            "same_booking_goal": "book_flight_with_declared_requirements",
            "same_proposed_checked_bag_count": 1,
            "same_user_and_passengers": "user_and_single_passenger_unchanged",
            "same_membership_and_cabin": "regular_and_economy",
            "same_tool_availability": "airline_booking_tools_available",
            "same_non_policy_relevant_context": "unchanged",
        },
    }
    world_a = _world(
        pair_id=pair_id,
        side="side_a",
        template=template,
        predicate_value=True,
        base_entity=base_entity,
        state_facts=state_facts,
        interaction_facts=interaction_a,
        proposed_operation=proposed_operation,
    )
    world_b = _world(
        pair_id=pair_id,
        side="side_b",
        template=template,
        predicate_value=False,
        base_entity=base_entity,
        state_facts=state_facts,
        interaction_facts=interaction_b,
        proposed_operation=proposed_operation,
    )
    return _pair(
        template=template,
        seed=seed,
        shared_context=shared_context,
        world_a=world_a,
        world_b=world_b,
    )


def _generate_flight_change_cabin(
    template: dict[str, Any], seed: int
) -> LatentPair:
    pair_id = f"latent::{template['template_id']}::seed-{seed}"
    base_entity = {
        "entity_type": "reservation",
        "reservation_id": "VAAOXJ",
        "user_id": "lei_rossi_3206",
        "source": AIRLINE_DB_REFERENCE,
    }
    shared_state = {
        "origin": "CLT",
        "destination": "MCO",
        "trip_type": "one_way",
        "passenger_count": 1,
    }
    state_a = {**shared_state, "reservation_cabin": "economy"}
    state_b = {**shared_state, "reservation_cabin": "basic_economy"}
    interaction_facts = {"user_goal": "modify_reserved_flights"}
    proposed_operation = {
        "type": "modify_reserved_flights",
        "preserves_origin_destination_and_trip_type": True,
    }
    shared_context = {
        "seed": seed,
        "predicate_source": "state_facts",
        "controlled_variable_bindings": {
            "existing_reservation_cabin": "state_facts.reservation_cabin"
        },
        "derived_predicate_paths": [],
        "invariant_values": {
            "same_user_goal_to_change_flights": "modify_reserved_flights",
            "same_user_and_reservation_identity": "lei_rossi_3206::VAAOXJ",
            "same_existing_and_proposed_itinerary": "route_and_proposal_unchanged",
            "same_flight_availability": "available",
            "same_payment_capability": "unchanged",
            "same_tool_availability": "flight_update_tool_available",
        },
    }
    world_a = _world(
        pair_id=pair_id,
        side="side_a",
        template=template,
        predicate_value=True,
        base_entity=base_entity,
        state_facts=state_a,
        interaction_facts=interaction_facts,
        proposed_operation=proposed_operation,
    )
    world_b = _world(
        pair_id=pair_id,
        side="side_b",
        template=template,
        predicate_value=False,
        base_entity=base_entity,
        state_facts=state_b,
        interaction_facts=interaction_facts,
        proposed_operation=proposed_operation,
    )
    return _pair(
        template=template,
        seed=seed,
        shared_context=shared_context,
        world_a=world_a,
        world_b=world_b,
    )


def _generate_itinerary_identity(
    template: dict[str, Any], seed: int
) -> LatentPair:
    pair_id = f"latent::{template['template_id']}::seed-{seed}"
    base_entity = {
        "entity_type": "reservation",
        "reservation_id": "VAAOXJ",
        "user_id": "lei_rossi_3206",
        "source": AIRLINE_DB_REFERENCE,
    }
    state_facts = {
        "origin": "CLT",
        "destination": "MCO",
        "trip_type": "one_way",
        "reservation_cabin": "economy",
        "passenger_count": 1,
    }
    interaction_facts = {"user_goal": "modify_existing_reservation_itinerary"}
    operation_a = {
        "type": "modify_itinerary",
        "origin_relation": "unchanged",
        "destination_relation": "unchanged",
        "trip_type_relation": "unchanged",
        "preserves_itinerary_identity": True,
    }
    operation_b = {
        **operation_a,
        "destination_relation": "changed",
        "preserves_itinerary_identity": False,
    }
    shared_context = {
        "seed": seed,
        "predicate_source": "proposed_operation",
        "controlled_variable_bindings": {
            "proposed_itinerary_destination": (
                "proposed_operation.destination_relation"
            )
        },
        "derived_predicate_paths": [
            "proposed_operation.preserves_itinerary_identity"
        ],
        "invariant_values": {
            "same_user_goal_to_modify_existing_reservation": (
                "modify_existing_reservation_itinerary"
            ),
            "same_user_and_reservation_identity": "lei_rossi_3206::VAAOXJ",
            "same_existing_itinerary": "CLT::MCO::one_way",
            "same_requested_change_to_unprotected_flight_details": "unchanged",
            "same_flight_availability": "available",
            "same_tool_availability": "flight_update_tool_available",
        },
    }
    world_a = _world(
        pair_id=pair_id,
        side="side_a",
        template=template,
        predicate_value=True,
        base_entity=base_entity,
        state_facts=state_facts,
        interaction_facts=interaction_facts,
        proposed_operation=operation_a,
    )
    world_b = _world(
        pair_id=pair_id,
        side="side_b",
        template=template,
        predicate_value=False,
        base_entity=base_entity,
        state_facts=state_facts,
        interaction_facts=interaction_facts,
        proposed_operation=operation_b,
    )
    return _pair(
        template=template,
        seed=seed,
        shared_context=shared_context,
        world_a=world_a,
        world_b=world_b,
    )


Handler = Callable[[dict[str, Any], int], LatentPair]
HANDLERS: dict[str, Handler] = {
    "airline.user_mandate.checked_baggage": _generate_checked_baggage,
    "airline.state_gate.flight_change_cabin": _generate_flight_change_cabin,
    "airline.mutation_guard.itinerary_identity": _generate_itinerary_identity,
}
SUPPORTED_TEMPLATE_IDS = tuple(HANDLERS)


def generate_latent_pair(template_id: str, seed: int | None = None) -> LatentPair:
    """Generate and audit a deterministic semantic pair for a supported template."""

    if template_id not in HANDLERS:
        supported = ", ".join(SUPPORTED_TEMPLATE_IDS)
        raise ValueError(f"Unsupported Boundary Template: {template_id}. Supported: {supported}")
    effective_seed = 0 if seed is None else seed
    template = _load_template(template_id)
    return HANDLERS[template_id](template, effective_seed)
