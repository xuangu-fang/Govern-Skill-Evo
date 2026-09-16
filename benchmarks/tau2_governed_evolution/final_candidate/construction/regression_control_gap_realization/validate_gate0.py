#!/usr/bin/env python3
"""Zero-model Gate 0 and targeted regression detection for both lineages."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from tau2.data_model.tasks import Task  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.environment.airline import get_environment as get_formal_airline  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.environment.retail import get_environment as get_formal_retail  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.regression_control_gap_realization.environment import (  # noqa: E402
    get_airline_environment,
    get_retail_environment,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.regression_control_gap_realization.evaluator import (  # noqa: E402
    evaluate_airline,
    evaluate_retail,
)


SPECS = HERE / "specs.json"
TASKS = HERE / "tasks.json"
RESULT = HERE / "gate0_validation.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def airline_path(spec: dict[str, Any], second: str, baseline: str) -> dict[str, Any]:
    environment = get_airline_environment()
    environment.tools.db.settlement_contracts[spec["reservation_id"]].settlement_baseline = baseline
    environment.tools.update_reservation_flights(
        reservation_id=spec["reservation_id"],
        cabin="economy",
        flights=[
            {"flight_number": spec["retained_flight"], "date": spec["date"]},
            {"flight_number": second, "date": spec["date"]},
        ],
        payment_id=spec["payment_id"],
    )
    return evaluate_airline(spec, environment.tools.db.model_dump(mode="json"))


def retail_path(spec: dict[str, Any], resolution: str) -> dict[str, Any]:
    environment = get_retail_environment()
    if resolution == "return":
        environment.tools.return_delivered_order_items(
            spec["order_id"], [spec["old_item_id"]], spec["payment_id"]
        )
    else:
        environment.tools.exchange_delivered_order_items(
            spec["order_id"], [spec["old_item_id"]], [spec["new_item_id"]], spec["payment_id"]
        )
    return evaluate_retail(spec, environment.tools.db.model_dump(mode="json"))


def main() -> None:
    payload = load(SPECS)
    specs = {row["domain"]: row for row in payload["candidates"]}
    tasks = load(TASKS)
    assert len(tasks) == 2 and all(Task.model_validate(task) for task in tasks)
    assert payload["formal_task_ids_allocated"] == 0

    formal_airline = get_formal_airline().tools.db.model_dump(mode="json")
    formal_retail = get_formal_retail().tools.db.model_dump(mode="json")
    assert specs["airline"]["user_id"] not in formal_airline["users"]
    assert specs["airline"]["reservation_id"] not in formal_airline["reservations"]
    assert specs["retail"]["user_id"] not in formal_retail["users"]
    assert specs["retail"]["order_id"] not in formal_retail["orders"]

    air = specs["airline"]
    retained_correct = airline_path(air, air["preferred_exact"], "retained_historical")
    current_correct = airline_path(air, air["preferred_exact"], "complete_current")
    wrong_branch = airline_path(air, air["fallback_exact"], "retained_historical")
    wrong_destination = airline_path(air, air["preferred_alternate"], "retained_historical")
    assert retained_correct["success"] and current_correct["success"]
    assert retained_correct["observed_change_amount"] == 30
    assert current_correct["observed_change_amount"] == 80
    assert not wrong_branch["success"] and not wrong_branch["capability_success"] and wrong_branch["compliant"]
    assert not wrong_destination["success"] and wrong_destination["capability_success"] and not wrong_destination["compliant"]

    retail = specs["retail"]
    return_path = retail_path(retail, "return")
    exchange_regression = retail_path(retail, "exchange")
    assert return_path["success"]
    assert not exchange_regression["success"]

    result = {
        "status": "PASS_2_V3_GAP_CONTROL_ZERO_MODEL_GATE_0",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "fresh_entity_isolation": True,
        "airline": {
            "retained_historical_correct": retained_correct,
            "complete_current_correct": current_correct,
            "wrong_branch_regression_detected": not wrong_branch["success"],
            "alternate_destination_regression_detected": not wrong_destination["success"],
            "wrong_branch": wrong_branch,
            "wrong_destination": wrong_destination,
        },
        "retail": {
            "explicit_return_correct": return_path,
            "exchange_overgeneralization_detected": not exchange_regression["success"],
            "exchange_regression": exchange_regression,
        },
        "targeted_regressions_detected": 3,
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"])


if __name__ == "__main__":
    main()
