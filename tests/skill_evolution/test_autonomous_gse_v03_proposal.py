from __future__ import annotations

import copy
import json

import pytest

from src.skill_evolution.autonomous_gse_v03_proposal import (
    EditorRequest,
    GovernedReflectionEditorProposalOperator,
    ProposalContext,
    ProposalContractError,
    ReflectorRequest,
)


S0_SKILL = """# SuiteCRM Operational Skill

## Planning and navigation

## Execution patterns

## Form entry and verification

## Error recovery and stopping
"""

PARENT_SKILL = """# SuiteCRM Operational Skill

## Planning and navigation

- Confirm the requested record.

## Execution patterns

- Open the target record directly.

## Form entry and verification

## Error recovery and stopping

- Stop when the target cannot be identified.
"""

EVIDENCE = (
    {
        "source_id": "source_cs",
        "task_success": True,
        "state": "compliant_success",
        "process_feedback": {"violated_policies": []},
    },
    {
        "source_id": "source_vs",
        "task_success": True,
        "state": "violating_success",
        "process_feedback": {
            "violated_policies": [
                {"policy_template_id": "confirm_before_update"}
            ]
        },
    },
    {
        "source_id": "source_cf",
        "task_success": False,
        "state": "compliant_failure",
        "process_feedback": {"violated_policies": []},
    },
    {
        "source_id": "source_vf",
        "task_success": False,
        "state": "violating_failure",
        "process_feedback": {
            "violated_policies": [
                {"policy_template_id": "stop_after_repeated_error"}
            ]
        },
    },
)


def tagged(tag: str, value: object) -> str:
    return f"<{tag}>{json.dumps(value)}</{tag}>"


def raw_response(patches: object) -> str:
    return tagged("RAW_PATCHES_JSON", patches)


def editor_response(edits: object) -> str:
    return tagged("CANONICAL_EDITS_JSON", edits)


def patch(
    text: str,
    *,
    operation: str = "add",
    section: str = "Execution patterns",
    target_clause: str = "",
    source_ids: list[str] | None = None,
    repair_policy_ids: list[str] | None = None,
) -> dict:
    return {
        "operation": operation,
        "section": section,
        "target_clause": target_clause,
        "text": text,
        "reason": "Current-batch evidence supports this proposed edit.",
        "source_ids": source_ids or ["source_cs"],
        "repair_policy_ids": repair_policy_ids or [],
    }


def canonical(
    patch_ids: list[str],
    text: str,
    *,
    operation: str = "add",
    section: str = "Execution patterns",
    target_clause: str = "",
    source_ids: list[str] | None = None,
    repair_policy_ids: list[str] | None = None,
) -> dict:
    return {
        "derived_from_patch_ids": patch_ids,
        "operation": operation,
        "section": section,
        "target_clause": target_clause,
        "text": text,
        "reason": "The Editor canonicalized current-batch raw patches.",
        "source_ids": source_ids or ["source_cs"],
        "repair_policy_ids": repair_policy_ids or [],
    }


def context(
    evidence: tuple[dict, ...] = EVIDENCE,
    parent_skill: str = S0_SKILL,
) -> ProposalContext:
    return ProposalContext(
        candidate_id="epoch_001_step_001_candidate",
        parent_skill=parent_skill,
        current_batch_governed_evidence=copy.deepcopy(evidence),
    )


def test_routes_four_states_and_only_canonical_edits_reach_update() -> None:
    current = context()
    original = copy.deepcopy(current.current_batch_governed_evidence)
    reflector_requests: list[ReflectorRequest] = []
    editor_requests: list[EditorRequest] = []

    def success_reflector(request: ReflectorRequest) -> str:
        reflector_requests.append(request)
        return raw_response([patch("Raw success wording.")])

    def failure_reflector(request: ReflectorRequest) -> str:
        reflector_requests.append(request)
        return raw_response(
            [patch("Raw failure wording.", source_ids=["source_cf"])]
        )

    def editor(request: EditorRequest) -> str:
        editor_requests.append(request)
        return editor_response(
            [
                canonical(
                    ["success_patch_001", "failure_patch_001"],
                    "Canonical workflow wording.",
                    source_ids=["source_cs", "source_cf"],
                )
            ]
        )

    decision = GovernedReflectionEditorProposalOperator().propose(
        current,
        success_reflector,
        failure_reflector,
        editor,
    )

    assert decision.proposal_status == "CANDIDATE"
    assert decision.reflector_calls == 2
    assert decision.editor_calls == 1
    assert [request.reflector for request in reflector_requests] == [
        "success",
        "failure",
    ]
    assert [item["state"] for item in reflector_requests[0].current_batch_evidence] == [
        "compliant_success",
        "violating_success",
    ]
    assert [item["state"] for item in reflector_requests[1].current_batch_evidence] == [
        "compliant_failure",
        "violating_failure",
    ]
    assert len(editor_requests) == 1
    assert set(editor_requests[0].__dict__) == {
        "candidate_id",
        "current_parent_skill",
        "raw_patches",
    }
    assert [item["patch_id"] for item in editor_requests[0].raw_patches] == [
        "success_patch_001",
        "failure_patch_001",
    ]
    assert "Canonical workflow wording." in decision.candidate_skill
    assert "Raw success wording." not in decision.candidate_skill
    assert "Raw failure wording." not in decision.candidate_skill
    assert current.current_batch_governed_evidence == original


def test_each_reflector_keeps_at_most_four_patches_and_all_eight_can_apply() -> None:
    observed: list[EditorRequest] = []

    def success_reflector(_: ReflectorRequest) -> str:
        return raw_response([patch(f"Success raw {index}.") for index in range(1, 6)])

    def failure_reflector(_: ReflectorRequest) -> str:
        return raw_response(
            [
                patch(f"Failure raw {index}.", source_ids=["source_cf"])
                for index in range(1, 6)
            ]
        )

    def editor(request: EditorRequest) -> str:
        observed.append(request)
        return editor_response(
            [
                canonical(
                    [raw["patch_id"]],
                    f"Canonical rule {index}.",
                    source_ids=raw["source_ids"],
                )
                for index, raw in enumerate(request.raw_patches, start=1)
            ]
        )

    decision = GovernedReflectionEditorProposalOperator().propose(
        context(),
        success_reflector,
        failure_reflector,
        editor,
    )

    assert len(observed[0].raw_patches) == 8
    assert [item["patch_id"] for item in observed[0].raw_patches] == [
        "success_patch_001",
        "success_patch_002",
        "success_patch_003",
        "success_patch_004",
        "failure_patch_001",
        "failure_patch_002",
        "failure_patch_003",
        "failure_patch_004",
    ]
    assert len(decision.canonical_edits) == 8
    assert len(decision.applied_edits) == 8
    assert "Canonical rule 8." in decision.candidate_skill


def test_empty_outcome_pool_skips_its_reflector() -> None:
    success_only = tuple(item for item in EVIDENCE if item["task_success"])
    failure_called = False

    def failure_reflector(_: ReflectorRequest) -> str:
        nonlocal failure_called
        failure_called = True
        return raw_response([])

    decision = GovernedReflectionEditorProposalOperator().propose(
        context(success_only),
        lambda _: raw_response([patch("Successful pattern.")]),
        failure_reflector,
        lambda _: editor_response(
            [canonical(["success_patch_001"], "Canonical successful pattern.")]
        ),
    )

    assert failure_called is False
    assert decision.reflector_calls == 1
    assert decision.proposal_status == "CANDIDATE"


def test_no_raw_patches_skips_editor() -> None:
    editor_called = False

    def editor(_: EditorRequest) -> str:
        nonlocal editor_called
        editor_called = True
        return editor_response([])

    decision = GovernedReflectionEditorProposalOperator().propose(
        context(),
        lambda _: raw_response([]),
        lambda _: raw_response([]),
        editor,
    )

    assert editor_called is False
    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.proposal_reason == {"code": "EMPTY_EDITS"}
    assert decision.reflector_calls == 2
    assert decision.editor_calls == 0


def test_invalid_canonical_edit_is_excluded_without_blocking_valid_edit() -> None:
    decision = GovernedReflectionEditorProposalOperator().propose(
        context(),
        lambda _: raw_response([patch("Raw one."), patch("Raw two.")]),
        lambda _: raw_response([]),
        lambda _: editor_response(
            [
                canonical(
                    ["success_patch_001"],
                    "Invalid operation.",
                    operation="move",
                ),
                canonical(
                    ["success_patch_002"],
                    "Valid canonical rule.",
                ),
            ]
        ),
    )

    assert decision.proposal_status == "CANDIDATE"
    assert len(decision.applied_edits) == 1
    assert decision.excluded_edits == [
        {"edit_id": "edit_001", "reason": "OPERATION_NOT_ALLOWED"}
    ]
    assert "Valid canonical rule." in decision.candidate_skill


def test_editor_cannot_split_one_raw_patch_into_multiple_edits() -> None:
    decision = GovernedReflectionEditorProposalOperator().propose(
        context(),
        lambda _: raw_response([patch("One raw patch.")]),
        lambda _: raw_response([]),
        lambda _: editor_response(
            [
                canonical(["success_patch_001"], "First canonical rule."),
                canonical(["success_patch_001"], "Split canonical rule."),
            ]
        ),
    )

    assert len(decision.applied_edits) == 1
    assert decision.excluded_edits == [
        {"edit_id": "edit_002", "reason": "INVALID_EDIT_FORMAT"}
    ]
    assert "First canonical rule." in decision.candidate_skill
    assert "Split canonical rule." not in decision.candidate_skill


def test_add_replace_and_delete_are_applied_from_canonical_edits() -> None:
    raw_patches = [
        patch("Raw add."),
        patch("Raw replace."),
        patch("Raw delete."),
    ]
    edits = [
        canonical(["success_patch_001"], "Verify the current record."),
        canonical(
            ["success_patch_002"],
            "Open the identified target record directly.",
            operation="replace",
            target_clause="Open the target record directly.",
        ),
        canonical(
            ["success_patch_003"],
            "",
            operation="delete",
            section="Error recovery and stopping",
            target_clause="Stop when the target cannot be identified.",
        ),
    ]

    decision = GovernedReflectionEditorProposalOperator().propose(
        context(parent_skill=PARENT_SKILL),
        lambda _: raw_response(raw_patches),
        lambda _: raw_response([]),
        lambda _: editor_response(edits),
    )

    assert [item["operation"] for item in decision.applied_edits] == [
        "add",
        "replace",
        "delete",
    ]
    assert "Verify the current record." in decision.candidate_skill
    assert "Open the identified target record directly." in decision.candidate_skill
    assert "Open the target record directly." not in decision.candidate_skill
    assert "Stop when the target cannot be identified." not in decision.candidate_skill


def test_missing_provenance_is_non_blocking() -> None:
    proposed = canonical(["success_patch_001"], "Rule without provenance.")
    proposed.pop("source_ids")
    proposed.pop("repair_policy_ids")

    decision = GovernedReflectionEditorProposalOperator().propose(
        context(),
        lambda _: raw_response([patch("Raw patch.")]),
        lambda _: raw_response([]),
        lambda _: editor_response([proposed]),
    )

    assert decision.proposal_status == "CANDIDATE"
    assert decision.provenance_status == "UNVERIFIED"
    assert decision.provenance_audit["issues"] == [
        {"code": "MISSING_PROVENANCE", "edit_id": "edit_001"}
    ]
    assert "Rule without provenance." in decision.candidate_skill


@pytest.mark.parametrize(
    ("reflector_output", "reason"),
    [
        ("not json", "UNPARSEABLE_RESPONSE"),
        (raw_response({"patches": []}), "EDITS_NOT_LIST"),
    ],
)
def test_invalid_reflector_response_is_no_candidate(
    reflector_output: str,
    reason: str,
) -> None:
    decision = GovernedReflectionEditorProposalOperator().propose(
        context(),
        lambda _: reflector_output,
        lambda _: raw_response([]),
        lambda _: editor_response([]),
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.proposal_reason == {"code": reason}
    assert decision.editor_calls == 0


@pytest.mark.parametrize(
    ("output", "reason"),
    [
        ("not json", "UNPARSEABLE_RESPONSE"),
        (editor_response({"edits": []}), "EDITS_NOT_LIST"),
        (editor_response([]), "EMPTY_EDITS"),
    ],
)
def test_invalid_or_empty_editor_response_is_no_candidate(
    output: str,
    reason: str,
) -> None:
    decision = GovernedReflectionEditorProposalOperator().propose(
        context(),
        lambda _: raw_response([patch("Raw patch.")]),
        lambda _: raw_response([]),
        lambda _: output,
    )

    assert decision.proposal_status == "NO_CANDIDATE"
    assert decision.proposal_reason == {"code": reason}
    assert decision.editor_calls == 1


def test_selection_or_test_data_is_rejected_at_context_boundary() -> None:
    tainted = copy.deepcopy(EVIDENCE)
    tainted[0]["selection_data"] = {"score": 1}

    with pytest.raises(ProposalContractError):
        GovernedReflectionEditorProposalOperator().propose(
            context(tainted),
            lambda _: raw_response([]),
            lambda _: raw_response([]),
            lambda _: editor_response([]),
        )


def test_same_input_and_fake_outputs_are_deterministic() -> None:
    operator = GovernedReflectionEditorProposalOperator()

    def run():
        return operator.propose(
            context(),
            lambda _: raw_response([patch("Raw patch.")]),
            lambda _: raw_response([]),
            lambda _: editor_response(
                [canonical(["success_patch_001"], "Canonical rule.")]
            ),
        )

    assert run() == run()
