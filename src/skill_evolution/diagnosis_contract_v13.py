"""Strict v0.13 dual-axis task-level multi-rollout Diagnosis contract."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from src.skill_evolution.diagnosis_contract_v11 import parse_diagnosis_response

ROOT_CAUSES = {"skill_issue", "execution_issue", "external_issue", "uncertain"}
UPDATE_RELEVANCE = {"update", "none", "uncertain"}
UPDATE_AXES = {"task_success", "compliance", "both", "none"}
UPDATE_ACTIONS = {"add", "replace", "delete", "none"}
EVIDENCE_CONSISTENCIES = {"supportive", "conflicting", "insufficient"}
DIAGNOSIS_FIELDS = {
    "task_behavior_summary", "cross_rollout_analysis", "root_cause",
    "skill_update_relevance", "update_axis", "repair_policy_ids",
    "target_behavior", "update_recommendation",
}
EVIDENCE_REF_FIELDS = {"source_id", "step_ids"}


@dataclass(frozen=True)
class DiagnosisValidation:
    diagnosis_id: str
    source_ids: tuple[str, ...]
    raw_response: str
    structured_output: dict[str, Any] | None
    valid: bool
    validation_errors: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnosis_id": self.diagnosis_id,
            "source_ids": list(self.source_ids),
            "raw_response": self.raw_response,
            "structured_output": copy.deepcopy(self.structured_output),
            "validation": {"valid": self.valid, "errors": list(self.validation_errors)},
        }


def _step_ids(evidence: dict[str, Any]) -> set[int]:
    actions = evidence.get("actions")
    if not isinstance(actions, list):
        trajectory = evidence.get("trajectory")
        actions = trajectory.get("actions") if isinstance(trajectory, dict) else trajectory
    if not isinstance(actions, list):
        return set()
    return {
        item["step"] for item in actions
        if isinstance(item, dict) and isinstance(item.get("step"), int)
        and not isinstance(item["step"], bool) and item["step"] > 0
    }


def _validate_refs(value: Any, evidence_by_source: dict[str, dict[str, Any]], prefix: str) -> list[str]:
    if not isinstance(value, list):
        return [f"INVALID_{prefix}_EVIDENCE_REFS"]
    errors: list[str] = []
    for ref in value:
        if not isinstance(ref, dict) or set(ref) != EVIDENCE_REF_FIELDS:
            errors.append(f"INVALID_{prefix}_EVIDENCE_REF")
            continue
        source_id, steps = ref.get("source_id"), ref.get("step_ids")
        if source_id not in evidence_by_source:
            errors.append(f"{prefix}_EVIDENCE_SOURCE_NOT_FOUND")
            continue
        if not isinstance(steps, list) or any(
            not isinstance(step, int) or isinstance(step, bool) or step <= 0 for step in steps
        ):
            errors.append(f"INVALID_{prefix}_EVIDENCE_STEPS")
        elif not set(steps) <= _step_ids(evidence_by_source[source_id]):
            errors.append(f"{prefix}_EVIDENCE_STEP_NOT_FOUND")
    return errors


def _policy_ids(experiences: tuple[dict[str, Any], ...]) -> set[str]:
    result: set[str] = set()
    for evidence in experiences:
        feedback = evidence.get("process_feedback", {})
        violations = feedback.get("violated_policies", []) if isinstance(feedback, dict) else []
        for item in violations:
            if isinstance(item, dict):
                for key in ("policy_template_id", "policy_id"):
                    value = item.get(key)
                    if isinstance(value, str) and value:
                        result.add(value)
    return result


def validate_task_evidence_group(experiences: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    if not isinstance(experiences, tuple) or len(experiences) != 3:
        return ("TASK_GROUP_MUST_HAVE_EXACTLY_THREE_ROLLOUTS",)
    indexes = [item.get("rollout_index") for item in experiences if isinstance(item, dict)]
    source_ids = [item.get("source_id") for item in experiences if isinstance(item, dict)]
    errors: list[str] = []
    if sorted(indexes) != [1, 2, 3]:
        errors.append("INVALID_OR_DUPLICATE_ROLLOUT_INDEX")
    if len(source_ids) != 3 or any(not isinstance(value, str) or not value for value in source_ids):
        errors.append("INVALID_SOURCE_ID")
    elif len(set(source_ids)) != 3:
        errors.append("DUPLICATE_SOURCE_ID")
    identities = {(item.get("domain"), str(item.get("task_id"))) for item in experiences}
    if len(identities) != 1 or any(
        not isinstance(domain, str) or not domain or task_id in {"", "None"}
        for domain, task_id in identities
    ):
        errors.append("MIXED_TASK_EVIDENCE_GROUP")
    return tuple(errors)


def validate_diagnosis(
    diagnosis: Any, *, experiences: tuple[dict[str, Any], ...],
    skill_sections: dict[str, list[dict[str, str]]],
) -> tuple[str, ...]:
    errors = list(validate_task_evidence_group(experiences))
    if not isinstance(diagnosis, dict):
        return tuple(dict.fromkeys([*errors, "DIAGNOSIS_NOT_OBJECT"]))
    if set(diagnosis) != DIAGNOSIS_FIELDS:
        errors.append("INVALID_DIAGNOSIS_FIELDS")
    if not isinstance(diagnosis.get("task_behavior_summary"), str):
        errors.append("INVALID_TASK_BEHAVIOR_SUMMARY")
    evidence_by_source = {
        item["source_id"]: item for item in experiences
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }
    analysis = diagnosis.get("cross_rollout_analysis")
    expected_analysis = {
        "stable_behavior", "success_contrast", "compliance_contrast", "counterevidence",
        "discriminating_behavior", "evidence_consistency",
        "support_evidence_refs", "counterevidence_refs",
    }
    if not isinstance(analysis, dict) or set(analysis) != expected_analysis:
        errors.append("INVALID_CROSS_ROLLOUT_ANALYSIS")
    else:
        if any(not isinstance(analysis.get(key), str) for key in (
            "stable_behavior", "success_contrast", "compliance_contrast",
            "discriminating_behavior", "evidence_consistency", "counterevidence"
        )):
            errors.append("INVALID_CROSS_ROLLOUT_ANALYSIS")
        errors.extend(_validate_refs(analysis.get("support_evidence_refs"), evidence_by_source, "SUPPORT"))
        errors.extend(_validate_refs(analysis.get("counterevidence_refs"), evidence_by_source, "COUNTER"))
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
        "skill_issue": "update", "execution_issue": "none", "external_issue": "none",
        "uncertain": "uncertain", None: "none",
    }.get(category)
    if relevance in UPDATE_RELEVANCE and relevance != expected_relevance:
        errors.append("ROOT_CAUSE_RELEVANCE_MISMATCH")
    consistency = analysis.get("evidence_consistency") if isinstance(analysis, dict) else None
    discriminating = analysis.get("discriminating_behavior") if isinstance(analysis, dict) else None
    if consistency not in EVIDENCE_CONSISTENCIES:
        errors.append("INVALID_EVIDENCE_CONSISTENCY")
    if relevance == "update":
        if consistency != "supportive":
            errors.append("UPDATE_REQUIRES_SUPPORTIVE_EVIDENCE")
        if not isinstance(discriminating, str) or not discriminating.strip():
            errors.append("UPDATE_REQUIRES_DISCRIMINATING_BEHAVIOR")
        elif set(re.findall(r"[a-z]+", discriminating.casefold())) <= {
            "cs", "vs", "cf", "vf", "and", "differ", "differs", "different",
            "label", "labels", "outcome", "outcomes", "state", "states", "contrast",
            "task", "success", "compliance", "in",
        }:
            errors.append("DISCRIMINATING_BEHAVIOR_IS_ONLY_LABEL_CONTRAST")
    if consistency == "conflicting" and not (
        category == "uncertain" and relevance == "uncertain"
    ):
        errors.append("CONFLICTING_EVIDENCE_REQUIRES_UNCERTAIN_NO_UPDATE")
    update_axis = diagnosis.get("update_axis")
    if update_axis not in UPDATE_AXES:
        errors.append("INVALID_UPDATE_AXIS")
    elif relevance == "update" and update_axis not in {"task_success", "compliance", "both"}:
        errors.append("UPDATE_REQUIRES_ACTIVE_AXIS")
    elif relevance in {"none", "uncertain"} and update_axis != "none":
        errors.append("NON_UPDATE_AXIS_MUST_BE_NONE")
    policy_ids = diagnosis.get("repair_policy_ids")
    if not isinstance(policy_ids, list) or any(not isinstance(value, str) or not value for value in policy_ids):
        errors.append("INVALID_REPAIR_POLICY_IDS")
    elif not set(policy_ids) <= _policy_ids(experiences):
        errors.append("POLICY_ID_NOT_IN_EVIDENCE")
    target = diagnosis.get("target_behavior")
    target_fields = {
        "problem", "trigger_condition", "decision_boundary", "repair_operator",
        "stopping_boundary", "expected_behavior",
    }
    if not isinstance(target, dict) or set(target) != target_fields or any(
        not isinstance(target.get(key), str) for key in target_fields
    ):
        errors.append("INVALID_TARGET_BEHAVIOR")
    rec = diagnosis.get("update_recommendation")
    expected_rec = {"action", "target_section", "target_rule_id", "objective", "description"}
    if not isinstance(rec, dict) or set(rec) != expected_rec:
        errors.append("INVALID_UPDATE_RECOMMENDATION")
    else:
        action, section, rule_id = rec.get("action"), rec.get("target_section"), rec.get("target_rule_id")
        if action not in UPDATE_ACTIONS:
            errors.append("INVALID_UPDATE_ACTION")
        if not isinstance(rec.get("objective"), str) or not isinstance(rec.get("description"), str):
            errors.append("INVALID_UPDATE_RECOMMENDATION")
        if relevance == "update" and action not in {"add", "replace", "delete"}:
            errors.append("UPDATE_RELEVANCE_ACTION_MISMATCH")
        if relevance in {"none", "uncertain"} and action != "none":
            errors.append("NON_UPDATE_RELEVANCE_ACTION_MISMATCH")
        if action == "add":
            if section is not None:
                errors.append("ADD_MUST_NOT_PRESELECT_SECTION")
            if rule_id is not None:
                errors.append("ADD_MUST_NOT_TARGET_RULE")
        elif action in {"replace", "delete"}:
            if section not in skill_sections:
                errors.append("TARGET_SECTION_NOT_FOUND")
            matches = [name for name, rules in skill_sections.items() if any(rule.get("rule_id") == rule_id for rule in rules)]
            if not matches:
                errors.append("TARGET_RULE_ID_NOT_FOUND")
            elif matches != [section]:
                errors.append("TARGET_RULE_SECTION_MISMATCH")
        elif action == "none" and (section is not None or rule_id is not None):
            errors.append("NONE_MUST_NOT_HAVE_TARGET")
    return tuple(dict.fromkeys(errors))


def parse_and_validate_diagnosis(
    diagnosis_id: str, response: Any, *, experiences: tuple[dict[str, Any], ...],
    skill_sections: dict[str, list[dict[str, str]]],
) -> DiagnosisValidation:
    parsed, parse_error = parse_diagnosis_response(response)
    errors = (parse_error,) if parse_error else validate_diagnosis(
        parsed, experiences=experiences, skill_sections=skill_sections
    )
    source_ids = tuple(item.get("source_id", "") for item in experiences)
    return DiagnosisValidation(
        diagnosis_id=diagnosis_id, source_ids=source_ids,
        raw_response=response if isinstance(response, str) else repr(response),
        structured_output=copy.deepcopy(parsed), valid=not errors,
        validation_errors=errors,
    )
