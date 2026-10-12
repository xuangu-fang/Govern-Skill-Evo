#!/usr/bin/env python3
"""Build the admitted PB-C02 tasks from construction-only specifications."""

from __future__ import annotations

import json
import sys
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[7] / 'scripts/benchmarks/v3/development/primitive_b/pb_c02/tools'))
EDITION = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')
REPO = EDITION.parents[3]
TAU2 = REPO / "external/tau2-bench"
sys.path.insert(0, str(TAU2 / "src"))

from tau2.data_model.tasks import (  # noqa: E402
    Action,
    Description,
    EvaluationCriteria,
    RewardType,
    StructuredUserInstructions,
    Task,
    UserScenario,
)
from tau2.domains.airline.data_model import FlightDB  # noqa: E402
from tau2.domains.airline.tools import AirlineTools  # noqa: E402
from tau2.domains.airline.utils import AIRLINE_DB_PATH  # noqa: E402


SPECS = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/primitive_b/pb_c02/candidates/task_specs.json')
CANDIDATE_TASKS = EDITION / "construction/primitive_b/pb_c02/candidate_tasks"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    payload = load(SPECS)
    base_db = FlightDB.load(AIRLINE_DB_PATH)
    tools = AirlineTools(base_db)
    tasks = []
    manifest_rows = []
    for spec in payload["tasks"]:
        reservation = tools.get_reservation_details(spec["reservation_id"])
        if reservation.user_id != spec["user_id"]:
            raise ValueError(f"{spec['task_id']}: reservation owner mismatch")
        candidates = tools.search_direct_flight(
            reservation.origin, reservation.destination, spec["target_date"]
        )
        candidate_ids = {candidate.flight_number for candidate in candidates}
        declared = set(spec["feasible_flights"] + spec["tempting_infeasible_flights"])
        if spec["correct_flight"] not in candidate_ids or not declared <= candidate_ids:
            raise ValueError(f"{spec['task_id']}: declared candidate missing from runtime search")
        correct = next(c for c in candidates if c.flight_number == spec["correct_flight"])
        if correct.available_seats[spec["target_cabin"]] < len(reservation.passengers):
            raise ValueError(f"{spec['task_id']}: correct candidate lacks capacity")

        action_args = {
            "reservation_id": spec["reservation_id"],
            "cabin": spec["target_cabin"],
            "flights": [{"flight_number": spec["correct_flight"], "date": spec["target_date"]}],
            "payment_id": spec["payment_id"],
        }
        task = Task(
            id=spec["task_id"],
            description=Description(
                purpose="Evaluate constrained runtime flight-candidate selection.",
                relevant_policies="Native tau2 Airline policy only.",
                notes="PB-C02 original Filter-Rank-Fallback baseline.",
            ),
            user_scenario=UserScenario(
                persona="The user is the reservation owner and communicates naturally and consistently.",
                instructions=StructuredUserInstructions(
                    domain="airline",
                    reason_for_call=spec["reason_for_call"],
                    known_info=(
                        f"Your user ID is {spec['user_id']}. Your reservation ID is "
                        f"{spec['reservation_id']}. You can use the saved {spec['payment_label']} "
                        "for any charge or refund."
                    ),
                    unknown_info="You do not know which flight number satisfies the request or what candidates the search will return.",
                    task_instructions=(
                        spec["interaction_instructions"]
                        + " After confirming a matching proposal, remain in the conversation "
                        "until the agent reports that the reservation mutation has completed; "
                        "do not emit the stop token merely because you confirmed the proposal."
                    ),
                ),
            ),
            initial_state=None,
            evaluation_criteria=EvaluationCriteria(
                actions=[Action(action_id=f"{spec['task_id']}_target", name="update_reservation_flights", arguments=action_args)],
                communicate_info=[],
                nl_assertions=None,
                reward_basis=[RewardType.DB],
            ),
        )
        tasks.append(task.model_dump(mode="json", exclude_none=True))
        manifest_rows.append({
            "task_id": spec["task_id"],
            "split": spec["split"],
            "geometry": spec["geometry"],
        })

    CANDIDATE_TASKS.mkdir(parents=True, exist_ok=True)
    (CANDIDATE_TASKS / "tasks.json").write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "edition": "phase_v3_day34",
        "family": payload["family"],
        "task_count": len(tasks),
        "status": "REJECTED_TOO_EASY",
        "task_file": "construction/primitive_b/pb_c02/candidate_tasks/tasks.json",
        "construction_source": "construction/primitive_b/pb_c02/candidates/task_specs.json",
        "tasks": manifest_rows,
    }
    (CANDIDATE_TASKS / "task_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Built {len(tasks)} PB-C02 tasks")


if __name__ == "__main__":
    main()
