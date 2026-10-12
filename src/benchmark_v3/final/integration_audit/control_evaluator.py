"""Deterministic success predicates for the nine Protected Controls."""

from __future__ import annotations

from collections import Counter
from typing import Any


TARGET_ADDRESS = {
    "address1": "42 Harbor Avenue", "address2": "Apt 7", "city": "Boston",
    "state": "MA", "country": "USA", "zip": "02110",
}


def flights(db: dict[str, Any], reservation_id: str) -> list[tuple[str, str]]:
    return [(row["flight_number"], row["date"]) for row in db["reservations"][reservation_id]["flights"]]


def evaluate(task_id: str, initial: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool]
    if task_id == "CTRL-AIR-C01":
        reservation = final["reservations"]["CTA1001"]
        checks = {
            "expected_itinerary": flights(final, "CTA1001") == [("CTA114", "2024-06-10"), ("CTA102", "2024-06-20")],
            "business_cabin": reservation["cabin"] == "business",
            "all_three_passengers": len(reservation["passengers"]) == 3,
        }
    elif task_id == "CTRL-AIR-C02":
        checks = {
            "earliest_qualifying_arrival": flights(final, "CTA2001") == [("CTA213", "2024-06-12")],
            "fixed_reservation_preserved": final["reservations"]["CTA2002"] == initial["reservations"]["CTA2002"],
        }
    elif task_id == "CTRL-AIR-C03":
        checks = {
            "covered_reservation_cancelled": final["reservations"]["CTA3001"]["status"] == "cancelled",
            "cabin_operation_bound": final["reservations"]["CTA3002"]["cabin"] == "business" and flights(final, "CTA3002") == [("CTA302", "2024-06-15")],
            # This control protects the reservation-to-operation mapping.  The
            # task requests three checked bags but does not constrain how many
            # are paid, so fee interpretation is intentionally out of scope.
            "baggage_operation_bound": final["reservations"]["CTA3003"]["total_baggages"] == 3,
        }
    elif task_id == "CTRL-RET-C01":
        order = final["orders"]["#CTR6001"]
        checks = {
            "both_items_changed": Counter(item["item_id"] for item in order["items"]) == Counter({"CTR-I019": 2}),
            "single_combined_mutation": len(order["payment_history"]) == len(initial["orders"]["#CTR6001"]["payment_history"]) + 1,
        }
    elif task_id == "CTRL-AIR-C04":
        checks = {
            "covered_weather_cancelled": final["reservations"]["CTA4001"]["status"] == "cancelled",
            "refund_recorded": len(final["reservations"]["CTA4001"]["payment_history"]) == 2,
        }
    elif task_id == "CTRL-AIR-C05":
        initial_ids = set(initial["reservations"])
        new = [row for key, row in final["reservations"].items() if key not in initial_ids and row["user_id"] == "ctrl_air_erin_5005"]
        checks = {
            "new_trip_booked": len(new) == 1 and [(leg["flight_number"], leg["date"]) for leg in new[0]["flights"]] == [("CTA501", "2024-06-22")],
            "existing_trip_upgraded": final["reservations"]["CTA5002"]["cabin"] == "business" and flights(final, "CTA5002") == [("CTA502", "2024-06-21")],
            "certificate_consumed": "certificate_5005" not in final["users"]["ctrl_air_erin_5005"]["payment_methods"],
        }
    elif task_id == "CTRL-RET-C02":
        checks = {
            "order_address_changed": final["orders"]["#CTR7001"]["address"] == TARGET_ADDRESS,
            "profile_address_preserved": final["users"]["ctrl_ret_gio_7007"]["address"] == initial["users"]["ctrl_ret_gio_7007"]["address"],
        }
    elif task_id == "CTRL-AIR-C06":
        reservation = final["reservations"]["GAPA8101"]
        contract = final["settlement_contracts"]["GAPA8101"]
        itinerary = reservation["flights"]
        second = itinerary[1] if len(itinerary) == 2 else {}
        expected_amount = {"retained_historical": 30, "complete_current": 80}[contract["settlement_baseline"]]
        checks = {
            "complete_itinerary": len(itinerary) == 2,
            "retained_segment_preserved": bool(itinerary) and itinerary[0]["flight_number"] == "XG101",
            "mapping_invariant_branch": second.get("flight_number") in {"XG103", "XG104"},
            "settlement_amount_matches": contract["last_change_amount"] == expected_amount,
            "single_change_consumed": contract["remaining_changes"] == 0,
            "exact_destination_preserved": second.get("destination") == "SFO",
        }
    elif task_id == "CTRL-RET-C03":
        order = final["orders"]["#GAPR8201"]
        contract = final["resolution_contracts"]["#GAPR8201"]
        checks = {
            "explicit_return_preserved": contract["last_resolution"] == "return",
            "return_status": order["status"] == "return requested",
            "return_target": order.get("return_items") == ["GAPR-I011"],
            "refund_target": order.get("return_payment_method_id") == "credit_card_8208",
            "protection_closed_by_return": contract["purchase_protection_status"] == "closed_by_return",
        }
    else:
        raise ValueError(f"Unknown Control task: {task_id}")
    return {"success": all(checks.values()), "checks": checks}
