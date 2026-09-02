"""Mechanism-preserving bounded Editor for Autonomous GSE v0.14."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.skill_evolution.autonomous_gse_v05_proposal import annotate_parent_skill
from src.skill_evolution.autonomous_gse_v14_proposal import (
    DiagnosisEditorRequest, EditorContractError,
)

LEARNER_MODEL = "openai/deepseek-v4-pro"
LearnerCall = Callable[[str, str, str], tuple[str, str, dict[str, Any] | None]]

VERIFICATION_TARGET_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["problem", "trigger_condition", "expected_behavior"],
    "properties": {
        "problem": {"type": "string"},
        "trigger_condition": {"type": "string"},
        "expected_behavior": {"type": "string"},
    },
}
CANONICAL_EDIT_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "derived_from_patch_ids", "operation", "section", "target_rule_id",
        "text", "reason", "source_ids", "repair_policy_ids",
        "verification_target",
    ],
    "properties": {
        "derived_from_patch_ids": {
            "type": "array", "items": {"type": "string"},
        },
        "operation": {"type": "string", "enum": ["add", "replace", "delete"]},
        "section": {"type": "string"},
        "target_rule_id": {"type": "string"},
        "text": {"type": "string"},
        "reason": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}},
        "repair_policy_ids": {"type": "array", "items": {"type": "string"}},
        "verification_target": VERIFICATION_TARGET_JSON_SCHEMA,
    },
}
EDITOR_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["canonical_edits"],
    "properties": {
        "canonical_edits": {
            "type": "array", "items": CANONICAL_EDIT_JSON_SCHEMA,
        },
    },
}
EDITOR_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "v14_canonical_edits",
        "strict": True,
        "schema": EDITOR_JSON_SCHEMA,
    },
}


class EditorResponse(str):
    """Internal tagged adapter carrying the original structured response."""

    def __new__(cls, value: str, raw_response: str):
        instance = super().__new__(cls, value)
        instance.raw_response = raw_response
        instance.structured_output_mode = "json_schema"
        instance.error_reason = None
        return instance


def _default_learner_call(
    model: str, system: str, user: str, *, response_format: dict | None = None,
) -> tuple[str, str, dict[str, Any] | None]:
    from src.learners.stwebagentbench.generate_skill import call_learner

    return call_learner(
        model, system, user, temperature=0.0, response_format=response_format,
    )


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

Return only the structured canonical-edit result required by the supplied response schema.
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
        + "\n</AUTHORITATIVE_DOMAIN_CONTEXT>\n\nReturn only the structured response."
    )


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _valid_structured_editor_result(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"canonical_edits"}:
        return False
    edits = value["canonical_edits"]
    expected_fields = set(CANONICAL_EDIT_JSON_SCHEMA["required"])
    verification_fields = set(VERIFICATION_TARGET_JSON_SCHEMA["required"])
    for edit in edits if isinstance(edits, list) else ():
        verification = edit.get("verification_target") if isinstance(edit, dict) else None
        if (
            not isinstance(edit, dict) or set(edit) != expected_fields
            or edit.get("operation") not in {"add", "replace", "delete"}
            or any(not isinstance(edit.get(field), str) for field in (
                "section", "target_rule_id", "text", "reason",
            ))
            or any(not _is_string_list(edit.get(field)) for field in (
                "derived_from_patch_ids", "source_ids", "repair_policy_ids",
            ))
            or not isinstance(verification, dict)
            or set(verification) != verification_fields
            or any(not isinstance(verification.get(field), str) for field in verification_fields)
        ):
            return False
    return isinstance(edits, list)


def call_governed_editor(request: DiagnosisEditorRequest, *, learner_call: LearnerCall = _default_learner_call) -> str:
    system, user = build_editor_prompts(request)
    try:
        response, _, _ = learner_call(
            LEARNER_MODEL, system, user, response_format=EDITOR_RESPONSE_FORMAT,
        )
    except Exception as error:
        raise EditorContractError(
            "EDITOR_STRUCTURED_OUTPUT_ERROR", raw_response=None,
            structured_output_mode="json_schema", error_reason=str(error),
        ) from error
    if not isinstance(response, str) or not response.strip():
        raise EditorContractError(
            "EDITOR_EMPTY_RESPONSE",
            raw_response=response if isinstance(response, str) else None,
            structured_output_mode="json_schema",
            error_reason="v0.14 Editor returned an empty response.",
        )
    raw_response = response.strip()
    try:
        structured = json.loads(raw_response)
    except json.JSONDecodeError as error:
        raise EditorContractError(
            "EDITOR_SCHEMA_CONTRACT_ERROR", raw_response=raw_response,
            structured_output_mode="json_schema", error_reason=str(error),
        ) from error
    if not _valid_structured_editor_result(structured):
        raise EditorContractError(
            "EDITOR_SCHEMA_CONTRACT_ERROR", raw_response=raw_response,
            structured_output_mode="json_schema",
            error_reason="Editor result does not match the strict response schema.",
        )
    internal = (
        "<CANONICAL_EDITS_JSON>"
        + json.dumps(structured["canonical_edits"], ensure_ascii=False)
        + "</CANONICAL_EDITS_JSON>"
    )
    return EditorResponse(internal, raw_response)
