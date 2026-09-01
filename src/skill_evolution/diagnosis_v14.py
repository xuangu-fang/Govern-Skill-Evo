"""Minimal task-level Semantic Diagnosis for Autonomous GSE v0.14."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.adapters.tau2.tau3_evaluation_scope_v13 import benchmark_exclusion_prompt
from src.skill_evolution.autonomous_gse_v05_proposal import _parse_skill, annotate_parent_skill
from src.skill_evolution.diagnosis_contract_v14 import (
    TARGET_BEHAVIOR_FIELDS, parse_and_validate_diagnosis,
    validate_task_evidence_group,
)
from src.skill_evolution.diagnosis_provenance_v14 import build_provenance_alias_context

LEARNER_MODEL = "openai/deepseek-v4-pro"
EMPTY_RESPONSE_RETRIES = 2
_STRUCTURED_OUTPUT_CAPABILITY = "unknown"
_STRUCTURED_OUTPUT_FALLBACK_REASON: str | None = None

SEMANTIC_DIAGNOSIS_TEMPLATE = {
    "behavioral_mechanism": {
        "description": "",
        "evidence_status": "insufficient",
        "support_evidence_refs": ["E001"],
        "counterevidence_refs": [],
        "counterevidence": "",
    },
    "feasibility": {"status": "uncertain", "explanation": ""},
    "skill_coverage": {
        "status": "not_applicable", "related_rule_ids": [], "explanation": "",
    },
    "outcome_relation": {
        "task_success": "insufficient", "compliance": "insufficient",
    },
    "repair_policy_refs": ["P001"],
    "target_behavior": {
        "problem": "", "trigger_condition": "", "decision_boundary": "",
        "repair_operator": "", "stopping_boundary": "", "expected_behavior": "",
    },
    "edit_intent": "not_applicable",
}

_ALIAS_ARRAY_SCHEMA = {
    "type": "array",
    "items": {"type": "string", "pattern": "^E[0-9]{3}$"},
}
_POLICY_ALIAS_ARRAY_SCHEMA = {
    "type": "array",
    "items": {"type": "string", "pattern": "^P[0-9]{3}$"},
}
SEMANTIC_DIAGNOSIS_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "behavioral_mechanism", "feasibility", "skill_coverage",
        "outcome_relation", "repair_policy_refs", "target_behavior", "edit_intent",
    ],
    "properties": {
        "behavioral_mechanism": {
            "type": "object", "additionalProperties": False,
            "required": [
                "description", "evidence_status", "support_evidence_refs",
                "counterevidence_refs", "counterevidence",
            ],
            "properties": {
                "description": {"type": "string"},
                "evidence_status": {"type": "string", "enum": [
                    "contrastive_support", "recurrent_support", "conflicting", "insufficient",
                ]},
                "support_evidence_refs": _ALIAS_ARRAY_SCHEMA,
                "counterevidence_refs": _ALIAS_ARRAY_SCHEMA,
                "counterevidence": {"type": "string"},
            },
        },
        "feasibility": {
            "type": "object", "additionalProperties": False,
            "required": ["status", "explanation"],
            "properties": {
                "status": {"type": "string", "enum": [
                    "feasible", "infeasible", "uncertain",
                ]},
                "explanation": {"type": "string"},
            },
        },
        "skill_coverage": {
            "type": "object", "additionalProperties": False,
            "required": ["status", "related_rule_ids", "explanation"],
            "properties": {
                "status": {"type": "string", "enum": [
                    "missing", "incorrect", "underspecified", "already_covered",
                    "not_applicable",
                ]},
                "related_rule_ids": {
                    "type": "array", "items": {"type": "string"},
                },
                "explanation": {"type": "string"},
            },
        },
        "outcome_relation": {
            "type": "object", "additionalProperties": False,
            "required": ["task_success", "compliance"],
            "properties": {
                "task_success": {"type": "string", "enum": [
                    "supports", "contradicts", "insufficient", "not_applicable",
                ]},
                "compliance": {"type": "string", "enum": [
                    "supports", "contradicts", "insufficient", "not_applicable",
                ]},
            },
        },
        "repair_policy_refs": _POLICY_ALIAS_ARRAY_SCHEMA,
        "target_behavior": {
            "type": "object", "additionalProperties": False,
            "required": [
                "problem", "trigger_condition", "decision_boundary", "repair_operator",
                "stopping_boundary", "expected_behavior",
            ],
            "properties": {
                field: {"type": "string"} for field in TARGET_BEHAVIOR_FIELDS
            },
        },
        "edit_intent": {
            "type": "string", "enum": ["replace", "delete", "not_applicable"],
        },
    },
}
SEMANTIC_DIAGNOSIS_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "v14_semantic_diagnosis",
        "strict": True,
        "schema": SEMANTIC_DIAGNOSIS_JSON_SCHEMA,
    },
}


@dataclass(frozen=True)
class MultiRolloutDiagnosisRequest:
    candidate_id: str
    diagnosis_id: str
    current_parent_skill: str
    task_context: dict[str, Any]
    original_domain_policy: str
    available_tool_contracts: tuple[dict[str, Any], ...]
    rollouts: tuple[dict[str, Any], ...]


Diagnoser = Callable[[MultiRolloutDiagnosisRequest], str]
LearnerCall = Callable[..., tuple[str, str, dict[str, Any] | None]]


class DiagnosisResponse(str):
    """Semantic response carrying transport-only structured-output metadata."""

    structured_output_mode: str
    structured_output_fallback_reason: str | None

    def __new__(cls, value: str, mode: str, fallback_reason: str | None = None):
        instance = super().__new__(cls, value)
        instance.structured_output_mode = mode
        instance.structured_output_fallback_reason = fallback_reason
        return instance


def _default_learner_call(
    model: str, system: str, user: str, *, response_format: dict | None = None,
) -> tuple[str, str, dict[str, Any] | None]:
    from src.learners.stwebagentbench.generate_skill import call_learner

    return call_learner(
        model, system, user, temperature=0.0, response_format=response_format,
    )


DIAGNOSIS_SYSTEM_PROMPT = """You are the v0.14 task-level Semantic Diagnosis component. Analyze exactly three independent Parent rollouts of the same task in one call. Return semantic judgments only. A deterministic Python compiler—not you—will derive root cause, update eligibility, update axis, edit operation, target rule, and target section.

Preserve this reasoning order:

1. Analyze Agent-controlled behavior before outcomes. Identify a concrete decision, predicate, condition check, tool or action choice, argument choice, ordering, retry, continuation, stopping decision, or explicit claim. Outcome labels, evaluator results, environment differences, latency, and tool-result differences are not behavioral mechanisms.

2. Evaluate feasibility at the relevant decision point using task requirements, the original Policy, and available tool contracts. feasible means a correct behavior existed that was simultaneously task-satisfying, Policy-permitted, technically supported, and available then. infeasible means no such behavior existed. uncertain means the supplied evidence cannot establish feasibility. Policy is normative; tool capability cannot create Policy permission.

3. Classify mechanism evidence across the three rollouts:
- contrastive_support: different Agent-controlled behaviors support one concrete mechanism under Policy/tool grounding.
- recurrent_support: multiple rollouts repeat the same problematic decision mechanism under the same relevant condition or decision opportunity, with a legal feasible alternative.
- conflicting: a concrete plausible mechanism has substantive support and unreconciled counterevidence.
- insufficient: no reliable Agent-controlled mechanism survives; evidence is mainly labels, environment differences, incidental behavior, or unreliable attribution.

4. Falsify before supporting. Compare the relevant predicate, decision opportunity, behavior, and predicted effect in every rollout. Select supporting and counter evidence only with E### references shown directly on supplied trajectory steps. A disproven allegation is insufficient, not conflicting. Counterevidence must constrain the proposed behavior change.

5. Compare the mechanism with the annotated Parent Skill:
- missing: the necessary mechanism is absent.
- incorrect: an existing rule gives wrong guidance.
- underspecified: a related rule omits an execution-critical trigger, predicate, boundary, ordering, feasibility condition, or stopping condition.
- already_covered: a clear, correct, executable existing rule covers the mechanism and the Agent did not follow it.
- not_applicable: the mechanism has no direct Parent Skill coverage relationship.
Only cite Rule IDs present in CURRENT_PARENT_SKILL_WITH_RULE_IDS. Do not label a rule underspecified merely to enable an update.

6. Judge Task Success and Compliance independently. Use supports, contradicts, insufficient, or not_applicable. Outcomes may test an already-proposed mechanism but must not create one. Policy may support a Compliance relationship even when Task Success evidence is insufficient. Do not derive or output an update axis.

7. Describe target behavior semantically: the problem, trigger, decision boundary, repair operator, necessary stopping boundary, and expected behavior. Generalize incidental episode values while preserving causal predicates. All six fields are strings; use an empty string when no special stopping boundary is needed.

8. edit_intent is limited to replace, delete, or not_applicable. For missing coverage use not_applicable because Python derives add. For incorrect or underspecified coverage, use replace or delete only when that is the intended treatment of the cited existing rule. For already_covered or not_applicable coverage use not_applicable. This field is consulted only if the deterministic compiler finds the Diagnosis update-eligible.

repair_policy_refs may contain only P### references shown in supplied violation evidence that directly ground the compliance repair.

Use only E### references shown in the supplied rollouts. Use only P### references shown in supplied violation evidence. Never copy raw source IDs, step IDs, or canonical Policy IDs into these fields. Use an empty array when no applicable evidence or Policy reference exists.

Do not output root_cause, skill_update_relevance, update_axis, update_recommendation, action, target_section, target_rule_id, objective, evidence_pattern, or evidence_consistency. Those are absent from the Semantic Diagnosis authority.

<<TAU3_BENCHMARK_EXCLUSION>>

Return only one JSON object matching this schema and no prose or tags:
<<SEMANTIC_DIAGNOSIS_TEMPLATE>>
""".replace(
    "<<TAU3_BENCHMARK_EXCLUSION>>", benchmark_exclusion_prompt("diagnosis"),
).replace(
    "<<SEMANTIC_DIAGNOSIS_TEMPLATE>>",
    json.dumps(SEMANTIC_DIAGNOSIS_TEMPLATE, ensure_ascii=False, indent=2),
)


def build_diagnosis_prompts(request: MultiRolloutDiagnosisRequest) -> tuple[str, str]:
    if not isinstance(request, MultiRolloutDiagnosisRequest):
        raise ValueError("v0.14 requires MultiRolloutDiagnosisRequest.")
    if not request.candidate_id or not request.diagnosis_id or not request.current_parent_skill.strip():
        raise ValueError("Diagnosis identifiers and Parent Skill are required.")
    if not isinstance(request.original_domain_policy, str) or not request.original_domain_policy.strip():
        raise ValueError("Original domain Policy is required.")
    if not isinstance(request.available_tool_contracts, tuple) or not request.available_tool_contracts or any(
        not isinstance(item, dict)
        or not isinstance(item.get("tool_name"), str) or not item["tool_name"].strip()
        or not isinstance(item.get("arguments"), list)
        or not isinstance(item.get("description"), str)
        for item in request.available_tool_contracts
    ):
        raise ValueError("Available tool contracts are invalid.")
    errors = validate_task_evidence_group(request.rollouts)
    if errors:
        raise ValueError(errors[0])
    annotated = annotate_parent_skill(request.current_parent_skill).replace(
        "# SuiteCRM Operational Skill", "# Operational Skill", 1,
    )
    alias_context = build_provenance_alias_context(request.rollouts)
    payload = {
        "task_context": request.task_context,
        "original_domain_policy": request.original_domain_policy,
        "available_tool_contracts": list(request.available_tool_contracts),
        "rollouts": list(alias_context["rollouts"]),
        "available_evidence_refs": list(alias_context["evidence_aliases"]),
        "available_policy_refs": list(alias_context["policy_aliases"]),
    }
    return DIAGNOSIS_SYSTEM_PROMPT, (
        "Diagnose this one task's three Parent rollouts.\n\n"
        f"<CURRENT_PARENT_SKILL_WITH_RULE_IDS>\n{annotated.strip()}\n</CURRENT_PARENT_SKILL_WITH_RULE_IDS>\n\n"
        "<TASK_EVIDENCE_GROUP>\n"
        + json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n</TASK_EVIDENCE_GROUP>\n\nReturn only the JSON object."
    )


def _call_nonempty_diagnosis(
    learner_call: LearnerCall, system: str, user: str, *, response_format: dict | None,
) -> str:
    empty_error = None
    for _ in range(EMPTY_RESPONSE_RETRIES + 1):
        try:
            response, _, _ = learner_call(
                LEARNER_MODEL, system, user, response_format=response_format,
            )
        except RuntimeError as error:
            if str(error) != "Learner returned an empty Skill.":
                raise
            empty_error = error
            continue
        if isinstance(response, str) and response.strip():
            return response.strip()
    raise RuntimeError(
        "v0.14 Semantic Diagnosis returned an empty response after "
        f"{EMPTY_RESPONSE_RETRIES} retries."
    ) from empty_error


def _is_structured_output_capability_error(error: Exception) -> bool:
    message = str(error).casefold()
    mentions_feature = any(value in message for value in (
        "response_format", "json_schema", "structured output",
    ))
    rejects_feature = any(value in message for value in (
        "unsupported", "not supported", "does not support", "invalid parameter",
        "invalid value", "unknown parameter", "unrecognized parameter",
        "unexpected keyword", "unavailable",
    ))
    return mentions_feature and rejects_feature


def _call_with_structured_output(
    learner_call: LearnerCall, system: str, user: str,
) -> DiagnosisResponse:
    global _STRUCTURED_OUTPUT_CAPABILITY, _STRUCTURED_OUTPUT_FALLBACK_REASON

    if _STRUCTURED_OUTPUT_CAPABILITY == "json_schema_unsupported":
        response = _call_nonempty_diagnosis(
            learner_call, system, user, response_format=None,
        )
        return DiagnosisResponse(
            response, "prompt_fallback", _STRUCTURED_OUTPUT_FALLBACK_REASON,
        )
    try:
        response = _call_nonempty_diagnosis(
            learner_call, system, user,
            response_format=SEMANTIC_DIAGNOSIS_RESPONSE_FORMAT,
        )
    except Exception as error:
        if not _is_structured_output_capability_error(error):
            raise
        _STRUCTURED_OUTPUT_CAPABILITY = "json_schema_unsupported"
        _STRUCTURED_OUTPUT_FALLBACK_REASON = str(error)
        response = _call_nonempty_diagnosis(
            learner_call, system, user, response_format=None,
        )
        return DiagnosisResponse(response, "prompt_fallback", str(error))
    _STRUCTURED_OUTPUT_CAPABILITY = "json_schema_supported"
    _STRUCTURED_OUTPUT_FALLBACK_REASON = None
    return DiagnosisResponse(response, "json_schema")


def _normalize_target_behavior_serialization(
    diagnosis: Any,
) -> dict[str, Any] | None:
    """Normalize only an explicit absent stopping boundary to its string form."""

    if not isinstance(diagnosis, dict):
        return None
    target = diagnosis.get("target_behavior")
    other_fields = TARGET_BEHAVIOR_FIELDS - {"stopping_boundary"}
    if (
        not isinstance(target, dict)
        or set(target) != TARGET_BEHAVIOR_FIELDS
        or target.get("stopping_boundary") is not None
        or any(not isinstance(target.get(field), str) for field in other_fields)
    ):
        return None
    normalized = copy.deepcopy(diagnosis)
    normalized["target_behavior"]["stopping_boundary"] = ""
    return normalized


def _serialize(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def call_diagnosis(
    request: MultiRolloutDiagnosisRequest, *, learner_call: LearnerCall = _default_learner_call,
) -> str:
    """Make one semantic learner call, with only transport-level empty retries."""

    system, user = build_diagnosis_prompts(request)
    response = _call_with_structured_output(learner_call, system, user)
    validation = parse_and_validate_diagnosis(
        request.diagnosis_id, response, experiences=request.rollouts,
        skill_sections=_parse_skill(request.current_parent_skill),
    )
    normalized = _normalize_target_behavior_serialization(validation.structured_output)
    if normalized is None:
        return response
    return DiagnosisResponse(
        _serialize(normalized), response.structured_output_mode,
        response.structured_output_fallback_reason,
    )
