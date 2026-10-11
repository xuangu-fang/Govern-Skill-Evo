"""Deterministic fixture for the EE-01 Gate 0 and admitted Core tasks."""

import json
from pathlib import Path
from typing import Any

from .data_model import SettlementFlightDB


DATE = "2024-06-01"
CORE_SPECS = (
    Path(__file__).resolve().parent.parent
    / "core_family/candidates/task_specs.json"
)


def _available(price: int) -> dict[str, Any]:
    return {
        "status": "available",
        "available_seats": {"basic_economy": 5, "economy": 5, "business": 5},
        "prices": {
            "basic_economy": price,
            "economy": price,
            "business": price + 200,
        },
    }


def _flight(
    number: str, origin: str, destination: str, price: int, date: str = DATE
) -> dict[str, Any]:
    return {
        "flight_number": number,
        "origin": origin,
        "destination": destination,
        "scheduled_departure_time_est": "09:00:00",
        "scheduled_arrival_time_est": "11:00:00",
        "dates": {date: _available(price)},
    }


def _user(user_id: str, reservation_id: str, card_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "name": {"first_name": "Evelyn", "last_name": "Stone"},
        "address": {
            "address1": "1 Test Way",
            "address2": None,
            "city": "Boston",
            "country": "USA",
            "state": "MA",
            "zip": "02108",
        },
        "email": f"{user_id}@example.test",
        "dob": "1990-01-01",
        "payment_methods": {
            card_id: {
                "source": "credit_card",
                "id": card_id,
                "brand": "visa",
                "last_four": card_id[-4:],
            }
        },
        "saved_passengers": [],
        "membership": "regular",
        "reservations": [reservation_id],
    }


def _reservation(
    reservation_id: str,
    user_id: str,
    retained: str,
    replaced: str,
    retained_historical_price: int,
    replaced_historical_price: int,
    card_id: str,
    date: str = DATE,
    origin: str = "AAA",
    connection: str = "BBB",
    destination: str = "CCC",
) -> dict[str, Any]:
    return {
        "reservation_id": reservation_id,
        "user_id": user_id,
        "origin": origin,
        "destination": destination,
        "flight_type": "one_way",
        "cabin": "economy",
        "flights": [
            {
                "origin": origin,
                "destination": connection,
                "flight_number": retained,
                "date": date,
                "price": retained_historical_price,
            },
            {
                "origin": connection,
                "destination": destination,
                "flight_number": replaced,
                "date": date,
                "price": replaced_historical_price,
            },
        ],
        "passengers": [
            {"first_name": "Evelyn", "last_name": "Stone", "dob": "1990-01-01"}
        ],
        "payment_history": [{"payment_id": card_id, "amount": retained_historical_price + replaced_historical_price}],
        "created_at": "2024-05-01T10:00:00",
        "total_baggages": 0,
        "nonfree_baggages": 0,
        "insurance": "no",
        "status": None,
    }


def build_gate0_db() -> SettlementFlightDB:
    """Build the two Gate 0 seeds plus the admitted eight-task Core family."""
    flights = {
        "ALEG10": _flight("ALEG10", "AAA", "BBB", 300),
        "AOLD20": _flight("AOLD20", "BBB", "CCC", 100),
        "APREF21": _flight("APREF21", "BBB", "CCC", 140),
        "AFALL22": _flight("AFALL22", "BBB", "CCC", 50),
        "BLEG10": _flight("BLEG10", "AAA", "BBB", 320),
        "BOLD20": _flight("BOLD20", "BBB", "CCC", 100),
        "BPREF21": _flight("BPREF21", "BBB", "CCC", 130),
        "BFALL22": _flight("BFALL22", "BBB", "CCC", 40),
    }
    users = {
        "ee01_user_a": _user("ee01_user_a", "EE01A1", "credit_card_1101"),
        "ee01_user_b": _user("ee01_user_b", "EE01B1", "credit_card_2202"),
    }
    reservations = {
        "EE01A1": _reservation(
            "EE01A1", "ee01_user_a", "ALEG10", "AOLD20", 100, 100, "credit_card_1101"
        ),
        "EE01B1": _reservation(
            "EE01B1", "ee01_user_b", "BLEG10", "BOLD20", 120, 100, "credit_card_2202"
        ),
    }
    contracts = {
        "EE01A1": {
            "ticketing_channel": "horizon",
            "remaining_changes": 1,
            "settlement_baseline": "retained_historical",
        },
        "EE01B1": {
            "ticketing_channel": "summit",
            "remaining_changes": 1,
            "settlement_baseline": "complete_current",
        },
    }

    core = json.loads(CORE_SPECS.read_text(encoding="utf-8"))
    for spec in core["tasks"]:
        date = spec["date"]
        origin = spec["origin"]
        connection = spec["connection"]
        destination = spec["destination"]
        flights[spec["retained_flight"]] = _flight(
            spec["retained_flight"],
            origin,
            connection,
            spec["retained_current_price"],
            date,
        )
        flights[spec["replaced_flight"]] = _flight(
            spec["replaced_flight"],
            connection,
            destination,
            spec["replaced_historical_price"],
            date,
        )
        flights[spec["preferred_flight"]] = _flight(
            spec["preferred_flight"],
            connection,
            destination,
            spec["preferred_current_price"],
            date,
        )
        flights[spec["fallback_flight"]] = _flight(
            spec["fallback_flight"],
            connection,
            destination,
            spec["fallback_current_price"],
            date,
        )
        users[spec["user_id"]] = _user(
            spec["user_id"], spec["reservation_id"], spec["payment_id"]
        )
        reservations[spec["reservation_id"]] = _reservation(
            spec["reservation_id"],
            spec["user_id"],
            spec["retained_flight"],
            spec["replaced_flight"],
            spec["retained_historical_price"],
            spec["replaced_historical_price"],
            spec["payment_id"],
            date,
            origin,
            connection,
            destination,
        )
        contracts[spec["reservation_id"]] = {
            "ticketing_channel": spec["ticketing_channel"],
            "remaining_changes": 1,
            "settlement_baseline": spec["settlement_baseline"],
        }
    return SettlementFlightDB.model_validate(
        {
            "flights": flights,
            "users": users,
            "reservations": reservations,
            "settlement_contracts": contracts,
        }
    )
