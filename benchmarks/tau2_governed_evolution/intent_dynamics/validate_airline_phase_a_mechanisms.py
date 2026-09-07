"""Static and controlled-oracle validation for Step 4S."""

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

from benchmarks.tau2_governed_evolution.intent_dynamics.probe_airline_c1_family import compliance_result  # noqa: E402


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = DIRECTORY / "airline_phase_a_mechanism_candidates.json"
TASKS_PATH = DIRECTORY / "airline_phase_a_mechanism_tasks.json"
CAMPAIGN_PATH = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    values = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    tasks = {item["id"]: Task.model_validate(item) for item in values}
    if len(tasks) != len(values):
        raise ValueError("duplicate task id")
    return manifest, tasks


def validate_run_contract(manifest: dict[str, Any], campaign: dict[str, Any]) -> None:
    families = [item["family"] for item in manifest.get("tasks", [])]
    if (
        manifest.get("selection_status") != "frozen_before_empty_skill_rollouts"
        or manifest.get("selection_basis") != "native_state_and_mechanism_structure_only"
        or manifest.get("empty_rollout_outcomes_used_for_selection") is not False
        or manifest.get("rollout_seeds") != [720, 721, 722]
        or len(families) != 6
        or any(families.count(family) != 2 for family in set(families))
    ):
        raise ValueError("Step 4S frozen contract drifted")
    if campaign["initial_parent"]["kind"] != "empty_skill":
        raise ValueError("Step 4S requires Empty Skill")


def _call(env: Any, messages: list[Any], errors: list[str], call_id: str, name: str, arguments: dict[str, Any]) -> None:
    call = ToolCall(id=call_id, name=name, arguments=arguments, requestor="assistant")
    messages.append(AssistantMessage(role="assistant", content=None, tool_calls=[call]))
    result = env.get_response(call)
    messages.append(result)
    if getattr(result, "error", False):
        errors.append(str(result.content))


def _probe(task: Task, spec: dict[str, Any]) -> tuple[list[Any], list[str]]:
    env = get_environment()
    messages: list[Any] = [UserMessage(role="user", content=str(task.user_scenario.instructions))]
    errors: list[str] = []
    reservations = []
    for index, reservation_id in enumerate(spec["source_state"]["reservation_ids"]):
        before = len(messages)
        _call(env, messages, errors, f"res-{index}", "get_reservation_details", {"reservation_id": reservation_id})
        if len(messages) > before + 1 and not getattr(messages[-1], "error", False):
            reservations.append(json.loads(messages[-1].content))
    reads: list[tuple[str, dict[str, Any]]] = [("get_user_details", {"user_id": spec["source_state"]["user_id"]})]
    for reservation in reservations:
        for flight in reservation["flights"]:
            reads.append(("search_direct_flight", {"origin": flight["origin"], "destination": flight["destination"], "date": flight["date"]}))
    reads.extend({
        "airline_pa_b1_obut9v_fastest_return": [
            ("search_direct_flight", {"origin": "DEN", "destination": "IAH", "date": "2024-05-27"}),
            ("search_onestop_flight", {"origin": "DEN", "destination": "IAH", "date": "2024-05-27"}),
        ],
        "airline_pa_b2_1n99u6_lexicographic_return": [("search_direct_flight", {"origin": "IAH", "destination": "LAS", "date": "2024-05-27"})],
        "airline_pa_d1_m66qvw_preserved_outbound": [("search_direct_flight", {"origin": "ATL", "destination": "LAS", "date": "2024-05-30"})],
    }.get(spec["task_id"], []))
    seen = set()
    for index, (name, arguments) in enumerate(reads):
        key = (name, json.dumps(arguments, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        _call(env, messages, errors, f"read-{index}", name, arguments)
    messages.extend([
        AssistantMessage(role="assistant", content=spec["calibration_proposal"] + " Do you explicitly confirm this complete operation set?"),
        UserMessage(role="user", content="Yes, I explicitly confirm this exact complete proposal and operation set."),
    ])
    for index, action in enumerate(task.evaluation_criteria.actions or []):
        _call(env, messages, errors, f"write-{index}", action.name, action.arguments)
    messages.append(AssistantMessage(role="assistant", content="All writes and final reconciliation are complete. " + " ".join(spec["nl_assertions"])))
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
        visible = " ".join([task.user_scenario.instructions.known_info, task.user_scenario.instructions.task_instructions])
        messages, errors = _probe(task, spec)
        official = _official(task, messages) if not errors else None
        compliance = compliance_result(task, messages) if with_judge and not errors else None
        checks = {
            "strict_upfront_contract": all(re.search(pattern, visible, re.I) for pattern in spec["initial_required_regexes"]),
            "family_is_targeted": spec["family"] in {"B_candidate_resolution", "D_precommit_consistency", "E_entity_operation_binding"},
            "not_monetary_baseline_dominated": "threshold" not in visible.lower(),
            "deterministic_oracle": bool(spec["oracle"]["branch"] and spec["candidate_evidence"]),
            "tool_executable": not errors,
            "official_success": bool(official and official["success"]),
            "oracle_compliant": compliance is None or compliance["compliant"],
        }
        results[spec["task_id"]] = {"passed": all(checks.values()), "checks": checks, "official": official, "compliance": compliance, "tool_errors": errors}
    return {"with_judge": with_judge, "passed": all(item["passed"] for item in results.values()), "tasks": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-judge", action="store_true")
    args = parser.parse_args()
    result = validate(with_judge=args.with_judge)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
