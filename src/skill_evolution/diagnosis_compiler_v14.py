"""Pure decision compiler for validated v0.14 Semantic Diagnoses."""

from __future__ import annotations

from typing import Any

SUPPORTED_EVIDENCE = {"contrastive_support", "recurrent_support"}
COVERAGE_WEAKNESSES = {"missing", "incorrect", "underspecified"}


def _result(
    *, root_cause: str | None, update_eligible: bool, update_axis: str,
    operation: str, target_section: str | None, target_rule_id: str | None,
    reason: str, semantic: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    outcome = semantic["outcome_relation"]
    supported_axes = [
        axis for axis in ("task_success", "compliance") if outcome[axis] == "supports"
    ]
    decision = {
        "root_cause": root_cause,
        "update_eligible": update_eligible,
        "update_axis": update_axis,
        "operation": operation,
        "target_section": target_section,
        "target_rule_id": target_rule_id,
        "reason": reason,
    }
    trace = {
        "evidence_supported": (
            semantic["behavioral_mechanism"]["evidence_status"] in SUPPORTED_EVIDENCE
        ),
        "evidence_status": semantic["behavioral_mechanism"]["evidence_status"],
        "feasibility": semantic["feasibility"]["status"],
        "coverage": semantic["skill_coverage"]["status"],
        "supported_axes": supported_axes,
        "decision_reason": reason,
    }
    return decision, trace


def compile_semantic_diagnosis(
    semantic: dict[str, Any], skill_sections: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile a validated semantic judgment into one legal downstream decision."""

    feasibility = semantic["feasibility"]["status"]
    evidence = semantic["behavioral_mechanism"]["evidence_status"]
    coverage = semantic["skill_coverage"]["status"]
    outcome = semantic["outcome_relation"]
    common = {"semantic": semantic}

    def no_update(root_cause: str | None, reason: str):
        return _result(
            root_cause=root_cause, update_eligible=False, update_axis="none",
            operation="none", target_section=None, target_rule_id=None,
            reason=reason, **common,
        )

    if feasibility == "infeasible":
        return no_update("external_issue", "INFEASIBLE_TASK_POLICY_TOOL_COMBINATION")
    if evidence == "insufficient":
        return no_update(None, "INSUFFICIENT_MECHANISM_EVIDENCE")
    if evidence == "conflicting":
        return no_update("uncertain", "CONFLICTING_MECHANISM_EVIDENCE")
    if feasibility == "uncertain":
        return no_update("uncertain", "FEASIBILITY_UNCERTAIN")
    if coverage == "already_covered":
        return no_update("execution_issue", "MECHANISM_ALREADY_COVERED")
    if coverage == "not_applicable":
        return no_update(None, "SKILL_COVERAGE_NOT_APPLICABLE")
    if coverage not in COVERAGE_WEAKNESSES:
        return no_update("uncertain", "UNSUPPORTED_SKILL_COVERAGE_STATE")

    supported_axes = [
        axis for axis in ("task_success", "compliance") if outcome[axis] == "supports"
    ]
    if not supported_axes:
        return no_update("uncertain", "NO_SUPPORTED_OPTIMIZATION_AXIS")
    update_axis = "both" if len(supported_axes) == 2 else supported_axes[0]

    if coverage == "missing":
        return _result(
            root_cause="skill_issue", update_eligible=True, update_axis=update_axis,
            operation="add", target_section=None, target_rule_id=None,
            reason="UPDATE_ELIGIBLE_MISSING_COVERAGE", **common,
        )

    related_rule_ids = semantic["skill_coverage"]["related_rule_ids"]
    if len(related_rule_ids) != 1:
        return no_update("uncertain", "AMBIGUOUS_RULE_TARGET")
    target_rule_id = related_rule_ids[0]
    matches = [
        section for section, rules in skill_sections.items()
        if any(rule.get("rule_id") == target_rule_id for rule in rules)
    ]
    if len(matches) != 1:
        return no_update("uncertain", "AMBIGUOUS_RULE_TARGET")
    edit_intent = semantic["edit_intent"]
    if edit_intent not in {"replace", "delete"}:
        return no_update("uncertain", "MISSING_REVISION_INTENT")
    return _result(
        root_cause="skill_issue", update_eligible=True, update_axis=update_axis,
        operation=edit_intent, target_section=matches[0], target_rule_id=target_rule_id,
        reason=f"UPDATE_ELIGIBLE_{coverage.upper()}", **common,
    )
