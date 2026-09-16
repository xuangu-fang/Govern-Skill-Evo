"""Final-state evaluator for the cabin–baggage–budget composite."""

from typing import Any


def evaluate(
    spec: dict[str, Any], initial_db: dict[str, Any], final_db: dict[str, Any]
) -> dict[str, Any]:
    initial = initial_db["reservations"][spec["reservation_id"]]
    final = final_db["reservations"][spec["reservation_id"]]
    appended = final["payment_history"][len(initial["payment_history"]):]
    expected_payments = [
        {
            "payment_id": spec["payment_id"],
            "amount": spec["expected_flight_change"],
        },
        {
            "payment_id": spec["payment_id"],
            "amount": spec["expected_baggage_charge"],
        },
    ]
    expected_flights = [
        {"flight_number": spec["new_flight"], "date": spec["new_date"]}
    ]
    actual_flights = [
        {"flight_number": row["flight_number"], "date": row["date"]}
        for row in final["flights"]
    ]
    preserved = (
        final["origin"] == initial["origin"] == spec["origin"]
        and final["destination"] == initial["destination"] == spec["destination"]
        and final["insurance"] == initial["insurance"]
        and final["flight_type"] == initial["flight_type"]
        and set(final_db["reservations"]) == set(initial_db["reservations"])
        and final_db["users"][spec["user_id"]]["payment_methods"]
        == initial_db["users"][spec["user_id"]]["payment_methods"]
    )
    checks = {
        "cabin": final["cabin"] == spec["expected_cabin"],
        "flight": actual_flights == expected_flights,
        "passengers": final["passengers"] == spec["replacement_passengers"],
        "total_baggages": final["total_baggages"] == spec["requested_baggages"],
        "nonfree_baggages": final["nonfree_baggages"]
        == spec["expected_nonfree_baggages"],
        "payments": appended == expected_payments,
        "preserved": preserved,
    }
    return {
        "success": all(checks.values()),
        "checks": checks,
        "selected_cabin": final["cabin"],
        "appended_payments": appended,
        "total_appended_charge": sum(row["amount"] for row in appended),
    }

