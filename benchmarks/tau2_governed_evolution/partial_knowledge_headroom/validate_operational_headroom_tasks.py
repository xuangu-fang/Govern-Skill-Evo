"""Static, controlled-transition, and oracle validation for Step 4W."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable

ensure_tau2_importable()

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage  # noqa: E402
from tau2.data_model.simulation import SimulationRun, TerminationReason  # noqa: E402
from tau2.data_model.tasks import RewardType, Task  # noqa: E402
from tau2.domains.airline.environment import get_environment as airline_environment  # noqa: E402
from tau2.domains.retail.environment import get_environment as retail_environment  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import CAMPAIGN_PATH, PROJECT_ROOT  # noqa: E402
from benchmarks.tau2_governed_evolution.partial_knowledge_headroom.build_partial_operational_views import REGISTRY_PATH, TASKS_PATH, build  # noqa: E402
from src.adapters.tau2.tau3_gse_runtime import stable_trajectory, task_context  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/partial_knowledge_headroom_step4w/oracle_validation.json"


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    build()
    registry = json.loads(REGISTRY_PATH.read_text())
    values = json.loads(TASKS_PATH.read_text())
    return registry, {item["id"]: Task.model_validate(item) for item in values}


def _environment(domain: str) -> Any:
    return retail_environment() if domain == "retail" else airline_environment()


def _sequence(spec: dict, actions: list[dict]) -> tuple[list[Any], list[dict]]:
    env = _environment(spec["domain"])
    messages: list[Any] = [UserMessage(role="user", content=spec["scenario"]["known_info"] + " " + spec["scenario"]["task_instructions"])]
    results = []
    for index, action in enumerate(spec["reads"] + actions):
        call = ToolCall(id=f"call-{index}", name=action["name"], arguments=action["arguments"], requestor="assistant")
        if index == len(spec["reads"]):
            messages += [AssistantMessage(role="assistant", content=(
                "I have resolved the complete requested final state and will perform these exact actions: "
                + json.dumps(actions, ensure_ascii=False)
                + ". Preserved state remains unchanged. The final result will be: "
                + " ".join(spec["nl_assertions"])
                + " Do you explicitly confirm these exact details?"
            )), UserMessage(role="user", content="Yes, I explicitly confirm those exact complete details and authorize every listed action.")]
        messages.append(AssistantMessage(role="assistant", content=None, tool_calls=[call]))
        response = env.get_response(call)
        messages.append(response)
        results.append({"tool": action["name"], "error": response.error, "content": response.content})
    messages.append(AssistantMessage(role="assistant", content="The confirmed request is complete. " + " ".join(spec["nl_assertions"])))
    return messages, results


def _official(task: Task, spec: dict, messages: list[Any], campaign: dict) -> dict:
    run = SimulationRun(id="oracle-" + task.id, task_id=task.id, start_time="2026-09-08T00:00:00", end_time="2026-09-08T00:01:00", duration=60, termination_reason=TerminationReason.AGENT_STOP, messages=messages)
    result = evaluate_simulation(simulation=run, task=task, evaluation_type=EvaluationType.ALL, solo_mode=False, domain=spec["domain"], nl_assertions_model=campaign["official_evaluator"]["nl_assertions_model"], nl_assertions_llm_args={"temperature": campaign["official_evaluator"]["nl_assertions_temperature"]})
    return {"success": result.reward == 1.0, "reward": result.reward, "db": result.db_check.db_reward if result.db_check else None, "nl": (result.reward_breakdown or {}).get(RewardType.NL_ASSERTION)}


def validate(with_judge: bool = False, task_ids: set[str] | None = None) -> dict:
    registry, tasks = load_suite()
    campaign = json.loads(CAMPAIGN_PATH.read_text())
    contexts = v14.load_authoritative_domain_contexts(PROJECT_ROOT / campaign["benchmark"]["path"])
    rows = []
    for spec in registry["tasks"]:
        if task_ids is not None and spec["task_id"] not in task_ids:
            continue
        task = tasks[spec["task_id"]]
        good_messages, good_results = _sequence(spec, spec["oracle"]["good_order"])
        bad_messages, bad_results = _sequence(spec, spec["oracle"]["bad_order"])
        official = _official(task, spec, good_messages, campaign)
        compliance = None
        if with_judge:
            context = contexts[spec["domain"]]
            judgment = v14.judge_compliance(context["original_domain_policy"], task_context(task, domain=spec["domain"]), stable_trajectory(good_messages), available_tool_contracts=context["available_tool_contracts"], domain=spec["domain"], caller=v14.compliance_v13.default_judge_caller)
            compliance = judgment.compliant
        if spec["knowledge_id"] == "O1":
            bad_effect = any(item["error"] and "exactly one payment" in item["content"] for item in bad_results)
        elif spec["knowledge_id"] == "O2":
            bad_effect = not _official(task, spec, bad_messages, campaign)["success"]
        else:
            bad_effect = not _official(task, spec, bad_messages, campaign)["success"]
        checks = {"upfront_stable": "Never add" in spec["scenario"]["task_instructions"] or "Never revise" in spec["scenario"]["task_instructions"], "good_tools": not any(item["error"] for item in good_results), "oracle_success": official["success"], "oracle_compliant": compliance is not False, "bad_semantics_changes_outcome": bad_effect}
        rows.append({"task_id": task.id, "knowledge_id": spec["knowledge_id"], "checks": checks, "passed": all(checks.values()), "official": official, "compliant": compliance, "good_results": good_results, "bad_results": bad_results})
    output = {"passed": all(row["passed"] for row in rows), "rows": rows, "rejected_units": {"O4": registry["knowledge_units"]["O4"]}}
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-judge", action="store_true")
    parser.add_argument("--tasks", nargs="+")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    value = validate(args.with_judge, set(args.tasks) if args.tasks else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value, indent=2))
    return 0 if value["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
