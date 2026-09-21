"""Add the unchanged insured-cancellation Governance stage to calibration entities."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.data_model import FinalCandidateAirlineDB
from benchmarks.tau2_governed_evolution.final_candidate.construction.joint_capability_experience_mapping_v1.fixture import _flight, build_db


HERE = Path(__file__).resolve().parent


def build_joint_db() -> FinalCandidateAirlineDB:
    payload = build_db().model_dump(mode="json")
    for spec in json.loads((HERE / "specs.json").read_text(encoding="utf-8"))["candidates"]:
        user = payload["users"][spec["user_id"]]
        card = spec["cancel_payment_id"]
        user["payment_methods"][card] = {"source": "credit_card", "id": card, "brand": "visa", "last_four": card[-4:]}
        user["reservations"].append(spec["cancel_reservation_id"])
        flight = {"flight_number": spec["cancel_flight_number"], "origin": spec["cancel_origin"], "destination": spec["cancel_destination"], "date": spec["cancel_flight_date"], "price": spec["cancel_price"]}
        payload["flights"][spec["cancel_flight_number"]] = _flight(flight)
        payload["reservations"][spec["cancel_reservation_id"]] = {
            "reservation_id": spec["cancel_reservation_id"], "user_id": spec["user_id"],
            "origin": spec["cancel_origin"], "destination": spec["cancel_destination"],
            "flight_type": "one_way", "cabin": "economy",
            "flights": [{"flight_number": spec["cancel_flight_number"], "origin": spec["cancel_origin"], "destination": spec["cancel_destination"], "date": spec["cancel_flight_date"], "price": spec["cancel_price"]}],
            "passengers": [spec["passenger"]], "payment_history": [{"payment_id": card, "amount": spec["cancel_price"]}],
            "created_at": "2024-05-01T10:00:00", "total_baggages": 0, "nonfree_baggages": 0,
            "insurance": "yes", "status": None,
        }
    return FinalCandidateAirlineDB.model_validate(payload)
