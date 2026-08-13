"""Pure deterministic state reducer for Autonomous GSE v0.1.

This module performs no file writes, API calls, benchmark runs, or model calls.
It only registers a Step from frozen inputs and reduces one declared fact event
into the next Step state.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any


STEP_SCHEMA_VERSION = "autonomous_gse_step_0.1.0"
PROTOCOL_VERSION = "autonomous_gse_v01"
STEP_COUNT = 3

TERMINAL_STATUSES = {"STEP_COMPLETED", "STEP_INVALID"}

NONTERMINAL_STATUSES = {
    "STEP_REGISTERED",
    "TRAIN_RUNNING",
    "TRAIN_COMPLETED",
    "TRAIN_VALIDATED",
    "EXPERIENCE_FROZEN",
    "PROPOSAL_RUNNING",
    "CANDIDATE_FROZEN",
    "CANDIDATE_SELECTION_RUNNING",
    "SELECTION_VALIDATED",
    "EVOLUTION_SUMMARY_FROZEN",
    "GATE_DECIDED",
}

CANDIDATE_STATUSES = {
    "CANDIDATE_FROZEN",
    "CANDIDATE_SELECTION_RUNNING",
    "SELECTION_VALIDATED",
    "EVOLUTION_SUMMARY_FROZEN",
    "GATE_DECIDED",
}

LINEAR_TRANSITIONS = {
    ("STEP_REGISTERED", "TRAIN_STARTED"): (
        "TRAIN_RUNNING",
        "WAIT_FOR_TRAIN_COMPLETION",
    ),
    ("TRAIN_RUNNING", "TRAIN_COMPLETED"): (
        "TRAIN_COMPLETED",
        "VALIDATE_TRAIN",
    ),
    ("TRAIN_COMPLETED", "TRAIN_VALIDATED"): (
        "TRAIN_VALIDATED",
        "BUILD_AND_FREEZE_EXPERIENCE",
    ),
    ("TRAIN_VALIDATED", "EXPERIENCE_FROZEN"): (
        "EXPERIENCE_FROZEN",
        "RUN_PROPOSAL",
    ),
    ("EXPERIENCE_FROZEN", "PROPOSAL_STARTED"): (
        "PROPOSAL_RUNNING",
        "WAIT_FOR_PROPOSAL",
    ),
    ("CANDIDATE_FROZEN", "CANDIDATE_SELECTION_STARTED"): (
        "CANDIDATE_SELECTION_RUNNING",
        "WAIT_FOR_CANDIDATE_SELECTION",
    ),
    ("CANDIDATE_SELECTION_RUNNING", "SELECTION_VALIDATED"): (
        "SELECTION_VALIDATED",
        "FREEZE_EVOLUTION_SUMMARY",
    ),
    ("SELECTION_VALIDATED", "EVOLUTION_SUMMARY_FROZEN"): (
        "EVOLUTION_SUMMARY_FROZEN",
        "APPLY_EVOLUTION_GATE",
    ),
    ("EVOLUTION_SUMMARY_FROZEN", "GATE_DECIDED"): (
        "GATE_DECIDED",
        "FINALIZE_STEP",
    ),
}


class ControllerIntegrityError(ValueError):
    """Raised when a declared Step or Campaign invariant is inconsistent."""


class InvalidTransitionError(ValueError):
    """Raised when an event is not legal from the current lifecycle status."""


@dataclass(frozen=True)
class ControllerResult:
    """A reducer result with the accepted state carried separately."""

    step: dict[str, Any]
    accepted_parent: dict[str, Any] | None
    accepted_parent_checkpoint: dict[str, Any] | None
    action: str


def _require_artifact(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ControllerIntegrityError(f"{label} must be an artifact.")
    required = {"kind", "version", "path", "sha256"}
    if set(value) != required:
        raise ControllerIntegrityError(
            f"{label} must contain exactly {sorted(required)}."
        )
    for field in ("kind", "version", "path"):
        if not isinstance(value[field], str) or not value[field]:
            raise ControllerIntegrityError(
                f"{label}.{field} must be a non-empty string."
            )
    digest = value["sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ControllerIntegrityError(f"{label}.sha256 must be SHA-256.")
    return value


def _require_parent(parent: Any) -> dict[str, Any]:
    artifact = _require_artifact(parent, "parent")
    kind = artifact["kind"]
    version = artifact["version"]
    if kind == "no_skill" and version == "S0":
        return artifact
    if kind == "accepted_skill" and version.startswith("S"):
        try:
            number = int(version[1:])
        except ValueError as error:
            raise ControllerIntegrityError(
                "accepted Parent version must be S1 or later."
            ) from error
        if number >= 1 and version == f"S{number}":
            return artifact
    raise ControllerIntegrityError(
        "Parent must be no_skill S0 or accepted_skill S1+."
    )


def _require_checkpoint(
    value: Any,
    parent: dict[str, Any],
) -> dict[str, Any]:
    checkpoint = _require_artifact(value, "parent_checkpoint")
    if checkpoint["kind"] != "selection_checkpoint":
        raise ControllerIntegrityError(
            "parent_checkpoint must be a selection_checkpoint."
        )
    if checkpoint["version"] != parent["version"]:
        raise ControllerIntegrityError(
            "parent_checkpoint must belong to the current Parent."
        )
    return checkpoint


def _proposal_operator(parent: dict[str, Any]) -> str:
    return "bootstrap" if parent["kind"] == "no_skill" else "incremental"


def _accepted_version_after(parent: dict[str, Any]) -> str:
    return f"S{int(parent['version'][1:]) + 1}"


def _require_campaign_contract(campaign: dict[str, Any]) -> None:
    if campaign.get("protocol_version") != PROTOCOL_VERSION:
        raise ControllerIntegrityError("Unsupported Campaign protocol.")
    if campaign.get("status") not in {"draft", "frozen"}:
        raise ControllerIntegrityError("Campaign status must be draft or frozen.")
    if campaign.get("schedule") != {
        "epochs": 1,
        "steps_per_epoch": 3,
        "scheduled_steps": 3,
    }:
        raise ControllerIntegrityError("Campaign must schedule exactly 3 Steps.")
    proposal = campaign.get("proposal", {})
    if (
        proposal.get("maximum_learner_calls") != 3
        or proposal.get("candidates_per_step") != 1
        or proposal.get("selection_feedback_to_learner") != "forbidden"
        or proposal.get("test_feedback_to_learner") != "forbidden"
    ):
        raise ControllerIntegrityError("Proposal budget or isolation drifted.")
    if campaign.get("test") != {
        "authorized": False,
        "data_for_learning": "forbidden",
    }:
        raise ControllerIntegrityError("Test must remain unauthorized.")
    budget = campaign.get("budget", {})
    if (
        budget.get("maximum_learner_calls") != 3
        or budget.get("maximum_candidates") != 3
        or budget.get("maximum_total_trajectories") != 123
    ):
        raise ControllerIntegrityError("Campaign budget drifted.")
    train = campaign.get("train", {})
    train_contract = {
        "total_tasks": 51,
        "intent_templates": 17,
        "batches": 3,
        "tasks_per_batch": 17,
        "tasks_per_template": 3,
        "template_balanced": True,
        "overlap_between_batches": 0,
        "cumulative_evidence": False,
        "replay_previous_batches": False,
    }
    if any(train.get(key) != value for key, value in train_contract.items()):
        raise ControllerIntegrityError("Train batch contract drifted.")
    selection = campaign.get("selection", {})
    if (
        selection.get("protocol") != "accepted_parent_checkpoint"
        or selection.get("tasks") != 18
        or selection.get("selection_data_for_learning") != "forbidden"
    ):
        raise ControllerIntegrityError("Selection checkpoint contract drifted.")


def _batch_for_step(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    step: int,
) -> dict[str, Any]:
    train = campaign.get("train", {})
    batch_binding = _require_artifact(train.get("batch_map"), "batch_map")
    canonical_batch_map = (
        json.dumps(batch_map, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    actual_batch_map_sha256 = hashlib.sha256(canonical_batch_map).hexdigest()
    if actual_batch_map_sha256 != batch_binding["sha256"]:
        raise ControllerIntegrityError("Batch Map SHA-256 does not match binding.")
    source_binding = _require_artifact(
        train.get("source_manifest"), "source_manifest"
    )
    source = batch_map.get("source", {})
    if (
        batch_map.get("status") != "frozen"
        or batch_map.get("campaign_id") != campaign.get("campaign_id")
        or batch_map.get("schema_version") != batch_binding["version"]
        or batch_map.get("assignment", {}).get("algorithm")
        != train.get("assignment_algorithm")
        or batch_map.get("assignment", {}).get("seed")
        != train.get("assignment_seed")
        or source.get("path") != source_binding["path"]
        or source.get("sha256") != source_binding["sha256"]
        or source.get("split") != train.get("source_split")
    ):
        raise ControllerIntegrityError("Batch Map does not match Campaign.")

    batches = batch_map.get("batches")
    if not isinstance(batches, list) or len(batches) != STEP_COUNT:
        raise ControllerIntegrityError("Batch Map must contain exactly 3 batches.")
    task_ids_by_batch: list[list[int]] = []
    template_ids_by_batch: list[list[int]] = []
    for rank, candidate_batch in enumerate(batches, start=1):
        expected_id = f"batch_{rank:03d}"
        if (
            not isinstance(candidate_batch, dict)
            or candidate_batch.get("batch_id") != expected_id
        ):
            raise ControllerIntegrityError("Batch order or identity drifted.")
        assignments = candidate_batch.get("assignments")
        if not isinstance(assignments, list) or len(assignments) != 17:
            raise ControllerIntegrityError(
                "Each batch must contain 17 assignments."
            )
        try:
            task_ids = [assignment["task_id"] for assignment in assignments]
            template_ids = [
                assignment["intent_template_id"] for assignment in assignments
            ]
        except (KeyError, TypeError) as error:
            raise ControllerIntegrityError(
                "Batch assignment is malformed."
            ) from error
        if len(set(task_ids)) != 17 or len(set(template_ids)) != 17:
            raise ControllerIntegrityError(
                "Each batch must contain 17 unique Tasks and templates."
            )
        task_ids_by_batch.append(task_ids)
        template_ids_by_batch.append(template_ids)

    all_task_ids = [task_id for task_ids in task_ids_by_batch for task_id in task_ids]
    template_sets = [set(template_ids) for template_ids in template_ids_by_batch]
    if len(set(all_task_ids)) != 51:
        raise ControllerIntegrityError("Batch Map must cover 51 unique Tasks.")
    if any(template_set != template_sets[0] for template_set in template_sets[1:]):
        raise ControllerIntegrityError(
            "Every batch must cover the same 17 intent templates."
        )

    expected_batch_id = f"batch_{step:03d}"
    task_ids = task_ids_by_batch[step - 1]
    return {
        "batch_id": expected_batch_id,
        "batch_map_path": batch_binding["path"],
        "batch_map_sha256": batch_binding["sha256"],
        "task_ids": task_ids,
    }


def register_step(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    *,
    step: int,
    parent: dict[str, Any],
    parent_checkpoint: dict[str, Any],
) -> dict[str, Any]:
    """Build one deterministic STEP_REGISTERED record from declared facts."""

    _require_campaign_contract(campaign)
    if not isinstance(step, int) or isinstance(step, bool) or not 1 <= step <= 3:
        raise ControllerIntegrityError("Step must be an integer from 1 to 3.")
    current_parent = _require_parent(parent)
    initial_parent = _require_parent(campaign.get("initial_parent"))
    if step == 1 and current_parent != initial_parent:
        raise ControllerIntegrityError(
            "Step 1 must start from the Campaign initial Parent."
        )
    checkpoint = _require_checkpoint(parent_checkpoint, current_parent)
    batch = _batch_for_step(campaign, batch_map, step)

    return {
        "schema_version": STEP_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "campaign_id": campaign["campaign_id"],
        "epoch": 1,
        "step": step,
        "status": "STEP_REGISTERED",
        "batch": copy.deepcopy(batch),
        "parent": copy.deepcopy(current_parent),
        "proposal_operator": _proposal_operator(current_parent),
        "candidate_id": f"epoch_001_step_{step:03d}_candidate",
        "parent_checkpoint": copy.deepcopy(checkpoint),
        "budget_reservation": {
            "train_trajectories": 17,
            "maximum_candidate_selection_trajectories": 18,
            "maximum_learner_calls": 1,
        },
        "data_isolation": {
            "current_batch_only": True,
            "selection_for_learning": "forbidden",
            "test_for_learning": "forbidden",
        },
    }


def _require_step_invariants(step: dict[str, Any]) -> None:
    if step.get("schema_version") != STEP_SCHEMA_VERSION:
        raise ControllerIntegrityError("Unsupported Step schema.")
    if step.get("protocol_version") != PROTOCOL_VERSION:
        raise ControllerIntegrityError("Unsupported Step protocol.")
    step_number = step.get("step")
    if not isinstance(step_number, int) or not 1 <= step_number <= STEP_COUNT:
        raise ControllerIntegrityError("Step number is out of range.")
    if step.get("batch", {}).get("batch_id") != f"batch_{step_number:03d}":
        raise ControllerIntegrityError("Step is bound to the wrong batch.")
    if step.get("candidate_id") != (
        f"epoch_001_step_{step_number:03d}_candidate"
    ):
        raise ControllerIntegrityError("Candidate identity does not match Step.")
    parent = _require_parent(step.get("parent"))
    _require_checkpoint(step.get("parent_checkpoint"), parent)
    if step.get("proposal_operator") != _proposal_operator(parent):
        raise ControllerIntegrityError("Proposal operator does not match Parent.")
    if step.get("data_isolation") != {
        "current_batch_only": True,
        "selection_for_learning": "forbidden",
        "test_for_learning": "forbidden",
    }:
        raise ControllerIntegrityError("Step data isolation drifted.")
    if step.get("budget_reservation") != {
        "train_trajectories": 17,
        "maximum_candidate_selection_trajectories": 18,
        "maximum_learner_calls": 1,
    }:
        raise ControllerIntegrityError("Step budget reservation drifted.")
    status = step.get("status")
    if status not in NONTERMINAL_STATUSES | TERMINAL_STATUSES:
        raise ControllerIntegrityError("Unknown Step lifecycle status.")
    if status in NONTERMINAL_STATUSES and (
        "outcome" in step or "next_parent" in step
    ):
        raise ControllerIntegrityError(
            "Nonterminal Step cannot have outcome or next_parent."
        )
    candidate_present = "candidate" in step
    if status in CANDIDATE_STATUSES and not candidate_present:
        raise ControllerIntegrityError(
            "Candidate lifecycle state requires a Candidate artifact."
        )
    if status in NONTERMINAL_STATUSES - CANDIDATE_STATUSES and candidate_present:
        raise ControllerIntegrityError(
            "Candidate artifact cannot precede CANDIDATE_FROZEN."
        )
    if candidate_present:
        candidate = _require_artifact(step["candidate"], "candidate")
        if (
            candidate["kind"] != "candidate_skill"
            or candidate["version"] != step["candidate_id"]
        ):
            raise ControllerIntegrityError(
                "Candidate artifact does not match the registered identity."
            )


def _require_event_keys(event: dict[str, Any], allowed: set[str]) -> None:
    if set(event) != allowed:
        raise ControllerIntegrityError(
            f"Event must contain exactly {sorted(allowed)}."
        )


def _result(
    step: dict[str, Any],
    action: str,
    *,
    parent: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
) -> ControllerResult:
    return ControllerResult(
        step=step,
        accepted_parent=copy.deepcopy(parent),
        accepted_parent_checkpoint=copy.deepcopy(checkpoint),
        action=action,
    )


def reduce_step(
    step: dict[str, Any],
    event: dict[str, Any],
) -> ControllerResult:
    """Reduce exactly one event without mutating the Step or event."""

    if not isinstance(step, dict) or not isinstance(event, dict):
        raise ControllerIntegrityError("Step and event must be objects.")
    _require_step_invariants(step)
    current_status = step.get("status")
    event_type = event.get("type")
    if current_status in TERMINAL_STATUSES:
        raise InvalidTransitionError("A terminal Step cannot be reduced again.")
    if not isinstance(event_type, str):
        raise ControllerIntegrityError("Event type must be a string.")

    updated = copy.deepcopy(step)
    parent = updated["parent"]
    checkpoint = updated["parent_checkpoint"]

    if event_type == "INTEGRITY_FAILURE":
        _require_event_keys(event, {"type"})
        updated["status"] = "STEP_INVALID"
        updated["outcome"] = "INTEGRITY_FAILURE"
        updated.pop("next_parent", None)
        return _result(updated, "HALT_CAMPAIGN")

    transition = LINEAR_TRANSITIONS.get((current_status, event_type))
    if transition is not None:
        _require_event_keys(event, {"type"})
        updated["status"], action = transition
        return _result(
            updated,
            action,
            parent=parent,
            checkpoint=checkpoint,
        )

    if current_status == "PROPOSAL_RUNNING" and event_type == (
        "CANDIDATE_FROZEN"
    ):
        _require_event_keys(event, {"type", "candidate"})
        frozen_candidate = _require_artifact(
            event.get("candidate"), "candidate"
        )
        if (
            frozen_candidate["kind"] != "candidate_skill"
            or frozen_candidate["version"] != updated["candidate_id"]
        ):
            raise ControllerIntegrityError(
                "Candidate artifact does not match the registered identity."
            )
        updated["candidate"] = copy.deepcopy(frozen_candidate)
        updated["status"] = "CANDIDATE_FROZEN"
        return _result(
            updated,
            "RUN_CANDIDATE_SELECTION",
            parent=parent,
            checkpoint=checkpoint,
        )

    if current_status == "PROPOSAL_RUNNING" and event_type in {
        "NO_CANDIDATE",
        "INVALID_PROPOSAL",
    }:
        _require_event_keys(event, {"type"})
        updated["status"] = "STEP_COMPLETED"
        updated["outcome"] = event_type
        updated["next_parent"] = copy.deepcopy(parent)
        action = (
            "COMPLETE_CAMPAIGN"
            if updated["step"] == STEP_COUNT
            else "REGISTER_NEXT_STEP"
        )
        return _result(
            updated,
            action,
            parent=parent,
            checkpoint=checkpoint,
        )

    if current_status == "GATE_DECIDED" and event_type == "STEP_COMPLETED":
        outcome = event.get("outcome")
        if outcome not in {"ACCEPT", "REJECT"}:
            raise ControllerIntegrityError(
                "Gate completion outcome must be ACCEPT or REJECT."
            )
        candidate = _require_artifact(updated.get("candidate"), "candidate")

        if outcome == "ACCEPT":
            _require_event_keys(
                event, {"type", "outcome", "candidate_checkpoint"}
            )
            next_parent = {
                "kind": "accepted_skill",
                "version": _accepted_version_after(parent),
                "path": candidate["path"],
                "sha256": candidate["sha256"],
            }
            next_checkpoint = _require_checkpoint(
                event.get("candidate_checkpoint"), next_parent
            )
        else:
            _require_event_keys(event, {"type", "outcome"})
            next_parent = parent
            next_checkpoint = checkpoint

        updated["status"] = "STEP_COMPLETED"
        updated["outcome"] = outcome
        updated["next_parent"] = copy.deepcopy(next_parent)
        action = (
            "COMPLETE_CAMPAIGN"
            if updated["step"] == STEP_COUNT
            else "REGISTER_NEXT_STEP"
        )
        return _result(
            updated,
            action,
            parent=next_parent,
            checkpoint=next_checkpoint,
        )

    raise InvalidTransitionError(
        f"Event {event_type!r} is invalid from {current_status!r}."
    )
