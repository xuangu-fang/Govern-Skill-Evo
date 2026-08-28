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
    rollouts: tuple[dict[str, Any], ...]


Diagnoser = Callable[[MultiRolloutDiagnosisRequest], str]
LearnerCall = Callable[[str, str, str], tuple[str, str, dict[str, Any] | None]]


def _default_learner_call(model: str, system: str, user: str) -> tuple[str, str, dict[str, Any] | None]:
    from src.learners.stwebagentbench.generate_skill import call_learner

    return call_learner(model, system, user, temperature=0.0)


DIAGNOSIS_SYSTEM_PROMPT = """You are the v0.13 task-level Diagnosis component. Analyze exactly three independent Parent rollouts of one task in one call. Use multi-evidence reasoning, never majority voting, and return at most one update signal. Do not force an update.

Treat Task Success and Compliance as independent axes. The supplied CS, VS, CF, and VF states are external facts and must not be relabeled. Use available contrasts when informative: CS vs CF and VS vs VF hold Compliance constant to expose behavior affecting Task Success; CS vs VS and CF vs VF hold Task Success constant to expose behavior affecting Compliance. These are reasoning aids, not required pairs or voting rules. Set update_axis to task_success, compliance, both, or none. update requires an active axis; none/uncertain requires none.

Generalize entities and episodes, preserve decision predicates, repair operators, and necessary stopping boundaries. Remove task IDs, reservation/order IDs, product names, fixed amounts, literal replay recipes, and accidental workflows from the target. Preserve the problem mechanism, trigger condition, operational distinction or decision predicate, concrete repair operator, and—only when applicable—the condition that says a blocking/repeated operator is satisfied. confirmation, clarification, verification, retry, authorization, or handoff may need a stopping boundary; record-integrity rules often do not. Never add one mechanically.

Do not produce abstractions such as "unsupported information / when uncertain / verify information." A target must remain mechanism-discriminative and behaviorally testable. Example: identify cross-record field composition, trigger on overlapping record-specific attributes/prices/availability, preserve each record's ID-attribute-price-availability binding, and reason within one record.

Counterevidence is not only evidence against an update; it also limits the strength and scope of the update. A compliant-success path must remain allowed unless explicit policy evidence forbids it. If lookup then asking a cancellation reason then canceling succeeds compliantly, a repair may require obtaining the reason before cancellation but may not require asking before lookup. Do not add obligations, restrictions, universal orderings, or scenarios absent from evidence.

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
7. The response has exactly the requested fields.

Return exactly one tagged JSON object and no prose:
<DIAGNOSIS_JSON>
{
  "task_behavior_summary":"",
  "cross_rollout_analysis":{"stable_behavior":"","success_contrast":"","compliance_contrast":"","counterevidence":"","support_evidence_refs":[],"counterevidence_refs":[]},
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
    errors = validate_task_evidence_group(request.rollouts)
    if errors:
        raise ValueError(errors[0])
    annotated = annotate_parent_skill(request.current_parent_skill).replace(
        "# SuiteCRM Operational Skill", "# Operational Skill", 1
    )
    payload = {"task_context": request.task_context, "rollouts": list(request.rollouts)}
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
