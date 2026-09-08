"""Build the frozen Step 4V tasks and agent-visible partial policy."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = DIRECTORY / "transition_probe_candidates.json"
TASKS_PATH = DIRECTORY / "transition_probe_tasks.json"
CANONICAL_POLICY_PATH = PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/retail/policy.md"
PARTIAL_POLICY_PATH = DIRECTORY / "retail_transition_partial_policy.md"

FULL_TRANSITION_CLAUSE = (
    "This action can only be called once, and will change the order status to 'pending (items modifed)'. "
    "The agent will not be able to modify or cancel the order anymore. So you must confirm all the details "
    "are correct and be cautious before taking this action. In particular, remember to remind the customer "
    "to confirm they have provided all the items they want to modify."
)
PARTIAL_TRANSITION_CLAUSE = (
    "This action can only be called once. You must confirm all the details are correct and be cautious "
    "before taking this action. In particular, remember to remind the customer to confirm they have "
    "provided all the items they want to modify."
)
FORBIDDEN_PATTERNS = (
    r"pending \(items modifed\)",
    r"not be able to modify or cancel",
    r"can no longer be modified",
    r"closes? (?:later|future|subsequent)",
    r"item mutation.*(?:last|after).*order",
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_partial_policy(canonical: str) -> str:
    if canonical.count(FULL_TRANSITION_CLAUSE) != 1:
        raise ValueError("canonical Retail transition clause drifted")
    partial = canonical.replace(FULL_TRANSITION_CLAUSE, PARTIAL_TRANSITION_CLAUSE)
    hits = [pattern for pattern in FORBIDDEN_PATTERNS if re.search(pattern, partial, re.I)]
    if hits:
        raise ValueError(f"partial policy leaks hidden transition: {hits}")
    return partial


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
            for index, action in enumerate(spec["oracle"]["good_order"])
        ]
        tasks.append(
            {
                "id": spec["task_id"],
                "description": {
                    "purpose": "Step 4V strictly-upfront latent transition semantics probe.",
                    "relevant_policies": "Original tau2 Retail Policy; agent view varies by condition.",
                    "notes": f"{spec['variant']}; frozen before model rollouts.",
                },
                "user_scenario": {
                    "persona": "The customer states a complete stable final-state request and never supplies an execution recipe.",
                    "instructions": {
                        "domain": "retail",
                        "reason_for_call": "Execute a strictly upfront multi-mutation pending-order request.",
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
                    "reward_basis": ["DB", "NL_ASSERTION"],
                },
            }
        )
    return tasks


def build() -> dict[str, str]:
    canonical = CANONICAL_POLICY_PATH.read_text(encoding="utf-8")
    partial = build_partial_policy(canonical)
    tasks = build_tasks()
    PARTIAL_POLICY_PATH.write_text(partial, encoding="utf-8")
    TASKS_PATH.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "canonical_policy_sha256": sha256_text(canonical),
        "partial_policy_sha256": sha256_text(partial),
        "tasks": str(len(tasks)),
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
