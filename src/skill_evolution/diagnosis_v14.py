"""Dual-axis task-level multi-rollout Diagnosis for Autonomous GSE v0.14."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.adapters.tau2.tau3_evaluation_scope_v13 import benchmark_exclusion_prompt
from src.skill_evolution.autonomous_gse_v05_proposal import _parse_skill, annotate_parent_skill
from src.skill_evolution.diagnosis_contract_v14 import (
    parse_and_validate_diagnosis, repair_diagnosis_contract_fields,
    validate_task_evidence_group,
)

LEARNER_MODEL = "openai/deepseek-v4-pro"
EMPTY_RESPONSE_RETRIES = 2


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

Classify evidence consistency once in the overall evidence_consistency field:
- supportive: a concrete Agent-controlled behavioral mechanism is supported by contrastive or recurrent trajectory evidence; Policy/tool grounding is sound; at least one relevant outcome axis is consistent with the mechanism's expected impact; and no material counterevidence defeats the mechanism. This evaluates the mechanism itself, not Parent Skill coverage, root cause, or update eligibility.
- conflicting: the same still-plausible mechanism has substantive supporting evidence and counterevidence that cannot be reconciled. Use uncertain and no update.
- insufficient: mechanism evidence is inadequate. Use no update unless a genuine unresolved ambiguity remains.
A disproven allegation is not conflicting evidence. If no alternative plausible mechanism remains, use insufficient and no update. Recurrent positive behavior is not a reason to add a duplicate Skill rule.
In particular, recurrent + supportive + already_covered must map to execution_issue + none + update_axis none + action none when the Agent simply failed to follow the existing correct rule. Never interpret supportive as an automatic skill_issue.

A useful mechanism identifies a concrete trigger or decision boundary and the Agent action, choice, predicate, ordering, stopping decision, or claim that should change. Generalize episode-specific entities while preserving the causal predicate and repair operator. Preserve a stopping boundary only when necessary; do not invent one mechanically. Counterevidence constrains both whether an update is justified and how strong it may be. A valid compliant-success behavior should remain allowed unless Policy explicitly rules it out. Do not infer stricter ordering, broader scope, or stronger obligations than the evidence supports.

repair_policy_ids only records Policy IDs from actual violation evidence that directly support a compliance repair. It is not a complete record of Policy grounding. For a task_success-only update it may be empty even when Policy analysis establishes permission. Never invent a Policy ID merely to express that Policy permits a repair.

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
""".replace("<<TAU3_BENCHMARK_EXCLUSION>>", benchmark_exclusion_prompt("diagnosis"))


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


def call_diagnosis(request: MultiRolloutDiagnosisRequest, *, learner_call: LearnerCall = _default_learner_call) -> str:
    system, user = build_diagnosis_prompts(request)
    response = _call_nonempty_diagnosis(learner_call, system, user)
    skill_sections = _parse_skill(request.current_parent_skill)
    validation = parse_and_validate_diagnosis(
        request.diagnosis_id, response, experiences=request.rollouts,
        skill_sections=skill_sections,
    )
    if validation.valid:
        return response
    repaired = repair_diagnosis_contract_fields(
        validation.structured_output, validation.validation_errors,
    )
    if repaired is None:
        return response
    repaired_response = (
        "<DIAGNOSIS_JSON>"
        + json.dumps(repaired, ensure_ascii=False, separators=(",", ":"))
        + "</DIAGNOSIS_JSON>"
    )
    repaired_validation = parse_and_validate_diagnosis(
        request.diagnosis_id, repaired_response, experiences=request.rollouts,
        skill_sections=skill_sections,
    )
    return repaired_response if repaired_validation.valid else response
