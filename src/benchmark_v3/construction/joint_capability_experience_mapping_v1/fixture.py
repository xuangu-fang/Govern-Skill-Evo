"""Fresh entities for the experience-critical Capability calibration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.benchmark_v3.construction.airline_unified_governance_gate0.data_model import FinalCandidateAirlineDB
from src.benchmark_v3.construction.airline_unified_governance_gate0.fixture import build_gate0_db


HERE = (Path(__file__).resolve().parents[4] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/joint_capability_experience_mapping_v1')


def _flight(spec: dict[str, Any]) -> dict[str, Any]:
    prices = {"basic_economy": spec["price"], "economy": spec["price"], "business": spec["price"]}
    return {
        "flight_number": spec["flight_number"],
        "origin": spec["origin"],
        "destination": spec["destination"],
        "scheduled_departure_time_est": "10:00:00",
        "scheduled_arrival_time_est": "12:00:00",
        "dates": {spec["date"]: {
            "status": "available",
            "available_seats": {"basic_economy": 12, "economy": 12, "business": 12},
            "prices": prices,
        }},
    }


def build_db() -> FinalCandidateAirlineDB:
    payload = build_gate0_db().model_dump(mode="json")
    specs = json.loads((HERE / "specs.json").read_text(encoding="utf-8"))["candidates"]
    for spec in specs:
        passenger = spec["passenger"]
        user_id = spec["user_id"]
        payload["users"][user_id] = {
            "user_id": user_id,
            "name": {"first_name": passenger["first_name"], "last_name": passenger["last_name"]},
            "address": {"address1": "17 Calibration Lane", "address2": None, "city": "Boston", "country": "USA", "state": "MA", "zip": "02108"},
            "email": f"{user_id}@example.test",
            "dob": passenger["dob"],
            "payment_methods": {
                spec["certificate_id"]: {"source": "certificate", "id": spec["certificate_id"], "amount": spec["certificate_amount"]},
                spec["gift_card_id"]: {"source": "gift_card", "id": spec["gift_card_id"], "amount": spec["gift_card_amount"]},
            },
            "saved_passengers": [],
            "membership": "regular",
            "reservations": [],
        }
        for trip in spec["trips"]:
            payload["flights"][trip["flight_number"]] = _flight(trip)
    return FinalCandidateAirlineDB.model_validate(payload)
