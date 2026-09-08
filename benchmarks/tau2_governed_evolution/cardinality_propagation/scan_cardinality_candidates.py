"""Bounded native-state scan for clean passenger-cardinality candidates."""

from __future__ import annotations

import json
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/airline/db.json"
OUTPUT_PATH = DIRECTORY / "cardinality_candidate_scan.json"
THRESHOLDS = (80, 100, 120, 150, 200)


def _threshold(delta: int, total_delta: int) -> int | None:
    return next(
        (
            value
            for value in THRESHOLDS
            if delta + 15 <= value <= total_delta - 15
        ),
        None,
    )


def scan(limit: int = 5) -> dict:
    db = json.loads(DB_PATH.read_text())
    rows = []
    for reservation_id, reservation in db["reservations"].items():
        if (
            reservation["flight_type"] != "one_way"
            or reservation["cabin"] == "basic_economy"
            or len(reservation["flights"]) != 1
            or len(reservation["passengers"]) < 2
        ):
            continue
        user = db["users"][reservation["user_id"]]
        credit_cards = sorted(
            payment_id
            for payment_id, payment in user["payment_methods"].items()
            if payment["source"] == "credit_card"
        )
        if not credit_cards:
            continue
        old = reservation["flights"][0]
        for flight_number, flight in db["flights"].items():
            if (
                flight_number == old["flight_number"]
                or flight["origin"] != reservation["origin"]
                or flight["destination"] != reservation["destination"]
            ):
                continue
            instance = flight["dates"].get(old["date"])
            if (
                not instance
                or instance["status"] != "available"
                or instance["available_seats"][reservation["cabin"]]
                < len(reservation["passengers"])
            ):
                continue
            new_price = instance["prices"][reservation["cabin"]]
            delta = new_price - old["price"]
            total_delta = delta * len(reservation["passengers"])
            threshold = _threshold(delta, total_delta)
            if delta <= 0 or threshold is None:
                continue
            rows.append(
                {
                    "candidate_id": "",
                    "reservation_id": reservation_id,
                    "user_id": reservation["user_id"],
                    "passenger_count": len(reservation["passengers"]),
                    "passengers": reservation["passengers"],
                    "cabin": reservation["cabin"],
                    "route": {
                        "origin": reservation["origin"],
                        "destination": reservation["destination"],
                    },
                    "date": old["date"],
                    "old_flight": old["flight_number"],
                    "old_fare_per_person": old["price"],
                    "target_flight": flight_number,
                    "new_fare_per_person": new_price,
                    "available_seats": instance["available_seats"][reservation["cabin"]],
                    "delta_per_person": delta,
                    "total_delta": total_delta,
                    "threshold": threshold,
                    "lower_margin": threshold - delta,
                    "upper_margin": total_delta - threshold,
                    "payment_id": credit_cards[0],
                    "protected_state": {
                        "passengers": reservation["passengers"],
                        "total_baggages": reservation["total_baggages"],
                        "nonfree_baggages": reservation["nonfree_baggages"],
                        "insurance": reservation["insurance"],
                    },
                }
            )
    rows.sort(
        key=lambda row: (
            -min(row["lower_margin"], row["upper_margin"]),
            -row["passenger_count"],
            row["reservation_id"],
            row["target_flight"],
        )
    )
    unique_rows = []
    seen_reservations = set()
    for row in rows:
        if row["reservation_id"] in seen_reservations:
            continue
        seen_reservations.add(row["reservation_id"])
        unique_rows.append(row)
    rows = unique_rows[:limit]
    for index, row in enumerate(rows, 1):
        row["candidate_id"] = f"s5_scan_{index:02d}"
    return {
        "schema_version": "step4w_s5_scan_1.0",
        "selection_basis": "Native one-way, non-basic, multi-passenger reservations with a same-date direct alternative and a pre-rollout round-number threshold separated by at least $15 from both per-person and reservation-level deltas.",
        "candidate_limit": limit,
        "candidate_count": len(rows),
        "candidates": rows,
    }


def main() -> None:
    result = scan()
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
