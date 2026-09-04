"""Static Airline inventory and calibration-primary exclusion for final v1."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from ..compiler.resolvers import ensure_tau2_importable

ensure_tau2_importable()

from tau2.domains.airline.data_model import (  # noqa: E402
    FlightDataStatusFlying,
    FlightDateStatusLanded,
)
from tau2.domains.airline.environment import get_environment  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
METADATA_GLOBS = (
    "compiler/examples/task_metadata_mvp.yaml",
    "compiler/examples/task_metadata_explicit_confirmation.yaml",
    "compiler/examples/task_metadata_cancellation_reason.yaml",
    "compiler/examples/task_metadata_delayed_flight_compensation.yaml",
    "compiler/examples/task_metadata_composition_baggage_confirmation.yaml",
)
TASK_GLOBS = (
    "compiler/examples/tasks_mvp.json",
    "compiler/examples/tasks_explicit_confirmation.json",
    "compiler/examples/tasks_cancellation_reason.json",
    "compiler/examples/tasks_delayed_flight_compensation.json",
    "compiler/examples/tasks_composition_baggage_confirmation.json",
)


def _walk(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _dicts(item)


def collect_calibration_blacklist() -> dict[str, Any]:
    """Extract primary structured IDs from all 48 calibration tasks and metadata."""

    users: set[str] = set()
    reservations: set[str] = set()
    flight_instances: set[str] = set()
    booking_contexts: set[str] = set()
    task_ids: set[str] = set()
    source_files: list[str] = []

    payloads: list[Any] = []
    for relative in METADATA_GLOBS:
        path = ROOT / relative
        data = yaml.safe_load(path.read_text())
        payloads.extend(data.get("metadata", []))
        source_files.append(relative)
    for relative in TASK_GLOBS:
        path = ROOT / relative
        tasks = json.loads(path.read_text())
        payloads.extend(tasks)
        task_ids.update(task["id"] for task in tasks)
        source_files.append(relative)

    for payload in payloads:
        for key, value in _walk(payload):
            if key == "user_id" and isinstance(value, str):
                users.add(value)
            elif key == "reservation_id" and isinstance(value, str):
                reservations.add(value)
            elif key in {"flight_number", "delayed_flight_number"} and isinstance(value, str):
                # Dates are paired below from their containing dictionaries.
                pass
        for value in _dicts(payload):
            flight_number = value.get("flight_number") or value.get("delayed_flight_number")
            date = value.get("date") or value.get("delayed_flight_date")
            if isinstance(flight_number, str) and isinstance(date, str):
                flight_instances.add(f"{flight_number}@{date}")
            if {
                "user_id",
                "origin",
                "destination",
                "flights",
            }.issubset(value):
                instances = ",".join(
                    f"{item.get('flight_number')}@{item.get('date')}"
                    for item in value.get("flights", [])
                )
                booking_contexts.add(
                    f"{value['user_id']}|{value['origin']}|{value['destination']}|{instances}"
                )

    return {
        "schema_version": 1,
        "generated_from_structured_assets": True,
        "calibration_task_count": len(task_ids),
        "source_files": source_files,
        "primary_user_ids": sorted(users),
        "primary_reservation_ids": sorted(reservations),
        "primary_flight_instances": sorted(flight_instances),
        "primary_booking_contexts": sorted(booking_contexts),
        "entity_family_count": len(users) + len(reservations) + len(booking_contexts),
    }


def _unflown(db, reservation) -> bool:
    return all(
        not isinstance(
            db.flights[item.flight_number].dates[item.date],
            (FlightDataStatusFlying, FlightDateStatusLanded),
        )
        for item in reservation.flights
    )


def scan_feasible_entity_inventory(blacklist: dict[str, Any]) -> dict[str, Any]:
    """Count policy-feasible native candidates without consulting model outcomes."""

    environment = get_environment()
    db = environment.tools.db
    blocked_users = set(blacklist["primary_user_ids"])
    blocked_reservations = set(blacklist["primary_reservation_ids"])
    blocked_flights = set(blacklist["primary_flight_instances"])

    available_by_route: dict[tuple[str, str], list[tuple[str, str, int]]] = defaultdict(list)
    for flight_number, flight in db.flights.items():
        for date, state in flight.dates.items():
            key = f"{flight_number}@{date}"
            if state.status == "available" and key not in blocked_flights:
                available_by_route[(flight.origin, flight.destination)].append(
                    (flight_number, date, min(state.available_seats.values()))
                )

    booking_users = []
    for user in db.users.values():
        credit_cards = [
            payment_id
            for payment_id, payment in user.payment_methods.items()
            if payment.source == "credit_card"
        ]
        if (
            user.user_id not in blocked_users
            and user.saved_passengers
            and credit_cards
        ):
            booking_users.append(user.user_id)

    active_unflown = []
    change_candidates = []
    business_cancellation = []
    native_delayed_business = []
    ordering_bases = []
    for reservation in db.reservations.values():
        if (
            reservation.reservation_id in blocked_reservations
            or reservation.user_id in blocked_users
            or reservation.status is not None
            or not _unflown(db, reservation)
        ):
            continue
        user = db.users[reservation.user_id]
        credit_cards = [
            payment_id
            for payment_id, payment in user.payment_methods.items()
            if payment.source == "credit_card"
        ]
        source_instances = {
            f"{item.flight_number}@{item.date}" for item in reservation.flights
        }
        if source_instances & blocked_flights:
            continue
        active_unflown.append(reservation.reservation_id)
        if reservation.cabin == "business":
            business_cancellation.append(reservation.reservation_id)
            if all(
                db.flights[item.flight_number].dates[item.date].status == "available"
                for item in reservation.flights
            ):
                ordering_bases.append(reservation.reservation_id)
            if any(
                db.flights[item.flight_number].dates[item.date].status == "delayed"
                for item in reservation.flights
            ):
                native_delayed_business.append(reservation.reservation_id)
        if reservation.flight_type != "one_way" or not credit_cards:
            continue
        alternatives = [
            item
            for item in available_by_route[(reservation.origin, reservation.destination)]
            if f"{item[0]}@{item[1]}" not in source_instances
            and item[2] >= len(reservation.passengers)
        ]
        violating = [
            item
            for (origin, destination), options in available_by_route.items()
            if origin == reservation.origin and destination != reservation.destination
            for item in options
            if item[2] >= len(reservation.passengers)
        ]
        if alternatives and violating:
            change_candidates.append(reservation.reservation_id)

    return {
        "schema_version": 1,
        "selection_basis": [
            "native Airline DB",
            "policy and tool feasibility",
            "target-mechanism isolation",
            "calibration-primary exclusion",
        ],
        "database_counts": {
            "users": len(db.users),
            "reservations": len(db.reservations),
            "flights": len(db.flights),
        },
        "fresh_candidate_counts": {
            "booking_users_with_saved_passenger_and_credit_card": len(booking_users),
            "available_flight_instances": sum(map(len, available_by_route.values())),
            "active_unflown_reservations": len(active_unflown),
            "flight_change_direct_route_candidates": len(change_candidates),
            "business_cancellation_candidates": len(business_cancellation),
            "native_delayed_business_candidates": len(native_delayed_business),
            "business_available_ordering_bases": len(ordering_bases),
        },
        "candidate_ids": {
            "booking_users": sorted(booking_users),
            "change_reservations": sorted(change_candidates),
            "business_cancellation_reservations": sorted(business_cancellation),
            "native_delayed_business_reservations": sorted(native_delayed_business),
            "ordering_base_reservations": sorted(ordering_bases),
        },
        "ordering_native_shortage": len(native_delayed_business) < 7,
        "ordering_minimal_state_strategy": (
            "Use seven distinct fresh native business reservations and materialize only one target flight instance as delayed."
        ),
    }


def extract_ids_from_text(text: str) -> dict[str, list[str]]:
    """Small audit helper; structured extraction remains authoritative."""

    return {
        "reservation_like": sorted(set(re.findall(r"\b[A-Z0-9]{6}\b", text))),
        "flight_like": sorted(set(re.findall(r"\bHAT\d{3}\b", text))),
    }
