"""Fresh entities for the one-seed Train/Monitor joint replication."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.data_model import FinalCandidateAirlineDB
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.fixture import build_gate0_db


HERE = Path(__file__).resolve().parent


def _flight(spec: dict[str, Any]) -> dict[str, Any]:
    price = spec["price"]
    return {
        "flight_number": spec["flight_number"],
        "origin": spec["origin"],
        "destination": spec["destination"],
        "scheduled_departure_time_est": "10:00:00",
        "scheduled_arrival_time_est": "12:00:00",
        "dates": {spec["date"]: {
            "status": "available",
            "available_seats": {"basic_economy": 12, "economy": 12, "business": 12},
            "prices": {"basic_economy": price, "economy": price, "business": price},
        }},
    }


def build_replication_db() -> FinalCandidateAirlineDB:
    payload = build_gate0_db().model_dump(mode="json")
    specs = json.loads((HERE / "specs.json").read_text(encoding="utf-8"))["candidates"]
    for spec in specs:
        passenger = spec["passenger"]
        user_id = spec["user_id"]
        card = spec["cancel_payment_id"]
        payload["users"][user_id] = {
            "user_id": user_id,
            "name": {"first_name": passenger["first_name"], "last_name": passenger["last_name"]},
            "address": {"address1": "41 Replication Way", "address2": None, "city": "Boston", "country": "USA", "state": "MA", "zip": "02108"},
            "email": f"{user_id}@example.test",
            "dob": passenger["dob"],
            "payment_methods": {
                spec["certificate_id"]: {"source": "certificate", "id": spec["certificate_id"], "amount": spec["certificate_amount"]},
                spec["gift_card_id"]: {"source": "gift_card", "id": spec["gift_card_id"], "amount": spec["gift_card_amount"]},
                card: {"source": "credit_card", "id": card, "brand": "visa", "last_four": card[-4:]},
            },
            "saved_passengers": [],
            "membership": "regular",
            "reservations": [spec["cancel_reservation_id"]],
        }
        for trip in spec["trips"]:
            payload["flights"][trip["flight_number"]] = _flight(trip)
        cancellation_flight = {
            "flight_number": spec["cancel_flight_number"], "origin": spec["cancel_origin"],
            "destination": spec["cancel_destination"], "date": spec["cancel_flight_date"],
            "price": spec["cancel_price"],
        }
        payload["flights"][spec["cancel_flight_number"]] = _flight(cancellation_flight)
        payload["reservations"][spec["cancel_reservation_id"]] = {
            "reservation_id": spec["cancel_reservation_id"], "user_id": user_id,
            "origin": spec["cancel_origin"], "destination": spec["cancel_destination"],
            "flight_type": "one_way", "cabin": "economy",
            "flights": [cancellation_flight], "passengers": [passenger],
            "payment_history": [{"payment_id": card, "amount": spec["cancel_price"]}],
            "created_at": "2024-05-01T10:00:00", "total_baggages": 0,
            "nonfree_baggages": 0, "insurance": "yes", "status": None,
        }
    return FinalCandidateAirlineDB.model_validate(payload)
