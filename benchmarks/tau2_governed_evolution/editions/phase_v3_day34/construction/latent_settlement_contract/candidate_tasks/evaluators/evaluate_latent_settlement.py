"""Final-state evaluator for EE-01 Gate 0 candidates."""

from typing import Any


def evaluate_success(spec: dict[str, Any], final_db: dict[str, Any]) -> dict[str, Any]:
    reservation_id = spec["reservation_id"]
    reservation = final_db["reservations"][reservation_id]
    contract = final_db["settlement_contracts"][reservation_id]
    observed_itinerary = [item["flight_number"] for item in reservation["flights"]]
    expected_itinerary = [spec["retained_flight"], spec["expected_flight"]]
    checks = {
        "complete_itinerary_matches_user_condition": observed_itinerary == expected_itinerary,
        "settlement_amount_matches": contract["last_change_amount"] == spec["expected_change_amount"],
        "change_budget_consumed": contract["remaining_changes"] == 0,
        "reservation_not_cancelled": reservation.get("status") != "cancelled",
    }
    return {
        "success": all(checks.values()),
        "semantic_invariant": checks,
        "expected_itinerary": expected_itinerary,
        "observed_itinerary": observed_itinerary,
        "observed_change_amount": contract["last_change_amount"],
    }
