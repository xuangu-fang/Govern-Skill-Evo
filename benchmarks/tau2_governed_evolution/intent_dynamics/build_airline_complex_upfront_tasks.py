"""Materialize the pre-registered Complex-Upfront tasks from native Airline targets."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = DIRECTORY / "airline_complex_upfront_candidates.json"
OUTPUT_PATH = DIRECTORY / "airline_complex_upfront_tasks.json"
NATIVE_TASKS_PATH = (
    PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/airline/tasks.json"
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_tasks() -> list[dict[str, Any]]:
    manifest = _load(MANIFEST_PATH)
    native = {item["id"]: item for item in _load(NATIVE_TASKS_PATH)}
    tasks = []
    for spec in manifest["tasks"]:
        source = native[spec["source_task_id"]]
        actions_by_id = {
            action["action_id"]: action
            for action in source["evaluation_criteria"]["actions"]
        }
        actions = []
        for index, source_action_id in enumerate(spec["source_action_ids"]):
            action = deepcopy(actions_by_id[source_action_id])
            action["action_id"] = f"{spec['task_id']}_target_{index}"
            action["requestor"] = "assistant"
            actions.append(action)
        tasks.append(
            {
                "id": spec["task_id"],
                "description": {
                    "purpose": (
                        "Complex-Upfront Phase-A probe for static transaction "
                        "compilation under stable intent."
                    ),
                    "relevant_policies": (
                        "Original tau2 Airline Policy; no added or modified rule."
                    ),
                    "notes": (
                        f"Materialized from native task {spec['source_task_id']} "
                        "before Empty-Skill rollout calibration."
                    ),
                },
                "user_scenario": {
                    "persona": (
                        "The user is a concise customer speaking to an airline "
                        "service agent and never adopts the agent role. After explicitly "
                        "confirming a complete proposal, the user remains active and must "
                        "not emit ###STOP### until the agent reports that every write and "
                        "the requested final reconciliation are complete."
                    ),
                    "instructions": {
                        "domain": "airline",
                        "reason_for_call": spec["scenario"]["reason_for_call"],
                        "known_info": spec["scenario"]["known_info"],
                        "unknown_info": None,
                        "task_instructions": spec["scenario"]["task_instructions"],
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
