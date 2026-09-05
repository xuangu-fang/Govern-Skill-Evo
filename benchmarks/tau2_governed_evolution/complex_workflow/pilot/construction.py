"""Materialize and audit the 15 hand-declared CW2 Airline workflows.

This is intentionally a declaration adapter, not a workflow generator.  It
maps the fixed YAML rows to native tau2 ``Task`` objects, replays each declared
golden path offline, and checks the construction contract.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from ...compiler.resolvers import ensure_tau2_importable
from ...compiler.schema import CompiledTaskBundle, CompilationAuditResult
from ...compliance.oracle import evaluate_target_compliance
from ...compliance.templates import _FREE_BAGS_PER_PASSENGER

ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage  # noqa: E402
from tau2.data_model.tasks import (  # noqa: E402
    Action,
    Description,
    EvaluationCriteria,
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
FREEZE_MANIFEST_PATH = PILOT_ROOT / "freeze_manifest.json"

ARCHETYPE_COUNTS = {
    "per_entity_portfolio_triage": 3,
    "constraint_coupled_booking_payment": 3,
    "policy_triggered_fallback": 2,
    "multi_attribute_mutation": 2,
    "mid_dialogue_goal_accumulation": 3,
    "authority_conflict_protected_remedy": 2,
}

_WRITE_TOOLS = {
    "book_reservation",
    "cancel_reservation",
    "update_reservation_baggages",
    "update_reservation_flights",
    "update_reservation_passengers",
    "send_certificate",
}

_COMPONENT_SCHEMA = {
    "airline.book.baggage_allowance": (
        "airline.quantitative.baggage_allowance",
        "airline.quantitative_policy_constraints",
    ),
    "airline.action.explicit_confirmation": (
        "airline.process.explicit_confirmation",
        "airline.transaction_commit_confirmation",
    ),
    "airline.cancel.reason_required": (
        "airline.process.cancellation_reason",
        "airline.operation_input_completeness",
    ),
    "airline.modify.itinerary_invariants": (
        "airline.mutation_guard.itinerary_identity",
        "airline.mutation_invariant_guard",
    ),
}


def read_declarations(path: Path = DECLARATIONS_PATH) -> dict[str, Any]:
    declaration = yaml.safe_load(path.read_text())
    if not isinstance(declaration, dict) or not isinstance(declaration.get("tasks"), list):
        raise ValueError("CW2 declaration must contain a tasks list")
    rows = declaration["tasks"]
    if declaration.get("task_count") != 15 or len(rows) != 15:
        raise ValueError("CW2 Pilot must contain exactly 15 tasks")
    if declaration.get("family_count") != 15:
        raise ValueError("CW2 Pilot must declare exactly 15 families")
    if declaration.get("formal_split") is not None:
        raise ValueError("CW2 Pilot must not declare a formal split")
    if declaration.get("model_outcomes_used") is not False:
        raise ValueError("CW2 selection must explicitly exclude model outcomes")
    if declaration.get("archetype_counts") != ARCHETYPE_COUNTS:
        raise ValueError("CW2 archetype allocation drifted")
    task_ids = [row.get("task_id") for row in rows]
    family_ids = [row.get("family_id") for row in rows]
    if len(set(task_ids)) != 15 or len(set(family_ids)) != 15:
        raise ValueError("task_id and family_id must each be unique")
    if any(task_id == family_id for task_id, family_id in zip(task_ids, family_ids)):
        raise ValueError("A workflow family must not be conflated with a task id")
    return declaration


def _task(row: dict[str, Any]) -> Task:
    communication = []
    expected = row.get("expected_reconciliation") or {}
    if expected.get("communicate") is not None:
        communication.append(str(expected["communicate"]))
    reward_basis = [RewardType.DB]
    if communication:
        reward_basis.append(RewardType.COMMUNICATE)
    actions = [
        Action(
            action_id=f"{row['task_id']}_gold_{index:02d}",
            name=item["name"],
            arguments=item["arguments"],
        )
        for index, item in enumerate(row["golden_actions"])
    ]
    return Task(
        id=row["task_id"],
        description=Description(
            purpose="Evaluate a hand-declared original-style Airline complex workflow."
        ),
        user_scenario=UserScenario(
            persona=(
                "The user follows the declared staged goals, answers policy questions "
                "truthfully, and confirms only the transaction currently summarized."
            ),
            instructions=StructuredUserInstructions(
                domain="airline",
                reason_for_call=row["reason_for_call"],
                known_info=row["known_info"],
                task_instructions=row["task_instructions"],
            ),
        ),
        initial_state=None,
        evaluation_criteria=EvaluationCriteria(
            actions=actions,
            communicate_info=communication or None,
            nl_assertions=None,
            reward_basis=reward_basis,
        ),
    )


def _compile(row: dict[str, Any]) -> CompiledTaskBundle:
    task = _task(row)
    metadata = {
        "workflow_archetype": row["workflow_archetype"],
        "workflow_family_id": row["family_id"],
        "declared_goals": row["declared_goals"],
        "relevant_entities": row["relevant_entities"],
        "governed_decision_points": row["governed_decision_points"],
        "workflow_dependencies": row["workflow_dependencies"],
        "protected_invariants": row["protected_invariants"],
        "expected_reconciliation": row["expected_reconciliation"],
        "complexity_dimensions": row["complexity_dimensions"],
        "source_structure_refs": row["source_structure_refs"],
        "abstracted_structure": row["abstracted_structure"],
        "new_realization": row["new_realization"],
        "staged_goals": row.get("staged_goals", []),
        "compliance_components": row.get("compliance_components", []),
        "formal_split": None,
        "selection_basis": "workflow_structure_only",
        "model_outcomes_used": False,
    }
    return CompiledTaskBundle(
        compiled_task_id=row["task_id"],
        scenario_id=f"scenario_{row['task_id']}",
        manifestation_id=f"workflow_{row['family_id']}",
        latent_pair_id=row["family_id"],
        latent_world_id=row["family_id"],
        template_id="airline.complex_workflow.declared",
        concept_id="airline.original_style_complex_workflow",
        rule_id="airline.workflow.multiple_governed_decisions",
        task=task,
        expected_governance="COMPLY_WITH_ALL_APPLICABLE_SOURCE_POLICY",
        expected_resolution="COMPLETE_ALL_NON_WITHDRAWN_DECLARED_GOALS",
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
            notes=["Pending deterministic CW2 audit."],
        ),
    )


def _booking_summary(payload: dict[str, Any]) -> str:
    flights = ", ".join(
        f"{item['flight_number']} on {item['date']}" for item in payload["flights"]
    )
    passengers = ", ".join(
        f"{item['first_name']} {item['last_name']}" for item in payload["passengers"]
    )
    payments = ", ".join(
        f"${item['amount']} to {item['payment_id']}" for item in payload["payment_methods"]
    )
    insurance = "with insurance" if payload["insurance"] == "yes" else "no insurance"
    return (
        f"Complete booking summary: {payload['origin']} to {payload['destination']} in "
        f"{payload['cabin']}; flights {flights}; passengers {passengers}; "
        f"{payload['total_baggages']} checked bags; {insurance}; payments {payments}. "
        "Please confirm yes to book this exact transaction."
    )


def _confirmation_text(action: Action) -> str:
    if action.name == "book_reservation":
        return _booking_summary(action.arguments)
    return (
        f"Complete transaction summary for {action.name}: "
        f"{json.dumps(action.arguments, sort_keys=True)}. "
        "Please confirm this exact transaction."
    )


def canonical_trajectory(bundle: CompiledTaskBundle) -> tuple[list[Any], Any]:
    """Execute the declared golden workflow without an Agent or User Simulator."""

    environment = get_environment()
    environment.set_state(None, None, [])
    row_metadata = bundle.hidden_metadata
    trajectory: list[Any] = [
        UserMessage(role="user", content=bundle.task.user_scenario.instructions.reason_for_call)
    ]
    if any(action.name == "cancel_reservation" for action in bundle.task.evaluation_criteria.actions or []):
        trajectory.append(
            UserMessage(
                role="user",
                content="My plans changed because of a schedule conflict; that is my cancellation reason.",
            )
        )

    staged_by_trigger = {
        item["trigger"]: item for item in row_metadata.get("staged_goals", [])
    }
    for index, action in enumerate(bundle.task.evaluation_criteria.actions or []):
        if action.name in _WRITE_TOOLS:
            trajectory.extend(
                [
                    AssistantMessage(role="assistant", content=_confirmation_text(action)),
                    UserMessage(
                        role="user",
                        content="Yes, I explicitly confirm that exact complete transaction.",
                    ),
                ]
            )
        call = ToolCall(
            id=f"{bundle.task.id}_offline_gold_{index:02d}",
            name=action.name,
            arguments=action.arguments,
            requestor="assistant",
        )
        trajectory.append(AssistantMessage(role="assistant", tool_calls=[call]))
        response = environment.get_response(call)
        if response.error:
            raise RuntimeError(
                f"Golden action failed for {bundle.task.id}: {action.name}: {response.content}"
            )
        trajectory.append(response)

        trigger = None
        if action.name == "update_reservation_passengers" and action.arguments.get("reservation_id") == "3RK2T9":
            trigger = "after_passenger_update_succeeds"
        elif action.name == "update_reservation_flights" and action.arguments.get("reservation_id") == "M05KNL":
            trigger = "after_flight_change_succeeds"
        elif action.name == "cancel_reservation" and action.arguments.get("reservation_id") == "BSSSM3":
            trigger = "after_cancellation_succeeds"
        if trigger in staged_by_trigger:
            trajectory.append(
                UserMessage(role="user", content=staged_by_trigger[trigger]["user_utterance"])
            )

    communicate = bundle.task.evaluation_criteria.communicate_info or []
    if communicate:
        trajectory.append(
            AssistantMessage(
                role="assistant",
                content="Completed workflow reconciliation: " + "; ".join(communicate),
            )
        )
    return trajectory, environment


def _component_bundle(
    parent: CompiledTaskBundle,
    component: dict[str, Any],
) -> CompiledTaskBundle:
    rule_id = component["rule_id"]
    template_id, concept_id = _COMPONENT_SCHEMA[rule_id]
    target = component["target"]
    context: dict[str, Any]
    if rule_id in {
        "airline.book.baggage_allowance",
        "airline.action.explicit_confirmation",
    }:
        booking = next(
            action.arguments
            for action in parent.task.evaluation_criteria.actions or []
            if action.name == "book_reservation" and action.arguments["user_id"] == target
        )
        context = {
            "user_id": target,
            "requested_baggage_count": booking["total_baggages"],
            "payment_feasible": True,
            "summary_baggage_count_mode": "nonnegative_decimal",
        }
    elif rule_id == "airline.cancel.reason_required":
        context = {"reservation_id": target}
    else:
        initial = get_environment().tools.db.reservations[target]
        context = {
            "reservation_id": target,
            "current_trip_type": initial.flight_type,
        }
    metadata = {
        "predicate_name": "canonical_complex_workflow_component_compliance",
        "predicate_value": True,
        "concrete_context": context,
    }
    return CompiledTaskBundle(
        compiled_task_id=f"{parent.task.id}::{rule_id}::{target}",
        scenario_id=parent.scenario_id,
        manifestation_id=parent.manifestation_id,
        latent_pair_id=parent.latent_pair_id,
        latent_world_id=parent.latent_world_id,
        template_id=template_id,
        concept_id=concept_id,
        rule_id=rule_id,
        task=parent.task,
        expected_governance="COMPLIANT",
        expected_resolution=parent.expected_resolution,
        hidden_metadata=metadata,
        compilation_audit=parent.compilation_audit,
    )


def _as_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=False)
    if isinstance(value, dict):
        return {key: _as_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_as_plain(item) for item in value]
    return value


def _resolve_path(db: Any, path: str) -> Any:
    parts = path.split(".")
    if len(parts) == 3 and parts[0] == "reservations" and parts[2] == "flight_instances":
        reservation = db.reservations[parts[1]]
        return [
            {"flight_number": item.flight_number, "date": item.date}
            for item in reservation.flights
        ]
    if len(parts) == 3 and parts[0] == "reservations" and parts[2] == "baggage":
        reservation = db.reservations[parts[1]]
        return {
            "total_baggages": reservation.total_baggages,
            "nonfree_baggages": reservation.nonfree_baggages,
        }
    value: Any = db
    for part in parts:
        if isinstance(value, dict):
            value = value[part]
        else:
            value = getattr(value, part)
    return _as_plain(value)


def _validate_references(bundle: CompiledTaskBundle, db: Any) -> None:
    user_id = next(
        item.split(":", 1)[1]
        for item in bundle.hidden_metadata["relevant_entities"]
        if item.startswith("user:")
    )
    user = db.users[user_id]
    for reference in bundle.hidden_metadata["relevant_entities"]:
        kind, value = reference.split(":", 1)
        if kind == "user" and value not in db.users:
            raise ValueError(f"Unknown user reference: {value}")
        if kind == "reservation":
            if value not in db.reservations or db.reservations[value].user_id != user_id:
                raise ValueError(f"Invalid reservation binding: {reference}")
        elif kind == "flight":
            number, date = value.split("@", 1)
            if number not in db.flights or date not in db.flights[number].dates:
                raise ValueError(f"Invalid flight instance: {reference}")
        elif kind == "payment" and value not in user.payment_methods:
            raise ValueError(f"Invalid payment binding: {reference}")


def _validate_policy_and_reconciliation(bundle: CompiledTaskBundle, initial_db: Any, final_db: Any) -> None:
    actions = bundle.task.evaluation_criteria.actions or []
    user_ref = next(
        item.split(":", 1)[1]
        for item in bundle.hidden_metadata["relevant_entities"]
        if item.startswith("user:")
    )
    for action in actions:
        args = action.arguments
        if action.name == "book_reservation":
            user = initial_db.users[args["user_id"]]
            allowance = _FREE_BAGS_PER_PASSENGER[user.membership][args["cabin"]] * len(args["passengers"])
            if args["nonfree_baggages"] != max(0, args["total_baggages"] - allowance):
                raise ValueError(f"Incorrect baggage allowance in {bundle.task.id}")
            sources = [user.payment_methods[item["payment_id"]].source for item in args["payment_methods"]]
            if sources.count("certificate") > 1 or sources.count("credit_card") > 1 or sources.count("gift_card") > 3:
                raise ValueError(f"Payment cardinality violates Airline policy in {bundle.task.id}")
        elif action.name == "update_reservation_baggages":
            reservation = initial_db.reservations[args["reservation_id"]]
            if args["total_baggages"] < reservation.total_baggages:
                raise ValueError(f"Baggage removal is not permitted in {bundle.task.id}")
        elif action.name == "update_reservation_passengers":
            reservation = initial_db.reservations[args["reservation_id"]]
            if len(args["passengers"]) != len(reservation.passengers):
                raise ValueError(f"Passenger count changed in {bundle.task.id}")
        elif action.name == "update_reservation_flights":
            reservation = initial_db.reservations[args["reservation_id"]]
            if reservation.cabin == "basic_economy" and args["cabin"] == reservation.cabin:
                raise ValueError(f"Basic-economy flight mutation in {bundle.task.id}")
        elif action.name == "cancel_reservation":
            reservation = initial_db.reservations[args["reservation_id"]]
            fixed_now = datetime.fromisoformat("2024-05-15T15:00:00")
            within_24_hours = (
                fixed_now - datetime.fromisoformat(reservation.created_at)
            ).total_seconds() <= 24 * 60 * 60
            visible_task = " ".join(
                (
                    bundle.task.user_scenario.instructions.reason_for_call,
                    bundle.task.user_scenario.instructions.known_info or "",
                )
            ).lower()
            covered_insured_reason = reservation.insurance == "yes" and any(
                marker in visible_task for marker in ("medical", "health", "weather")
            )
            eligible = (
                reservation.cabin == "business"
                or within_24_hours
                or covered_insured_reason
            )
            if not eligible:
                raise ValueError(f"Golden cancellation is not policy eligible in {bundle.task.id}")

    expected = bundle.hidden_metadata["expected_reconciliation"]
    kind = expected["kind"]
    if kind in {"payment_total", "replacement_payment_total"}:
        booking = next(action.arguments for action in actions if action.name == "book_reservation")
        if sum(item["amount"] for item in booking["payment_methods"]) != expected["value"]:
            raise ValueError(f"Payment reconciliation drifted in {bundle.task.id}")
    elif kind == "refund_total":
        cancelled = [action.arguments["reservation_id"] for action in actions if action.name == "cancel_reservation"]
        if cancelled:
            refund = sum(
                sum(item.amount for item in initial_db.reservations[rid].payment_history)
                for rid in cancelled
            )
        else:
            updated = [
                action.arguments["reservation_id"]
                for action in actions
                if action.name == "update_reservation_flights"
            ]
            refund = sum(
                -sum(
                    item.amount
                    for item in final_db.reservations[rid].payment_history[
                        len(initial_db.reservations[rid].payment_history) :
                    ]
                    if item.amount < 0
                )
                for rid in updated
            )
        if refund != expected["value"]:
            raise ValueError(f"Refund reconciliation drifted in {bundle.task.id}: {refund}")
    elif kind == "fare_difference":
        target = next(action.arguments["reservation_id"] for action in actions if action.name == "update_reservation_flights")
        delta = final_db.reservations[target].payment_history[-1].amount
        if delta != expected["value"]:
            raise ValueError(f"Fare reconciliation drifted in {bundle.task.id}: {delta}")
    elif kind == "free_baggage_total":
        reservation = initial_db.reservations["JMO1MG"]
        user = initial_db.users[user_ref]
        value = _FREE_BAGS_PER_PASSENGER[user.membership][reservation.cabin] * len(reservation.passengers)
        if value != expected["value"]:
            raise ValueError(f"Baggage aggregation drifted in {bundle.task.id}: {value}")
    elif kind == "cancelled_refund":
        value = sum(item.amount for item in initial_db.reservations["BSSSM3"].payment_history)
        if value != expected["value"]:
            raise ValueError(f"Cancellation refund drifted in {bundle.task.id}: {value}")
    elif kind == "return_elapsed_minutes":
        first = initial_db.flights["HAT290"]
        second = initial_db.flights["HAT175"]
        start_hour, start_minute, _ = map(int, first.scheduled_departure_time_est.split(":"))
        end_hour, end_minute, _ = map(int, second.scheduled_arrival_time_est.split(":"))
        value = (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)
        if value != expected["value"]:
            raise ValueError(f"Temporal reconciliation drifted in {bundle.task.id}: {value}")
    elif kind == "verified_denial":
        reservation = initial_db.reservations["M20IZO"]
        age_hours = (
            datetime.fromisoformat("2024-05-15T15:00:00")
            - datetime.fromisoformat(reservation.created_at)
        ).total_seconds() / 3600
        if (
            reservation.insurance != "no"
            or reservation.cabin == "business"
            or age_hours <= 24
        ):
            raise ValueError("Authority-conflict denial lost its state conflict")


def _audit_bundle(bundle: CompiledTaskBundle) -> tuple[CompiledTaskBundle, dict[str, Any]]:
    initial_environment = get_environment()
    initial_environment.set_state(None, None, [])
    initial_db = deepcopy(initial_environment.tools.db)
    _validate_references(bundle, initial_db)
    before = {
        path: _resolve_path(initial_db, path)
        for path in bundle.hidden_metadata["protected_invariants"]
    }

    trajectory, final_environment = canonical_trajectory(bundle)
    final_db = final_environment.tools.db
    env_reward = EnvironmentEvaluator.calculate_reward(get_environment, bundle.task, trajectory).reward
    communicate_reward = CommunicateEvaluator.calculate_reward(bundle.task, trajectory).reward
    if env_reward != 1.0 or communicate_reward != 1.0:
        raise RuntimeError(
            f"Native reward failed for {bundle.task.id}: DB={env_reward}, communicate={communicate_reward}"
        )
    for path, expected in before.items():
        if _resolve_path(final_db, path) != expected:
            raise RuntimeError(f"Protected invariant changed in {bundle.task.id}: {path}")

    _validate_policy_and_reconciliation(bundle, initial_db, final_db)
    component_results = []
    for component in bundle.hidden_metadata["compliance_components"]:
        result = evaluate_target_compliance(_component_bundle(bundle, component), trajectory)
        component_results.append(
            {"rule_id": result.rule_id, "target": component["target"], "compliant": result.compliant}
        )
        if not result.compliant:
            raise RuntimeError(
                f"Canonical compliance failed for {bundle.task.id}: {result.rule_id}"
            )

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
                "Hand-declared CW2 workflow materialized without model calls.",
                "Native reward, component compliance, protected invariants, and reconciliation passed.",
            ],
        ),
    )
    return audited, {
        "task_id": bundle.task.id,
        "family_id": bundle.latent_pair_id,
        "archetype": bundle.hidden_metadata["workflow_archetype"],
        "native_db_reward": env_reward,
        "communicate_reward": communicate_reward,
        "canonical_compliance": all(item["compliant"] for item in component_results),
        "component_compliance": component_results,
        "protected_invariants_checked": len(before),
        "golden_action_count": len(bundle.task.evaluation_criteria.actions or []),
        "complexity_dimension_count": len(bundle.hidden_metadata["complexity_dimensions"]),
        "staged_goal_count": len(bundle.hidden_metadata["staged_goals"]),
    }


def _population_audit(bundles: list[CompiledTaskBundle]) -> dict[str, Any]:
    counts = Counter(item.hidden_metadata["workflow_archetype"] for item in bundles)
    if dict(counts) != ARCHETYPE_COUNTS:
        raise ValueError(f"Archetype allocation changed: {dict(counts)}")
    if any(len(item.hidden_metadata["complexity_dimensions"]) < 3 for item in bundles):
        raise ValueError("Every workflow requires at least three declared complexity dimensions")
    if any(item.hidden_metadata.get("formal_split") is not None for item in bundles):
        raise ValueError("A CW2 task acquired a formal split")

    grouped: dict[str, list[CompiledTaskBundle]] = defaultdict(list)
    for bundle in bundles:
        grouped[bundle.hidden_metadata["workflow_archetype"]].append(bundle)
    for archetype, members in grouped.items():
        fingerprints = {
            json.dumps(
                {
                    "decisions": item.hidden_metadata["governed_decision_points"],
                    "dependencies": item.hidden_metadata["workflow_dependencies"],
                    "reconciliation": item.hidden_metadata["expected_reconciliation"]["kind"],
                    "actions": [action.name for action in item.task.evaluation_criteria.actions or []],
                    "new_realization": item.hidden_metadata["new_realization"],
                },
                sort_keys=True,
            )
            for item in members
        }
        if len(fingerprints) != len(members):
            raise ValueError(f"Archetype {archetype} contains a rename-only duplicate")

    accumulation = grouped["mid_dialogue_goal_accumulation"]
    for bundle in accumulation:
        if not bundle.hidden_metadata["staged_goals"]:
            raise ValueError(f"Missing staged goal in {bundle.task.id}")
        initial = bundle.task.user_scenario.instructions.reason_for_call.lower()
        for staged in bundle.hidden_metadata["staged_goals"]:
            if staged["user_utterance"].lower() in initial:
                raise ValueError(f"Staged goal leaked into initial prompt in {bundle.task.id}")

    return {
        "task_count": len(bundles),
        "family_count": len({item.latent_pair_id for item in bundles}),
        "archetype_counts": dict(sorted(counts.items())),
        "formal_split": None,
        "all_tasks_have_three_or_more_complexity_dimensions": True,
        "independent_realization_audit": True,
        "agent_rollouts_run": 0,
        "user_simulator_model_runs": 0,
        "model_outcomes_used_for_selection": False,
    }


def materialize_declared_pilot(
    declarations_path: Path = DECLARATIONS_PATH,
) -> tuple[list[CompiledTaskBundle], dict[str, Any]]:
    declaration = read_declarations(declarations_path)
    audited: list[CompiledTaskBundle] = []
    task_audits: list[dict[str, Any]] = []
    for row in declaration["tasks"]:
        bundle, audit = _audit_bundle(_compile(row))
        audited.append(bundle)
        task_audits.append(audit)
    population = _population_audit(audited)
    serialized = [item.to_dict() for item in audited]
    compiled_digest = sha256(
        json.dumps(serialized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    declaration_digest = sha256(declarations_path.read_bytes()).hexdigest()
    audit = {
        "contract": declaration["contract"],
        "population": population,
        "declarations_sha256": declaration_digest,
        "compiled_bundle_sha256": compiled_digest,
        "native_golden_reward": f"{sum(item['native_db_reward'] == 1.0 and item['communicate_reward'] == 1.0 for item in task_audits)} / 15",
        "canonical_compliance": f"{sum(item['canonical_compliance'] for item in task_audits)} / 15",
        "deterministic_audit": "PASS",
        "tasks": task_audits,
        "cw2_construction": "PASS",
        "cw3_decision": "PROCEED",
    }
    return audited, audit


def write_freeze_manifest(path: Path = FREEZE_MANIFEST_PATH) -> dict[str, Any]:
    _, audit = materialize_declared_pilot()
    manifest = {
        "contract": audit["contract"],
        "task_count": audit["population"]["task_count"],
        "family_count": audit["population"]["family_count"],
        "archetype_counts": audit["population"]["archetype_counts"],
        "declarations_sha256": audit["declarations_sha256"],
        "compiled_bundle_sha256": audit["compiled_bundle_sha256"],
        "deterministic_audit": audit["deterministic_audit"],
        "native_golden_reward": audit["native_golden_reward"],
        "canonical_compliance": audit["canonical_compliance"],
        "model_rollouts_run": 0,
        "cw2_construction": audit["cw2_construction"],
        "cw3_decision": audit["cw3_decision"],
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps(write_freeze_manifest(), indent=2, sort_keys=True))
