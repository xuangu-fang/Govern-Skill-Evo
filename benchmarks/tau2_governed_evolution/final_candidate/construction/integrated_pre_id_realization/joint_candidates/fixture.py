"""Add only the selected pre-ID Joint fixtures to the integrated Airline DB."""

import json
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.data_model import (
    FinalCandidateAirlineDB,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.fixture import (
    build_gate0_db,
)


HERE = Path(__file__).resolve().parent


def _available(price: int) -> dict[str, Any]:
    return {
        "status": "available",
        "available_seats": {"basic_economy": 12, "economy": 12, "business": 12},
        "prices": {"basic_economy": price, "economy": price, "business": price},
    }


def build_joint_db() -> FinalCandidateAirlineDB:
    payload = build_gate0_db().model_dump(mode="json")
    specs = json.loads((HERE / "specs.json").read_text(encoding="utf-8"))
    candidates = [item for family in specs["families"] for item in family["candidates"]]
    for spec in candidates:
        payment_methods = {
            spec["certificate_id"]: {
                "source": "certificate",
                "id": spec["certificate_id"],
                "amount": spec["certificate_amount"],
            },
            spec["gift_card_id"]: {
                "source": "gift_card",
                "id": spec["gift_card_id"],
                "amount": spec["gift_card_amount"],
            },
        }
        first_passenger = (
            spec["passenger"]
            if "passenger" in spec
            else spec["group_passengers"][0]
        )
        payload["users"][spec["user_id"]] = {
            "user_id": spec["user_id"],
            "name": {
                "first_name": first_passenger["first_name"],
                "last_name": first_passenger["last_name"],
            },
            "address": {
                "address1": "1 Joint Way", "address2": None, "city": "Boston",
                "country": "USA", "state": "MA", "zip": "02108",
            },
            "email": f"{spec['user_id']}@example.test",
            "dob": first_passenger["dob"],
            "payment_methods": payment_methods,
            "saved_passengers": [],
            "membership": spec["membership"],
            "reservations": [],
        }
        for trip in (spec["governed_trip"], spec["certificate_trip"]):
            payload["flights"][trip["flight_number"]] = {
                "flight_number": trip["flight_number"],
                "origin": trip["origin"],
                "destination": trip["destination"],
                "scheduled_departure_time_est": "10:00:00",
                "scheduled_arrival_time_est": "12:00:00",
                "dates": {trip["date"]: _available(trip["price"])},
            }
    return FinalCandidateAirlineDB.model_validate(payload)
