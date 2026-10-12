"""Representation-neutral Task Success for endpoint-preservation fixtures."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any


def _person(value: dict[str, Any]) -> tuple[str, str, str]:
    return value["first_name"].casefold(), value["last_name"].casefold(), value["dob"]


def _route(reservation: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    return [
        (
            item["origin"],
            item["destination"],
            item["flight_number"],
            item["date"],
        )
        for item in reservation["flights"]
    ]


def _active_user_reservations(
    db: dict[str, Any], user_id: str
) -> list[dict[str, Any]]:
    return [
        row
        for row in db["reservations"].values()
        if row["user_id"] == user_id and row.get("status") != "cancelled"
    ]


def _incremental_charge(
    spec: dict[str, Any], initial_db: dict[str, Any], final_db: dict[str, Any]
) -> Decimal:
    def total(db: dict[str, Any]) -> Decimal:
        return sum(
            (
                Decimal(str(payment["amount"]))
                for reservation in db["reservations"].values()
                if reservation["user_id"] == spec["user_id"]
                for payment in reservation["payment_history"]
            ),
            Decimal(0),
        )

    return total(final_db) - total(initial_db)


def evaluate(
    spec: dict[str, Any], initial_db: dict[str, Any], final_db: dict[str, Any]
) -> dict[str, Any]:
    reservations = _active_user_reservations(final_db, spec["user_id"])
    expected_people = Counter(_person(row) for row in spec["passengers"])

    def matches_service(row: dict[str, Any]) -> bool:
        return (
            Counter(_person(person) for person in row["passengers"]) == expected_people
            and row["cabin"] == spec["cabin"]
            and row["total_baggages"] == spec["total_baggages"]
            and row["nonfree_baggages"] == spec["nonfree_baggages"]
            and row["insurance"] == spec["insurance"]
        )

    desired = [
        (
            spec["target_origin"],
            spec["target_destination"],
            flight["flight_number"],
            flight["date"],
        )
        for flight in spec["target_flights"]
    ]
    focal_reservation_active = (
        final_db["reservations"][spec["reservation_id"]].get("status")
        != "cancelled"
    )
    if spec["topology"] == "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT":
        matching = [
            row for row in reservations
            if _route(row) == desired and matches_service(row)
        ]
        outcome_ok = len(matching) == 1
    elif spec["topology"] == "APPENDED_REVERSE_RETURN":
        outbound = [
            (
                spec["initial_origin"],
                spec["initial_destination"],
                spec["initial_flight"]["flight_number"],
                spec["initial_flight"]["date"],
            )
        ]
        allowed = [
            row for row in reservations
            if matches_service(row) and _route(row) in (outbound, desired, outbound + desired)
        ]
        leg_counts = Counter(
            leg for row in allowed for leg in _route(row)
        )
        outcome_ok = leg_counts == Counter(outbound + desired)
    else:
        raise ValueError(f"Unknown topology: {spec['topology']}")

    incremental_charge = _incremental_charge(spec, initial_db, final_db)
    budget_ok = Decimal(0) <= incremental_charge <= Decimal(str(spec["budget"]))
    success = bool(outcome_ok and budget_ok and focal_reservation_active)
    return {
        "success": success,
        "travel_outcome_present": bool(outcome_ok),
        "incremental_charge": float(incremental_charge),
        "budget_ok": bool(budget_ok),
        "focal_reservation_active": focal_reservation_active,
        "representation_neutral": True,
    }
