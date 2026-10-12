#!/usr/bin/env python3
"""Zero-model Gate 0 for the Composite Capability fixtures."""

import json
import sys
from copy import deepcopy
from pathlib import Path


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/composite_capability/p5_cabin_baggage_budget')
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from src.benchmark_v3.construction.airline_unified_governance_gate0.data_model import FinalCandidateAirlineDB
from src.benchmark_v3.construction.airline_unified_governance_gate0.fixture import build_gate0_db
from src.benchmark_v3.construction.airline_unified_governance_gate0.tools import FinalCandidateAirlineTools
from src.benchmark_v3.construction.composite_capability.p5_cabin_baggage_budget.evaluator import evaluate


specs = json.loads((HERE / "specs.json").read_text())["surfaces"]


def apply(spec, *, cabin=None, passengers=True, nonfree=None):
    initial = build_gate0_db().model_dump(mode="json")
    tools = FinalCandidateAirlineTools(FinalCandidateAirlineDB.model_validate(deepcopy(initial)))
    selected = cabin or spec["expected_cabin"]
    tools.update_reservation_flights(
        reservation_id=spec["reservation_id"],
        cabin=selected,
        flights=[{"flight_number": spec["new_flight"], "date": spec["new_date"]}],
        payment_id=spec["payment_id"],
    )
    if passengers:
        tools.update_reservation_passengers(
            reservation_id=spec["reservation_id"],
            passengers=spec["replacement_passengers"],
        )
    tools.update_reservation_baggages(
        reservation_id=spec["reservation_id"],
        total_baggages=spec["requested_baggages"],
        nonfree_baggages=(
            spec["expected_nonfree_baggages"] if nonfree is None else nonfree
        ),
        payment_id=spec["payment_id"],
    )
    final = tools.db.model_dump(mode="json")
    return evaluate(spec, initial, final)


rows = []
for spec in specs:
    correct = apply(spec)
    wrong_cabin = apply(
        spec,
        cabin="business",
        nonfree=max(0, spec["expected_nonfree_baggages"] - 1),
    )
    missing_passenger = apply(spec, passengers=False)
    wrong_baggage = apply(
        spec, nonfree=max(0, spec["expected_nonfree_baggages"] - 1)
    )
    assert correct["success"]
    assert correct["total_appended_charge"] == spec["expected_total_additional"]
    assert not wrong_cabin["success"]
    assert not missing_passenger["success"]
    assert not wrong_baggage["success"]
    rows.append({
        "input_label": spec["input_label"],
        "correct_path": "CS",
        "wrong_cabin_path": "CF",
        "missing_passenger_path": "CF",
        "wrong_baggage_path": "CF",
        "expected_total_additional": spec["expected_total_additional"],
    })

result = {
    "status": "PASS_COMPOSITE_CAPABILITY_ZERO_MODEL_GATE_0",
    "surface_count": len(specs),
    "model_calls": 0,
    "formal_task_ids_allocated": 0,
    "rows": rows,
    "next_gate": "MATCHED_E0_ER_NECESSITY",
}
((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/composite_capability/p5_cabin_baggage_budget/gate0_validation.json')).write_text(json.dumps(result, indent=2) + "\n")
print(result["status"])

