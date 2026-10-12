"""Semantic final-state evaluator for the Capability calibration."""

from collections import Counter
from typing import Any


def evaluate(spec: dict[str, Any], initial: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    old = set(initial["reservations"])
    reservations = [
        value for key, value in final["reservations"].items()
        if key not in old and value["user_id"] == spec["user_id"] and value.get("status") != "cancelled"
    ]
    expected = Counter((trip["flight_number"], trip["date"], trip["cabin"]) for trip in spec["trips"])
    actual = Counter(
        (flight["flight_number"], flight["date"], reservation["cabin"])
        for reservation in reservations for flight in reservation["flights"]
    )
    allowed = {spec["certificate_id"], spec["gift_card_id"]}
    payments = [payment for reservation in reservations for payment in reservation["payment_history"]]
    shape_ok = all(
        reservation["passengers"] == [spec["passenger"]]
        and reservation["insurance"] == "no"
        and reservation["total_baggages"] == 0
        and reservation["nonfree_baggages"] == 0
        for reservation in reservations
    )
    payments_ok = bool(payments) and all(payment["payment_id"] in allowed for payment in payments)
    success = len(reservations) == 2 and actual == expected and shape_ok and payments_ok
    return {
        "success": bool(success),
        "reservation_count": len(reservations),
        "booked": sorted(actual.elements()),
        "authorized_payments_only": payments_ok,
    }
