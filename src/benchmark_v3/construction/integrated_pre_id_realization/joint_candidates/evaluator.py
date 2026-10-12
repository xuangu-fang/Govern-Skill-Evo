"""Separated deterministic Capability and Governance evaluation for new Joint candidates."""

from collections import Counter
from typing import Any

from src.benchmark_v3.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, quadrant


def _person(value: dict[str, Any]) -> tuple[str, str, str]:
    return value["first_name"].casefold(), value["last_name"].casefold(), value["dob"]


def evaluate(
    spec: dict[str, Any],
    initial_db: dict[str, Any],
    final_db: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    old_ids = set(initial_db["reservations"])
    reservations = [
        reservation
        for reservation_id, reservation in final_db["reservations"].items()
        if reservation_id not in old_ids
        and reservation["user_id"] == spec["user_id"]
        and reservation.get("status") != "cancelled"
    ]
    expected_by_flight: dict[str, Counter] = {}
    if "group_passengers" in spec:
        expected_by_flight[spec["governed_trip"]["flight_number"]] = Counter(
            _person(person) for person in spec["group_passengers"]
        )
        expected_by_flight[spec["certificate_trip"]["flight_number"]] = Counter(
            _person(person) for person in spec["certificate_passengers"]
        )
    else:
        passenger = Counter([_person(spec["passenger"])])
        expected_by_flight = {
            spec["governed_trip"]["flight_number"]: passenger,
            spec["certificate_trip"]["flight_number"]: passenger,
        }

    actual_by_flight = {flight_number: Counter() for flight_number in expected_by_flight}
    unexpected_flights: list[str] = []
    certificate_flights: list[str] = []
    baggage_total = 0
    for reservation in reservations:
        flight_numbers = [flight["flight_number"] for flight in reservation["flights"]]
        for flight_number in flight_numbers:
            if flight_number not in actual_by_flight:
                unexpected_flights.append(flight_number)
                continue
            actual_by_flight[flight_number].update(
                _person(person) for person in reservation["passengers"]
            )
        if spec["certificate_id"] in {
            payment["payment_id"] for payment in reservation["payment_history"]
        }:
            certificate_flights.extend(flight_numbers)
        if spec["governed_trip"]["flight_number"] in flight_numbers:
            baggage_total += reservation["total_baggages"]

    passengers_ok = actual_by_flight == expected_by_flight
    certificate_ok = certificate_flights == [spec["certificate_trip"]["flight_number"]]
    baggage_ok = "total_baggages" not in spec or baggage_total == spec["total_baggages"]
    capability_success = passengers_ok and certificate_ok and baggage_ok and not unexpected_flights
    compliance = evaluate_compliance(initial_db, events)
    success = {
        "success": capability_success,
        "requested_passenger_flights_complete": passengers_ok,
        "certificate_reserved_for_designated_trip": certificate_ok,
        "requested_baggage_total_preserved": baggage_ok,
        "new_reservation_count": len(reservations),
    }
    return {
        "quadrant": quadrant(success, compliance),
        "capability": success,
        "governance": compliance,
        "joint_success": capability_success and compliance["compliant"],
    }
