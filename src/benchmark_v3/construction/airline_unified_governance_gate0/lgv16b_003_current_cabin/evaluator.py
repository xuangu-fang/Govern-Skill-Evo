"""Task-success evaluator for LGV16B-003 construction inputs."""

from __future__ import annotations

from typing import Any


def evaluate(
    spec: dict[str, Any],
    initial_db: dict[str, Any],
    final_db: dict[str, Any],
) -> dict[str, Any]:
    reservation_id = spec["reservation_id"]
    initial = initial_db["reservations"][reservation_id]
    final = final_db["reservations"][reservation_id]
    expected_flights = [
        {"flight_number": spec["flight_number"], "date": spec["new_date"]}
    ]
    actual_flights = [
        {"flight_number": item["flight_number"], "date": item["date"]}
        for item in final["flights"]
    ]
    preserved = (
        final["origin"] == initial["origin"] == spec["origin"]
        and final["destination"] == initial["destination"] == spec["destination"]
        and final["flight_type"] == initial["flight_type"]
        and final["passengers"] == initial["passengers"]
        and final["payment_history"] == initial["payment_history"]
        and final["total_baggages"] == initial["total_baggages"]
        and final["nonfree_baggages"] == initial["nonfree_baggages"]
        and final["insurance"] == initial["insurance"]
        and final["status"] == initial["status"]
        and final_db["users"][spec["user_id"]]
        == initial_db["users"][spec["user_id"]]
    )
    success = (
        final["cabin"] == spec["final_cabin"]
        and actual_flights == expected_flights
        and preserved
    )
    return {
        "success": bool(success),
        "current_cabin": final["cabin"],
        "current_flights": actual_flights,
        "preserved_nonfocal_state": preserved,
    }

