"""Materialize the frozen Step 4S Phase-A mechanism tasks."""

from __future__ import annotations

import json
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
MANIFEST_PATH = DIRECTORY / "airline_phase_a_mechanism_candidates.json"
OUTPUT_PATH = DIRECTORY / "airline_phase_a_mechanism_tasks.json"


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
                    "purpose": "Step 4S strictly-upfront procedural mechanism expansion.",
                    "relevant_policies": "Original tau2 Airline Policy only.",
                    "notes": f"Family {spec['family']}; frozen before Empty rollout.",
                },
                "user_scenario": {
                    "persona": (
                        "The user is the airline customer. The complete stable business "
                        "rule is stated in the first turn and never revised."
                    ),
                    "instructions": {
                        "domain": "airline",
                        "reason_for_call": f"Execute a strictly upfront {spec['family']} request.",
                        "known_info": spec["scenario"]["known_info"],
                        "unknown_info": None,
                        "task_instructions": (
                            "Your first response must be the customer's complete request and "
                            "must literally state the user id, every named reservation id, all "
                            "selection or mapping rules, protected state, payment information, "
                            "and the requirement for explicit confirmation after a complete "
                            "proposal. Do not expose any oracle flight choice before the agent "
                            "discovers it from tools. "
                            + spec["scenario"]["task_instructions"]
                            + " After confirmation, do not emit ###STOP### until the agent "
                            "reports all writes and final reconciliation complete."
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
        json.dumps(build_tasks(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
