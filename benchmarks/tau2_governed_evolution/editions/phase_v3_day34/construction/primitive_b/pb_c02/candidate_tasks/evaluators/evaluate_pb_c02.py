"""Semantic final-state evaluation and offline attribution for PB-C02."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[9]
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from tau2.domains.airline.data_model import FlightDB  # noqa: E402
from tau2.domains.airline.tools import AirlineTools  # noqa: E402


FAILURE_MODES = (
    "HARD_CONSTRAINT_VIOLATION",
    "PREMATURE_PREFERENCE_OPTIMIZATION",
    "WRONG_FEASIBLE_RANKING",
    "FALLBACK_ERROR",
    "NO_FEASIBLE_CANDIDATE_ERROR",
    "SEARCH_OR_BINDING_ERROR",
    "UNRELATED_FAILURE",
)


def _same_day_time(value: str) -> tuple[bool, str]:
    return "+1" not in value, value.replace("+1", "")


def feasible_candidates(
    spec: dict[str, Any], initial_db: dict[str, Any], cabin: str
) -> list[dict[str, Any]]:
    db = FlightDB.model_validate(copy.deepcopy(initial_db))
    tools = AirlineTools(db)
    reservation = tools.get_reservation_details(spec["reservation_id"])
    profile = spec["constraint_profile"]
    rows = []
    for candidate in tools.search_direct_flight(
        reservation.origin, reservation.destination, spec["target_date"]
    ):
        same_day, arrival = _same_day_time(candidate.scheduled_arrival_time_est)
        if profile.get("same_day_arrival") and not same_day:
            continue
        if profile.get("departure_min") and candidate.scheduled_departure_time_est < profile["departure_min"]:
            continue
        if profile.get("arrival_max") and arrival > profile["arrival_max"]:
            continue
        if candidate.available_seats[cabin] < len(reservation.passengers):
            continue
        max_fare = profile.get("max_fare")
        if cabin == profile.get("preferred_cabin"):
            max_fare = profile.get("preferred_cabin_max_fare")
        if max_fare is not None and candidate.prices[cabin] > max_fare:
            continue
        rows.append({
            "flight_number": candidate.flight_number,
            "departure": candidate.scheduled_departure_time_est,
            "arrival": candidate.scheduled_arrival_time_est,
            "fare": candidate.prices[cabin],
            "cabin": cabin,
        })
    return rows


def selected_cabin(spec: dict[str, Any], initial_db: dict[str, Any]) -> str | None:
    profile = spec["constraint_profile"]
    preferred = profile.get("preferred_cabin")
    if preferred and feasible_candidates(spec, initial_db, preferred):
        return preferred
    fallback = profile.get("fallback_cabin")
    return fallback or spec["target_cabin"]


def rank_candidates(spec: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = list(rows)
    for rule in reversed(spec["ranking"]):
        if rule == "min_fare":
            ranked.sort(key=lambda row: row["fare"])
        elif rule == "max_departure":
            ranked.sort(key=lambda row: row["departure"], reverse=True)
        else:
            raise ValueError(f"unknown ranking rule: {rule}")
    return ranked


def expected_selection(spec: dict[str, Any], initial_db: dict[str, Any]) -> tuple[str | None, str | None]:
    cabin = selected_cabin(spec, initial_db)
    if cabin is None:
        return None, None
    ranked = rank_candidates(spec, feasible_candidates(spec, initial_db, cabin))
    return (cabin, ranked[0]["flight_number"]) if ranked else (None, None)


def expected_final_db(spec: dict[str, Any], initial_db: dict[str, Any]) -> dict[str, Any]:
    db = FlightDB.model_validate(copy.deepcopy(initial_db))
    tools = AirlineTools(db)
    cabin, flight_number = expected_selection(spec, initial_db)
    if cabin is None or flight_number is None:
        return db.model_dump(mode="json")
    tools.update_reservation_flights(
        reservation_id=spec["reservation_id"],
        cabin=cabin,
        flights=[{"flight_number": flight_number, "date": spec["target_date"]}],
        payment_id=spec["payment_id"],
    )
    return db.model_dump(mode="json")


def evaluate_success(
    spec: dict[str, Any], initial_db: dict[str, Any], final_db: dict[str, Any]
) -> dict[str, Any]:
    expected = expected_final_db(spec, initial_db)
    rid = spec["reservation_id"]
    success = final_db == expected
    return {
        "success": success,
        "semantic_invariant": {
            "selected_candidate_satisfies_all_hard_constraints": final_db["reservations"].get(rid) == expected["reservations"].get(rid),
            "selection_matches_feasible_set_ranking_or_allowed_fallback": final_db["reservations"].get(rid, {}).get("flights") == expected["reservations"].get(rid, {}).get("flights") and final_db["reservations"].get(rid, {}).get("cabin") == expected["reservations"].get(rid, {}).get("cabin"),
            "no_invalid_mutation_committed": final_db == expected,
        },
        "expected_selection": {
            "cabin": expected["reservations"][rid]["cabin"],
            "flights": expected["reservations"][rid]["flights"],
        },
        "observed_selection": {
            "cabin": final_db["reservations"][rid]["cabin"],
            "flights": final_db["reservations"][rid]["flights"],
        },
    }


def _tool_calls(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        call
        for message in simulation.get("messages", [])
        if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
    ]


def attribute_failure(
    spec: dict[str, Any], initial_db: dict[str, Any], simulation: dict[str, Any]
) -> dict[str, Any]:
    calls = _tool_calls(simulation)
    writes = [
        call for call in calls
        if call.get("name") == "update_reservation_flights"
        and call.get("arguments", {}).get("reservation_id") == spec["reservation_id"]
    ]
    searches = [call for call in calls if call.get("name") in {"search_direct_flight", "search_onestop_flight"}]
    correct_cabin, correct_flight = expected_selection(spec, initial_db)
    if not writes:
        mode = "FALLBACK_ERROR" if spec["constraint_profile"].get("preferred_cabin") else "SEARCH_OR_BINDING_ERROR"
        return {"mode": mode, "evidence": "no target reservation flight mutation", "search_calls": len(searches)}

    args = writes[-1].get("arguments", {})
    cabin = args.get("cabin")
    flight_rows = args.get("flights") or []
    if len(flight_rows) != 1 or not isinstance(flight_rows[0], dict):
        return {"mode": "SEARCH_OR_BINDING_ERROR", "evidence": "mutation did not bind exactly one candidate"}
    flight = flight_rows[0].get("flight_number")

    if cabin != correct_cabin:
        return {"mode": "FALLBACK_ERROR", "evidence": f"selected cabin {cabin!r}, expected allowed branch {correct_cabin!r}"}
    feasible = {row["flight_number"] for row in feasible_candidates(spec, initial_db, cabin)}
    if flight not in feasible:
        mode = (
            "PREMATURE_PREFERENCE_OPTIMIZATION"
            if flight in set(spec.get("tempting_infeasible_flights", []))
            else "HARD_CONSTRAINT_VIOLATION"
        )
        return {"mode": mode, "evidence": f"selected infeasible candidate {flight!r}"}
    if flight != correct_flight:
        return {"mode": "WRONG_FEASIBLE_RANKING", "evidence": f"selected {flight!r}, ranked optimum is {correct_flight!r}"}
    return {"mode": "UNRELATED_FAILURE", "evidence": "correct final candidate was selected but final DB differs from semantic target"}
