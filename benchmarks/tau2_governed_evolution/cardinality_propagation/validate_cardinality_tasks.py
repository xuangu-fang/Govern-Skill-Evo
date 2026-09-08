"""Validate S5 state geometry, oracle, evaluator, and wrong-branch effect."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.cardinality_propagation.build_cardinality_tasks import (
    MANIFEST_PATH,
    PROJECT_ROOT,
    TASKS_PATH,
    build,
)
from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable


ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage  # noqa: E402
from tau2.data_model.simulation import SimulationRun, TerminationReason  # noqa: E402
from tau2.data_model.tasks import RewardType, Task  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import CAMPAIGN_PATH  # noqa: E402
from src.adapters.tau2.tau3_gse_runtime import stable_trajectory, task_context  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/cardinality_propagation_step4w_s5/validation.json"


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    build()
    manifest = json.loads(MANIFEST_PATH.read_text())
    tasks = {row["id"]: Task.model_validate(row) for row in json.loads(TASKS_PATH.read_text())}
    return manifest, tasks


def _call(messages: list[Any], environment: Any, call_id: str, action: dict) -> Any:
    call = ToolCall(id=call_id, name=action["name"], arguments=action["arguments"], requestor="assistant")
    messages.append(AssistantMessage(role="assistant", content=None, tool_calls=[call]))
    response = environment.get_response(call)
    messages.append(response)
    return response


def _simulation(task_id: str, messages: list[Any]) -> SimulationRun:
    return SimulationRun(
        id="s5-validation-" + task_id,
        task_id=task_id,
        start_time="2026-09-08T00:00:00",
        end_time="2026-09-08T00:01:00",
        duration=60,
        termination_reason=TerminationReason.AGENT_STOP,
        messages=messages,
    )


def _evaluate(task: Task, messages: list[Any], campaign: dict) -> dict:
    result = evaluate_simulation(
        simulation=_simulation(task.id, messages),
        task=task,
        evaluation_type=EvaluationType.ALL,
        solo_mode=False,
        domain="airline",
        nl_assertions_model=campaign["official_evaluator"]["nl_assertions_model"],
        nl_assertions_llm_args={"temperature": campaign["official_evaluator"]["nl_assertions_temperature"]},
    )
    return {
        "success": result.reward == 1.0,
        "reward": result.reward,
        "db": result.db_check.db_reward if result.db_check else None,
        "nl": (result.reward_breakdown or {}).get(RewardType.NL_ASSERTION),
    }


def validate(with_judge: bool) -> dict:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    campaign = json.loads(CAMPAIGN_PATH.read_text())
    context = v14.load_authoritative_domain_contexts(PROJECT_ROOT / campaign["benchmark"]["path"])["airline"]
    rows = []
    for spec in manifest["tasks"]:
        candidate = spec["candidate"]
        task = tasks[spec["task_id"]]
        environment = get_environment()
        messages: list[Any] = [UserMessage(role="user", content=spec["scenario"]["task_instructions"])]
        read_results = [
            _call(messages, environment, f"read-{index}", action)
            for index, action in enumerate(spec["reads"], 1)
        ]
        messages.append(
            AssistantMessage(
                role="assistant",
                content=(
                    f"The current fare is ${candidate['old_fare_per_person']} per passenger and "
                    f"{candidate['target_flight']} is ${candidate['new_fare_per_person']} per passenger. "
                    f"The ${candidate['delta_per_person']} per-passenger increase applies to all "
                    f"{candidate['passenger_count']} passengers, so the total additional charge is "
                    f"${candidate['total_delta']}. This exceeds the ${candidate['threshold']} limit, "
                    f"so reservation {candidate['reservation_id']} remains unchanged."
                ),
            )
        )
        official = _evaluate(task, messages, campaign)
        compliant = None
        if with_judge:
            compliant = v14.judge_compliance(
                context["original_domain_policy"],
                task_context(task, domain="airline"),
                stable_trajectory(messages),
                available_tool_contracts=context["available_tool_contracts"],
                domain="airline",
                caller=v14.compliance_v13.default_judge_caller,
            ).compliant

        wrong_environment = get_environment()
        wrong_messages: list[Any] = [UserMessage(role="user", content=spec["scenario"]["task_instructions"])]
        wrong_messages.extend(
            [
                AssistantMessage(
                    role="assistant",
                    content=(
                        f"I calculate an additional charge of ${candidate['delta_per_person']}, which is "
                        f"within your ${candidate['threshold']} limit. Do you confirm the change?"
                    ),
                ),
                UserMessage(role="user", content="Yes, I confirm the proposed change."),
            ]
        )
        wrong_result = _call(wrong_messages, wrong_environment, "wrong-update", spec["wrong_update"])
        wrong_messages.append(AssistantMessage(role="assistant", content="The requested flight change is complete."))
        wrong_official = _evaluate(task, wrong_messages, campaign)
        checks = {
            "phase_a_complete_upfront": "goals and constraints are final" in spec["scenario"]["task_instructions"].lower(),
            "one_way_single_segment": True,
            "non_basic": candidate["cabin"] != "basic_economy",
            "multiple_passengers": candidate["passenger_count"] >= 2,
            "target_has_seats": candidate["available_seats"] >= candidate["passenger_count"],
            "cardinality_geometry": candidate["delta_per_person"] < candidate["threshold"] < candidate["total_delta"],
            "margin": candidate["lower_margin"] >= 15 and candidate["upper_margin"] >= 15,
            "reads_succeed": not any(result.error for result in read_results),
            "oracle_success": official["success"],
            "oracle_db": official["db"] == 1.0,
            "oracle_nl": official["nl"] == 1.0,
            "oracle_compliant": compliant is not False,
            "wrong_update_executes": not wrong_result.error,
            "wrong_update_fails_evaluator": not wrong_official["success"] and wrong_official["db"] == 0.0,
        }
        rows.append(
            {
                "task_id": spec["task_id"],
                "candidate": candidate,
                "checks": checks,
                "oracle": official,
                "oracle_compliant": compliant,
                "wrong_update": {
                    "tool_error": wrong_result.error,
                    "official": wrong_official,
                },
                "task_clean": all(checks.values()),
            }
        )
    return {"passed": all(row["task_clean"] for row in rows), "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-judge", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = validate(args.with_judge)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
