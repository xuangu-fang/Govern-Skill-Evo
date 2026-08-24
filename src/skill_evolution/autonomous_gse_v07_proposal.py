"""Diagnosis-driven Proposal path layered over v0.5 bounded editing."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    ProposalContext,
    ProposalDecision,
    _no_candidate,
    _parse_tagged_list,
    _string_list,
)
from src.skill_evolution.autonomous_gse_v05_proposal import (
    _parse_skill,
    _validate_context,
    propose_from_update_signals,
)
from src.skill_evolution.diagnosis import Diagnoser, DiagnosisRequest
from src.skill_evolution.diagnosis_contract import (
    DiagnosisValidation,
    parse_and_validate_diagnosis,
)


@dataclass(frozen=True)
class DiagnosisEditorRequest:
    candidate_id: str
    current_parent_skill: str
    eligible_diagnoses: tuple[dict[str, Any], ...]
    preserve_constraints: tuple[dict[str, Any], ...]


DiagnosisEditor = Callable[[DiagnosisEditorRequest], str]


_TASK_SPECIFIC_RULE_PATTERNS = (
    re.compile(
        r"\b(?:enter|fill|set|select|choose)\b[^.!?\n]{0,120}"
        r"\bfirst\b[^.!?\n]{0,120}\b(?:then|second)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:enter|fill)\b[^.!?\n]{0,120}\bincluding\b"
        r"[^.!?\n]{0,80}\bbefore\b[^.!?\n]{0,80}",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:[Ss]et|[Ss]elect|[Cc]hoose)\b[^.!?\n]{0,80}\bto\s+"
        r"(?:a\s+|an\s+|the\s+)?[A-Z][A-Za-z0-9_-]*\b"
    ),
    re.compile(
        r"(?:\b\d{4}-\d{2}-\d{2}\b|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|"
        r"https?://\S+)",
        re.IGNORECASE,
    ),
)


def _contains_task_specific_recipe(text: str) -> bool:
    return any(pattern.search(text) for pattern in _TASK_SPECIFIC_RULE_PATTERNS)


@dataclass(frozen=True)
class DiagnosisProposalDecision:
    """v0.5-compatible decision plus inspectable Diagnosis lineage."""

    proposal_status: str
    proposal_reason: dict[str, str]
    reflector_calls: int
    editor_calls: int
    raw_patches: list[dict[str, Any]]
    canonical_edits: list[Any]
    applied_edits: list[dict[str, Any]]
    excluded_edits: list[dict[str, Any]]
    candidate_skill: str | None
    provenance_status: str | None
    provenance_audit: dict[str, Any] | None
    diagnosis_calls: int
    diagnoses: list[dict[str, Any]]
    eligible_diagnosis_ids: list[str]
    preserve_constraints: list[dict[str, Any]]


def _enrich_decision(
    decision: ProposalDecision,
    *,
    diagnoses: list[DiagnosisValidation],
    eligible_ids: list[str],
    preserve_constraints: list[dict[str, Any]],
) -> DiagnosisProposalDecision:
    base_fields = copy.deepcopy(decision.__dict__)
    base_fields["reflector_calls"] = len(diagnoses)
    return DiagnosisProposalDecision(
        **base_fields,
        diagnosis_calls=len(diagnoses),
        diagnoses=[item.as_dict() for item in diagnoses],
        eligible_diagnosis_ids=copy.deepcopy(eligible_ids),
        preserve_constraints=copy.deepcopy(preserve_constraints),
    )


def _recommendation_signal(
    validation: DiagnosisValidation,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    assert validation.structured_output is not None
    diagnosis = validation.structured_output
    recommendation = diagnosis["update_recommendation"]
    return {
        "patch_id": validation.diagnosis_id,
        "diagnosis_id": validation.diagnosis_id,
        "operation": recommendation["action"],
        "section": recommendation["target_section"],
        "target_rule_id": recommendation["target_rule_id"] or "",
        "objective": recommendation["objective"],
        "description": recommendation["description"],
        "source_ids": [validation.source_id],
        "repair_policy_ids": list(diagnosis["policy_analysis"]["policy_ids"]),
        "four_state": evidence["state"],
        "root_cause": copy.deepcopy(diagnosis["root_cause"]),
    }


def _preserve_constraints(
    diagnoses: list[DiagnosisValidation],
) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for validation in diagnoses:
        if not validation.valid or validation.structured_output is None:
            continue
        for item in validation.structured_output["preserve_constraints"]:
            key = (
                validation.diagnosis_id,
                item["target_rule_id"],
                item["reason"],
            )
            if key in seen:
                continue
            seen.add(key)
            constraints.append(
                {
                    "source_diagnosis_id": validation.diagnosis_id,
                    "source_id": validation.source_id,
                    **copy.deepcopy(item),
                }
            )
    return constraints


def _guard_editor_response(
    response: str,
    request: EditorRequest,
    preserve_constraints: list[dict[str, Any]],
) -> str:
    """Reject target drift, protected edits, and policy-ID leakage."""

    edits, reason = _parse_tagged_list(response, "CANONICAL_EDITS_JSON")
    if reason is not None or edits is None:
        return response
    signals = {item["patch_id"]: item for item in request.raw_patches}
    preserved_rule_ids = {
        item["target_rule_id"] for item in preserve_constraints
    }
    guarded: list[Any] = []
    for value in edits:
        edit = copy.deepcopy(value)
        if not isinstance(edit, dict):
            guarded.append(edit)
            continue
        patch_ids = _string_list(edit.get("derived_from_patch_ids"))
        sources = [signals[item] for item in (patch_ids or []) if item in signals]
        expected = {
            (
                item["operation"],
                item["section"],
                item.get("target_rule_id", ""),
            )
            for item in sources
        }
        actual = (
            edit.get("operation"),
            edit.get("section"),
            edit.get("target_rule_id", ""),
        )
        exclusion_reason = None
        if not sources or len(sources) != len(patch_ids or []) or expected != {actual}:
            exclusion_reason = "DIAGNOSIS_TARGET_DRIFT"
        elif edit.get("operation") == "delete" and edit.get(
            "target_rule_id"
        ) in preserved_rule_ids:
            exclusion_reason = "PRESERVE_CONSTRAINT_CONFLICT"
        elif isinstance(edit.get("text"), str) and any(
            policy_id.casefold() in edit["text"].casefold()
            for source in sources
            for policy_id in source["repair_policy_ids"]
        ):
            exclusion_reason = "POLICY_ID_LEAKAGE"
        elif (
            edit.get("operation") in {"add", "replace"}
            and isinstance(edit.get("text"), str)
            and _contains_task_specific_recipe(edit["text"])
        ):
            exclusion_reason = "TASK_SPECIFIC_RULE"
        if exclusion_reason is not None:
            edit["v07_validation_error"] = exclusion_reason
            edit["derived_from_patch_ids"] = []
        guarded.append(edit)
    return (
        "<CANONICAL_EDITS_JSON>"
        + json.dumps(guarded, ensure_ascii=False)
        + "</CANONICAL_EDITS_JSON>"
    )


class DiagnosisDrivenProposalOperator:
    """Run one Diagnosis call per rollout, then reuse v0.5 bounded Update."""

    name = "diagnosis_driven_bounded_edit"

    def propose(
        self,
        context: ProposalContext,
        diagnoser: Diagnoser,
        editor: DiagnosisEditor,
    ) -> DiagnosisProposalDecision:
        sections, _, _, _ = _validate_context(context)
        validations: list[DiagnosisValidation] = []
        evidence_by_diagnosis_id: dict[str, dict[str, Any]] = {}
        for index, evidence in enumerate(
            context.current_batch_governed_evidence, start=1
        ):
            diagnosis_id = f"diagnosis_{index:03d}"
            request = DiagnosisRequest(
                candidate_id=context.candidate_id,
                diagnosis_id=diagnosis_id,
                current_parent_skill=context.parent_skill,
                governed_experience=copy.deepcopy(evidence),
            )
            response = diagnoser(request)
            validation = parse_and_validate_diagnosis(
                diagnosis_id,
                evidence["source_id"],
                response,
                evidence=evidence,
                skill_sections=sections,
            )
            validations.append(validation)
            evidence_by_diagnosis_id[diagnosis_id] = evidence

        eligible = [
            item
            for item in validations
            if item.valid
            and item.structured_output is not None
            and item.structured_output["skill_update_relevance"] == "update"
        ]
        preserve_constraints = _preserve_constraints(validations)
        eligible_ids = [item.diagnosis_id for item in eligible]
        if not eligible:
            decision = _no_candidate(
                "NO_UPDATE_ELIGIBLE_DIAGNOSIS",
                reflector_calls=len(validations),
                editor_calls=0,
            )
            return _enrich_decision(
                decision,
                diagnoses=validations,
                eligible_ids=eligible_ids,
                preserve_constraints=preserve_constraints,
            )

        eligible_signals: list[dict[str, Any]] = []
        for validation in eligible:
            evidence = evidence_by_diagnosis_id[validation.diagnosis_id]
            eligible_signals.append(
                _recommendation_signal(validation, evidence)
            )

        def diagnosis_editor(request: EditorRequest) -> str:
            eligible_diagnoses = tuple(
                copy.deepcopy(item)
                for item in request.raw_patches
            )
            response = editor(
                DiagnosisEditorRequest(
                    candidate_id=request.candidate_id,
                    current_parent_skill=request.current_parent_skill,
                    eligible_diagnoses=eligible_diagnoses,
                    preserve_constraints=tuple(copy.deepcopy(preserve_constraints)),
                )
            )
            return _guard_editor_response(response, request, preserve_constraints)

        base = propose_from_update_signals(
            context,
            eligible_signals,
            diagnosis_editor,
            upstream_calls=len(validations),
        )
        return _enrich_decision(
            base,
            diagnoses=validations,
            eligible_ids=eligible_ids,
            preserve_constraints=preserve_constraints,
        )


def structured_skill(skill: str) -> dict[str, list[dict[str, str]]]:
    """Expose the reused v0.5 Skill representation for artifacts/tests."""

    return copy.deepcopy(_parse_skill(skill))
