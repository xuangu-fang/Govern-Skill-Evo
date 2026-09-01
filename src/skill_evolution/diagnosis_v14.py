"""Dual-axis task-level multi-rollout Diagnosis for Autonomous GSE v0.14."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.adapters.tau2.tau3_evaluation_scope_v13 import benchmark_exclusion_prompt
from src.skill_evolution.autonomous_gse_v05_proposal import _parse_skill, annotate_parent_skill
from src.skill_evolution.diagnosis_contract_v14 import (
    AXIS_RELATIONS, EVIDENCE_CONSISTENCIES, EVIDENCE_PATTERNS,
    parse_and_validate_diagnosis, repair_diagnosis_contract_fields,
    validate_task_evidence_group,
)

LEARNER_MODEL = "openai/deepseek-v4-pro"
EMPTY_RESPONSE_RETRIES = 2
SEMANTIC_REPAIR_FIELD_BY_ERROR = {
    "INVALID_COMPLIANCE_RELATION": ("behavior_analysis", "compliance_relation"),
    "INVALID_TASK_SUCCESS_RELATION": ("behavior_analysis", "task_success_relation"),
    "INVALID_EVIDENCE_CONSISTENCY": ("behavior_analysis", "evidence_consistency"),
    "INVALID_EVIDENCE_PATTERN": ("behavior_analysis", "evidence_pattern"),
}
SEMANTIC_REPAIRABLE_ERRORS = frozenset(SEMANTIC_REPAIR_FIELD_BY_ERROR)
SEMANTIC_REPAIR_ALLOWED_VALUES_BY_PATH = {
    "behavior_analysis.compliance_relation": AXIS_RELATIONS,
    "behavior_analysis.task_success_relation": AXIS_RELATIONS,
    "behavior_analysis.evidence_consistency": EVIDENCE_CONSISTENCIES,
    "behavior_analysis.evidence_pattern": EVIDENCE_PATTERNS,
}
OUTCOME_SUPPORT_CHECKPOINT = """Outcome-support checkpoint for the final update decision:
A Parent Skill coverage gap does not by itself justify root_cause.category = "skill_issue" or skill_update_relevance = "update". Decide the outcome-axis relations before deciding root cause and update relevance; do not change an outcome-axis relation to "supportive" merely to make an otherwise plausible Skill update satisfy the contract.

Use this final decision order:
1. Is there a supported Agent-controlled behavioral mechanism?
2. Is there a real Parent Skill coverage weakness?
3. Does at least one observed optimization-axis relation support the mechanism?
4. Only then may root_cause.category be "skill_issue" and skill_update_relevance be "update"; update_axis must name exactly the supportive axis or axes.

If the mechanism is supported and coverage is missing, incorrect, or underspecified, but neither task_success_relation nor compliance_relation is supportive, do not force an update. Preserve the observed coverage status, and use root_cause.category = "uncertain", skill_update_relevance = "uncertain", update_axis = "none", update_recommendation.action = "none", target_section = null, and target_rule_id = null. This represents a plausible Skill weakness whose effect on the optimization objectives is not sufficiently established by the supplied rollouts. Do not relabel it execution_issue merely to produce no update; execution_issue remains for an already_covered correct rule that the Agent failed to follow.

Example: The Agent makes a questionable intermediate decision that is absent from the Parent Skill, but later self-corrects and all supplied rollouts still finish successfully and compliantly. The behavioral mechanism and coverage weakness may be real, but if the supplied outcomes do not support an effect on Task Success or Compliance, do not emit an update. Use uncertain, no active axis, and no action rather than inventing supportive outcome evidence."""
V14_OUTPUT_CONTRACT_CLARIFICATION = """Output-contract clarification:
All six target_behavior fields must always be JSON strings. Never use null for any target_behavior field. If no special stopping boundary is needed, use "stopping_boundary": "".
For update_recommendation.action = "add", target_section and target_rule_id must both be null. Diagnosis must not choose the destination section for an add; the Editor decides placement."""
TARGET_BEHAVIOR_FIELDS = {
    "problem", "trigger_condition", "decision_boundary", "repair_operator",
    "stopping_boundary", "expected_behavior",
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
LearnerCall = Callable[[str, str, str], tuple[str, str, dict[str, Any] | None]]


class DiagnosisResponse(str):
    """String-compatible Diagnosis response carrying runtime-only audit metadata."""

    repair_trace: dict[str, Any]

    def __new__(cls, value: str, repair_trace: dict[str, Any]):
        instance = super().__new__(cls, value)
        instance.repair_trace = copy.deepcopy(repair_trace)
        return instance


@dataclass(frozen=True)
class ContractRepairParseResult:
    raw_response: str
    patch: dict[str, Any] | None
    parse_status: str
    rejection_reason: str | None


@dataclass(frozen=True)
class ContractRepairApplyResult:
    repaired_diagnosis: dict[str, Any] | None
    rejection_reason: str | None


def _default_learner_call(model: str, system: str, user: str) -> tuple[str, str, dict[str, Any] | None]:
    from src.learners.stwebagentbench.generate_skill import call_learner

    return call_learner(model, system, user, temperature=0.0)


DIAGNOSIS_SYSTEM_PROMPT = """You are the v0.14 task-level Diagnosis component. Analyze exactly three independent Parent rollouts of one task in one call and return at most one update signal. Do not force an update. An update requires one evidence-supported Agent-controlled behavioral mechanism; cross-rollout contrast is one possible evidence pattern, not the only one. If the evidence cannot select one mechanism reliably, return no update or uncertainty.

Follow this six-step reasoning order strictly. These are reasoning disciplines, not additional output fields.

Keep three judgment layers independent. Layer 1 asks whether rollout trajectories plus Policy and tool semantics support a behavioral mechanism; record that only in behavior_analysis.evidence_consistency. Layer 2 compares that supported mechanism with the Parent Skill; record that in parent_skill_coverage. Layer 3 attributes ownership in root_cause and then determines skill_update_relevance. Supportive mechanism evidence does not by itself mean skill_issue or update.

1. Identify actual Agent behavior. Analyze behavior before outcomes: identify what the Agent actually did in each rollout before looking at Task Success or Compliance attribution. Use only Agent-controlled behavior: a decision; predicate or condition check; action or tool choice; argument or value choice; ordering; retry or continuation; stopping decision; or explicit claim. Task Success or Failure labels, Compliance labels, CS/VS/CF/VF, evaluator output, environment response, tool latency, completion timing, and mere tool-result differences are not Agent behavioral mechanisms. Label contrast is not behavioral evidence, and environment difference is not Agent behavior.

2. Check task x Policy x tool feasibility at the relevant decision point before choosing an evidence pattern or attributing a Skill issue. Determine whether at least one Agent behavior could both satisfy the relevant task requirement and avoid the alleged problem while being Policy-permitted, technically supported by the available tools, and available at that decision point. Policy is normative, and tool capability does not create Policy permission. If no such behavior exists because the task requirement, Policy, and tool capability cannot be satisfied together, or Policy explicitly blocks the task-required action or state, classify external_issue with not_applicable coverage and no update; never invent a Skill repair for an infeasible requirement. Apply this check to the relevant requirement and mechanism rather than treating one infeasible subgoal as proof that every independent part of a compound task is external.

3. Determine the behavioral evidence pattern:
- contrastive: different rollouts contain different Agent-controlled behaviors, and that difference helps explain an observed outcome difference when grounded by Policy or tool semantics.
- recurrent: multiple rollouts repeat the same problematic decision mechanism, not merely the same action, tool call, task outcome, or workflow fragment. The claimed cases must share the relevant decision opportunity, the relevant condition or predicate, and the same Agent-controlled choice or omission under that condition. The repeated choice itself must constitute the diagnosed problem rather than merely co-occur with a failure. Recurrent is a semantic judgment, not a mechanical rollout-count threshold. It may be supportive without success/failure contrast only when a correct alternative was Policy-permitted, technically supported, available at the relevant decision point, and relevant to avoiding the problem. If no real alternative can be identified, use insufficient; if no legal feasible alternative exists, use external_issue.
- insufficient: no sufficiently clear Agent-controlled mechanism exists; the suspected behavior or opportunity did not occur; behavior is the same but cannot explain differing outcomes; evidence is mainly labels, environment, or benchmark effects; or attribution is unreliable. The mere fact that behavior is the same does not determine insufficiency: first check whether it supplies recurrent evidence.

4. Falsify the proposed mechanism before marking it supportive. Before marking a mechanism supportive, test it against every supplied rollout and actively search for counterexamples. For each claimed contrastive or recurrent case, compare the behavior, relevant predicate, and decision context, and verify that the claimed behavior and opportunity actually occurred. If the allegedly problematic behavior also appears under the same relevant condition in a good or compliant rollout without the predicted effect, the proposed mechanism is not sufficient unless another concrete predicate explains the difference. Use conflicting when a still-plausible mechanism has substantive support and unreconciled counterevidence; use insufficient when no reliable mechanism survives. Do not mechanically reject a mechanism merely because the same action name appears elsewhere under a different trigger, state, argument, authorization condition, or decision context. Outcomes may test or falsify an already-proposed mechanism, but they must not create one.

5. Attribute the surviving mechanism against the current annotated Parent Skill. Set parent_skill_coverage.status to:
- missing when the necessary mechanism is absent;
- incorrect when the Skill gives wrong guidance;
- underspecified when it mentions the behavior but omits an execution-critical trigger, predicate, decision boundary, feasibility condition, ordering, or stopping condition;
- already_covered when a clear, correct, executable existing rule covers it and the Agent failed to follow that rule;
- not_applicable when the mechanism has no direct Parent Skill coverage relationship, such as an external issue.
Only missing, incorrect, or underspecified coverage can support skill_issue. already_covered normally means execution_issue and no update; do not add a duplicate rule unless a separate sufficiently supported Skill mechanism exists. related_rule_ids may name only Rule IDs that actually appear in CURRENT_PARENT_SKILL_WITH_RULE_IDS. missing may use an empty list; for incorrect, underspecified, and already_covered cite the applicable existing Rule IDs whenever available.
Do not call a rule underspecified merely to enable an update. If fully following the existing rule is already sufficient to avoid the observed problem, use already_covered.

6. Use outcomes only as supporting axis evidence. Task Success and Compliance are independent observed outcomes, and their supplied values are frozen external facts: do not relabel them or re-judge Compliance. Never start from Failure and reverse-engineer a mechanism. Describe the surviving mechanism's relation to each axis separately as supportive, contradictory, insufficient, or not_applicable. Identical behavior with mixed task outcomes does not support a task-success causal claim merely because failures are the majority. Policy can independently make the Compliance relation supportive even when the Task Success relation is insufficient. Set update_axis to task_success, compliance, or both according to exactly which axis relations support a Skill repair; do not require both axes to improve.

<<V14_OUTCOME_SUPPORT_CHECKPOINT>>

Classify evidence consistency once in the overall evidence_consistency field:
- supportive: a concrete Agent-controlled behavioral mechanism is supported by contrastive or recurrent trajectory evidence; Policy/tool grounding is sound; at least one relevant outcome axis is consistent with the mechanism's expected impact; and no material counterevidence defeats the mechanism. This evaluates the mechanism itself, not Parent Skill coverage, root cause, or update eligibility.
- conflicting: the same still-plausible mechanism has substantive supporting evidence and counterevidence that cannot be reconciled. Use uncertain and no update.
- insufficient: mechanism evidence is inadequate. Use no update unless a genuine unresolved ambiguity remains.
A disproven allegation is not conflicting evidence. If no alternative plausible mechanism remains, use insufficient and no update. Recurrent positive behavior is not a reason to add a duplicate Skill rule.
In particular, recurrent + supportive + already_covered must map to execution_issue + none + update_axis none + action none when the Agent simply failed to follow the existing correct rule. Never interpret supportive as an automatic skill_issue.

A useful mechanism identifies a concrete trigger or decision boundary and the Agent action, choice, predicate, ordering, stopping decision, or claim that should change. Generalize episode-specific entities while preserving the causal predicate and repair operator. Preserve a stopping boundary only when necessary; do not invent one mechanically. Counterevidence constrains both whether an update is justified and how strong it may be. A valid compliant-success behavior should remain allowed unless Policy explicitly rules it out. Do not infer stricter ordering, broader scope, or stronger obligations than the evidence supports.

repair_policy_ids only records Policy IDs from actual violation evidence that directly support a compliance repair. It is not a complete record of Policy grounding. For a task_success-only update it may be empty even when Policy analysis establishes permission. Never invent a Policy ID merely to express that Policy permits a repair.

<<V14_OUTPUT_CONTRACT_CLARIFICATION>>

<<TAU3_BENCHMARK_EXCLUSION>>

Return exactly the requested schema. Evidence refs must contain source_id and non-empty step_ids copied from supplied rollout steps. Deterministic field mappings and target legality are enforced by the Python contract.

Output contract — use only these enum values:
- root_cause.category: "skill_issue" | "execution_issue" | "external_issue" | "uncertain" | null
- skill_update_relevance: "update" | "none" | "uncertain"
- update_axis: "task_success" | "compliance" | "both" | "none"
- update_recommendation.action: "add" | "replace" | "delete" | "none"
Required mapping:
- skill_issue -> update -> task_success | compliance | both -> add | replace | delete
- execution_issue | external_issue | null -> none -> none -> none
- uncertain -> uncertain -> none -> none
For add, target_section and target_rule_id are null. For replace/delete, both identify an existing Parent Skill rule. For none, both are null.

Return exactly one tagged JSON object and no prose:
<DIAGNOSIS_JSON>
{
  "task_behavior_summary":"",
  "behavior_analysis":{"evidence_pattern":"insufficient","stable_behavior":"","behavioral_mechanism":"","task_success_relation":"insufficient","compliance_relation":"insufficient","evidence_consistency":"insufficient","counterevidence":"","support_evidence_refs":[],"counterevidence_refs":[]},
  "parent_skill_coverage":{"status":"not_applicable","related_rule_ids":[],"explanation":""},
  "root_cause":{"category":null,"explanation":""},
  "skill_update_relevance":"none",
  "update_axis":"none",
  "repair_policy_ids":[],
  "target_behavior":{"problem":"","trigger_condition":"","decision_boundary":"","repair_operator":"","stopping_boundary":"","expected_behavior":""},
  "update_recommendation":{"action":"none","target_section":null,"target_rule_id":null,"objective":"","description":""}
}
</DIAGNOSIS_JSON>
""".replace(
    "<<V14_OUTCOME_SUPPORT_CHECKPOINT>>", OUTCOME_SUPPORT_CHECKPOINT,
).replace(
    "<<V14_OUTPUT_CONTRACT_CLARIFICATION>>", V14_OUTPUT_CONTRACT_CLARIFICATION,
).replace("<<TAU3_BENCHMARK_EXCLUSION>>", benchmark_exclusion_prompt("diagnosis"))


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
        "# SuiteCRM Operational Skill", "# Operational Skill", 1
    )
    payload = {
        "task_context": request.task_context,
        "original_domain_policy": request.original_domain_policy,
        "available_tool_contracts": list(request.available_tool_contracts),
        "rollouts": list(request.rollouts),
    }
    return DIAGNOSIS_SYSTEM_PROMPT, (
        "Diagnose this one task's three Parent rollouts.\n\n"
        f"<CURRENT_PARENT_SKILL_WITH_RULE_IDS>\n{annotated.strip()}\n</CURRENT_PARENT_SKILL_WITH_RULE_IDS>\n\n"
        "<TASK_EVIDENCE_GROUP>\n"
        + json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n</TASK_EVIDENCE_GROUP>\n\nReturn only the DIAGNOSIS_JSON block."
    )


def _call_nonempty_diagnosis(
    learner_call: LearnerCall, system: str, user: str,
) -> str:
    empty_error = None
    for _ in range(EMPTY_RESPONSE_RETRIES + 1):
        try:
            response, _, _ = learner_call(LEARNER_MODEL, system, user)
        except RuntimeError as error:
            if str(error) != "Learner returned an empty Skill.":
                raise
            empty_error = error
            continue
        if isinstance(response, str) and response.strip():
            return response.strip()
    raise RuntimeError(
        "v0.14 Diagnosis returned an empty response after "
        f"{EMPTY_RESPONSE_RETRIES} retries."
    ) from empty_error


def _tag_bare_json_response(response: str) -> str:
    """Add the required envelope to a bare JSON object without changing its content."""

    stripped = response.strip()
    try:
        parsed = json.loads(stripped)
    except (TypeError, json.JSONDecodeError):
        return stripped
    if not isinstance(parsed, dict):
        return stripped
    return f"<DIAGNOSIS_JSON>{stripped}</DIAGNOSIS_JSON>"


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


def _call_contract_repair(
    learner_call: LearnerCall, *, task_context: dict[str, Any],
    original_domain_policy: str, available_tool_contracts: tuple[dict[str, Any], ...],
    rollouts: tuple[dict[str, Any], ...],
    original_diagnosis: dict[str, Any], validation_errors: tuple[str, ...],
) -> str:
    """Make one bounded field-patch call for whitelisted vocabulary errors."""

    allowed_fields = {
        ".".join(SEMANTIC_REPAIR_FIELD_BY_ERROR[error]): sorted(
            SEMANTIC_REPAIR_ALLOWED_VALUES_BY_PATH[
                ".".join(SEMANTIC_REPAIR_FIELD_BY_ERROR[error])
            ]
        )
        for error in validation_errors
    }
    repair_system = """You are the v0.14 bounded Diagnosis contract repair component.
You are not re-performing Diagnosis. The original Diagnosis is frozen except for the explicitly listed contract-invalid fields. Return only one DIAGNOSIS_REPAIR_JSON object containing exactly the allowed field paths. Do not modify or restate any other Diagnosis field. Do not introduce new mechanisms, evidence, source IDs, Policy claims, root causes, target behaviors, or update recommendations. Return no prose."""
    evidence_context = {
        "task_context": task_context,
        "original_domain_policy": original_domain_policy,
        "available_tool_contracts": list(available_tool_contracts),
        "rollouts": list(rollouts),
    }
    repair_user = (
        "<REPAIR_EVIDENCE_CONTEXT>\n"
        + json.dumps(evidence_context, ensure_ascii=False, sort_keys=True)
        + "\n</REPAIR_EVIDENCE_CONTEXT>\n\n"
        + "<FROZEN_ORIGINAL_DIAGNOSIS>\n"
        + json.dumps(original_diagnosis, ensure_ascii=False, sort_keys=True)
        + "\n</FROZEN_ORIGINAL_DIAGNOSIS>\n\n"
        + "<PYTHON_CONTRACT_VALIDATION_ERRORS>\n"
        + json.dumps(list(validation_errors), ensure_ascii=False)
        + "\n</PYTHON_CONTRACT_VALIDATION_ERRORS>\n\n"
        + "<PYTHON_ALLOWED_REPAIR_FIELDS_AND_VALUES>\n"
        + json.dumps(allowed_fields, ensure_ascii=False, sort_keys=True)
        + "\n</PYTHON_ALLOWED_REPAIR_FIELDS_AND_VALUES>\n\n"
        + "Return exactly this envelope with a JSON object whose keys exactly match the allowed fields:\n"
        + "<DIAGNOSIS_REPAIR_JSON>{...}</DIAGNOSIS_REPAIR_JSON>"
    )
    response, _, _ = learner_call(LEARNER_MODEL, repair_system, repair_user)
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("v0.14 Diagnosis contract repair returned an empty response.")
    return response.strip()


def _parse_contract_repair_patch(response: str) -> ContractRepairParseResult:
    opening = "<DIAGNOSIS_REPAIR_JSON>"
    closing = "</DIAGNOSIS_REPAIR_JSON>"
    stripped = response.strip()
    if stripped.startswith(opening) and stripped.endswith(closing):
        parse_status = "tagged_json_object"
        payload = stripped[len(opening):-len(closing)].strip()
        try:
            patch = json.loads(payload)
        except json.JSONDecodeError:
            return ContractRepairParseResult(
                response, None, "tagged_invalid_json", "INVALID_JSON",
            )
    else:
        try:
            patch = json.loads(stripped)
        except json.JSONDecodeError:
            return ContractRepairParseResult(
                response, None, "invalid_envelope", "INVALID_ENVELOPE",
            )
        parse_status = "bare_json_object"
    if not isinstance(patch, dict):
        return ContractRepairParseResult(
            response, None, parse_status.replace("object", "non_object"),
            "PATCH_NOT_OBJECT",
        )
    return ContractRepairParseResult(response, patch, parse_status, None)


def _apply_semantic_contract_patch(
    original: dict[str, Any], validation_errors: tuple[str, ...], patch: Any,
) -> ContractRepairApplyResult:
    """Apply exactly the Python-authorized vocabulary fields to a deep copy."""

    errors = set(validation_errors)
    if not errors or not errors <= SEMANTIC_REPAIRABLE_ERRORS or not isinstance(patch, dict):
        return ContractRepairApplyResult(None, "PATCH_APPLY_FAILED")
    allowed_paths = {
        ".".join(SEMANTIC_REPAIR_FIELD_BY_ERROR[error]) for error in errors
    }
    if set(patch) != allowed_paths:
        return ContractRepairApplyResult(None, "PATCH_KEYS_MISMATCH")
    if any(
        value not in SEMANTIC_REPAIR_ALLOWED_VALUES_BY_PATH[path]
        for path, value in patch.items()
    ):
        return ContractRepairApplyResult(None, "INVALID_PATCH_VALUE")

    repaired = copy.deepcopy(original)
    for error in validation_errors:
        path = SEMANTIC_REPAIR_FIELD_BY_ERROR[error]
        target: Any = repaired
        for key in path[:-1]:
            if not isinstance(target, dict) or not isinstance(target.get(key), dict):
                return ContractRepairApplyResult(None, "PATCH_APPLY_FAILED")
            target = target[key]
        target[path[-1]] = patch[".".join(path)]
    return ContractRepairApplyResult(repaired, None)


def call_diagnosis(request: MultiRolloutDiagnosisRequest, *, learner_call: LearnerCall = _default_learner_call) -> str:
    system, user = build_diagnosis_prompts(request)
    response = _tag_bare_json_response(
        _call_nonempty_diagnosis(learner_call, system, user)
    )
    initial_response = response
    skill_sections = _parse_skill(request.current_parent_skill)
    validation = parse_and_validate_diagnosis(
        request.diagnosis_id, response, experiences=request.rollouts,
        skill_sections=skill_sections,
    )
    normalized = _normalize_target_behavior_serialization(
        validation.structured_output,
    )
    if normalized is not None:
        response = (
            "<DIAGNOSIS_JSON>"
            + json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
            + "</DIAGNOSIS_JSON>"
        )
        validation = parse_and_validate_diagnosis(
            request.diagnosis_id, response, experiences=request.rollouts,
            skill_sections=skill_sections,
        )
    if validation.valid:
        return DiagnosisResponse(response, {"attempted": False})
    repaired = repair_diagnosis_contract_fields(
        validation.structured_output, validation.validation_errors,
    )
    if repaired is not None:
        repaired_response = (
            "<DIAGNOSIS_JSON>"
            + json.dumps(repaired, ensure_ascii=False, separators=(",", ":"))
            + "</DIAGNOSIS_JSON>"
        )
        repaired_validation = parse_and_validate_diagnosis(
            request.diagnosis_id, repaired_response, experiences=request.rollouts,
            skill_sections=skill_sections,
        )
        if repaired_validation.valid:
            return DiagnosisResponse(repaired_response, {"attempted": False})
        response, validation = repaired_response, repaired_validation
    errors = set(validation.validation_errors)
    if (
        not errors
        or not errors <= SEMANTIC_REPAIRABLE_ERRORS
        or not isinstance(validation.structured_output, dict)
    ):
        return DiagnosisResponse(response, {"attempted": False})
    allowed_fields = {
        ".".join(SEMANTIC_REPAIR_FIELD_BY_ERROR[error]): sorted(
            SEMANTIC_REPAIR_ALLOWED_VALUES_BY_PATH[
                ".".join(SEMANTIC_REPAIR_FIELD_BY_ERROR[error])
            ]
        )
        for error in validation.validation_errors
    }
    repair_response = _call_contract_repair(
        learner_call, task_context=request.task_context,
        original_domain_policy=request.original_domain_policy,
        available_tool_contracts=request.available_tool_contracts,
        rollouts=request.rollouts, original_diagnosis=validation.structured_output,
        validation_errors=validation.validation_errors,
    )
    parse_result = _parse_contract_repair_patch(repair_response)
    trace = {
        "attempted": True,
        "initial_raw_response": initial_response,
        "validation_errors_before": list(validation.validation_errors),
        "allowed_fields": allowed_fields,
        "raw_repair_response": repair_response,
        "parse_status": parse_result.parse_status,
        "parsed_patch": copy.deepcopy(parse_result.patch),
        "rejection_reason": parse_result.rejection_reason,
        "final_validation": {
            "valid": False, "errors": list(validation.validation_errors),
        },
    }
    if parse_result.patch is None:
        return DiagnosisResponse(response, trace)
    apply_result = _apply_semantic_contract_patch(
        validation.structured_output, validation.validation_errors, parse_result.patch,
    )
    if apply_result.repaired_diagnosis is None:
        trace["rejection_reason"] = apply_result.rejection_reason
        return DiagnosisResponse(response, trace)
    semantic_repair_response = (
        "<DIAGNOSIS_JSON>"
        + json.dumps(
            apply_result.repaired_diagnosis, ensure_ascii=False, separators=(",", ":"),
        )
        + "</DIAGNOSIS_JSON>"
    )
    final_validation = parse_and_validate_diagnosis(
        request.diagnosis_id, semantic_repair_response, experiences=request.rollouts,
        skill_sections=skill_sections,
    )
    trace["final_validation"] = {
        "valid": final_validation.valid,
        "errors": list(final_validation.validation_errors),
    }
    if final_validation.valid:
        return DiagnosisResponse(semantic_repair_response, trace)
    trace["rejection_reason"] = "FINAL_VALIDATION_FAILED"
    return DiagnosisResponse(response, trace)
