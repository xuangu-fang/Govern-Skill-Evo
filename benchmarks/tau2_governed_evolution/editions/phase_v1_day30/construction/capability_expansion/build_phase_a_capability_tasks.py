"""Materialize the frozen Step 4T cross-domain task pool."""

from __future__ import annotations

import json
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
MANIFEST_PATH = DIRECTORY / "phase_a_capability_candidates.json"
OUTPUT_PATH = DIRECTORY / "phase_a_capability_tasks.json"


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
                    "purpose": "Step 4T strictly-upfront cross-domain capability expansion.",
                    "relevant_policies": f"Original tau2 {spec['domain'].title()} Policy only.",
                    "notes": f"Family {spec['family']}; frozen before Empty rollout.",
                },
                "user_scenario": {
                    "persona": "The customer states the complete stable business request in the first turn and never revises it.",
                    "instructions": {
                        "domain": spec["domain"],
                        "reason_for_call": f"Execute a strictly upfront {spec['family']} request.",
                        "known_info": spec["scenario"]["known_info"],
                        "unknown_info": None,
                        "task_instructions": (
                            "Your first response must state all goals, constraints, tie-breaks, protected state, scope, payment information, and the confirmation requirement. "
                            "Do not disclose oracle flight or item identifiers before the agent discovers them through tools. "
                            + spec["scenario"]["task_instructions"]
                            + " After confirmation, do not emit ###STOP### until the agent reports the complete final result."
                        ),
                    },
                },
                "initial_state": None,
                "evaluation_criteria": {
                    "actions": actions,
                    "env_assertions": None,
                    "communicate_info": [],
                    "nl_assertions": spec["nl_assertions"],
                    "reward_basis": ["DB", "NL_ASSERTION"],
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
