#!/usr/bin/env python3
"""Semantic final-state evaluation and offline failure attribution."""

from __future__ import annotations

from collections import Counter
from typing import Any


FAILURE_MODES = (
    "EARLY_CERTIFICATE_CONSUMPTION",
    "LOCAL_PAYMENT_OPTIMIZATION",
    "RESOURCE_FEASIBILITY_MISPLANNING",
    "UNNECESSARY_CERTIFICATE_AVOIDANCE",
    "PAYMENT_BINDING_ERROR",
    "UNRELATED_FAILURE",
)


def _matches(reservation: dict[str, Any], transaction: dict[str, Any], user: dict[str, Any]) -> bool:
    expected_passenger = {
        "first_name": user["name"]["first_name"],
        "last_name": user["name"]["last_name"],
        "dob": user["dob"],
    }
    flights = reservation.get("flights", [])
    payments = reservation.get("payment_history", [])
    return (
        reservation.get("status") != "cancelled"
        and reservation.get("origin") == transaction["origin"]
        and reservation.get("destination") == transaction["destination"]
        and reservation.get("flight_type") == "one_way"
        and reservation.get("cabin") == transaction["cabin"]
        and flights == [{
            "flight_number": transaction["flight_number"],
            "origin": transaction["origin"],
            "destination": transaction["destination"],
            "date": transaction["date"],
            "price": transaction["price"],
        }]
        and reservation.get("passengers") == [expected_passenger]
        and len(payments) == 1
        and payments[0].get("amount") == transaction["price"]
        and reservation.get("total_baggages") == 0
        and reservation.get("nonfree_baggages") == 0
        and reservation.get("insurance") == "no"
    )


def evaluate_success(spec: dict[str, Any], initial: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    user_id = spec["user_id"]
    initial_ids = set(initial["users"][user_id]["reservations"])
    final_ids = set(final["users"][user_id]["reservations"])
    new_ids = final_ids - initial_ids
    new_reservations = [final["reservations"][reservation_id] for reservation_id in sorted(new_ids)]
    required_matches = []
    for transaction in spec["transactions"]:
        matches = [r["reservation_id"] for r in new_reservations if _matches(r, transaction, initial["users"][user_id])]
        required_matches.append(matches)
    complete = all(len(matches) == 1 for matches in required_matches)
    no_extra_booking = len(new_reservations) == len(spec["transactions"])
    initial_other = {uid: value for uid, value in initial["users"].items() if uid != user_id}
    final_other = {uid: value for uid, value in final["users"].items() if uid != user_id}
    other_users_unchanged = initial_other == final_other
    return {
        "success": complete and no_extra_booking and other_users_unchanged,
        "required_matches": required_matches,
        "new_reservation_ids": sorted(new_ids),
        "complete_required_goals": complete,
        "no_extra_booking": no_extra_booking,
        "other_users_unchanged": other_users_unchanged,
    }


def _book_calls(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    calls = []
    for message in simulation.get("messages", []):
        if message.get("role") != "assistant":
            continue
        for call in message.get("tool_calls") or []:
            if call.get("name") == "book_reservation":
                calls.append(call.get("arguments") or {})
    return calls


def attribute_failure(
    spec: dict[str, Any], initial: dict[str, Any], final: dict[str, Any], simulation: dict[str, Any]
) -> dict[str, Any]:
    evaluation = evaluate_success(spec, initial, final)
    calls = _book_calls(simulation)
    cert_id = spec["certificate"]["payment_id"]
    created = [final["reservations"][rid] for rid in evaluation["new_reservation_ids"]]
    active_completed = [r for r in created if r.get("status") != "cancelled"]
    cert_funded = [
        r for r in created
        if any(payment.get("payment_id") == cert_id for payment in r.get("payment_history", []))
    ]
    if spec["role"] in {"CAPABILITY_CORE", "HELD_OUT_TRANSFER"} and cert_funded:
        return {
            "mode": "EARLY_CERTIFICATE_CONSUMPTION",
            "evidence": "certificate funded an early booking and was irreversibly consumed; cancellation did not restore it",
            "active_completed_bookings": len(active_completed),
            "book_calls": len(calls),
        }
    if spec["role"] == "PROTECTED_CONTROL" and not evaluation["complete_required_goals"]:
        cert_attempted = any(
            any(payment.get("payment_id") == cert_id for payment in call.get("payment_methods", []))
            for call in calls
        )
        if not cert_attempted:
            return {
                "mode": "UNNECESSARY_CERTIFICATE_AVOIDANCE",
                "evidence": "control goal was left incomplete without attempting the available certificate",
                "book_calls": len(calls),
            }
    if calls:
        known_ids = set(initial["users"][spec["user_id"]]["payment_methods"])
        supplied_ids = [
            payment.get("payment_id")
            for call in calls
            for payment in call.get("payment_methods", [])
        ]
        if any(payment_id not in known_ids for payment_id in supplied_ids):
            return {"mode": "PAYMENT_BINDING_ERROR", "evidence": "booking call used an unknown payment identifier"}
        return {
            "mode": "RESOURCE_FEASIBILITY_MISPLANNING",
            "evidence": "booking calls were made but the complete resource-feasible goal set was not reached",
            "book_calls": len(calls),
        }
    if active_completed:
        return {
            "mode": "LOCAL_PAYMENT_OPTIMIZATION",
            "evidence": "only a strict subset of required transactions completed",
            "completed_bookings": len(active_completed),
        }
    return {"mode": "UNRELATED_FAILURE", "evidence": "no diagnostic payment allocation pattern observed"}


def summarize_failures(rows: list[dict[str, Any]], role: str = "CAPABILITY_CORE") -> dict[str, Any]:
    failures = [row for row in rows if row["condition"] == "E0" and row["role"] == role and not row["success"]]
    counts = Counter(row["failure_attribution"]["mode"] for row in failures)
    for mode in FAILURE_MODES:
        counts.setdefault(mode, 0)
    dominant_mode, dominant_count = counts.most_common(1)[0] if failures else (None, 0)
    return {
        "role": role,
        "empty_total_failures": len(failures),
        "counts": dict(counts),
        "dominant_failure_mode": dominant_mode,
        "dominant_failure_count": dominant_count,
        "dominant_failure_fraction": dominant_count / len(failures) if failures else None,
    }
