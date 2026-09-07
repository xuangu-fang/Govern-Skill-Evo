"""Static and exact-oracle validation for the Step 4R deep-dependency pilot."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable


ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage  # noqa: E402
from tau2.data_model.simulation import SimulationRun, TerminationReason  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.domains.airline.environment import get_environment  # noqa: E402
from tau2.evaluator import evaluator_nl_assertions  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.intent_dynamics.probe_airline_c1_family import (  # noqa: E402
    compliance_result,
)


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = DIRECTORY / "airline_deep_dependency_candidates.json"
TASKS_PATH = DIRECTORY / "airline_deep_dependency_tasks.json"
CAMPAIGN_PATH = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    values = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    tasks = {item["id"]: Task.model_validate(item) for item in values}
    if len(tasks) != len(values):
        raise ValueError("duplicate task id")
    return manifest, tasks


def validate_run_contract(manifest: dict[str, Any], campaign: dict[str, Any]) -> None:
    if (
        manifest.get("selection_status") != "frozen_before_empty_skill_rollouts"
        or manifest.get("selection_basis") != "real_state_branch_audit_only"
        or manifest.get("empty_rollout_outcomes_used_for_selection") is not False
        or manifest.get("rollout_seeds") != [620, 621, 622]
        or len(manifest.get("tasks", [])) != 6
    ):
        raise ValueError("Step 4R frozen contract drifted")
    if campaign["initial_parent"]["kind"] != "empty_skill":
        raise ValueError("Step 4R requires Empty Skill")


def _probe(task: Task, spec: dict[str, Any]) -> tuple[list[Any], list[str]]:
    env = get_environment()
    messages: list[Any] = [UserMessage(role="user", content=str(task.user_scenario.instructions))]
    errors = []
    read_calls = [("get_user_details", {"user_id": spec["source_state"]["user_id"]})]
    reservations = []
    for reservation_id in spec["source_state"]["reservation_ids"]:
        call = ToolCall(id=f"read-res-{reservation_id}", name="get_reservation_details", arguments={"reservation_id": reservation_id}, requestor="assistant")
        messages.append(AssistantMessage(role="assistant", content=None, tool_calls=[call]))
        result = env.get_response(call)
        messages.append(result)
        if getattr(result, "error", False):
            errors.append(str(result.content))
        else:
            reservations.append(json.loads(result.content))
    for reservation in reservations:
        for flight in reservation["flights"]:
            read_calls.append(("search_direct_flight", {"origin": flight["origin"], "destination": flight["destination"], "date": flight["date"]}))
    special = {
        "airline_dd_m05knl_conditional_arrival": [("search_direct_flight", {"origin": "ATL", "destination": "PHL", "date": "2024-05-24"}), ("search_onestop_flight", {"origin": "ATL", "destination": "PHL", "date": "2024-05-24"})],
        "airline_dd_obut9v_fast_price_refund": [("search_direct_flight", {"origin": "DEN", "destination": "IAH", "date": "2024-05-27"}), ("search_onestop_flight", {"origin": "DEN", "destination": "IAH", "date": "2024-05-27"})],
        "airline_dd_hxdubj_multistage_propagation": [("search_direct_flight", {"origin": "IAH", "destination": "SFO", "date": "2024-05-19"}), ("search_direct_flight", {"origin": "SFO", "destination": "IAH", "date": "2024-05-23"})],
    }
    read_calls.extend(special.get(spec["task_id"], []))
    seen = set()
    for index, (name, arguments) in enumerate(read_calls):
        key = (name, json.dumps(arguments, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        call = ToolCall(id=f"oracle-read-{index}", name=name, arguments=arguments, requestor="assistant")
        messages.append(AssistantMessage(role="assistant", content=None, tool_calls=[call]))
        result = env.get_response(call)
        messages.append(result)
        if getattr(result, "error", False):
            errors.append(str(result.content))
    messages.extend([
        AssistantMessage(role="assistant", content=spec["calibration_proposal"] + " Do you confirm?"),
        UserMessage(role="user", content="Yes, I explicitly confirm this exact complete proposal."),
    ])
    for index, action in enumerate(task.evaluation_criteria.actions or []):
        call = ToolCall(id=f"oracle-{index}", name=action.name, arguments=action.arguments, requestor="assistant")
        messages.append(AssistantMessage(role="assistant", content=None, tool_calls=[call]))
        result = env.get_response(call)
        messages.append(result)
        if getattr(result, "error", False):
            errors.append(str(result.content))
    messages.append(AssistantMessage(role="assistant", content="All writes and reconciliation are complete. " + " ".join(spec["nl_assertions"])))
    return messages, errors


def _official(task: Task, messages: list[Any]) -> dict[str, Any]:
    run = SimulationRun(id=f"oracle-{task.id}", task_id=task.id, start_time="2026-09-07T00:00:00", end_time="2026-09-07T00:01:00", duration=60, termination_reason=TerminationReason.AGENT_STOP, messages=messages)
    result = evaluate_simulation(simulation=run, task=task, evaluation_type=EvaluationType.ALL, solo_mode=False, domain="airline")
    return {"reward": result.reward, "success": result.reward == 1.0, "db_reward": result.db_check.db_reward if result.db_check else None}


def validate(*, with_judge: bool) -> dict[str, Any]:
    manifest, tasks = load_suite()
    campaign = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
    validate_run_contract(manifest, campaign)
    evaluator = campaign["official_evaluator"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = evaluator["nl_assertions_model"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {"temperature": evaluator["nl_assertions_temperature"]}
    results = {}
    for spec in manifest["tasks"]:
        task = tasks[spec["task_id"]]
        text = " ".join([task.user_scenario.instructions.reason_for_call, task.user_scenario.instructions.known_info, task.user_scenario.instructions.task_instructions])
        messages, errors = _probe(task, spec)
        official = _official(task, messages) if not errors else None
        compliance = compliance_result(task, messages) if with_judge and not errors else None
        checks = {
            "strict_upfront_contract": all(re.search(p, text, re.I) for p in spec["initial_required_regexes"]),
            "deep_dependency": len(spec["dependency_graph"]) >= 4,
            "deterministic_branch": bool(spec["oracle"]["branch"]),
            "tool_executable": not errors,
            "official_success": bool(official and official["success"]),
            "oracle_compliant": compliance is None or compliance["compliant"],
        }
        results[spec["task_id"]] = {"passed": all(checks.values()), "checks": checks, "official": official, "compliance": compliance, "tool_errors": errors}
    return {"with_judge": with_judge, "passed": all(x["passed"] for x in results.values()), "tasks": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-judge", action="store_true")
    args = parser.parse_args()
    result = validate(with_judge=args.with_judge)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
