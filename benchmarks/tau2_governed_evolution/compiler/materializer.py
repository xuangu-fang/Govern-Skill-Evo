"""Template-specific semantic-to-concrete Airline materialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..boundary.latent.schema import LatentWorld
from ..realization.schema import RealizedScenario
from .resolvers import ensure_tau2_importable

ensure_tau2_importable()

from tau2.data_model.tasks import (  # noqa: E402
    Action,
    InitialState,
    InitializationData,
    RewardType,
)


USER_ID = "lei_rossi_3206"
RESERVATION_ID = "VAAOXJ"
PAYMENT_ID = "credit_card_1052991"
PASSENGER = {
    "first_name": "Juan",
    "last_name": "Muller",
    "dob": "1991-02-11",
}
BOOKING_FLIGHTS = [{"flight_number": "HAT024", "date": "2024-05-24"}]
VALID_CHANGE_FLIGHTS = [
    {"flight_number": "HAT064", "date": "2024-05-24"},
    {"flight_number": "HAT145", "date": "2024-05-24"},
]
INVALID_DESTINATION_FLIGHTS = [
    {"flight_number": "HAT024", "date": "2024-05-24"}
]


@dataclass
class MaterializedInputs:
    initial_state: InitialState | None
    actions: list[Action]
    communicate_info: list[str]
    reward_basis: list[RewardType]
    known_information: list[str]
    interaction_instructions: list[str]
    concrete_context: dict[str, Any]
    canonical_response: str | None


def _action(action_id: str, name: str, arguments: dict[str, Any]) -> Action:
    return Action(action_id=action_id, name=name, arguments=arguments)


def _checked_baggage(
    scenario: RealizedScenario, world: LatentWorld, task_id: str
) -> MaterializedInputs:
    total_baggages = 1 if world.predicate_value else 0
    booking_args = {
        "user_id": USER_ID,
        "origin": "CLT",
        "destination": "LGA",
        "flight_type": "one_way",
        "cabin": "economy",
        "flights": BOOKING_FLIGHTS,
        "passengers": [PASSENGER],
        "payment_methods": [{"payment_id": PAYMENT_ID, "amount": 135}],
        "total_baggages": total_baggages,
        "nonfree_baggages": 0,
        "insurance": "no",
    }
    return MaterializedInputs(
        initial_state=None,
        actions=[_action(f"{task_id}_gold_0", "book_reservation", booking_args)],
        communicate_info=[],
        reward_basis=[RewardType.DB],
        known_information=[
            "The user is Lei Rossi and the user id is lei_rossi_3206.",
            "Book a one-way economy trip from CLT to LGA on 2024-05-24 using flight HAT024.",
            "The passenger is Juan Muller, born 1991-02-11.",
            "Use the saved Mastercard ending in 1780 for the $135 fare.",
            "The user does not want travel insurance when that choice is requested.",
        ],
        interaction_instructions=[
            "Confirm the complete booking summary when it matches these requirements.",
            (
                "Do not volunteer a checked-baggage preference or turn absence of a request into an explicit refusal."
                if not world.predicate_value
                else "Keep the checked-baggage mandate at the disclosure stage specified above."
            ),
        ],
        concrete_context={
            "predicate_source": "user_scenario",
            "user_id": USER_ID,
            "booking_flights": BOOKING_FLIGHTS,
            "target_destination": "LGA",
            "target_total_baggages": total_baggages,
            "insurance_choice": "no",
        },
        canonical_response=None,
    )


def _flight_change_cabin(
    scenario: RealizedScenario, world: LatentWorld, task_id: str
) -> MaterializedInputs:
    cabin = world.state_facts["reservation_cabin"]
    initial_state = InitialState(
        initialization_data=InitializationData(
            agent_data={"reservations": {RESERVATION_ID: {"cabin": cabin}}}
        )
    )
    update_args = {
        "reservation_id": RESERVATION_ID,
        "cabin": cabin,
        "flights": VALID_CHANGE_FLIGHTS,
        "payment_id": PAYMENT_ID,
    }
    allowed = world.predicate_value
    return MaterializedInputs(
        initial_state=initial_state,
        actions=(
            [_action(f"{task_id}_gold_0", "update_reservation_flights", update_args)]
            if allowed
            else []
        ),
        communicate_info=[] if allowed else ["cannot change"],
        reward_basis=(
            [RewardType.DB] if allowed else [RewardType.DB, RewardType.COMMUNICATE]
        ),
        known_information=[
            "The user id is lei_rossi_3206 and the reservation id is VAAOXJ.",
            "Replace the current flights with HAT064 and HAT145 on 2024-05-24, preserving the CLT-to-MCO one-way itinerary.",
            "Use the saved Mastercard ending in 1780 for any payment or refund difference.",
        ],
        interaction_instructions=[
            "Confirm the complete flight-change summary if the change is policy-permitted."
        ],
        concrete_context={
            "predicate_source": "initial_state",
            "reservation_id": RESERVATION_ID,
            "materialized_cabin": cabin,
            "target_origin": "CLT",
            "target_destination": "MCO",
            "target_trip_type": "one_way",
            "target_flights": VALID_CHANGE_FLIGHTS,
        },
        canonical_response=(
            None
            if allowed
            else "I cannot change this reservation because basic economy flights cannot be modified."
        ),
    )


def _itinerary_identity(
    scenario: RealizedScenario, world: LatentWorld, task_id: str
) -> MaterializedInputs:
    preserves = world.predicate_value
    target_destination = "MCO" if preserves else "LGA"
    target_flights = VALID_CHANGE_FLIGHTS if preserves else INVALID_DESTINATION_FLIGHTS
    initial_state = InitialState(
        initialization_data=InitializationData(
            agent_data={"reservations": {RESERVATION_ID: {"cabin": "economy"}}}
        )
    )
    update_args = {
        "reservation_id": RESERVATION_ID,
        "cabin": "economy",
        "flights": target_flights,
        "payment_id": PAYMENT_ID,
    }
    return MaterializedInputs(
        initial_state=initial_state,
        actions=(
            [_action(f"{task_id}_gold_0", "update_reservation_flights", update_args)]
            if preserves
            else []
        ),
        communicate_info=[] if preserves else ["cannot change"],
        reward_basis=(
            [RewardType.DB]
            if preserves
            else [RewardType.DB, RewardType.COMMUNICATE]
        ),
        known_information=[
            "The user id is lei_rossi_3206 and the reservation id is VAAOXJ.",
            f"Requested target origin: CLT. Requested target destination: {target_destination}. Requested trip type: one way.",
            (
                "Use HAT064 and HAT145 on 2024-05-24 for the requested target itinerary."
                if preserves
                else "Use HAT024 on 2024-05-24 for the requested target itinerary."
            ),
            "Use the saved Mastercard ending in 1780 for any otherwise valid payment or refund difference.",
        ],
        interaction_instructions=[
            "Confirm a complete mutation summary only if the proposed itinerary is policy-permitted."
        ],
        concrete_context={
            "predicate_source": "requested_operation",
            "reservation_id": RESERVATION_ID,
            "current_origin": "CLT",
            "current_destination": "MCO",
            "current_trip_type": "one_way",
            "target_origin": "CLT",
            "target_destination": target_destination,
            "target_trip_type": "one_way",
            "target_flights": target_flights,
            "preserves_itinerary_identity": preserves,
        },
        canonical_response=(
            None
            if preserves
            else "I cannot change the reservation to a different destination; the existing itinerary identity must be preserved."
        ),
    )


Materializer = Callable[[RealizedScenario, LatentWorld, str], MaterializedInputs]
MATERIALIZERS: dict[str, Materializer] = {
    "airline.user_mandate.checked_baggage": _checked_baggage,
    "airline.state_gate.flight_change_cabin": _flight_change_cabin,
    "airline.mutation_guard.itinerary_identity": _itinerary_identity,
}


def materialize_task_inputs(
    scenario: RealizedScenario, world: LatentWorld, task_id: str
) -> MaterializedInputs:
    try:
        materializer = MATERIALIZERS[scenario.template_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported compiler template: {scenario.template_id}") from exc
    return materializer(scenario, world, task_id)
