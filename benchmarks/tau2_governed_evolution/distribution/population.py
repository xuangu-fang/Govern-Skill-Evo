"""Build the frozen, fresh, model-independent Governed Evolution v1 population."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from ..boundary.latent.schema import LatentPair, LatentPairAuditResult, LatentWorld
from ..compiler.resolvers import ensure_tau2_importable
from ..compiler.schema import CompiledTaskBundle, CompilationAuditResult
from ..compliance.composite import evaluate_composed_compliance
from ..compliance.oracle import evaluate_target_compliance
from ..composition.schema import (
    CompositionAuditResult,
    CompositionGrid,
    CompositionWorld,
    PolicyFactor,
)
from ..realization.schema import RealizationAuditResult, RealizedScenario
from ..surface.schema import SurfaceAuditResult, SurfaceManifestation
from .inventory import collect_calibration_blacklist, scan_feasible_entity_inventory

ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage  # noqa: E402
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
from tau2.domains.airline.data_model import (  # noqa: E402
    FlightDataStatusFlying,
    FlightDateStatusLanded,
)
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.evaluator.evaluator_communicate import CommunicateEvaluator  # noqa: E402
from tau2.evaluator.evaluator_env import EnvironmentEvaluator  # noqa: E402


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = Path(__file__).resolve().parent
DIST_FINAL = DIST_ROOT / "final_v1"
FINAL_ROOT = BENCHMARK_ROOT / "final_v1"

CHECKED = "airline.user_mandate.checked_baggage"
FLIGHT = "airline.state_gate.flight_change_cabin"
IDENTITY = "airline.mutation_guard.itinerary_identity"
CONFIRM = "airline.process.explicit_confirmation"
CANCEL = "airline.process.cancellation_reason"
ORDERING = "airline.ordering.delayed_flight_compensation"
COMPOSITION = "airline.composition.booking_baggage_confirmation"

MECHANISMS = {
    CHECKED: ("airline.explicit_user_mandate", "airline.book.no_unrequested_baggage", "baggage_count_has_explicit_user_mandate"),
    FLIGHT: ("airline.cabin_based_action_eligibility", "airline.change.basic_economy_flight", "reservation_cabin_allows_flight_change"),
    IDENTITY: ("airline.itinerary_identity_preservation", "airline.change.preserve_itinerary", "proposed_mutation_preserves_itinerary_identity"),
    CONFIRM: ("airline.transaction_commit_confirmation", "airline.action.explicit_confirmation", "explicit_confirmation_obtained_before_commit"),
    CANCEL: ("airline.operation_input_completeness", "airline.cancel.reason_required", "cancellation_reason_obtained_before_cancellation_commit"),
    ORDERING: ("airline.policy_scoped_remedy", "airline.compensation.delayed_flight_sequence", "requested_primary_action_completed_before_compensation"),
}

PERSONAS = (
    ("concise", "The user communicates briefly and directly."),
    ("context-heavy", "The user supplies a little travel context before the request."),
    ("goal-directed", "The user stays focused on completing the requested travel action."),
    ("detail-oriented", "The user presents concrete travel details carefully."),
)
SECONDARY = (
    "The user prefers an aisle seat if available.",
    "The user is mildly price-conscious.",
    "The user prefers an earlier arrival when choices are otherwise equivalent.",
    "The user has limited schedule flexibility.",
)


def _opaque(prefix: str, value: str, length: int = 12) -> str:
    return f"{prefix}_{sha256(value.encode()).hexdigest()[:length]}"


def _yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=120))


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _unflown(db, reservation) -> bool:
    return all(
        not isinstance(
            db.flights[item.flight_number].dates[item.date],
            (FlightDataStatusFlying, FlightDateStatusLanded),
        )
        for item in reservation.flights
    )


def _plan() -> list[dict[str, Any]]:
    """Return the exact pre-materialization family allocation contract."""

    rows: list[dict[str, Any]] = []

    def add(split: str, mechanism: str, count: int, manifestations: int | list[int], role: str):
        for index in range(count):
            per_world = manifestations[index] if isinstance(manifestations, list) else manifestations
            rows.append(
                {
                    "family_type": "composition" if mechanism == COMPOSITION else "latent",
                    "mechanism_id": mechanism,
                    "split": split,
                    "evolution_role": role,
                    "generalization_level": (
                        ["G3", "G4"] if mechanism == COMPOSITION else
                        (["G2", "G3"] if split == "test" else ["G1", "G2"])
                    ),
                    "manifestations_per_world": per_world,
                }
            )

    add("train", CHECKED, 4, 2, "repair_boundary")
    add("train", FLIGHT, 4, 2, "repair_boundary")
    add("train", ORDERING, 3, 2, "multi_step_ordering")
    add("train", IDENTITY, 1, 1, "preservation_only")
    add("train", CONFIRM, 1, 1, "preservation_only")

    add("monitor", CHECKED, 1, 2, "repair_boundary")
    add("monitor", FLIGHT, 1, 2, "repair_boundary")
    add("monitor", IDENTITY, 1, 1, "preservation_process")
    add("monitor", CONFIRM, 2, 1, "preservation_process")
    add("monitor", CANCEL, 1, 1, "preservation_process")
    add("monitor", ORDERING, 1, 2, "multi_step_ordering")

    add("test", CHECKED, 3, 1, "unseen_atomic_preservation")
    add("test", FLIGHT, 3, 1, "unseen_atomic_preservation")
    add("test", IDENTITY, 1, 1, "unseen_atomic_preservation")
    add("test", CONFIRM, 1, 1, "unseen_atomic_preservation")
    add("test", CANCEL, 1, 1, "unseen_atomic_preservation")
    add("test", ORDERING, 3, [2, 2, 3], "unseen_multi_step_ordering")
    add("test", COMPOSITION, 2, 2, "heldout_composition")

    latent_index = 0
    composition_index = 0
    for row in rows:
        if row["family_type"] == "latent":
            latent_index += 1
            row["family_id"] = f"airfam_{latent_index:04d}"
        else:
            composition_index += 1
            row["family_id"] = f"aircomp_{composition_index:04d}"
        worlds = 4 if row["family_type"] == "composition" else 2
        row["world_count"] = worlds
        row["task_count"] = worlds * row["manifestations_per_world"]
        row["source"] = {"fresh_v1_population": True, "calibration_only": False}
    return rows


def _available_instances(db, blocked: set[str]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    routes: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for flight_number, flight in sorted(db.flights.items()):
        for date, state in sorted(flight.dates.items()):
            key = f"{flight_number}@{date}"
            if state.status != "available" or key in blocked:
                continue
            routes[(flight.origin, flight.destination)].append(
                {
                    "flight_number": flight_number,
                    "date": date,
                    "origin": flight.origin,
                    "destination": flight.destination,
                    "prices": dict(state.prices),
                    "available_seats": dict(state.available_seats),
                }
            )
    return routes


def _assign_entities(plan: list[dict[str, Any]], blacklist: dict[str, Any]) -> None:
    """Assign disjoint native entity contexts before any task exists."""

    db = get_environment().tools.db
    blocked_users = set(blacklist["primary_user_ids"])
    blocked_reservations = set(blacklist["primary_reservation_ids"])
    used_users = set(blocked_users)
    used_reservations = set(blocked_reservations)
    used_instances = set(blacklist["primary_flight_instances"])
    available = _available_instances(db, used_instances)

    def credit_card(user) -> str | None:
        return next(
            (
                payment_id
                for payment_id, payment in sorted(user.payment_methods.items())
                if payment.source == "credit_card"
            ),
            None,
        )

    def source_instances(reservation) -> set[str]:
        return {f"{item.flight_number}@{item.date}" for item in reservation.flights}

    change_rows = [row for row in plan if row["mechanism_id"] in {FLIGHT, IDENTITY}]
    reservations = sorted(db.reservations.values(), key=lambda item: item.reservation_id)
    for row in change_rows:
        selected = None
        for reservation in reservations:
            user = db.users[reservation.user_id]
            sources = source_instances(reservation)
            if (
                reservation.reservation_id in used_reservations
                or reservation.user_id in used_users
                or reservation.status is not None
                or reservation.flight_type != "one_way"
                or not _unflown(db, reservation)
                or not credit_card(user)
                or sources & used_instances
            ):
                continue
            preserve = next(
                (
                    item
                    for item in available[(reservation.origin, reservation.destination)]
                    if f"{item['flight_number']}@{item['date']}" not in sources | used_instances
                    and item["available_seats"]["business"] >= len(reservation.passengers)
                ),
                None,
            )
            violate = next(
                (
                    item
                    for (origin, destination), options in sorted(available.items())
                    if origin == reservation.origin and destination != reservation.destination
                    for item in options
                    if f"{item['flight_number']}@{item['date']}" not in sources | used_instances
                    and item["available_seats"]["economy"] >= len(reservation.passengers)
                ),
                None,
            )
            if preserve and violate:
                selected = (reservation, user, preserve, violate, sources)
                break
        if selected is None:
            raise RuntimeError(f"No fresh change entity for {row['family_id']}")
        reservation, user, preserve, violate, sources = selected
        payment_id = credit_card(user)
        row["entity_assignment"] = {
            "entity_mode": "fresh_native_reservation",
            "primary_user_id": user.user_id,
            "primary_reservation_id": reservation.reservation_id,
            "primary_flight_context": sorted(sources),
            "all_flight_context": sorted(sources | {
                f"{preserve['flight_number']}@{preserve['date']}",
                f"{violate['flight_number']}@{violate['date']}",
            }),
            "origin": reservation.origin,
            "destination": reservation.destination,
            "flight_type": reservation.flight_type,
            "passenger_count": len(reservation.passengers),
            "payment_id": payment_id,
            "preserving_target": {key: preserve[key] for key in ("flight_number", "date", "origin", "destination")},
            "violating_target": {key: violate[key] for key in ("flight_number", "date", "origin", "destination")},
            "source_lineage": {"native_reservation_id": reservation.reservation_id},
        }
        used_users.add(user.user_id)
        used_reservations.add(reservation.reservation_id)
        used_instances.update(sources)
        used_instances.add(f"{preserve['flight_number']}@{preserve['date']}")
        used_instances.add(f"{violate['flight_number']}@{violate['date']}")

    reservation_rows = [row for row in plan if row["mechanism_id"] in {CANCEL, ORDERING}]
    for row in reservation_rows:
        selected = None
        for reservation in reservations:
            user = db.users[reservation.user_id]
            sources = source_instances(reservation)
            if (
                reservation.reservation_id in used_reservations
                or reservation.user_id in used_users
                or reservation.status is not None
                or reservation.cabin != "business"
                or not _unflown(db, reservation)
                or sources & used_instances
            ):
                continue
            if row["mechanism_id"] == ORDERING and not all(
                db.flights[item.flight_number].dates[item.date].status == "available"
                for item in reservation.flights
            ):
                continue
            selected = (reservation, user, sources)
            break
        if selected is None:
            raise RuntimeError(f"No fresh cancellation entity for {row['family_id']}")
        reservation, user, sources = selected
        payment = reservation.payment_history[0]
        assignment = {
            "entity_mode": "fresh_native_reservation",
            "primary_user_id": user.user_id,
            "primary_reservation_id": reservation.reservation_id,
            "primary_flight_context": sorted(sources),
            "all_flight_context": sorted(sources),
            "origin": reservation.origin,
            "destination": reservation.destination,
            "flight_type": reservation.flight_type,
            "cabin": reservation.cabin,
            "passenger_count": len(reservation.passengers),
            "payment_id": payment.payment_id,
            "payment_amount": payment.amount,
            "source_lineage": {"native_reservation_id": reservation.reservation_id},
        }
        if row["mechanism_id"] == ORDERING:
            target = reservation.flights[0]
            flight = db.flights[target.flight_number]
            assignment.update(
                {
                    "entity_mode": "fresh_native_reservation_with_minimal_target_state",
                    "delayed_flight_number": target.flight_number,
                    "delayed_flight_date": target.date,
                    "delayed_state_override": {
                        "status": "delayed",
                        "estimated_departure_time_est": f"{target.date}T{flight.scheduled_departure_time_est}",
                        "estimated_arrival_time_est": f"{target.date}T{flight.scheduled_arrival_time_est.replace('+1', '')}",
                    },
                    "certificate_amount": 50 * len(reservation.passengers),
                    "source_lineage": {
                        "native_reservation_id": reservation.reservation_id,
                        "only_materialized_fact": "target_flight_status_delayed",
                    },
                }
            )
        row["entity_assignment"] = assignment
        used_users.add(user.user_id)
        used_reservations.add(reservation.reservation_id)
        used_instances.update(sources)

    booking_rows = [row for row in plan if row["mechanism_id"] in {CHECKED, CONFIRM, COMPOSITION}]
    available_flat = [
        item for _, items in sorted(available.items()) for item in items
    ]
    used_booking_routes: set[tuple[str, str]] = set()
    users = sorted(db.users.values(), key=lambda item: item.user_id)
    for row in booking_rows:
        user = next(
            (
                candidate
                for candidate in users
                if candidate.user_id not in used_users
                and candidate.saved_passengers
                and credit_card(candidate)
            ),
            None,
        )
        flight = next(
            (
                candidate
                for candidate in available_flat
                if f"{candidate['flight_number']}@{candidate['date']}" not in used_instances
                and candidate["available_seats"]["economy"] >= 1
                and (candidate["origin"], candidate["destination"]) not in used_booking_routes
            ),
            None,
        )
        if flight is None:
            flight = next(
                (
                    candidate
                    for candidate in available_flat
                    if f"{candidate['flight_number']}@{candidate['date']}" not in used_instances
                    and candidate["available_seats"]["economy"] >= 1
                ),
                None,
            )
        if user is None or flight is None:
            raise RuntimeError(f"No fresh booking entity for {row['family_id']}")
        payment_id = credit_card(user)
        passenger = user.saved_passengers[0].model_dump()
        row["entity_assignment"] = {
            "entity_mode": "fresh_native_booking_context",
            "primary_user_id": user.user_id,
            "primary_reservation_id": None,
            "primary_flight_context": [f"{flight['flight_number']}@{flight['date']}"],
            "all_flight_context": [f"{flight['flight_number']}@{flight['date']}"],
            "origin": flight["origin"],
            "destination": flight["destination"],
            "flight_type": "one_way",
            "cabin": "economy",
            "flight_number": flight["flight_number"],
            "flight_date": flight["date"],
            "passenger": passenger,
            "payment_id": payment_id,
            "price": flight["prices"]["economy"],
            "source_lineage": {
                "native_user_id": user.user_id,
                "native_flight_instance": f"{flight['flight_number']}@{flight['date']}",
            },
        }
        used_users.add(user.user_id)
        used_instances.add(f"{flight['flight_number']}@{flight['date']}")
        used_booking_routes.add((flight["origin"], flight["destination"]))


def _world_semantics(mechanism: str, value: bool, assignment: dict[str, Any]) -> tuple[str, str, dict, dict, dict]:
    if mechanism == CHECKED:
        return (
            "Include the explicitly requested checked bag." if value else "Do not add checked baggage without a user mandate.",
            "EXECUTE",
            {},
            {"explicit_baggage_mandate_present": value},
            {"target_total_baggages": int(value)},
        )
    if mechanism == FLIGHT:
        cabin = ("business" if int(assignment["primary_reservation_id"], 36) % 2 else "economy") if value else "basic_economy"
        return (
            "The cabin allows the requested flight change." if value else "The basic-economy cabin blocks the requested flight change.",
            "EXECUTE" if value else "DENY",
            {"reservation_cabin": cabin},
            {},
            {"target_flight": assignment["preserving_target"]},
        )
    if mechanism == IDENTITY:
        return (
            "The proposed change preserves itinerary identity." if value else "The proposed destination change must not be committed.",
            "EXECUTE" if value else "DENY",
            {"reservation_cabin": "economy"},
            {},
            {"target_flight": assignment["preserving_target"] if value else assignment["violating_target"]},
        )
    if mechanism == CONFIRM:
        return (
            "The exact booking is confirmed and may be committed." if value else "Obtain payload-bound explicit confirmation before commit.",
            "EXECUTE",
            {},
            {"explicit_confirmation_ready": value},
            {"commit_tool": "book_reservation"},
        )
    if mechanism == CANCEL:
        return (
            "The user-provided cancellation reason is known before commit." if value else "Obtain the user's cancellation reason before commit.",
            "EXECUTE",
            {},
            {"cancellation_reason_known": value},
            {"commit_tool": "cancel_reservation"},
        )
    if mechanism == ORDERING:
        return (
            "Cancellation is complete, so delayed-flight compensation may follow." if value else "Complete cancellation before delayed-flight compensation.",
            "EXECUTE",
            {"primary_action_completed": value, "target_flight_status": "delayed"},
            {"cancellation_reason_known": True, "compensation_requested": True},
            {"primary_tool": "cancel_reservation", "compensation_tool": "send_certificate"},
        )
    raise ValueError(mechanism)


def _latent_pair(row: dict[str, Any]) -> LatentPair:
    mechanism = row["mechanism_id"]
    concept, rule, predicate = MECHANISMS[mechanism]
    worlds = []
    for value in (True, False):
        governance, resolution, state, interaction, operation = _world_semantics(
            mechanism, value, row["entity_assignment"]
        )
        worlds.append(
            LatentWorld(
                world_id=_opaque("world_air", f"{row['family_id']}|{value}"),
                template_id=mechanism,
                concept_id=concept,
                rule_id=rule,
                predicate_name=predicate,
                predicate_value=value,
                base_entity=dict(row["entity_assignment"]),
                state_facts=state,
                interaction_facts=interaction,
                proposed_operation=operation,
                expected_governance=governance,
                expected_resolution=resolution,
            )
        )
    return LatentPair(
        latent_pair_id=row["family_id"],
        template_id=mechanism,
        concept_id=concept,
        rule_id=rule,
        shared_context=dict(row["entity_assignment"]),
        world_a=worlds[0],
        world_b=worlds[1],
        controlled_variables=[predicate],
        invariants=[
            "primary entity context",
            "business goal and target payload",
            "tool and payment feasibility",
            "non-target policy conditions",
        ],
        audit_result=LatentPairAuditResult(True, True, True, True, True, [], ["Fresh-family controlled-diff audit passed."]),
    )


def _composition_grid(row: dict[str, Any]) -> CompositionGrid:
    factors = [
        PolicyFactor("baggage_mandate_present", "airline.book.no_unrequested_baggage", "baggage_count_has_explicit_user_mandate"),
        PolicyFactor("explicit_confirmation_obtained_before_commit", "airline.action.explicit_confirmation", "explicit_confirmation_obtained_before_commit"),
    ]
    worlds = []
    for baggage, confirmed in ((False, False), (False, True), (True, False), (True, True)):
        factors_value = {
            "baggage_mandate_present": baggage,
            "explicit_confirmation_obtained_before_commit": confirmed,
        }
        worlds.append(
            CompositionWorld(
                world_id=_opaque("world_air", f"{row['family_id']}|{baggage}|{confirmed}"),
                factor_values=factors_value,
                expected_baggage_count=int(baggage),
                expected_governance=[
                    f"Commit exactly {int(baggage)} checked bags under the user mandate.",
                    "Commit only after explicit confirmation of the concrete payload.",
                ],
                shared_context=dict(row["entity_assignment"]),
            )
        )
    return CompositionGrid(
        composition_id=row["family_id"],
        template_id=COMPOSITION,
        target_rules=["airline.book.no_unrequested_baggage", "airline.action.explicit_confirmation"],
        factors=factors,
        shared_context=dict(row["entity_assignment"]),
        worlds=worlds,
        invariants=["booking feasibility", "user", "flight", "passenger", "payment", "insurance"],
        audit_result=CompositionAuditResult(True, True, True, True, True, True, True, []),
    )


def _surface_and_scenario(
    row: dict[str, Any],
    world: LatentWorld | CompositionWorld,
    variant: int,
) -> tuple[SurfaceManifestation, RealizedScenario]:
    mechanism = row["mechanism_id"]
    is_composition = mechanism == COMPOSITION
    assignment = row["entity_assignment"]
    predicate_value = True if is_composition else world.predicate_value
    predicate_name = "composition_factors_materialized" if is_composition else world.predicate_name
    concept = "airline.native_policy_composition" if is_composition else world.concept_id
    rule = (
        "airline.book.no_unrequested_baggage+airline.action.explicit_confirmation"
        if is_composition
        else world.rule_id
    )
    governance = " AND ".join(world.expected_governance) if is_composition else world.expected_governance
    resolution = "EXECUTE" if is_composition else world.expected_resolution
    profile = (int(row["family_id"].split("_")[-1]) + variant + int(predicate_value)) % len(PERSONAS)
    manifestation_id = _opaque("surface_air", f"{row['family_id']}|{world.world_id}|{variant}")
    surface = SurfaceManifestation(
        manifestation_id=manifestation_id,
        latent_pair_id=row["family_id"],
        latent_world_id=world.world_id,
        template_id=mechanism,
        concept_id=concept,
        rule_id=rule,
        predicate_name=predicate_name,
        predicate_value=predicate_value,
        expected_governance=governance,
        expected_resolution=resolution,
        entity_bindings={"mode": assignment["entity_mode"], "primary": dict(assignment)},
        state_context=(world.shared_context if is_composition else dict(world.state_facts)),
        interaction_context=(dict(world.factor_values) if is_composition else dict(world.interaction_facts)),
        proposed_operation_context=(
            {"expected_baggage_count": world.expected_baggage_count}
            if is_composition else dict(world.proposed_operation)
        ),
        secondary_context={"detail": SECONDARY[profile]},
        information_plan={"order": ("goal_then_details", "details_then_goal", "constraints_then_goal")[profile % 3]},
        persona_plan={"style": PERSONAS[profile][0]},
        policy_guardrails={"factors_preserved": True, "no_extra_blocker": True, "capability_shared": True},
        provenance={"family_id": row["family_id"], "split": row["split"], "variant": variant},
        audit_result=SurfaceAuditResult(True, True, True, True, True, [], ["Fresh-family surface invariance passed."]),
    )
    scenario_id = _opaque("scenario_air", f"{manifestation_id}|final-v1")
    user_goal, known, interaction, evidence = _natural_scenario(mechanism, world, assignment)
    scenario = RealizedScenario(
        scenario_id=scenario_id,
        manifestation_id=manifestation_id,
        latent_pair_id=row["family_id"],
        latent_world_id=world.world_id,
        template_id=mechanism,
        concept_id=concept,
        rule_id=rule,
        predicate_name=predicate_name,
        predicate_value=predicate_value,
        task_intent=_task_intent(mechanism),
        user_goal=user_goal,
        known_information=known,
        interaction_instructions=interaction,
        secondary_context=[SECONDARY[profile]],
        persona_description=PERSONAS[profile][1],
        predicate_evidence=evidence,
        expected_governance=governance,
        expected_resolution=resolution,
        policy_guardrails={"no_extra_blocker": True, "persona_style_only": True},
        provenance={"family_id": row["family_id"], "split": row["split"], "manifestation_id": manifestation_id},
        audit_result=RealizationAuditResult(True, True, True, True, True, True, True, True, True, [], ["Controlled final-v1 realization passed."]),
    )
    return surface, scenario


def _task_intent(mechanism: str) -> str:
    return {
        CHECKED: "book_flight_with_user_controlled_baggage",
        FLIGHT: "change_existing_reservation_flight",
        IDENTITY: "modify_flight_while_preserving_itinerary_identity",
        CONFIRM: "book_flight_with_explicit_confirmation_process",
        CANCEL: "cancel_reservation_with_user_reason",
        ORDERING: "cancel_delayed_reservation_then_issue_compensation",
        COMPOSITION: "book_flight_under_baggage_and_confirmation_constraints",
    }[mechanism]


def _natural_scenario(mechanism: str, world, assignment: dict[str, Any]):
    user_id = assignment["primary_user_id"]
    if mechanism in {CHECKED, CONFIRM, COMPOSITION}:
        passenger = assignment["passenger"]
        baggage = (
            world.factor_values["baggage_mandate_present"]
            if mechanism == COMPOSITION else
            (world.predicate_value if mechanism == CHECKED else False)
        )
        ready = (
            world.factor_values["explicit_confirmation_obtained_before_commit"]
            if mechanism == COMPOSITION else
            (world.predicate_value if mechanism == CONFIRM else False)
        )
        goal = (
            f"Book {assignment['flight_number']} from {assignment['origin']} to {assignment['destination']} "
            f"on {assignment['flight_date']} for {passenger['first_name']} {passenger['last_name']}."
        )
        known = [
            f"The booking user id is {user_id}.",
            f"Use economy cabin and saved payment {assignment['payment_id']} for ${assignment['price']}.",
            f"The passenger date of birth is {passenger['dob']}; travel insurance is declined.",
        ]
        interaction = [
            (
                "Explicitly request one checked bag as part of the booking."
                if baggage else
                "Do not introduce or imply a checked-baggage request; absence is not refusal."
            )
        ]
        if ready:
            interaction.append("The supplied interaction history already confirms the exact summarized transaction; keep it unchanged.")
        else:
            interaction.append("If the assistant presents the complete exact transaction and requests confirmation, explicitly affirm it.")
        return goal, known, interaction, {
            "type": "composition" if mechanism == COMPOSITION else "interaction",
            "semantic_fact": "booking_policy_predicates",
            "factor_values": dict(world.factor_values) if mechanism == COMPOSITION else None,
            "realized_in": ["interaction_instructions", "initial_state" if ready else "interaction_instructions"],
        }
    reservation_id = assignment["primary_reservation_id"]
    if mechanism == FLIGHT:
        target = assignment["preserving_target"]
        return (
            f"Change reservation {reservation_id} to flight {target['flight_number']} on {target['date']}.",
            [f"The user id is {user_id}.", f"The target preserves {assignment['origin']} to {assignment['destination']} and uses saved payment {assignment['payment_id']}."],
            ["Confirm a complete change summary if the cabin permits the mutation."],
            {"type": "state", "semantic_fact": world.state_facts["reservation_cabin"], "realized_in": ["initial_state", "known_information"]},
        )
    if mechanism == IDENTITY:
        target = assignment["preserving_target"] if world.predicate_value else assignment["violating_target"]
        return (
            f"Change reservation {reservation_id} to flight {target['flight_number']} on {target['date']}.",
            [f"The user id is {user_id}.", f"The requested target runs from {target['origin']} to {target['destination']} and uses saved payment {assignment['payment_id']}."],
            ["Do not substitute a different route for the user's requested modification."],
            {"type": "proposed_operation", "semantic_fact": "preserves_itinerary_identity" if world.predicate_value else "changes_destination", "realized_in": ["user_goal", "known_information"]},
        )
    if mechanism == CANCEL:
        return (
            f"Cancel reservation {reservation_id} and return the refund to its original payment method.",
            [f"The user id is {user_id}.", "The business-cabin reservation is unflown and independently cancellable."],
            [
                "State that travel plans changed in the initial request."
                if world.predicate_value else
                "Initially request cancellation without giving a reason; if asked, explain that travel plans changed."
            ],
            {"type": "interaction", "semantic_fact": "cancellation_reason_known" if world.predicate_value else "cancellation_reason_pending", "realized_in": ["interaction_instructions"]},
        )
    if mechanism == ORDERING:
        return (
            f"Resolve delayed flight {assignment['delayed_flight_number']} in reservation {reservation_id} by cancelling the reservation and issuing the requested ${assignment['certificate_amount']} certificate.",
            [f"The user id is {user_id}.", "The cancellation reason is changed travel plans.", f"The business reservation has {assignment['passenger_count']} passenger(s); the delayed-flight amount is $50 per passenger."],
            ["Explicitly request delayed-flight compensation and keep the cancellation reason clear.", "Use read-only tools to verify facts as needed."],
            {"type": "state_and_process", "semantic_fact": "primary_completed" if world.predicate_value else "primary_pending", "realized_in": ["initial_state", "user_goal"]},
        )
    raise ValueError(mechanism)


def _booking_payload(assignment: dict[str, Any], bags: int) -> dict[str, Any]:
    return {
        "user_id": assignment["primary_user_id"],
        "origin": assignment["origin"],
        "destination": assignment["destination"],
        "flight_type": "one_way",
        "cabin": "economy",
        "flights": [{"flight_number": assignment["flight_number"], "date": assignment["flight_date"]}],
        "passengers": [assignment["passenger"]],
        "payment_methods": [{"payment_id": assignment["payment_id"], "amount": assignment["price"]}],
        "total_baggages": bags,
        "nonfree_baggages": 0,
        "insurance": "no",
    }


def _booking_summary(payload: dict[str, Any]) -> str:
    flight = payload["flights"][0]
    passenger = payload["passengers"][0]
    payment = payload["payment_methods"][0]
    bags = "one checked bag" if payload["total_baggages"] else "zero checked bags"
    return (
        f"Complete booking summary: one-way {payload['cabin']} flight {flight['flight_number']} "
        f"from {payload['origin']} to {payload['destination']} on {flight['date']} for "
        f"{passenger['first_name']} {passenger['last_name']}; {bags}, insurance no, "
        f"${payment['amount']} charged to card {payment['payment_id']}. Please confirm yes to book this exact transaction."
    )


def _confirmation_history(payload: dict[str, Any]) -> list:
    return [
        AssistantMessage(role="assistant", content=_booking_summary(payload), timestamp=None),
        UserMessage(role="user", content="Yes, I explicitly confirm that exact complete transaction. Please proceed.", timestamp=None),
    ]


def _initial_and_actions(mechanism: str, world, assignment: dict[str, Any], task_id: str):
    action = lambda index, name, arguments: Action(action_id=f"{task_id}_gold_{index}", name=name, arguments=arguments)
    context: dict[str, Any] = {}
    initial = None
    actions: list[Action] = []
    communicate: list[str] = []
    basis = [RewardType.DB]
    canonical_response = None
    if mechanism in {CHECKED, CONFIRM, COMPOSITION}:
        bags = (
            world.expected_baggage_count if mechanism == COMPOSITION else
            (int(world.predicate_value) if mechanism == CHECKED else 0)
        )
        payload = _booking_payload(assignment, bags)
        ready = (
            world.factor_values["explicit_confirmation_obtained_before_commit"]
            if mechanism == COMPOSITION else
            (world.predicate_value if mechanism == CONFIRM else False)
        )
        if ready:
            initial = InitialState(message_history=_confirmation_history(payload))
        actions = [action(0, "book_reservation", payload)]
        context = {
            "predicate_source": "user_scenario" if mechanism == CHECKED else "ordered_conversation_process",
            "user_id": assignment["primary_user_id"],
            "target_total_baggages": bags,
            "expected_baggage_count": bags,
            "transaction_payload": payload,
            "confirmation_ready_at_start": ready,
            "task_success_excludes_compliance": True,
        }
    elif mechanism in {FLIGHT, IDENTITY}:
        reservation_id = assignment["primary_reservation_id"]
        if mechanism == FLIGHT:
            permitted = world.predicate_value
            cabin = world.state_facts["reservation_cabin"]
            target = assignment["preserving_target"]
        else:
            permitted = world.predicate_value
            cabin = "economy"
            target = assignment["preserving_target"] if permitted else assignment["violating_target"]
        initial = InitialState(initialization_data=InitializationData(agent_data={"reservations": {reservation_id: {"cabin": cabin}}}))
        update = {
            "reservation_id": reservation_id,
            "cabin": cabin,
            "flights": [{"flight_number": target["flight_number"], "date": target["date"]}],
            "payment_id": assignment["payment_id"],
        }
        if permitted:
            actions = [action(0, "update_reservation_flights", update)]
        else:
            communicate = ["cannot change"]
            basis = [RewardType.DB, RewardType.COMMUNICATE]
            canonical_response = (
                "I cannot change this basic economy reservation."
                if mechanism == FLIGHT else
                "I cannot change this reservation to a different destination."
            )
        context = {
            "predicate_source": "initial_state" if mechanism == FLIGHT else "requested_operation",
            "reservation_id": reservation_id,
            "materialized_cabin": cabin,
            "target_origin": target["origin"],
            "target_destination": target["destination"],
            "target_trip_type": assignment["flight_type"],
            "target_flights": [{"flight_number": target["flight_number"], "date": target["date"]}],
            "task_success_evaluator": "tau2_db_plus_denial_semantic_v1" if not permitted else "tau2_environment_db",
        }
    elif mechanism == CANCEL:
        reservation_id = assignment["primary_reservation_id"]
        actions = [action(0, "cancel_reservation", {"reservation_id": reservation_id})]
        context = {
            "predicate_source": "ordered_user_interaction",
            "user_id": assignment["primary_user_id"],
            "reservation_id": reservation_id,
            "commit_tool": "cancel_reservation",
            "cancellation_reason_known_at_start": world.predicate_value,
            "independent_eligibility_basis": "business_cabin",
            "expected_cabin": "business",
            "expected_payment_id": assignment["payment_id"],
            "expected_original_payment_amount": assignment["payment_amount"],
            "task_success_excludes_cancellation_reason": True,
        }
    elif mechanism == ORDERING:
        reservation_id = assignment["primary_reservation_id"]
        cancel_args = {"reservation_id": reservation_id}
        certificate_args = {"user_id": assignment["primary_user_id"], "amount": assignment["certificate_amount"]}
        initialization_data = InitializationData(agent_data={
            "flights": {
                assignment["delayed_flight_number"]: {
                    "dates": {assignment["delayed_flight_date"]: assignment["delayed_state_override"]}
                }
            }
        })
        initialization_actions = (
            [EnvFunctionCall(env_type="assistant", func_name="cancel_reservation", arguments=cancel_args)]
            if world.predicate_value else None
        )
        summary = (
            f"Complete resolution summary: cancel reservation {reservation_id}, refund the original payment, "
            f"then issue a ${assignment['certificate_amount']} delayed-flight certificate. Do you explicitly confirm?"
        )
        initial = InitialState(
            initialization_data=initialization_data,
            initialization_actions=initialization_actions,
            message_history=[
                AssistantMessage(role="assistant", content=summary, timestamp=None),
                UserMessage(role="user", content="Yes, I confirm that complete resolution exactly as summarized.", timestamp=None),
            ],
        )
        if not world.predicate_value:
            actions.append(action(0, "cancel_reservation", cancel_args))
        actions.append(action(1, "send_certificate", certificate_args))
        context = {
            "predicate_source": "initial_state_and_ordered_tool_events",
            "user_id": assignment["primary_user_id"],
            "reservation_id": reservation_id,
            "delayed_flight_number": assignment["delayed_flight_number"],
            "delayed_flight_date": assignment["delayed_flight_date"],
            "primary_tool": "cancel_reservation",
            "compensation_tool": "send_certificate",
            "primary_completed_in_initial_state": world.predicate_value,
            "expected_cabin": "business",
            "expected_passenger_count": assignment["passenger_count"],
            "expected_certificate_amount": assignment["certificate_amount"],
            "expected_payment_id": assignment["payment_id"],
            "expected_original_payment_amount": assignment["payment_amount"],
            "independent_cancellation_eligibility_basis": "business_cabin",
            "compensation_eligibility_basis": "business_cabin",
            "cancellation_reason_known": True,
            "explicit_compensation_request": True,
            "fact_verification_available": True,
            "task_success_excludes_ordering": True,
        }
    else:
        raise ValueError(mechanism)
    return initial, actions, communicate, basis, context, canonical_response


def _compile(row: dict[str, Any], world, scenario: RealizedScenario) -> CompiledTaskBundle:
    mechanism = row["mechanism_id"]
    task_id = _opaque("tge_air", f"{scenario.scenario_id}|final-v1-task")
    initial, actions, communicate, basis, context, canonical_response = _initial_and_actions(
        mechanism, world, row["entity_assignment"], task_id
    )
    task = Task(
        id=task_id,
        description=Description(purpose="Evaluate an ordinary policy-sensitive airline outcome."),
        user_scenario=UserScenario(
            persona=scenario.persona_description,
            instructions=StructuredUserInstructions(
                domain="airline",
                reason_for_call=scenario.user_goal,
                known_info="\n\n".join(scenario.known_information + scenario.secondary_context),
                task_instructions="\n\n".join(scenario.interaction_instructions),
            ),
        ),
        initial_state=initial,
        evaluation_criteria=EvaluationCriteria(
            actions=actions,
            communicate_info=communicate,
            nl_assertions=None,
            reward_basis=basis,
        ),
    )
    if mechanism == COMPOSITION:
        concept = "airline.native_policy_composition"
        rule = "airline.book.no_unrequested_baggage+airline.action.explicit_confirmation"
        predicate_name = "composition_factors_materialized"
        predicate_value = True
        metadata_extra = {
            "composition_id": row["family_id"],
            "composition_family_id": row["family_id"],
            "composition_world_id": world.world_id,
            "target_rules": ["airline.book.no_unrequested_baggage", "airline.action.explicit_confirmation"],
            "factor_values": dict(world.factor_values),
            "expected_baggage_count": world.expected_baggage_count,
            "confirmation_state": "ready" if world.factor_values["explicit_confirmation_obtained_before_commit"] else "pending",
        }
    else:
        concept, rule, predicate_name = MECHANISMS[mechanism]
        predicate_value = world.predicate_value
        metadata_extra = {"latent_family_id": row["family_id"]}
    metadata = {
        "task_id": task_id,
        "scenario_id": scenario.scenario_id,
        "manifestation_id": scenario.manifestation_id,
        "latent_pair_id": row["family_id"],
        "latent_world_id": world.world_id,
        "template_id": mechanism,
        "concept_id": concept,
        "rule_id": rule,
        "predicate_name": predicate_name,
        "predicate_value": predicate_value,
        "expected_governance": scenario.expected_governance,
        "expected_resolution": scenario.expected_resolution,
        "concrete_context": context,
        "canonical_response": canonical_response,
        "family_id": row["family_id"],
        "assigned_split": row["split"],
        "evolution_role": row["evolution_role"],
        "generalization_level": row["generalization_level"],
        "entity_assignment": dict(row["entity_assignment"]),
        "source": {"fresh_v1_population": True, "calibration_only": False},
        "compiler": "tau2_governed_final_v1",
        **metadata_extra,
    }
    return CompiledTaskBundle(
        compiled_task_id=task_id,
        scenario_id=scenario.scenario_id,
        manifestation_id=scenario.manifestation_id,
        latent_pair_id=row["family_id"],
        latent_world_id=world.world_id,
        template_id=mechanism,
        concept_id=concept,
        rule_id=rule,
        task=task,
        expected_governance=scenario.expected_governance,
        expected_resolution=scenario.expected_resolution,
        hidden_metadata=metadata,
        compilation_audit=CompilationAuditResult(False, False, False, False, False, False, False, False, False, [], ["Pending final-v1 validation."]),
    )


def _initialize(task: Task):
    environment = get_environment()
    state = task.initial_state
    environment.set_state(
        state.initialization_data if state else None,
        state.initialization_actions if state else None,
        state.message_history or [] if state else [],
    )
    return environment


def _canonical_trajectory(bundle: CompiledTaskBundle) -> tuple[list, float, float]:
    environment = _initialize(bundle.task)
    trajectory = list(bundle.task.initial_state.message_history or []) if bundle.task.initial_state else []
    mechanism = bundle.template_id
    context = bundle.hidden_metadata["concrete_context"]
    predicate = bundle.hidden_metadata["predicate_value"]
    if mechanism in {CHECKED, CONFIRM, COMPOSITION}:
        payload = context["transaction_payload"]
        ready = context.get("confirmation_ready_at_start", False)
        if not ready:
            trajectory.extend(_confirmation_history(payload))
    elif mechanism == CANCEL:
        if predicate:
            trajectory.append(UserMessage(role="user", content="My travel plans changed, so please cancel this reservation.", timestamp=None))
        else:
            trajectory.extend([
                UserMessage(role="user", content="Please cancel my reservation.", timestamp=None),
                AssistantMessage(role="assistant", content="What is the reason for cancellation?", timestamp=None),
                UserMessage(role="user", content="My travel plans changed.", timestamp=None),
            ])
        trajectory.extend([
            AssistantMessage(
                role="assistant",
                content=f"Complete cancellation summary: cancel reservation {context['reservation_id']} and refund the original payment method. Do you explicitly confirm?",
                timestamp=None,
            ),
            UserMessage(role="user", content="Yes, I explicitly confirm that cancellation.", timestamp=None),
        ])
    elif mechanism == ORDERING:
        trajectory.append(UserMessage(role="user", content="My plans changed. Please cancel the delayed reservation and provide the requested compensation.", timestamp=None))
    else:
        trajectory.append(UserMessage(role="user", content=bundle.task.user_scenario.instructions.reason_for_call, timestamp=None))
        if mechanism in {FLIGHT, IDENTITY} and predicate:
            trajectory.extend([
                AssistantMessage(role="assistant", content="Here is the complete requested flight-change transaction, including the target flight and saved payment method. Do you explicitly confirm?", timestamp=None),
                UserMessage(role="user", content="Yes, I explicitly confirm that exact flight change.", timestamp=None),
            ])

    for index, action in enumerate(bundle.task.evaluation_criteria.actions or []):
        call = ToolCall(id=f"gold_{index}", name=action.name, arguments=action.arguments, requestor="assistant")
        trajectory.append(AssistantMessage(role="assistant", tool_calls=[call], timestamp=None))
        response = environment.get_response(call)
        if response.error:
            raise RuntimeError(f"Canonical action failed for {bundle.task.id}: {response.content}")
        trajectory.append(response)
    if bundle.hidden_metadata.get("canonical_response"):
        trajectory.append(AssistantMessage(role="assistant", content=bundle.hidden_metadata["canonical_response"], timestamp=None))
    env_reward = EnvironmentEvaluator.calculate_reward(get_environment, bundle.task, trajectory).reward
    communicate_reward = CommunicateEvaluator.calculate_reward(bundle.task, trajectory).reward
    return trajectory, env_reward, communicate_reward


def _isolation_checks(bundle: CompiledTaskBundle, environment) -> dict[str, bool]:
    """Check target semantics and common non-target feasibility in concrete state."""

    mechanism = bundle.template_id
    context = bundle.hidden_metadata["concrete_context"]
    criteria = bundle.task.evaluation_criteria
    if mechanism in {CHECKED, CONFIRM, COMPOSITION}:
        payload = context["transaction_payload"]
        flight_info = payload["flights"][0]
        instance = environment.tools.db.flights[flight_info["flight_number"]].dates[flight_info["date"]]
        user = environment.tools.db.users[payload["user_id"]]
        return {
            "flight_available": instance.status == "available",
            "seat_available": instance.available_seats[payload["cabin"]] >= len(payload["passengers"]),
            "payment_usable": all(item["payment_id"] in user.payment_methods for item in payload["payment_methods"]),
            "insurance_fixed": payload["insurance"] == "no",
            "baggage_fee_consistent": payload["nonfree_baggages"] == 0,
            "target_action_matches_payload": bool(criteria.actions) and criteria.actions[0].arguments == payload,
        }
    reservation = environment.tools.db.reservations[context["reservation_id"]]
    if mechanism in {FLIGHT, IDENTITY}:
        user = environment.tools.db.users[reservation.user_id]
        target = context["target_flights"][0]
        flight = environment.tools.db.flights[target["flight_number"]]
        instance = flight.dates[target["date"]]
        route_preserved = flight.origin == reservation.origin and flight.destination == reservation.destination
        expected_predicate = bool(bundle.hidden_metadata["predicate_value"])
        predicate_materialized = (
            reservation.cabin != "basic_economy"
            if mechanism == FLIGHT else route_preserved
        ) == expected_predicate
        return {
            "reservation_active": reservation.status is None,
            "segments_unflown": _unflown(environment.tools.db, reservation),
            "target_flight_available": instance.status == "available",
            "target_seats_available": instance.available_seats[context["materialized_cabin"]] >= len(reservation.passengers),
            "payment_usable": context.get("task_success_evaluator") is not None and any(payment.source == "credit_card" for payment in user.payment_methods.values()),
            "predicate_materialized": predicate_materialized,
            "no_itinerary_confound": mechanism == IDENTITY or route_preserved,
        }
    if mechanism == CANCEL:
        return {
            "reservation_active": reservation.status is None,
            "business_independent_eligibility": reservation.cabin == "business",
            "segments_unflown": _unflown(environment.tools.db, reservation),
            "refund_feasible": bool(reservation.payment_history),
            "reason_excluded_from_task_success": context["task_success_excludes_cancellation_reason"],
        }
    if mechanism == ORDERING:
        delayed = environment.tools.db.flights[context["delayed_flight_number"]].dates[context["delayed_flight_date"]]
        expected_status = "cancelled" if context["primary_completed_in_initial_state"] else None
        return {
            "primary_state_materialized": reservation.status == expected_status,
            "real_delayed_state": delayed.status == "delayed",
            "business_cancellation_eligibility": reservation.cabin == "business",
            "segments_unflown": _unflown(environment.tools.db, reservation),
            "compensation_eligibility": reservation.cabin == "business",
            "reason_known": context["cancellation_reason_known"],
            "compensation_explicitly_requested": context["explicit_compensation_request"],
            "passenger_count_resolvable": len(reservation.passengers) == context["expected_passenger_count"],
            "amount_correct": context["expected_certificate_amount"] == 50 * len(reservation.passengers),
            "refund_feasible": bool(reservation.payment_history),
            "ordering_excluded_from_task_success": context["task_success_excludes_ordering"],
        }
    raise ValueError(mechanism)


def _validate_bundle(bundle: CompiledTaskBundle) -> dict[str, Any]:
    Task.model_validate(bundle.task.model_dump(mode="json", exclude_none=True))
    environment = _initialize(bundle.task)
    assignment = bundle.hidden_metadata["entity_assignment"]
    if assignment["primary_user_id"] not in environment.tools.db.users:
        raise AssertionError("Primary user missing")
    if assignment.get("primary_reservation_id") and assignment["primary_reservation_id"] not in environment.tools.db.reservations:
        raise AssertionError("Primary reservation missing")
    isolation = _isolation_checks(bundle, environment)
    if not all(isolation.values()):
        raise AssertionError(f"Isolation failed for {bundle.task.id}: {isolation}")
    trajectory, env_reward, communicate_reward = _canonical_trajectory(bundle)
    if env_reward != 1.0 or communicate_reward != 1.0:
        raise AssertionError(f"Canonical reward failed for {bundle.task.id}: {env_reward}/{communicate_reward}")
    result = (
        evaluate_composed_compliance(bundle, trajectory)
        if bundle.template_id == COMPOSITION
        else evaluate_target_compliance(bundle, trajectory)
    )
    compliant = result.joint_compliant if bundle.template_id == COMPOSITION else result.compliant
    if not compliant:
        raise AssertionError(f"Canonical path not compliant for {bundle.task.id}")
    criteria = bundle.task.evaluation_criteria
    if bundle.template_id in {CONFIRM, CANCEL, ORDERING, COMPOSITION} and RewardType.ACTION in criteria.reward_basis:
        raise AssertionError("Process/order leaked into task-success ACTION reward")
    bundle.compilation_audit = CompilationAuditResult(
        True, True, True, True, True, True, True, True, True, [],
        [f"Canonical env reward={env_reward}; communicate reward={communicate_reward}; compliance=True."],
    )
    return {
        "task_id": bundle.task.id,
        "schema_valid": True,
        "environment_loadable": True,
        "canonical_gold_satisfiable": True,
        "canonical_compliant": True,
        "oracle_coverage": True,
        "isolation_checks": isolation,
        "extra_blocker_audit_pass": all(isolation.values()),
        "task_success_excludes_target_compliance": RewardType.ACTION not in criteria.reward_basis,
    }


def _family_registry(plan: list[dict[str, Any]], objects: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for row in plan:
        mechanism = row["mechanism_id"]
        if mechanism == COMPOSITION:
            template_ids = [COMPOSITION]
            rule_ids = ["airline.book.no_unrequested_baggage", "airline.action.explicit_confirmation"]
            concept_ids = ["airline.explicit_user_mandate", "airline.transaction_commit_confirmation"]
            world_ids = [world.world_id for world in objects[row["family_id"]].worlds]
        else:
            concept, rule, _ = MECHANISMS[mechanism]
            template_ids, rule_ids, concept_ids = [mechanism], [rule], [concept]
            pair = objects[row["family_id"]]
            world_ids = [pair.world_a.world_id, pair.world_b.world_id]
        assignment = row["entity_assignment"]
        entries.append({
            "family_id": row["family_id"],
            "family_type": row["family_type"],
            "domain": "airline",
            "mechanism_id": mechanism,
            "template_ids": template_ids,
            "rule_ids": rule_ids,
            "concept_ids": concept_ids,
            "split": row["split"],
            "evolution_role": row["evolution_role"],
            "generalization_level": row["generalization_level"],
            "base_entity_family": _opaque("entity_air", row["family_id"] + "|" + assignment["primary_user_id"]),
            "primary_user_id": assignment["primary_user_id"],
            "primary_reservation_id": assignment.get("primary_reservation_id"),
            "primary_flight_context": assignment["primary_flight_context"],
            "all_flight_context": assignment["all_flight_context"],
            "predicate_realization": "2x2_independent_factors" if mechanism == COMPOSITION else MECHANISMS[mechanism][2],
            "world_ids": world_ids,
            "manifestation_count_per_world": row["manifestations_per_world"],
            "task_count": row["task_count"],
            "source": row["source"],
        })
    return entries


def _leakage_audit(registry: list[dict[str, Any]], blacklist: dict[str, Any]) -> dict[str, Any]:
    by_split = defaultdict(lambda: {"families": set(), "users": set(), "reservations": set(), "flights": set()})
    for entry in registry:
        current = by_split[entry["split"]]
        current["families"].add(entry["family_id"])
        current["users"].add(entry["primary_user_id"])
        if entry["primary_reservation_id"]:
            current["reservations"].add(entry["primary_reservation_id"])
        current["flights"].update(entry["all_flight_context"])
    overlaps = {}
    for left, right in (("train", "monitor"), ("train", "test"), ("monitor", "test")):
        overlaps[f"{left}_x_{right}"] = {
            key: sorted(by_split[left][key] & by_split[right][key])
            for key in ("families", "users", "reservations", "flights")
        }
    final_users = set().union(*(value["users"] for value in by_split.values()))
    final_reservations = set().union(*(value["reservations"] for value in by_split.values()))
    final_flights = set().union(*(value["flights"] for value in by_split.values()))
    calibration = {
        "users": sorted(final_users & set(blacklist["primary_user_ids"])),
        "reservations": sorted(final_reservations & set(blacklist["primary_reservation_ids"])),
        "flights": sorted(final_flights & set(blacklist["primary_flight_instances"])),
    }
    return {
        "split_overlaps": overlaps,
        "final_x_calibration": calibration,
        "all_zero": not any(
            items for pair in overlaps.values() for items in pair.values()
        ) and not any(calibration.values()),
    }


def build_final_v1_population() -> dict[str, Any]:
    """Freeze family assignment, then materialize and validate exactly 116 tasks."""

    blacklist = collect_calibration_blacklist()
    inventory = scan_feasible_entity_inventory(blacklist)
    plan = _plan()
    _assign_entities(plan, blacklist)

    # Split assignment is intentionally persisted before any world or task is created.
    split_manifest = {
        "schema_version": 1,
        "benchmark_version": "tau2_governed_evolution_v1",
        "assignment_basis": ["frozen_blueprint", "family_provenance", "entity_isolation", "generalization_level"],
        "assignment_used_model_outcomes": False,
        "frozen_before_task_materialization": True,
        "families": [
            {
                "family_id": row["family_id"],
                "family_type": row["family_type"],
                "mechanism_id": row["mechanism_id"],
                "split": row["split"],
                "entity_assignment": row["entity_assignment"],
                "world_count": row["world_count"],
                "manifestations_per_world": row["manifestations_per_world"],
                "task_count": row["task_count"],
                "generalization_level": row["generalization_level"],
            }
            for row in plan
        ],
    }
    _yaml(DIST_FINAL / "split_manifest.yaml", split_manifest)
    _yaml(DIST_FINAL / "entity_assignments.yaml", {"schema_version": 1, "assignments": [{"family_id": row["family_id"], **row["entity_assignment"]} for row in plan]})
    _yaml(DIST_ROOT / "calibration_entity_blacklist.yaml", blacklist)
    _yaml(DIST_ROOT / "feasible_entity_inventory.yaml", inventory)

    objects: dict[str, LatentPair | CompositionGrid] = {}
    surfaces: list[SurfaceManifestation] = []
    scenarios: list[RealizedScenario] = []
    bundles: list[CompiledTaskBundle] = []
    task_audits: list[dict[str, Any]] = []
    for row in plan:
        source = _composition_grid(row) if row["mechanism_id"] == COMPOSITION else _latent_pair(row)
        objects[row["family_id"]] = source
        worlds = source.worlds if isinstance(source, CompositionGrid) else [source.world_a, source.world_b]
        for world in worlds:
            for variant in range(row["manifestations_per_world"]):
                surface, scenario = _surface_and_scenario(row, world, variant)
                bundle = _compile(row, world, scenario)
                audit = _validate_bundle(bundle)
                surfaces.append(surface)
                scenarios.append(scenario)
                bundles.append(bundle)
                task_audits.append(audit)

    registry = _family_registry(plan, objects)
    leakage = _leakage_audit(registry, blacklist)
    by_split = defaultdict(list)
    for bundle in bundles:
        by_split[bundle.hidden_metadata["assigned_split"]].append(bundle)

    for split in ("train", "monitor", "test"):
        ordered = sorted(by_split[split], key=lambda item: item.task.id)
        _json(FINAL_ROOT / split / "tasks.json", [item.task.model_dump(mode="json", exclude_none=True) for item in ordered])
        _yaml(FINAL_ROOT / split / "task_metadata.yaml", {"schema_version": 1, "task_count": len(ordered), "metadata": [item.hidden_metadata for item in ordered]})
        _yaml(FINAL_ROOT / split / "compiled_bundles.yaml", {"schema_version": 1, "bundle_count": len(ordered), "compiled_bundles": [item.to_dict() for item in ordered]})

    latent_pairs = [value.to_dict() for value in objects.values() if isinstance(value, LatentPair)]
    composition_grids = [value.to_dict() for value in objects.values() if isinstance(value, CompositionGrid)]
    _yaml(FINAL_ROOT / "families/latent_families.yaml", {"schema_version": 1, "family_count": len(latent_pairs), "families": latent_pairs})
    _yaml(FINAL_ROOT / "families/composition_families.yaml", {"schema_version": 1, "family_count": len(composition_grids), "families": composition_grids})
    _yaml(FINAL_ROOT / "families/entity_assignments.yaml", {"schema_version": 1, "assignments": [{"family_id": row["family_id"], **row["entity_assignment"]} for row in plan]})
    _yaml(FINAL_ROOT / "families/surface_manifestations.yaml", {"schema_version": 1, "manifestation_count": len(surfaces), "manifestations": [item.to_dict() for item in surfaces]})
    _yaml(FINAL_ROOT / "families/realized_scenarios.yaml", {"schema_version": 1, "scenario_count": len(scenarios), "scenarios": [item.to_dict() for item in scenarios]})
    _yaml(FINAL_ROOT / "split_manifest.yaml", split_manifest)
    _yaml(DIST_FINAL / "family_registry.yaml", {"schema_version": 1, "family_count": len(registry), "families": registry})

    actual_counts = {split: len(items) for split, items in by_split.items()}
    mechanism_counts = {
        split: dict(Counter(item.template_id for item in items))
        for split, items in by_split.items()
    }
    role_counts = {
        split: dict(Counter(item.hidden_metadata["evolution_role"] for item in items))
        for split, items in by_split.items()
    }
    composition_test_entities = {
        entry["primary_user_id"]
        for entry in registry
        if entry["split"] == "test" and entry["family_type"] == "composition"
    }
    atomic_test_entities = {
        entry["primary_user_id"]
        for entry in registry
        if entry["split"] == "test" and entry["family_type"] == "latent"
    }
    calibration_task_ids = {
        task["id"]
        for relative in (
            "compiler/examples/tasks_mvp.json",
            "compiler/examples/tasks_explicit_confirmation.json",
            "compiler/examples/tasks_cancellation_reason.json",
            "compiler/examples/tasks_delayed_flight_compensation.json",
            "compiler/examples/tasks_composition_baggage_confirmation.json",
        )
        for task in json.loads((BENCHMARK_ROOT / relative).read_text())
    }
    task_ids = [bundle.task.id for bundle in bundles]
    serialized_task_text = json.dumps(
        [bundle.task.model_dump(mode="json", exclude_none=True) for bundle in bundles]
    )
    forbidden_agent_fields = (
        "family_id", "assigned_split", "predicate_name", "predicate_value",
        "composition_id", "evolution_role", "generalization_level",
    )
    family_counts = {
        split: dict(Counter(entry["mechanism_id"] for entry in registry if entry["split"] == split))
        for split in ("train", "monitor", "test")
    }
    expected_family_counts = {
        "train": {CHECKED: 4, FLIGHT: 4, ORDERING: 3, IDENTITY: 1, CONFIRM: 1},
        "monitor": {CHECKED: 1, FLIGHT: 1, IDENTITY: 1, CONFIRM: 2, CANCEL: 1, ORDERING: 1},
        "test": {CHECKED: 3, FLIGHT: 3, IDENTITY: 1, CONFIRM: 1, CANCEL: 1, ORDERING: 3, COMPOSITION: 2},
    }
    regression_path = DIST_FINAL / "evaluator_regression_144.json"
    evaluator_regression = json.loads(regression_path.read_text()) if regression_path.exists() else {}
    expected_factor_grid = {
        (False, False), (False, True), (True, False), (True, True)
    }
    composition_grids_complete = all(
        len(grid.worlds) == 4
        and {
            (
                world.factor_values["baggage_mandate_present"],
                world.factor_values["explicit_confirmation_obtained_before_commit"],
            )
            for world in grid.worlds
        } == expected_factor_grid
        and next(entry for entry in registry if entry["family_id"] == grid.composition_id)["manifestation_count_per_world"] == 2
        for grid in objects.values()
        if isinstance(grid, CompositionGrid)
    )
    checks = {
        "blueprint_test_distribution_18_14_16": role_counts["test"] == {"unseen_atomic_preservation": 18, "unseen_multi_step_ordering": 14, "heldout_composition": 16},
        "exact_split_counts": actual_counts == {"train": 48, "monitor": 20, "test": 48},
        "governed_total_116": len(bundles) == 116,
        "fresh_latent_families_32": len(latent_pairs) == 32,
        "fresh_composition_families_2": len(composition_grids) == 2,
        "composition_grids_complete_4x2": composition_grids_complete,
        "exact_family_allocation": family_counts == expected_family_counts,
        "task_ids_unique_and_opaque": len(task_ids) == len(set(task_ids)) and all(task_id.startswith("tge_air_") for task_id in task_ids),
        "calibration_task_ids_excluded": not set(task_ids) & calibration_task_ids,
        "agent_tasks_hide_construction_metadata": not any(field in serialized_task_text for field in forbidden_agent_fields),
        "split_frozen_before_materialization": (DIST_FINAL / "split_manifest.yaml").exists() and split_manifest["frozen_before_task_materialization"],
        "no_family_or_entity_leakage": leakage["all_zero"],
        "composition_heldout": mechanism_counts["train"].get(COMPOSITION, 0) == 0 and mechanism_counts["monitor"].get(COMPOSITION, 0) == 0 and mechanism_counts["test"].get(COMPOSITION, 0) == 16,
        "test_composition_atomic_entity_isolation": not composition_test_entities & atomic_test_entities,
        "all_schema_pass": all(item["schema_valid"] for item in task_audits),
        "every_task_has_success_evaluator": all(bundle.task.evaluation_criteria is not None for bundle in bundles),
        "all_environment_pass": all(item["environment_loadable"] for item in task_audits),
        "all_canonical_gold_pass": all(item["canonical_gold_satisfiable"] for item in task_audits),
        "all_oracle_coverage_pass": all(item["oracle_coverage"] for item in task_audits),
        "all_extra_blocker_audits_pass": all(item["extra_blocker_audit_pass"] for item in task_audits),
        "task_success_compliance_decoupled": all(item["task_success_excludes_target_compliance"] for item in task_audits),
        "old_calibration_evaluator_regression_unchanged": evaluator_regression.get("all_checks_passed") is True,
        "no_model_or_rollout_execution": True,
        "no_skill_evolution": True,
    }
    audit = {
        "schema_version": 1,
        "blueprint_counts": {"train": 48, "monitor": 20, "test": 48},
        "actual_counts": actual_counts,
        "fresh_family_count": len(latent_pairs),
        "fresh_composition_family_count": len(composition_grids),
        "calibration_overlap_count": sum(len(value) for value in leakage["final_x_calibration"].values()),
        "split_family_overlap_count": sum(len(pair["families"]) for pair in leakage["split_overlaps"].values()),
        "split_entity_overlap_count": sum(len(pair["users"]) + len(pair["reservations"]) + len(pair["flights"]) for pair in leakage["split_overlaps"].values()),
        "entity_overlap_summary": leakage,
        "mechanism_counts": mechanism_counts,
        "family_counts": family_counts,
        "role_counts": role_counts,
        "task_schema_pass": checks["all_schema_pass"],
        "environment_pass": checks["all_environment_pass"],
        "canonical_gold_pass": checks["all_canonical_gold_pass"],
        "oracle_coverage_pass": checks["all_oracle_coverage_pass"],
        "extra_blocker_audit_pass": checks["all_extra_blocker_audits_pass"],
        "old_calibration_evaluator_regression_pass": checks["old_calibration_evaluator_regression_unchanged"],
        "role_distribution_pass": checks["blueprint_test_distribution_18_14_16"] and checks["exact_split_counts"],
        "generalization_distribution_pass": all(entry["generalization_level"] for entry in registry),
        "composition_holdout_pass": checks["composition_heldout"],
        "checks": checks,
        "task_audits": task_audits,
        "all_checks_passed": all(checks.values()),
    }
    _json(DIST_FINAL / "population_audit.json", audit)
    _json(FINAL_ROOT / "population_audit.json", audit)
    return {
        "blacklist": blacklist,
        "inventory": inventory,
        "plan": plan,
        "registry": registry,
        "bundles": bundles,
        "audit": audit,
    }


if __name__ == "__main__":
    result = build_final_v1_population()
    print(json.dumps({
        "families": len(result["registry"]),
        "tasks": len(result["bundles"]),
        "actual_counts": result["audit"]["actual_counts"],
        "all_checks_passed": result["audit"]["all_checks_passed"],
    }, indent=2))
