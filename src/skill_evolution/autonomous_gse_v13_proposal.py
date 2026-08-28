"""v0.13 dual-axis Diagnosis over the established bounded editor path."""

from __future__ import annotations

import copy
import json
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest, ProposalContext, ProposalDecision, _no_candidate,
    _parse_tagged_list, _string_list,
)
from src.skill_evolution.autonomous_gse_v05_proposal import (
    _parse_skill, _validate_context, propose_from_update_signals,
)
from src.skill_evolution.diagnosis_contract_v13 import (
    DiagnosisValidation, parse_and_validate_diagnosis, validate_task_evidence_group,
)
from src.skill_evolution.diagnosis_v13 import Diagnoser, MultiRolloutDiagnosisRequest

_TASK_SPECIFIC_RULE_PATTERNS = (
    re.compile(r"\b(?:enter|fill|set|select|choose)\b[^.!?\n]{0,120}\bfirst\b[^.!?\n]{0,120}\b(?:then|second)\b", re.IGNORECASE),
    re.compile(r"\b(?:enter|fill)\b[^.!?\n]{0,120}\bincluding\b[^.!?\n]{0,80}\bbefore\b[^.!?\n]{0,80}", re.IGNORECASE),
    re.compile(r"\b(?:[Ss]et|[Ss]elect|[Cc]hoose)\b[^.!?\n]{0,80}\bto\s+(?:a\s+|an\s+|the\s+)?[A-Z][A-Za-z0-9_-]*\b"),
    re.compile(r"(?:\b\d{4}-\d{2}-\d{2}\b|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|https?://\S+)", re.IGNORECASE),
)


def _contains_task_specific_recipe(text: str) -> bool:
    return any(pattern.search(text) for pattern in _TASK_SPECIFIC_RULE_PATTERNS)


@dataclass(frozen=True)
class DiagnosisEditorRequest:
    candidate_id: str
    current_parent_skill: str
    eligible_diagnoses: tuple[dict[str, Any], ...]
    domain_contexts: tuple[dict[str, Any], ...]


DiagnosisEditor = Callable[[DiagnosisEditorRequest], str]


class DiagnosisContractError(ValueError):
    code = "DIAGNOSIS_CONTRACT_ERROR"

    def __init__(self, validations: list[DiagnosisValidation]) -> None:
        self.validations = tuple(validations)
        self.invalid_diagnosis_ids = tuple(
            item.diagnosis_id for item in validations if not item.valid
        )
        super().__init__(f"{self.code}: {len(self.invalid_diagnosis_ids)} invalid Diagnoses")


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


def group_task_evidence(evidence: tuple[dict[str, Any], ...]) -> list[tuple[tuple[str, str], tuple[dict[str, Any], ...]]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    order: list[tuple[str, str]] = []
    for item in evidence:
        key = (str(item.get("domain", "")), str(item.get("task_id", "")))
        if key not in groups:
            order.append(key)
        groups[key].append(item)
    result = []
    for key in order:
        rollouts = tuple(sorted(groups[key], key=lambda item: item.get("rollout_index", 0)))
        errors = validate_task_evidence_group(rollouts)
        if errors:
            raise ValueError(errors[0])
        result.append((key, rollouts))
    return result


def _signal(item: DiagnosisValidation, task: tuple[str, str]) -> dict[str, Any]:
    assert item.structured_output is not None
    diagnosis = item.structured_output
    rec = diagnosis["update_recommendation"]
    return {
        "patch_id": item.diagnosis_id,
        "diagnosis_id": item.diagnosis_id,
        "derived_from_diagnosis_ids": [item.diagnosis_id],
        "task_identity": {"domain": task[0], "task_id": task[1]},
        "operation": rec["action"],
        "section": rec["target_section"],
        "target_rule_id": rec["target_rule_id"] or "",
        "objective": rec["objective"],
        "description": rec["description"],
        "update_axis": diagnosis["update_axis"],
        "target_behavior": copy.deepcopy(diagnosis["target_behavior"]),
        "cross_rollout_analysis": copy.deepcopy(diagnosis["cross_rollout_analysis"]),
        "source_ids": list(item.source_ids),
        "repair_policy_ids": list(diagnosis["repair_policy_ids"]),
        "root_cause": copy.deepcopy(diagnosis["root_cause"]),
    }


def _valid_verification_target(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {
        "problem", "trigger_condition", "expected_behavior"
    } and all(isinstance(value.get(key), str) and value[key].strip() for key in value)


def _guard_editor_response(response: str, request: EditorRequest, sections: set[str]) -> str:
    edits, error = _parse_tagged_list(response, "CANONICAL_EDITS_JSON")
    if error or edits is None:
        return response
    signals = {item["patch_id"]: item for item in request.raw_patches}
    expected_fields = {
        "derived_from_patch_ids", "operation", "section", "target_rule_id",
        "text", "reason", "source_ids", "repair_policy_ids", "verification_target",
    }
    guarded: list[Any] = []
    for value in edits:
        edit = copy.deepcopy(value)
        if not isinstance(edit, dict):
            guarded.append(edit)
            continue
        patch_ids = _string_list(edit.get("derived_from_patch_ids"))
        sources = [signals[item] for item in (patch_ids or []) if item in signals]
        operation = edit.get("operation")
        exclusion = None
        if set(edit) != expected_fields:
            exclusion = "INVALID_CANONICAL_EDIT_FIELDS"
        elif not sources or len(sources) != len(patch_ids or []):
            exclusion = "DIAGNOSIS_TARGET_DRIFT"
        elif operation == "add":
            if any(item["operation"] != "add" for item in sources) or edit.get("section") not in sections or edit.get("target_rule_id", "") not in {None, ""}:
                exclusion = "DIAGNOSIS_TARGET_DRIFT"
        else:
            expected = {(item["operation"], item["section"], item.get("target_rule_id", "")) for item in sources}
            actual = (operation, edit.get("section"), edit.get("target_rule_id", ""))
            if operation not in {"replace", "delete"} or expected != {actual}:
                exclusion = "DIAGNOSIS_TARGET_DRIFT"
        if exclusion is None and not _valid_verification_target(edit.get("verification_target")):
            exclusion = "INVALID_VERIFICATION_TARGET"
        if exclusion is None and isinstance(edit.get("text"), str) and any(
            policy_id.casefold() in edit["text"].casefold()
            for source in sources for policy_id in source["repair_policy_ids"]
        ):
            exclusion = "POLICY_ID_LEAKAGE"
        if exclusion is None and operation in {"add", "replace"} and isinstance(edit.get("text"), str) and _contains_task_specific_recipe(edit["text"]):
            exclusion = "TASK_SPECIFIC_RULE"
        if exclusion:
            edit["v13_validation_error"] = exclusion
            edit["derived_from_patch_ids"] = []
        guarded.append(edit)
    return "<CANONICAL_EDITS_JSON>" + json.dumps(guarded, ensure_ascii=False) + "</CANONICAL_EDITS_JSON>"


def _enrich_decision(decision: ProposalDecision, validations: list[DiagnosisValidation], eligible_ids: list[str]) -> DiagnosisProposalDecision:
    fields = copy.deepcopy(decision.__dict__)
    canonical_by_id = {
        item.get("edit_id"): item for item in fields["canonical_edits"] if isinstance(item, dict)
    }
    enriched_applied = []
    for index, edit in enumerate(fields["applied_edits"], start=1):
        enriched = copy.deepcopy(edit)
        canonical = canonical_by_id.get(edit.get("edit_id"), {})
        enriched["canonical_edit_id"] = f"canonical_edit_{index:03d}"
        enriched["verification_target"] = copy.deepcopy(canonical.get("verification_target"))
        enriched_applied.append(enriched)
    fields["applied_edits"] = enriched_applied
    fields["reflector_calls"] = len(validations)
    return DiagnosisProposalDecision(
        **fields, diagnosis_calls=len(validations),
        diagnoses=[item.as_dict() for item in validations],
        eligible_diagnosis_ids=eligible_ids,
    )


class MultiRolloutDiagnosisProposalOperator:
    name = "v13_dual_axis_mechanism_preserving_bounded_edit"

    def propose(
        self, context: ProposalContext, diagnoser: Diagnoser, editor: DiagnosisEditor, *,
        domain_contexts: dict[str, dict[str, Any]],
    ) -> DiagnosisProposalDecision:
        sections, _, _, _ = _validate_context(context)
        grouped = group_task_evidence(context.current_batch_governed_evidence)
        validations: list[DiagnosisValidation] = []
        tasks_by_diagnosis: dict[str, tuple[str, str]] = {}
        for index, (task, rollouts) in enumerate(grouped, start=1):
            diagnosis_id = f"diagnosis_{index:03d}"
            domain_context = domain_contexts.get(task[0])
            if (
                not isinstance(domain_context, dict)
                or not isinstance(domain_context.get("original_domain_policy"), str)
                or not domain_context["original_domain_policy"].strip()
                or not isinstance(domain_context.get("available_tool_contracts"), (list, tuple))
                or not domain_context["available_tool_contracts"]
            ):
                raise ValueError(f"Missing authoritative domain context for {task[0]}.")
            response = diagnoser(MultiRolloutDiagnosisRequest(
                candidate_id=context.candidate_id, diagnosis_id=diagnosis_id,
                current_parent_skill=context.parent_skill,
                task_context={"domain": task[0], "task_id": task[1]},
                original_domain_policy=domain_context["original_domain_policy"],
                available_tool_contracts=tuple(copy.deepcopy(
                    domain_context["available_tool_contracts"]
                )),
                rollouts=copy.deepcopy(rollouts),
            ))
            validation = parse_and_validate_diagnosis(
                diagnosis_id, response, experiences=rollouts, skill_sections=sections
            )
            validations.append(validation)
            tasks_by_diagnosis[diagnosis_id] = task
        if any(not item.valid for item in validations):
            raise DiagnosisContractError(validations)
        eligible = [
            item for item in validations
            if item.structured_output is not None
            and item.structured_output["skill_update_relevance"] == "update"
        ]
        eligible_ids = [item.diagnosis_id for item in eligible]
        if not eligible:
            return _enrich_decision(_no_candidate(
                "NO_UPDATE_ELIGIBLE_DIAGNOSIS", reflector_calls=len(validations), editor_calls=0
            ), validations, eligible_ids)
        signals = [_signal(item, tasks_by_diagnosis[item.diagnosis_id]) for item in eligible]
        eligible_domains = sorted({tasks_by_diagnosis[item.diagnosis_id][0] for item in eligible})

        def bounded_editor(request: EditorRequest) -> str:
            response = editor(DiagnosisEditorRequest(
                candidate_id=request.candidate_id,
                current_parent_skill=request.current_parent_skill,
                eligible_diagnoses=tuple(copy.deepcopy(request.raw_patches)),
                domain_contexts=tuple({
                    "domain": domain,
                    "original_domain_policy": domain_contexts[domain]["original_domain_policy"],
                    "available_tool_contracts": copy.deepcopy(
                        domain_contexts[domain]["available_tool_contracts"]
                    ),
                } for domain in eligible_domains),
            ))
            return _guard_editor_response(response, request, set(sections))

        decision = propose_from_update_signals(context, signals, bounded_editor, upstream_calls=len(validations))
        return _enrich_decision(decision, validations, eligible_ids)


def structured_skill(skill: str) -> dict[str, list[dict[str, str]]]:
    return copy.deepcopy(_parse_skill(skill))
