"""Minimal Semantic Diagnosis contract for Autonomous GSE v0.14."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any

EVIDENCE_STATUSES = {
    "contrastive_support", "recurrent_support", "conflicting", "insufficient",
}
FEASIBILITY_STATUSES = {"feasible", "infeasible", "uncertain"}
SKILL_COVERAGE_STATUSES = {
    "missing", "incorrect", "underspecified", "already_covered", "not_applicable",
}
OUTCOME_RELATIONS = {"supports", "contradicts", "insufficient", "not_applicable"}
EDIT_INTENTS = {"replace", "delete", "not_applicable"}
SEMANTIC_DIAGNOSIS_FIELDS = {
    "behavioral_mechanism", "feasibility", "skill_coverage", "outcome_relation",
    "repair_policy_ids", "target_behavior", "edit_intent",
}
EVIDENCE_REF_FIELDS = {"source_id", "step_ids"}
TARGET_BEHAVIOR_FIELDS = {
    "problem", "trigger_condition", "decision_boundary", "repair_operator",
    "stopping_boundary", "expected_behavior",
}


@dataclass(frozen=True)
class DiagnosisValidation:
    diagnosis_id: str
    source_ids: tuple[str, ...]
    raw_response: str
    structured_output: dict[str, Any] | None
    valid: bool
    validation_errors: tuple[str, ...]
    compiled_decision: dict[str, Any] | None = None
    compiler_trace: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnosis_id": self.diagnosis_id,
            "source_ids": list(self.source_ids),
            "semantic": {
                "raw_response": self.raw_response,
                "structured_output": copy.deepcopy(self.structured_output),
                "validation": {
                    "valid": self.valid,
                    "errors": list(self.validation_errors),
                },
            },
            "compiled_decision": copy.deepcopy(self.compiled_decision),
            "compiler_trace": copy.deepcopy(self.compiler_trace),
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


def _validate_refs(
    value: Any, evidence_by_source: dict[str, dict[str, Any]], prefix: str,
) -> list[str]:
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
        if not isinstance(steps, list) or not steps or any(
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
        return tuple(dict.fromkeys([*errors, "SEMANTIC_DIAGNOSIS_NOT_OBJECT"]))
    if set(diagnosis) != SEMANTIC_DIAGNOSIS_FIELDS:
        errors.append("INVALID_SEMANTIC_DIAGNOSIS_FIELDS")

    evidence_by_source = {
        item["source_id"]: item for item in experiences
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }
    mechanism = diagnosis.get("behavioral_mechanism")
    mechanism_fields = {
        "description", "evidence_status", "support_evidence_refs",
        "counterevidence_refs", "counterevidence",
    }
    evidence_status = None
    if not isinstance(mechanism, dict) or set(mechanism) != mechanism_fields:
        errors.append("INVALID_BEHAVIORAL_MECHANISM")
    else:
        evidence_status = mechanism.get("evidence_status")
        if evidence_status not in EVIDENCE_STATUSES:
            errors.append("INVALID_EVIDENCE_STATUS")
        if not isinstance(mechanism.get("description"), str) or not isinstance(
            mechanism.get("counterevidence"), str,
        ):
            errors.append("INVALID_BEHAVIORAL_MECHANISM")
        errors.extend(_validate_refs(
            mechanism.get("support_evidence_refs"), evidence_by_source, "SUPPORT",
        ))
        errors.extend(_validate_refs(
            mechanism.get("counterevidence_refs"), evidence_by_source, "COUNTER",
        ))
        if evidence_status in {"contrastive_support", "recurrent_support"}:
            if not isinstance(mechanism.get("description"), str) or not mechanism["description"].strip():
                errors.append("SUPPORTED_EVIDENCE_REQUIRES_MECHANISM")
            if not mechanism.get("support_evidence_refs"):
                errors.append("SUPPORTED_EVIDENCE_REQUIRES_SUPPORT_REFS")

    feasibility = diagnosis.get("feasibility")
    if not isinstance(feasibility, dict) or set(feasibility) != {"status", "explanation"}:
        errors.append("INVALID_FEASIBILITY")
    else:
        if feasibility.get("status") not in FEASIBILITY_STATUSES:
            errors.append("INVALID_FEASIBILITY_STATUS")
        if not isinstance(feasibility.get("explanation"), str):
            errors.append("INVALID_FEASIBILITY")

    coverage = diagnosis.get("skill_coverage")
    if not isinstance(coverage, dict) or set(coverage) != {
        "status", "related_rule_ids", "explanation",
    }:
        errors.append("INVALID_SKILL_COVERAGE")
    else:
        if coverage.get("status") not in SKILL_COVERAGE_STATUSES:
            errors.append("INVALID_SKILL_COVERAGE_STATUS")
        if not isinstance(coverage.get("explanation"), str):
            errors.append("INVALID_SKILL_COVERAGE")
        rule_ids = coverage.get("related_rule_ids")
        if not isinstance(rule_ids, list) or any(
            not isinstance(rule_id, str) or not rule_id for rule_id in rule_ids
        ):
            errors.append("INVALID_RELATED_RULE_IDS")
        else:
            known_rule_ids = {
                rule.get("rule_id") for rules in skill_sections.values() for rule in rules
                if isinstance(rule, dict) and isinstance(rule.get("rule_id"), str)
            }
            if not set(rule_ids) <= known_rule_ids:
                errors.append("RELATED_RULE_ID_NOT_FOUND")

    outcome = diagnosis.get("outcome_relation")
    if not isinstance(outcome, dict) or set(outcome) != {"task_success", "compliance"}:
        errors.append("INVALID_OUTCOME_RELATION")
    else:
        if outcome.get("task_success") not in OUTCOME_RELATIONS:
            errors.append("INVALID_TASK_SUCCESS_RELATION")
        if outcome.get("compliance") not in OUTCOME_RELATIONS:
            errors.append("INVALID_COMPLIANCE_RELATION")

    policy_ids = diagnosis.get("repair_policy_ids")
    if not isinstance(policy_ids, list) or any(
        not isinstance(value, str) or not value for value in policy_ids
    ):
        errors.append("INVALID_REPAIR_POLICY_IDS")
    elif not set(policy_ids) <= _policy_ids(experiences):
        errors.append("POLICY_ID_NOT_IN_EVIDENCE")

    target = diagnosis.get("target_behavior")
    if not isinstance(target, dict) or set(target) != TARGET_BEHAVIOR_FIELDS or any(
        not isinstance(target.get(key), str) for key in TARGET_BEHAVIOR_FIELDS
    ):
        errors.append("INVALID_TARGET_BEHAVIOR")
    if diagnosis.get("edit_intent") not in EDIT_INTENTS:
        errors.append("INVALID_EDIT_INTENT")
    return tuple(dict.fromkeys(errors))


def _parse_semantic_response(response: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(response, str):
        return None, "SEMANTIC_DIAGNOSIS_RESPONSE_NOT_STRING"
    opening = "<SEMANTIC_DIAGNOSIS_JSON>"
    closing = "</SEMANTIC_DIAGNOSIS_JSON>"
    stripped = response.strip()
    if not stripped.startswith(opening) or not stripped.endswith(closing):
        return None, "SEMANTIC_DIAGNOSIS_JSON_NOT_FOUND"
    payload = stripped[len(opening):-len(closing)].strip()
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None, "INVALID_SEMANTIC_DIAGNOSIS_JSON"
    if not isinstance(parsed, dict):
        return None, "SEMANTIC_DIAGNOSIS_NOT_OBJECT"
    return parsed, None


def parse_and_validate_diagnosis(
    diagnosis_id: str, response: Any, *, experiences: tuple[dict[str, Any], ...],
    skill_sections: dict[str, list[dict[str, str]]],
) -> DiagnosisValidation:
    parsed, parse_error = _parse_semantic_response(response)
    errors = (parse_error,) if parse_error else validate_diagnosis(
        parsed, experiences=experiences, skill_sections=skill_sections,
    )
    return DiagnosisValidation(
        diagnosis_id=diagnosis_id,
        source_ids=tuple(item.get("source_id", "") for item in experiences),
        raw_response=response if isinstance(response, str) else repr(response),
        structured_output=copy.deepcopy(parsed),
        valid=not errors,
        validation_errors=errors,
    )
