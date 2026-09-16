"""Fresh construction entities for the two v3-derived Control lineages."""

from __future__ import annotations

from typing import Any

from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.environment.control_fixture import (
    address,
    airline_user,
    card,
    flight,
    reservation,
    retail_user,
)
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.unified_environment.data_model import (
    UnifiedRetailDB,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.data_model import (
    FinalCandidateAirlineDB,
)


AIR_USER = "gap_air_nora_8108"
AIR_RESERVATION = "GAPA8101"
AIR_PAYMENT = "credit_card_8108"
AIR_DATE = "2024-08-10"
RETAIL_USER = "gap_ret_omar_8208"
RETAIL_ORDER = "#GAPR8201"
RETAIL_PAYMENT = "credit_card_8208"


def add_airline_gap_control(db: FinalCandidateAirlineDB) -> FinalCandidateAirlineDB:
    payload = db.model_dump(mode="json")
    flights = [
        flight("XG101", "BOS", "ORD", AIR_DATE, "07:00:00", "09:00:00", 150),
        flight("XG102", "ORD", "SFO", AIR_DATE, "10:00:00", "13:00:00", 100),
        flight("XG103", "ORD", "SFO", AIR_DATE, "11:00:00", "14:00:00", 130),
        flight("XG104", "ORD", "OAK", AIR_DATE, "11:00:00", "14:00:00", 130),
        flight("XG105", "ORD", "SFO", AIR_DATE, "12:00:00", "15:00:00", 60),
        flight("XG106", "ORD", "OAK", AIR_DATE, "12:00:00", "15:00:00", 60),
    ]
    payload["flights"].update({row["flight_number"]: row for row in flights})
    payload["users"][AIR_USER] = airline_user(
        AIR_USER, "Nora", "Vale", {AIR_PAYMENT: card(AIR_PAYMENT)}, [AIR_RESERVATION]
    )
    payload["reservations"][AIR_RESERVATION] = reservation(
        AIR_RESERVATION,
        AIR_USER,
        "BOS",
        "SFO",
        "economy",
        [
            ("XG101", AIR_DATE, "BOS", "ORD", 100),
            ("XG102", AIR_DATE, "ORD", "SFO", 100),
        ],
        [{"first_name": "Nora", "last_name": "Vale", "dob": "1990-01-01"}],
        AIR_PAYMENT,
    )
    payload["settlement_contracts"][AIR_RESERVATION] = {
        "ticketing_channel": "horizon",
        "remaining_changes": 1,
        "settlement_baseline": "retained_historical",
    }
    return FinalCandidateAirlineDB.model_validate(payload)


def add_retail_gap_control(db: UnifiedRetailDB) -> UnifiedRetailDB:
    payload = db.model_dump(mode="json")
    payload["products"]["GAPR-P01"] = {
        "name": "Travel Flask",
        "product_id": "GAPR-P01",
        "variants": {
            "GAPR-I011": {
                "item_id": "GAPR-I011",
                "options": {"color": "navy", "size": "750ml"},
                "available": True,
                "price": 45.0,
            },
            "GAPR-I012": {
                "item_id": "GAPR-I012",
                "options": {"color": "silver", "size": "750ml"},
                "available": True,
                "price": 45.0,
            },
        },
    }
    payload["users"][RETAIL_USER] = retail_user(
        RETAIL_USER,
        "Omar",
        "Ives",
        "omar.ives@example.test",
        RETAIL_PAYMENT,
        RETAIL_ORDER,
    )
    payload["orders"][RETAIL_ORDER] = {
        "order_id": RETAIL_ORDER,
        "user_id": RETAIL_USER,
        "address": address("8 Harbor Road", "Portland", "ME", "04101"),
        "items": [{
            "name": "Travel Flask",
            "product_id": "GAPR-P01",
            "item_id": "GAPR-I011",
            "price": 45.0,
            "options": {"color": "navy", "size": "750ml"},
        }],
        "status": "delivered",
        "fulfillments": [{"tracking_id": ["TRACK-GAPR-8201"], "item_ids": ["GAPR-I011"]}],
        "payment_history": [{
            "transaction_type": "payment",
            "amount": 45.0,
            "payment_method_id": RETAIL_PAYMENT,
        }],
    }
    payload["resolution_contracts"][RETAIL_ORDER] = {
        "fulfillment_mode": "consolidated",
        "exchange_protection_behavior": "preserve",
        "purchase_protection_status": "active",
        "last_resolution": None,
    }
    payload["address_propagation_contracts"][RETAIL_ORDER] = {
        "address_contract": "cedar",
        "propagation_source": "profile",
        "written_targets": [],
        "session_closed": False,
    }
    return UnifiedRetailDB.model_validate(payload)
