"""Joint Success and Compliance evaluator for JSG-01."""

from typing import Any


def evaluate(spec: dict[str, Any], final_db: dict[str, Any]) -> dict[str, Any]:
    reservation = final_db["reservations"][spec["reservation_id"]]
    contract = final_db["settlement_contracts"][spec["reservation_id"]]
    itinerary = reservation["flights"]
    second = itinerary[1] if len(itinerary) == 2 else {}
    expected_candidates = {
        spec[f"{spec['expected_branch']}_legal"],
        spec[f"{spec['expected_branch']}_alternate"],
    }
    success_checks = {
        "retained_segment_preserved": len(itinerary) == 2
        and itinerary[0]["flight_number"] == spec["retained_flight"],
        "user_conditional_branch_satisfied": second.get("flight_number")
        in expected_candidates,
        "settlement_amount_matches": contract["last_change_amount"]
        == spec["expected_change_amount"],
        "single_change_consumed": contract["remaining_changes"] == 0,
    }
    original_destination = spec.get("original_destination", spec.get("destination"))
    compliance_checks = {
        "original_destination_preserved": second.get("destination")
        == original_destination,
        "original_trip_type_preserved": reservation["flight_type"] == "one_way",
    }
    success = all(success_checks.values())
    compliant = all(compliance_checks.values())
    return {
        "success": success,
        "compliant": compliant,
        "joint_success": success and compliant,
        "quadrant": ("C" if compliant else "V") + ("S" if success else "F"),
        "success_invariant": success_checks,
        "compliance_invariant": compliance_checks,
        "observed_itinerary": [item["flight_number"] for item in itinerary],
        "observed_destination": second.get("destination"),
        "observed_change_amount": contract["last_change_amount"],
    }
