"""Static, tool-execution, and optional official-evaluator validation for Step 4."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)


ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage  # noqa: E402
from tau2.data_model.simulation import SimulationRun, TerminationReason  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation  # noqa: E402
from tau2.evaluator import evaluator_nl_assertions  # noqa: E402


DIRECTORY = Path(__file__).resolve().parent
MANIFEST_PATH = DIRECTORY / "airline_complex_upfront_candidates.json"
TASKS_PATH = DIRECTORY / "airline_complex_upfront_tasks.json"
CAMPAIGN_PATH = (
    Path(__file__).resolve().parents[3]
    / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
)
REQUIRED_STRUCTURES = {
    "multi_goal_completeness",
    "cross_entity_bookkeeping",
    "dependent_transaction_compilation",
    "global_all_or_nothing",
    "operation_ordering",
    "final_reconciliation",
}


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    values = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    tasks = {value["id"]: Task.model_validate(value) for value in values}
    if len(tasks) != len(values):
        raise ValueError("Duplicate Complex-Upfront task ID")
    return manifest, tasks


def _controlled_trajectory(task: Task, assertions: list[str]) -> tuple[list[Any], list[str]]:
    environment = get_environment()
    messages: list[Any] = [
        UserMessage(
            role="user",
            content=str(task.user_scenario.instructions),
        ),
        AssistantMessage(
            role="assistant",
            content=(
                "I have compiled every requested goal, dependency, constraint, "
                "payment path, and fallback into one complete transaction. May I proceed?"
            ),
        ),
        UserMessage(role="user", content="Yes, proceed with that complete transaction."),
    ]
    errors = []
    for index, action in enumerate(task.evaluation_criteria.actions or []):
        call = ToolCall(
            id=f"{task.id}-controlled-{index}",
            name=action.name,
            arguments=action.arguments,
            requestor="assistant",
        )
        messages.append(AssistantMessage(role="assistant", content=None, tool_calls=[call]))
        response = environment.get_response(call)
        messages.append(response)
        if getattr(response, "error", False):
            errors.append(f"{action.name}: {response.content}")
    messages.append(
        AssistantMessage(
            role="assistant",
            content="All requested actions are complete. " + " ".join(assertions),
        )
    )
    return messages, errors


def _official(task: Task, messages: list[Any]) -> dict[str, Any]:
    simulation = SimulationRun(
        id=f"controlled-{task.id}",
        task_id=task.id,
        start_time="2026-09-07T00:00:00",
        end_time="2026-09-07T00:01:00",
        duration=60.0,
        termination_reason=TerminationReason.AGENT_STOP,
        messages=messages,
    )
    result = evaluate_simulation(
        simulation=simulation,
        task=task,
        evaluation_type=EvaluationType.ALL,
        solo_mode=False,
        domain="airline",
    )
    return {
        "success": result.reward == 1.0,
        "reward": result.reward,
        "db_reward": result.db_check.db_reward if result.db_check else None,
        "action_checks": [item.action_match for item in result.action_checks or []],
        "nl_checks": [item.met for item in result.nl_assertions or []],
    }


def validate_suite(*, with_official: bool) -> dict[str, Any]:
    manifest, tasks = load_suite()
    if with_official:
        campaign = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
        evaluator = campaign["official_evaluator"]
        evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = evaluator[
            "nl_assertions_model"
        ]
        evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
            "temperature": evaluator["nl_assertions_temperature"]
        }
    specs = {item["task_id"]: item for item in manifest["tasks"]}
    all_structures = {value for item in specs.values() for value in item["structures"]}
    suite_checks = {
        "selection_frozen": manifest["selection_status"]
        == "frozen_before_empty_skill_rollouts",
        "selection_ignores_outcomes": manifest["empty_rollout_outcomes_used_for_selection"]
        is False,
        "six_unique_tasks": len(specs) == len(tasks) == 6,
        "task_ids_match": set(specs) == set(tasks),
        "structure_coverage": REQUIRED_STRUCTURES <= all_structures,
        "three_calibration_seeds": len(manifest["calibration_seeds"]) == 3,
        "three_rollout_seeds": len(manifest["rollout_seeds"]) == 3,
    }
    results = {}
    for task_id, spec in specs.items():
        task = tasks[task_id]
        instructions = task.user_scenario.instructions
        instruction_text = " ".join(
            [
                instructions.reason_for_call,
                instructions.known_info,
                instructions.task_instructions,
            ]
        )
        messages, tool_errors = _controlled_trajectory(task, spec["nl_assertions"])
        checks = {
            "strict_upfront_contract": all(
                re.search(pattern, instruction_text, re.IGNORECASE)
                for pattern in spec["initial_required_regexes"]
            ),
            "high_execution_complexity": len(spec["goals"]) >= 4
            and len(spec["dependencies"]) >= 3,
            "not_policy_memorization_only": len(spec["structures"]) >= 3,
            "has_dependency_graph": bool(spec["dependencies"]),
            "policy_and_tool_claims_recorded": bool(spec["evaluator_target"]),
            "reference_tools_execute": not tool_errors,
            "revision_transformable": all(
                spec["revision_transformability"].get(key)
                for key in ("transformable", "potential_revision_trigger", "p0", "p1")
            ),
            "same_future_initial_db_and_target": spec["revision_transformability"][
                "same_initial_db"
            ]
            and spec["revision_transformability"]["same_final_target"],
        }
        official = _official(task, messages) if with_official and not tool_errors else None
        if official is not None:
            checks["controlled_official_success"] = official["success"]
        results[task_id] = {
            "passed": all(checks.values()),
            "checks": checks,
            "tool_errors": tool_errors,
            "official": official,
        }
    return {
        "with_official": with_official,
        "passed": all(suite_checks.values())
        and all(item["passed"] for item in results.values()),
        "suite_checks": suite_checks,
        "tasks": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-official", action="store_true")
    args = parser.parse_args()
    result = validate_suite(with_official=args.with_official)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
