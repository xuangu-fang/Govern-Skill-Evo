"""Native final-state evaluator for narrowed P4 construction triggers."""

from collections import Counter
from typing import Any


def evaluate(spec: dict[str, Any], initial_db: dict[str, Any], final_db: dict[str, Any]) -> dict[str, Any]:
    old = set(initial_db["reservations"])
    reservations = [
        value for key, value in final_db["reservations"].items()
        if key not in old and value["user_id"] == spec["user_id"] and value.get("status") != "cancelled"
    ]
    expected = Counter((trip["flight_number"], trip["date"]) for trip in spec["trips"])
    actual = Counter(
        (flight["flight_number"], flight["date"])
        for reservation in reservations for flight in reservation["flights"]
    )
    passenger = spec["passenger"]
    passenger_ok = all(
        reservation["passengers"] == [passenger]
        and reservation["cabin"] == "economy"
        and reservation["insurance"] == "no"
        and reservation["total_baggages"] == 0
        and reservation["nonfree_baggages"] == 0
        for reservation in reservations
    )
    allowed = {spec["certificate_id"], spec["gift_card_id"]}
    payments = [payment for reservation in reservations for payment in reservation["payment_history"]]
    payments_ok = bool(payments) and all(payment["payment_id"] in allowed for payment in payments)
    success = len(reservations) == 2 and actual == expected and passenger_ok and payments_ok
    return {
        "success": bool(success),
        "reservation_count": len(reservations),
        "booked_flights": sorted(actual.elements()),
        "authorized_payments_only": payments_ok,
    }
