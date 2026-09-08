"""Bounded native-state scan for Step 4W-S3 certificate lifecycle candidates."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/airline/db.json"
OUTPUT_PATH = DIRECTORY / "certificate_candidate_scan.json"


def _available_direct_economy_flights(db: dict) -> list[dict]:
    rows: list[dict] = []
    for flight_number, flight in db["flights"].items():
        for date, state in flight["dates"].items():
            if state.get("status") != "available":
                continue
            if state["available_seats"]["economy"] < 1:
                continue
            rows.append(
                {
                    "flight_number": flight_number,
                    "date": date,
                    "origin": flight["origin"],
                    "destination": flight["destination"],
                    "departure": flight["scheduled_departure_time_est"],
                    "arrival": flight["scheduled_arrival_time_est"],
                    "price": state["prices"]["economy"],
                }
            )
    return rows


def scan(limit: int = 5) -> dict:
    db = json.loads(DB_PATH.read_text())
    flights = _available_direct_economy_flights(db)
    # Group by price so we can scan the small price grid while retaining
    # independent, chronologically plausible flight/date realizations.
    flights_by_price: dict[int, list[dict]] = {}
    for flight in sorted(flights, key=lambda row: (row["date"], row["flight_number"])):
        flights_by_price.setdefault(flight["price"], []).append(flight)
    candidates: list[dict] = []

    for user_id, user in sorted(db["users"].items()):
        certificates = sorted(
            (method for method in user["payment_methods"].values() if method["source"] == "certificate"),
            key=lambda method: (-method["amount"], method["id"]),
        )
        gift_cards = sorted(
            (method for method in user["payment_methods"].values() if method["source"] == "gift_card"),
            key=lambda method: (-method["amount"], method["id"]),
        )
        if not certificates or not gift_cards:
            continue

        # Prefer one certificate and one gift card with a large, easy-to-explain
        # separation between the cheap first trip and the expensive second trip.
        for certificate in certificates:
            for gift_card in gift_cards:
                c_balance = certificate["amount"]
                g_balance = gift_card["amount"]
                a_prices = [price for price in flights_by_price if price < c_balance and price <= g_balance]
                b_prices = [price for price in flights_by_price if g_balance < price <= c_balance]
                pairs = []
                for a_price in a_prices:
                    for b_price in b_prices:
                        if a_price + b_price > c_balance + g_balance:
                            continue
                        for trip_a in flights_by_price[a_price][:20]:
                            for trip_b in flights_by_price[b_price][-20:]:
                                if trip_a["date"] >= trip_b["date"]:
                                    continue
                                pairs.append((trip_a, trip_b))
                                break
                            if pairs and pairs[-1][0] is trip_a:
                                break
                if not pairs:
                    continue
                pairs.sort(
                    key=lambda pair: (
                        -(c_balance - pair[0]["price"]),
                        -(pair[1]["price"] - g_balance),
                        pair[0]["date"],
                        pair[0]["flight_number"],
                        pair[1]["date"],
                        pair[1]["flight_number"],
                    )
                )
                top_pairs = pairs[: min(40, len(pairs))]
                offset = int(hashlib.sha256(user_id.encode()).hexdigest()[:8], 16) % len(top_pairs)
                trip_a, trip_b = top_pairs[offset]
                candidates.append(
                    {
                        "candidate_id": f"s3_scan_{len(candidates) + 1:02d}",
                        "user_id": user_id,
                        "passenger": {
                            "first_name": user["name"]["first_name"],
                            "last_name": user["name"]["last_name"],
                            "dob": user["dob"],
                        },
                        "membership": user["membership"],
                        "certificate": {"id": certificate["id"], "balance": c_balance},
                        "gift_card": {"id": gift_card["id"], "balance": g_balance},
                        "trip_a": trip_a,
                        "trip_b": trip_b,
                        "correct_allocation": {
                            "trip_a": [{"payment_id": gift_card["id"], "amount": trip_a["price"]}],
                            "trip_b": [{"payment_id": certificate["id"], "amount": trip_b["price"]}],
                        },
                        "wrong_local_allocation": {
                            "trip_a": [{"payment_id": certificate["id"], "amount": trip_a["price"]}],
                            "trip_b_remaining_allowed_balance": g_balance,
                        },
                        "geometry": {
                            "a_lt_c": trip_a["price"] < c_balance,
                            "a_le_g": trip_a["price"] <= g_balance,
                            "b_gt_g": trip_b["price"] > g_balance,
                            "a_plus_b_le_c_plus_g": trip_a["price"] + trip_b["price"] <= c_balance + g_balance,
                            "b_le_c_plus_g_minus_a": trip_b["price"] <= c_balance + (g_balance - trip_a["price"]),
                            "unused_certificate_value_if_used_on_a": c_balance - trip_a["price"],
                            "trip_b_shortfall_after_wrong_allocation": trip_b["price"] - g_balance,
                        },
                        "why_wrong_allocation_fails": (
                            f"Using {certificate['id']} for ${trip_a['price']} on Trip A removes the certificate; "
                            f"the remaining allowed gift card balance ${g_balance} is ${trip_b['price'] - g_balance} short for Trip B."
                        ),
                    }
                )
                break
            if candidates and candidates[-1]["user_id"] == user_id:
                break

    # Rank for clean, salient geometry and retain only the bounded scan output.
    candidates.sort(
        key=lambda item: (
            -item["geometry"]["trip_b_shortfall_after_wrong_allocation"],
            -item["geometry"]["unused_certificate_value_if_used_on_a"],
            item["user_id"],
        )
    )
    selected = candidates[:limit]
    for index, item in enumerate(selected, 1):
        item["candidate_id"] = f"s3_scan_{index:02d}"
    return {
        "schema_version": "step4w_s3_scan_1.0",
        "selection_basis": "native DB geometry only; no model rollout outcomes",
        "candidate_limit": limit,
        "candidate_count": len(selected),
        "candidates": selected,
    }


def main() -> int:
    result = scan()
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
