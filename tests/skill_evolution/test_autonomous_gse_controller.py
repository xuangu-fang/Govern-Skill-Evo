"""State-reducer tests for the simplified Autonomous GSE v0.1 contract."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.skill_evolution.autonomous_gse_controller import (
    ControllerIntegrityError,
    InvalidTransitionError,
    reduce_step,
    register_step,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_PATH = (
    PROJECT_ROOT
    / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
)
BATCH_MAP_PATH = (
    PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v01/batch_map.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact(kind: str, version: str, name: str) -> dict[str, str]:
    return {
        "kind": kind,
        "version": version,
        "path": f"artifacts/{name}",
    }


def registered_step(step: int = 1) -> dict:
    parent = load_json(CAMPAIGN_PATH)["initial_parent"]
    checkpoint = artifact("selection_checkpoint", "S0", "s0.json")
    return register_step(
        load_json(CAMPAIGN_PATH),
        load_json(BATCH_MAP_PATH),
        step=step,
        parent=parent,
        parent_checkpoint=checkpoint,
    )


def advance_to_proposal(step: dict) -> dict:
    for event in (
        "TRAIN_STARTED",
        "TRAIN_COMPLETED",
        "TRAIN_VALIDATED",
        "EXPERIENCE_FROZEN",
        "PROPOSAL_STARTED",
    ):
        step = reduce_step(step, {"type": event}).step
    return step


def advance_candidate_to_gate(step: dict) -> dict:
    candidate = artifact("candidate_skill", step["candidate_id"], "skill.md")
    step = reduce_step(
        step, {"type": "CANDIDATE_FROZEN", "candidate": candidate}
    ).step
    for event in (
        "CANDIDATE_SELECTION_STARTED",
        "SELECTION_VALIDATED",
        "EVOLUTION_SUMMARY_FROZEN",
        "GATE_DECIDED",
    ):
        step = reduce_step(step, {"type": event}).step
    return step


def test_register_step_uses_recorded_batch_paths_and_plain_artifacts() -> None:
    step = registered_step()

    assert step["batch"]["batch_id"] == "batch_001"
    assert len(step["batch"]["task_ids"]) == 17
    assert step["batch"]["batch_map_path"].endswith("batch_map.json")
    assert set(step["parent"]) == {"kind", "version", "path"}
    assert step["proposal_operator"] == "bootstrap"


def test_accept_promotes_candidate_and_checkpoint() -> None:
    step = advance_candidate_to_gate(advance_to_proposal(registered_step()))
    checkpoint = artifact("selection_checkpoint", "S1", "s1.json")

    result = reduce_step(
        step,
        {
            "type": "STEP_COMPLETED",
            "outcome": "ACCEPT",
            "candidate_checkpoint": checkpoint,
        },
    )

    assert result.step["outcome"] == "ACCEPT"
    assert result.accepted_parent == {
        "kind": "accepted_skill",
        "version": "S1",
        "path": "artifacts/skill.md",
    }
    assert result.accepted_parent_checkpoint == checkpoint


def test_reject_and_no_candidate_keep_current_parent() -> None:
    parent = registered_step()["parent"]
    rejected = reduce_step(
        advance_candidate_to_gate(advance_to_proposal(registered_step())),
        {"type": "STEP_COMPLETED", "outcome": "REJECT"},
    )
    no_candidate = reduce_step(
        advance_to_proposal(registered_step()), {"type": "NO_CANDIDATE"}
    )

    assert rejected.accepted_parent == parent
    assert no_candidate.accepted_parent == parent


def test_all_recorded_batches_are_unique_and_balanced() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    batch_map = load_json(BATCH_MAP_PATH)
    task_ids = []
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
        assert len(step["batch"]["task_ids"]) == 17
        task_ids.extend(step["batch"]["task_ids"])
    assert len(task_ids) == len(set(task_ids)) == 51


def test_semantically_invalid_batch_map_is_rejected_without_digests() -> None:
    batch_map = load_json(BATCH_MAP_PATH)
    batch_map["batches"][1]["assignments"][0]["task_id"] = (
        batch_map["batches"][0]["assignments"][0]["task_id"]
    )

    with pytest.raises(ControllerIntegrityError, match="51 unique"):
        register_step(
            load_json(CAMPAIGN_PATH),
            batch_map,
            step=1,
            parent=load_json(CAMPAIGN_PATH)["initial_parent"],
            parent_checkpoint=artifact("selection_checkpoint", "S0", "s0.json"),
        )


def test_reducer_does_not_mutate_input_and_rejects_wrong_order() -> None:
    step = registered_step()
    original = copy.deepcopy(step)

    result = reduce_step(step, {"type": "TRAIN_STARTED"})

    assert step == original
    assert result.step["status"] == "TRAIN_RUNNING"
    with pytest.raises(InvalidTransitionError):
        reduce_step(step, {"type": "TRAIN_COMPLETED"})


def test_integrity_failure_still_halts_as_a_v01_outcome() -> None:
    result = reduce_step(registered_step(), {"type": "INTEGRITY_FAILURE"})

    assert result.step["status"] == "STEP_INVALID"
    assert result.step["outcome"] == "INTEGRITY_FAILURE"
    assert result.action == "HALT_CAMPAIGN"
