"""Pure bounded-edit Proposal logic for Autonomous GSE v0.2."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, Callable


MAXIMUM_EDITS = 6
MAXIMUM_SKILL_RULES = 18
MAXIMUM_SKILL_WORDS = 900
ALLOWED_OPERATIONS = {"add", "replace", "delete"}
ELIGIBLE_EVIDENCE_STATES = {"compliant_success", "violating_success"}
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
    """Raised when the v0.2 Proposal input contract is invalid."""


@dataclass(frozen=True)
class ProposalContext:
    candidate_id: str
    parent_skill: str
    current_batch_success_evidence: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class LearnerRequest:
    """The complete and isolated input visible to the v0.2 Learner."""

    candidate_id: str
    current_parent_skill: str
    current_batch_success_evidence: tuple[dict[str, Any], ...]
    maximum_edits: int
    allowed_source_ids: tuple[str, ...]
    allowed_repair_policy_ids_by_source: dict[str, tuple[str, ...]]


Learner = Callable[[LearnerRequest], str]


@dataclass(frozen=True)
class ProposalDecision:
    proposal_status: str
    proposal_reason: dict[str, str]
    learner_calls: int
    proposed_edits: list[Any]
    selected_edits: list[dict[str, Any]]
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
) -> tuple[dict[str, list[str]], dict[str, tuple[str, ...]]]:
    if not isinstance(context.candidate_id, str) or not context.candidate_id:
        raise ProposalContractError("Candidate ID must be non-empty text.")
    sections = _parse_skill(context.parent_skill)
    evidence = context.current_batch_success_evidence
    if not isinstance(evidence, tuple):
        raise ProposalContractError("Current-batch success evidence must be a tuple.")
    if _contains_forbidden_context_key(evidence):
        raise ProposalContractError(
            "Selection or Test data cannot enter the Proposal context."
        )

    allowed_policies: dict[str, tuple[str, ...]] = {}
    for item in evidence:
        if not isinstance(item, dict):
            raise ProposalContractError("Every evidence item must be an object.")
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise ProposalContractError("Every evidence item needs a source_id.")
        if source_id in allowed_policies:
            raise ProposalContractError("Evidence source IDs must be unique.")
        if item.get("task_success") is not True:
            raise ProposalContractError("Proposal evidence must be task-successful.")
        if item.get("state") not in ELIGIBLE_EVIDENCE_STATES:
            raise ProposalContractError("Proposal evidence state is not eligible.")
        feedback = item.get("process_feedback")
        if not isinstance(feedback, dict):
            raise ProposalContractError("Evidence process feedback is invalid.")
        violated = feedback.get("violated_policies")
        if not isinstance(violated, list):
            raise ProposalContractError("Violated policies must be a list.")
        policy_ids = [policy for value in violated if (policy := _policy_id(value))]
        allowed_policies[source_id] = tuple(dict.fromkeys(policy_ids))
    return sections, allowed_policies


def _parse_learner_response(response: Any) -> tuple[list[Any] | None, str | None]:
    if not isinstance(response, str):
        return None, "UNPARSEABLE_RESPONSE"
    match = re.fullmatch(
        r"\s*<EDITS_JSON>\s*(.*?)\s*</EDITS_JSON>\s*",
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
    if not parsed:
        return [], "EMPTY_EDITS"
    return parsed, None


def _valid_clause(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and "\n" not in value
        and not value.strip().startswith(("#", "- "))
    )


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        return None
    return list(value)


def _selected_record(index: int, edit: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "edit_index": index,
        "status": "SELECTED",
        "operation": edit["operation"],
        "section": edit["section"],
    }
    if edit.get("target_clause"):
        record["target_clause"] = edit["target_clause"].strip()
    if edit.get("text"):
        record["text"] = edit["text"].strip()
    if isinstance(edit.get("reason"), str) and edit["reason"].strip():
        record["reason"] = edit["reason"].strip()
    source_ids = _string_list(edit.get("source_ids"))
    if source_ids is not None:
        record["source_ids"] = source_ids
    policy_ids = _string_list(edit.get("repair_policy_ids"))
    if policy_ids is not None:
        record["repair_policy_ids"] = policy_ids
    return record


def _excluded_record(index: int, reason: str, edit: Any) -> dict[str, Any]:
    return {
        "edit_index": index,
        "status": "EXCLUDED",
        "reason": reason,
        "original_edit": copy.deepcopy(edit),
    }


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


def _audit_provenance(
    selected: list[tuple[int, dict[str, Any]]],
    allowed_policies: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    verified_edits = 0
    for index, edit in selected:
        edit_issues: list[dict[str, Any]] = []
        source_ids = _string_list(edit.get("source_ids"))
        repair_policy_ids = _string_list(edit.get("repair_policy_ids"))
        if not source_ids or repair_policy_ids is None:
            edit_issues.append(
                {"code": "MISSING_PROVENANCE", "edit_index": index}
            )
        else:
            for source_id in source_ids:
                if source_id not in allowed_policies:
                    edit_issues.append(
                        {
                            "code": "UNKNOWN_SOURCE_ID",
                            "edit_index": index,
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
                            "edit_index": index,
                            "policy_id": policy_id,
                        }
                    )
        if not edit_issues:
            verified_edits += 1
        issues.extend(edit_issues)

    unverified_edits = len(selected) - verified_edits
    return {
        "status": "VERIFIED" if unverified_edits == 0 else "UNVERIFIED",
        "verified_edits": verified_edits,
        "unverified_edits": unverified_edits,
        "issues": issues,
    }


def _no_candidate(
    code: str,
    *,
    learner_calls: int,
    proposed_edits: list[Any] | None = None,
    excluded_edits: list[dict[str, Any]] | None = None,
    detail: str | None = None,
) -> ProposalDecision:
    reason = {"code": code}
    if detail is not None:
        reason["detail"] = detail
    return ProposalDecision(
        proposal_status="NO_CANDIDATE",
        proposal_reason=reason,
        learner_calls=learner_calls,
        proposed_edits=copy.deepcopy(proposed_edits or []),
        selected_edits=[],
        excluded_edits=copy.deepcopy(excluded_edits or []),
        candidate_skill=None,
        provenance_status=None,
        provenance_audit=None,
    )


class BoundedEditProposalOperator:
    """Construct one Candidate from up to six applicable edits."""

    name = "bounded_edit"

    def propose(
        self,
        context: ProposalContext,
        learner: Learner,
    ) -> ProposalDecision:
        original_sections, allowed_policies = _validate_context(context)
        if not context.current_batch_success_evidence:
            return _no_candidate(
                "NO_APPLICABLE_EDITS",
                learner_calls=0,
                detail="No eligible current-batch success evidence.",
            )

        request = LearnerRequest(
            candidate_id=context.candidate_id,
            current_parent_skill=context.parent_skill,
            current_batch_success_evidence=copy.deepcopy(
                context.current_batch_success_evidence
            ),
            maximum_edits=MAXIMUM_EDITS,
            allowed_source_ids=tuple(allowed_policies),
            allowed_repair_policy_ids_by_source=copy.deepcopy(allowed_policies),
        )
        response = learner(request)
        proposed_edits, parse_reason = _parse_learner_response(response)
        if parse_reason is not None:
            return _no_candidate(parse_reason, learner_calls=1)
        assert proposed_edits is not None

        current_sections = copy.deepcopy(original_sections)
        touched_parent_clauses: set[tuple[str, str]] = set()
        selected_records: list[dict[str, Any]] = []
        selected_raw: list[tuple[int, dict[str, Any]]] = []
        excluded_records: list[dict[str, Any]] = []
        for index, edit in enumerate(proposed_edits, start=1):
            if len(selected_records) == MAXIMUM_EDITS:
                excluded_records.append(
                    _excluded_record(index, "EDIT_BUDGET_EXCEEDED", edit)
                )
                continue
            trial, exclusion_reason = _try_apply_edit(
                original_sections,
                current_sections,
                touched_parent_clauses,
                edit,
            )
            if exclusion_reason is not None:
                excluded_records.append(
                    _excluded_record(index, exclusion_reason, edit)
                )
                continue
            assert trial is not None and isinstance(edit, dict)
            current_sections = trial
            if edit["operation"] != "add":
                touched_parent_clauses.add(
                    (edit["section"], edit["target_clause"].strip())
                )
            selected_records.append(_selected_record(index, edit))
            selected_raw.append((index, copy.deepcopy(edit)))

        if not selected_records:
            return _no_candidate(
                "NO_APPLICABLE_EDITS",
                learner_calls=1,
                proposed_edits=proposed_edits,
                excluded_edits=excluded_records,
            )

        candidate_skill = _render_skill(current_sections)
        if candidate_skill == _render_skill(original_sections):
            excluded_records.extend(
                _excluded_record(index, "NO_SKILL_CHANGE", edit)
                for index, edit in selected_raw
            )
            excluded_records.sort(key=lambda item: item["edit_index"])
            return _no_candidate(
                "NO_SKILL_CHANGE",
                learner_calls=1,
                proposed_edits=proposed_edits,
                excluded_edits=excluded_records,
            )

        provenance_audit = _audit_provenance(selected_raw, allowed_policies)
        return ProposalDecision(
            proposal_status="CANDIDATE",
            proposal_reason={"code": "CANDIDATE_CONSTRUCTED"},
            learner_calls=1,
            proposed_edits=copy.deepcopy(proposed_edits),
            selected_edits=selected_records,
            excluded_edits=excluded_records,
            candidate_skill=candidate_skill,
            provenance_status=provenance_audit["status"],
            provenance_audit=provenance_audit,
        )
