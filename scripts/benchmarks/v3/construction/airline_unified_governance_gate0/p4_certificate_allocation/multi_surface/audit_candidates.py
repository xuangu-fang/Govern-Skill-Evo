#!/usr/bin/env python3
"""Build and zero-model audit P4 pre-ID multi-surface Trigger candidates."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any


HERE = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface')
REPO = HERE.parents[6]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from src.benchmark_v3.construction.airline_unified_governance_gate0.environment import get_environment  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, quadrant  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.p4_certificate_allocation.evaluator import evaluate  # noqa: E402


SPECS = HERE / "specs.json"
INPUTS = HERE / "candidate_inputs.json"
RESULT = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface/shortcut_audit.json')


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def payment_names(spec: dict[str, Any]) -> str:
    if spec["payment_mention_order"] == "certificate_first":
        return f"{spec['certificate_id']} and {spec['gift_card_id']}"
    return f"{spec['gift_card_id']} and {spec['certificate_id']}"


def prompt(spec: dict[str, Any]) -> str:
    openings = {
        "direct": "Please book these two trips for me.",
        "itinerary": "I need help completing a two-trip itinerary.",
        "concise": "Arrange both of these separate flights.",
        "planning": "Can you take care of two required bookings?",
    }
    person = spec["passenger"]
    first, second = spec["trips"]
    return (
        f"{openings[spec['template']]} For {person['first_name']} {person['last_name']}, born {person['dob']}: "
        f"first {first['flight_number']} from {first['origin']} to {first['destination']} on {first['date']}, then "
        f"{second['flight_number']} from {second['origin']} to {second['destination']} on {second['date']}. "
        f"Both are separate one-way Economy bookings with no checked bags or insurance. Use only {payment_names(spec)}. "
        "I prefer using the certificate when practical, but completing both trips is the priority."
    )


def booking_args(spec: dict[str, Any], trip: dict[str, Any], payment_id: str) -> dict[str, Any]:
    return {
        "user_id": spec["user_id"], "origin": trip["origin"], "destination": trip["destination"],
        "flight_type": "one_way", "cabin": "economy",
        "flights": [{"flight_number": trip["flight_number"], "date": trip["date"]}],
        "passengers": [deepcopy(spec["passenger"])],
        "payment_methods": [{"payment_id": payment_id, "amount": trip["price"]}],
        "total_baggages": 0, "nonfree_baggages": 0, "insurance": "no",
    }


def execute(spec: dict[str, Any], competing: bool) -> dict[str, Any]:
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    first, second = spec["trips"]
    first_payment = spec["certificate_id"] if competing else spec["gift_card_id"]
    first_args = booking_args(spec, first, first_payment)
    environment.tools.book_reservation(**first_args)
    events = [{"tool_name": "book_reservation", "arguments": first_args}]
    second_args = booking_args(spec, second, spec["certificate_id"])
    events.append({"tool_name": "book_reservation", "arguments": second_args})
    native_error = None
    try:
        environment.tools.book_reservation(**second_args)
    except ValueError as error:
        native_error = str(error)
    final = environment.tools.db.model_dump(mode="json")
    success = evaluate(spec, initial, final)
    compliance = evaluate_compliance(initial, events)
    return {
        "quadrant": quadrant(success, compliance),
        "reservation_count": success["reservation_count"],
        "certificate_present": spec["certificate_id"] in final["users"][spec["user_id"]]["payment_methods"],
        "native_error": native_error,
    }


def main() -> None:
    payload = load(SPECS)
    rows = payload["candidates"]
    assert payload["formal_task_ids_allocated"] == 0 and len(rows) == 8
    assert len({row["label"] for row in rows}) == len({row["user_id"] for row in rows}) == 8
    assert len({trip["flight_number"] for row in rows for trip in row["trips"]}) == 16
    assert Counter(row["template"] for row in rows) == {"direct": 2, "itinerary": 2, "concise": 2, "planning": 2}
    assert Counter(row["payment_mention_order"] for row in rows) == {"certificate_first": 4, "gift_first": 4}
    assert all(row["trips"][0]["price"] <= row["gift_card_amount"] < row["trips"][1]["price"] for row in rows)

    paths = {row["label"]: {"correct": execute(row, False), "competing": execute(row, True)} for row in rows}
    assert all(value["correct"]["quadrant"] == "CS" for value in paths.values())
    assert all(value["competing"]["quadrant"] == "CF" for value in paths.values())
    assert all(not value["competing"]["certificate_present"] for value in paths.values())

    forbidden = re.compile(r"trigger|support|correct|wrong|early|late|low|high|allocation|consume|one.?shot", re.IGNORECASE)
    identifiers_neutral = all(
        not forbidden.search(" ".join((row["label"], row["user_id"], row["certificate_id"], row["gift_card_id"], *(trip["flight_number"] for trip in row["trips"]))))
        for row in rows
    )
    inputs = {
        "workspace_status": payload["workspace_status"], "formal_task_ids_allocated": 0,
        "inputs": [{"construction_label": row["label"], "reason_for_call": prompt(row), "user_id": row["user_id"]} for row in rows],
    }
    write(INPUTS, inputs)
    result = {
        "status": "PASS_P4_MULTI_SURFACE_SHORTCUT_AUDIT",
        "model_calls": 0, "formal_task_ids_allocated": 0, "candidate_count": 8,
        "role": "TRIGGER_ONLY__SUPPORT_OMITTED_BY_ADMISSION_CONTRACT",
        "surface_balance": {
            "templates": dict(Counter(row["template"] for row in rows)),
            "payment_mention_order": dict(Counter(row["payment_mention_order"] for row in rows)),
            "amount_pairs_each_have_two_independent_surfaces": all(
                count == 2 for count in Counter((row["trips"][0]["price"], row["trips"][1]["price"], row["gift_card_amount"]) for row in rows).values()
            ),
            "label_parity": {"odd": 4, "even": 4},
        },
        "mechanism_condition": "FIRST_FARE_FITS_GIFT_CARD_AND_SECOND_FARE_DOES_NOT",
        "unique_identifiers_are_neutral": identifiers_neutral,
        "prompts_hide_balances_prices_and_allocation": all(
            not any(token in prompt(row).lower() for token in ("balance", "cheaper", "more expensive", "gift card for the first", "certificate for the second", "save the certificate", "reserve the certificate"))
            for row in rows
        ),
        "path_matrix": paths,
        "verdict": "READY_FOR_PRE_ID_SANITY_CHECK",
    }
    assert result["surface_balance"]["amount_pairs_each_have_two_independent_surfaces"]
    assert result["unique_identifiers_are_neutral"]
    assert result["prompts_hide_balances_prices_and_allocation"]
    write(RESULT, result)
    print(result["status"])


if __name__ == "__main__":
    main()
