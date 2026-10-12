"""Structured Diagnosis contract for diagnosis-driven Skill evolution."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any

ROOT_CAUSES = {"skill_issue", "execution_issue", "external_issue", "uncertain"}
UPDATE_RELEVANCE = {"update", "preserve", "none", "uncertain"}
UPDATE_ACTIONS = {"add", "replace", "delete", "none"}
DIAGNOSIS_FIELDS = {
    "behavior_summary",
    "task_analysis",
    "policy_analysis",
    "root_cause",
    "skill_update_relevance",
    "update_recommendation",
    "preserve_constraints",
}


@dataclass(frozen=True)
class DiagnosisValidation:
    """One raw Diagnosis response and its deterministic validation result."""

    diagnosis_id: str
    source_id: str
    raw_response: str
    structured_output: dict[str, Any] | None
    valid: bool
    validation_errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnosis_id": self.diagnosis_id,
            "source_id": self.source_id,
            "raw_response": self.raw_response,
            "structured_output": copy.deepcopy(self.structured_output),
            "validation": {
                "valid": self.valid,
                "errors": list(self.validation_errors),
            },
        }


def parse_diagnosis_response(response: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Parse exactly one tagged JSON object without attempting repair."""

    if not isinstance(response, str):
        return None, "UNPARSEABLE_DIAGNOSIS"
    match = re.fullmatch(
        r"\s*<DIAGNOSIS_JSON>\s*(.*?)\s*</DIAGNOSIS_JSON>\s*",
        response,
        flags=re.DOTALL,
    )
    if match is None:
        return None, "UNPARSEABLE_DIAGNOSIS"
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, "UNPARSEABLE_DIAGNOSIS"
    if not isinstance(parsed, dict):
        return None, "DIAGNOSIS_NOT_OBJECT"
    return parsed, None


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and item for item in value
    )


def _action_step_ids(evidence: dict[str, Any]) -> set[int]:
    actions = evidence.get("actions")
    if not isinstance(actions, list):
        trajectory = evidence.get("trajectory")
        actions = trajectory.get("actions") if isinstance(trajectory, dict) else None
    if not isinstance(actions, list):
        return set()
    return {
        step
        for item in actions
        if isinstance(item, dict)
        and isinstance((step := item.get("step")), int)
        and not isinstance(step, bool)
        and step > 0
    }


def _validate_evidence_steps(
    value: Any,
    known_step_ids: set[int],
    *,
    field: str,
) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(step, int) or isinstance(step, bool) or step <= 0
        for step in value
    ):
        return (f"INVALID_{field}_EVIDENCE_STEPS",)
    if any(step not in known_step_ids for step in value):
        return (f"{field}_EVIDENCE_STEP_NOT_FOUND",)
    return ()


def validate_diagnosis(
    diagnosis: Any,
    *,
    evidence: dict[str, Any],
    skill_sections: dict[str, list[dict[str, str]]],
) -> tuple[str, ...]:
    """Validate Diagnosis semantics against verifier facts and Skill addresses."""

    errors: list[str] = []
    if not isinstance(diagnosis, dict):
        return ("DIAGNOSIS_NOT_OBJECT",)
    if set(diagnosis) != DIAGNOSIS_FIELDS:
        errors.append("INVALID_DIAGNOSIS_FIELDS")

    if not isinstance(diagnosis.get("behavior_summary"), str):
        errors.append("INVALID_BEHAVIOR_SUMMARY")

    state = evidence.get("state")
    expected_task = "success" if evidence.get("task_success") is True else "failure"
    expected_policy = "violated" if state in {
        "violating_success",
        "violating_failure",
    } else "compliant"
    known_step_ids = _action_step_ids(evidence)

    task = diagnosis.get("task_analysis")
    if not isinstance(task, dict) or set(task) != {"status", "reason", "evidence_steps"}:
        errors.append("INVALID_TASK_ANALYSIS")
    else:
        if task.get("status") != expected_task:
            errors.append("TASK_STATUS_DISAGREES_WITH_FOUR_STATE")
        if not isinstance(task.get("reason"), str):
            errors.append("INVALID_TASK_ANALYSIS")
        errors.extend(
            _validate_evidence_steps(
                task.get("evidence_steps"), known_step_ids, field="TASK"
            )
        )

    feedback = evidence.get("process_feedback", {})
    allowed_policy_ids = {
        item.get("policy_template_id")
        for item in feedback.get("violated_policies", [])
        if isinstance(item, dict) and isinstance(item.get("policy_template_id"), str)
    }
    policy = diagnosis.get("policy_analysis")
    if not isinstance(policy, dict) or set(policy) != {
        "status",
        "reason",
        "policy_ids",
        "evidence_steps",
    }:
        errors.append("INVALID_POLICY_ANALYSIS")
    else:
        policy_ids = policy.get("policy_ids")
        if policy.get("status") != expected_policy:
            errors.append("POLICY_STATUS_DISAGREES_WITH_FOUR_STATE")
        if (
            not isinstance(policy.get("reason"), str)
            or not _is_string_list(policy_ids)
        ):
            errors.append("INVALID_POLICY_ANALYSIS")
        elif not set(policy_ids).issubset(allowed_policy_ids):
            errors.append("POLICY_ID_NOT_IN_EVIDENCE")
        errors.extend(
            _validate_evidence_steps(
                policy.get("evidence_steps"), known_step_ids, field="POLICY"
            )
        )
        if expected_policy == "compliant" and policy_ids != []:
            errors.append("COMPLIANT_DIAGNOSIS_HAS_POLICY_IDS")

    root_cause = diagnosis.get("root_cause")
    category: Any = None
    if not isinstance(root_cause, dict) or set(root_cause) != {"category", "explanation"}:
        errors.append("INVALID_ROOT_CAUSE")
    else:
        category = root_cause.get("category")
        if category is not None and category not in ROOT_CAUSES:
            errors.append("INVALID_ROOT_CAUSE_CATEGORY")
        if not isinstance(root_cause.get("explanation"), str):
            errors.append("INVALID_ROOT_CAUSE")

    relevance = diagnosis.get("skill_update_relevance")
    if relevance not in UPDATE_RELEVANCE:
        errors.append("INVALID_SKILL_UPDATE_RELEVANCE")
    if category == "execution_issue" and relevance != "none":
        errors.append("EXECUTION_ISSUE_MUST_NOT_UPDATE")
    if category == "external_issue" and relevance != "none":
        errors.append("EXTERNAL_ISSUE_MUST_NOT_UPDATE")
    if category == "uncertain" and relevance != "uncertain":
        errors.append("UNCERTAIN_CAUSE_REQUIRES_UNCERTAIN_RELEVANCE")
    if relevance == "update" and category != "skill_issue":
        errors.append("UPDATE_REQUIRES_SKILL_ISSUE")

    recommendation = diagnosis.get("update_recommendation")
    if not isinstance(recommendation, dict) or set(recommendation) != {
        "action",
        "target_section",
        "target_rule_id",
        "objective",
        "description",
    }:
        errors.append("INVALID_UPDATE_RECOMMENDATION")
    else:
        action = recommendation.get("action")
        section = recommendation.get("target_section")
        rule_id = recommendation.get("target_rule_id")
        if action not in UPDATE_ACTIONS:
            errors.append("INVALID_UPDATE_ACTION")
        if not isinstance(recommendation.get("objective"), str) or not isinstance(
            recommendation.get("description"), str
        ):
            errors.append("INVALID_UPDATE_RECOMMENDATION")
        if relevance == "update" and action not in {"add", "replace", "delete"}:
            errors.append("UPDATE_RELEVANCE_ACTION_MISMATCH")
        if relevance != "update" and action != "none":
            errors.append("NON_UPDATE_RELEVANCE_ACTION_MISMATCH")
        if action == "add":
            if section not in skill_sections:
                errors.append("TARGET_SECTION_NOT_FOUND")
            if rule_id is not None:
                errors.append("ADD_MUST_NOT_TARGET_RULE")
        elif action in {"replace", "delete"}:
            if section not in skill_sections:
                errors.append("TARGET_SECTION_NOT_FOUND")
            matching_sections = [
                name
                for name, rules in skill_sections.items()
                if any(rule.get("rule_id") == rule_id for rule in rules)
            ]
            if not matching_sections:
                errors.append("TARGET_RULE_ID_NOT_FOUND")
            elif matching_sections != [section]:
                errors.append("TARGET_RULE_SECTION_MISMATCH")
        elif action == "none" and (section is not None or rule_id is not None):
            errors.append("NONE_MUST_NOT_HAVE_TARGET")

    preserve = diagnosis.get("preserve_constraints")
    if not isinstance(preserve, list):
        errors.append("INVALID_PRESERVE_CONSTRAINTS")
    else:
        known_rule_ids = {
            rule["rule_id"] for rules in skill_sections.values() for rule in rules
        }
        for item in preserve:
            if (
                not isinstance(item, dict)
                or set(item) != {"target_rule_id", "reason"}
                or item.get("target_rule_id") not in known_rule_ids
                or not isinstance(item.get("reason"), str)
                or not item.get("reason")
            ):
                errors.append("INVALID_PRESERVE_CONSTRAINT")
                break

    return tuple(dict.fromkeys(errors))


def parse_and_validate_diagnosis(
    diagnosis_id: str,
    source_id: str,
    response: Any,
    *,
    evidence: dict[str, Any],
    skill_sections: dict[str, list[dict[str, str]]],
) -> DiagnosisValidation:
    parsed, parse_error = parse_diagnosis_response(response)
    errors = (
        (parse_error,)
        if parse_error is not None
        else validate_diagnosis(parsed, evidence=evidence, skill_sections=skill_sections)
    )
    return DiagnosisValidation(
        diagnosis_id=diagnosis_id,
        source_id=source_id,
        raw_response=response if isinstance(response, str) else repr(response),
        structured_output=copy.deepcopy(parsed),
        valid=not errors,
        validation_errors=errors,
    )
