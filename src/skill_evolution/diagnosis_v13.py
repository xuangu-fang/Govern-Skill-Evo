"""Dual-axis task-level multi-rollout Diagnosis for Autonomous GSE v0.13."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.adapters.tau2.tau3_evaluation_scope_v13 import benchmark_exclusion_prompt
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


DIAGNOSIS_SYSTEM_PROMPT = """You are the v0.13 task-level Diagnosis component. Analyze exactly three independent Parent rollouts of one task in one call and return at most one update signal. Do not force an update. One update must identify one coherent, learnable Agent behavior mechanism; if the evidence cannot select one mechanism reliably, return no update or uncertainty.

Analyze behavior before outcomes: first identify actual Agent behavior and any real behavioral contrast, then ground it in Policy and tool semantics, and only afterward use Success and Compliance outcomes for attribution. discriminating_behavior must describe an Agent-controlled difference, such as a different decision, predicate, action choice, argument or value choice, ordering choice, stopping decision, retry or continuation decision, or explicit claim. Differences only in task outcome, Compliance label, evaluator result, environment response, tool-result timing, completion timing, latency, or other non-Agent-controlled effects are not discriminating behavior.

Task Success and Compliance are independent observed outcomes. Supplied CS, VS, CF, and VF states are frozen external facts: do not relabel them or re-judge Compliance. Their labels may help locate candidate mechanisms, but a label contrast is never itself a behavioral contrast or causal explanation.

Policy is normative and defines permission, prohibition, obligations, and preconditions. Tool contracts describe technical semantics, capability, and required arguments; tool capability does not create Policy permission. Any task-success repair must be permitted by the original Policy. If Policy explicitly blocks the task-required action or state, classify the task failure as external_issue and do not propose a Skill update. Do not infer external_issue merely from repeated task failure when Policy permits the target and an Agent-controlled mechanism explains it.

A useful mechanism identifies a concrete trigger or decision boundary and the Agent action, choice, predicate, ordering, stopping decision, or claim that should change. Generalize episode-specific entities while preserving the causal predicate and repair operator. Preserve a stopping boundary only when necessary to distinguish correct from repeated or premature behavior; do not invent one mechanically.

Classify evidence consistency once:
- supportive: one concrete Agent-controlled mechanism has a real behavioral contrast, Policy/tool evidence supports its relevance, and outcome evidence is consistent with it. Only supportive evidence may produce skill_update_relevance update, and the discriminating behavior must be non-empty.
- conflicting: the same still-plausible mechanism has material supporting and counterevidence that cannot be reconciled. Use uncertainty and no update.
- insufficient: no concrete update-worthy mechanism is sufficiently supported, including when behavior does not differ, opportunity is absent, a suspected allegation is disproven, or only outcome or environment effects differ. Use no update unless a genuine unresolved ambiguity remains.
A disproven allegation is not conflicting evidence. If no alternative plausible mechanism remains, use insufficient and no update.

If the three rollouts contain no concrete Agent-controlled behavioral difference relevant to the suspected mechanism, do not manufacture one from outcome timing, tool completion, or label differences. Return insufficient and no update unless a different independently supported mechanism exists.

Counterevidence constrains both whether an update is justified and how strong it may be. A valid compliant-success behavior should remain allowed unless Policy explicitly rules it out. Do not infer stricter ordering, broader scope, or stronger obligations than the evidence supports.

<<TAU3_BENCHMARK_EXCLUSION>>

Return exactly the requested schema. Evidence refs must contain source_id and step_ids copied from supplied rollout steps. An update requires supportive evidence, a real non-empty discriminating_behavior, one coherent mechanism, and a Policy-permitted repair. Deterministic field mappings and target legality are enforced by the Python contract.

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
  "cross_rollout_analysis":{"stable_behavior":"","success_contrast":"","compliance_contrast":"","discriminating_behavior":"","evidence_consistency":"insufficient","counterevidence":"","support_evidence_refs":[],"counterevidence_refs":[]},
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
