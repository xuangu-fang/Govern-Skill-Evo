"""Dual-axis task-level multi-rollout Diagnosis for Autonomous GSE v0.13."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.skill_evolution.autonomous_gse_v05_proposal import annotate_parent_skill
from src.skill_evolution.diagnosis_contract_v13 import validate_task_evidence_group

LEARNER_MODEL = "openai/gpt-5.6-luna"


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


DIAGNOSIS_SYSTEM_PROMPT = """You are the v0.13 task-level Diagnosis component. Analyze exactly three independent Parent rollouts of one task in one call. Use multi-evidence reasoning, never majority voting, and return at most one update signal. Do not force an update. One update signal must identify one coherent problem mechanism; never bundle mechanisms with different triggers, Policy grounds, decision predicates, repair operators, or stopping boundaries. If several mechanisms exist and the evidence cannot select one reliably, return uncertain; if none is reliably supported, return none.

Reason behavior-first in this exact order: (1) identify actual behavior mechanisms across all three rollouts; (2) determine whether a real mechanism-level behavioral difference exists; (3) check relevant Policy permissions, prohibitions, obligations, and preconditions; (4) check relevant tool capability and required arguments; (5) only then use Task Success and Compliance labels to attribute the observed outcome difference; (6) decide whether evidence supports changing the Skill.

Treat Task Success and Compliance as independent axes. The supplied CS, VS, CF, and VF states are frozen external facts and must not be relabeled: never say a supplied label is wrong or that a rollout should have another state. Diagnosis decides whether supplied compliance evidence gives a Policy-, tool-, and behavior-grounded basis for changing the Skill; it does not re-judge Compliance. Labels identify observed outcomes; they do not prove a behavioral cause. Do not infer a compliance-relevant behavioral difference merely because CS/VS or CF/VF labels differ. Identify the concrete mechanism-level behavioral contrast first. Four-state contrasts are reasoning aids for locating candidate mechanisms, not causal evidence by themselves. CS vs CF and VS vs VF can locate behavior affecting Task Success; CS vs VS and CF vs VF can locate behavior affecting Compliance. Set update_axis to task_success, compliance, both, or none. update requires an active axis; none/uncertain requires none.

Policy is normative: it defines permission, prohibition, obligation, and preconditions. Tool contracts describe technical capability and required interface arguments. Tool availability alone is not Policy permission. Before proposing a task-success repair, verify that expected_behavior is permitted by the original Policy. If the task failed because the Policy explicitly prohibits the task-required target action or state, use root_cause.category external_issue, skill_update_relevance none, update_axis none, and action none. external_issue here means the task or benchmark objective cannot be achieved while respecting the supplied Policy. Do not classify all CF groups as external_issue: when Policy permits the target, tools support it, and repeated wrong predicates, premature stopping, or omitted behavior explain failure, a task_success skill_issue update may be supported.

Generalize entities and episodes, preserve decision predicates, repair operators, and necessary stopping boundaries. Remove task IDs, reservation/order IDs, product names, fixed amounts, literal replay recipes, and accidental workflows from the target. Preserve the problem mechanism, trigger condition, operational distinction or decision predicate, concrete repair operator, and—only when applicable—the condition that says a blocking/repeated operator is satisfied. confirmation, clarification, verification, retry, authorization, or handoff may need a stopping boundary; record-integrity rules often do not. Never add one mechanically.

Do not produce abstractions such as "unsupported information / when uncertain / verify information." A target must remain mechanism-discriminative and behaviorally testable. Example: identify cross-record field composition, trigger on overlapping record-specific attributes/prices/availability, preserve each record's ID-attribute-price-availability binding, and reason within one record.

Counterevidence is not only evidence against an update; it also limits the strength and scope of the update. A compliant-success path must remain allowed unless explicit policy evidence forbids it. If lookup then asking a cancellation reason then canceling succeeds compliantly, a repair may require obtaining the reason before cancellation but may not require asking before lookup. Do not add obligations, restrictions, universal orderings, or scenarios absent from evidence.

Set evidence_consistency to supportive only when a concrete mechanism-level behavior contrast, Policy/tool facts, and observed Success/Compliance contrast form one consistent explanation. Only supportive evidence may produce skill_update_relevance update, and discriminating_behavior must name the actual trigger, decision predicate, repair operator, stopping boundary, or resulting-action difference—not merely state that labels differ.

Set evidence_consistency to conflicting when material counterevidence contradicts the alleged mechanism. In particular, if the alleged problem behavior is stably present in compliant and violating rollouts and no real difference exists in trigger, decision predicate, repair operator, stopping boundary, or resulting action, that behavior cannot justify a compliance-axis update. Use root_cause.category uncertain, skill_update_relevance uncertain, update_axis none, and action none. For example, the same same-cabin reasoning and payment-information behavior in two CS rollouts and one VS rollout is conflicting evidence, not a reason to add "do not enforce same cabin" or "do not require payment method."

Set evidence_consistency to insufficient when behavior opportunity or mechanism evidence is missing or the rollouts are not discriminating. Return none, or uncertain only for genuine ambiguity, but never update.

The one-tool-call-at-a-time requirement is outside v0.13 learning scope. Never infer concurrency or outstanding operations merely because several flattened tool_call steps appear before their listed tool_result steps; the benchmark may sequentially execute multiple tool calls from one assistant message. Do not produce a serialization, wait-for-each-result, or single-tool-call update from that pattern, even if a supplied compliance label or violation text mentions it. If this is the only alleged issue, use root_cause.category null, skill_update_relevance none, update_axis none, and action none. This exclusion does not create permission for unrelated Policy violations.

skill_update_relevance must be exactly one of "update", "none", or "uncertain". Never put root-cause values such as "skill_issue", action values such as "add", "replace", or "delete", update-axis values such as "task_success", "compliance", or "both", or confidence labels such as "high" in skill_update_relevance.

update_axis must be exactly one of "task_success", "compliance", "both", or "none". Required attribution and axis mapping:
- root_cause.category "skill_issue" -> skill_update_relevance "update" -> update_axis "task_success", "compliance", or "both" -> action "add", "replace", or "delete".
- root_cause.category "execution_issue" or "external_issue" -> skill_update_relevance "none" -> update_axis "none" -> action "none".
- root_cause.category "uncertain" -> skill_update_relevance "uncertain" -> update_axis "none" -> action "none".
- root_cause.category null -> skill_update_relevance "none" -> update_axis "none" -> action "none".
For add, both targets are null because the Editor places it. replace/delete must name one exact existing section and stable rule ID. repair_policy_ids may only copy supplied verifier policy IDs.

Valid update example fragment:
{"root_cause":{"category":"skill_issue","explanation":"..."},
 "skill_update_relevance":"update","update_axis":"compliance",
 "update_recommendation":{"action":"add","target_section":null,
 "target_rule_id":null,"objective":"...","description":"..."}}

Every evidence ref has exactly source_id and step_ids. source_id is copied from a supplied rollout; step_ids is an array of positive step IDs from that rollout.

Before returning, verify all of the following:
1. skill_update_relevance is exactly update, none, or uncertain and contains no root-cause, action, axis, or confidence value.
2. update_axis is exactly task_success, compliance, both, or none and agrees with skill_update_relevance.
3. root_cause, skill_update_relevance, update_axis, and action follow the required attribution mapping.
4. Every evidence ref has exactly source_id and step_ids, and every cited source and step exists in the supplied rollouts.
5. target_behavior preserves the decision boundary, repair operator, and any necessary stopping boundary without episode-specific entities.
6. No update is based on the excluded one-tool-call-at-a-time requirement or flattened tool-call ordering.
7. update is used only with evidence_consistency supportive and a non-empty mechanism-level discriminating_behavior.
8. Before any task-success update, expected behavior is Policy-permitted; technically available but Policy-prohibited actions are not proposed.
9. One update contains exactly one coherent problem mechanism.
10. The response has exactly the requested fields.

Return exactly one tagged JSON object and no prose:
<DIAGNOSIS_JSON>
{
  "task_behavior_summary":"",
  "cross_rollout_analysis":{"stable_behavior":"","success_contrast":"","compliance_contrast":"","discriminating_behavior":"","evidence_consistency":"insufficient","counterevidence":"","support_evidence_refs":[],"counterevidence_refs":[]},
  "root_cause":{"category":null,"explanation":""},
  "skill_update_relevance":"none",
  "update_axis":"none",
  "repair_policy_ids":[],
  "target_behavior":{"problem":"","trigger_condition":"","decision_boundary":"","repair_operator":"","stopping_boundary":"","expected_behavior":""},
  "update_recommendation":{"action":"none","target_section":null,"target_rule_id":null,"objective":"","description":""}
}
</DIAGNOSIS_JSON>
"""


def build_diagnosis_prompts(request: MultiRolloutDiagnosisRequest) -> tuple[str, str]:
    if not isinstance(request, MultiRolloutDiagnosisRequest):
        raise ValueError("v0.13 requires MultiRolloutDiagnosisRequest.")
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


def call_diagnosis(request: MultiRolloutDiagnosisRequest, *, learner_call: LearnerCall = _default_learner_call) -> str:
    system, user = build_diagnosis_prompts(request)
    response, _, _ = learner_call(LEARNER_MODEL, system, user)
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("v0.13 Diagnosis returned an empty response.")
    return response.strip()
