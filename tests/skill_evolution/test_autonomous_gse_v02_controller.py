"""State-reducer tests for the Autonomous GSE v0.2 Controller."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.skill_evolution.autonomous_gse_v02_controller import (
    ControllerContractError,
    InvalidTransitionError,
    reduce_step,
    register_step,
)
from src.skill_evolution.autonomous_gse_v02_proposal import (
    BoundedEditProposalOperator,
    ProposalContext,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v02/campaign_manifest.json"
)
V01_BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v01/batch_map.json"
)
V02_BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v02/batch_map.json"
)
STEP_SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v02_step.schema.json"
S0_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v02/skills/S0_empty_skill.md"
)

EVIDENCE = (
    {
        "source_id": "source_001",
        "task_success": True,
        "state": "compliant_success",
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
        load_json(V02_BATCH_MAP_PATH),
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


def candidate_event(step: dict, *, verified: bool) -> dict:
    edit = {
        "operation": "add",
        "section": "Planning and navigation",
        "target_clause": "",
        "text": "Ask for missing details before acting.",
        "reason": "Use current-batch success evidence.",
        "source_ids": ["source_001" if verified else "unknown_source"],
        "repair_policy_ids": [],
    }
    response = f"<EDITS_JSON>{json.dumps([edit])}</EDITS_JSON>"
    decision = BoundedEditProposalOperator().propose(
        ProposalContext(
            candidate_id=step["candidate_id"],
            parent_skill=S0_PATH.read_text(encoding="utf-8"),
            current_batch_success_evidence=copy.deepcopy(EVIDENCE),
        ),
        lambda _: response,
    )
    return {
        "type": "CANDIDATE_FROZEN",
        "candidate": artifact(
            "candidate_skill", step["candidate_id"], "candidate_skill.md"
        ),
        "proposal_reason": decision.proposal_reason,
        "proposed_edits": decision.proposed_edits,
        "selected_edits": decision.selected_edits,
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
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(step)


def test_v02_batch_map_reuses_exact_v01_assignments() -> None:
    v01 = load_json(V01_BATCH_MAP_PATH)
    v02 = load_json(V02_BATCH_MAP_PATH)

    assert v02["batches"] == v01["batches"]
    assert v02["campaign_id"] == "autonomous_gse_v02"
    assert v02["schema_version"] == "autonomous_gse_batch_map_0.2.0"
    assert v02["status"] == "ready"
    assert set(v02) == {
        "batches",
        "campaign_id",
        "schema_version",
        "source",
        "status",
    }


def test_register_step_uses_bounded_edit_and_v02_contract() -> None:
    step = registered_step()

    assert step["batch"]["batch_id"] == "batch_001"
    assert len(step["batch"]["task_ids"]) == 17
    assert step["proposal_operator"] == "bounded_edit"
    assert step["edit_budget"]["maximum_edits_per_step"] == 6
    assert step["parent"]["kind"] == "empty_skill"
    validate_step(step)


def test_all_batches_are_unique_and_template_balanced() -> None:
    task_ids: list[int] = []
    batch_map = load_json(V02_BATCH_MAP_PATH)
    campaign = ready_campaign()
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

    assert step["proposal_operator"] == "bounded_edit"
    assert step["parent"] == parent
    validate_step(step)


def test_unverified_candidate_still_runs_selection_and_can_be_accepted() -> None:
    step = advance_to_proposal(registered_step())
    candidate_result = reduce_step(
        step,
        candidate_event(step, verified=False),
    )

    assert candidate_result.step["provenance_status"] == "UNVERIFIED"
    assert candidate_result.action == "RUN_CANDIDATE_SELECTION"

    gate_step = advance_candidate_to_gate(step, verified=False)
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
        load_json(V02_BATCH_MAP_PATH),
        step=2,
        parent=result.accepted_parent,
        parent_checkpoint=result.accepted_parent_checkpoint,
    )
    assert next_step["parent"]["version"] == "S1"
    assert next_step["proposal_operator"] == "bounded_edit"


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
            "proposed_edits": [{"operation": "move"}],
            "selected_edits": [],
            "excluded_edits": [
                {
                    "edit_index": 1,
                    "status": "EXCLUDED",
                    "reason": "OPERATION_NOT_ALLOWED",
                    "original_edit": {"operation": "move"},
                }
            ],
        },
    )

    assert rejected.accepted_parent == initial["parent"]
    assert no_candidate.accepted_parent == initial["parent"]
    assert no_candidate.step["outcome"] == "NO_CANDIDATE"
    assert no_candidate.action == "REGISTER_NEXT_STEP"
    validate_step(rejected.step)
    validate_step(no_candidate.step)


def test_invalid_proposal_is_not_a_v02_transition() -> None:
    step = advance_to_proposal(registered_step())

    with pytest.raises(InvalidTransitionError):
        reduce_step(step, {"type": "INVALID_PROPOSAL"})


def test_draft_campaign_and_changed_budget_are_rejected() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    batch_map = load_json(V02_BATCH_MAP_PATH)
    checkpoint = artifact("selection_checkpoint", "S0", "s0.json")

    with pytest.raises(ControllerContractError, match="ready"):
        register_step(
            campaign,
            batch_map,
            step=1,
            parent=campaign["initial_parent"],
            parent_checkpoint=checkpoint,
        )

    campaign["status"] = "ready"
    campaign["proposal"]["maximum_edits_per_step"] = 5
    with pytest.raises(ControllerContractError, match="Proposal contract"):
        register_step(
            campaign,
            batch_map,
            step=1,
            parent=campaign["initial_parent"],
            parent_checkpoint=checkpoint,
        )


def test_semantically_changed_batch_map_is_rejected() -> None:
    batch_map = load_json(V02_BATCH_MAP_PATH)
    batch_map["batches"][1]["assignments"][0]["task_id"] = (
        batch_map["batches"][0]["assignments"][0]["task_id"]
    )

    with pytest.raises(ControllerContractError, match="51 unique"):
        register_step(
            ready_campaign(),
            batch_map,
            step=1,
            parent=ready_campaign()["initial_parent"],
            parent_checkpoint=artifact("selection_checkpoint", "S0", "s0.json"),
        )


def test_reducer_is_pure_and_rejects_wrong_order() -> None:
    step = registered_step()
    original = copy.deepcopy(step)

    result = reduce_step(step, {"type": "TRAIN_STARTED"})

    assert step == original
    assert result.step["status"] == "TRAIN_RUNNING"
    with pytest.raises(InvalidTransitionError):
        reduce_step(step, {"type": "TRAIN_COMPLETED"})


def test_integrity_failure_halts_without_a_candidate() -> None:
    result = reduce_step(registered_step(), {"type": "INTEGRITY_FAILURE"})

    assert result.step["status"] == "STEP_INVALID"
    assert result.step["outcome"] == "INTEGRITY_FAILURE"
    assert result.action == "HALT_CAMPAIGN"
    validate_step(result.step)
