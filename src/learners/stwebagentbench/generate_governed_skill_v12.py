"""Domain-neutral v0.12 cross-task canonicalizing bounded Editor prompt."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.skill_evolution.autonomous_gse_v05_proposal import annotate_parent_skill
from src.skill_evolution.autonomous_gse_v12_proposal import DiagnosisEditorRequest

LEARNER_MODEL = "openai/gpt-5.6-luna"
LearnerCall = Callable[[str, str, str], tuple[str, str, dict[str, Any] | None]]


def _default_learner_call(model: str, system: str, user: str) -> tuple[str, str, dict[str, Any] | None]:
    from src.learners.stwebagentbench.generate_skill import call_learner

    return call_learner(model, system, user, temperature=0.0)


EDITOR_SYSTEM_PROMPT = """You are the v0.12 bounded Editor for a domain-neutral Airline/Retail operational Skill. In one call, perform semantic merge, mechanism-level generalization, minimization, section placement, and final wording over all update-eligible task Diagnoses. Diagnosis already decided attribution and operation; do not reconsider whether an item is a skill issue.

For add Diagnoses, ignore source section (it is null). Merge semantically equivalent adds when one general rule can preserve every necessary trigger and expected behavior. Compare underlying problem, trigger condition, and expected behavior—not episode nouns. Do not merge distinct mechanisms such as unsupported inference and premature termination. Choose one real Parent Skill section for every final add and keep target_rule_id empty. For replace/delete, merge only when operation, section, and target_rule_id are exactly identical.

Minimize away episode nouns, literal workflows, unsupported ordering constraints, and redundant rules. Preserve applicability boundaries and necessary behavior. Do not invent obligations, policies, unsupported scenarios, or change the core objective. Each patch contributes to at most one canonical edit.

Return canonical edits containing exactly derived_from_patch_ids, operation, section, target_rule_id, text, reason, source_ids, repair_policy_ids, verification_target. verification_target must contain exactly problem, trigger_condition, expected_behavior and must align with the final canonical rule. Preserve all merged provenance. For add/replace, text is one actionable rule without a Markdown bullet; delete has empty text. Never include task-specific recipes or internal policy IDs. Return exactly one tagged JSON list and no prose:
<CANONICAL_EDITS_JSON>
[]
</CANONICAL_EDITS_JSON>
"""


def build_editor_prompts(request: DiagnosisEditorRequest) -> tuple[str, str]:
    if not isinstance(request, DiagnosisEditorRequest):
        raise ValueError("v0.12 requires DiagnosisEditorRequest.")
    if not request.current_parent_skill.strip() or not request.eligible_diagnoses:
        raise ValueError("Parent and update Diagnoses are required.")
    annotated = annotate_parent_skill(request.current_parent_skill).replace(
        "# SuiteCRM Operational Skill", "# Operational Skill", 1
    )
    return EDITOR_SYSTEM_PROMPT, (
        "Canonicalize these task-level interventions into minimal edits.\n\n"
        f"<CURRENT_PARENT_SKILL_WITH_RULE_IDS>\n{annotated.strip()}\n</CURRENT_PARENT_SKILL_WITH_RULE_IDS>\n\n"
        "<UPDATE_ELIGIBLE_TASK_DIAGNOSES>\n"
        + json.dumps(list(request.eligible_diagnoses), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n</UPDATE_ELIGIBLE_TASK_DIAGNOSES>\n\nReturn only the CANONICAL_EDITS_JSON block."
    )


def call_governed_editor(request: DiagnosisEditorRequest, *, learner_call: LearnerCall = _default_learner_call) -> str:
    system, user = build_editor_prompts(request)
    response, _, _ = learner_call(LEARNER_MODEL, system, user)
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("v0.12 Editor returned an empty response.")
    return response.strip()
