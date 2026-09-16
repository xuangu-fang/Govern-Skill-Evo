"""Fresh entities for the nine formally realized Protected Controls."""

from __future__ import annotations

from typing import Any

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.unified_environment.data_model import (
    UnifiedRetailDB,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.data_model import (
    FinalCandidateAirlineDB,
)


def address(street: str = "10 Control Lane", city: str = "Boston", state: str = "MA", zip_code: str = "02108") -> dict[str, str]:
    return {"address1": street, "address2": "", "city": city, "country": "USA", "state": state, "zip": zip_code}


def card(card_id: str) -> dict[str, Any]:
    return {"source": "credit_card", "id": card_id, "brand": "visa", "last_four": card_id[-4:]}


def airline_user(user_id: str, first: str, last: str, payments: dict[str, Any], reservations: list[str]) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "name": {"first_name": first, "last_name": last},
        "address": address(),
        "email": f"{user_id}@example.test",
        "dob": "1990-01-01",
        "payment_methods": payments,
        "saved_passengers": [],
        "membership": "regular",
        "reservations": reservations,
    }


def flight(number: str, origin: str, destination: str, date: str, departure: str, arrival: str, price: int, business_seats: int = 12) -> dict[str, Any]:
    return {
        "flight_number": number,
        "origin": origin,
        "destination": destination,
        "scheduled_departure_time_est": departure,
        "scheduled_arrival_time_est": arrival,
        "dates": {
            date: {
                "status": "available",
                "available_seats": {"basic_economy": 12, "economy": 12, "business": business_seats},
                "prices": {"basic_economy": price, "economy": price, "business": price + 100},
            }
        },
    }


def reservation(
    reservation_id: str,
    user_id: str,
    origin: str,
    destination: str,
    cabin: str,
    legs: list[tuple[str, str, str, str, int]],
    passengers: list[dict[str, str]],
    payment_id: str,
    *,
    flight_type: str = "one_way",
    total_baggages: int = 0,
    nonfree_baggages: int = 0,
    insurance: str = "no",
) -> dict[str, Any]:
    total = sum(item[4] for item in legs) * len(passengers)
    if insurance == "yes":
        total += 30 * len(passengers)
    return {
        "reservation_id": reservation_id,
        "user_id": user_id,
        "origin": origin,
        "destination": destination,
        "flight_type": flight_type,
        "cabin": cabin,
        "flights": [
            {"flight_number": number, "date": date, "origin": leg_origin, "destination": leg_destination, "price": price}
            for number, date, leg_origin, leg_destination, price in legs
        ],
        "passengers": passengers,
        "payment_history": [{"payment_id": payment_id, "amount": total}],
        "created_at": "2024-05-01T10:00:00",
        "total_baggages": total_baggages,
        "nonfree_baggages": nonfree_baggages,
        "insurance": insurance,
        "status": None,
    }


def add_airline_controls(db: FinalCandidateAirlineDB) -> FinalCandidateAirlineDB:
    payload = db.model_dump(mode="json")
    passengers3 = [
        {"first_name": "Ari", "last_name": f"Control{i}", "dob": f"199{i}-01-01"}
        for i in range(1, 4)
    ]
    solo = lambda first, last: [{"first_name": first, "last_name": last, "dob": "1990-01-01"}]

    new_flights = [
        # Keep the booked flight feasible but strictly slower than CTA114 so the
        # "shortest qualifying" control has one unambiguous answer.
        flight("CTA101", "EWR", "LAS", "2024-06-10", "08:00:00", "11:30:00", 100),
        flight("CTA102", "LAS", "EWR", "2024-06-20", "14:00:00", "22:00:00", 100),
        flight("CTA111", "EWR", "LAS", "2024-06-10", "07:00:00", "09:30:00", 120, 2),
        flight("CTA112", "EWR", "DEN", "2024-06-10", "07:00:00", "08:30:00", 80, 6),
        flight("CTA113", "DEN", "LAS", "2024-06-10", "09:15:00", "10:30:00", 80, 6),
        flight("CTA114", "EWR", "LAS", "2024-06-10", "09:00:00", "12:00:00", 170, 6),
        flight("CTA201", "BOS", "DTW", "2024-06-12", "08:00:00", "12:00:00", 100),
        flight("CTA202", "DTW", "SEA", "2024-06-12", "16:00:00", "20:00:00", 100),
        flight("CTA211", "BOS", "DTW", "2024-06-12", "05:30:00", "09:30:00", 130),
        flight("CTA212", "BOS", "DTW", "2024-06-12", "06:30:00", "10:30:00", 90),
        flight("CTA213", "BOS", "DTW", "2024-06-12", "04:30:00", "08:30:00", 150),
        flight("CTA301", "SFO", "SAN", "2024-06-14", "08:00:00", "09:30:00", 110),
        flight("CTA302", "PDX", "SLC", "2024-06-15", "09:00:00", "11:00:00", 100),
        flight("CTA303", "AUS", "MCI", "2024-06-16", "10:00:00", "12:00:00", 120),
        flight("CTA401", "DEN", "PHX", "2024-06-18", "11:00:00", "13:00:00", 120),
        flight("CTA501", "ATL", "MCO", "2024-06-22", "08:00:00", "09:30:00", 90),
        flight("CTA502", "SEA", "DFW", "2024-06-21", "07:00:00", "12:00:00", 100),
    ]
    payload["flights"].update({row["flight_number"]: row for row in new_flights})

    payload["users"].update({
        "ctrl_air_ari_1001": airline_user("ctrl_air_ari_1001", "Ari", "Morgan", {"credit_card_1001": card("credit_card_1001")}, ["CTA1001"]),
        "ctrl_air_bea_2002": airline_user("ctrl_air_bea_2002", "Bea", "Nolan", {"credit_card_2002": card("credit_card_2002")}, ["CTA2001", "CTA2002"]),
        "ctrl_air_cia_3003": airline_user("ctrl_air_cia_3003", "Cia", "Ortiz", {"credit_card_3003": card("credit_card_3003")}, ["CTA3001", "CTA3002", "CTA3003"]),
        "ctrl_air_dan_4004": airline_user("ctrl_air_dan_4004", "Dan", "Park", {"credit_card_4004": card("credit_card_4004")}, ["CTA4001"]),
        "ctrl_air_erin_5005": airline_user(
            "ctrl_air_erin_5005", "Erin", "Quill",
            {
                "certificate_5005": {"source": "certificate", "id": "certificate_5005", "amount": 500},
                "gift_card_5005": {"source": "gift_card", "id": "gift_card_5005", "amount": 120},
            },
            ["CTA5002"],
        ),
    })
    payload["users"]["ctrl_air_cia_3003"]["membership"] = "gold"

    payload["reservations"].update({
        "CTA1001": reservation("CTA1001", "ctrl_air_ari_1001", "EWR", "EWR", "business", [("CTA101", "2024-06-10", "EWR", "LAS", 200), ("CTA102", "2024-06-20", "LAS", "EWR", 200)], passengers3, "credit_card_1001", flight_type="round_trip"),
        "CTA2001": reservation("CTA2001", "ctrl_air_bea_2002", "BOS", "DTW", "economy", [("CTA201", "2024-06-12", "BOS", "DTW", 100)], solo("Bea", "Nolan"), "credit_card_2002"),
        "CTA2002": reservation("CTA2002", "ctrl_air_bea_2002", "DTW", "SEA", "economy", [("CTA202", "2024-06-12", "DTW", "SEA", 100)], solo("Bea", "Nolan"), "credit_card_2002"),
        "CTA3001": reservation("CTA3001", "ctrl_air_cia_3003", "SFO", "SAN", "economy", [("CTA301", "2024-06-14", "SFO", "SAN", 110)], solo("Cia", "Ortiz"), "credit_card_3003", insurance="yes"),
        "CTA3002": reservation("CTA3002", "ctrl_air_cia_3003", "PDX", "SLC", "economy", [("CTA302", "2024-06-15", "PDX", "SLC", 100)], solo("Cia", "Ortiz"), "credit_card_3003"),
        "CTA3003": reservation("CTA3003", "ctrl_air_cia_3003", "AUS", "MCI", "business", [("CTA303", "2024-06-16", "AUS", "MCI", 220)], solo("Cia", "Ortiz"), "credit_card_3003"),
        "CTA4001": reservation("CTA4001", "ctrl_air_dan_4004", "DEN", "PHX", "economy", [("CTA401", "2024-06-18", "DEN", "PHX", 120)], solo("Dan", "Park"), "credit_card_4004", insurance="yes"),
        "CTA5002": reservation("CTA5002", "ctrl_air_erin_5005", "SEA", "DFW", "economy", [("CTA502", "2024-06-21", "SEA", "DFW", 100)], solo("Erin", "Quill"), "gift_card_5005"),
    })
    for reservation_id in ("CTA1001", "CTA2001", "CTA2002", "CTA3001", "CTA3002", "CTA3003", "CTA4001", "CTA5002"):
        payload["settlement_contracts"][reservation_id] = {
            "ticketing_channel": "horizon",
            "remaining_changes": 3,
            "settlement_baseline": "retained_historical",
        }

    gap_date = "2024-08-10"
    gap_flights = [
        flight("XG101", "BOS", "ORD", gap_date, "07:00:00", "09:00:00", 150),
        flight("XG102", "ORD", "SFO", gap_date, "10:00:00", "13:00:00", 100),
        flight("XG103", "ORD", "SFO", gap_date, "11:00:00", "14:00:00", 130),
        flight("XG104", "ORD", "OAK", gap_date, "11:00:00", "14:00:00", 130),
        flight("XG105", "ORD", "SFO", gap_date, "12:00:00", "15:00:00", 60),
        flight("XG106", "ORD", "OAK", gap_date, "12:00:00", "15:00:00", 60),
    ]
    payload["flights"].update({row["flight_number"]: row for row in gap_flights})
    payload["users"]["gap_air_nora_8108"] = airline_user(
        "gap_air_nora_8108", "Nora", "Vale",
        {"credit_card_8108": card("credit_card_8108")}, ["GAPA8101"],
    )
    payload["reservations"]["GAPA8101"] = reservation(
        "GAPA8101", "gap_air_nora_8108", "BOS", "SFO", "economy",
        [
            ("XG101", gap_date, "BOS", "ORD", 100),
            ("XG102", gap_date, "ORD", "SFO", 100),
        ],
        [{"first_name": "Nora", "last_name": "Vale", "dob": "1990-01-01"}],
        "credit_card_8108",
    )
    payload["settlement_contracts"]["GAPA8101"] = {
        "ticketing_channel": "horizon",
        "remaining_changes": 1,
        "settlement_baseline": "retained_historical",
    }
    return FinalCandidateAirlineDB.model_validate(payload)


def retail_user(user_id: str, first: str, last: str, email: str, card_id: str, order_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "name": {"first_name": first, "last_name": last},
        "address": address(),
        "email": email,
        "payment_methods": {card_id: card(card_id)},
        "orders": [order_id],
    }


def add_retail_controls(db: UnifiedRetailDB) -> UnifiedRetailDB:
    payload = db.model_dump(mode="json")
    payload["products"]["CTR-P01"] = {
        "name": "Action Camera",
        "product_id": "CTR-P01",
        "variants": {
            "CTR-I011": {"item_id": "CTR-I011", "options": {"resolution": "HD", "waterproof": "no", "color": "black"}, "available": True, "price": 90.0},
            "CTR-I012": {"item_id": "CTR-I012", "options": {"resolution": "HD", "waterproof": "no", "color": "silver"}, "available": True, "price": 90.0},
            "CTR-I019": {"item_id": "CTR-I019", "options": {"resolution": "4K", "waterproof": "yes", "color": "black"}, "available": True, "price": 120.0},
        },
    }
    payload["products"]["CTR-P02"] = {
        "name": "Desk Organizer",
        "product_id": "CTR-P02",
        "variants": {
            "CTR-I021": {"item_id": "CTR-I021", "options": {"color": "navy", "size": "standard"}, "available": True, "price": 40.0}
        },
    }
    payload["users"].update({
        "ctrl_ret_faye_6006": retail_user("ctrl_ret_faye_6006", "Faye", "Reed", "faye.reed@example.test", "credit_card_6006", "#CTR6001"),
        "ctrl_ret_gio_7007": retail_user("ctrl_ret_gio_7007", "Gio", "Stone", "gio.stone@example.test", "credit_card_7007", "#CTR7001"),
    })
    payload["orders"].update({
        "#CTR6001": {
            "order_id": "#CTR6001", "user_id": "ctrl_ret_faye_6006", "address": address(),
            "items": [
                {"name": "Action Camera", "product_id": "CTR-P01", "item_id": "CTR-I011", "price": 90.0, "options": {"resolution": "HD", "waterproof": "no", "color": "black"}},
                {"name": "Action Camera", "product_id": "CTR-P01", "item_id": "CTR-I012", "price": 90.0, "options": {"resolution": "HD", "waterproof": "no", "color": "silver"}},
            ],
            "status": "pending", "fulfillments": [],
            "payment_history": [{"transaction_type": "payment", "amount": 180.0, "payment_method_id": "credit_card_6006"}],
        },
        "#CTR7001": {
            "order_id": "#CTR7001", "user_id": "ctrl_ret_gio_7007", "address": address(),
            "items": [{"name": "Desk Organizer", "product_id": "CTR-P02", "item_id": "CTR-I021", "price": 40.0, "options": {"color": "navy", "size": "standard"}}],
            "status": "pending", "fulfillments": [],
            "payment_history": [{"transaction_type": "payment", "amount": 40.0, "payment_method_id": "credit_card_7007"}],
        },
    })
    payload["resolution_contracts"].update({
        order_id: {"fulfillment_mode": "consolidated", "exchange_protection_behavior": "preserve", "purchase_protection_status": "active", "last_resolution": None}
        for order_id in ("#CTR6001", "#CTR7001")
    })
    payload["address_propagation_contracts"].update({
        "#CTR6001": {"address_contract": "cedar", "propagation_source": "profile", "written_targets": [], "session_closed": False},
        "#CTR7001": {"address_contract": "cedar", "propagation_source": "profile", "written_targets": [], "session_closed": False},
    })

    payload["products"]["GAPR-P01"] = {
        "name": "Travel Flask",
        "product_id": "GAPR-P01",
        "variants": {
            "GAPR-I011": {"item_id": "GAPR-I011", "options": {"color": "navy", "size": "750ml"}, "available": True, "price": 45.0},
            "GAPR-I012": {"item_id": "GAPR-I012", "options": {"color": "silver", "size": "750ml"}, "available": True, "price": 45.0},
        },
    }
    payload["users"]["gap_ret_omar_8208"] = retail_user(
        "gap_ret_omar_8208", "Omar", "Ives", "omar.ives@example.test",
        "credit_card_8208", "#GAPR8201",
    )
    payload["orders"]["#GAPR8201"] = {
        "order_id": "#GAPR8201", "user_id": "gap_ret_omar_8208",
        "address": address("8 Harbor Road", "Portland", "ME", "04101"),
        "items": [{
            "name": "Travel Flask", "product_id": "GAPR-P01", "item_id": "GAPR-I011",
            "price": 45.0, "options": {"color": "navy", "size": "750ml"},
        }],
        "status": "delivered",
        "fulfillments": [{"tracking_id": ["TRACK-GAPR-8201"], "item_ids": ["GAPR-I011"]}],
        "payment_history": [{"transaction_type": "payment", "amount": 45.0, "payment_method_id": "credit_card_8208"}],
    }
    payload["resolution_contracts"]["#GAPR8201"] = {
        "fulfillment_mode": "consolidated", "exchange_protection_behavior": "preserve",
        "purchase_protection_status": "active", "last_resolution": None,
    }
    payload["address_propagation_contracts"]["#GAPR8201"] = {
        "address_contract": "cedar", "propagation_source": "profile",
        "written_targets": [], "session_closed": False,
    }
    return UnifiedRetailDB.model_validate(payload)
