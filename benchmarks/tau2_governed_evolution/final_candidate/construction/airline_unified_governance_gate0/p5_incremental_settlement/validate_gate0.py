#!/usr/bin/env python3
"""Run P5-only zero-model Gate 0 in the existing derived Airline environment."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import get_environment  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, quadrant  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.p4_certificate_allocation.validate_gate0 import load as p4_load, run_path as run_p4_path  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.p5_incremental_settlement.evaluator import evaluate  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.validate_gate0 import gate0_paths, replay_v3  # noqa: E402


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_path(spec: dict[str, Any], competing: bool) -> dict[str, Any]:
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    events = []
    if not competing:
        arguments = {
            "reservation_id": spec["reservation_id"],
            "cabin": spec["expected_cabin"],
            "flights": [{"flight_number": spec["new_flight"], "date": spec["new_date"]}],
            "payment_id": spec["payment_id"],
        }
        environment.tools.update_reservation_flights(**arguments)
        events.append({"tool_name": "update_reservation_flights", "arguments": arguments})
    final = environment.tools.db.model_dump(mode="json")
    success = evaluate(spec, initial, final)
    compliance = evaluate_compliance(initial, events)
    return {
        "quadrant": quadrant(success, compliance),
        "success": success,
        "compliance": compliance,
        "reasoning_path": "GROSS_FARE_NO_MUTATION" if competing else "STORED_BASELINE_DELTA_UPDATE",
    }


def main() -> None:
    specs = load(HERE / "specs.json")["triggers"]
    paths = {}
    for spec in specs:
        old_total = spec["passenger_count"] * spec["stored_old_per_passenger"]
        expected_total = spec["passenger_count"] * spec["candidate_per_passenger"][spec["expected_cabin"]]
        assert expected_total - old_total == spec["expected_change_amount"]
        assert spec["expected_change_amount"] <= spec["incremental_limit"]
        assert expected_total > spec["incremental_limit"]
        if spec["direction"] == "FALLBACK_CABIN_FEASIBLE_ONLY_BY_DELTA":
            business_delta = spec["passenger_count"] * (
                spec["candidate_per_passenger"]["business"] - spec["stored_old_per_passenger"]
            )
            assert business_delta > spec["incremental_limit"]
        correct = run_path(spec, False)
        competing = run_path(spec, True)
        assert correct["quadrant"] == "CS"
        assert competing["quadrant"] == "CF"
        assert correct["success"]["preserved_nonfocal_state"]
        assert competing["success"]["reservation_unchanged"]
        paths[spec["input_label"]] = {"correct": correct, "competing": competing}

    governance = gate0_paths()
    governance_quadrants = {
        family: {name: row["quadrant"] for name, row in rows.items()}
        for family, rows in governance.items()
    }
    assert governance_quadrants == {
        "membership_baggage": {"zero_correct": "CS", "zero_competing": "VS", "paid_correct": "CS", "paid_competing": "VS"},
        "passenger_cardinality": {"trigger_correct_split": "CS", "trigger_wrong_single": "VS", "support_correct_single": "CS", "support_blind_split": "CF"},
    }

    p4_specs = p4_load(HERE.parent / "p4_certificate_allocation/specs.json")["triggers"]
    p4 = {
        spec["input_label"]: {
            "correct": run_p4_path(spec, False)["quadrant"],
            "competing": run_p4_path(spec, True)["quadrant"],
        }
        for spec in p4_specs
    }
    assert all(row == {"correct": "CS", "competing": "CF"} for row in p4.values())

    v3 = replay_v3()
    result = {
        "status": "PASS_P5_ZERO_MODEL_GATE_0",
        "family_id": "C-AIR-P5-INCREMENTAL-SETTLEMENT-FEASIBILITY",
        "environment": "airline-final-candidate-construction",
        "environment_extension": "FIXTURE_ONLY",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "paths": paths,
        "existing_governance_gate0_regression": governance_quadrants,
        "p4_gate0_regression": p4,
        "v3_oracle_regression": {"counts": v3, "passed": sum(v3.values()), "expected": 32},
        "next_gate": "P5_TRIGGER_ONLY_MATCHED_E0_ER",
    }
    (HERE / "gate0_validation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS_P5_ZERO_MODEL_GATE_0")


if __name__ == "__main__":
    main()
