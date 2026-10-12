#!/usr/bin/env python3
"""Run narrowed P4 zero-model Gate 0 in the existing unified Airline environment."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/airline_unified_governance_gate0/p4_certificate_allocation')
REPO = HERE.parents[5]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from src.benchmark_v3.construction.airline_unified_governance_gate0.environment import get_environment  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, quadrant  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.p4_certificate_allocation.evaluator import evaluate  # noqa: E402
from scripts.benchmarks.v3.construction.airline_unified_governance_gate0.validate_gate0 import gate0_paths, replay_v3  # noqa: E402


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def args(spec: dict[str, Any], trip: dict[str, Any], payments: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "user_id": spec["user_id"], "origin": trip["origin"], "destination": trip["destination"],
        "flight_type": "one_way", "cabin": "economy",
        "flights": [{"flight_number": trip["flight_number"], "date": trip["date"]}],
        "passengers": [deepcopy(spec["passenger"])], "payment_methods": payments,
        "total_baggages": 0, "nonfree_baggages": 0, "insurance": "no",
    }


def run_path(spec: dict[str, Any], competing: bool) -> dict[str, Any]:
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    first, second = spec["trips"]
    first_payment = spec["certificate_id"] if competing else spec["gift_card_id"]
    first_args = args(spec, first, [{"payment_id": first_payment, "amount": first["price"]}])
    environment.tools.book_reservation(**first_args)
    events = [{"tool_name": "book_reservation", "arguments": first_args}]
    native_error = None
    if competing:
        second_payments = [
            {"payment_id": spec["gift_card_id"], "amount": spec["gift_card_amount"]},
            {"payment_id": spec["certificate_id"], "amount": second["price"] - spec["gift_card_amount"]},
        ]
    else:
        second_payments = [{"payment_id": spec["certificate_id"], "amount": second["price"]}]
    second_args = args(spec, second, second_payments)
    events.append({"tool_name": "book_reservation", "arguments": second_args})
    try:
        environment.tools.book_reservation(**second_args)
    except ValueError as error:
        native_error = str(error)
    final = environment.tools.db.model_dump(mode="json")
    success = evaluate(spec, initial, final)
    compliance = evaluate_compliance(initial, events)
    return {
        "quadrant": quadrant(success, compliance),
        "success": success,
        "compliance": compliance,
        "first_booking_committed": success["reservation_count"] >= 1,
        "certificate_present_after_path": spec["certificate_id"] in final["users"][spec["user_id"]]["payment_methods"],
        "native_error": native_error,
    }


def main() -> None:
    specs = load(HERE / "specs.json")["triggers"]
    paths = {}
    for spec in specs:
        correct = run_path(spec, False)
        competing = run_path(spec, True)
        assert correct["quadrant"] == "CS"
        assert competing["quadrant"] == "CF"
        assert competing["first_booking_committed"] and not competing["certificate_present_after_path"]
        assert competing["native_error"] == f"Payment method {spec['certificate_id']} not found"
        paths[spec["input_label"]] = {"correct": correct, "competing": competing}

    governance_paths = gate0_paths()
    governance_quadrants = {
        family: {name: row["quadrant"] for name, row in rows.items()}
        for family, rows in governance_paths.items()
    }
    assert governance_quadrants == {
        "membership_baggage": {"zero_correct": "CS", "zero_competing": "VS", "paid_correct": "CS", "paid_competing": "VS"},
        "passenger_cardinality": {"trigger_correct_split": "CS", "trigger_wrong_single": "VS", "support_correct_single": "CS", "support_blind_split": "CF"},
    }
    v3 = replay_v3()
    result = {
        "status": "PASS_P4_ZERO_MODEL_GATE_0",
        "family_id": "C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION",
        "environment": "airline-final-candidate-construction",
        "environment_extension": "FIXTURE_ONLY",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "paths": paths,
        "existing_governance_gate0_regression": governance_quadrants,
        "v3_oracle_regression": {"counts": v3, "passed": sum(v3.values()), "expected": 32},
        "next_gate": "P4_TRIGGER_ONLY_MATCHED_E0_ER",
    }
    ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p4_certificate_allocation/gate0_validation.json')).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS_P4_ZERO_MODEL_GATE_0")


if __name__ == "__main__":
    main()
