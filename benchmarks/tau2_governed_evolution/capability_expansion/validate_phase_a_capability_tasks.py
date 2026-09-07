"""Static and controlled-oracle validation for Step 4T."""

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
from tau2.data_model.tasks import RewardType, Task  # noqa: E402
from tau2.domains.airline.environment import get_environment as get_airline_environment  # noqa: E402
from tau2.domains.retail.environment import get_environment as get_retail_environment  # noqa: E402
from tau2.evaluator import evaluator_nl_assertions  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation  # noqa: E402

from src.adapters.tau2.tau3_gse_runtime import stable_trajectory, task_context  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = DIRECTORY / "phase_a_capability_candidates.json"
TASKS_PATH = DIRECTORY / "phase_a_capability_tasks.json"
CAMPAIGN_PATH = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    values = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    tasks = {item["id"]: Task.model_validate(item) for item in values}
    if len(tasks) != len(values):
        raise ValueError("duplicate task id")
    return manifest, tasks


def validate_run_contract(manifest: dict[str, Any], campaign: dict[str, Any]) -> None:
    v14.validate_campaign_contract(campaign)
    specs = manifest.get("tasks", [])
    families = [item["family"] for item in specs]
    domains = [item["domain"] for item in specs]
    if (
        manifest.get("selection_status") != "frozen_before_empty_skill_rollouts"
        or manifest.get("selection_basis") != "native_state_and_mechanism_structure_only"
        or manifest.get("empty_rollout_outcomes_used_for_selection") is not False
        or manifest.get("calibration_seeds") != [810, 811, 812]
        or manifest.get("rollout_seeds") != [820, 821, 822]
        or len(specs) != 8
        or domains.count("retail") != 4
        or domains.count("airline") != 4
        or families.count("R2_minimal_mutation_scope") != 2
        or families.count("R4_one_shot_compilation") != 2
        or families.count("A1_bottleneck_feasibility") != 2
        or families.count("A2_cross_reservation_constraint") != 2
        or len(manifest.get("rejected_candidates", [])) != 2
    ):
        raise ValueError("Step 4T frozen contract drifted")
    if campaign["initial_parent"]["kind"] != "empty_skill":
        raise ValueError("Step 4T requires Empty Skill")


def _environment(domain: str) -> Any:
    return get_retail_environment() if domain == "retail" else get_airline_environment()


def _call(
    environment: Any,
    messages: list[Any],
    errors: list[str],
    call_id: str,
    name: str,
    arguments: dict[str, Any],
) -> None:
    call = ToolCall(id=call_id, name=name, arguments=arguments, requestor="assistant")
    messages.append(AssistantMessage(role="assistant", content=None, tool_calls=[call]))
    result = environment.get_response(call)
    messages.append(result)
    if getattr(result, "error", False):
        errors.append(f"{name}: {result.content}")


def build_oracle(task: Task, spec: dict[str, Any]) -> tuple[list[Any], list[str]]:
    environment = _environment(spec["domain"])
    messages: list[Any] = [
        UserMessage(
            role="user",
            content=(
                str(task.user_scenario.instructions.known_info)
                + " "
                + str(task.user_scenario.instructions.task_instructions)
            ),
        )
    ]
    errors: list[str] = []
    for index, read in enumerate(spec["reads"]):
        _call(environment, messages, errors, f"read-{index}", read["name"], read["arguments"])
    messages.extend(
        [
            AssistantMessage(
                role="assistant",
                content=spec["calibration_proposal"] + " Do you explicitly confirm this exact complete transaction?",
            ),
            UserMessage(role="user", content="Yes, I explicitly confirm this exact complete transaction."),
        ]
    )
    for index, action in enumerate(task.evaluation_criteria.actions or []):
        _call(environment, messages, errors, f"write-{index}", action.name, action.arguments)
    messages.append(
        AssistantMessage(
            role="assistant",
            content="The confirmed transaction is complete. " + " ".join(spec["nl_assertions"]),
        )
    )
    return messages, errors


def _official(
    task: Task,
    spec: dict[str, Any],
    messages: list[Any],
    evaluator: dict[str, Any],
) -> dict[str, Any]:
    run = SimulationRun(
        id=f"oracle-{task.id}",
        task_id=task.id,
        start_time="2026-09-07T00:00:00",
        end_time="2026-09-07T00:01:00",
        duration=60,
        termination_reason=TerminationReason.AGENT_STOP,
        messages=messages,
    )
    result = evaluate_simulation(
        simulation=run,
        task=task,
        evaluation_type=EvaluationType.ALL,
        solo_mode=False,
        domain=spec["domain"],
        nl_assertions_model=evaluator["nl_assertions_model"],
        nl_assertions_llm_args={
            "temperature": evaluator["nl_assertions_temperature"]
        },
    )
    return {
        "reward": result.reward,
        "success": result.reward == 1.0,
        "db_reward": result.db_check.db_reward if result.db_check else None,
        "nl_reward": (result.reward_breakdown or {}).get(RewardType.NL_ASSERTION),
    }


def _compliance(
    task: Task,
    spec: dict[str, Any],
    messages: list[Any],
    contexts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    domain = spec["domain"]
    context = contexts[domain]
    judgment = v14.judge_compliance(
        context["original_domain_policy"],
        task_context(task, domain=domain),
        stable_trajectory(messages),
        available_tool_contracts=context["available_tool_contracts"],
        domain=domain,
        caller=v14.compliance_v13.default_judge_caller,
    )
    return {
        "compliant": judgment.compliant,
        "violations": [
            {
                "policy_section": item.policy_section,
                "policy_clause": item.policy_clause,
                "evidence_steps": list(item.evidence_steps),
                "reason": item.reason,
            }
            for item in judgment.violations
        ],
    }


def validate(
    *, with_judge: bool, task_ids: tuple[str, ...] | None = None
) -> dict[str, Any]:
    manifest, tasks = load_suite()
    campaign = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
    validate_run_contract(manifest, campaign)
    evaluator = campaign["official_evaluator"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = evaluator[
        "nl_assertions_model"
    ]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
        "temperature": evaluator["nl_assertions_temperature"]
    }
    contexts = v14.load_authoritative_domain_contexts(
        PROJECT_ROOT / campaign["benchmark"]["path"]
    )
    results: dict[str, Any] = {}
    selected_ids = set(task_ids) if task_ids else {item["task_id"] for item in manifest["tasks"]}
    if not selected_ids <= set(tasks):
        raise ValueError("Unknown --tasks value")
    for spec in manifest["tasks"]:
        if spec["task_id"] not in selected_ids:
            continue
        task = tasks[spec["task_id"]]
        visible = " ".join(
            [
                str(task.user_scenario.instructions.known_info),
                str(task.user_scenario.instructions.task_instructions),
            ]
        )
        messages, errors = build_oracle(task, spec)
        official = _official(task, spec, messages, evaluator) if not errors else None
        compliance = (
            _compliance(task, spec, messages, contexts)
            if with_judge and not errors
            else None
        )
        checks = {
            "strict_upfront_contract": all(
                re.search(pattern, visible, re.I)
                for pattern in spec["initial_required_regexes"]
            ),
            "domain_matches": task.user_scenario.instructions.domain == spec["domain"],
            "target_family": spec["family"]
            in {
                "R2_minimal_mutation_scope",
                "R4_one_shot_compilation",
                "A1_bottleneck_feasibility",
                "A2_cross_reservation_constraint",
            },
            "not_monetary_baseline_dominated": "price threshold" not in visible.lower(),
            "deterministic_oracle": bool(
                spec["oracle"]["branch"] and spec["candidate_evidence"]
            ),
            "tool_executable": not errors,
            "official_success": bool(official and official["success"]),
            "oracle_compliant": compliance is None or compliance["compliant"],
        }
        results[spec["task_id"]] = {
            "domain": spec["domain"],
            "family": spec["family"],
            "passed": all(checks.values()),
            "checks": checks,
            "official": official,
            "compliance": compliance,
            "tool_errors": errors,
        }
    return {
        "with_judge": with_judge,
        "passed": all(item["passed"] for item in results.values()),
        "rejected_candidates": manifest["rejected_candidates"],
        "tasks": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-judge", action="store_true")
    parser.add_argument("--tasks", nargs="+")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "artifacts/phase_a_capability_step4t/oracle_validation.json",
    )
    args = parser.parse_args()
    result = validate(
        with_judge=args.with_judge,
        task_ids=tuple(args.tasks) if args.tasks else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
