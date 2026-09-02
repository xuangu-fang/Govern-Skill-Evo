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
        "support_evidence_refs": [],
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
    "repair_policy_refs": [],
    "target_behavior": {
        "problem": "", "trigger_condition": "", "decision_boundary": "",
        "repair_operator": "", "stopping_boundary": "", "expected_behavior": "",
    },
    "edit_intent": "not_applicable",
}

_EMPTY_ALIAS_ARRAY_SCHEMA = {"type": "array", "maxItems": 0}
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
                "support_evidence_refs": _EMPTY_ALIAS_ARRAY_SCHEMA,
                "counterevidence_refs": _EMPTY_ALIAS_ARRAY_SCHEMA,
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
        "repair_policy_refs": _EMPTY_ALIAS_ARRAY_SCHEMA,
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


def _alias_array_schema(aliases: list[str]) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "array"}
    if aliases:
        schema["items"] = {"type": "string", "enum": aliases}
    else:
        schema["maxItems"] = 0
    return schema


def build_semantic_diagnosis_response_format(
    alias_context: dict[str, Any],
) -> dict[str, Any]:
    """Build the strict response schema from aliases available for one task."""

    evidence_refs = list(alias_context["evidence_aliases"])
    policy_refs = list(alias_context["policy_aliases"])
    schema = copy.deepcopy(SEMANTIC_DIAGNOSIS_JSON_SCHEMA)
    mechanism = schema["properties"]["behavioral_mechanism"]["properties"]
    mechanism["support_evidence_refs"] = _alias_array_schema(evidence_refs)
    mechanism["counterevidence_refs"] = _alias_array_schema(evidence_refs)
    schema["properties"]["repair_policy_refs"] = _alias_array_schema(policy_refs)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "v14_semantic_diagnosis",
            "strict": True,
            "schema": schema,
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

2. Identify one candidate problematic Agent-controlled behavioral mechanism. contrastive_support / recurrent_support must support a problematic behavioral mechanism or repair hypothesis, not merely a stable behavior pattern. If the Agent already executes the target behavior correctly across all relevant rollouts, do not create an update merely because the Parent Skill does not explicitly encode that behavior. Stable correct behavior may be positive or counterevidence, but is not itself a Skill issue.

3. Compare all three rollouts at the relevant predicate and decision opportunity, then collect cross-rollout evidence. Do not assign the final evidence_status yet. Select supporting and counter evidence only with E### references shown directly on supplied trajectory steps. support_evidence_refs and counterevidence_refs must be disjoint. Before citing evidence as support or counterevidence, verify that the claimed fact is actually supported by that step and the necessary prior context in the same rollout. Do not infer that required information was absent merely because it was not repeated immediately before the action; check whether it had already been supplied earlier in the trajectory.

4. Falsify the candidate mechanism against all three rollouts. Actively search for same-condition counterexamples, different predicates, missing decision opportunities, and cases where the predicted effect does not occur. Compare the relevant predicate, decision opportunity, behavior, and predicted effect in every rollout. A rollout without the relevant decision opportunity is neither support nor counterevidence for that mechanism. Do not preserve a mechanism merely because it initially looked plausible. A disproven allegation is insufficient, not conflicting. Counterevidence must directly constrain the proposed causal mechanism or behavior change.

5. Evaluate feasibility of a correct Agent handling path at the relevant decision point using task requirements, the original Policy, available tool contracts, and relevant environment state. Feasibility may constrain whether a repair is actionable, but must not create mechanism evidence. feasible, infeasible, or uncertain must not turn insufficient evidence into recurrent_support, contrastive_support, or conflicting evidence. Policy is normative; tool capability cannot create Policy permission.

feasible: At the relevant decision point, at least one correct Agent handling path was available that was simultaneously consistent with the task, permitted by the original Policy, and technically supported. A correct handling path may include performing the requested action, offering a permitted alternative, correctly refusing a prohibited request, requesting required information or authorization, or escalating when Policy requires it. If the actual rollouts already demonstrate a correct, compliant, tool-supported handling path, feasibility = feasible. Do not use uncertain merely because no problematic mechanism was found.

infeasible: No correct Agent handling path existed under the task requirements, original Policy, available tools, and relevant environment state. The user's preferred action being prohibited or unavailable does not by itself make the situation infeasible if the Agent still had a correct permitted way to handle the request.

uncertain: A relevant problematic decision point has been identified, but the supplied task, Policy, or tool evidence is insufficient to determine whether any correct handling path was actually available. Do not use uncertain merely because no problematic mechanism was found.

Evidence status answers whether a reliable Agent-controlled problematic mechanism exists. Feasibility answers whether a correct, Policy-permitted, tool-supported Agent handling path existed. Outcome relation answers whether the problematic mechanism affected Task Success or Compliance. These three judgments are independent.

6. Only after falsification and the separate feasibility assessment, assign the final evidence_status based on mechanism evidence:
- contrastive_support: At least one rollout exhibits the problematic behavior and at least one matched rollout exhibits the correct alternative under the same relevant predicate and decision opportunity. The matched correct behavior is supporting contrastive evidence, not counterevidence.
- recurrent_support: The same problematic Agent-controlled mechanism repeats in multiple rollouts under the same relevant predicate and decision opportunity. Different decision opportunities do not count toward recurrence. If matched problematic and correct behaviors are both observed under comparable decision opportunities, prefer contrastive_support over recurrent_support.
- conflicting: Substantive evidence directly undermines the proposed causal mechanism. This includes the same claimed problematic behavior without the predicted adverse effect, a supposedly supporting rollout that lacks the causal predicate, an alleged correct alternative that was not actually available, or matched evidence supporting mutually incompatible causal explanations. A matched correct alternative behavior is not by itself counterevidence; it may be exactly the contrast required for contrastive_support.
- insufficient: No reliable problematic mechanism can be established because evidence is too weak, not comparable, or the relevant decision opportunity is absent. A rollout without the relevant decision opportunity is neither support nor counterevidence for that mechanism.
The final evidence_status must reflect the mechanism evidence after falsification, not feasibility or the initial hypothesis.

7. Compare the mechanism with the annotated Parent Skill:
- missing: the necessary mechanism is absent.
- incorrect: an existing rule gives wrong guidance.
- underspecified: a related rule omits an execution-critical trigger, predicate, boundary, ordering, feasibility condition, or stopping condition.
- already_covered: a clear, correct, executable existing rule covers the mechanism and the Agent did not follow it.
- not_applicable: the mechanism has no direct Parent Skill coverage relationship.
Only cite Rule IDs present in CURRENT_PARENT_SKILL_WITH_RULE_IDS. Do not label a rule underspecified merely to enable an update.

8. Judge Task Success and Compliance outcome relation independently. Use supports, contradicts, insufficient, or not_applicable. Outcomes may test an already-proposed mechanism but must not create one. Policy may support a Compliance relationship even when Task Success evidence is insufficient. Do not derive or output an update axis.

supports: The observed outcome supports the causal claim that the identified problematic behavioral mechanism should be repaired on this axis.

contradicts: The observed outcome provides counterevidence against that repair attribution.

Do not use "contradicts" merely because the task failed or because the trajectory violated Policy.

Examples:
- A problematic behavior occurs in a violating rollout while the correct alternative is compliant -> compliance = supports.
- A recurrent problematic behavior contributes to task failure -> task_success = supports.

Task Success and Compliance labels are observational evidence. The original domain Policy is the normative authority. If a Compliance label appears inconsistent with Policy/tool-grounded behavior analysis, do not let the label alone create a Skill update.

A locally suboptimal behavior does not by itself imply task_success = supports. If the rollout ultimately achieves the official Task Success outcome and the evidence only shows extra dialogue, user correction, inefficiency, a recoverable detour, or delayed completion, use task_success = insufficient unless the supplied Task Success evidence explicitly demonstrates degradation on the official Task Success axis. Do not invent efficiency, user burden, interaction cost, or any optimization axis beyond Task Success and Compliance.

9. Produce target_behavior and edit_intent. Describe target behavior semantically: the problem, trigger, decision boundary, repair operator, necessary stopping boundary, and expected behavior. Generalize incidental episode values while preserving causal predicates. Do not convert a semantic authorization, confirmation, consent, or intent condition into lexical substring matching unless the authoritative Policy explicitly requires an exact literal token. Confirmation must semantically and unambiguously authorize the complete listed action details and intended scope. A phrase that negates confirmation or confirms only part of an action bundle does not authorize the full action. All six target_behavior fields are strings; use an empty string when no special stopping boundary is needed.

edit_intent is limited to replace, delete, or not_applicable. For missing coverage use not_applicable because Python derives add. For incorrect or underspecified coverage, use replace or delete only when that is the intended treatment of the cited existing rule. For already_covered or not_applicable coverage use not_applicable. This field is consulted only if the deterministic compiler finds the Diagnosis update-eligible.

repair_policy_refs may contain only P### references shown in supplied violation evidence that directly ground the compliance repair.

Use only E### references supplied for this task. Use only P### references supplied for this task. If none apply, return []. Never copy raw source IDs, step IDs, or canonical Policy IDs into these fields.

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


def build_diagnosis_prompts(
    request: MultiRolloutDiagnosisRequest, *,
    alias_context: dict[str, Any] | None = None,
) -> tuple[str, str]:
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
    if alias_context is None:
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
        "invalidparameter", "invalid value", "unknown parameter", "unknownparameter",
        "unrecognized parameter",
        "unexpected keyword", "unavailable",
    ))
    return mentions_feature and rejects_feature


def _call_with_structured_output(
    learner_call: LearnerCall, system: str, user: str,
    response_format: dict[str, Any],
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
            learner_call, system, user, response_format=response_format,
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

    alias_context = build_provenance_alias_context(request.rollouts)
    system, user = build_diagnosis_prompts(request, alias_context=alias_context)
    response_format = build_semantic_diagnosis_response_format(alias_context)
    response = _call_with_structured_output(
        learner_call, system, user, response_format,
    )
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
