"""Materialize the frozen Step 4R deep-dependency tasks."""

from __future__ import annotations

import json
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
MANIFEST_PATH = DIRECTORY / "airline_deep_dependency_candidates.json"
OUTPUT_PATH = DIRECTORY / "airline_deep_dependency_tasks.json"


def build_tasks() -> list[dict]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    tasks = []
    for spec in manifest["tasks"]:
        actions = [
            {
                "action_id": f"{spec['task_id']}_target_{index}",
                "requestor": "assistant",
                **action,
            }
            for index, action in enumerate(spec["oracle"]["actions"])
        ]
        tasks.append(
            {
                "id": spec["task_id"],
                "description": {
                    "purpose": "Step 4R strictly-upfront deep dependency-coupling pilot.",
                    "relevant_policies": "Original tau2 Airline Policy only.",
                    "notes": f"Frozen before Empty rollout; source state {spec['source_state']['source_task_id']}.",
                },
                "user_scenario": {
                    "persona": (
                        "The user is the airline customer, never the agent. The user "
                        "states the complete conditional rule in the first turn, confirms "
                        "only a complete proposal, and does not stop before final reconciliation."
                    ),
                    "instructions": {
                        "domain": "airline",
                        "reason_for_call": spec["scenario"]["reason_for_call"],
                        "known_info": spec["scenario"]["known_info"],
                        "unknown_info": None,
                        "task_instructions": (
                            "Your first response must be the customer's complete request, "
                            "not an offer to help or a request for identity. It must literally "
                            "state the user id and every reservation id from known_info, every "
                            "date, threshold, branch, fallback, payment rule, protected invariant, "
                            "and that you will explicitly confirm only after the complete proposal. "
                            + spec["scenario"]["task_instructions"]
                            + " After explicit confirmation, do not emit ###STOP###; wait until "
                            "the agent reports all writes and final reconciliation complete."
                        ),
                    },
                },
                "initial_state": None,
                "evaluation_criteria": {
                    "actions": actions,
                    "env_assertions": None,
                    "communicate_info": [],
                    "nl_assertions": spec["nl_assertions"],
                    "reward_basis": ["DB", "COMMUNICATE"],
                },
            }
        )
    return tasks


def main() -> None:
    OUTPUT_PATH.write_text(
        json.dumps(build_tasks(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
