"""State-reducer tests for the Autonomous GSE v0.3 Controller."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.skill_evolution.autonomous_gse_v03_controller import (
    ControllerContractError,
    InvalidTransitionError,
    reduce_step,
    register_step,
)
from src.skill_evolution.autonomous_gse_v03_proposal import (
    GovernedReflectionEditorProposalOperator,
    ProposalContext,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v03/campaign_manifest.json"
)
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)
STEP_SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v03_step.schema.json"
S0_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v03/skills/S0_empty_skill.md"
)

EVIDENCE = (
    {
        "source_id": "source_success",
        "task_success": True,
        "state": "compliant_success",
        "process_feedback": {"violated_policies": []},
    },
    {
        "source_id": "source_failure",
        "task_success": False,
        "state": "compliant_failure",
        "process_feedback": {"violated_policies": []},
    },
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ready_campaign() -> dict:
    campaign = load_json(CAMPAIGN_PATH)
    campaign["status"] = "ready"
    return campaign


def artifact(kind: str, version: str, name: str) -> dict[str, str]:
    return {
        "kind": kind,
        "version": version,
        "path": f"artifacts/{name}",
    }


def tagged(tag: str, value: object) -> str:
    return f"<{tag}>{json.dumps(value)}</{tag}>"


def raw_patch(text: str, source_id: str) -> dict:
    return {
        "operation": "add",
        "section": "Execution patterns",
        "target_clause": "",
        "text": text,
        "reason": "Current-batch evidence supports this edit.",
        "source_ids": [source_id],
        "repair_policy_ids": [],
    }


def canonical_edit(patch_id: str, text: str, source_id: str) -> dict:
    return {
        "derived_from_patch_ids": [patch_id],
        "operation": "add",
        "section": "Execution patterns",
        "target_clause": "",
        "text": text,
        "reason": "The Editor canonicalized the raw patch.",
        "source_ids": [source_id],
        "repair_policy_ids": [],
    }


def registered_step(
    step: int = 1,
    *,
    parent: dict | None = None,
) -> dict:
    campaign = ready_campaign()
    current_parent = parent or campaign["initial_parent"]
    checkpoint = artifact(
        "selection_checkpoint",
        current_parent["version"],
        f"{current_parent['version'].lower()}_selection.json",
    )
    return register_step(
        campaign,
        load_json(BATCH_MAP_PATH),
        step=step,
        parent=current_parent,
        parent_checkpoint=checkpoint,
    )


def advance_to_proposal(step: dict) -> dict:
    for event_type in (
        "TRAIN_STARTED",
        "TRAIN_COMPLETED",
        "TRAIN_VALIDATED",
        "EXPERIENCE_FROZEN",
        "PROPOSAL_STARTED",
    ):
        step = reduce_step(step, {"type": event_type}).step
    return step


def proposal_decision(
    *,
    source_id: str = "source_success",
    patches_per_reflector: int = 1,
):
    success_patches = [
        raw_patch(f"Success workflow {index}.", "source_success")
        for index in range(1, patches_per_reflector + 1)
    ]
    failure_patches = [
        raw_patch(f"Failure recovery {index}.", "source_failure")
        for index in range(1, patches_per_reflector + 1)
    ]

    def editor(request) -> str:
        edits = [
            canonical_edit(
                patch["patch_id"],
                f"Canonical workflow {index}.",
                source_id,
            )
            for index, patch in enumerate(request.raw_patches, start=1)
        ]
        return tagged("CANONICAL_EDITS_JSON", edits)

    return GovernedReflectionEditorProposalOperator().propose(
        ProposalContext(
            candidate_id="epoch_001_step_001_candidate",
            parent_skill=S0_PATH.read_text(encoding="utf-8"),
            current_batch_governed_evidence=copy.deepcopy(EVIDENCE),
        ),
        lambda _: tagged("RAW_PATCHES_JSON", success_patches),
        lambda _: tagged("RAW_PATCHES_JSON", failure_patches),
        editor,
    )


def candidate_event(
    step: dict,
    *,
    verified: bool = True,
    patches_per_reflector: int = 1,
) -> dict:
    decision = proposal_decision(
        source_id="source_success" if verified else "unknown_source",
        patches_per_reflector=patches_per_reflector,
    )
    return {
        "type": "CANDIDATE_FROZEN",
        "candidate": artifact(
            "candidate_skill", step["candidate_id"], "candidate_skill.md"
        ),
        "proposal_reason": decision.proposal_reason,
        "raw_patches": decision.raw_patches,
        "canonical_edits": decision.canonical_edits,
        "applied_edits": decision.applied_edits,
        "excluded_edits": decision.excluded_edits,
        "provenance_status": decision.provenance_status,
        "provenance_audit": decision.provenance_audit,
    }


def advance_candidate_to_gate(step: dict, *, verified: bool = True) -> dict:
    step = reduce_step(step, candidate_event(step, verified=verified)).step
    for event_type in (
        "CANDIDATE_SELECTION_STARTED",
        "SELECTION_VALIDATED",
        "EVOLUTION_SUMMARY_FROZEN",
        "GATE_DECIDED",
    ):
        step = reduce_step(step, {"type": event_type}).step
    return step


def validate_step(step: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json(STEP_SCHEMA_PATH)
    jsonschema.Draft202012Validator(schema).validate(step)


def test_register_step_uses_v03_reflection_editor_contract() -> None:
    step = registered_step()

    assert step["batch"]["batch_id"] == "batch_001"
    assert len(step["batch"]["task_ids"]) == 17
    assert step["batch"]["batch_map"] == (
        "experiments/campaigns/autonomous_gse_v02/batch_map.json"
    )
    assert step["proposal_operator"] == "governed_reflection_editor"
    assert step["proposal_budget"] == {
        "maximum_raw_patches_per_reflector": 4,
        "maximum_reflector_calls": 2,
        "maximum_editor_calls": 1,
        "additional_minibatching": False,
        "maximum_skill_rules": 18,
        "maximum_skill_words": 900,
        "allowed_operations": ["add", "replace", "delete"],
    }
    assert step["data_isolation"]["eligible_evidence_states"] == [
        "compliant_success",
        "violating_success",
        "compliant_failure",
        "violating_failure",
    ]
    validate_step(step)


def test_all_batches_are_unique_and_reuse_v02_assignment() -> None:
    campaign = ready_campaign()
    batch_map = load_json(BATCH_MAP_PATH)
    task_ids: list[int] = []

    for step_number in range(1, 4):
        step = register_step(
            campaign,
            batch_map,
            step=step_number,
            parent=campaign["initial_parent"],
            parent_checkpoint=artifact(
                "selection_checkpoint", "S0", f"s0_{step_number}.json"
            ),
        )
        task_ids.extend(step["batch"]["task_ids"])

    assert len(task_ids) == len(set(task_ids)) == 51


def test_same_operator_is_used_for_accepted_parent() -> None:
    parent = artifact("accepted_skill", "S1", "accepted_s1.md")

    step = registered_step(2, parent=parent)

    assert step["parent"] == parent
    assert step["proposal_operator"] == "governed_reflection_editor"
    validate_step(step)


def test_candidate_preserves_all_edit_histories_and_has_no_six_edit_cap() -> None:
    step = advance_to_proposal(registered_step())
    event = candidate_event(step, patches_per_reflector=4)

    result = reduce_step(step, event)

    assert result.action == "RUN_CANDIDATE_SELECTION"
    assert len(result.step["raw_patches"]) == 8
    assert len(result.step["canonical_edits"]) == 8
    assert len(result.step["applied_edits"]) == 8
    assert result.step["excluded_edits"] == []
    validate_step(result.step)


def test_unverified_candidate_runs_selection_and_can_be_accepted() -> None:
    proposal_step = advance_to_proposal(registered_step())
    candidate_result = reduce_step(
        proposal_step,
        candidate_event(proposal_step, verified=False),
    )

    assert candidate_result.step["provenance_status"] == "UNVERIFIED"
    assert candidate_result.action == "RUN_CANDIDATE_SELECTION"

    gate_step = advance_candidate_to_gate(proposal_step, verified=False)
    checkpoint = artifact("selection_checkpoint", "S1", "s1_selection.json")
    result = reduce_step(
        gate_step,
        {
            "type": "STEP_COMPLETED",
            "outcome": "ACCEPT",
            "candidate_checkpoint": checkpoint,
        },
    )

    assert result.step["outcome"] == "ACCEPT"
    assert result.step["provenance_status"] == "UNVERIFIED"
    assert result.accepted_parent == {
        "kind": "accepted_skill",
        "version": "S1",
        "path": "artifacts/candidate_skill.md",
    }
    assert result.accepted_parent_checkpoint == checkpoint
    validate_step(result.step)

    next_step = register_step(
        ready_campaign(),
        load_json(BATCH_MAP_PATH),
        step=2,
        parent=result.accepted_parent,
        parent_checkpoint=result.accepted_parent_checkpoint,
    )
    assert next_step["parent"]["version"] == "S1"


def test_reject_and_no_candidate_keep_parent_and_checkpoint() -> None:
    initial = registered_step()
    rejected = reduce_step(
        advance_candidate_to_gate(advance_to_proposal(initial)),
        {"type": "STEP_COMPLETED", "outcome": "REJECT"},
    )
    proposal_step = advance_to_proposal(registered_step())
    no_candidate = reduce_step(
        proposal_step,
        {
            "type": "NO_CANDIDATE",
            "proposal_reason": {"code": "NO_APPLICABLE_EDITS"},
            "raw_patches": [
                {
                    "patch_id": "success_patch_001",
                    "reflector": "success",
                    **raw_patch("Unsupported raw patch.", "source_success"),
                }
            ],
            "canonical_edits": [],
            "applied_edits": [],
            "excluded_edits": [
                {"edit_id": "edit_001", "reason": "OPERATION_NOT_ALLOWED"}
            ],
        },
    )

    assert rejected.accepted_parent == initial["parent"]
    assert no_candidate.accepted_parent == initial["parent"]
    assert no_candidate.step["outcome"] == "NO_CANDIDATE"
    assert no_candidate.step["raw_patches"][0]["patch_id"] == (
        "success_patch_001"
    )
    assert no_candidate.action == "REGISTER_NEXT_STEP"
    validate_step(rejected.step)
    validate_step(no_candidate.step)


def test_more_than_four_raw_patches_from_one_reflector_is_rejected() -> None:
    step = advance_to_proposal(registered_step())
    event = candidate_event(step)
    first = event["raw_patches"][0]
    event["raw_patches"] = [
        {**copy.deepcopy(first), "patch_id": f"success_patch_{index:03d}"}
        for index in range(1, 6)
    ]

    with pytest.raises(ControllerContractError, match="raw patch budget"):
        reduce_step(step, event)


def test_draft_or_changed_governance_contract_is_rejected() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    checkpoint = artifact("selection_checkpoint", "S0", "s0.json")

    campaign["status"] = "draft"
    with pytest.raises(ControllerContractError, match="ready"):
        register_step(
            campaign,
            load_json(BATCH_MAP_PATH),
            step=1,
            parent=campaign["initial_parent"],
            parent_checkpoint=checkpoint,
        )

    campaign["status"] = "ready"
    campaign["proposal"]["editor"]["ranking"] = True
    with pytest.raises(ControllerContractError, match="Editor contract"):
        register_step(
            campaign,
            load_json(BATCH_MAP_PATH),
            step=1,
            parent=campaign["initial_parent"],
            parent_checkpoint=checkpoint,
        )


def test_reducer_is_pure_and_rejects_wrong_order() -> None:
    step = registered_step()
    original = copy.deepcopy(step)

    result = reduce_step(step, {"type": "TRAIN_STARTED"})

    assert step == original
    assert result.step["status"] == "TRAIN_RUNNING"
    with pytest.raises(InvalidTransitionError):
        reduce_step(step, {"type": "TRAIN_COMPLETED"})


def test_integrity_failure_halts_without_candidate_or_edit_history() -> None:
    result = reduce_step(registered_step(), {"type": "INTEGRITY_FAILURE"})

    assert result.step["status"] == "STEP_INVALID"
    assert result.step["outcome"] == "INTEGRITY_FAILURE"
    assert result.action == "HALT_CAMPAIGN"
    assert "raw_patches" not in result.step
    assert "candidate" not in result.step
    validate_step(result.step)
