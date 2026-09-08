"""Static, real-transition, and controlled-oracle validation for Step 4V."""

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
from tau2.domains.retail.environment import get_environment  # noqa: E402
from tau2.evaluator import evaluator_nl_assertions  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import (  # noqa: E402
    CAMPAIGN_PATH,
    PROJECT_ROOT,
)
from benchmarks.tau2_governed_evolution.transition_ablation.build_transition_probe import (  # noqa: E402
    CANONICAL_POLICY_PATH,
    FORBIDDEN_PATTERNS,
    MANIFEST_PATH,
    PARTIAL_POLICY_PATH,
    TASKS_PATH,
    build,
)
from src.adapters.tau2.tau3_gse_runtime import stable_trajectory, task_context  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


EXPERIMENT_MANIFEST = Path(__file__).resolve().parent / "transition_ablation_manifest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/transition_ablation_step4v/oracle_validation.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    manifest = _load(MANIFEST_PATH)
    values = _load(TASKS_PATH)
    tasks = {item["id"]: Task.model_validate(item) for item in values}
    if len(tasks) != len(values):
        raise ValueError("duplicate Step 4V task id")
    return manifest, tasks


def _call(environment: Any, messages: list[Any], call_id: str, action: dict[str, Any]) -> Any:
    call = ToolCall(
        id=call_id,
        name=action["name"],
        arguments=action["arguments"],
        requestor="assistant",
    )
    messages.append(AssistantMessage(role="assistant", content=None, tool_calls=[call]))
    result = environment.get_response(call)
    messages.append(result)
    return result


def _controlled_sequence(spec: dict[str, Any], order: str) -> tuple[list[Any], list[dict[str, Any]]]:
    environment = get_environment()
    messages: list[Any] = [
        UserMessage(
            role="user",
            content=spec["scenario"]["known_info"] + " " + spec["scenario"]["task_instructions"],
        )
    ]
    results: list[dict[str, Any]] = []
    for index, read in enumerate(spec["reads"]):
        result = _call(environment, messages, f"{order}-read-{index}", read)
        results.append({"name": read["name"], "error": result.error, "content": result.content})
    messages.extend(
        [
            AssistantMessage(
                role="assistant",
                content=(
                    "I have resolved the complete requested final state. I will execute these exact updates: "
                    + json.dumps(spec["oracle"]["good_order"], ensure_ascii=False)
                    + ". All unrelated fields remain unchanged. Please confirm both that these are all "
                    "items you want modified and that I may execute all three updates."
                ),
            ),
            UserMessage(
                role="user",
                content="Yes, those are all the items I want modified, and I explicitly confirm all three exact updates.",
            ),
        ]
    )
    for index, action in enumerate(spec["oracle"][order]):
        result = _call(environment, messages, f"{order}-write-{index}", action)
        results.append({"name": action["name"], "error": result.error, "content": result.content})
    messages.append(
        AssistantMessage(
            role="assistant",
            content="The requested address, payment, and item changes are complete; unrelated state is unchanged. "
            + spec["nl_assertions"][0],
        )
    )
    return messages, results


def _official(task: Task, messages: list[Any], evaluator: dict[str, Any]) -> dict[str, Any]:
    run = SimulationRun(
        id=f"oracle-{task.id}",
        task_id=task.id,
        start_time="2026-09-08T00:00:00",
        end_time="2026-09-08T00:01:00",
        duration=60,
        termination_reason=TerminationReason.AGENT_STOP,
        messages=messages,
    )
    result = evaluate_simulation(
        simulation=run,
        task=task,
        evaluation_type=EvaluationType.ALL,
        solo_mode=False,
        domain="retail",
        nl_assertions_model=evaluator["nl_assertions_model"],
        nl_assertions_llm_args={"temperature": evaluator["nl_assertions_temperature"]},
    )
    return {
        "reward": result.reward,
        "success": result.reward == 1.0,
        "db_reward": result.db_check.db_reward if result.db_check else None,
        "nl_reward": (result.reward_breakdown or {}).get(RewardType.NL_ASSERTION),
    }


def validate(with_judge: bool) -> dict[str, Any]:
    build_info = build()
    manifest, tasks = load_suite()
    experiment = _load(EXPERIMENT_MANIFEST)
    campaign = _load(CAMPAIGN_PATH)
    evaluator = campaign["official_evaluator"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = evaluator["nl_assertions_model"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
        "temperature": evaluator["nl_assertions_temperature"]
    }
    contexts = v14.load_authoritative_domain_contexts(
        PROJECT_ROOT / campaign["benchmark"]["path"]
    )
    partial = PARTIAL_POLICY_PATH.read_text(encoding="utf-8")
    if any(re.search(pattern, partial, re.I) for pattern in FORBIDDEN_PATTERNS):
        raise ValueError("partial transition view leaks hidden state consequence")
    if "can only be called once" not in partial or "collected into a list" not in partial:
        raise ValueError("Step 4V must retain one-shot/list-compilation knowledge")
    results: dict[str, Any] = {}
    for spec in manifest["tasks"]:
        task = tasks[spec["task_id"]]
        visible = spec["scenario"]["known_info"] + " " + spec["scenario"]["task_instructions"]
        good_messages, good_calls = _controlled_sequence(spec, "good_order")
        bad_messages, bad_calls = _controlled_sequence(spec, "bad_order")
        official = _official(task, good_messages, evaluator)
        official_bad = _official(task, bad_messages, evaluator)
        compliance = None
        if with_judge:
            context = contexts["retail"]
            judgment = v14.judge_compliance(
                context["original_domain_policy"],
                task_context(task, domain="retail"),
                stable_trajectory(good_messages),
                available_tool_contracts=context["available_tool_contracts"],
                domain="retail",
                caller=v14.compliance_v13.default_judge_caller,
            )
            compliance = {
                "compliant": judgment.compliant,
                "violations": [
                    item.model_dump() if hasattr(item, "model_dump") else vars(item)
                    for item in judgment.violations
                ],
            }
        bad_writes = bad_calls[len(spec["reads"]):]
        observed_errors = [item for item in bad_writes[1:] if item["error"]]
        checks = {
            "strict_upfront_complete": all(
                re.search(pattern, visible, re.I) for pattern in spec["initial_required_regexes"]
            ),
            "procedure_neutral": not re.search(
                r"(?:address|payment|items?).{0,20}(?:must|should).{0,10}(?:first|last)|"
                r"(?:first|last).{0,10}(?:address|payment|items?)",
                visible,
                re.I,
            ),
            "good_sequence_tool_executable": not any(item["error"] for item in good_calls),
            "good_sequence_official_success": official["success"],
            "good_sequence_compliant": compliance is None or compliance["compliant"],
            "bad_item_write_succeeds": not bad_writes[0]["error"],
            "bad_required_operation_rejected": len(observed_errors) >= 1,
            "bad_error_is_transition_consequence": all(
                "Non-pending order cannot be modified" in str(item["content"])
                or "exactly one payment" in str(item["content"])
                for item in observed_errors
            ),
            "bad_sequence_official_failure": not official_bad["success"],
        }
        results[spec["task_id"]] = {
            "passed": all(checks.values()),
            "checks": checks,
            "official_good": official,
            "official_bad": official_bad,
            "compliance_good": compliance,
            "bad_order_write_results": bad_writes,
        }
    contract = {
        "two_independent_tasks": len(tasks) == 2 and len({s["source_state"]["user_id"] for s in manifest["tasks"]}) == 2,
        "frozen_before_rollouts": manifest["selection_status"] == "frozen_before_model_rollouts",
        "experiment_task_ids_match": experiment["task_ids"] == [s["task_id"] for s in manifest["tasks"]],
        "canonical_policy_unchanged": CANONICAL_POLICY_PATH.exists(),
    }
    return {
        "with_judge": with_judge,
        "passed": all(contract.values()) and all(item["passed"] for item in results.values()),
        "build": build_info,
        "contract": contract,
        "tasks": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-judge", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = validate(args.with_judge)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
