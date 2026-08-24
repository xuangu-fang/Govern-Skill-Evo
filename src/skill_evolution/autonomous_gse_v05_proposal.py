"""Rule-ID based governed Proposal logic for Autonomous GSE v0.5."""

from __future__ import annotations

import copy
import re
from typing import Any

from src.skill_evolution.autonomous_gse_v03_proposal import (
    ALLOWED_OPERATIONS,
    ELIGIBLE_EVIDENCE_STATES,
    FORBIDDEN_CONTEXT_KEYS,
    MAXIMUM_RAW_PATCHES_PER_REFLECTOR,
    MAXIMUM_SKILL_RULES,
    MAXIMUM_SKILL_WORDS,
    SKILL_SECTIONS,
    SKILL_TITLE,
    SUCCESS_STATES,
    Editor,
    EditorRequest,
    ProposalContext,
    ProposalContractError,
    ProposalDecision,
    Reflector,
    ReflectorRequest,
    _audit_provenance,
    _no_candidate,
    _parse_tagged_list,
    _policy_id,
    _string_list,
    _valid_clause,
)

RULE_ID_PATTERN = re.compile(r"^rule_[0-9]{3,}$")
MARKDOWN_BULLET_PATTERN = re.compile(r"^\s*(?:[-*+]|[0-9]+[.)])\s+")


def normalize_markdown_clause(value: Any) -> str | None:
    """Normalize legacy clause text before a compatibility-only match."""

    if not isinstance(value, str):
        return None
    normalized = " ".join(value.strip().split())
    normalized = MARKDOWN_BULLET_PATTERN.sub("", normalized, count=1).strip()
    return normalized or None


def _contains_forbidden_context_key(value: Any) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in FORBIDDEN_CONTEXT_KEYS for key in value):
            return True
        return any(_contains_forbidden_context_key(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_context_key(item) for item in value)
    return False


def _parse_skill(skill: str) -> dict[str, list[dict[str, str]]]:
    if not isinstance(skill, str) or not skill.strip():
        raise ProposalContractError("Parent Skill must be non-empty text.")
    expected_headings = [
        f"# {SKILL_TITLE}",
        *(f"## {section}" for section in SKILL_SECTIONS),
    ]
    headings = [line.strip() for line in skill.splitlines() if line.startswith("#")]
    if headings != expected_headings:
        raise ProposalContractError("Parent Skill headings are invalid.")

    sections: dict[str, list[dict[str, str]]] = {
        section: [] for section in SKILL_SECTIONS
    }
    current_section: str | None = None
    rule_number = 0
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
        clause = normalize_markdown_clause(line)
        if clause is None:
            raise ProposalContractError("Parent Skill contains an empty rule.")
        rule_number += 1
        sections[current_section].append(
            {"rule_id": f"rule_{rule_number:03d}", "clause": clause}
        )

    if rule_number > MAXIMUM_SKILL_RULES:
        raise ProposalContractError("Parent Skill exceeds the rule limit.")
    if len(skill.split()) > MAXIMUM_SKILL_WORDS:
        raise ProposalContractError("Parent Skill exceeds the word limit.")
    return sections


def annotate_parent_skill(skill: str) -> str:
    """Expose deterministic IDs to the v0.5 Reflector and Editor."""

    sections = _parse_skill(skill)
    lines = [f"# {SKILL_TITLE}", ""]
    for section in SKILL_SECTIONS:
        lines.extend((f"## {section}", ""))
        for rule in sections[section]:
            lines.append(f"- [{rule['rule_id']}] {rule['clause']}")
        if sections[section]:
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_skill(sections: dict[str, list[dict[str, str]]]) -> str:
    lines = [f"# {SKILL_TITLE}", ""]
    for section in SKILL_SECTIONS:
        lines.extend((f"## {section}", ""))
        for rule in sections[section]:
            lines.append(f"- {rule['clause']}")
        if sections[section]:
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _validate_context(
    context: ProposalContext,
) -> tuple[
    dict[str, list[dict[str, str]]],
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


def _raw_patches_for_reflector(
    reflector: str, response: str
) -> tuple[list[dict[str, Any]] | None, str | None]:
    parsed, reason = _parse_tagged_list(response, "RAW_PATCHES_JSON")
    if reason is not None:
        return None, reason
    assert parsed is not None
    patches = []
    for index, value in enumerate(
        parsed[:MAXIMUM_RAW_PATCHES_PER_REFLECTOR], start=1
    ):
        if not isinstance(value, dict):
            continue
        patch = copy.deepcopy(value)
        patch["patch_id"] = f"{reflector}_patch_{index:03d}"
        patch["reflector"] = reflector
        patches.append(patch)
    return patches, None


def _rule_index(
    sections: dict[str, list[dict[str, str]]]
) -> dict[str, tuple[str, dict[str, str]]]:
    return {
        rule["rule_id"]: (section, rule)
        for section, rules in sections.items()
        for rule in rules
    }


def _resolve_edit_target(
    edit: dict[str, Any],
    original: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, Any] | None, str | None]:
    resolved = copy.deepcopy(edit)
    operation = resolved.get("operation")
    if operation not in ALLOWED_OPERATIONS:
        return None, "OPERATION_NOT_ALLOWED"
    if resolved.get("section") not in SKILL_SECTIONS:
        return None, "SECTION_NOT_FOUND"
    if operation == "add":
        if resolved.get("target_rule_id") not in {None, ""}:
            return None, "INVALID_EDIT_FORMAT"
        if resolved.get("target_clause") not in {None, ""}:
            return None, "INVALID_EDIT_FORMAT"
        resolved["target_rule_id"] = ""
        resolved.pop("target_clause", None)
        resolved["target_resolution"] = "not_applicable"
        return resolved, None

    section = resolved.get("section")
    target_rule_id = resolved.get("target_rule_id")
    index = _rule_index(original)
    if isinstance(target_rule_id, str) and RULE_ID_PATTERN.fullmatch(
        target_rule_id
    ):
        target = index.get(target_rule_id)
        if target is None:
            return None, "TARGET_RULE_ID_NOT_FOUND"
        if target[0] != section:
            return None, "TARGET_RULE_SECTION_MISMATCH"
        resolved.pop("target_clause", None)
        resolved["target_resolution"] = "rule_id"
        return resolved, None

    legacy_target = normalize_markdown_clause(resolved.get("target_clause"))
    if legacy_target is None or section not in original:
        return None, "TARGET_RULE_ID_NOT_FOUND"
    matches = [
        rule["rule_id"]
        for rule in original[section]
        if normalize_markdown_clause(rule["clause"]) == legacy_target
    ]
    if not matches:
        return None, "TARGET_CLAUSE_NOT_FOUND"
    if len(matches) > 1:
        return None, "AMBIGUOUS_TARGET_CLAUSE"
    resolved["target_rule_id"] = matches[0]
    resolved["legacy_target_clause"] = resolved.get("target_clause")
    resolved.pop("target_clause", None)
    resolved["target_resolution"] = "normalized_target_clause"
    return resolved, None


def _next_rule_id(sections: dict[str, list[dict[str, str]]]) -> str:
    numbers = [
        int(rule["rule_id"].split("_")[1])
        for rules in sections.values()
        for rule in rules
    ]
    return f"rule_{max(numbers, default=0) + 1:03d}"


def _try_apply_edit(
    original: dict[str, list[dict[str, str]]],
    current: dict[str, list[dict[str, str]]],
    touched_rule_ids: set[str],
    edit: dict[str, Any],
) -> tuple[dict[str, list[dict[str, str]]] | None, str | None]:
    operation = edit.get("operation")
    if operation not in ALLOWED_OPERATIONS:
        return None, "OPERATION_NOT_ALLOWED"
    section = edit.get("section")
    if section not in SKILL_SECTIONS:
        return None, "SECTION_NOT_FOUND"
    text = edit.get("text")
    trial = copy.deepcopy(current)

    if operation == "add":
        if not _valid_clause(text):
            return None, "MISSING_EDIT_TEXT"
        clause = text.strip()
        if any(
            clause == rule["clause"]
            for rules in current.values()
            for rule in rules
        ):
            return None, "DUPLICATE_CLAUSE"
        trial[section].append(
            {"rule_id": _next_rule_id(current), "clause": clause}
        )
    else:
        target_rule_id = edit.get("target_rule_id")
        target = _rule_index(original).get(target_rule_id)
        if target is None:
            return None, "TARGET_RULE_ID_NOT_FOUND"
        if target_rule_id in touched_rule_ids:
            return None, "CONFLICTING_EDIT"
        current_target = _rule_index(current).get(target_rule_id)
        if current_target is None or current_target[0] != section:
            return None, "TARGET_RULE_ID_NOT_FOUND"
        rules = trial[section]
        position = next(
            index
            for index, rule in enumerate(rules)
            if rule["rule_id"] == target_rule_id
        )
        if operation == "replace":
            if not _valid_clause(text):
                return None, "MISSING_EDIT_TEXT"
            clause = text.strip()
            if clause == rules[position]["clause"]:
                return None, "NO_SKILL_CHANGE"
            if any(
                clause == rule["clause"]
                for rule_id, (_, rule) in _rule_index(current).items()
                if rule_id != target_rule_id
            ):
                return None, "DUPLICATE_CLAUSE"
            rules[position]["clause"] = clause
        else:
            if text not in {None, ""}:
                return None, "INVALID_EDIT_FORMAT"
            del rules[position]

    rendered = _render_skill(trial)
    rule_count = sum(len(rules) for rules in trial.values())
    if rule_count > MAXIMUM_SKILL_RULES or len(rendered.split()) > MAXIMUM_SKILL_WORDS:
        return None, "STRUCTURE_INVALID"
    return trial, None


def _lineage_is_valid(
    edit: Any, raw_patch_ids: set[str], consumed_patch_ids: set[str]
) -> bool:
    if not isinstance(edit, dict):
        return False
    patch_ids = _string_list(edit.get("derived_from_patch_ids"))
    if not patch_ids or len(set(patch_ids)) != len(patch_ids):
        return False
    if any(patch_id not in raw_patch_ids for patch_id in patch_ids):
        return False
    return not consumed_patch_ids.intersection(patch_ids)


def _merge_patch_provenance(
    edit: dict[str, Any], raw_patches_by_id: dict[str, dict[str, Any]]
) -> None:
    patch_ids = _string_list(edit.get("derived_from_patch_ids"))
    if (
        not patch_ids
        or _string_list(edit.get("source_ids")) is None
        or _string_list(edit.get("repair_policy_ids")) is None
        or any(patch_id not in raw_patches_by_id for patch_id in patch_ids)
    ):
        return
    edit["source_ids"] = list(
        dict.fromkeys(
            source_id
            for patch_id in patch_ids
            for source_id in (
                _string_list(raw_patches_by_id[patch_id].get("source_ids")) or []
            )
        )
    )
    edit["repair_policy_ids"] = list(
        dict.fromkeys(
            policy_id
            for patch_id in patch_ids
            for policy_id in (
                _string_list(
                    raw_patches_by_id[patch_id].get("repair_policy_ids")
                )
                or []
            )
        )
    )


def _canonical_record(edit_id: str, edit: dict[str, Any]) -> dict[str, Any]:
    return {
        "edit_id": edit_id,
        "derived_from_patch_ids": list(edit.get("derived_from_patch_ids", [])),
        "operation": edit.get("operation"),
        "section": edit.get("section"),
        "target_rule_id": edit.get("target_rule_id", ""),
        "target_resolution": edit.get("target_resolution"),
        "text": edit.get("text", ""),
        "reason": edit.get("reason", ""),
        "source_ids": _string_list(edit.get("source_ids")) or [],
        "repair_policy_ids": _string_list(edit.get("repair_policy_ids")) or [],
    }


def _edit_update_signals(
    context: ProposalContext,
    original: dict[str, list[dict[str, str]]],
    allowed_policies: dict[str, tuple[str, ...]],
    update_signals: list[dict[str, Any]],
    editor: Editor,
    *,
    upstream_calls: int,
) -> ProposalDecision:
    """Run shared bounded editing and deterministic Update over supplied signals."""

    if not update_signals:
        return _no_candidate(
            "EMPTY_EDITS", reflector_calls=upstream_calls, editor_calls=0
        )
    editor_request = EditorRequest(
        candidate_id=context.candidate_id,
        current_parent_skill=context.parent_skill,
        raw_patches=copy.deepcopy(tuple(update_signals)),
    )
    parsed_edits, reason = _parse_tagged_list(
        editor(editor_request), "CANONICAL_EDITS_JSON"
    )
    if reason is not None:
        return _no_candidate(
            reason,
            reflector_calls=upstream_calls,
            editor_calls=1,
            raw_patches=update_signals,
        )
    assert parsed_edits is not None
    if not parsed_edits:
        return _no_candidate(
            "EMPTY_EDITS",
            reflector_calls=upstream_calls,
            editor_calls=1,
            raw_patches=update_signals,
        )

    current = copy.deepcopy(original)
    touched_rule_ids: set[str] = set()
    raw_patch_ids = {patch["patch_id"] for patch in update_signals}
    raw_patches_by_id = {patch["patch_id"]: patch for patch in update_signals}
    consumed_patch_ids: set[str] = set()
    canonical_edits: list[Any] = []
    applied_records: list[dict[str, Any]] = []
    applied_raw: list[tuple[str, dict[str, Any]]] = []
    excluded_edits: list[dict[str, Any]] = []

    for index, value in enumerate(parsed_edits, start=1):
        edit_id = f"edit_{index:03d}"
        if not isinstance(value, dict):
            canonical_edits.append(copy.deepcopy(value))
            excluded_edits.append(
                {"edit_id": edit_id, "reason": "INVALID_EDIT_FORMAT"}
            )
            continue
        edit = copy.deepcopy(value)
        edit["edit_id"] = edit_id
        _merge_patch_provenance(edit, raw_patches_by_id)
        if not _lineage_is_valid(edit, raw_patch_ids, consumed_patch_ids):
            canonical_edits.append(edit)
            excluded_edits.append(
                {"edit_id": edit_id, "reason": "INVALID_EDIT_FORMAT"}
            )
            continue
        resolved, exclusion_reason = _resolve_edit_target(edit, original)
        if exclusion_reason is not None:
            canonical_edits.append(edit)
            excluded_edits.append(
                {"edit_id": edit_id, "reason": exclusion_reason}
            )
            continue
        assert resolved is not None
        canonical_edits.append(resolved)
        trial, exclusion_reason = _try_apply_edit(
            original, current, touched_rule_ids, resolved
        )
        if exclusion_reason is not None:
            excluded_edits.append(
                {"edit_id": edit_id, "reason": exclusion_reason}
            )
            continue
        assert trial is not None
        current = trial
        consumed_patch_ids.update(resolved["derived_from_patch_ids"])
        if resolved["operation"] != "add":
            touched_rule_ids.add(resolved["target_rule_id"])
        applied_records.append(_canonical_record(edit_id, resolved))
        applied_raw.append((edit_id, resolved))

    if not applied_records:
        return _no_candidate(
            "NO_APPLICABLE_EDITS",
            reflector_calls=upstream_calls,
            editor_calls=1,
            raw_patches=update_signals,
            canonical_edits=canonical_edits,
            excluded_edits=excluded_edits,
        )
    candidate_skill = _render_skill(current)
    if candidate_skill == _render_skill(original):
        return _no_candidate(
            "NO_SKILL_CHANGE",
            reflector_calls=upstream_calls,
            editor_calls=1,
            raw_patches=update_signals,
            canonical_edits=canonical_edits,
            excluded_edits=excluded_edits,
        )
    provenance_audit = _audit_provenance(applied_raw, allowed_policies)
    return ProposalDecision(
        proposal_status="CANDIDATE",
        proposal_reason={"code": "CANDIDATE_CONSTRUCTED"},
        reflector_calls=upstream_calls,
        editor_calls=1,
        raw_patches=copy.deepcopy(update_signals),
        canonical_edits=copy.deepcopy(canonical_edits),
        applied_edits=applied_records,
        excluded_edits=excluded_edits,
        candidate_skill=candidate_skill,
        provenance_status=provenance_audit["status"],
        provenance_audit=provenance_audit,
    )


def propose_from_update_signals(
    context: ProposalContext,
    update_signals: list[dict[str, Any]],
    editor: Editor,
    *,
    upstream_calls: int = 0,
) -> ProposalDecision:
    """Apply the shared v0.5 bounded Editor/Update path to prefiltered signals."""

    original, _, _, allowed_policies = _validate_context(context)
    return _edit_update_signals(
        context,
        original,
        allowed_policies,
        copy.deepcopy(update_signals),
        editor,
        upstream_calls=upstream_calls,
    )


class RuleIdGovernedReflectionEditorProposalOperator:
    """Construct a v0.5 Candidate using stable IDs within each Parent snapshot."""

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

        return _edit_update_signals(
            context,
            original,
            allowed_policies,
            raw_patches,
            editor,
            upstream_calls=reflector_calls,
        )
