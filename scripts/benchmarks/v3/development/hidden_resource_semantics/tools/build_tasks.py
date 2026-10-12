#!/usr/bin/env python3
"""Materialize the Hidden Single-Use Resource Semantics Pilot tasks."""

from __future__ import annotations

import json
import sys
from pathlib import Path


DATA_ROOT = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/hidden_resource_semantics')
EDITION = DATA_ROOT.parents[1]
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
from tau2.domains.airline.utils import AIRLINE_DB_PATH  # noqa: E402


SPECS = DATA_ROOT / "candidates/task_specs.json"
CANDIDATE_TASKS = EDITION / "construction/hidden_resource_semantics/candidate_tasks"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def booking_args(spec: dict, transaction: dict, payment_id: str, passenger: dict) -> dict:
    return {
        "user_id": spec["user_id"],
        "origin": transaction["origin"],
        "destination": transaction["destination"],
        "flight_type": "one_way",
        "cabin": transaction["cabin"],
        "flights": [{"flight_number": transaction["flight_number"], "date": transaction["date"]}],
        "passengers": [passenger],
        "payment_methods": [{"payment_id": payment_id, "amount": transaction["price"]}],
        "total_baggages": 0,
        "nonfree_baggages": 0,
        "insurance": "no",
    }


def main() -> None:
    payload = load(SPECS)
    db = FlightDB.load(AIRLINE_DB_PATH)
    tasks = []
    manifest_rows = []
    for spec in payload["tasks"]:
        user = db.users[spec["user_id"]]
        passenger = {
            "first_name": user.name.first_name,
            "last_name": user.name.last_name,
            "dob": user.dob,
        }
        actions = [
            Action(
                action_id=f"{spec['task_id']}_booking_{index + 1}",
                name="book_reservation",
                arguments=booking_args(spec, transaction, spec["valid_allocation"][index], passenger),
            )
            for index, transaction in enumerate(spec["transactions"])
        ]
        task = Task(
            id=spec["task_id"],
            description=Description(
                purpose="Evaluate allocation of a hidden single-use payment resource across required bookings.",
                relevant_policies="Native Airline booking policy with the certificate remainder sentence removed from Agent-visible context only.",
                notes=f"Role: {spec['role']}. Construction and evaluator metadata are not Agent-visible.",
            ),
            user_scenario=UserScenario(
                persona="The caller is the account owner and wants every explicitly requested booking completed.",
                instructions=StructuredUserInstructions(
                    domain="airline",
                    reason_for_call=spec["request"],
                    known_info=f"Your user ID is {spec['user_id']}. You are booking only for yourself.",
                    unknown_info=(
                        "You do not know the exact fares or internal payment identifiers until the agent checks the tools. "
                        "You do not know or explain how certificate value behaves after redemption."
                    ),
                    task_instructions=(
                        "State the complete request naturally. Do not prescribe a payment allocation or explain certificate semantics. "
                        "If asked about certificate reuse, say you do not know and ask the agent to use the available tools. "
                        "Confirm a proposal only when it includes every requested booking, no bags, no insurance, and charges that do not "
                        "exceed the methods' starting displayed values. Confirmation must not reveal whether a certificate can be reused. "
                        "After confirmation, remain until the agent reports all requested bookings completed; do not stop after only one."
                    ),
                ),
            ),
            initial_state=None,
            evaluation_criteria=EvaluationCriteria(
                actions=actions,
                communicate_info=[],
                nl_assertions=None,
                reward_basis=[RewardType.DB],
            ),
        )
        tasks.append(task.model_dump(mode="json", exclude_none=True))
        manifest_rows.append({
            "task_id": spec["task_id"],
            "role": spec["role"],
            "transaction_count": len(spec["transactions"]),
            "surface": spec["surface"],
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
        "task_file": "construction/hidden_resource_semantics/candidate_tasks/tasks.json",
        "construction_source": "construction/hidden_resource_semantics/candidates/task_specs.json",
        "roles": {"CAPABILITY_CORE": 4, "PROTECTED_CONTROL": 2, "HELD_OUT_TRANSFER": 2},
        "tasks": manifest_rows,
    }
    (CANDIDATE_TASKS / "task_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Built {len(tasks)} Hidden Resource Semantics tasks")


if __name__ == "__main__":
    main()
