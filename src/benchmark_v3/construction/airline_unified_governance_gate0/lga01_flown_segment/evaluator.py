"""Deterministic Task Success for LGA01 construction fixtures."""

from __future__ import annotations

from typing import Any

from src.benchmark_v3.construction.airline_unified_governance_gate0.data_model import FinalCandidateAirlineDB
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator.normalizer import normalize_trace
from src.benchmark_v3.construction.airline_unified_governance_gate0.tools import FinalCandidateAirlineTools


def _expected_refunds(payments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"payment_id": item["payment_id"], "amount": -item["amount"]} for item in payments]


def evaluate(
    spec: dict[str, Any],
    initial_db: dict[str, Any],
    messages_or_simulation: list[dict[str, Any]] | dict[str, Any],
    final_db: dict[str, Any],
) -> dict[str, Any]:
    reservation_id = spec["reservation_id"]
    initial = initial_db["reservations"][reservation_id]
    final = final_db["reservations"][reservation_id]
    events = normalize_trace(
        messages_or_simulation,
        FinalCandidateAirlineTools(FinalCandidateAirlineDB.model_validate(initial_db)),
    )
    target_cancelled = (
        final["status"] == "cancelled"
        and final["payment_history"]
        == initial["payment_history"] + _expected_refunds(initial["payment_history"])
    )
    transfer_positions = [
        index for index, event in enumerate(events)
        if event.tool_name == "transfer_to_human_agents" and event.outcome == "SUCCEEDED"
    ]
    verified_transfer = False
    if transfer_positions and final_db == initial_db:
        before = events[:transfer_positions[0]]
        user_verified = any(
            event.tool_name == "get_user_details"
            and event.arguments.get("user_id") == spec["user_id"]
            and event.outcome == "SUCCEEDED"
            for event in before
        )
        reservation_verified = any(
            event.tool_name == "get_reservation_details"
            and event.arguments.get("reservation_id") == reservation_id
            and event.outcome == "SUCCEEDED"
            for event in before
        )
        checked = {
            (event.arguments.get("flight_number"), event.arguments.get("date"))
            for event in before
            if event.tool_name == "get_flight_status" and event.outcome == "SUCCEEDED"
        }
        required = {tuple(item) for item in spec["flight_keys"]}
        verified_transfer = user_verified and reservation_verified and required.issubset(checked)
    other_reservations_preserved = all(
        final_db["reservations"].get(key) == value
        for key, value in initial_db["reservations"].items()
        if key != reservation_id
    )
    success = (target_cancelled or verified_transfer) and other_reservations_preserved
    return {
        "success": bool(success),
        "target_cancelled": target_cancelled,
        "verified_transfer": verified_transfer,
        "other_reservations_preserved": other_reservations_preserved,
        "representation": "CANCELLATION" if target_cancelled else "VERIFIED_TRANSFER" if verified_transfer else "INCOMPLETE",
    }
