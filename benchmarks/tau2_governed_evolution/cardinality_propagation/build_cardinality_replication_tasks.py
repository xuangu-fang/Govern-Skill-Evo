"""Build the bounded Step 4W-S5-R unscaffolded replication tasks."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.tau2_governed_evolution.cardinality_propagation.build_cardinality_tasks import (
    PROJECT_ROOT,
)


DIRECTORY = Path(__file__).resolve().parent
SOURCE_MANIFEST_PATH = DIRECTORY / "cardinality_manifest.json"
MANIFEST_PATH = DIRECTORY / "cardinality_replication_manifest.json"
TASKS_PATH = DIRECTORY / "cardinality_replication_tasks.json"


def _instructions(candidate: dict) -> str:
    return (
        "You are the airline customer. In your first response, state the complete final request: "
        f"your user id is {candidate['user_id']} and reservation is {candidate['reservation_id']}. "
        f"You want everyone on the reservation switched to {candidate['target_flight']} on {candidate['date']} "
        f"in the existing {candidate['cabin']} cabin, but only if the total additional charge for the entire "
        f"reservation is no more than ${candidate['threshold']}. If it is above ${candidate['threshold']}, "
        "leave the reservation unchanged. Require the same route, passengers, cabin, baggage, insurance, and "
        f"all other state to remain unchanged. If a change is made, use {candidate['payment_id']}. These goals "
        "and constraints are final; never revise the target, threshold, or scope. If the agent proposes a change "
        "it claims is within the limit, explicitly confirm the complete proposal; otherwise acknowledge the "
        "no-change decision. Do not perform arithmetic for the agent and do not reveal any fare calculation or "
        "the expected total additional charge."
    )


def build() -> dict:
    source = json.loads(SOURCE_MANIFEST_PATH.read_text())
    specs = []
    tasks = []
    for original in source["tasks"]:
        candidate = original["candidate"]
        task_id = f"airline_s5r_{candidate['reservation_id'].lower()}_unscaffolded"
        scenario = {
            "known_info": original["scenario"]["known_info"],
            "task_instructions": _instructions(candidate),
        }
        spec = {
            **original,
            "task_id": task_id,
            "mechanism_id": "S5-R",
            "scenario": scenario,
            "replicates_task_id": original["task_id"],
            "prompt_intervention": {
                "only_change": "remove_explicit_cardinality_calculation_checklist",
                "removed_user_visible_fields": [
                    "old fare per passenger",
                    "new fare per passenger",
                    "passenger count",
                    "calculation breakdown",
                ],
                "evaluation_metadata_unchanged": True,
            },
            "admission_status": "FROZEN_UNSCAFFOLDED_REPLICATION",
        }
        specs.append(spec)
        tasks.append(
            {
                "id": task_id,
                "description": {
                    "purpose": "Step 4W-S5-R unscaffolded cardinality replication",
                    "relevant_policies": "Full canonical tau2 Airline Policy",
                    "notes": "Same state, target, threshold, and evaluator as S5; only the user-visible calculation checklist is removed",
                },
                "user_scenario": {
                    "persona": "Customer with complete stable intent",
                    "instructions": {
                        "domain": "airline",
                        "reason_for_call": "Apply a reservation-level budget gate to one explicitly named replacement flight",
                        "known_info": scenario["known_info"],
                        "unknown_info": None,
                        "task_instructions": scenario["task_instructions"],
                    },
                },
                "initial_state": None,
                "evaluation_criteria": {
                    "actions": [],
                    "env_assertions": None,
                    "communicate_info": [],
                    "nl_assertions": [
                        f"The assistant reports that {candidate['old_fare_per_person']} dollars per passenger on the current flight and "
                        f"{candidate['new_fare_per_person']} dollars per passenger on {candidate['target_flight']} produce a total additional "
                        f"charge of {candidate['total_delta']} dollars for {candidate['passenger_count']} passengers, exceeding the "
                        f"{candidate['threshold']} dollar reservation limit, so reservation {candidate['reservation_id']} remains unchanged."
                    ],
                    "reward_basis": ["DB", "NL_ASSERTION"],
                },
            }
        )

    TASKS_PATH.write_text(json.dumps(tasks, indent=2) + "\n")
    manifest = {
        "schema_version": "step4w_s5r_1.0",
        "benchmark_id": "airline_cardinality_unscaffolded_replication_step4w_s5r",
        "mechanism": {
            "id": "S5-R",
            "name": "airline_cardinality_propagation_unscaffolded_replication",
            "mechanism_source": "CANONICAL_REASONING_WEAKNESS",
            "agent_view": "FULL_CANONICAL",
        },
        "controlled_difference": "user_visible_reasoning_scaffold_removed",
        "source_manifest": str(SOURCE_MANIFEST_PATH.relative_to(PROJECT_ROOT)),
        "state_target_threshold_evaluator_unchanged": True,
        "rollout_seeds": source["rollout_seeds"],
        "tasks": specs,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"tasks": len(tasks), "manifest": str(MANIFEST_PATH), "task_file": str(TASKS_PATH)}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
