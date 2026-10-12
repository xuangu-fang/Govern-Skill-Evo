"""Final-state Success evaluator for the three Phase-10 candidates.

This module checks user-goal completion only. It never invokes tools and does not
score policy compliance, confirmation, communication, or focal mechanisms.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def evaluate(spec, initial_db, final_db):
    try:
        failures = _failures(spec, initial_db, final_db)
    except (KeyError, TypeError, ValueError, IndexError):
        failures = ["malformed_or_missing_final_state"]
    success = not failures
    return {
        "success": success,
        "reward": float(success),
        "compliance_evaluated": False,
        "basis": "user_goal_final_state_properties",
        "failures": failures,
    }


def _money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def _payment_totals(history):
    totals = defaultdict(lambda: Decimal("0"))
    for payment in history:
        totals[payment["payment_id"]] += _money(payment["amount"])
    return dict(totals)


def _goal_matches(actual, goal):
    exact_fields = (
        "origin",
        "destination",
        "flight_type",
        "cabin",
        "passengers",
        "total_baggages",
        "nonfree_baggages",
        "insurance",
        "flights",
    )
    return (
        actual.get("status") != "cancelled"
        and all(actual.get(field) == goal[field] for field in exact_fields)
        and _money(sum(p["amount"] for p in actual["payment_history"]))
        == _money(goal["total"])
    )


def _new_reservations(before, after, user_id):
    old_ids = set(before["users"][user_id]["reservations"])
    ids = [rid for rid in after["users"][user_id]["reservations"] if rid not in old_ids]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate reservation id")
    return [(rid, after["reservations"][rid]) for rid in ids]


def _match_goals(rows, goals, allowed_resources):
    if len(rows) != len(goals):
        return False
    unmatched = list(goals)
    for _, reservation in rows:
        if reservation["user_id"] != goals[0]["user_id"]:
            return False
        if any(
            p["payment_id"] not in allowed_resources or _money(p["amount"]) < 0
            for p in reservation["payment_history"]
        ):
            return False
        index = next(
            (i for i, goal in enumerate(unmatched) if _goal_matches(reservation, goal)),
            None,
        )
        if index is None:
            return False
        unmatched.pop(index)
    return not unmatched


def _expected_profile(before, after, spec, payment_events, new_ids):
    user_id = spec["user_id"]
    expected = copy.deepcopy(before["users"][user_id])
    expected["reservations"] = list(before["users"][user_id]["reservations"]) + list(new_ids)
    for payment_id, amount in payment_events:
        method = expected["payment_methods"][payment_id]
        if method["source"] == "certificate":
            expected["payment_methods"].pop(payment_id)
        elif method["source"] == "gift_card":
            method["amount"] = float(_money(method["amount"]) - _money(amount))
    return expected == after["users"][user_id]


def _own_reservations_unchanged(before, after, user_id, excluded):
    for reservation_id in before["users"][user_id]["reservations"]:
        if reservation_id not in excluded and (
            after["reservations"].get(reservation_id) != before["reservations"][reservation_id]
        ):
            return False
    return True


def _booking_payment_events(rows):
    return [
        (payment["payment_id"], payment["amount"])
        for _, reservation in rows
        for payment in reservation["payment_history"]
    ]


def _failures(spec, before, after):
    kind = spec["kind"]
    if kind == "mixed_booking_update":
        return _mixed_failures(spec, before, after)
    if kind == "three_bookings":
        return _three_booking_failures(spec, before, after)
    if kind == "trip_type_change":
        return _trip_type_failures(spec, before, after)
    raise ValueError("unsupported Phase-10 evaluator kind")


def _mixed_failures(spec, before, after):
    failures = []
    user_id = spec["user_id"]
    rows = _new_reservations(before, after, user_id)
    if not _match_goals(rows, [spec["booking"]], set(spec["allowed_resources"])):
        failures.append("booking_goal_not_completed")

    reservation_id = spec["update"]["reservation_id"]
    original = before["reservations"][reservation_id]
    actual = after["reservations"][reservation_id]
    update = spec["update"]
    preserve = (
        "origin",
        "destination",
        "flight_type",
        "passengers",
        "total_baggages",
        "nonfree_baggages",
        "insurance",
    )
    if (
        actual.get("status") == "cancelled"
        or actual["cabin"] != update["cabin"]
        or actual["flights"] != update["flights"]
        or any(actual[field] != original[field] for field in preserve)
    ):
        failures.append("cabin_update_goal_not_completed")

    old_history = original["payment_history"]
    if actual["payment_history"][: len(old_history)] != old_history:
        failures.append("original_update_payment_history_changed")
        update_payments = []
    else:
        update_payments = actual["payment_history"][len(old_history) :]
    if (
        any(p["payment_id"] not in spec["allowed_resources"] for p in update_payments)
        or _money(sum(p["amount"] for p in update_payments))
        != _money(update["fare_difference"])
    ):
        failures.append("update_payment_result_incorrect")

    events = _booking_payment_events(rows) + [
        (payment["payment_id"], payment["amount"]) for payment in update_payments
    ]
    if not _expected_profile(before, after, spec, events, [rid for rid, _ in rows]):
        failures.append("final_payment_or_profile_state_incorrect")
    if not _own_reservations_unchanged(before, after, user_id, {reservation_id}):
        failures.append("unrequested_reservation_changed")
    return failures


def _three_booking_failures(spec, before, after):
    failures = []
    user_id = spec["user_id"]
    rows = _new_reservations(before, after, user_id)
    if not _match_goals(rows, spec["bookings"], set(spec["allowed_resources"])):
        failures.append("three_booking_goals_not_completed")
    events = _booking_payment_events(rows)
    if not _expected_profile(before, after, spec, events, [rid for rid, _ in rows]):
        failures.append("final_payment_or_profile_state_incorrect")
    if not _own_reservations_unchanged(before, after, user_id, set()):
        failures.append("unrequested_reservation_changed")
    return failures


def _trip_type_failures(spec, before, after):
    failures = []
    user_id = spec["user_id"]
    reservation_id = spec["reservation_id"]
    original = before["reservations"][reservation_id]
    actual = after["reservations"][reservation_id]
    preserve = (
        "origin",
        "destination",
        "cabin",
        "passengers",
        "total_baggages",
        "nonfree_baggages",
        "insurance",
    )
    if (
        actual.get("status") == "cancelled"
        or actual["flights"] != spec["flights"]
        or any(actual[field] != original[field] for field in preserve)
    ):
        failures.append("return_segment_goal_not_completed")

    old_history = original["payment_history"]
    if actual["payment_history"][: len(old_history)] != old_history:
        failures.append("original_payment_history_changed")
        new_payments = []
    else:
        new_payments = actual["payment_history"][len(old_history) :]
    if (
        any(p["payment_id"] != spec["payment_id"] for p in new_payments)
        or _money(sum(p["amount"] for p in new_payments))
        != _money(spec["fare_difference"])
    ):
        failures.append("round_trip_payment_result_incorrect")

    expected_user = copy.deepcopy(before["users"][user_id])
    expected_user["payment_methods"][spec["payment_id"]]["amount"] = float(
        _money(expected_user["payment_methods"][spec["payment_id"]]["amount"])
        - _money(spec["fare_difference"])
    )
    if after["users"][user_id] != expected_user:
        failures.append("final_payment_or_profile_state_incorrect")
    if not _own_reservations_unchanged(before, after, user_id, {reservation_id}):
        failures.append("unrequested_reservation_changed")
    if _new_reservations(before, after, user_id):
        failures.append("unrequested_new_reservation_created")
    return failures
