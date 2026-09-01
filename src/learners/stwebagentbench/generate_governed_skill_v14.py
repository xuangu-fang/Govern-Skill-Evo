"""Mechanism-preserving bounded Editor for Autonomous GSE v0.14."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.skill_evolution.autonomous_gse_v05_proposal import annotate_parent_skill
from src.skill_evolution.autonomous_gse_v14_proposal import DiagnosisEditorRequest

LEARNER_MODEL = "openai/deepseek-v4-pro"
LearnerCall = Callable[[str, str, str], tuple[str, str, dict[str, Any] | None]]


def _default_learner_call(model: str, system: str, user: str) -> tuple[str, str, dict[str, Any] | None]:
    from src.learners.stwebagentbench.generate_skill import call_learner

    return call_learner(model, system, user, temperature=0.0)


EDITOR_SYSTEM_PROMPT = """You are the v0.14 bounded Editor. In at most one call, perform cross-task deduplication, wording normalization, episode generalization, section placement, and final Skill wording. Diagnosis already decided the behavioral mechanism, attribution, update axis, operation, and target behavior. Do not reanalyze rollouts, judge evidence consistency, choose recurrent versus contrastive evidence, relabel Compliance, redo root-cause attribution, or invent a new update mechanism. Diagnosis decides what mechanism changes; Editor decides how to represent that mechanism in the Skill.

Use supplied domain context only as a lightweight fail-closed constraint. Never canonicalize an update into behavior explicitly forbidden by the original Policy. Policy may veto an unsupported or forbidden canonicalization, but Policy alone must not create an edit or obligation absent from an eligible Diagnosis. Policy is normative; tool availability alone is not Policy permission. If a Diagnosis target plainly requires Policy-forbidden behavior, emit no canonical edit for it.

Generalize episode-specific values, not the conditions that make behavior correct. You may remove or abstract identities, record identifiers, contact details, URLs, dates, incidental numeric values, episode-specific entities, accidental wording, examples, and trajectory details with no causal role. Do not mechanically remove information merely because it looks concrete; ask whether it determines the correct action.

Generalization must preserve every mechanism-defining condition that determines when a rule applies, when it does not apply, or which action is correct. This includes the trigger condition, causal predicate, decision boundary, feasibility condition, Policy precondition, required-evidence condition, authorization or confirmation condition, necessary ordering relation, repair operator, necessary stopping boundary, and scope condition. If removing a predicate would make the rule apply where the source Diagnosis does not justify it, that predicate is necessary and must remain. Generalization may remove incidental constants but must not enlarge the trigger scope beyond the minimum reusable scope jointly supported by the source mechanisms.

Before emitting each canonical edit, compare its text and verification_target with every source target_behavior field: problem, trigger_condition, decision_boundary, repair_operator, stopping_boundary, and expected_behavior. If an Agent following the canonical rule exactly would not make the decision required by every source Diagnosis under the same relevant conditions, the wording is over-abstract and must retain more conditions. Preserve supported predicates and ordering, but do not turn accidental episode order into a new obligation.

Minimality concerns unnecessary behavioral constraints, not wording length. It means removing unsupported or accidental constraints, not removing supported decision conditions. Minimal is not shortest. A rule may use two or three sentences to retain its trigger, predicate, repair, and stopping boundary. A stronger rule is not a safer canonicalization when the source Diagnosis did not justify it: do not replace a conditional requirement with an always-rule, enlarge its scope, strengthen its obligation, or impose stricter ordering.

Normalize equivalent mechanisms without flattening operational distinctions. Merge only when all sources have the same problem mechanism, compatible triggers and decision boundaries, the same repair operator, and compatible necessary scope semantics. Semantic or thematic similarity alone is not sufficient for merge. Sharing a topic, domain, tool, object type, or general safety concept is not mechanism equivalence. A canonical edit represents one coherent decision mechanism, not a collection of related workflows. Different operation semantics—such as verifying, prohibiting, stopping to request information, ordering actions, or requiring evidence—must remain separate unless the same precise conditional rule genuinely represents them.

Before merging, ask whether one precise verification_target can represent every source behavioral requirement without broadening, weakening, or changing any source mechanism. If a merged edit cannot retain one precise target that accurately covers every source Diagnosis, do not merge. Do not make the verification_target broader or more generic merely to enable a merge. If distinct conditions require distinct actions, preserve those branches explicitly only when they form one coherent decision mechanism; otherwise emit separate edits.

Every canonical edit needs one precise, operational, behaviorally testable verification_target with exactly problem, trigger_condition, and expected_behavior. Catch-all wording that merely says to act carefully, follow Policy, or verify required conditions is too broad unless the source mechanism itself is genuinely that broad.

For any edit derived from multiple patch IDs, reason must briefly state the shared behavioral mechanism, shared trigger or decision boundary, identical repair operator, and why one rule preserves every source's necessary conditions. Topic-level statements such as "these Diagnoses are related" are insufficient.

Counterevidence constrains final rule strength. Do not create broader scope, stronger obligations, or stricter ordering than the evidence supports. Do not invent obligations, policies, scenarios, workflows, or unsupported Policy content.

For add, choose one real Parent section and keep target_rule_id empty. For replace/delete, merge only identical operation + section + stable target_rule_id. Preserve all source_ids, repair_policy_ids, and derived_from_patch_ids; each patch contributes to at most one edit. For add/replace, text is actionable Skill wording without a Markdown bullet; delete has empty text. Never include task-specific recipes or internal policy IDs.

Return exactly one tagged JSON list with fields derived_from_patch_ids, operation, section, target_rule_id, text, reason, source_ids, repair_policy_ids, verification_target, and no prose:
<CANONICAL_EDITS_JSON>
[]
</CANONICAL_EDITS_JSON>
"""


def build_editor_prompts(request: DiagnosisEditorRequest) -> tuple[str, str]:
    if not isinstance(request, DiagnosisEditorRequest):
        raise ValueError("v0.14 requires DiagnosisEditorRequest.")
    if not request.current_parent_skill.strip() or not request.eligible_diagnoses:
        raise ValueError("Parent and update Diagnoses are required.")
    if not request.domain_contexts or any(
        not isinstance(item, dict)
        or not isinstance(item.get("domain"), str) or not item["domain"].strip()
        or not isinstance(item.get("original_domain_policy"), str)
        or not item["original_domain_policy"].strip()
        or set(item) != {"domain", "original_domain_policy"}
        for item in request.domain_contexts
    ):
        raise ValueError("Authoritative domain context is required.")
    annotated = annotate_parent_skill(request.current_parent_skill).replace(
        "# SuiteCRM Operational Skill", "# Operational Skill", 1
    )
    return EDITOR_SYSTEM_PROMPT, (
        "Canonicalize these task-level interventions by mechanism equivalence.\n\n"
        f"<CURRENT_PARENT_SKILL_WITH_RULE_IDS>\n{annotated.strip()}\n</CURRENT_PARENT_SKILL_WITH_RULE_IDS>\n\n"
        "<UPDATE_ELIGIBLE_TASK_DIAGNOSES>\n"
        + json.dumps(list(request.eligible_diagnoses), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n</UPDATE_ELIGIBLE_TASK_DIAGNOSES>\n\n"
        "<AUTHORITATIVE_DOMAIN_CONTEXT>\n"
        + json.dumps(list(request.domain_contexts), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n</AUTHORITATIVE_DOMAIN_CONTEXT>\n\nReturn only the CANONICAL_EDITS_JSON block."
    )


def call_governed_editor(request: DiagnosisEditorRequest, *, learner_call: LearnerCall = _default_learner_call) -> str:
    system, user = build_editor_prompts(request)
    response, _, _ = learner_call(LEARNER_MODEL, system, user)
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("v0.14 Editor returned an empty response.")
    return response.strip()
