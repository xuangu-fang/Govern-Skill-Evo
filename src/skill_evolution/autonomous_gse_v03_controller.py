"""Pure deterministic state reducer for Autonomous GSE v0.3."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


STEP_SCHEMA_VERSION = "autonomous_gse_step_0.3.0"
PROTOCOL_VERSION = "autonomous_gse_v03"
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
        "BUILD_EXPERIENCE",
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
        "RECORD_EVOLUTION_SUMMARY",
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

PROPOSAL_BUDGET = {
    "maximum_raw_patches_per_reflector": 4,
    "maximum_reflector_calls": 2,
    "maximum_editor_calls": 1,
    "additional_minibatching": False,
    "maximum_skill_rules": 18,
    "maximum_skill_words": 900,
    "allowed_operations": ["add", "replace", "delete"],
}
DIAGNOSIS_PROPOSAL_OPERATOR = "diagnosis_driven_bounded_edit"
DIAGNOSIS_PROPOSAL_BUDGET_FIELDS = {
    "maximum_diagnosis_calls",
    "eligible_update_diagnoses",
    "maximum_editor_calls",
    "additional_minibatching",
    "maximum_skill_rules",
    "maximum_skill_words",
    "allowed_operations",
}
DATA_ISOLATION = {
    "current_batch_only": True,
    "eligible_evidence_states": [
        "compliant_success",
        "violating_success",
        "compliant_failure",
        "violating_failure",
    ],
    "selection_for_learning": "forbidden",
    "test_for_learning": "forbidden",
}
NO_CANDIDATE_REASONS = {
    "UNPARSEABLE_RESPONSE",
    "EDITS_NOT_LIST",
    "EMPTY_EDITS",
    "NO_APPLICABLE_EDITS",
    "NO_SKILL_CHANGE",
    "NO_UPDATE_ELIGIBLE_DIAGNOSIS",
}


class ControllerContractError(ValueError):
    """Raised when declared v0.3 Controller data is inconsistent."""


class InvalidTransitionError(ValueError):
    """Raised when an event is not legal from the current status."""


@dataclass(frozen=True)
class ControllerResult:
    step: dict[str, Any]
    accepted_parent: dict[str, Any] | None
    accepted_parent_checkpoint: dict[str, Any] | None
    action: str


def _require_artifact(value: Any, label: str) -> dict[str, Any]:
    required = {"kind", "version", "path"}
    if not isinstance(value, dict) or set(value) != required:
        raise ControllerContractError(
            f"{label} must contain exactly {sorted(required)}."
        )
    if any(not isinstance(value[key], str) or not value[key] for key in required):
        raise ControllerContractError(f"{label} fields must be non-empty text.")
    return copy.deepcopy(value)


def _require_parent(value: Any) -> dict[str, Any]:
    required = {"kind", "version", "path"}
    if not isinstance(value, dict) or not required <= set(value):
        raise ControllerContractError("Parent artifact is invalid.")
    parent = {key: value[key] for key in required}
    if any(not isinstance(parent[key], str) or not parent[key] for key in required):
        raise ControllerContractError("Parent fields must be non-empty text.")
    if parent["kind"] == "empty_skill" and parent["version"] == "S0":
        return parent
    if parent["kind"] == "accepted_skill" and parent["version"].startswith("S"):
        try:
            number = int(parent["version"][1:])
        except ValueError as error:
            raise ControllerContractError(
                "Accepted Parent version must be S1 or later."
            ) from error
        if number >= 1 and parent["version"] == f"S{number}":
            return parent
    raise ControllerContractError(
        "Parent must be empty_skill S0 or accepted_skill S1+."
    )


def _require_checkpoint(value: Any, parent: dict[str, Any]) -> dict[str, Any]:
    checkpoint = _require_artifact(value, "parent_checkpoint")
    if checkpoint["kind"] != "selection_checkpoint":
        raise ControllerContractError(
            "parent_checkpoint must be a selection_checkpoint."
        )
    if checkpoint["version"] != parent["version"]:
        raise ControllerContractError(
            "parent_checkpoint must belong to the current Parent."
        )
    return checkpoint


def _accepted_version_after(parent: dict[str, Any]) -> str:
    return f"S{int(parent['version'][1:]) + 1}"


def _require_campaign_contract(campaign: dict[str, Any]) -> None:
    if campaign.get("protocol_version") != PROTOCOL_VERSION:
        raise ControllerContractError("Unsupported Campaign protocol.")
    if campaign.get("campaign_id") != PROTOCOL_VERSION:
        raise ControllerContractError("Campaign ID does not match v0.3.")
    if campaign.get("status") != "ready":
        raise ControllerContractError("Campaign status must be ready.")
    if campaign.get("schedule") != {
        "epochs": 1,
        "steps_per_epoch": 3,
        "scheduled_steps": 3,
    }:
        raise ControllerContractError("Campaign must schedule exactly 3 Steps.")

    proposal = campaign.get("proposal", {})
    proposal_contract = {
        "operator": "governed_reflection_editor",
        "candidates_per_step": 1,
        "maximum_learner_calls_per_step": 3,
        "learner_retry": "forbidden",
        "eligible_evidence_states": DATA_ISOLATION["eligible_evidence_states"],
        "selection_feedback_to_learner": "forbidden",
        "test_feedback_to_learner": "forbidden",
    }
    if any(proposal.get(key) != value for key, value in proposal_contract.items()):
        raise ControllerContractError("Proposal contract drifted.")
    if proposal.get("reflection") != {
        "reflectors": ["success", "failure"],
        "success_states": ["compliant_success", "violating_success"],
        "failure_states": ["compliant_failure", "violating_failure"],
        "grouping_strategy": "one_group_per_outcome",
        "additional_minibatching": False,
        "maximum_raw_patches_per_reflector": 4,
        "output": "raw_patches_only",
    }:
        raise ControllerContractError("Reflection contract drifted.")
    if proposal.get("editor") != {
        "input": "current_parent_skill_and_all_raw_patches",
        "output": "canonical_edits",
        "merge": True,
        "deduplicate": True,
        "resolve_conflicts": True,
        "patch_expansion": "forbidden",
        "ranking": False,
        "top_k_selection": False,
    }:
        raise ControllerContractError("Editor contract drifted.")
    if proposal.get("deterministic_update") != {
        "input": "canonical_edits_only",
        "maximum_skill_rules": 18,
        "maximum_skill_words": 900,
        "allowed_operations": ["add", "replace", "delete"],
        "edit_unit": "one_markdown_bullet",
        "invalid_edit_scope": "exclude_edit_without_invalidating_proposal",
        "minimum_applied_edits_for_candidate": 1,
    }:
        raise ControllerContractError("Deterministic Update contract drifted.")
    provenance = proposal.get("provenance", {})
    if (
        provenance.get("blocks_candidate_selection") is not False
        or provenance.get("read_by_evolution_gate") is not False
        or provenance.get("accepted_unverified_candidate_can_be_parent") is not True
    ):
        raise ControllerContractError("Provenance must remain diagnostic.")

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
        "batch_map": "experiments/campaigns/autonomous_gse_v02/batch_map.json",
    }
    if any(train.get(key) != value for key, value in train_contract.items()):
        raise ControllerContractError("Train batch contract drifted.")
    budget = campaign.get("budget", {})
    if (
        budget.get("maximum_total_trajectories") != 123
        or budget.get("maximum_learner_calls") != 9
    ):
        raise ControllerContractError("Campaign budget drifted.")
    if campaign.get("test") != {
        "authorized": False,
        "data_for_learning": "forbidden",
    }:
        raise ControllerContractError("Test must remain unauthorized.")
    selection = campaign.get("selection", {})
    if (
        selection.get("tasks") != 18
        or selection.get("selection_data_for_learning") != "forbidden"
        or selection.get("provenance_status_is_selection_input") is not False
    ):
        raise ControllerContractError("Selection contract drifted.")
    if campaign.get("gate", {}).get("provenance_status_is_input") is not False:
        raise ControllerContractError("Gate cannot read Provenance status.")


def _batch_for_step(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    step: int,
) -> dict[str, Any]:
    train = campaign.get("train", {})
    source = batch_map.get("source", {})
    if (
        batch_map.get("schema_version") != "autonomous_gse_batch_map_0.2.0"
        or batch_map.get("campaign_id") != "autonomous_gse_v02"
        or batch_map.get("status") != "ready"
        or source.get("path") != train.get("source_manifest")
        or source.get("split") != train.get("source_split")
    ):
        raise ControllerContractError("Batch Map does not match Campaign.")

    batches = batch_map.get("batches")
    if not isinstance(batches, list) or len(batches) != STEP_COUNT:
        raise ControllerContractError("Batch Map must contain exactly 3 batches.")
    all_task_ids: list[int] = []
    template_sets: list[set[int]] = []
    task_ids_by_batch: list[list[int]] = []
    for rank, batch in enumerate(batches, start=1):
        if not isinstance(batch, dict) or batch.get("batch_id") != (
            f"batch_{rank:03d}"
        ):
            raise ControllerContractError("Batch order or identity is invalid.")
        assignments = batch.get("assignments")
        if not isinstance(assignments, list) or len(assignments) != 17:
            raise ControllerContractError("Each batch needs 17 assignments.")
        if any(
            not isinstance(assignment, dict)
            or set(assignment) != {"task_id", "intent_template_id"}
            or not isinstance(assignment["task_id"], int)
            or not isinstance(assignment["intent_template_id"], int)
            for assignment in assignments
        ):
            raise ControllerContractError("Batch assignment is malformed.")
        task_ids = [assignment["task_id"] for assignment in assignments]
        template_ids = [
            assignment["intent_template_id"] for assignment in assignments
        ]
        if len(set(task_ids)) != 17 or len(set(template_ids)) != 17:
            raise ControllerContractError(
                "Each batch needs 17 unique Tasks and templates."
            )
        task_ids_by_batch.append(task_ids)
        all_task_ids.extend(task_ids)
        template_sets.append(set(template_ids))
    if len(set(all_task_ids)) != 51:
        raise ControllerContractError("Batch Map must cover 51 unique Tasks.")
    if any(item != template_sets[0] for item in template_sets[1:]):
        raise ControllerContractError(
            "Every batch must cover the same intent templates."
        )

    return {
        "batch_id": f"batch_{step:03d}",
        "batch_map": train["batch_map"],
        "task_ids": task_ids_by_batch[step - 1],
    }


def register_step(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    *,
    step: int,
    parent: dict[str, Any],
    parent_checkpoint: dict[str, Any],
    epoch: int = 1,
    batch_step: int | None = None,
    scheduled_steps: int = STEP_COUNT,
) -> dict[str, Any]:
    """Build one deterministic STEP_REGISTERED record."""

    _require_campaign_contract(campaign)
    resolved_batch_step = step if batch_step is None else batch_step
    if (
        not isinstance(step, int)
        or isinstance(step, bool)
        or not 1 <= step <= scheduled_steps
        or not isinstance(epoch, int)
        or isinstance(epoch, bool)
        or epoch < 1
        or not isinstance(resolved_batch_step, int)
        or isinstance(resolved_batch_step, bool)
        or not 1 <= resolved_batch_step <= STEP_COUNT
    ):
        raise ControllerContractError("Step schedule is invalid.")
    current_parent = _require_parent(parent)
    initial_parent = _require_parent(campaign.get("initial_parent"))
    if step == 1 and current_parent != initial_parent:
        raise ControllerContractError("Step 1 must start from explicit empty S0.")
    checkpoint = _require_checkpoint(parent_checkpoint, current_parent)

    registered = {
        "schema_version": STEP_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "campaign_id": campaign["campaign_id"],
        "epoch": epoch,
        "step": step,
        "status": "STEP_REGISTERED",
        "batch": _batch_for_step(campaign, batch_map, resolved_batch_step),
        "parent": current_parent,
        "proposal_operator": "governed_reflection_editor",
        "candidate_id": f"epoch_{epoch:03d}_step_{step:03d}_candidate",
        "parent_checkpoint": checkpoint,
        "proposal_budget": copy.deepcopy(PROPOSAL_BUDGET),
        "data_isolation": copy.deepcopy(DATA_ISOLATION),
    }
    if batch_step is not None:
        registered["batch_step"] = resolved_batch_step
        registered["scheduled_steps"] = scheduled_steps
    return registered


def _require_proposal_fields(step: dict[str, Any]) -> None:
    for field in (
        "raw_patches",
        "canonical_edits",
        "applied_edits",
        "excluded_edits",
    ):
        if not isinstance(step.get(field), list):
            raise ControllerContractError("Proposal edit history is invalid.")
    reason = step.get("proposal_reason")
    if not isinstance(reason, dict) or not isinstance(reason.get("code"), str):
        raise ControllerContractError("Proposal reason is invalid.")

    if step.get("proposal_operator") == "governed_reflection_editor":
        raw_patches = step["raw_patches"]
        if len(raw_patches) > 8:
            raise ControllerContractError("Raw patch budget was exceeded.")
        for reflector in ("success", "failure"):
            count = sum(
                isinstance(patch, dict) and patch.get("reflector") == reflector
                for patch in raw_patches
            )
            if count > 4:
                raise ControllerContractError(
                    "Reflector raw patch budget was exceeded."
                )


def _require_candidate_fields(step: dict[str, Any]) -> None:
    _require_proposal_fields(step)
    if step.get("proposal_status") != "CANDIDATE":
        raise ControllerContractError("Candidate status is invalid.")
    if step["proposal_reason"] != {"code": "CANDIDATE_CONSTRUCTED"}:
        raise ControllerContractError("Candidate reason is invalid.")
    if not step["applied_edits"]:
        raise ControllerContractError("Candidate needs at least one applied edit.")
    status = step.get("provenance_status")
    audit = step.get("provenance_audit")
    if status not in {"VERIFIED", "UNVERIFIED"} or not isinstance(audit, dict):
        raise ControllerContractError("Candidate Provenance diagnostic is invalid.")
    if audit.get("status") != status or not isinstance(audit.get("issues"), list):
        raise ControllerContractError("Provenance status and audit disagree.")


def _require_step_invariants(step: dict[str, Any]) -> None:
    if step.get("schema_version") != STEP_SCHEMA_VERSION:
        raise ControllerContractError("Unsupported Step schema.")
    if step.get("protocol_version") != PROTOCOL_VERSION:
        raise ControllerContractError("Unsupported Step protocol.")
    step_number = step.get("step")
    scheduled_steps = step.get("scheduled_steps", STEP_COUNT)
    batch_step = step.get("batch_step", step_number)
    epoch = step.get("epoch")
    if (
        not isinstance(step_number, int)
        or not isinstance(scheduled_steps, int)
        or not 1 <= step_number <= scheduled_steps
        or not isinstance(batch_step, int)
        or not 1 <= batch_step <= STEP_COUNT
        or not isinstance(epoch, int)
        or epoch < 1
    ):
        raise ControllerContractError("Step number is out of range.")
    if step.get("batch", {}).get("batch_id") != f"batch_{batch_step:03d}":
        raise ControllerContractError("Step is assigned to the wrong batch.")
    if step.get("candidate_id") != (
        f"epoch_{epoch:03d}_step_{step_number:03d}_candidate"
    ):
        raise ControllerContractError("Candidate ID does not match Step.")
    parent = _require_parent(step.get("parent"))
    _require_checkpoint(step.get("parent_checkpoint"), parent)
    proposal_operator = step.get("proposal_operator")
    proposal_budget = step.get("proposal_budget")
    if proposal_operator == "governed_reflection_editor":
        if proposal_budget != PROPOSAL_BUDGET:
            raise ControllerContractError("Step proposal budget drifted.")
    elif proposal_operator == DIAGNOSIS_PROPOSAL_OPERATOR:
        if (
            not isinstance(proposal_budget, dict)
            or set(proposal_budget) != DIAGNOSIS_PROPOSAL_BUDGET_FIELDS
            or not isinstance(proposal_budget.get("maximum_diagnosis_calls"), int)
            or isinstance(proposal_budget.get("maximum_diagnosis_calls"), bool)
            or proposal_budget["maximum_diagnosis_calls"] <= 0
            or proposal_budget.get("eligible_update_diagnoses") != "all_valid_updates"
            or proposal_budget.get("maximum_editor_calls") != 1
            or proposal_budget.get("additional_minibatching") is not False
            or proposal_budget.get("maximum_skill_rules") != 18
            or proposal_budget.get("maximum_skill_words") != 900
            or proposal_budget.get("allowed_operations")
            != ["add", "replace", "delete"]
        ):
            raise ControllerContractError("Diagnosis proposal budget drifted.")
    else:
        raise ControllerContractError("Step proposal operator is unsupported.")
    if step.get("data_isolation") != DATA_ISOLATION:
        raise ControllerContractError("Step data isolation drifted.")

    status = step.get("status")
    if status not in NONTERMINAL_STATUSES | TERMINAL_STATUSES:
        raise ControllerContractError("Unknown Step status.")
    candidate_present = "candidate" in step
    if status in CANDIDATE_STATUSES:
        if not candidate_present:
            raise ControllerContractError("Candidate state needs an artifact.")
        _require_candidate_fields(step)
    elif status in NONTERMINAL_STATUSES and candidate_present:
        raise ControllerContractError("Candidate artifact appeared too early.")
    if candidate_present:
        candidate = _require_artifact(step["candidate"], "candidate")
        if (
            candidate["kind"] != "candidate_skill"
            or candidate["version"] != step["candidate_id"]
        ):
            raise ControllerContractError("Candidate artifact is inconsistent.")
    if status in NONTERMINAL_STATUSES and (
        "outcome" in step or "next_parent" in step
    ):
        raise ControllerContractError("Nonterminal Step has a final outcome.")
    if status == "STEP_COMPLETED":
        _require_proposal_fields(step)
        if step.get("outcome") in {"ACCEPT", "REJECT"}:
            _require_candidate_fields(step)
        elif step.get("outcome") == "NO_CANDIDATE":
            if step.get("proposal_status") != "NO_CANDIDATE":
                raise ControllerContractError("NO_CANDIDATE status is invalid.")
            if step["proposal_reason"].get("code") not in NO_CANDIDATE_REASONS:
                raise ControllerContractError("NO_CANDIDATE reason is invalid.")
            if step["applied_edits"] or candidate_present:
                raise ControllerContractError(
                    "NO_CANDIDATE cannot contain a Candidate."
                )
        else:
            raise ControllerContractError("Completed Step outcome is invalid.")
        _require_parent(step.get("next_parent"))
    if status == "STEP_INVALID":
        if step.get("outcome") != "INTEGRITY_FAILURE" or candidate_present:
            raise ControllerContractError("Invalid Step outcome is inconsistent.")


def _require_event_keys(event: dict[str, Any], allowed: set[str]) -> None:
    if set(event) != allowed:
        raise ControllerContractError(
            f"Event must contain exactly {sorted(allowed)}."
        )


def _result(
    step: dict[str, Any],
    action: str,
    *,
    parent: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
) -> ControllerResult:
    _require_step_invariants(step)
    return ControllerResult(
        step=step,
        accepted_parent=copy.deepcopy(parent),
        accepted_parent_checkpoint=copy.deepcopy(checkpoint),
        action=action,
    )


def _next_action(step: int, scheduled_steps: int = STEP_COUNT) -> str:
    return "COMPLETE_CAMPAIGN" if step == scheduled_steps else "REGISTER_NEXT_STEP"


def reduce_step(step: dict[str, Any], event: dict[str, Any]) -> ControllerResult:
    """Reduce one declared event without mutating its inputs."""

    if not isinstance(step, dict) or not isinstance(event, dict):
        raise ControllerContractError("Step and event must be objects.")
    _require_step_invariants(step)
    status = step["status"]
    if status in TERMINAL_STATUSES:
        raise InvalidTransitionError("A terminal Step cannot be reduced again.")
    event_type = event.get("type")
    if not isinstance(event_type, str):
        raise ControllerContractError("Event type must be text.")

    updated = copy.deepcopy(step)
    parent = updated["parent"]
    checkpoint = updated["parent_checkpoint"]

    if event_type == "INTEGRITY_FAILURE":
        _require_event_keys(event, {"type"})
        for field in (
            "candidate",
            "proposal_status",
            "proposal_reason",
            "raw_patches",
            "canonical_edits",
            "applied_edits",
            "excluded_edits",
            "provenance_status",
            "provenance_audit",
            "next_parent",
        ):
            updated.pop(field, None)
        updated["status"] = "STEP_INVALID"
        updated["outcome"] = "INTEGRITY_FAILURE"
        return _result(updated, "HALT_CAMPAIGN")

    transition = LINEAR_TRANSITIONS.get((status, event_type))
    if transition is not None:
        _require_event_keys(event, {"type"})
        updated["status"], action = transition
        return _result(updated, action, parent=parent, checkpoint=checkpoint)

    if status == "PROPOSAL_RUNNING" and event_type == "CANDIDATE_FROZEN":
        required = {
            "type",
            "candidate",
            "proposal_reason",
            "raw_patches",
            "canonical_edits",
            "applied_edits",
            "excluded_edits",
            "provenance_status",
            "provenance_audit",
        }
        _require_event_keys(event, required)
        candidate = _require_artifact(event["candidate"], "candidate")
        if (
            candidate["kind"] != "candidate_skill"
            or candidate["version"] != updated["candidate_id"]
        ):
            raise ControllerContractError("Candidate artifact is inconsistent.")
        for field in required - {"type"}:
            updated[field] = copy.deepcopy(event[field])
        updated["proposal_status"] = "CANDIDATE"
        updated["status"] = "CANDIDATE_FROZEN"
        return _result(
            updated,
            "RUN_CANDIDATE_SELECTION",
            parent=parent,
            checkpoint=checkpoint,
        )

    if status == "PROPOSAL_RUNNING" and event_type == "NO_CANDIDATE":
        required = {
            "type",
            "proposal_reason",
            "raw_patches",
            "canonical_edits",
            "applied_edits",
            "excluded_edits",
        }
        _require_event_keys(event, required)
        for field in required - {"type"}:
            updated[field] = copy.deepcopy(event[field])
        updated["proposal_status"] = "NO_CANDIDATE"
        updated["status"] = "STEP_COMPLETED"
        updated["outcome"] = "NO_CANDIDATE"
        updated["next_parent"] = copy.deepcopy(parent)
        return _result(
            updated,
            _next_action(
                updated["step"], updated.get("scheduled_steps", STEP_COUNT)
            ),
            parent=parent,
            checkpoint=checkpoint,
        )

    if status == "GATE_DECIDED" and event_type == "STEP_COMPLETED":
        outcome = event.get("outcome")
        if outcome not in {"ACCEPT", "REJECT"}:
            raise ControllerContractError("Gate outcome must be ACCEPT or REJECT.")
        candidate = _require_artifact(updated.get("candidate"), "candidate")
        if outcome == "ACCEPT":
            _require_event_keys(event, {"type", "outcome", "candidate_checkpoint"})
            next_parent = {
                "kind": "accepted_skill",
                "version": _accepted_version_after(parent),
                "path": candidate["path"],
            }
            next_checkpoint = _require_checkpoint(
                event["candidate_checkpoint"], next_parent
            )
        else:
            _require_event_keys(event, {"type", "outcome"})
            next_parent = parent
            next_checkpoint = checkpoint
        updated["status"] = "STEP_COMPLETED"
        updated["outcome"] = outcome
        updated["next_parent"] = copy.deepcopy(next_parent)
        return _result(
            updated,
            _next_action(
                updated["step"], updated.get("scheduled_steps", STEP_COUNT)
            ),
            parent=next_parent,
            checkpoint=next_checkpoint,
        )

    raise InvalidTransitionError(
        f"Event {event_type!r} is invalid from {status!r}."
    )
