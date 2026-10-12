"""JSG-01 reservations with legal and destination-changing options."""

import json
from pathlib import Path
from typing import Any

from src.benchmark_v3.development.latent_settlement_contract.environment.data_model import SettlementFlightDB
from src.benchmark_v3.development.latent_settlement_contract.environment.fixture import _flight, _reservation, _user, build_gate0_db as build_ee01_db


def _add_task(
    payload: dict[str, Any],
    *,
    reservation_id: str,
    user_id: str,
    card_id: str,
    channel: str,
    baseline: str,
    date: str,
    origin: str,
    connection: str,
    destination: str,
    alternate_destination: str,
    retained: str,
    replaced: str,
    retained_historical: int,
    replaced_historical: int,
    retained_current: int,
    preferred_legal: str,
    preferred_alternate: str,
    preferred_price: int,
    fallback_legal: str,
    fallback_alternate: str,
    fallback_price: int,
    candidate_order: list[str] | None = None,
) -> None:
    flights = payload["flights"]
    flights[retained] = _flight(retained, origin, connection, retained_current, date)
    flights[replaced] = _flight(replaced, connection, destination, replaced_historical, date)
    candidates = {
        "preferred_legal": (preferred_legal, destination, preferred_price),
        "preferred_alternate": (
            preferred_alternate,
            alternate_destination,
            preferred_price,
        ),
        "fallback_legal": (fallback_legal, destination, fallback_price),
        "fallback_alternate": (
            fallback_alternate,
            alternate_destination,
            fallback_price,
        ),
    }
    order = candidate_order or list(candidates)
    if set(order) != set(candidates) or len(order) != len(candidates):
        raise ValueError("candidate_order must contain each candidate exactly once")
    for label in order:
        flight_number, candidate_destination, price = candidates[label]
        flights[flight_number] = _flight(
            flight_number, connection, candidate_destination, price, date
        )
    payload["users"][user_id] = _user(user_id, reservation_id, card_id)
    payload["reservations"][reservation_id] = _reservation(
        reservation_id,
        user_id,
        retained,
        replaced,
        retained_historical,
        replaced_historical,
        card_id,
        date,
        origin,
        connection,
        destination,
    )
    payload["settlement_contracts"][reservation_id] = {
        "ticketing_channel": channel,
        "remaining_changes": 1,
        "settlement_baseline": baseline,
    }


def build_gate0_db() -> SettlementFlightDB:
    payload = build_ee01_db().model_dump(mode="json")
    _add_task(
        payload,
        reservation_id="JSG01A",
        user_id="jsg_user_a",
        card_id="credit_card_6101",
        channel="horizon",
        baseline="retained_historical",
        date="2024-06-20",
        origin="CLT",
        connection="PHL",
        destination="EWR",
        alternate_destination="LGA",
        retained="JAA110",
        replaced="JAA120",
        retained_historical=100,
        replaced_historical=100,
        retained_current=300,
        preferred_legal="JAA121",
        preferred_alternate="JAA122",
        preferred_price=140,
        fallback_legal="JAA123",
        fallback_alternate="JAA124",
        fallback_price=50,
    )
    _add_task(
        payload,
        reservation_id="JSG01B",
        user_id="jsg_user_b",
        card_id="credit_card_6202",
        channel="summit",
        baseline="complete_current",
        date="2024-06-21",
        origin="SEA",
        connection="PDX",
        destination="SFO",
        alternate_destination="OAK",
        retained="JBB210",
        replaced="JBB220",
        retained_historical=120,
        replaced_historical=100,
        retained_current=320,
        preferred_legal="JBB221",
        preferred_alternate="JBB222",
        preferred_price=130,
        fallback_legal="JBB223",
        fallback_alternate="JBB224",
        fallback_price=40,
    )
    return SettlementFlightDB.model_validate(payload)


def build_core_db() -> SettlementFlightDB:
    payload = build_gate0_db().model_dump(mode="json")
    specs_path = (
        (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/joint_settlement_destination_scope/core_family/candidates/task_specs.json')
    )
    specs = json.loads(specs_path.read_text(encoding="utf-8"))["tasks"]
    for spec in specs:
        _add_task(
            payload,
            reservation_id=spec["reservation_id"],
            user_id=spec["user_id"],
            card_id=spec["payment_id"],
            channel=spec["ticketing_channel"],
            baseline=spec["settlement_baseline"],
            date=spec["date"],
            origin=spec["origin"],
            connection=spec["connection"],
            destination=spec["destination"],
            alternate_destination=spec["alternate_destination"],
            retained=spec["retained_flight"],
            replaced=spec["replaced_flight"],
            retained_historical=spec["retained_historical_price"],
            replaced_historical=spec["replaced_historical_price"],
            retained_current=spec["retained_current_price"],
            preferred_legal=spec["preferred_legal"],
            preferred_alternate=spec["preferred_alternate"],
            preferred_price=spec["preferred_current_price"],
            fallback_legal=spec["fallback_legal"],
            fallback_alternate=spec["fallback_alternate"],
            fallback_price=spec["fallback_current_price"],
            candidate_order=spec["candidate_order"],
        )
    return SettlementFlightDB.model_validate(payload)
