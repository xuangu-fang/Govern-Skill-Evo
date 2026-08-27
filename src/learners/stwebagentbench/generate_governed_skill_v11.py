"""Domain-neutral v0.11 bounded Editor prompt."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.learners.stwebagentbench.generate_skill import call_learner
from src.skill_evolution.autonomous_gse_v05_proposal import annotate_parent_skill
from src.skill_evolution.autonomous_gse_v11_proposal import DiagnosisEditorRequest

LEARNER_MODEL = "openai/gpt-5.6-luna"
LearnerCall = Callable[[str, str, str], tuple[str, str, dict[str, Any] | None]]


def _default_learner_call(
    model: str, system_prompt: str, user_prompt: str
) -> tuple[str, str, dict[str, Any] | None]:
    return call_learner(
        model, system_prompt, user_prompt, temperature=0.0
    )

EDITOR_SYSTEM_PROMPT = """You are the bounded Editor for a domain-neutral τ³
Airline/Retail operational Skill. Validated Diagnoses already fixed relevance,
operation, target, objective, and source lineage. Express only those supported
interventions as minimal final Skill wording.

Return canonical edits containing exactly derived_from_patch_ids, operation,
section, target_rule_id, text, reason, source_ids, repair_policy_ids. Copy the
operation/section/target exactly. Each patch contributes to at most one edit.
Combine patches only when they share the same diagnosed gap and exact target.
For add/replace, text is one actionable rule without a Markdown bullet; delete
has empty text. Write a transferable operating method with an applicability
condition and verification/stopping condition. Never hard-code task-specific
IDs, values, entities, dates, fields, or replay sequences. Never put internal
policy IDs in Skill text. Preserve supplied source and policy provenance.
Do not return a complete Skill, ranking, diagnosis, or prose. Return exactly:
<CANONICAL_EDITS_JSON>
[]
</CANONICAL_EDITS_JSON>
"""

EDITOR_USER_PROMPT = """Express these validated interventions as minimal edits.

<CURRENT_PARENT_SKILL_WITH_RULE_IDS>
{parent_skill}
</CURRENT_PARENT_SKILL_WITH_RULE_IDS>

<UPDATE_ELIGIBLE_DIAGNOSES>
{diagnoses}
</UPDATE_ELIGIBLE_DIAGNOSES>

Return only the CANONICAL_EDITS_JSON block.
"""


class EditorPromptContractError(ValueError):
    pass


def build_editor_prompts(request: DiagnosisEditorRequest) -> tuple[str, str]:
    if not isinstance(request, DiagnosisEditorRequest):
        raise EditorPromptContractError("v0.11 requires a DiagnosisEditorRequest.")
    if not request.current_parent_skill.strip() or not request.eligible_diagnoses:
        raise EditorPromptContractError("Parent and update Diagnoses are required.")
    annotated = annotate_parent_skill(request.current_parent_skill).replace(
        "# SuiteCRM Operational Skill", "# Operational Skill", 1
    )
    return EDITOR_SYSTEM_PROMPT, EDITOR_USER_PROMPT.format(
        parent_skill=annotated.strip(),
        diagnoses=json.dumps(
            list(request.eligible_diagnoses), ensure_ascii=False, indent=2, sort_keys=True
        ),
    )


def call_governed_editor(
    request: DiagnosisEditorRequest, *, learner_call: LearnerCall = _default_learner_call
) -> str:
    system_prompt, user_prompt = build_editor_prompts(request)
    response, _, _ = learner_call(LEARNER_MODEL, system_prompt, user_prompt)
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("v0.11 Editor returned an empty response.")
    return response.strip()
