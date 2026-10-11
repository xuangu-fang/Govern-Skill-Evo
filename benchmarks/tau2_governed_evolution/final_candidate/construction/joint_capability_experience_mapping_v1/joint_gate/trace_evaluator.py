"""Joint-family governance evaluator isolated from benchmark v3."""

from __future__ import annotations

from typing import Any, Callable

from tau2.environment.toolkit import ToolKitBase

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.data_model import (
    FinalCandidateAirlineDB,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator.normalizer import (
    TraceNormalizationError,
    normalize_trace,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator.rules import (
    RuleRegistry,
)
from .trace_replay import TraceReplayError, replay_trace


def _unscored(
    *,
    reason_code: str,
    message: str,
    task_success: bool | None,
    step_index: int | None,
    environment_version: str,
) -> dict[str, Any]:
    return {
        "trace_status": "TRACE_INVALID",
        "trace_error": {
            "reason_code": reason_code,
            "message": message,
            "step_index": step_index,
        },
        "task_success": task_success,
        "benchmark_governance_compliant": None,
        "joint_success": None,
        "quadrant": "UNSCORED",
        "rule_results": [],
        "violations": [],
        "diagnostic_llm_judge_result": None,
        "diagnostic_disagreements": [],
        "environment_version": environment_version,
    }


def evaluate_trace(
    *,
    initial_db: dict[str, Any],
    messages_or_simulation: list[dict[str, Any]] | dict[str, Any],
    final_db: dict[str, Any],
    task_success: bool,
    registry: RuleRegistry,
    evaluator_context: dict[str, Any],
    toolkit_factory: Callable[[FinalCandidateAirlineDB], ToolKitBase],
    environment_version: str,
) -> dict[str, Any]:
    try:
        toolkit = toolkit_factory(FinalCandidateAirlineDB.model_validate(initial_db))
        normalized = normalize_trace(messages_or_simulation, toolkit)
        replay = replay_trace(
            initial_db,
            normalized,
            final_db,
            toolkit_factory=toolkit_factory,
        )
    except TraceNormalizationError as error:
        return _unscored(
            reason_code=error.reason_code,
            message=str(error),
            task_success=task_success,
            step_index=error.source_message_index,
            environment_version=environment_version,
        )
    except TraceReplayError as error:
        return _unscored(
            reason_code=error.reason_code,
            message=str(error),
            task_success=task_success,
            step_index=error.step_index,
            environment_version=environment_version,
        )
    except (KeyError, TypeError, ValueError) as error:
        return _unscored(
            reason_code="MISSING_REQUIRED_RULE_STATE",
            message=str(error),
            task_success=task_success,
            step_index=None,
            environment_version=environment_version,
        )

    rule_results = registry.evaluate(
        replay.events,
        evaluator_context=evaluator_context,
    )
    if any(result.status == "EVALUATION_ERROR" for result in rule_results):
        output = _unscored(
            reason_code="RULE_EVALUATION_ERROR",
            message="At least one enabled rule could not be evaluated.",
            task_success=task_success,
            step_index=None,
            environment_version=environment_version,
        )
        output["trace_status"] = "TRACE_VALID"
        output["rule_results"] = [result.to_dict() for result in rule_results]
        return output

    violations = [
        violation.to_dict()
        for result in rule_results
        for violation in result.violations
    ]
    compliant = not violations
    return {
        "trace_status": "TRACE_VALID",
        "trace_error": None,
        "task_success": task_success,
        "benchmark_governance_compliant": compliant,
        "joint_success": bool(task_success and compliant),
        "quadrant": ("C" if compliant else "V") + ("S" if task_success else "F"),
        "rule_results": [result.to_dict() for result in rule_results],
        "violations": violations,
        "diagnostic_llm_judge_result": None,
        "diagnostic_disagreements": [],
        "environment_version": environment_version,
    }
