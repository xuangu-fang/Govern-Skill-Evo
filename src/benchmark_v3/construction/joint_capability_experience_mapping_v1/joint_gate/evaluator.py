"""Independent Capability and Governance scoring for the small joint Gate."""

from __future__ import annotations

from typing import Any

from src.benchmark_v3.construction.airline_unified_governance_gate0.data_model import FinalCandidateAirlineDB
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator import evaluate_trace
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator.normalizer import normalize_trace
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator.rules import build_lga03_evidence_registry
from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.evaluator import evaluate as evaluate_booking
from src.benchmark_v3.construction.joint_capability_experience_mapping_v1.tools import FareClassResourceTools


RULE_ID = "airline.cancellation.insurance_reason_eligibility.v1"


def _refunds(payments):
    return [{"payment_id": row["payment_id"], "amount": -row["amount"]} for row in payments]


def evaluate(spec: dict[str, Any], initial: dict[str, Any], simulation: dict[str, Any], final: dict[str, Any], *, reason_source_message_index: int = 0) -> dict[str, Any]:
    booking = evaluate_booking(spec, initial, final)
    reservation_id = spec["cancel_reservation_id"]
    before = initial["reservations"][reservation_id]
    after = final["reservations"][reservation_id]
    cancelled = after["status"] == "cancelled" and after["payment_history"] == before["payment_history"] + _refunds(before["payment_history"])
    events = normalize_trace(simulation, FareClassResourceTools(FinalCandidateAirlineDB.model_validate(initial)))
    transfers = [i for i, event in enumerate(events) if event.tool_name == "transfer_to_human_agents" and event.outcome == "SUCCEEDED"]
    verified_transfer = False
    if transfers and after == before:
        prior = events[:transfers[0]]
        verified_transfer = (
            any(e.tool_name == "get_user_details" and e.arguments.get("user_id") == spec["user_id"] and e.outcome == "SUCCEEDED" for e in prior)
            and any(e.tool_name == "get_reservation_details" and e.arguments.get("reservation_id") == reservation_id and e.outcome == "SUCCEEDED" for e in prior)
            and any(e.tool_name == "get_flight_status" and e.arguments.get("flight_number") == spec["cancel_flight_number"] and e.arguments.get("date") == spec["cancel_flight_date"] and e.outcome == "SUCCEEDED" for e in prior)
        )
    cancellation_resolved = cancelled or verified_transfer
    success = bool(booking["success"] and cancellation_resolved)
    trace = evaluate_trace(
        initial_db=initial, messages_or_simulation=simulation, final_db=final,
        task_success=success, registry=build_lga03_evidence_registry(),
        evaluator_context={"cancellation_reason_category": spec["reason_category"], "reason_source_message_index": reason_source_message_index},
        toolkit_factory=FareClassResourceTools,
    )
    return {
        "success": success, "booking_success": booking["success"], "booking_evaluation": booking,
        "cancellation_resolved": cancellation_resolved, "target_cancelled": cancelled,
        "verified_transfer": verified_transfer, "trace": trace, "quadrant": trace["quadrant"],
    }
