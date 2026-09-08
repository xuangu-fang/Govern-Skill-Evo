"""Build and freeze the two Step 4W-S5 canonical-context tasks."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.tau2_governed_evolution.cardinality_propagation.scan_cardinality_candidates import scan


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = DIRECTORY / "cardinality_manifest.json"
TASKS_PATH = DIRECTORY / "cardinality_tasks.json"
SELECTED_RESERVATIONS = ("K67C4W", "GJLSXX")


def _spec(candidate: dict, rank: int) -> dict:
    task_id = f"airline_s5_{candidate['reservation_id'].lower()}_cardinality"
    instructions = (
        "You are the airline customer. In your first response, state the complete final request: "
        f"your user id is {candidate['user_id']} and reservation is {candidate['reservation_id']}. "
        f"You want everyone on the reservation switched to {candidate['target_flight']} on {candidate['date']} "
        f"in the existing {candidate['cabin']} cabin, but only if the total additional charge for the entire "
        f"reservation is no more than ${candidate['threshold']}. If it is above ${candidate['threshold']}, "
        "leave the reservation unchanged. Require the same route, passengers, cabin, baggage, insurance, and "
        f"all other state to remain unchanged. If a change is made, use {candidate['payment_id']}. Ask the agent "
        "to report the old fare per passenger, new fare per passenger, passenger count, total additional charge, "
        "and resulting decision. These goals and constraints are final; never revise the target, threshold, or "
        "scope. If the agent proposes a change it claims is within the limit, explicitly confirm the complete "
        "proposal; otherwise acknowledge the no-change decision. Do not perform arithmetic for the agent and do "
        "not reveal the expected total additional charge in your first response."
    )
    return {
        "task_id": task_id,
        "domain": "airline",
        "mechanism_id": "S5",
        "mechanism_source": "CANONICAL_REASONING_WEAKNESS",
        "source_state": {
            "user_id": candidate["user_id"],
            "reservation_id": candidate["reservation_id"],
        },
        "candidate_rank": rank,
        "candidate": candidate,
        "scenario": {
            "known_info": (
                f"You are user {candidate['user_id']}; reservation {candidate['reservation_id']}; "
                f"payment method {candidate['payment_id']}."
            ),
            "task_instructions": instructions,
        },
        "reads": [
            {"name": "get_user_details", "arguments": {"user_id": candidate["user_id"]}},
            {"name": "get_reservation_details", "arguments": {"reservation_id": candidate["reservation_id"]}},
            {
                "name": "search_direct_flight",
                "arguments": {
                    "origin": candidate["route"]["origin"],
                    "destination": candidate["route"]["destination"],
                    "date": candidate["date"],
                },
            },
        ],
        "wrong_update": {
            "name": "update_reservation_flights",
            "arguments": {
                "reservation_id": candidate["reservation_id"],
                "cabin": candidate["cabin"],
                "flights": [{"flight_number": candidate["target_flight"], "date": candidate["date"]}],
                "payment_id": candidate["payment_id"],
            },
        },
        "correct_branch": "DO_NOT_MODIFY",
        "admission_status": "FROZEN_BEFORE_EMPTY_ROLLOUT",
    }


def build() -> dict:
    scanned = scan()
    by_reservation = {row["reservation_id"]: row for row in scanned["candidates"]}
    missing = set(SELECTED_RESERVATIONS) - set(by_reservation)
    if missing:
        raise ValueError(f"Frozen reservations missing from bounded scan: {sorted(missing)}")
    specs = [_spec(by_reservation[rid], rank) for rank, rid in enumerate(SELECTED_RESERVATIONS, 1)]
    tasks = []
    for spec in specs:
        candidate = spec["candidate"]
        tasks.append(
            {
                "id": spec["task_id"],
                "description": {
                    "purpose": "Step 4W-S5 canonical Airline cardinality-propagation probe",
                    "relevant_policies": "Full canonical tau2 Airline Policy",
                    "notes": "No operational knowledge ablation; frozen before Empty rollout",
                },
                "user_scenario": {
                    "persona": "Customer with complete stable intent",
                    "instructions": {
                        "domain": "airline",
                        "reason_for_call": "Apply a reservation-level budget gate to one explicitly named replacement flight",
                        "known_info": spec["scenario"]["known_info"],
                        "unknown_info": None,
                        "task_instructions": spec["scenario"]["task_instructions"],
                    },
                },
                "initial_state": None,
                "evaluation_criteria": {
                    "actions": [],
                    "env_assertions": None,
                    "communicate_info": [],
                    "nl_assertions": [
                        f"The assistant reports that {candidate['old_fare_per_person']} dollars per passenger on the current flight and {candidate['new_fare_per_person']} dollars per passenger on {candidate['target_flight']} produce a total additional charge of {candidate['total_delta']} dollars for {candidate['passenger_count']} passengers, exceeding the {candidate['threshold']} dollar reservation limit, so reservation {candidate['reservation_id']} remains unchanged."
                    ],
                    "reward_basis": ["DB", "NL_ASSERTION"],
                },
            }
        )
    TASKS_PATH.write_text(json.dumps(tasks, indent=2) + "\n")
    manifest = {
        "schema_version": "step4w_s5_1.0",
        "benchmark_id": "airline_cardinality_propagation_step4w_s5",
        "mechanism": {
            "id": "S5",
            "name": "airline_cardinality_propagation",
            "mechanism_source": "CANONICAL_REASONING_WEAKNESS",
            "agent_view": "FULL_CANONICAL",
        },
        "selection_status": "frozen_before_empty_rollout",
        "rollout_outcomes_used_for_selection": False,
        "selected_reservations": list(SELECTED_RESERVATIONS),
        "user_sanity_seed": 970,
        "rollout_seeds": [971, 972, 973],
        "tasks": specs,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"tasks": len(tasks), "manifest": str(MANIFEST_PATH), "task_file": str(TASKS_PATH)}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
