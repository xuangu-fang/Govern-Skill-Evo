"""Tests for the bounded S1 -> Candidate S2 learner."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.learners.stwebagentbench.generate_governed_s2 import (
    MAX_EDITS,
    apply_edits,
    build_candidate_provenance,
    parse_edits,
    validate_edits,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PARENT_SKILL = (
    REPO_ROOT
    / "experiments/results/stweb_suitecrm_poc_v01/skills/"
    "governed_candidate_s1_skill.md"
).read_text(encoding="utf-8").strip()


def evidence(*, violating: bool = True) -> list[dict]:
    policy = {"policy_template_id": "ask_the_user"}
    return [
        {
            "source_id": "s1_train_task_049_trial_01",
            "task_success": True,
            "state": "violating_success" if violating else "compliant_success",
            "process_feedback": {
                "compliant": not violating,
                "violated_policies": [policy] if violating else [],
            },
        }
    ]


def replacement_edit() -> dict:
    return {
        "operation": "replace",
        "section": "Execution patterns",
        "parent_clause": (
            "Before a bulk update, explain how the target records will be "
            "identified and request confirmation for the bulk update."
        ),
        "new_clause": (
            "Before a bulk update, identify the target records, explain the "
            "planned change, and request confirmation before applying it."
        ),
        "attribution": "repair",
        "source_ids": ["s1_train_task_049_trial_01"],
        "policy_template_ids": ["ask_the_user"],
    }


def test_parses_exact_edit_block() -> None:
    assert parse_edits("<EDITS_JSON>[]</EDITS_JSON>") == []
    with pytest.raises(ValueError, match="exactly one"):
        parse_edits("comment\n<EDITS_JSON>[]</EDITS_JSON>")


def test_applies_one_bounded_replacement_to_parent_s1() -> None:
    edits = [replacement_edit()]
    validate_edits(edits, PARENT_SKILL, evidence())
    candidate = apply_edits(PARENT_SKILL, edits)

    assert replacement_edit()["new_clause"] in candidate
    assert replacement_edit()["parent_clause"] not in candidate
    assert candidate.startswith("# SuiteCRM Operational Skill")

    provenance = build_candidate_provenance(PARENT_SKILL, edits)
    modified = [
        rule
        for rule in provenance["rules"]
        if rule["origin"] == "modified_s2"
    ]
    assert len(modified) == 1
    assert modified[0]["source_ids"] == ["s1_train_task_049_trial_01"]


def test_rejects_more_than_four_edits() -> None:
    edits = [
        {
            **replacement_edit(),
            "operation": "add",
            "section": "Planning and navigation",
            "parent_clause": "",
            "new_clause": f"New supported rule {index}.",
            "attribution": "preserve",
            "policy_template_ids": [],
        }
        for index in range(MAX_EDITS + 1)
    ]
    with pytest.raises(ValueError, match="At most 4 edits"):
        validate_edits(edits, PARENT_SKILL, evidence())


def test_rejects_repair_without_violated_policy_support() -> None:
    with pytest.raises(ValueError, match="repair provenance"):
        validate_edits(
            [replacement_edit()],
            PARENT_SKILL,
            evidence(violating=False),
        )
