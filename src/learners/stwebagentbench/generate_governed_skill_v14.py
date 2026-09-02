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


EDITOR_SYSTEM_PROMPT = """You are the v0.14 bounded Editor. In at most one call, perform cross-task deduplication, wording normalization, episode generalization, section placement, and final Skill wording.

A. Authority boundary
Diagnosis determines what behavioral mechanism should change. The deterministic Decision Compiler determines whether and how the Skill may be edited. The Editor only canonicalizes eligible update signals into Skill wording. Do not re-diagnose rollouts, rejudge evidence, relabel Compliance, redo root-cause attribution, or invent a new update mechanism. Supplied Policy may veto a forbidden canonicalization, but cannot create an update by itself. Policy is normative; tool availability alone is not Policy permission. If an eligible target requires Policy-forbidden behavior, emit no edit for it.

B. Mechanism-preserving canonicalization
Generalize incidental episode details while preserving every mechanism-defining condition. A condition is mechanism-defining if removing or changing it would alter:
- when the rule applies;
- which action is correct;
- what authorization or evidence is required;
- what ordering is required; or
- when execution must stop.
Preserve the source trigger, decision boundary, repair operator, and stopping boundary. Do not broaden scope, strengthen obligations, or impose stricter ordering than supported by the source Diagnoses. Counterevidence constrains final rule strength. Minimality means removing unsupported constraints, not supported decision conditions; minimal is not shortest.

C. Scope and provenance preservation
Domain is a scope condition. For a single-domain edit, BOTH the Skill text and verification_target.trigger_condition must begin with the canonical prefix: airline -> "For airline requests,"; retail -> "For retail requests,". Do not paraphrase, relocate, or imply the prefix. The deterministic Editor Guard validates this exact form. Multi-domain generalization is allowed only when the merge contract below is satisfied.

Preserve source provenance. Never invent obligations, Policy content, scenarios, or workflows. Never expose internal Policy IDs or emit a task-specific recipe. For add, choose one real Parent section and keep target_rule_id empty. For replace or delete, merge only identical operation, section, and stable target_rule_id.

D. User-controlled decisions
Preserve user control over every parameter whose value is not determined by the eligible Diagnosis or authoritative Policy. For each required user-controlled decision:
- preserve an existing explicit user choice or authorization;
- otherwise use an authoritative deterministic selector if one is supplied;
- otherwise preserve a step that obtains the user's choice before execution.
Do not hide an unresolved user-controlled parameter inside generic fallback wording. Authorization for one parameter does not authorize the Agent to choose other independent parameters.

E. Merge semantics
Merge source Diagnoses only when one canonical rule can preserve every source mechanism without changing any source-specific predicate. A valid merge requires:
- compatible triggers and decision boundaries;
- the same repair operator;
- compatible scope semantics; and
- no source-specific predicate being promoted into another source branch.
Shared repair operators do not imply shared predicates. Only conditions supported by every source may appear in the shared portion of a merged rule. Source-specific conditions must remain branch-scoped. If one precise verification target cannot represent every source without broadening, weakening, or strengthening any source mechanism, emit separate edits. Semantic or thematic similarity alone is not mechanism equivalence.

For a merged edit, reason must briefly identify the shared behavioral mechanism, compatible trigger or decision boundary, common repair operator, and why one rule preserves every source's necessary conditions.

F. Semantic-form preservation
Preserve semantic meaning rather than surface form. Do not promote:
- examples into obligations;
- illustrative alternatives into preferences;
- semantic authorization, confirmation, consent, or intent into lexical matching; or
- supported abstract categories into unsupported concrete enumerations.
Illustrative surface forms must not become lexical requirements. When a source expresses a semantic authorization, confirmation, consent, or intent condition, preserve semantic equivalence unless authoritative Policy explicitly requires a literal form. Preserve the abstraction level supported by provenance. If provenance does not establish a complete taxonomy, prefer the grounded abstract category over a speculative list. Use a stronger or more concrete formulation only when directly supported by the eligible Diagnosis or authoritative Policy.

G. Verification target
Every canonical edit needs exactly one verification_target containing problem, trigger_condition, and expected_behavior. It must be precise, operational, behaviorally testable, and consistent with the canonical Skill text. The verification target must not be narrower, broader, or stronger than the canonical Skill rule or its source Diagnoses.

Before emitting an edit, verify that its Skill text and verification target jointly preserve the source mechanism, scope, user-control boundaries, and semantic strength without adding unsupported constraints.

H. Output contract
Preserve all source_ids, repair_policy_ids, and derived_from_patch_ids; each patch contributes to at most one edit. For add or replace, text is actionable Skill wording without a Markdown bullet; delete has empty text.

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
