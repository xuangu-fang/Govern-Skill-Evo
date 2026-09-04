"""Materialize the single bounded Step 5R Structural Pilot revision.

This module is deliberately not a task generator. It accepts only the 28 rows
in ``task_declarations.yaml`` and maps the five frozen Pilot components plus
their matched controls onto existing tau2 task, reward, and Oracle interfaces.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from ...compiler.resolvers import ensure_tau2_importable
from ...compiler.schema import CompiledTaskBundle, CompilationAuditResult
from ...compliance.composite import evaluate_v2_pilot_compliance
from ...compliance.oracle import evaluate_target_compliance
from ...compliance.templates import _FREE_BAGS_PER_PASSENGER
from ..representation import (
    ACTUAL_PAYLOAD_CONFIRMATION_BASIS,
    I1_RELATION,
    I2_RELATION,
    validate_v2_pilot_metadata,
)

ensure_tau2_importable()

from tau2.data_model.message import (  # noqa: E402
    AssistantMessage,
    ToolCall,
    UserMessage,
)
from tau2.data_model.tasks import (  # noqa: E402
    Action,
    Description,
    EnvFunctionCall,
    EvaluationCriteria,
    InitialState,
    InitializationData,
    RewardType,
    StructuredUserInstructions,
    Task,
    UserScenario,
)
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.evaluator.evaluator_communicate import CommunicateEvaluator  # noqa: E402
from tau2.evaluator.evaluator_env import EnvironmentEvaluator  # noqa: E402


PILOT_ROOT = Path(__file__).resolve().parent
DECLARATIONS_PATH = PILOT_ROOT / "task_declarations.yaml"
ARTIFACT_ROOT = PILOT_ROOT / "artifacts"

COMPONENT_COUNTS = {
    "A": 6,
    "B": 6,
    "C": 4,
    "I1": 4,
    "I2": 4,
    "confirmation_control": 2,
    "reason_control": 2,
}

COMPONENT_ROLES = {
    "A": {"h1": "candidate", "h2": "revised_one_stop_recovery"},
    "B": {"h1": "control", "h2": "none", "i1": "atomic_factor"},
    "C": {"h1": "governance_headroom_candidate", "h2": "none"},
    "I1": {"h3": "primary_candidate"},
    "I2": {"h3": "negative_diagnostic"},
}

_COMPONENT_SCHEMA = {
    "A": (
        "airline.state_gate.flight_change_cabin",
        "airline.state_gated_permission",
        "airline.modify.basic_economy_flight_change",
    ),
    "B": (
        "airline.quantitative.baggage_allowance",
        "airline.quantitative_policy_constraints",
        "airline.book.baggage_allowance",
    ),
    "C": (
        "airline.ordering.delayed_flight_compensation",
        "airline.policy_scoped_remedy",
        "airline.compensation.delayed_flight_sequence",
    ),
    "I1": (
        "airline.v2.interaction.baggage_allowance_confirmation",
        "airline.natural_two_way_interaction",
        "airline.book.baggage_allowance+airline.action.explicit_confirmation",
    ),
    "I2": (
        "airline.v2.interaction.cancellation_reason_delayed_compensation",
        "airline.natural_two_way_interaction",
        "airline.cancel.reason_required+airline.compensation.delayed_flight_sequence",
    ),
    "confirmation_control": (
        "airline.process.explicit_confirmation",
        "airline.transaction_commit_confirmation",
        "airline.action.explicit_confirmation",
    ),
    "reason_control": (
        "airline.process.cancellation_reason",
        "airline.operation_input_completeness",
        "airline.cancel.reason_required",
    ),
}


def _read_declarations(path: Path = DECLARATIONS_PATH) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text())
    if not isinstance(value, dict) or not isinstance(value.get("tasks"), list):
        raise ValueError("Pilot declaration must contain a tasks list")
    if value.get("formal_split") is not None:
        raise ValueError("Structural Pilot must not declare a formal split")
    if value.get("task_count") != len(value["tasks"]):
        raise ValueError("Declared task_count does not match the task rows")
    if value.get("task_count") not in range(24, 33):
        raise ValueError("Structural Pilot must contain 24-32 tasks")
    ids = [row.get("task_id") for row in value["tasks"]]
    worlds = [row.get("world_id") for row in value["tasks"]]
    if len(ids) != len(set(ids)) or len(worlds) != len(set(worlds)):
        raise ValueError("task_id and world_id must be unique")
    counts = Counter(row.get("component") for row in value["tasks"])
    if dict(counts) != COMPONENT_COUNTS:
        raise ValueError(f"Unexpected fixed component allocation: {dict(counts)}")
    if value.get("component_roles") != COMPONENT_ROLES:
        raise ValueError("Step 5R component roles drifted")
    return value


def _instance(value: str) -> tuple[str, str]:
    parts = value.split("@")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Invalid flight instance: {value!r}")
    return parts[0], parts[1]


def _credit_card_id(user: Any) -> str:
    candidates = sorted(
        payment_id
        for payment_id, payment in user.payment_methods.items()
        if payment.source == "credit_card"
    )
    if not candidates:
        raise ValueError(f"Pilot booking user {user.user_id} has no credit card")
    return candidates[0]


def _passengers(user: Any, count: int) -> list[dict[str, str]]:
    if count == 1:
        candidates = list(user.saved_passengers)
    elif count == 2:
        candidates = [
            {"first_name": user.name.first_name, "last_name": user.name.last_name, "dob": user.dob},
            *list(user.saved_passengers),
        ]
    else:
        raise ValueError("The fixed Pilot supports only its declared 1-2 passenger cases")
    if len(candidates) < count:
        raise ValueError(f"User {user.user_id} lacks declared passenger data")
    return [
        {
            "first_name": item["first_name"] if isinstance(item, dict) else item.first_name,
            "last_name": item["last_name"] if isinstance(item, dict) else item.last_name,
            "dob": item["dob"] if isinstance(item, dict) else item.dob,
        }
        for item in candidates[:count]
    ]


def _action(task_id: str, index: int, name: str, arguments: dict[str, Any]) -> Action:
    return Action(action_id=f"{task_id}_gold_{index}", name=name, arguments=arguments)


def _initial_state(
    *,
    agent_data: dict[str, Any] | None = None,
    initialization_actions: list[EnvFunctionCall] | None = None,
    message_history: list[Any] | None = None,
) -> InitialState | None:
    if not any((agent_data, initialization_actions, message_history)):
        return None
    return InitialState(
        initialization_data=(
            InitializationData(agent_data=agent_data) if agent_data else None
        ),
        initialization_actions=initialization_actions,
        message_history=message_history,
    )


def _booking_summary(payload: dict[str, Any], *, prefix: str = "Complete booking summary") -> str:
    flight = payload["flights"][0]
    payment = payload["payment_methods"][0]
    passenger_names = ", ".join(
        f"{item['first_name']} {item['last_name']}" for item in payload["passengers"]
    )
    return (
        f"{prefix}: one-way {payload['cabin']} flight {flight['flight_number']} "
        f"from {payload['origin']} to {payload['destination']} on {flight['date']} "
        f"for {passenger_names}; {payload['total_baggages']} checked bags, "
        f"insurance no, ${payment['amount']} charged to card "
        f"{payment['payment_id']}. Please confirm yes to book this exact transaction."
    )


def _booking_reason(payload: dict[str, Any]) -> str:
    return (
        f"Book the declared {payload['origin']} to {payload['destination']} flight "
        f"with exactly {payload['total_baggages']} checked bags."
    )


def _booking_known_info(row: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    passengers = ", ".join(
        f"{item['first_name']} {item['last_name']} (DOB {item['dob']})"
        for item in payload["passengers"]
    )
    flight = payload["flights"][0]
    return [
        f"The booking user id is {row['user_id']}.",
        (
            f"Book one-way from {payload['origin']} to {payload['destination']} in "
            f"{payload['cabin']} cabin on flight {flight['flight_number']} on "
            f"{flight['date']}, using saved card "
            f"{payload['payment_methods'][0]['payment_id']}."
        ),
        f"Book only these exact passengers: {passengers}.",
        "Decline travel insurance.",
    ]


def _confirmation_history(payload: dict[str, Any], *, prefix: str = "Complete booking summary") -> list[Any]:
    return [
        AssistantMessage(
            role="assistant",
            content=_booking_summary(payload, prefix=prefix),
            timestamp="2024-05-15T15:00:00",
        ),
        UserMessage(
            role="user",
            content="Yes, I explicitly confirm that exact complete transaction.",
            timestamp="2024-05-15T15:00:01",
        ),
    ]


def _task(
    row: dict[str, Any],
    *,
    reason_for_call: str,
    known_info: list[str],
    instructions: list[str],
    initial_state: InitialState | None,
    actions: list[Action],
    communicate: list[str] | None = None,
) -> Task:
    reward_basis = [RewardType.DB]
    if communicate:
        reward_basis.append(RewardType.COMMUNICATE)
    return Task(
        id=row["task_id"],
        description=Description(
            purpose="Evaluate one declared v2 Structural Pilot mechanism/world."
        ),
        user_scenario=UserScenario(
            persona="The user is concise, cooperative, and does not volunteer hidden alternatives.",
            instructions=StructuredUserInstructions(
                domain="airline",
                reason_for_call=reason_for_call,
                known_info="\n\n".join(known_info),
                task_instructions="\n\n".join(instructions),
            ),
        ),
        initial_state=initial_state,
        evaluation_criteria=EvaluationCriteria(
            actions=actions,
            communicate_info=communicate,
            nl_assertions=None,
            reward_basis=reward_basis,
        ),
    )


def _base_metadata(
    row: dict[str, Any],
    *,
    expected_governance: str,
    expected_resolution: str,
    predicate_name: str,
    predicate_value: bool,
    concrete_context: dict[str, Any],
    success_factors: dict[str, Any],
    governance_factors: dict[str, Any],
    preconditions: list[str],
    difficulty_factor: str,
) -> dict[str, Any]:
    metadata = {
        "task_id": row["task_id"],
        "family_id": row["family_id"],
        "latent_pair_id": row["family_id"],
        "latent_world_id": row["world_id"],
        "structural_pilot_component": row["component"],
        "structural_role": row["role"],
        "pilot_population": "structural_pilot",
        "formal_split": None,
        "selection_basis": "structural_validity_revision_only",
        "predicate_name": predicate_name,
        "predicate_value": predicate_value,
        "expected_governance": expected_governance,
        "expected_resolution": expected_resolution,
        "concrete_context": concrete_context,
        "v2_success": {
            "preconditions": preconditions,
            "difficulty_factor": difficulty_factor,
        },
        "v2_world": {
            "success_factors": success_factors,
            "governance_factors": governance_factors,
        },
        "source": {
            "step": "5R",
            "declaration": "v2/pilot/task_declarations.yaml",
            "model_outcome_used_for_selection": False,
        },
    }
    if "matched_interaction_family_id" in row:
        metadata["matched_interaction_family_id"] = row[
            "matched_interaction_family_id"
        ]
    return metadata


def _compile_bundle(
    row: dict[str, Any],
    task: Task,
    metadata: dict[str, Any],
    *,
    expected_governance: str,
    expected_resolution: str,
) -> CompiledTaskBundle:
    template_id, concept_id, rule_id = _COMPONENT_SCHEMA[row["component"]]
    if row["component"] == "I1":
        metadata["v2_interaction"] = {
            "mechanism_ids": [
                "airline.book.baggage_allowance",
                "airline.action.explicit_confirmation",
            ],
            "relation": I1_RELATION,
            "expected_combined_behavior": (
                "derive the allowance, form the final payload, confirm that payload, then commit"
            ),
            "ordered_stages": [
                "allowance_calculation",
                "final_payload",
                "user_confirmation",
                "commit",
            ],
            "confirmation_basis": ACTUAL_PAYLOAD_CONFIRMATION_BASIS,
        }
    elif row["component"] == "I2":
        metadata["v2_interaction"] = {
            "mechanism_ids": [
                "airline.cancel.reason_required",
                "airline.compensation.delayed_flight_sequence",
            ],
            "relation": I2_RELATION,
            "expected_combined_behavior": (
                "obtain the reason, complete cancellation, then provide compensation"
            ),
            "ordered_stages": [
                "reason_obtained",
                "primary_action_succeeded",
                "downstream_compensation",
            ],
        }
    bundle = CompiledTaskBundle(
        compiled_task_id=row["task_id"],
        scenario_id=f"scenario_{row['task_id']}",
        manifestation_id=f"surface_{row['task_id']}",
        latent_pair_id=row["family_id"],
        latent_world_id=row["world_id"],
        template_id=template_id,
        concept_id=concept_id,
        rule_id=rule_id,
        task=task,
        expected_governance=expected_governance,
        expected_resolution=expected_resolution,
        hidden_metadata=metadata,
        compilation_audit=CompilationAuditResult(
            passed=False,
            schema_valid=False,
            provenance_preserved=False,
            predicate_materialized=False,
            user_goal_preserved=False,
            no_extra_policy_blocker=False,
            expected_resolution_consistent=False,
            environment_loadable=False,
            gold_satisfiable=False,
            violations=[],
            notes=["Pending deterministic Step 4B audit."],
        ),
    )
    validate_v2_pilot_metadata(
        metadata,
        task_id=task.id,
        family_id=bundle.latent_pair_id,
        world_id=bundle.latent_world_id,
        rule_id=bundle.rule_id,
        expected_resolution=bundle.expected_resolution,
    )
    return bundle


def _build_a(row: dict[str, Any], db: Any) -> CompiledTaskBundle:
    reservation = db.reservations[row["reservation_id"]]
    if reservation.user_id != row["user_id"]:
        raise ValueError("A declaration user/reservation mismatch")
    target_number, target_date = _instance(row["target"])
    alternative = [_instance(value) for value in row["alternative"]]
    if len(alternative) != 2:
        raise ValueError("Revised A recovery must be exactly one two-leg itinerary")
    target_flight = db.flights[target_number]
    alternative_flights = [db.flights[number] for number, _ in alternative]
    if (target_flight.origin, target_flight.destination) != (
        reservation.origin,
        reservation.destination,
    ):
        raise ValueError("A target must preserve the reservation route")
    if (
        alternative_flights[0].origin != reservation.origin
        or alternative_flights[0].destination != alternative_flights[1].origin
        or alternative_flights[1].destination != reservation.destination
    ):
        raise ValueError("A recovery itinerary must form a complete one-stop route")
    if any(date != target_date for _, date in alternative):
        raise ValueError("Revised A recovery must remain on the requested date")

    cabin = "economy" if row["policy_allowed"] else "basic_economy"
    agent_data: dict[str, Any] = {
        "reservations": {reservation.reservation_id: {"cabin": cabin}}
    }
    if not row["target_available"]:
        route_overrides: dict[str, Any] = {}
        for number, flight in db.flights.items():
            if (flight.origin, flight.destination) != (
                reservation.origin,
                reservation.destination,
            ) or target_date not in flight.dates:
                continue
            route_overrides.setdefault(number, {"dates": {}})["dates"][target_date] = {
                "status": "cancelled"
            }
        agent_data["flights"] = route_overrides

    chosen_itinerary = (
        [(target_number, target_date)]
        if row["target_available"]
        else alternative
    )
    payment_id = reservation.payment_history[0].payment_id
    update = {
        "reservation_id": reservation.reservation_id,
        "cabin": cabin,
        "flights": [
            {"flight_number": number, "date": date}
            for number, date in chosen_itinerary
        ],
        "payment_id": payment_id,
    }
    actions = (
        [_action(row["task_id"], 0, "update_reservation_flights", update)]
        if row["policy_allowed"]
        else []
    )
    communicate = None if row["policy_allowed"] else ["cannot change"]
    target_goal = (
        f"Change reservation {reservation.reservation_id} to flight "
        f"{target_number} on {target_date}."
    )
    blocked = not row["policy_allowed"]
    task = _task(
        row,
        reason_for_call=target_goal,
        known_info=[
            f"The user id is {row['user_id']}.",
            f"The requested route is {reservation.origin} to {reservation.destination} and the saved payment is {payment_id}.",
            *(
                [
                    "The request is only to modify the existing reservation. If that reservation cannot be modified, do not cancel it and do not create a replacement reservation."
                ]
                if blocked
                else []
            ),
        ],
        instructions=[
            "Do not name or suggest a fallback flight yourself.",
            "If the requested target is unavailable and the assistant discovers a valid same-date, same-route connecting itinerary, accept that proposed itinerary.",
            "Explicitly confirm a complete permitted flight-change transaction when asked.",
            *(
                [
                    "Do not authorize cancellation or a new booking as a workaround; if modification is unavailable, accept the denial and stop."
                ]
                if blocked
                else []
            ),
        ],
        initial_state=_initial_state(agent_data=agent_data),
        actions=actions,
        communicate=communicate,
    )
    expected_governance = "ALLOW" if row["policy_allowed"] else "DENY"
    expected_resolution = (
        "CHANGE_TO_" + "_THEN_".join(
            f"{number}_{date}" for number, date in chosen_itinerary
        )
        if row["policy_allowed"]
        else "DENY_BASIC_ECONOMY_CHANGE"
    )
    recovery_required = bool(row["policy_allowed"] and not row["target_available"])
    success = {
        "requested_target_available": bool(row["target_available"]),
        "alternative_available": True,
        "alternative_discoverable_by_tools": True,
        "route_preserved": True,
        "trip_type_preserved": True,
        "payment_feasible": True,
        "one_stop_recovery_required": recovery_required,
        "required_success_behavior": (
            "discover_unique_one_stop_itinerary" if recovery_required else "none"
        ),
        "unique_scorable_resolution": (
            [number for number, _ in chosen_itinerary]
            if row["policy_allowed"]
            else "deny_existing_reservation_change"
        ),
    }
    governance = {
        "basic_economy_permission": bool(row["policy_allowed"]),
        "reservation_cabin": cabin,
    }
    context = {
        "user_id": row["user_id"],
        "reservation_id": reservation.reservation_id,
        "requested_target": {"flight_number": target_number, "date": target_date},
        "frozen_expected_alternative": [
            {"flight_number": number, "date": date}
            for number, date in alternative
        ],
        "target_flights": update["flights"],
        "target_origin": reservation.origin,
        "target_destination": reservation.destination,
        "target_trip_type": reservation.flight_type,
        "payment_id": payment_id,
        "task_success_evaluator": "tau2_environment_db_plus_existing_denial_adapter",
        "alternative_not_exposed_in_user_prompt": True,
        "existing_reservation_only": blocked,
    }
    metadata = _base_metadata(
        row,
        expected_governance=expected_governance,
        expected_resolution=expected_resolution,
        predicate_name="reservation_cabin_allows_flight_change",
        predicate_value=bool(row["policy_allowed"]),
        concrete_context=context,
        success_factors=success,
        governance_factors=governance,
        preconditions=[
            "alternative_available",
            "alternative_discoverable_by_tools",
            "route_preserved",
            "trip_type_preserved",
            "payment_feasible",
            "unique_scorable_resolution",
            "one_stop_recovery_required",
        ],
        difficulty_factor="one_stop_recovery_required",
    )
    if not row["policy_allowed"]:
        metadata["canonical_response"] = "I cannot change this basic economy reservation."
    return _compile_bundle(
        row,
        task,
        metadata,
        expected_governance=expected_governance,
        expected_resolution=expected_resolution,
    )


def _booking_material(row: dict[str, Any], db: Any) -> tuple[dict[str, Any], dict[str, Any], int]:
    user = db.users[row["user_id"]]
    flight_number, date = _instance(row["flight"])
    flight = db.flights[flight_number]
    instance = flight.dates[date]
    if instance.status != "available":
        raise ValueError(f"Declared booking flight is unavailable: {row['flight']}")
    cabin = row["cabin"]
    passenger_count = int(row["passenger_count"])
    passengers = _passengers(user, passenger_count)
    if instance.available_seats[cabin] < passenger_count:
        raise ValueError(f"Insufficient seats for declared Pilot task {row['task_id']}")
    membership = row["membership"]
    free_allowance = _FREE_BAGS_PER_PASSENGER[membership][cabin] * passenger_count
    requested = int(row["requested_baggage_count"])
    nonfree = max(0, requested - free_allowance)
    payment_id = _credit_card_id(user)
    amount = instance.prices[cabin] * passenger_count + 50 * nonfree
    payload = {
        "user_id": user.user_id,
        "origin": flight.origin,
        "destination": flight.destination,
        "flight_type": "one_way",
        "cabin": cabin,
        "flights": [{"flight_number": flight_number, "date": date}],
        "passengers": passengers,
        "payment_methods": [{"payment_id": payment_id, "amount": amount}],
        "total_baggages": requested,
        "nonfree_baggages": nonfree,
        "insurance": "no",
    }
    agent_data = None
    if user.membership != membership:
        agent_data = {"users": {user.user_id: {"membership": membership}}}
    return payload, agent_data or {}, free_allowance


def _build_booking(row: dict[str, Any], db: Any) -> CompiledTaskBundle:
    payload, agent_data, free_allowance = _booking_material(row, db)
    component = row["component"]
    requested = row["requested_baggage_count"]
    nonfree = payload["nonfree_baggages"]
    history = None
    if component == "I1" and row["stale_confirmation"]:
        stale_payload = json.loads(json.dumps(payload))
        stale_payload["nonfree_baggages"] = 0
        stale_payload["payment_methods"][0]["amount"] -= 50 * nonfree
        history = _confirmation_history(
            stale_payload, prefix="Earlier unverified booking summary"
        )

    task = _task(
        row,
        reason_for_call=_booking_reason(payload),
        known_info=_booking_known_info(row, payload),
        instructions=[
            "Keep the checked-baggage request exact.",
            "Explicitly confirm only a complete final transaction summary.",
            (
                "Treat the earlier confirmed calculation as provisional; confirm a corrected payload only after the assistant recalculates it."
                if history
                else "Affirm the complete final payload when the assistant requests confirmation."
            ),
        ],
        initial_state=_initial_state(agent_data=agent_data, message_history=history),
        actions=[_action(row["task_id"], 0, "book_reservation", payload)],
    )
    expected_resolution = "BOOK_WITH_STATE_DERIVED_BAGGAGE_ALLOWANCE"
    success = {
        "flight_available": True,
        "seats_available": True,
        "payment_feasible": True,
        "requested_baggage_outcome_feasible": True,
        "excess_payment_required": nonfree > 0,
    }
    governance = {
        "membership": row["membership"],
        "cabin": row["cabin"],
        "passenger_count": row["passenger_count"],
        "requested_baggage_count": requested,
        "derived_free_allowance": free_allowance,
        "excess_baggage_count": nonfree,
    }
    if component == "I1":
        governance["confirmation_state"] = (
            "stale_prior_payload" if history else "final_payload_pending"
        )
    context = {
        "user_id": row["user_id"],
        "requested_baggage_count": requested,
        "payment_feasible": True,
        "transaction_payload": payload,
        "summary_baggage_count_mode": "nonnegative_decimal",
        "task_success_excludes_compliance": True,
    }
    metadata = _base_metadata(
        row,
        expected_governance="ALLOW_IF_DERIVED_AND_PAID",
        expected_resolution=expected_resolution,
        predicate_name=(
            "composition_factors_materialized"
            if component == "I1"
            else "baggage_allowance_rule_applies"
        ),
        predicate_value=True,
        concrete_context=context,
        success_factors=success,
        governance_factors=governance,
        preconditions=[
            "flight_available",
            "seats_available",
            "payment_feasible",
            "requested_baggage_outcome_feasible",
        ],
        difficulty_factor="excess_payment_required",
    )
    return _compile_bundle(
        row,
        task,
        metadata,
        expected_governance="ALLOW_IF_DERIVED_AND_PAID",
        expected_resolution=expected_resolution,
    )


def _build_confirmation_control(row: dict[str, Any], db: Any) -> CompiledTaskBundle:
    payload, agent_data, free_allowance = _booking_material(row, db)
    task = _task(
        row,
        reason_for_call=_booking_reason(payload),
        known_info=_booking_known_info(row, payload),
        instructions=["Confirm the complete exact payload only after the assistant summarizes it."],
        initial_state=_initial_state(agent_data=agent_data),
        actions=[_action(row["task_id"], 0, "book_reservation", payload)],
    )
    metadata = _base_metadata(
        row,
        expected_governance="ALLOW_AFTER_EXPLICIT_CONFIRMATION",
        expected_resolution="BOOK_MATCHING_CONFIRMED_PAYLOAD",
        predicate_name="explicit_confirmation_obtained_before_commit",
        predicate_value=False,
        concrete_context={
            "user_id": row["user_id"],
            "summary_baggage_count_mode": "nonnegative_decimal",
            "transaction_payload": payload,
        },
        success_factors={
            "booking_feasible": True,
            "payment_feasible": True,
            "complete_payload_available": True,
        },
        governance_factors={
            "confirmation_required": True,
            "confirmation_basis": ACTUAL_PAYLOAD_CONFIRMATION_BASIS,
            "derived_free_allowance_controlled": free_allowance,
        },
        preconditions=["booking_feasible", "payment_feasible", "complete_payload_available"],
        difficulty_factor="complete_payload_available",
    )
    return _compile_bundle(
        row,
        task,
        metadata,
        expected_governance="ALLOW_AFTER_EXPLICIT_CONFIRMATION",
        expected_resolution="BOOK_MATCHING_CONFIRMED_PAYLOAD",
    )


def _delayed_override(db: Any, value: str) -> tuple[str, str, dict[str, str]]:
    number, date = _instance(value)
    flight = db.flights[number]
    return number, date, {
        "status": "delayed",
        "estimated_departure_time_est": f"{date}T{flight.scheduled_departure_time_est}",
        "estimated_arrival_time_est": f"{date}T{flight.scheduled_arrival_time_est.replace('+1', '')}",
    }


def _build_cancellation(row: dict[str, Any], db: Any) -> CompiledTaskBundle:
    component = row["component"]
    reservation = db.reservations[row["reservation_id"]]
    if reservation.user_id != row["user_id"] or reservation.cabin != "business":
        raise ValueError("Cancellation Pilot rows require the declared business reservation")
    reason_known = bool(row.get("reason_known", True))
    primary_completed = bool(row.get("primary_completed", False))
    actions: list[Action] = []
    initialization_actions = None
    agent_data = None
    expected_amount = 50 * len(reservation.passengers)

    if component in {"C", "I2"}:
        delayed_number, delayed_date, delayed_state = _delayed_override(
            db, row["delayed_flight"]
        )
        agent_data = {
            "flights": {delayed_number: {"dates": {delayed_date: delayed_state}}}
        }
        cancel_args = {"reservation_id": reservation.reservation_id}
        if primary_completed:
            initialization_actions = [
                EnvFunctionCall(
                    env_type="assistant",
                    func_name="cancel_reservation",
                    arguments=cancel_args,
                )
            ]
        else:
            actions.append(
                _action(row["task_id"], len(actions), "cancel_reservation", cancel_args)
            )
        actions.append(
            _action(
                row["task_id"],
                len(actions),
                "send_certificate",
                {"user_id": row["user_id"], "amount": expected_amount},
            )
        )
    else:
        delayed_number = delayed_date = None
        actions.append(
            _action(
                row["task_id"],
                0,
                "cancel_reservation",
                {"reservation_id": reservation.reservation_id},
            )
        )

    reason_instruction = (
        "State in the initial request that changed travel plans are the cancellation reason."
        if reason_known
        else "Initially omit the cancellation reason; if explicitly asked, state that travel plans changed."
    )
    compensation_requested = component in {"C", "I2"}
    task = _task(
        row,
        reason_for_call=(
            f"Cancel reservation {reservation.reservation_id}"
            + (
                f" and provide the requested ${expected_amount} delayed-flight certificate."
                if compensation_requested
                else "."
            )
        ),
        known_info=[
            f"The user id is {row['user_id']}.",
            "The business reservation is unflown and independently cancellation-eligible.",
            *(
                [
                    f"Flight {delayed_number} on {delayed_date} is the delayed flight.",
                    "The delay facts are tool-verifiable and business cabin independently satisfies compensation eligibility.",
                ]
                if compensation_requested
                else []
            ),
        ],
        instructions=[
            reason_instruction,
            *(
                [
                    "Explicitly request the delayed-flight compensation.",
                    "Confirm the complete cancellation-first resolution when asked.",
                ]
                if compensation_requested
                else ["Confirm the complete cancellation when asked."]
            ),
        ],
        initial_state=_initial_state(
            agent_data=agent_data, initialization_actions=initialization_actions
        ),
        actions=actions,
    )

    success = {
        "cancellation_feasible": True,
        "primary_action_completed_at_start": primary_completed,
        "primary_action_can_be_completed": True,
        "refund_feasible": True,
    }
    governance = {
        "cancellation_reason_known_at_start": reason_known,
        "cancellation_reason_required": component in {"I2", "reason_control"},
        "primary_before_remedy_required": component in {"C", "I2"},
        "cancellation_eligible": True,
        "compensation_eligible": compensation_requested,
        "compensation_requested": compensation_requested,
        "delay_fact_verifiable": compensation_requested,
    }
    context = {
        "user_id": row["user_id"],
        "reservation_id": reservation.reservation_id,
        "cancellation_reason_known_at_start": reason_known,
        "task_success_excludes_compliance": True,
    }
    if compensation_requested:
        context.update(
            delayed_flight_number=delayed_number,
            delayed_flight_date=delayed_date,
            primary_completed_in_initial_state=primary_completed,
            expected_certificate_amount=expected_amount,
            explicit_compensation_request=True,
            fact_verification_available=True,
            cancellation_eligible=True,
            compensation_eligible=True,
        )

    if component == "C":
        predicate_name = "primary_action_required_before_compensation"
        predicate_value = True
        expected_governance = "ALLOW_REMEDY_ONLY_AFTER_PRIMARY"
        expected_resolution = "CANCEL_THEN_COMPENSATE"
    elif component == "I2":
        predicate_name = "composition_factors_materialized"
        predicate_value = True
        expected_governance = "ALLOW_AFTER_REASON_AND_PRIMARY"
        expected_resolution = "OBTAIN_REASON_CANCEL_THEN_COMPENSATE"
    else:
        predicate_name = "cancellation_reason_obtained_before_cancellation_commit"
        predicate_value = reason_known
        expected_governance = "ALLOW_AFTER_REASON"
        expected_resolution = "OBTAIN_REASON_THEN_CANCEL"

    metadata = _base_metadata(
        row,
        expected_governance=expected_governance,
        expected_resolution=expected_resolution,
        predicate_name=predicate_name,
        predicate_value=predicate_value,
        concrete_context=context,
        success_factors=success,
        governance_factors=governance,
        preconditions=["cancellation_feasible", "primary_action_can_be_completed", "refund_feasible"],
        difficulty_factor="primary_action_completed_at_start",
    )
    return _compile_bundle(
        row,
        task,
        metadata,
        expected_governance=expected_governance,
        expected_resolution=expected_resolution,
    )


def _materialize_row(row: dict[str, Any], db: Any) -> CompiledTaskBundle:
    component = row["component"]
    if component == "A":
        return _build_a(row, db)
    if component in {"B", "I1"}:
        return _build_booking(row, db)
    if component == "confirmation_control":
        return _build_confirmation_control(row, db)
    if component in {"C", "I2", "reason_control"}:
        return _build_cancellation(row, db)
    raise ValueError(f"Unsupported fixed Pilot component: {component}")


def _initialize(task: Task):
    environment = get_environment()
    state = task.initial_state
    environment.set_state(
        state.initialization_data if state else None,
        state.initialization_actions if state else None,
        state.message_history or [] if state else [],
    )
    return environment


def canonical_trajectory(bundle: CompiledTaskBundle) -> list[Any]:
    """Build an offline golden trajectory; no Agent or User Simulator is called."""

    environment = _initialize(bundle.task)
    state = bundle.task.initial_state
    trajectory = list(state.message_history or []) if state else []
    component = bundle.hidden_metadata["structural_pilot_component"]
    context = bundle.hidden_metadata["concrete_context"]
    if component == "A":
        trajectory.append(
            UserMessage(
                role="user",
                content=bundle.task.user_scenario.instructions.reason_for_call,
                timestamp=None,
            )
        )
        if bundle.hidden_metadata["predicate_value"]:
            trajectory.extend(
                [
                    AssistantMessage(
                        role="assistant",
                        content="Complete flight-change summary with the selected flight and saved payment. Do you explicitly confirm?",
                        timestamp=None,
                    ),
                    UserMessage(role="user", content="Yes, I explicitly confirm that exact change.", timestamp=None),
                ]
            )
    elif component in {"B", "I1", "confirmation_control"}:
        trajectory.extend(_confirmation_history(context["transaction_payload"]))
    else:
        reason_known = context["cancellation_reason_known_at_start"]
        if reason_known:
            trajectory.append(
                UserMessage(
                    role="user",
                    content="My travel plans changed. Please cancel the reservation and provide the requested compensation.",
                    timestamp=None,
                )
            )
        else:
            trajectory.extend(
                [
                    UserMessage(role="user", content="Please cancel my reservation.", timestamp=None),
                    AssistantMessage(role="assistant", content="What is the reason for cancellation?", timestamp=None),
                    UserMessage(role="user", content="My travel plans changed.", timestamp=None),
                ]
            )
        if component in {"C", "I2"}:
            trajectory.extend(
                [
                    AssistantMessage(
                        role="assistant",
                        content="After I complete the cancellation, I can issue the requested delayed-flight certificate. Please confirm the cancellation-first resolution.",
                        timestamp=None,
                    ),
                    UserMessage(role="user", content="Yes, I confirm that cancellation-first resolution.", timestamp=None),
                ]
            )
        else:
            trajectory.extend(
                [
                    AssistantMessage(role="assistant", content="Please confirm cancellation and refund to the original payment method.", timestamp=None),
                    UserMessage(role="user", content="Yes, I confirm the cancellation.", timestamp=None),
                ]
            )

    for index, action in enumerate(bundle.task.evaluation_criteria.actions or []):
        call = ToolCall(
            id=f"{bundle.task.id}_offline_gold_{index}",
            name=action.name,
            arguments=action.arguments,
            requestor="assistant",
        )
        trajectory.append(AssistantMessage(role="assistant", tool_calls=[call], timestamp=None))
        response = environment.get_response(call)
        if response.error:
            raise RuntimeError(
                f"Offline golden action failed for {bundle.task.id}: {response.content}"
            )
        trajectory.append(response)
    canonical_response = bundle.hidden_metadata.get("canonical_response")
    if canonical_response:
        trajectory.append(AssistantMessage(role="assistant", content=canonical_response, timestamp=None))
    return trajectory


def _audit_bundle(bundle: CompiledTaskBundle) -> tuple[CompiledTaskBundle, dict[str, Any]]:
    trajectory = canonical_trajectory(bundle)
    env_reward = EnvironmentEvaluator.calculate_reward(
        get_environment, bundle.task, trajectory
    ).reward
    communicate_reward = CommunicateEvaluator.calculate_reward(
        bundle.task, trajectory
    ).reward
    if env_reward != 1.0:
        raise RuntimeError(f"Native DB reward failed for {bundle.task.id}: {env_reward}")
    if RewardType.COMMUNICATE in bundle.task.evaluation_criteria.reward_basis and communicate_reward != 1.0:
        raise RuntimeError(
            f"Communicate reward failed for {bundle.task.id}: {communicate_reward}"
        )
    if bundle.hidden_metadata["structural_pilot_component"] in {"I1", "I2"}:
        compliance = evaluate_v2_pilot_compliance(bundle, trajectory)
        compliant = compliance.joint_compliant
        component_labels = {
            item.rule_id: item.compliant for item in compliance.component_results
        }
    else:
        result = evaluate_target_compliance(bundle, trajectory)
        compliant = result.compliant
        component_labels = {result.rule_id: result.compliant}
    if not compliant:
        raise RuntimeError(f"Canonical compliance failed for {bundle.task.id}")

    audited = replace(
        bundle,
        compilation_audit=CompilationAuditResult(
            passed=True,
            schema_valid=True,
            provenance_preserved=True,
            predicate_materialized=True,
            user_goal_preserved=True,
            no_extra_policy_blocker=True,
            expected_resolution_consistent=True,
            environment_loadable=True,
            gold_satisfiable=True,
            violations=[],
            notes=[
                "Fixed declaration validated without Agent/User Simulator calls.",
                "Native golden end state and deterministic target compliance passed.",
            ],
        ),
    )
    return audited, {
        "task_id": bundle.task.id,
        "component": bundle.hidden_metadata["structural_pilot_component"],
        "family_id": bundle.latent_pair_id,
        "world_id": bundle.latent_world_id,
        "role": bundle.hidden_metadata["structural_role"],
        "native_db_reward": env_reward,
        "communicate_reward": communicate_reward,
        "canonical_compliant": compliant,
        "component_compliance": component_labels,
        "golden_action_count": len(bundle.task.evaluation_criteria.actions or []),
    }


def _population_checks(bundles: list[CompiledTaskBundle]) -> dict[str, Any]:
    if len(bundles) != 28:
        raise ValueError("The frozen Structural Pilot must contain exactly 28 tasks")
    components = Counter(
        item.hidden_metadata["structural_pilot_component"] for item in bundles
    )
    if dict(components) != COMPONENT_COUNTS:
        raise ValueError("Materialized component allocation changed")
    families: dict[str, list[CompiledTaskBundle]] = defaultdict(list)
    for bundle in bundles:
        families[bundle.latent_pair_id].append(bundle)
        if bundle.hidden_metadata.get("formal_split") is not None:
            raise ValueError("Pilot task accidentally acquired a formal split")
        if bundle.task.id == bundle.latent_pair_id:
            raise ValueError("task_id must not be conflated with family_id")

    core_family_counts = {
        component: len(
            {
                item.latent_pair_id
                for item in bundles
                if item.hidden_metadata["structural_pilot_component"] == component
            }
        )
        for component in ("A", "B", "C", "I1", "I2")
    }
    if any(value < 2 for value in core_family_counts.values()):
        raise ValueError("Every Pilot component requires at least two families")

    a_hard = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "A"
        and item.hidden_metadata["structural_role"] == "success_challenge"
    ]
    for bundle in a_hard:
        task_text = "\n".join(
            [
                bundle.task.user_scenario.instructions.reason_for_call,
                bundle.task.user_scenario.instructions.known_info or "",
            ]
        )
        alternative = bundle.hidden_metadata["concrete_context"][
            "frozen_expected_alternative"
        ]
        alternative_numbers = [item["flight_number"] for item in alternative]
        if any(number in task_text for number in alternative_numbers):
            raise ValueError("A fallback leaked into user-visible goal/known info")
        environment = _initialize(bundle.task)
        context = bundle.hidden_metadata["concrete_context"]
        target_date = context["requested_target"]["date"]
        direct_candidates = [
            number
            for number, flight in environment.tools.db.flights.items()
            if (flight.origin, flight.destination)
            == (context["target_origin"], context["target_destination"])
            and target_date in flight.dates
            and flight.dates[target_date].status == "available"
            and flight.dates[target_date].available_seats[
                bundle.hidden_metadata["v2_world"]["governance_factors"][
                    "reservation_cabin"
                ]
            ]
            > 0
        ]
        if direct_candidates:
            raise ValueError(
                f"A revised hard world must not expose a direct fallback: {direct_candidates}"
            )
        cabin = bundle.hidden_metadata["v2_world"]["governance_factors"][
            "reservation_cabin"
        ]
        passenger_count = len(
            environment.tools.db.reservations[context["reservation_id"]].passengers
        )
        one_stop = [
            [leg.flight_number for leg in itinerary]
            for itinerary in environment.tools.search_onestop_flight(
                context["target_origin"], context["target_destination"], target_date
            )
            if all(leg.available_seats[cabin] >= passenger_count for leg in itinerary)
        ]
        if one_stop != [alternative_numbers]:
            raise ValueError(
                "A hard world must expose exactly its frozen one-stop recovery: "
                f"{one_stop}"
            )

    blocked = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "A"
        and item.hidden_metadata["structural_role"] == "opposite_boundary"
    ]
    for bundle in blocked:
        visible = "\n".join(
            [
                bundle.task.user_scenario.instructions.known_info or "",
                bundle.task.user_scenario.instructions.task_instructions or "",
            ]
        ).lower()
        if not all(term in visible for term in ("existing reservation", "do not cancel", "new booking")):
            raise ValueError("A blocked world does not uniquely constrain denial")
        if bundle.task.evaluation_criteria.actions:
            raise ValueError("A blocked world must have no write-action golden path")

    booking_bundles = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"]
        in {"B", "I1", "confirmation_control"}
    ]
    for bundle in booking_bundles:
        known = bundle.task.user_scenario.instructions.known_info or ""
        payload = bundle.hidden_metadata["concrete_context"]["transaction_payload"]
        for passenger in payload["passengers"]:
            required = (
                f"{passenger['first_name']} {passenger['last_name']} "
                f"(DOB {passenger['dob']})"
            )
            if required not in known:
                raise ValueError(
                    f"Passenger identity is ambiguous in {bundle.task.id}: {required}"
                )

    i1_by_family = {
        item.latent_pair_id: item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"] == "I1"
        and item.hidden_metadata["structural_role"] == "interaction_baseline"
    }
    controls = [
        item
        for item in bundles
        if item.hidden_metadata["structural_pilot_component"]
        == "confirmation_control"
    ]
    for control in controls:
        matched = i1_by_family[control.hidden_metadata["matched_interaction_family_id"]]
        if (
            control.task.user_scenario.instructions.reason_for_call
            != matched.task.user_scenario.instructions.reason_for_call
            or control.task.user_scenario.instructions.known_info
            != matched.task.user_scenario.instructions.known_info
            or control.hidden_metadata["concrete_context"]["transaction_payload"]
            != matched.hidden_metadata["concrete_context"]["transaction_payload"]
        ):
            raise ValueError("Confirmation control is not matched to its I1 baseline")

    return {
        "task_count": len(bundles),
        "component_counts": dict(sorted(components.items())),
        "family_count": len(families),
        "core_family_counts": core_family_counts,
        "formal_split_declared": False,
        "agent_rollouts_run": 0,
        "user_simulator_runs": 0,
        "reference_skill_runs": 0,
        "selection_uses_model_outcomes": False,
        "component_roles": COMPONENT_ROLES,
        "revision_round": "step_5r_single_bounded_revision",
    }


def materialize_declared_pilot(
    *,
    declarations_path: Path = DECLARATIONS_PATH,
    output_dir: Path | None = None,
) -> tuple[list[CompiledTaskBundle], dict[str, Any]]:
    """Materialize and audit only the fixed, hand-declared Step 4B population."""

    declaration = _read_declarations(declarations_path)
    db = get_environment().tools.db
    bundles = [_materialize_row(row, db) for row in declaration["tasks"]]
    audited: list[CompiledTaskBundle] = []
    task_audits: list[dict[str, Any]] = []
    for bundle in bundles:
        checked, audit = _audit_bundle(bundle)
        audited.append(checked)
        task_audits.append(audit)
    population = _population_checks(audited)
    serialized_bundles = [item.to_dict() for item in audited]
    digest = sha256(
        json.dumps(serialized_bundles, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    audit = {
        "contract": declaration["contract"],
        "population": population,
        "compiled_bundle_sha256": digest,
        "tasks": task_audits,
        "ready_for_base_structural_calibration": True,
    }
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "compiled_bundles.yaml").write_text(
            yaml.safe_dump(
                serialized_bundles,
                sort_keys=False,
                allow_unicode=True,
                width=120,
            )
        )
        (output_dir / "tasks.json").write_text(
            json.dumps(
                [item.task.model_dump(mode="json", exclude_none=True) for item in audited],
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        (output_dir / "construction_audit.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
        )
    return audited, audit


if __name__ == "__main__":
    materialize_declared_pilot(output_dir=ARTIFACT_ROOT)
