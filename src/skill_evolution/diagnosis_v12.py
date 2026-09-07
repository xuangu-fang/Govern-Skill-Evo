"""Task-level multi-rollout Diagnosis prompt for Autonomous GSE v0.12."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.skill_evolution.autonomous_gse_v05_proposal import annotate_parent_skill
from src.skill_evolution.diagnosis_contract_v12 import validate_task_evidence_group

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


DIAGNOSIS_SYSTEM_PROMPT = """You are the v0.12 task-level Diagnosis component. Analyze exactly three independent Parent rollouts of one task as multi-evidence reasoning, never majority voting. Determine whether their stable behavior, key outcome/compliance contrast, and counterevidence demonstrate one Parent Skill deficiency. At most one update signal may be returned; if several issues appear, choose only the clearest, most reusable, minimally sufficient issue. Do not require 2/3 repetition and do not force an update.

Separate episode-specific manifestations from the general behavioral mechanism. Keep concrete objects in the summary/evidence, but make target_behavior and the update objective mechanism-level, transferable, evidence-bounded, and minimal. Never turn one valid trajectory ordering into a universal ordering constraint unless policy/verifier evidence requires it. A compliant-success path is counterevidence that limits update strength: do not prohibit that path without explicit policy evidence. Do not write a complex task workflow or literal replay recipe into the Skill. Do not add obligations, policies, restrictions, or scenarios absent from the evidence.

External four-state outcomes are supplied facts and must not be relabeled.
repair_policy_ids may only copy policy IDs supplied by the three verifier results.

Evidence-reference contract:
- Every evidence ref must be a JSON object with exactly two fields: source_id
  and step_ids.
- source_id must be copied from one supplied rollout.
- step_ids must always be a JSON array containing only positive integer step
  IDs from that same rollout, even when citing exactly one step.
- Correct: {"source_id":"step_001_airline_5_rollout_01","step_ids":[22]}
- Correct: {"source_id":"step_001_airline_5_rollout_03","step_ids":[3,5]}
- Incorrect: {"source_id":"...","step_id":22}
- Incorrect: {"source_id":"...","steps":[22]}
- Incorrect: "step_001_airline_5_rollout_01:22"

skill_update_relevance must be exactly one of "update", "none", or
"uncertain". Never put "skill_issue", "add", "replace", "delete", or
"relevance" in skill_update_relevance. Required attribution mapping:
- root_cause.category "skill_issue" -> skill_update_relevance "update" ->
  action "add", "replace", or "delete".
- root_cause.category "execution_issue" or "external_issue" ->
  skill_update_relevance "none" -> action "none".
- root_cause.category "uncertain" -> skill_update_relevance "uncertain" ->
  action "none".
- root_cause.category null -> skill_update_relevance "none" -> action "none".
For add, both targets are null because the Editor places it. replace/delete
must exactly target an existing section and stable rule ID.

Valid update example fragment:
{"root_cause":{"category":"skill_issue","explanation":"..."},
 "skill_update_relevance":"update",
 "update_recommendation":{"action":"add","target_section":null,
 "target_rule_id":null,"objective":"...","description":"..."}}

The angle-bracket source placeholder in the schema below is illustrative and
must be replaced with an actual supplied source_id.

Before returning, verify all of the following:
1. skill_update_relevance is exactly update, none, or uncertain.
2. Every evidence ref has exactly source_id and step_ids.
3. Every step_ids value is an integer array, including a single-step citation.
4. Every cited source and step exists in the supplied rollouts.
5. The response has exactly the requested fields.

Return exactly one tagged JSON object with exactly this shape and no prose:
<DIAGNOSIS_JSON>
{
  "task_behavior_summary":"",
  "cross_rollout_analysis":{"stable_behavior":"","key_behavior_difference":"","counterevidence":"","support_evidence_refs":[{"source_id":"<replace_with_supplied_source_id>","step_ids":[1]}],"counterevidence_refs":[]},
  "root_cause":{"category":null,"explanation":""},
  "skill_update_relevance":"none",
  "repair_policy_ids":[],
  "target_behavior":{"problem":"","trigger_condition":"","expected_behavior":""},
  "update_recommendation":{"action":"none","target_section":null,"target_rule_id":null,"objective":"","description":""}
}
</DIAGNOSIS_JSON>
"""


def build_diagnosis_prompts(request: MultiRolloutDiagnosisRequest) -> tuple[str, str]:
    if not isinstance(request, MultiRolloutDiagnosisRequest):
        raise ValueError("v0.12 requires MultiRolloutDiagnosisRequest.")
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
        raise RuntimeError("v0.12 Diagnosis returned an empty response.")
    return response.strip()
