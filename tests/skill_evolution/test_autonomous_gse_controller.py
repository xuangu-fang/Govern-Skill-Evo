"""Pure state-transition tests for the Autonomous GSE v0.1 Controller."""

from __future__ import annotations

import copy
import hashlib
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
STEP_SCHEMA_PATH = PROJECT_ROOT / "schemas/autonomous_gse_v01_step.schema.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(payload: dict) -> str:
    data = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def artifact(kind: str, version: str, marker: str) -> dict[str, str]:
    return {
        "kind": kind,
        "version": version,
        "path": f"artifacts/{marker}.json",
        "sha256": marker[0] * 64,
    }


def checkpoint(version: str, marker: str = "c") -> dict[str, str]:
    return artifact("selection_checkpoint", version, marker)


def candidate(step: int, marker: str = "d") -> dict[str, str]:
    candidate_id = f"epoch_001_step_{step:03d}_candidate"
    return artifact("candidate_skill", candidate_id, marker)


def validate_step(step: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json(STEP_SCHEMA_PATH)
    jsonschema.Draft202012Validator(schema).validate(step)


def registered_step(
    step_number: int = 1,
    *,
    parent: dict | None = None,
    parent_checkpoint: dict | None = None,
) -> dict:
    campaign = load_json(CAMPAIGN_PATH)
    current_parent = parent or campaign["initial_parent"]
    current_checkpoint = parent_checkpoint or checkpoint(
        current_parent["version"]
    )
    return register_step(
        campaign,
        load_json(BATCH_MAP_PATH),
        step=step_number,
        parent=current_parent,
        parent_checkpoint=current_checkpoint,
    )


def apply_events(step: dict, *event_types: str) -> dict:
    current = step
    for event_type in event_types:
        current = reduce_step(current, {"type": event_type}).step
    return current


TO_PROPOSAL = (
    "TRAIN_STARTED",
    "TRAIN_COMPLETED",
    "TRAIN_VALIDATED",
    "EXPERIENCE_FROZEN",
    "PROPOSAL_STARTED",
)

TO_GATE = (
    *TO_PROPOSAL,
    "CANDIDATE_FROZEN",
    "CANDIDATE_SELECTION_STARTED",
    "SELECTION_VALIDATED",
    "EVOLUTION_SUMMARY_FROZEN",
    "GATE_DECIDED",
)


def candidate_path_to_gate(step: dict, frozen_candidate: dict) -> dict:
    current = apply_events(step, *TO_PROPOSAL)
    current = reduce_step(
        current,
        {"type": "CANDIDATE_FROZEN", "candidate": frozen_candidate},
    ).step
    return apply_events(current, *TO_GATE[len(TO_PROPOSAL) + 1 :])


def test_registers_step_one_from_frozen_batch_map() -> None:
    step = registered_step()
    batch_map = load_json(BATCH_MAP_PATH)
    expected_task_ids = [
        assignment["task_id"]
        for assignment in batch_map["batches"][0]["assignments"]
    ]

    assert step["status"] == "STEP_REGISTERED"
    assert step["batch"]["batch_id"] == "batch_001"
    assert step["batch"]["task_ids"] == expected_task_ids
    assert step["proposal_operator"] == "bootstrap"
    assert step["candidate_id"] == "epoch_001_step_001_candidate"
    assert step["data_isolation"] == {
        "current_batch_only": True,
        "selection_for_learning": "forbidden",
        "test_for_learning": "forbidden",
    }
    validate_step(step)


def test_candidate_lifecycle_is_strictly_linear() -> None:
    current = registered_step()
    expected = [
        ("TRAIN_STARTED", "TRAIN_RUNNING", "WAIT_FOR_TRAIN_COMPLETION"),
        ("TRAIN_COMPLETED", "TRAIN_COMPLETED", "VALIDATE_TRAIN"),
        ("TRAIN_VALIDATED", "TRAIN_VALIDATED", "BUILD_AND_FREEZE_EXPERIENCE"),
        ("EXPERIENCE_FROZEN", "EXPERIENCE_FROZEN", "RUN_PROPOSAL"),
        ("PROPOSAL_STARTED", "PROPOSAL_RUNNING", "WAIT_FOR_PROPOSAL"),
    ]
    for event_type, status, action in expected:
        result = reduce_step(current, {"type": event_type})
        assert (result.step["status"], result.action) == (status, action)
        validate_step(result.step)
        current = result.step

    result = reduce_step(
        current,
        {"type": "CANDIDATE_FROZEN", "candidate": candidate(1)},
    )
    assert (result.step["status"], result.action) == (
        "CANDIDATE_FROZEN",
        "RUN_CANDIDATE_SELECTION",
    )
    validate_step(result.step)
    current = result.step

    expected = [
        (
            "CANDIDATE_SELECTION_STARTED",
            "CANDIDATE_SELECTION_RUNNING",
            "WAIT_FOR_CANDIDATE_SELECTION",
        ),
        (
            "SELECTION_VALIDATED",
            "SELECTION_VALIDATED",
            "FREEZE_EVOLUTION_SUMMARY",
        ),
        (
            "EVOLUTION_SUMMARY_FROZEN",
            "EVOLUTION_SUMMARY_FROZEN",
            "APPLY_EVOLUTION_GATE",
        ),
        ("GATE_DECIDED", "GATE_DECIDED", "FINALIZE_STEP"),
    ]
    for event_type, status, action in expected:
        result = reduce_step(current, {"type": event_type})
        assert (result.step["status"], result.action) == (status, action)
        validate_step(result.step)
        current = result.step


def test_accepted_parent_dispatches_incremental_on_next_batch() -> None:
    parent = artifact("accepted_skill", "S1", "a")
    step = registered_step(
        2,
        parent=parent,
        parent_checkpoint=checkpoint("S1", "b"),
    )

    assert step["batch"]["batch_id"] == "batch_002"
    assert step["proposal_operator"] == "incremental"
    assert step["candidate_id"] == "epoch_001_step_002_candidate"
    validate_step(step)


def test_step_one_must_use_explicit_campaign_s0() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    with pytest.raises(ControllerIntegrityError, match="initial Parent"):
        register_step(
            campaign,
            load_json(BATCH_MAP_PATH),
            step=1,
            parent=artifact("accepted_skill", "S1", "a"),
            parent_checkpoint=checkpoint("S1", "b"),
        )


def test_accept_path_promotes_candidate_and_checkpoint() -> None:
    initial = registered_step()
    frozen_candidate = candidate(1)
    at_gate = candidate_path_to_gate(initial, frozen_candidate)
    promoted_checkpoint = checkpoint("S1", "e")

    result = reduce_step(
        at_gate,
        {
            "type": "STEP_COMPLETED",
            "outcome": "ACCEPT",
            "candidate_checkpoint": promoted_checkpoint,
        },
    )

    assert result.step["status"] == "STEP_COMPLETED"
    assert result.step["outcome"] == "ACCEPT"
    assert result.step["next_parent"] == {
        "kind": "accepted_skill",
        "version": "S1",
        "path": frozen_candidate["path"],
        "sha256": frozen_candidate["sha256"],
    }
    assert result.accepted_parent == result.step["next_parent"]
    assert result.accepted_parent_checkpoint == promoted_checkpoint
    assert result.action == "REGISTER_NEXT_STEP"
    validate_step(result.step)

    next_step = register_step(
        load_json(CAMPAIGN_PATH),
        load_json(BATCH_MAP_PATH),
        step=2,
        parent=result.accepted_parent,
        parent_checkpoint=result.accepted_parent_checkpoint,
    )
    assert next_step["proposal_operator"] == "incremental"


def test_reject_path_retains_parent_and_checkpoint() -> None:
    parent = artifact("accepted_skill", "S1", "a")
    current_checkpoint = checkpoint("S1", "b")
    initial = registered_step(
        2,
        parent=parent,
        parent_checkpoint=current_checkpoint,
    )
    at_gate = candidate_path_to_gate(initial, candidate(2))

    result = reduce_step(
        at_gate,
        {"type": "STEP_COMPLETED", "outcome": "REJECT"},
    )

    assert result.step["outcome"] == "REJECT"
    assert result.step["next_parent"] == parent
    assert result.accepted_parent == parent
    assert result.accepted_parent_checkpoint == current_checkpoint
    assert result.action == "REGISTER_NEXT_STEP"
    validate_step(result.step)


@pytest.mark.parametrize("outcome", ["NO_CANDIDATE", "INVALID_PROPOSAL"])
def test_proposal_terminal_outcomes_skip_selection_and_retain_parent(
    outcome: str,
) -> None:
    initial = registered_step()
    at_proposal = apply_events(initial, *TO_PROPOSAL)

    result = reduce_step(at_proposal, {"type": outcome})

    assert result.step["status"] == "STEP_COMPLETED"
    assert result.step["outcome"] == outcome
    assert "candidate" not in result.step
    assert result.accepted_parent == initial["parent"]
    assert result.accepted_parent_checkpoint == initial["parent_checkpoint"]
    assert result.action == "REGISTER_NEXT_STEP"
    validate_step(result.step)


def test_integrity_failure_fails_closed_without_next_parent() -> None:
    running = reduce_step(
        registered_step(), {"type": "TRAIN_STARTED"}
    ).step

    result = reduce_step(running, {"type": "INTEGRITY_FAILURE"})

    assert result.step["status"] == "STEP_INVALID"
    assert result.step["outcome"] == "INTEGRITY_FAILURE"
    assert "next_parent" not in result.step
    assert result.action == "HALT_CAMPAIGN"
    validate_step(result.step)


def test_final_step_completion_completes_campaign() -> None:
    parent = artifact("accepted_skill", "S1", "a")
    initial = registered_step(
        3,
        parent=parent,
        parent_checkpoint=checkpoint("S1", "b"),
    )
    at_gate = candidate_path_to_gate(initial, candidate(3))

    result = reduce_step(
        at_gate,
        {"type": "STEP_COMPLETED", "outcome": "REJECT"},
    )

    assert result.action == "COMPLETE_CAMPAIGN"


def test_illegal_transition_and_terminal_reentry_are_rejected() -> None:
    initial = registered_step()
    with pytest.raises(InvalidTransitionError):
        reduce_step(initial, {"type": "TRAIN_COMPLETED"})

    at_proposal = apply_events(initial, *TO_PROPOSAL)
    completed = reduce_step(at_proposal, {"type": "NO_CANDIDATE"}).step
    with pytest.raises(InvalidTransitionError):
        reduce_step(completed, {"type": "TRAIN_STARTED"})


def test_accept_requires_candidate_checkpoint_for_new_parent() -> None:
    at_gate = candidate_path_to_gate(registered_step(), candidate(1))

    with pytest.raises(ControllerIntegrityError):
        reduce_step(
            at_gate,
            {"type": "STEP_COMPLETED", "outcome": "ACCEPT"},
        )

    with pytest.raises(ControllerIntegrityError, match="current Parent"):
        reduce_step(
            at_gate,
            {
                "type": "STEP_COMPLETED",
                "outcome": "ACCEPT",
                "candidate_checkpoint": checkpoint("S0"),
            },
        )


def test_reducer_is_deterministic_and_does_not_mutate_inputs() -> None:
    step = registered_step()
    event = {"type": "TRAIN_STARTED"}
    original_step = copy.deepcopy(step)
    original_event = copy.deepcopy(event)

    first = reduce_step(step, event)
    second = reduce_step(step, event)

    assert first == second
    assert step == original_step
    assert event == original_event


def test_registration_rejects_test_or_learning_isolation_drift() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    batch_map = load_json(BATCH_MAP_PATH)
    parent = campaign["initial_parent"]

    campaign["test"]["authorized"] = True
    with pytest.raises(ControllerIntegrityError):
        register_step(
            campaign,
            batch_map,
            step=1,
            parent=parent,
            parent_checkpoint=checkpoint("S0"),
        )


def test_only_three_steps_can_be_registered() -> None:
    with pytest.raises(ControllerIntegrityError):
        registered_step(4)


def test_registration_rejects_cross_batch_task_overlap() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    batch_map = load_json(BATCH_MAP_PATH)
    batch_map["batches"][1]["assignments"][0]["task_id"] = (
        batch_map["batches"][0]["assignments"][0]["task_id"]
    )
    campaign["train"]["batch_map"]["sha256"] = canonical_sha256(batch_map)

    with pytest.raises(ControllerIntegrityError, match="51 unique Tasks"):
        register_step(
            campaign,
            batch_map,
            step=1,
            parent=campaign["initial_parent"],
            parent_checkpoint=checkpoint("S0"),
        )


def test_registration_rejects_batch_map_hash_mismatch() -> None:
    campaign = load_json(CAMPAIGN_PATH)
    batch_map = load_json(BATCH_MAP_PATH)
    batch_map["assignment"]["seed"] = "tampered"

    with pytest.raises(ControllerIntegrityError, match="SHA-256"):
        register_step(
            campaign,
            batch_map,
            step=1,
            parent=campaign["initial_parent"],
            parent_checkpoint=checkpoint("S0"),
        )


def test_reducer_rejects_forged_candidate_lifecycle_state() -> None:
    forged = registered_step()
    forged["status"] = "CANDIDATE_SELECTION_RUNNING"

    with pytest.raises(ControllerIntegrityError, match="Candidate artifact"):
        reduce_step(forged, {"type": "SELECTION_VALIDATED"})
