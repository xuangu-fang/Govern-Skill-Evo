"""Pure governed-reflection Proposal logic for Autonomous GSE v0.3."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, Callable


MAXIMUM_RAW_PATCHES_PER_REFLECTOR = 4
MAXIMUM_SKILL_RULES = 18
MAXIMUM_SKILL_WORDS = 900
ALLOWED_OPERATIONS = {"add", "replace", "delete"}
SUCCESS_STATES = {"compliant_success", "violating_success"}
FAILURE_STATES = {"compliant_failure", "violating_failure"}
ELIGIBLE_EVIDENCE_STATES = SUCCESS_STATES | FAILURE_STATES
SKILL_TITLE = "SuiteCRM Operational Skill"
SKILL_SECTIONS = (
    "Planning and navigation",
    "Execution patterns",
    "Form entry and verification",
    "Error recovery and stopping",
)
FORBIDDEN_CONTEXT_KEYS = {
    "selection",
    "selection_data",
    "selection_results",
    "test",
    "test_data",
    "test_results",
}


class ProposalContractError(ValueError):
    """Raised when the v0.3 Proposal input contract is invalid."""


@dataclass(frozen=True)
class ProposalContext:
    candidate_id: str
    parent_skill: str
    current_batch_governed_evidence: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ReflectorRequest:
    candidate_id: str
    reflector: str
    current_parent_skill: str
    current_batch_evidence: tuple[dict[str, Any], ...]
    maximum_raw_patches: int


@dataclass(frozen=True)
class EditorRequest:
    candidate_id: str
    current_parent_skill: str
    raw_patches: tuple[dict[str, Any], ...]


Reflector = Callable[[ReflectorRequest], str]
Editor = Callable[[EditorRequest], str]


@dataclass(frozen=True)
class ProposalDecision:
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


def _contains_forbidden_context_key(value: Any) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in FORBIDDEN_CONTEXT_KEYS for key in value):
            return True
        return any(_contains_forbidden_context_key(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_context_key(item) for item in value)
    return False


def _parse_skill(skill: str) -> dict[str, list[str]]:
    if not isinstance(skill, str) or not skill.strip():
        raise ProposalContractError("Parent Skill must be non-empty text.")

    expected_headings = [
        f"# {SKILL_TITLE}",
        *(f"## {section}" for section in SKILL_SECTIONS),
    ]
    headings = [line.strip() for line in skill.splitlines() if line.startswith("#")]
    if headings != expected_headings:
        raise ProposalContractError("Parent Skill headings are invalid.")

    sections = {section: [] for section in SKILL_SECTIONS}
    current_section: str | None = None
    for raw_line in skill.splitlines():
        line = raw_line.strip()
        if not line or line == f"# {SKILL_TITLE}":
            continue
        if line.startswith("## "):
            current_section = line[3:]
            continue
        if not line.startswith("- ") or current_section not in sections:
            raise ProposalContractError(
                "Parent Skill content must contain only Markdown bullets."
            )
        clause = line[2:].strip()
        if not clause:
            raise ProposalContractError("Parent Skill contains an empty rule.")
        sections[current_section].append(clause)

    clauses = [clause for values in sections.values() for clause in values]
    if len(clauses) > MAXIMUM_SKILL_RULES:
        raise ProposalContractError("Parent Skill exceeds the rule limit.")
    if len(skill.split()) > MAXIMUM_SKILL_WORDS:
        raise ProposalContractError("Parent Skill exceeds the word limit.")
    if len(set(clauses)) != len(clauses):
        raise ProposalContractError("Parent Skill contains duplicate rules.")
    return sections


def _render_skill(sections: dict[str, list[str]]) -> str:
    lines = [f"# {SKILL_TITLE}", ""]
    for section in SKILL_SECTIONS:
        lines.append(f"## {section}")
        lines.append("")
        for clause in sections[section]:
            lines.append(f"- {clause}")
        if sections[section]:
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _policy_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    candidate = value.get("policy_template_id")
    return candidate if isinstance(candidate, str) and candidate else None


def _validate_context(
    context: ProposalContext,
) -> tuple[
    dict[str, list[str]],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
    dict[str, tuple[str, ...]],
]:
    if not isinstance(context.candidate_id, str) or not context.candidate_id:
        raise ProposalContractError("Candidate ID must be non-empty text.")
    sections = _parse_skill(context.parent_skill)
    evidence = context.current_batch_governed_evidence
    if not isinstance(evidence, tuple):
        raise ProposalContractError("Current-batch evidence must be a tuple.")
    if _contains_forbidden_context_key(evidence):
        raise ProposalContractError(
            "Selection or Test data cannot enter the Proposal context."
        )

    success: list[dict[str, Any]] = []
    failure: list[dict[str, Any]] = []
    allowed_policies: dict[str, tuple[str, ...]] = {}
    for item in evidence:
        if not isinstance(item, dict):
            raise ProposalContractError("Every evidence item must be an object.")
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise ProposalContractError("Every evidence item needs a source_id.")
        if source_id in allowed_policies:
            raise ProposalContractError("Evidence source IDs must be unique.")
        state = item.get("state")
        if state not in ELIGIBLE_EVIDENCE_STATES:
            raise ProposalContractError("Evidence state is not eligible.")
        if item.get("task_success") is not (state in SUCCESS_STATES):
            raise ProposalContractError("Evidence state and task outcome disagree.")
        feedback = item.get("process_feedback")
        if not isinstance(feedback, dict):
            raise ProposalContractError("Evidence process feedback is invalid.")
        violated = feedback.get("violated_policies")
        if not isinstance(violated, list):
            raise ProposalContractError("Violated policies must be a list.")
        policy_ids = [policy for value in violated if (policy := _policy_id(value))]
        allowed_policies[source_id] = tuple(dict.fromkeys(policy_ids))
        (success if state in SUCCESS_STATES else failure).append(item)

    return sections, tuple(success), tuple(failure), allowed_policies


def _parse_tagged_list(
    response: Any,
    tag: str,
) -> tuple[list[Any] | None, str | None]:
    if not isinstance(response, str):
        return None, "UNPARSEABLE_RESPONSE"
    match = re.fullmatch(
        rf"\s*<{tag}>\s*(.*?)\s*</{tag}>\s*",
        response,
        flags=re.DOTALL,
    )
    if match is None:
        return None, "UNPARSEABLE_RESPONSE"
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, "UNPARSEABLE_RESPONSE"
    if not isinstance(parsed, list):
        return None, "EDITS_NOT_LIST"
    return parsed, None


def _raw_patches_for_reflector(
    reflector: str,
    response: str,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    parsed, reason = _parse_tagged_list(response, "RAW_PATCHES_JSON")
    if reason is not None:
        return None, reason
    assert parsed is not None
    patches: list[dict[str, Any]] = []
    for index, value in enumerate(
        parsed[:MAXIMUM_RAW_PATCHES_PER_REFLECTOR],
        start=1,
    ):
        if not isinstance(value, dict):
            continue
        patch = copy.deepcopy(value)
        patch["patch_id"] = f"{reflector}_patch_{index:03d}"
        patch["reflector"] = reflector
        patches.append(patch)
    return patches, None


def _valid_clause(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and "\n" not in value
        and not value.strip().startswith(("#", "- "))
    )


def _try_apply_edit(
    original: dict[str, list[str]],
    current: dict[str, list[str]],
    touched_parent_clauses: set[tuple[str, str]],
    edit: Any,
) -> tuple[dict[str, list[str]] | None, str | None]:
    if not isinstance(edit, dict):
        return None, "INVALID_EDIT_FORMAT"
    operation = edit.get("operation")
    if operation not in ALLOWED_OPERATIONS:
        return None, "OPERATION_NOT_ALLOWED"
    section = edit.get("section")
    if section not in SKILL_SECTIONS:
        return None, "SECTION_NOT_FOUND"

    target = edit.get("target_clause")
    text = edit.get("text")
    trial = copy.deepcopy(current)
    if operation == "add":
        if target not in {None, ""}:
            return None, "INVALID_EDIT_FORMAT"
        if not _valid_clause(text):
            return None, "MISSING_EDIT_TEXT"
        clause = text.strip()
        if any(clause in clauses for clauses in current.values()):
            return None, "DUPLICATE_CLAUSE"
        trial[section].append(clause)
    else:
        if not _valid_clause(target):
            return None, "TARGET_CLAUSE_NOT_FOUND"
        parent_clause = target.strip()
        if parent_clause not in original[section]:
            return None, "TARGET_CLAUSE_NOT_FOUND"
        touched = (section, parent_clause)
        if touched in touched_parent_clauses:
            return None, "CONFLICTING_EDIT"
        if operation == "replace":
            if not _valid_clause(text):
                return None, "MISSING_EDIT_TEXT"
            clause = text.strip()
            if clause == parent_clause:
                return None, "NO_SKILL_CHANGE"
            if any(
                clause in clauses
                for name, clauses in current.items()
                if name != section or clause != parent_clause
            ):
                return None, "DUPLICATE_CLAUSE"
            position = trial[section].index(parent_clause)
            trial[section][position] = clause
        else:
            if text not in {None, ""}:
                return None, "INVALID_EDIT_FORMAT"
            trial[section].remove(parent_clause)

    rendered = _render_skill(trial)
    rule_count = sum(len(clauses) for clauses in trial.values())
    if rule_count > MAXIMUM_SKILL_RULES or len(rendered.split()) > MAXIMUM_SKILL_WORDS:
        return None, "STRUCTURE_INVALID"
    return trial, None


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        return None
    return list(value)


def _canonical_record(edit_id: str, edit: dict[str, Any]) -> dict[str, Any]:
    return {
        "edit_id": edit_id,
        "derived_from_patch_ids": list(edit.get("derived_from_patch_ids", [])),
        "operation": edit.get("operation"),
        "section": edit.get("section"),
        "target_clause": edit.get("target_clause", ""),
        "text": edit.get("text", ""),
        "reason": edit.get("reason", ""),
        "source_ids": _string_list(edit.get("source_ids")) or [],
        "repair_policy_ids": _string_list(edit.get("repair_policy_ids")) or [],
    }


def _lineage_is_valid(
    edit: Any,
    raw_patch_ids: set[str],
    consumed_patch_ids: set[str],
) -> bool:
    if not isinstance(edit, dict):
        return False
    patch_ids = _string_list(edit.get("derived_from_patch_ids"))
    if not patch_ids or len(set(patch_ids)) != len(patch_ids):
        return False
    if any(patch_id not in raw_patch_ids for patch_id in patch_ids):
        return False
    return not consumed_patch_ids.intersection(patch_ids)


def _audit_provenance(
    applied: list[tuple[str, dict[str, Any]]],
    allowed_policies: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    verified_edits = 0
    for edit_id, edit in applied:
        edit_issues: list[dict[str, Any]] = []
        source_ids = _string_list(edit.get("source_ids"))
        repair_policy_ids = _string_list(edit.get("repair_policy_ids"))
        if not source_ids or repair_policy_ids is None:
            edit_issues.append({"code": "MISSING_PROVENANCE", "edit_id": edit_id})
        else:
            for source_id in source_ids:
                if source_id not in allowed_policies:
                    edit_issues.append(
                        {
                            "code": "UNKNOWN_SOURCE_ID",
                            "edit_id": edit_id,
                            "source_id": source_id,
                        }
                    )
            supported_policies = {
                policy_id
                for source_id in source_ids
                for policy_id in allowed_policies.get(source_id, ())
            }
            for policy_id in repair_policy_ids:
                if policy_id not in supported_policies:
                    edit_issues.append(
                        {
                            "code": "UNSUPPORTED_REPAIR_POLICY",
                            "edit_id": edit_id,
                            "policy_id": policy_id,
                        }
                    )
        if not edit_issues:
            verified_edits += 1
        issues.extend(edit_issues)

    unverified_edits = len(applied) - verified_edits
    return {
        "status": "VERIFIED" if unverified_edits == 0 else "UNVERIFIED",
        "verified_edits": verified_edits,
        "unverified_edits": unverified_edits,
        "issues": issues,
    }


def _no_candidate(
    code: str,
    *,
    reflector_calls: int,
    editor_calls: int,
    raw_patches: list[dict[str, Any]] | None = None,
    canonical_edits: list[Any] | None = None,
    excluded_edits: list[dict[str, Any]] | None = None,
    detail: str | None = None,
) -> ProposalDecision:
    reason = {"code": code}
    if detail is not None:
        reason["detail"] = detail
    return ProposalDecision(
        proposal_status="NO_CANDIDATE",
        proposal_reason=reason,
        reflector_calls=reflector_calls,
        editor_calls=editor_calls,
        raw_patches=copy.deepcopy(raw_patches or []),
        canonical_edits=copy.deepcopy(canonical_edits or []),
        applied_edits=[],
        excluded_edits=copy.deepcopy(excluded_edits or []),
        candidate_skill=None,
        provenance_status=None,
        provenance_audit=None,
    )


class GovernedReflectionEditorProposalOperator:
    """Construct one Candidate from reflected and canonicalized edits."""

    name = "governed_reflection_editor"

    def propose(
        self,
        context: ProposalContext,
        success_reflector: Reflector,
        failure_reflector: Reflector,
        editor: Editor,
    ) -> ProposalDecision:
        original, success, failure, allowed_policies = _validate_context(context)
        raw_patches: list[dict[str, Any]] = []
        reflector_calls = 0
        for reflector_name, evidence, reflector in (
            ("success", success, success_reflector),
            ("failure", failure, failure_reflector),
        ):
            if not evidence:
                continue
            request = ReflectorRequest(
                candidate_id=context.candidate_id,
                reflector=reflector_name,
                current_parent_skill=context.parent_skill,
                current_batch_evidence=copy.deepcopy(evidence),
                maximum_raw_patches=MAXIMUM_RAW_PATCHES_PER_REFLECTOR,
            )
            response = reflector(request)
            reflector_calls += 1
            patches, reason = _raw_patches_for_reflector(reflector_name, response)
            if reason is not None:
                return _no_candidate(
                    reason,
                    reflector_calls=reflector_calls,
                    editor_calls=0,
                    raw_patches=raw_patches,
                )
            assert patches is not None
            raw_patches.extend(patches)

        if not raw_patches:
            return _no_candidate(
                "EMPTY_EDITS",
                reflector_calls=reflector_calls,
                editor_calls=0,
            )

        editor_request = EditorRequest(
            candidate_id=context.candidate_id,
            current_parent_skill=context.parent_skill,
            raw_patches=copy.deepcopy(tuple(raw_patches)),
        )
        editor_response = editor(editor_request)
        parsed_edits, reason = _parse_tagged_list(
            editor_response,
            "CANONICAL_EDITS_JSON",
        )
        if reason is not None:
            return _no_candidate(
                reason,
                reflector_calls=reflector_calls,
                editor_calls=1,
                raw_patches=raw_patches,
            )
        assert parsed_edits is not None
        if not parsed_edits:
            return _no_candidate(
                "EMPTY_EDITS",
                reflector_calls=reflector_calls,
                editor_calls=1,
                raw_patches=raw_patches,
            )

        current = copy.deepcopy(original)
        touched_parent_clauses: set[tuple[str, str]] = set()
        raw_patch_ids = {patch["patch_id"] for patch in raw_patches}
        consumed_patch_ids: set[str] = set()
        canonical_edits: list[Any] = []
        applied_records: list[dict[str, Any]] = []
        applied_raw: list[tuple[str, dict[str, Any]]] = []
        excluded_edits: list[dict[str, Any]] = []
        for index, value in enumerate(parsed_edits, start=1):
            edit_id = f"edit_{index:03d}"
            edit = copy.deepcopy(value)
            if isinstance(edit, dict):
                edit["edit_id"] = edit_id
            canonical_edits.append(edit)
            if not _lineage_is_valid(edit, raw_patch_ids, consumed_patch_ids):
                excluded_edits.append(
                    {"edit_id": edit_id, "reason": "INVALID_EDIT_FORMAT"}
                )
                continue
            assert isinstance(edit, dict)
            trial, exclusion_reason = _try_apply_edit(
                original,
                current,
                touched_parent_clauses,
                edit,
            )
            if exclusion_reason is not None:
                excluded_edits.append(
                    {"edit_id": edit_id, "reason": exclusion_reason}
                )
                continue
            assert trial is not None
            current = trial
            patch_ids = edit["derived_from_patch_ids"]
            consumed_patch_ids.update(patch_ids)
            if edit["operation"] != "add":
                touched_parent_clauses.add(
                    (edit["section"], edit["target_clause"].strip())
                )
            applied_records.append(_canonical_record(edit_id, edit))
            applied_raw.append((edit_id, edit))

        if not applied_records:
            return _no_candidate(
                "NO_APPLICABLE_EDITS",
                reflector_calls=reflector_calls,
                editor_calls=1,
                raw_patches=raw_patches,
                canonical_edits=canonical_edits,
                excluded_edits=excluded_edits,
            )

        candidate_skill = _render_skill(current)
        if candidate_skill == _render_skill(original):
            return _no_candidate(
                "NO_SKILL_CHANGE",
                reflector_calls=reflector_calls,
                editor_calls=1,
                raw_patches=raw_patches,
                canonical_edits=canonical_edits,
                excluded_edits=excluded_edits,
            )

        provenance_audit = _audit_provenance(applied_raw, allowed_policies)
        return ProposalDecision(
            proposal_status="CANDIDATE",
            proposal_reason={"code": "CANDIDATE_CONSTRUCTED"},
            reflector_calls=reflector_calls,
            editor_calls=1,
            raw_patches=copy.deepcopy(raw_patches),
            canonical_edits=copy.deepcopy(canonical_edits),
            applied_edits=applied_records,
            excluded_edits=excluded_edits,
            candidate_skill=candidate_skill,
            provenance_status=provenance_audit["status"],
            provenance_audit=provenance_audit,
        )
