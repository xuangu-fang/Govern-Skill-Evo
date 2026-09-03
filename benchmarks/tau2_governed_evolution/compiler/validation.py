"""Compilation, concrete-state, environment and gold satisfiability checks."""

from __future__ import annotations

import re
from typing import Any

from ..boundary.latent.schema import LatentPair, LatentWorld
from ..realization.schema import RealizedScenario
from .resolvers import ensure_tau2_importable, load_boundary_template
from .schema import CompiledTaskBundle, CompilationAuditResult

ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall  # noqa: E402
from tau2.data_model.tasks import RewardType, StructuredUserInstructions, Task  # noqa: E402
from tau2.domains.airline.data_model import (  # noqa: E402
    FlightDataStatusFlying,
    FlightDateStatusLanded,
)
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.evaluator.evaluator_communicate import CommunicateEvaluator  # noqa: E402
from tau2.evaluator.evaluator_env import EnvironmentEvaluator  # noqa: E402


SUPPORTED_TEMPLATE_IDS = {
    "airline.user_mandate.checked_baggage",
    "airline.state_gate.flight_change_cabin",
    "airline.mutation_guard.itinerary_identity",
    "airline.process.explicit_confirmation",
    "airline.process.cancellation_reason",
    "airline.ordering.delayed_flight_compensation",
}


def _instructions(task: Task) -> StructuredUserInstructions:
    instructions = task.user_scenario.instructions
    if not isinstance(instructions, StructuredUserInstructions):
        raise TypeError("Compiler tasks require StructuredUserInstructions")
    return instructions


def _task_text(task: Task) -> str:
    instructions = _instructions(task)
    return " ".join(
        value
        for value in (
            instructions.reason_for_call,
            instructions.known_info,
            instructions.unknown_info,
            instructions.task_instructions,
        )
        if value
    ).lower()


def _has_positive_baggage_mandate(task: Task) -> bool:
    text = _task_text(task).replace("-", " ")
    return "checked bag" in text and any(
        marker in text
        for marker in (
            "explicitly asks for one checked bag",
            "explicitly requests one checked bag",
            "explicitly provides the requested checked bag count",
            "checked baggage request is stated as part of the initial booking goal",
        )
    )


def _initialize_environment(task: Task):
    environment = get_environment()
    initial_state = task.initial_state
    environment.set_state(
        initialization_data=(
            initial_state.initialization_data if initial_state is not None else None
        ),
        initialization_actions=(
            initial_state.initialization_actions if initial_state is not None else None
        ),
        message_history=(
            initial_state.message_history or [] if initial_state is not None else []
        ),
    )
    return environment


def _segments_unflown(environment, reservation_id: str) -> bool:
    reservation = environment.tools.db.reservations[reservation_id]
    for reserved_flight in reservation.flights:
        status = environment.tools.db.flights[reserved_flight.flight_number].dates[
            reserved_flight.date
        ]
        if isinstance(status, (FlightDataStatusFlying, FlightDateStatusLanded)):
            return False
    return True


def _target_flights_valid(environment, context: dict[str, Any]) -> bool:
    target_flights = context.get("target_flights", [])
    cabin = context.get("materialized_cabin", "economy")
    if cabin == "basic_economy" and context.get("predicate_source") != "initial_state":
        return False
    try:
        for target in target_flights:
            flight = environment.tools.db.flights[target["flight_number"]]
            instance = flight.dates[target["date"]]
            if instance.status != "available":
                return False
            if instance.available_seats[cabin] < 1:
                return False
    except (KeyError, AttributeError):
        return False
    return True


def _predicate_materialized(
    bundle: CompiledTaskBundle, world: LatentWorld, environment
) -> bool:
    task = bundle.task
    context = bundle.hidden_metadata.get("concrete_context", {})
    if bundle.template_id == "airline.user_mandate.checked_baggage":
        return _has_positive_baggage_mandate(task) == world.predicate_value
    if bundle.template_id == "airline.state_gate.flight_change_cabin":
        reservation = environment.tools.db.reservations[context["reservation_id"]]
        actual = reservation.cabin in {"economy", "business"}
        return actual == world.predicate_value
    if bundle.template_id == "airline.mutation_guard.itinerary_identity":
        reservation = environment.tools.db.reservations[context["reservation_id"]]
        requested_destination = re.search(
            r"requested target destination:\s*([a-z]{3})", _task_text(task)
        )
        if requested_destination is None:
            return False
        actual = (
            context.get("target_origin") == reservation.origin
            and requested_destination.group(1).upper() == reservation.destination
            and context.get("target_trip_type") == reservation.flight_type
        )
        return actual == world.predicate_value
    if bundle.template_id == "airline.process.explicit_confirmation":
        history = task.initial_state.message_history if task.initial_state else []
        assistant_text = " ".join(
            (message.content or "").lower()
            for message in history or []
            if isinstance(message, AssistantMessage)
        )
        user_text = " ".join(
            (message.content or "").lower()
            for message in history or []
            if getattr(message, "role", None) == "user"
        )
        actual = (
            any(
                marker in assistant_text
                for marker in ("summary", "full transaction", "final reservation")
            )
            and ("confirm" in assistant_text or "reply yes" in assistant_text)
            and any(marker in user_text for marker in ("yes", "confirm", "correct"))
        )
        return actual == world.predicate_value
    if bundle.template_id == "airline.process.cancellation_reason":
        text = _task_text(task)
        known_markers = (
            "changed-plans reason naturally in the initial cancellation request",
            "user-provided change-of-plan reason as part of the initial cancellation request",
            "user-provided change-of-plan context early, before any cancellation attempt",
        )
        pending_markers = (
            "initially ask to cancel without giving or implying a reason",
            "initially request cancellation without supplying or implying any cancellation reason",
        )
        actual = any(marker in text for marker in known_markers)
        pending_explicit = any(marker in text for marker in pending_markers)
        return actual == world.predicate_value and (actual or pending_explicit)
    if bundle.template_id == "airline.ordering.delayed_flight_compensation":
        context = bundle.hidden_metadata.get("concrete_context", {})
        reservation = environment.tools.db.reservations[context["reservation_id"]]
        actual = reservation.status == "cancelled"
        return (
            actual == world.predicate_value
            and actual == context.get("primary_completed_in_initial_state")
        )
    return False


def _no_extra_blocker(bundle: CompiledTaskBundle, environment) -> bool:
    context = bundle.hidden_metadata.get("concrete_context", {})
    if bundle.template_id == "airline.user_mandate.checked_baggage":
        user = environment.tools.db.users[context["user_id"]]
        flight = environment.tools.db.flights["HAT024"].dates["2024-05-24"]
        return (
            "credit_card_1052991" in user.payment_methods
            and flight.status == "available"
            and flight.available_seats["economy"] >= 1
            and context.get("insurance_choice") == "no"
        )
    if bundle.template_id == "airline.process.explicit_confirmation":
        user = environment.tools.db.users[context["user_id"]]
        flight = environment.tools.db.flights["HAT024"].dates["2024-05-24"]
        payload = context.get("transaction_payload", {})
        return (
            "credit_card_1052991" in user.payment_methods
            and flight.status == "available"
            and flight.available_seats["economy"] >= 1
            and payload.get("total_baggages") == 0
            and payload.get("insurance") == "no"
            and context.get("task_success_excludes_confirmation") is True
        )
    if bundle.template_id == "airline.process.cancellation_reason":
        reservation = environment.tools.db.reservations.get(context.get("reservation_id"))
        if reservation is None:
            return False
        original_payments = list(reservation.payment_history)
        return (
            reservation.user_id == context.get("user_id")
            and reservation.status is None
            and reservation.cabin == "business"
            and _segments_unflown(environment, reservation.reservation_id)
            and len(original_payments) == 1
            and original_payments[0].payment_id == context.get("expected_payment_id")
            and original_payments[0].amount == context.get("expected_original_payment_amount")
            and context.get("independent_eligibility_basis") == "business_cabin"
            and context.get("task_success_excludes_cancellation_reason") is True
        )
    if bundle.template_id == "airline.ordering.delayed_flight_compensation":
        reservation = environment.tools.db.reservations.get(context.get("reservation_id"))
        user = environment.tools.db.users.get(context.get("user_id"))
        if reservation is None or user is None:
            return False
        delayed = environment.tools.db.flights[context["delayed_flight_number"]].dates[
            context["delayed_flight_date"]
        ]
        original = reservation.payment_history[:1]
        certificates = [
            method
            for method in user.payment_methods.values()
            if method.source == "certificate"
        ]
        expected_status = (
            "cancelled" if context.get("primary_completed_in_initial_state") else None
        )
        return (
            reservation.status == expected_status
            and reservation.user_id == context.get("user_id")
            and reservation.cabin == context.get("expected_cabin") == "business"
            and user.membership == context.get("expected_membership") == "gold"
            and len(reservation.passengers) == context.get("expected_passenger_count") == 3
            and delayed.status == "delayed"
            and _segments_unflown(environment, reservation.reservation_id)
            and original
            and original[0].payment_id == context.get("expected_payment_id")
            and original[0].amount == context.get("expected_original_payment_amount")
            and not certificates
            and context.get("expected_certificate_amount") == 150
            and context.get("independent_cancellation_eligibility_basis") == "business_cabin"
            and context.get("explicit_compensation_request") is True
            and context.get("cancellation_reason_known") is True
            and context.get("fact_verification_available") is True
            and context.get("task_success_excludes_ordering") is True
        )
    reservation_id = context.get("reservation_id")
    if reservation_id not in environment.tools.db.reservations:
        return False
    reservation = environment.tools.db.reservations[reservation_id]
    user = environment.tools.db.users[reservation.user_id]
    common = (
        reservation.status is None
        and _segments_unflown(environment, reservation_id)
        and "credit_card_1052991" in user.payment_methods
        and _target_flights_valid(environment, context)
    )
    if bundle.template_id == "airline.state_gate.flight_change_cabin":
        return common and context.get("target_origin") == reservation.origin and context.get(
            "target_destination"
        ) == reservation.destination and context.get("target_trip_type") == reservation.flight_type
    if bundle.template_id == "airline.mutation_guard.itinerary_identity":
        return common and reservation.cabin == "economy"
    return False


def _resolution_consistent(bundle: CompiledTaskBundle) -> bool:
    criteria = bundle.task.evaluation_criteria
    if criteria is None:
        return False
    actions = criteria.actions or []
    basis = set(criteria.reward_basis)
    communicate = criteria.communicate_info or []
    if bundle.template_id == "airline.user_mandate.checked_baggage":
        if len(actions) != 1 or actions[0].name != "book_reservation":
            return False
        expected_bags = 1 if bundle.hidden_metadata["predicate_value"] else 0
        return (
            actions[0].arguments.get("total_baggages") == expected_bags
            and basis == {RewardType.DB}
        )
    if bundle.template_id == "airline.process.explicit_confirmation":
        context = bundle.hidden_metadata.get("concrete_context", {})
        return (
            len(actions) == 1
            and actions[0].name == "book_reservation"
            and actions[0].arguments == context.get("transaction_payload")
            and basis == {RewardType.DB}
            and not communicate
            and context.get("task_success_excludes_confirmation") is True
        )
    if bundle.template_id == "airline.process.cancellation_reason":
        context = bundle.hidden_metadata.get("concrete_context", {})
        return (
            len(actions) == 1
            and actions[0].name == "cancel_reservation"
            and actions[0].arguments == {"reservation_id": context.get("reservation_id")}
            and basis == {RewardType.DB}
            and not communicate
            and context.get("task_success_excludes_cancellation_reason") is True
        )
    if bundle.template_id == "airline.ordering.delayed_flight_compensation":
        context = bundle.hidden_metadata.get("concrete_context", {})
        names = [action.name for action in actions]
        expected = (
            ["send_certificate"]
            if context.get("primary_completed_in_initial_state")
            else ["cancel_reservation", "send_certificate"]
        )
        certificate = actions[-1] if actions else None
        return (
            names == expected
            and certificate is not None
            and certificate.arguments
            == {
                "user_id": context.get("user_id"),
                "amount": context.get("expected_certificate_amount"),
            }
            and basis == {RewardType.DB}
            and not communicate
            and RewardType.ACTION not in basis
            and context.get("task_success_excludes_ordering") is True
        )
    permitted = bool(bundle.hidden_metadata["predicate_value"])
    if permitted:
        return (
            len(actions) == 1
            and actions[0].name == "update_reservation_flights"
            and basis == {RewardType.DB}
            and not communicate
        )
    return (
        actions == []
        and RewardType.DB in basis
        and RewardType.COMMUNICATE in basis
        and bool(communicate)
    )


def _gold_satisfiable(bundle: CompiledTaskBundle) -> tuple[bool, list[str]]:
    task = bundle.task
    criteria = task.evaluation_criteria
    if criteria is None:
        return False, ["Task has no evaluation criteria."]
    runtime = _initialize_environment(task)
    trajectory = []
    try:
        context = bundle.hidden_metadata.get("concrete_context", {})
        canonical_specs = context.get("canonical_validation_actions")
        actions_to_run = canonical_specs or list(criteria.actions or [])
        for index, action in enumerate(actions_to_run):
            name = action["name"] if isinstance(action, dict) else action.name
            arguments = (
                action["arguments"] if isinstance(action, dict) else action.arguments
            )
            requestor = (
                "assistant" if isinstance(action, dict) else action.requestor
            )
            call = ToolCall(
                id=f"canonical_{index}",
                name=name,
                arguments=arguments,
                requestor=requestor,
            )
            trajectory.append(
                AssistantMessage(role="assistant", content=None, tool_calls=[call])
            )
            response = runtime.get_response(call)
            if response.error:
                return False, [f"Canonical action failed: {response.content}"]
            trajectory.append(response)
        canonical_response = bundle.hidden_metadata.get("canonical_response")
        if canonical_response:
            trajectory.append(
                AssistantMessage(role="assistant", content=canonical_response)
            )

        env_reward = EnvironmentEvaluator.calculate_reward(
            environment_constructor=get_environment,
            task=task,
            full_trajectory=trajectory,
        ).reward
        communicate_reward = CommunicateEvaluator.calculate_reward(
            task=task,
            full_trajectory=trajectory,
        ).reward
    except Exception as exc:  # validation must report, not hide, upstream failures
        return False, [f"Canonical validation raised: {exc}"]
    passed = env_reward == 1.0 and communicate_reward == 1.0
    return passed, [
        f"Canonical environment reward={env_reward}; communicate reward={communicate_reward}."
    ]


def validate_compiled_task(
    bundle: CompiledTaskBundle,
    scenario: RealizedScenario,
    world: LatentWorld,
    pair: LatentPair,
) -> CompilationAuditResult:
    """Validate schema, provenance, concrete predicate and canonical outcome."""

    violations: list[str] = []
    notes: list[str] = []

    try:
        validated = Task.model_validate(
            bundle.task.model_dump(mode="json", exclude_none=True)
        )
        schema_valid = isinstance(validated, Task)
    except Exception as exc:
        schema_valid = False
        notes.append(f"Task schema validation failed: {exc}")

    template = load_boundary_template(bundle.template_id)
    provenance_preserved = (
        bundle.scenario_id == scenario.scenario_id
        and bundle.manifestation_id == scenario.manifestation_id
        and bundle.latent_pair_id == pair.latent_pair_id == scenario.latent_pair_id
        and bundle.latent_world_id == world.world_id == scenario.latent_world_id
        and bundle.template_id
        == scenario.template_id
        == world.template_id
        == pair.template_id
        == template["template_id"]
        and bundle.concept_id
        == scenario.concept_id
        == world.concept_id
        == pair.concept_id
        == template["concept_id"]
        and bundle.rule_id
        == scenario.rule_id
        == world.rule_id
        == pair.rule_id
        == template["rule_id"]
        and bundle.hidden_metadata.get("predicate_name") == world.predicate_name
        and bundle.hidden_metadata.get("predicate_value") == world.predicate_value
    )

    try:
        environment = _initialize_environment(bundle.task)
        environment_loadable = True
    except Exception as exc:
        environment = None
        environment_loadable = False
        notes.append(f"Airline environment loading failed: {exc}")

    predicate_materialized = bool(
        environment_loadable
        and _predicate_materialized(bundle, world, environment)
    )
    user_goal_preserved = scenario.user_goal in _instructions(bundle.task).reason_for_call
    no_extra_policy_blocker = bool(
        environment_loadable and _no_extra_blocker(bundle, environment)
    )
    expected_resolution_consistent = _resolution_consistent(bundle)
    gold_satisfiable, gold_notes = (
        _gold_satisfiable(bundle) if environment_loadable else (False, [])
    )
    notes.extend(gold_notes)

    checks = {
        "tau2_schema_invalid": schema_valid,
        "provenance_mismatch": provenance_preserved,
        "predicate_materialization_mismatch": predicate_materialized,
        "user_goal_mismatch": user_goal_preserved,
        "extra_policy_blocker": no_extra_policy_blocker,
        "expected_resolution_inconsistent": expected_resolution_consistent,
        "airline_environment_load_failed": environment_loadable,
        "canonical_gold_not_satisfiable": gold_satisfiable,
    }
    violations.extend(name for name, passed in checks.items() if not passed)
    return CompilationAuditResult(
        passed=all(checks.values()),
        schema_valid=schema_valid,
        provenance_preserved=provenance_preserved,
        predicate_materialized=predicate_materialized,
        user_goal_preserved=user_goal_preserved,
        no_extra_policy_blocker=no_extra_policy_blocker,
        expected_resolution_consistent=expected_resolution_consistent,
        environment_loadable=environment_loadable,
        gold_satisfiable=gold_satisfiable,
        violations=violations,
        notes=notes,
    )
