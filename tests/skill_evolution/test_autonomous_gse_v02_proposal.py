"""Pure-logic tests for the Autonomous GSE v0.2 proposal operator."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.skill_evolution.autonomous_gse_v02_proposal import (
    BoundedEditProposalOperator,
    LearnerRequest,
    ProposalContext,
    ProposalContractError,
)


S0_SKILL = """# SuiteCRM Operational Skill

## Planning and navigation

## Execution patterns

## Form entry and verification

## Error recovery and stopping
"""

PARENT_SKILL = """# SuiteCRM Operational Skill

## Planning and navigation

- Inspect the current record before planning a change.

## Execution patterns

- Open the target record directly.

## Form entry and verification

- Verify saved values after submitting the form.

## Error recovery and stopping

- Stop when the requested record cannot be identified.
"""

EVIDENCE = (
    {
        "source_id": "source_001",
        "task_success": True,
        "state": "compliant_success",
        "process_feedback": {"violated_policies": []},
    },
    {
        "source_id": "source_002",
        "task_success": True,
        "state": "violating_success",
        "process_feedback": {
            "violated_policies": [
                {"policy_template_id": "confirm_before_update"}
            ]
        },
    },
)
STEP_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schemas/autonomous_gse_v02_step.schema.json"
)


def response(edits: object) -> str:
    return f"<EDITS_JSON>{json.dumps(edits)}</EDITS_JSON>"


def edit(
    operation: str = "add",
    *,
    section: str = "Planning and navigation",
    target_clause: str = "",
    text: str = "Ask for missing details before acting.",
    source_ids: object = ("source_001",),
    repair_policy_ids: object = (),
) -> dict:
    return {
        "operation": operation,
        "section": section,
        "target_clause": target_clause,
        "text": text,
        "reason": "Use successful current-batch evidence.",
        "source_ids": list(source_ids) if isinstance(source_ids, tuple) else source_ids,
        "repair_policy_ids": (
            list(repair_policy_ids)
            if isinstance(repair_policy_ids, tuple)
            else repair_policy_ids
        ),
    }


def context(parent_skill: str = S0_SKILL) -> ProposalContext:
    return ProposalContext(
        candidate_id="epoch_001_step_001_candidate",
        parent_skill=parent_skill,
        current_batch_success_evidence=copy.deepcopy(EVIDENCE),
    )


def test_empty_s0_add_builds_verified_candidate_without_mutating_input() -> None:
    current = context()
    original = copy.deepcopy(current.current_batch_success_evidence)
    observed: list[LearnerRequest] = []

    def learner(request: LearnerRequest) -> str:
        observed.append(request)
        return response([edit()])

    decision = BoundedEditProposalOperator().propose(current, learner)

    assert decision.proposal_status == "CANDIDATE"
    assert decision.proposal_reason == {"code": "CANDIDATE_CONSTRUCTED"}
    assert decision.learner_calls == 1
    assert len(decision.selected_edits) == 1
    assert decision.excluded_edits == []
    assert "- Ask for missing details before acting." in decision.candidate_skill
    assert decision.provenance_status == "VERIFIED"
    assert decision.provenance_audit == {
        "status": "VERIFIED",
        "verified_edits": 1,
        "unverified_edits": 0,
        "issues": [],
    }
    assert current.current_batch_success_evidence == original
    assert observed[0].maximum_edits == 6
    assert observed[0].allowed_source_ids == ("source_001", "source_002")
    assert observed[0].allowed_repair_policy_ids_by_source == {
        "source_001": (),
        "source_002": ("confirm_before_update",),
    }
    assert set(observed[0].__dict__) == {
        "candidate_id",
        "current_parent_skill",
        "current_batch_success_evidence",
        "maximum_edits",
        "allowed_source_ids",
        "allowed_repair_policy_ids_by_source",
    }


def test_same_operator_applies_add_replace_and_delete_to_parent() -> None:
    edits = [
        edit(text="Confirm the intended record before navigating."),
        edit(
            "replace",
            section="Execution patterns",
            target_clause="Open the target record directly.",
            text="Open the identified target record directly.",
        ),
        edit(
            "delete",
            section="Error recovery and stopping",
            target_clause="Stop when the requested record cannot be identified.",
            text="",
        ),
    ]

    decision = BoundedEditProposalOperator().propose(
        context(PARENT_SKILL), lambda _: response(edits)
    )

    assert decision.proposal_status == "CANDIDATE"
    assert [item["operation"] for item in decision.selected_edits] == [
        "add",
        "replace",
        "delete",
    ]
    assert "Open the identified target record directly." in decision.candidate_skill
    assert "Open the target record directly." not in decision.candidate_skill
    assert "Stop when the requested record cannot be identified." not in (
        decision.candidate_skill
    )


def test_s0_excludes_replace_and_delete_but_keeps_valid_add() -> None:
    edits = [
        edit(
            "replace",
            target_clause="A missing S0 clause.",
            text="Replacement.",
        ),
        edit(
            "delete",
            target_clause="Another missing S0 clause.",
            text="",
        ),
        edit(text="Use the visible record title to confirm context."),
    ]

    decision = BoundedEditProposalOperator().propose(
        context(), lambda _: response(edits)
    )

    assert decision.proposal_status == "CANDIDATE"
    assert [item["edit_index"] for item in decision.selected_edits] == [3]
    assert [item["reason"] for item in decision.excluded_edits] == [
        "TARGET_CLAUSE_NOT_FOUND",
        "TARGET_CLAUSE_NOT_FOUND",
    ]


def test_selects_first_six_applicable_edits_in_response_order() -> None:
    edits = [
        edit(operation="move"),
        *[
            edit(text=f"Reusable rule {index}.")
            for index in range(1, 8)
        ],
    ]

    decision = BoundedEditProposalOperator().propose(
        context(), lambda _: response(edits)
    )

    assert [item["edit_index"] for item in decision.selected_edits] == [
        2,
        3,
        4,
        5,
        6,
        7,
    ]
    assert decision.excluded_edits[0]["reason"] == "OPERATION_NOT_ALLOWED"
    assert decision.excluded_edits[1]["edit_index"] == 8
    assert decision.excluded_edits[1]["reason"] == "EDIT_BUDGET_EXCEEDED"


def test_provenance_errors_are_unverified_diagnostics_not_rejections() -> None:
    unsupported = edit(
        source_ids=("unknown_source",),
        repair_policy_ids=("unsupported_policy",),
    )

    decision = BoundedEditProposalOperator().propose(
        context(), lambda _: response([unsupported])
    )

    assert decision.proposal_status == "CANDIDATE"
    assert len(decision.selected_edits) == 1
    assert decision.provenance_status == "UNVERIFIED"
    assert decision.provenance_audit["unverified_edits"] == 1
    assert {issue["code"] for issue in decision.provenance_audit["issues"]} == {
        "UNKNOWN_SOURCE_ID",
        "UNSUPPORTED_REPAIR_POLICY",
    }
    assert "Ask for missing details before acting." in decision.candidate_skill


def test_missing_provenance_still_constructs_unverified_candidate() -> None:
    proposed = edit()
    proposed.pop("source_ids")
    proposed.pop("repair_policy_ids")

    decision = BoundedEditProposalOperator().propose(
        context(), lambda _: response([proposed])
    )

    assert decision.proposal_status == "CANDIDATE"
    assert decision.provenance_status == "UNVERIFIED"
    assert [issue["code"] for issue in decision.provenance_audit["issues"]] == [
        "MISSING_PROVENANCE"
    ]


@pytest.mark.parametrize(
    ("learner_output", "reason"),
    [
        ("not json", "UNPARSEABLE_RESPONSE"),
        (response({"edits": []}), "EDITS_NOT_LIST"),
        (response([]), "EMPTY_EDITS"),
    ],
)
def test_malformed_or_empty_response_is_no_candidate(
    learner_output: str,
    reason: str,
) -> None:
    decision = BoundedEditProposalOperator().propose(
        context(), lambda _: learner_output
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.proposal_reason == {"code": reason}
    assert decision.candidate_skill is None
    assert decision.selected_edits == []


def test_all_inapplicable_edits_is_no_candidate_with_history() -> None:
    decision = BoundedEditProposalOperator().propose(
        context(),
        lambda _: response(
            [
                edit(operation="move"),
                edit(
                    "replace",
                    target_clause="Missing clause.",
                    text="Replacement.",
                ),
            ]
        ),
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.proposal_reason == {"code": "NO_APPLICABLE_EDITS"}
    assert len(decision.proposed_edits) == 2
    assert len(decision.excluded_edits) == 2


def test_no_success_evidence_skips_learner() -> None:
    called = False

    def learner(_: LearnerRequest) -> str:
        nonlocal called
        called = True
        return response([edit()])

    current = ProposalContext(
        candidate_id="epoch_001_step_001_candidate",
        parent_skill=S0_SKILL,
        current_batch_success_evidence=(),
    )
    decision = BoundedEditProposalOperator().propose(current, learner)

    assert called is False
    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.proposal_reason == {
        "code": "NO_APPLICABLE_EDITS",
        "detail": "No eligible current-batch success evidence.",
    }
    assert decision.learner_calls == 0


def test_selection_or_test_data_is_rejected_at_context_boundary() -> None:
    tainted = copy.deepcopy(EVIDENCE)
    tainted[0]["selection_data"] = {"score": 1}
    current = ProposalContext(
        candidate_id="epoch_001_step_001_candidate",
        parent_skill=S0_SKILL,
        current_batch_success_evidence=tainted,
    )

    with pytest.raises(ProposalContractError):
        BoundedEditProposalOperator().propose(
            current, lambda _: response([edit()])
        )


def test_same_input_is_deterministic() -> None:
    current = context(PARENT_SKILL)
    edits = [
        edit(
            "replace",
            section="Execution patterns",
            target_clause="Open the target record directly.",
            text="Open the identified target record directly.",
            source_ids=("source_002",),
            repair_policy_ids=("confirm_before_update",),
        )
    ]
    operator = BoundedEditProposalOperator()

    first = operator.propose(current, lambda _: response(edits))
    second = operator.propose(current, lambda _: response(edits))

    assert first == second


def test_decision_records_match_v02_step_schema_definitions() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(STEP_SCHEMA_PATH.read_text(encoding="utf-8"))
    decision = BoundedEditProposalOperator().propose(
        context(),
        lambda _: response([edit(), edit(operation="move")]),
    )

    jsonschema.Draft202012Validator(schema["$defs"]["proposal_reason"]).validate(
        decision.proposal_reason
    )
    selected_validator = jsonschema.Draft202012Validator(
        schema["$defs"]["selected_edit"]
    )
    for selected in decision.selected_edits:
        selected_validator.validate(selected)
    excluded_validator = jsonschema.Draft202012Validator(
        schema["$defs"]["excluded_edit"]
    )
    for excluded in decision.excluded_edits:
        excluded_validator.validate(excluded)
    jsonschema.Draft202012Validator(schema["$defs"]["provenance_audit"]).validate(
        decision.provenance_audit
    )
