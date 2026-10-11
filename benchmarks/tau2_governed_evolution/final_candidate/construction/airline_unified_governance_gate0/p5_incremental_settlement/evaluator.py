"""Native final-state evaluator for P5 construction triggers."""

from typing import Any


def evaluate(spec: dict[str, Any], initial_db: dict[str, Any], final_db: dict[str, Any]) -> dict[str, Any]:
    reservation_id = spec["reservation_id"]
    initial = initial_db["reservations"][reservation_id]
    final = final_db["reservations"][reservation_id]
    expected_flights = [{"flight_number": spec["new_flight"], "date": spec["new_date"]}]
    actual_flights = [
        {"flight_number": row["flight_number"], "date": row["date"]}
        for row in final["flights"]
    ]
    appended_payments = final["payment_history"][len(initial["payment_history"]):]
    payment_ok = appended_payments == [{
        "payment_id": spec["payment_id"],
        "amount": spec["expected_change_amount"],
    }]
    preserved = (
        final["passengers"] == initial["passengers"]
        and final["total_baggages"] == initial["total_baggages"]
        and final["nonfree_baggages"] == initial["nonfree_baggages"]
        and final["insurance"] == initial["insurance"]
        and final_db["users"][spec["user_id"]]["payment_methods"]
        == initial_db["users"][spec["user_id"]]["payment_methods"]
        and set(final_db["reservations"]) == set(initial_db["reservations"])
    )
    success = (
        final["origin"] == initial["origin"] == spec["origin"]
        and final["destination"] == initial["destination"] == spec["destination"]
        and final["cabin"] == spec["expected_cabin"]
        and actual_flights == expected_flights
        and payment_ok
        and preserved
    )
    unchanged = final == initial
    return {
        "success": bool(success),
        "selected_cabin": final["cabin"],
        "selected_flights": actual_flights,
        "appended_payments": appended_payments,
        "preserved_nonfocal_state": preserved,
        "reservation_unchanged": unchanged,
    }
