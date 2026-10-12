#!/usr/bin/env python3
"""Stage 0.5 construction checks for the concrete PB-C02 family."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[7] / 'scripts/benchmarks/v3/development/primitive_b/pb_c02/tools'))
EDITION = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from tau2.data_model.tasks import Task  # noqa: E402
from tau2.domains.airline.data_model import FlightDB  # noqa: E402
from tau2.domains.airline.tools import AirlineTools  # noqa: E402
from tau2.domains.airline.utils import AIRLINE_DB_PATH  # noqa: E402
from src.benchmark_v3.development.primitive_b.pb_c02.candidate_tasks.evaluators.evaluate_pb_c02 import expected_final_db, expected_selection, feasible_candidates


SPECS = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/primitive_b/pb_c02/candidates/task_specs.json')
TASKS = EDITION / "construction/primitive_b/pb_c02/candidate_tasks/tasks.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    specs = load(SPECS)["tasks"]
    tasks = load(TASKS)
    errors = []
    if len(specs) != 8 or len(tasks) != 8:
        errors.append("expected eight task specs and executable tasks")
    if len({row["task_id"] for row in specs}) != len(specs):
        errors.append("duplicate spec IDs")
    if {row["split"] for row in specs} != {"train_like", "held_out"}:
        errors.append("missing split")
    by_id = {row["id"]: Task.model_validate(row) for row in tasks}
    initial = FlightDB.load(AIRLINE_DB_PATH).model_dump(mode="json")
    for spec in specs:
        task_id = spec["task_id"]
        task = by_id.get(task_id)
        if task is None:
            errors.append(f"{task_id}: missing executable task")
            continue
        visible = str(task.user_scenario).lower()
        if spec["correct_flight"].lower() in visible or re.search(r"\bhat\d+\b", visible):
            errors.append(f"{task_id}: flight answer leaked to user context")
        tools = AirlineTools(FlightDB.model_validate(initial))
        reservation = tools.get_reservation_details(spec["reservation_id"])
        runtime = tools.search_direct_flight(reservation.origin, reservation.destination, spec["target_date"])
        cabin, flight = expected_selection(spec, initial)
        feasible = feasible_candidates(spec, initial, cabin) if cabin else []
        if len(runtime) < 3:
            errors.append(f"{task_id}: trivial runtime candidate set")
        if len(feasible) < 2:
            errors.append(f"{task_id}: fewer than two candidates require ranking")
        if cabin != spec["target_cabin"] or flight != spec["correct_flight"]:
            errors.append(f"{task_id}: declared answer disagrees with filter/rank/fallback result")
        expected = expected_final_db(spec, initial)
        target = expected["reservations"][spec["reservation_id"]]
        if target["flights"][0]["flight_number"] != spec["correct_flight"] or target["cabin"] != spec["target_cabin"]:
            errors.append(f"{task_id}: semantic target replay mismatch")

    if errors:
        print("FAIL PB-C02 Stage 0.5: " + "; ".join(errors))
        return 1
    print("PASS PB-C02 Stage 0.5: 8 tasks, 4 train-like/4 held-out, all runtime-derived and semantically satisfiable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
