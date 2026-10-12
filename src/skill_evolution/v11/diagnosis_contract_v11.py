"""Strict v0.11 single-rollout Diagnosis contract."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any

ROOT_CAUSES = {"skill_issue", "execution_issue", "external_issue", "uncertain"}
UPDATE_RELEVANCE = {"update", "none", "uncertain"}
UPDATE_ACTIONS = {"add", "replace", "delete", "none"}
DIAGNOSIS_FIELDS = {
    "behavior_summary",
    "task_analysis",
    "policy_analysis",
    "root_cause",
    "skill_update_relevance",
    "update_recommendation",
}


@dataclass(frozen=True)
class DiagnosisValidation:
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
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, "UNPARSEABLE_DIAGNOSIS"
    return (value, None) if isinstance(value, dict) else (None, "DIAGNOSIS_NOT_OBJECT")


def _step_ids(evidence: dict[str, Any]) -> set[int]:
    actions = evidence.get("actions")
    if not isinstance(actions, list):
        trajectory = evidence.get("trajectory")
        actions = trajectory.get("actions") if isinstance(trajectory, dict) else trajectory
    if not isinstance(actions, list):
        return set()
    return {
        item["step"]
        for item in actions
        if isinstance(item, dict)
        and isinstance(item.get("step"), int)
        and not isinstance(item["step"], bool)
        and item["step"] > 0
    }


def _validate_steps(value: Any, known: set[int], prefix: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(step, int) or isinstance(step, bool) or step <= 0 for step in value
    ):
        return [f"INVALID_{prefix}_EVIDENCE_STEPS"]
    return [f"{prefix}_EVIDENCE_STEP_NOT_FOUND"] if not set(value) <= known else []


def validate_diagnosis(
    diagnosis: Any,
    *,
    evidence: dict[str, Any],
    skill_sections: dict[str, list[dict[str, str]]],
) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(diagnosis, dict):
        return ("DIAGNOSIS_NOT_OBJECT",)
    if set(diagnosis) != DIAGNOSIS_FIELDS:
        errors.append("INVALID_DIAGNOSIS_FIELDS")
    if not isinstance(diagnosis.get("behavior_summary"), str):
        errors.append("INVALID_BEHAVIOR_SUMMARY")

    state = evidence.get("state")
    if state not in {
        "compliant_success", "violating_success", "compliant_failure", "violating_failure"
    }:
        errors.append("INVALID_EXTERNAL_FOUR_STATE")
    expected_task = "success" if evidence.get("task_success") is True else "failure"
    expected_policy = "violated" if str(state).startswith("violating_") else "compliant"
    known_steps = _step_ids(evidence)

    task = diagnosis.get("task_analysis")
    if not isinstance(task, dict) or set(task) != {"status", "reason", "evidence_steps"}:
        errors.append("INVALID_TASK_ANALYSIS")
    else:
        if task.get("status") != expected_task:
            errors.append("TASK_STATUS_DISAGREES_WITH_FOUR_STATE")
        if not isinstance(task.get("reason"), str):
            errors.append("INVALID_TASK_ANALYSIS")
        errors.extend(_validate_steps(task.get("evidence_steps"), known_steps, "TASK"))

    feedback = evidence.get("process_feedback", {})
    violations = feedback.get("violated_policies", []) if isinstance(feedback, dict) else []
    allowed_policy_ids = {
        value
        for item in violations
        if isinstance(item, dict)
        for value in (item.get("policy_template_id"), item.get("policy_id"))
        if isinstance(value, str) and value
    }
    policy = diagnosis.get("policy_analysis")
    if not isinstance(policy, dict) or set(policy) != {
        "status", "reason", "policy_ids", "evidence_steps"
    }:
        errors.append("INVALID_POLICY_ANALYSIS")
    else:
        ids = policy.get("policy_ids")
        if policy.get("status") != expected_policy:
            errors.append("POLICY_STATUS_DISAGREES_WITH_FOUR_STATE")
        if not isinstance(policy.get("reason"), str) or not isinstance(ids, list) or any(
            not isinstance(item, str) or not item for item in ids
        ):
            errors.append("INVALID_POLICY_ANALYSIS")
        elif not set(ids) <= allowed_policy_ids:
            errors.append("POLICY_ID_NOT_IN_EVIDENCE")
        if expected_policy == "compliant" and ids != []:
            errors.append("COMPLIANT_DIAGNOSIS_HAS_POLICY_IDS")
        errors.extend(_validate_steps(policy.get("evidence_steps"), known_steps, "POLICY"))

    root = diagnosis.get("root_cause")
    category = None
    if not isinstance(root, dict) or set(root) != {"category", "explanation"}:
        errors.append("INVALID_ROOT_CAUSE")
    else:
        category = root.get("category")
        if category is not None and category not in ROOT_CAUSES:
            errors.append("INVALID_ROOT_CAUSE_CATEGORY")
        if not isinstance(root.get("explanation"), str):
            errors.append("INVALID_ROOT_CAUSE")

    relevance = diagnosis.get("skill_update_relevance")
    if relevance not in UPDATE_RELEVANCE:
        errors.append("INVALID_SKILL_UPDATE_RELEVANCE")
    expected_relevance = {
        "skill_issue": "update",
        "execution_issue": "none",
        "external_issue": "none",
        "uncertain": "uncertain",
        None: "none",
    }.get(category)
    if relevance in UPDATE_RELEVANCE and expected_relevance != relevance:
        errors.append("ROOT_CAUSE_RELEVANCE_MISMATCH")

    rec = diagnosis.get("update_recommendation")
    if not isinstance(rec, dict) or set(rec) != {
        "action", "target_section", "target_rule_id", "objective", "description"
    }:
        errors.append("INVALID_UPDATE_RECOMMENDATION")
    else:
        action = rec.get("action")
        section = rec.get("target_section")
        rule_id = rec.get("target_rule_id")
        if action not in UPDATE_ACTIONS:
            errors.append("INVALID_UPDATE_ACTION")
        if not isinstance(rec.get("objective"), str) or not isinstance(rec.get("description"), str):
            errors.append("INVALID_UPDATE_RECOMMENDATION")
        if relevance == "update" and action not in {"add", "replace", "delete"}:
            errors.append("UPDATE_RELEVANCE_ACTION_MISMATCH")
        if relevance in {"none", "uncertain"} and action != "none":
            errors.append("NON_UPDATE_RELEVANCE_ACTION_MISMATCH")
        if action == "add":
            if section not in skill_sections:
                errors.append("TARGET_SECTION_NOT_FOUND")
            if rule_id is not None:
                errors.append("ADD_MUST_NOT_TARGET_RULE")
        elif action in {"replace", "delete"}:
            if section not in skill_sections:
                errors.append("TARGET_SECTION_NOT_FOUND")
            matches = [
                name for name, rules in skill_sections.items()
                if any(rule.get("rule_id") == rule_id for rule in rules)
            ]
            if not matches:
                errors.append("TARGET_RULE_ID_NOT_FOUND")
            elif matches != [section]:
                errors.append("TARGET_RULE_SECTION_MISMATCH")
        elif action == "none" and (section is not None or rule_id is not None):
            errors.append("NONE_MUST_NOT_HAVE_TARGET")
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
    errors = (parse_error,) if parse_error else validate_diagnosis(
        parsed, evidence=evidence, skill_sections=skill_sections
    )
    return DiagnosisValidation(
        diagnosis_id=diagnosis_id,
        source_id=source_id,
        raw_response=response if isinstance(response, str) else repr(response),
        structured_output=copy.deepcopy(parsed),
        valid=not errors,
        validation_errors=errors,
    )
