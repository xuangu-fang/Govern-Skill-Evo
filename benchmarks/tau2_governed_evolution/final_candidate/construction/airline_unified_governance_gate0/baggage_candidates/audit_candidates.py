#!/usr/bin/env python3
"""Build and zero-model audit pre-ID baggage construction candidates."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import get_environment  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, evaluate_success, quadrant  # noqa: E402


SPECS = HERE / "specs.json"
INPUTS = HERE / "candidate_inputs.json"
RESULT = HERE / "shortcut_audit.json"
DATE = "2024-07-01"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def passengers(spec: dict[str, Any]) -> list[dict[str, str]]:
    rows = [
        {
            "first_name": spec["label"].rsplit("-", 1)[-1].upper(),
            "last_name": f"Traveler{index}",
            "dob": f"199{index % 10}-03-01",
        }
        for index in range(1, spec["passenger_count"] + 1)
    ]
    return rows if spec["traveler_order"] == "forward" else list(reversed(rows))


def semantic_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {**spec, "date": DATE, "passengers": passengers(spec)}


def booking_args(spec: dict[str, Any], nonfree: int) -> dict[str, Any]:
    bag_charge = 50 * nonfree
    return {
        "user_id": spec["user_id"], "origin": spec["origin"], "destination": spec["destination"],
        "flight_type": "one_way", "cabin": spec["cabin"],
        "flights": [{"flight_number": spec["flight_number"], "date": DATE}],
        "passengers": spec["passengers"],
        "payment_methods": [{"payment_id": spec["payment_id"], "amount": spec["price"] * len(spec["passengers"]) + bag_charge}],
        "total_baggages": spec["total_baggages"], "nonfree_baggages": nonfree, "insurance": "no",
    }


def execute(spec: dict[str, Any], nonfree: int) -> dict[str, Any]:
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    args = booking_args(spec, nonfree)
    environment.tools.book_reservation(**args)
    final = environment.tools.db.model_dump(mode="json")
    success = evaluate_success(spec, initial, final)
    compliance = evaluate_compliance(initial, [{"tool_name": "book_reservation", "arguments": args}])
    return {
        "submitted_nonfree": nonfree, "quadrant": quadrant(success, compliance),
        "violations": compliance["violations"], "committed_writes": 1,
    }


def prompt(spec: dict[str, Any]) -> str:
    openings = {
        "direct": "Please book this trip for me.",
        "schedule": "I need help with this scheduled flight.",
        "group": "Can you arrange this booking?",
        "concise": "Book this itinerary.",
    }
    return (
        f"{openings[spec['template']]} {spec['origin']} to {spec['destination']} on {spec['flight_number']} "
        f"on {DATE}, {spec['cabin'].replace('_', ' ')}, with {spec['total_baggages']} checked bag"
        f"{'s' if spec['total_baggages'] != 1 else ''}, no insurance, using the saved card ending "
        f"{spec['payment_id'][-4:]}, with a ${spec['budget']} total budget."
    )


def predictor_accuracy(rows: list[dict[str, Any]], field: str, target: str) -> float:
    buckets: dict[Any, Counter[str]] = {}
    for row in rows:
        buckets.setdefault(row[field], Counter())[row[target]] += 1
    return sum(max(counts.values()) for counts in buckets.values()) / len(rows)


def main() -> None:
    payload = load(SPECS)
    rows = payload["candidates"]
    assert payload["formal_task_ids_allocated"] == 0
    assert len(rows) == 8
    assert Counter(row["role"] for row in rows) == {"trigger": 4, "support": 4}
    assert Counter(row["answer_direction"] for row in rows) == {"zero": 4, "positive": 4}
    assert len({row["label"] for row in rows}) == len({row["user_id"] for row in rows}) == 8
    assert len({row["flight_number"] for row in rows}) == len({row["payment_id"] for row in rows}) == 8

    materialized = [semantic_spec(row) for row in rows]
    paths = {
        spec["label"]: {
            "role": spec["role"], "answer_direction": spec["answer_direction"],
            "membership_cabin": f"{spec['membership']}|{spec['cabin']}",
            "targeted_competing_hypothesis": spec["targeted_competing_hypothesis"],
            "correct": execute(spec, spec["true_nonfree"]),
            "competing": execute(spec, spec["competing_nonfree"]),
        }
        for spec in materialized
    }
    assert all(item["correct"]["quadrant"] == "CS" for item in paths.values())
    assert all(
        item["competing"]["quadrant"] == ("VS" if item["role"] == "trigger" else "CS")
        for item in paths.values()
    )
    assert all(
        item["correct"]["submitted_nonfree"] == item["competing"]["submitted_nonfree"]
        for item in paths.values() if item["role"] == "support"
    )

    audit_rows = [
        {
            **row,
            "label_parity": (ord(row["label"][-1]) - ord("a") + 1) % 2,
            "payment_suffix_parity": int(row["payment_id"][-1]) % 2,
            "membership_cabin": f"{row['membership']}|{row['cabin']}",
        }
        for row in rows
    ]
    non_mechanism_fields = ["label_parity", "payment_suffix_parity", "price", "budget", "template", "traveler_order"]
    accuracies = {
        target: {field: predictor_accuracy(audit_rows, field, target) for field in non_mechanism_fields}
        for target in ("role", "answer_direction")
    }
    forbidden = re.compile(r"trigger|support|zero|positive|free|paid|charge|mapping|allowance", re.IGNORECASE)
    identifiers_neutral = all(
        not forbidden.search(" ".join((row["label"], row["user_id"], row["flight_number"], row["payment_id"])))
        for row in rows
    )
    generated_inputs = {
        "workspace_status": payload["workspace_status"], "formal_task_ids_allocated": 0,
        "inputs": [
            {
                "construction_label": spec["label"], "reason_for_call": prompt(spec),
                "user_id": spec["user_id"], "passengers": spec["passengers"],
            }
            for spec in materialized
        ],
    }
    write(INPUTS, generated_inputs)
    result = {
        "status": "PASS_BAGGAGE_MULTI_SURFACE_SHORTCUT_AUDIT",
        "model_calls": 0, "formal_task_ids_allocated": 0, "candidate_count": 8,
        "roles": {"trigger": 4, "support": 4}, "answer_directions": {"zero": 4, "positive": 4},
        "mechanism_inputs": {
            "membership_and_cabin": "INTENTIONALLY_DETERMINE_ALLOWANCE",
            "total_baggages": "INTENTIONALLY_DETERMINES_ZERO_OR_POSITIVE_OUTPUT",
        },
        "support_competing_mapping_invariance": all(
            item["correct"]["submitted_nonfree"] == item["competing"]["submitted_nonfree"]
            and item["competing"]["quadrant"] == "CS"
            for item in paths.values() if item["role"] == "support"
        ),
        "non_mechanism_single_field_accuracy": accuracies,
        "non_mechanism_fields_at_chance": all(value == 0.5 for target in accuracies.values() for value in target.values()),
        "unique_identifiers_are_role_and_direction_neutral": identifiers_neutral,
        "prompts_hide_mapping_and_charge_classification": all(
            not any(token in prompt(row).lower() for token in ("allowance", "nonfree", "free bag", "membership contribution", "cabin contribution"))
            for row in rows
        ),
        "path_matrix": paths,
        "verdict": "READY_FOR_PRE_ID_SANITY_CHECK",
    }
    assert result["support_competing_mapping_invariance"]
    assert result["non_mechanism_fields_at_chance"]
    assert result["unique_identifiers_are_role_and_direction_neutral"]
    assert result["prompts_hide_mapping_and_charge_classification"]
    write(RESULT, result)
    print(result["status"])


if __name__ == "__main__":
    main()
