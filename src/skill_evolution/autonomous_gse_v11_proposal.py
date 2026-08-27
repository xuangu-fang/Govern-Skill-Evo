"""v0.11 Diagnosis-only proposal path over the v0.5 bounded editor."""

from __future__ import annotations

import copy
import json
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
from src.skill_evolution.autonomous_gse_v07_proposal import _contains_task_specific_recipe
from src.skill_evolution.diagnosis_contract_v11 import (
    DiagnosisValidation,
    parse_and_validate_diagnosis,
)
from src.skill_evolution.diagnosis_v11 import Diagnoser, DiagnosisRequest


@dataclass(frozen=True)
class DiagnosisEditorRequest:
    candidate_id: str
    current_parent_skill: str
    eligible_diagnoses: tuple[dict[str, Any], ...]


DiagnosisEditor = Callable[[DiagnosisEditorRequest], str]


@dataclass(frozen=True)
class DiagnosisProposalDecision:
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


def _enrich(
    decision: ProposalDecision,
    validations: list[DiagnosisValidation],
    eligible_ids: list[str],
) -> DiagnosisProposalDecision:
    fields = copy.deepcopy(decision.__dict__)
    fields["reflector_calls"] = len(validations)
    return DiagnosisProposalDecision(
        **fields,
        diagnosis_calls=len(validations),
        diagnoses=[item.as_dict() for item in validations],
        eligible_diagnosis_ids=eligible_ids,
    )


def _signal(item: DiagnosisValidation, evidence: dict[str, Any]) -> dict[str, Any]:
    assert item.structured_output is not None
    diagnosis = item.structured_output
    recommendation = diagnosis["update_recommendation"]
    return {
        "patch_id": item.diagnosis_id,
        "diagnosis_id": item.diagnosis_id,
        "derived_from_diagnosis_ids": [item.diagnosis_id],
        "operation": recommendation["action"],
        "section": recommendation["target_section"],
        "target_rule_id": recommendation["target_rule_id"] or "",
        "objective": recommendation["objective"],
        "description": recommendation["description"],
        "source_ids": [item.source_id],
        "repair_policy_ids": list(diagnosis["policy_analysis"]["policy_ids"]),
        "four_state": evidence["state"],
        "root_cause": copy.deepcopy(diagnosis["root_cause"]),
    }


def _guard_editor_response(response: str, request: EditorRequest) -> str:
    edits, error = _parse_tagged_list(response, "CANONICAL_EDITS_JSON")
    if error or edits is None:
        return response
    signals = {item["patch_id"]: item for item in request.raw_patches}
    guarded: list[Any] = []
    for value in edits:
        edit = copy.deepcopy(value)
        if not isinstance(edit, dict):
            guarded.append(edit)
            continue
        patch_ids = _string_list(edit.get("derived_from_patch_ids"))
        sources = [signals[item] for item in (patch_ids or []) if item in signals]
        expected = {
            (item["operation"], item["section"], item.get("target_rule_id", ""))
            for item in sources
        }
        actual = (edit.get("operation"), edit.get("section"), edit.get("target_rule_id", ""))
        exclusion = None
        if not sources or len(sources) != len(patch_ids or []) or expected != {actual}:
            exclusion = "DIAGNOSIS_TARGET_DRIFT"
        elif isinstance(edit.get("text"), str) and any(
            policy_id.casefold() in edit["text"].casefold()
            for source in sources
            for policy_id in source["repair_policy_ids"]
        ):
            exclusion = "POLICY_ID_LEAKAGE"
        elif edit.get("operation") in {"add", "replace"} and isinstance(
            edit.get("text"), str
        ) and _contains_task_specific_recipe(edit["text"]):
            exclusion = "TASK_SPECIFIC_RULE"
        if exclusion:
            edit["v11_validation_error"] = exclusion
            edit["derived_from_patch_ids"] = []
        guarded.append(edit)
    return "<CANONICAL_EDITS_JSON>" + json.dumps(guarded, ensure_ascii=False) + "</CANONICAL_EDITS_JSON>"


class DiagnosisDrivenProposalOperator:
    name = "v11_diagnosis_driven_bounded_edit"

    def propose(
        self,
        context: ProposalContext,
        diagnoser: Diagnoser,
        editor: DiagnosisEditor,
    ) -> DiagnosisProposalDecision:
        sections, _, _, _ = _validate_context(context)
        validations: list[DiagnosisValidation] = []
        evidence_by_id: dict[str, dict[str, Any]] = {}
        for index, evidence in enumerate(context.current_batch_governed_evidence, start=1):
            diagnosis_id = f"diagnosis_{index:03d}"
            response = diagnoser(
                DiagnosisRequest(
                    candidate_id=context.candidate_id,
                    diagnosis_id=diagnosis_id,
                    current_parent_skill=context.parent_skill,
                    governed_experience=copy.deepcopy(evidence),
                )
            )
            validation = parse_and_validate_diagnosis(
                diagnosis_id,
                evidence["source_id"],
                response,
                evidence=evidence,
                skill_sections=sections,
            )
            validations.append(validation)
            evidence_by_id[diagnosis_id] = evidence
        eligible = [
            item for item in validations
            if item.valid
            and item.structured_output is not None
            and item.structured_output["skill_update_relevance"] == "update"
        ]
        eligible_ids = [item.diagnosis_id for item in eligible]
        if not eligible:
            return _enrich(
                _no_candidate(
                    "NO_UPDATE_ELIGIBLE_DIAGNOSIS",
                    reflector_calls=len(validations),
                    editor_calls=0,
                ),
                validations,
                eligible_ids,
            )
        signals = [_signal(item, evidence_by_id[item.diagnosis_id]) for item in eligible]

        def bounded_editor(request: EditorRequest) -> str:
            response = editor(
                DiagnosisEditorRequest(
                    candidate_id=request.candidate_id,
                    current_parent_skill=request.current_parent_skill,
                    eligible_diagnoses=tuple(copy.deepcopy(request.raw_patches)),
                )
            )
            return _guard_editor_response(response, request)

        decision = propose_from_update_signals(
            context, signals, bounded_editor, upstream_calls=len(validations)
        )
        return _enrich(decision, validations, eligible_ids)


def structured_skill(skill: str) -> dict[str, list[dict[str, str]]]:
    return copy.deepcopy(_parse_skill(skill))
