"""Mechanism-preserving bounded Editor for Autonomous GSE v0.13."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.skill_evolution.autonomous_gse_v05_proposal import annotate_parent_skill
from src.skill_evolution.autonomous_gse_v13_proposal import DiagnosisEditorRequest

LEARNER_MODEL = "openai/deepseek-v4-pro"
LearnerCall = Callable[[str, str, str], tuple[str, str, dict[str, Any] | None]]


def _default_learner_call(model: str, system: str, user: str) -> tuple[str, str, dict[str, Any] | None]:
    from src.learners.stwebagentbench.generate_skill import call_learner

    return call_learner(model, system, user, temperature=0.0)


EDITOR_SYSTEM_PROMPT = """You are the v0.13 bounded Editor. In at most one call, perform cross-task deduplication, wording normalization, episode generalization, section placement, and final Skill wording. Diagnosis already decided attribution and operation; do not add a stage or reconsider attribution.

Use supplied domain context only as a lightweight fail-closed constraint. Never canonicalize an update into behavior explicitly forbidden by the original Policy. Policy is normative; tool availability alone is not Policy permission. Do not reanalyze the three rollouts, relabel Compliance, or redo root-cause attribution. If a Diagnosis target plainly requires Policy-forbidden behavior, emit no canonical edit for it.

Normalize equivalent mechanisms without flattening their operational distinctions. Merge only when the problem mechanism, trigger or decision boundary, repair operator, and necessary scope semantics are compatible. Semantic or thematic similarity alone is not sufficient for merge.

Every canonical edit needs one precise, operational, behaviorally testable verification_target with exactly problem, trigger_condition, and expected_behavior. If a merged edit cannot retain one such target that accurately covers every source Diagnosis, do not merge. A catch-all such as "when using information, ensure information is grounded" proves the merge is too broad.

Minimality concerns unnecessary behavioral constraints, not wording length. Minimal is not shortest. A rule may use two or three sentences to preserve trigger, decision predicate, repair action, and a necessary stopping boundary. Remove episode entities and accidental workflows, but preserve operational information. Do not invent obligations, policies, scenarios, or ordering constraints.

Counterevidence constrains final rule strength. Do not create broader scope, stronger obligations, or stricter ordering than the evidence supports.

For add, choose one real Parent section and keep target_rule_id empty. For replace/delete, merge only identical operation + section + stable target_rule_id. Preserve all source_ids, repair_policy_ids, and derived_from_patch_ids; each patch contributes to at most one edit. For add/replace, text is actionable Skill wording without a Markdown bullet; delete has empty text. Never include task-specific recipes or internal policy IDs.

Return exactly one tagged JSON list with fields derived_from_patch_ids, operation, section, target_rule_id, text, reason, source_ids, repair_policy_ids, verification_target, and no prose:
<CANONICAL_EDITS_JSON>
[]
</CANONICAL_EDITS_JSON>
"""


def build_editor_prompts(request: DiagnosisEditorRequest) -> tuple[str, str]:
    if not isinstance(request, DiagnosisEditorRequest):
        raise ValueError("v0.13 requires DiagnosisEditorRequest.")
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
        raise RuntimeError("v0.13 Editor returned an empty response.")
    return response.strip()
