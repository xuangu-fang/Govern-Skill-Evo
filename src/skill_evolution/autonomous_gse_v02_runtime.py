"""In-memory, no-API dry-run runtime for Autonomous GSE v0.2."""

from __future__ import annotations

import copy
import json
from typing import Any, Sequence

from src.learners.stwebagentbench.generate_bounded_skill_v02 import (
    call_bounded_learner,
)
from src.skill_evolution.autonomous_gse_v02_controller import (
    ControllerResult,
    reduce_step,
    register_step,
)
from src.skill_evolution.autonomous_gse_v02_proposal import (
    BoundedEditProposalOperator,
    LearnerRequest,
    ProposalContext,
)


NORMAL_OUTCOMES = {"ACCEPT", "REJECT", "NO_CANDIDATE"}
CANDIDATE_OUTCOMES = {"ACCEPT", "REJECT"}


class RuntimeContractError(ValueError):
    """Raised when the deterministic dry-run contract is violated."""


def _memory_artifact(kind: str, version: str, label: str) -> dict[str, str]:
    suffix = "md" if kind in {"candidate_skill", "accepted_skill"} else "json"
    return {
        "kind": kind,
        "version": version,
        "path": f"memory://autonomous_gse_v02/{label}.{suffix}",
    }


def _accepted_version_after(parent: dict[str, Any]) -> str:
    return f"S{int(parent['version'][1:]) + 1}"


class DeterministicDryRunAdapter:
    """Synthetic in-memory facts for exercising the real v0.2 loop."""

    mode = "deterministic_no_api_no_write_dry_run"

    def __init__(
        self,
        outcomes: Sequence[str],
        *,
        initial_skill: str,
        unverified_steps: Sequence[int] = (),
    ) -> None:
        planned = tuple(outcomes)
        if len(planned) != 3 or any(item not in NORMAL_OUTCOMES for item in planned):
            raise RuntimeContractError(
                "Dry-run outcome plan must contain exactly 3 normal outcomes."
            )
        unverified = frozenset(unverified_steps)
        if any(
            not isinstance(step, int)
            or isinstance(step, bool)
            or step not in {1, 2, 3}
            or planned[step - 1] not in CANDIDATE_OUTCOMES
            for step in unverified
        ):
            raise RuntimeContractError(
                "UNVERIFIED steps must identify planned Candidate outcomes."
            )
        if not isinstance(initial_skill, str) or not initial_skill.strip():
            raise RuntimeContractError("Dry run requires explicit S0 Skill text.")
        self._outcomes = planned
        self._unverified_steps = unverified
        self._initial_skill = initial_skill
        self._skills: dict[str, str] = {}
        self._trace: list[dict[str, Any]] = []

    @property
    def trace(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._trace)

    @property
    def side_effects(self) -> dict[str, int]:
        return {
            "api_calls": 0,
            "browser_calls": 0,
            "database_calls": 0,
            "filesystem_writes": 0,
        }

    def create_initial_checkpoint(
        self,
        parent: dict[str, Any],
        task_count: int,
    ) -> dict[str, Any]:
        self._skills[parent["path"]] = self._initial_skill
        checkpoint = _memory_artifact(
            "selection_checkpoint", parent["version"], "initial_s0_selection"
        )
        self._trace.append(
            {
                "operation": "create_initial_checkpoint",
                "step": 0,
                "parent_version": parent["version"],
                "task_count": task_count,
                "checkpoint_path": checkpoint["path"],
            }
        )
        return checkpoint

    def run_train(self, step: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        self._trace.append(
            {
                "operation": "run_train",
                "step": step["step"],
                "batch_id": step["batch"]["batch_id"],
                "task_ids": list(step["batch"]["task_ids"]),
            }
        )
        return (
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

    def skill_for_parent(self, parent: dict[str, Any]) -> str:
        try:
            return self._skills[parent["path"]]
        except KeyError as error:
            raise RuntimeContractError("Accepted Parent Skill is missing.") from error

    def learner_response(self, step: dict[str, Any], request: LearnerRequest) -> str:
        outcome = self._outcomes[step["step"] - 1]
        self._trace.append(
            {
                "operation": "propose",
                "step": step["step"],
                "operator": step["proposal_operator"],
                "parent_version": step["parent"]["version"],
                "batch_id": step["batch"]["batch_id"],
                "task_ids": list(step["batch"]["task_ids"]),
                "maximum_edits": request.maximum_edits,
                "allowed_source_ids": list(request.allowed_source_ids),
                "allowed_repair_policy_ids_by_source": {
                    source_id: list(policy_ids)
                    for source_id, policy_ids in (
                        request.allowed_repair_policy_ids_by_source.items()
                    )
                },
            }
        )
        if outcome == "NO_CANDIDATE":
            return "<EDITS_JSON>[]</EDITS_JSON>"

        clauses = {
            1: "Confirm the current record context before acting.",
            2: "Review the intended values before submitting a change.",
            3: "Verify the saved record reflects the requested values.",
        }
        edit = {
            "operation": "add",
            "section": "Planning and navigation",
            "target_clause": "",
            "text": clauses[step["step"]],
            "reason": "Use current-batch successful evidence.",
            "source_ids": [
                "unknown_source"
                if step["step"] in self._unverified_steps
                else "source_001"
            ],
            "repair_policy_ids": [],
        }
        return f"<EDITS_JSON>{json.dumps([edit])}</EDITS_JSON>"

    def learner_call(
        self,
        step: dict[str, Any],
        request: LearnerRequest,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str, None]:
        if not system_prompt or not user_prompt:
            raise RuntimeContractError("Unified Learner Prompt is empty.")
        return self.learner_response(step, request), model.removeprefix("openai/"), None

    def record_candidate(
        self,
        step: dict[str, Any],
        candidate_skill: str,
    ) -> dict[str, Any]:
        candidate = _memory_artifact(
            "candidate_skill",
            step["candidate_id"],
            f"step_{step['step']:03d}_candidate",
        )
        self._skills[candidate["path"]] = candidate_skill
        self._trace.append(
            {
                "operation": "record_candidate_in_memory",
                "step": step["step"],
                "candidate_path": candidate["path"],
            }
        )
        return candidate

    def record_proposal(
        self,
        step: dict[str, Any],
        decision: Any,
        candidate: dict[str, Any] | None,
    ) -> None:
        del step, decision, candidate

    def run_candidate_selection(
        self,
        step: dict[str, Any],
        candidate: dict[str, Any],
        promoted_version: str,
        task_count: int,
    ) -> dict[str, Any]:
        checkpoint = _memory_artifact(
            "selection_checkpoint",
            promoted_version,
            f"step_{step['step']:03d}_candidate_selection",
        )
        self._trace.append(
            {
                "operation": "run_candidate_selection",
                "step": step["step"],
                "candidate_path": candidate["path"],
                "task_count": task_count,
                "checkpoint_path": checkpoint["path"],
            }
        )
        return checkpoint

    def validate_candidate_selection(
        self,
        step: dict[str, Any],
        checkpoint: dict[str, Any],
    ) -> None:
        del step, checkpoint

    def build_evolution_summary(
        self,
        step: dict[str, Any],
        candidate_checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        return _memory_artifact(
            "evolution_summary",
            f"step_{step['step']:03d}",
            f"step_{step['step']:03d}_evolution_summary",
        )

    def apply_gate(
        self,
        step: dict[str, Any],
        summary: dict[str, Any],
    ) -> str:
        del summary
        outcome = self._outcomes[step["step"] - 1]
        if outcome not in CANDIDATE_OUTCOMES:
            raise RuntimeContractError("Gate requires a Candidate outcome.")
        self._trace.append(
            {
                "operation": "apply_gate",
                "step": step["step"],
                "outcome": outcome,
            }
        )
        return outcome


def _require_artifact(
    value: Any,
    label: str,
    *,
    kind: str,
    version: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"kind", "version", "path"}:
        raise RuntimeContractError(f"{label} is not a complete artifact.")
    if value["kind"] != kind:
        raise RuntimeContractError(f"{label} must have kind {kind!r}.")
    if version is not None and value["version"] != version:
        raise RuntimeContractError(f"{label} has the wrong version.")
    if any(not isinstance(value[field], str) or not value[field] for field in value):
        raise RuntimeContractError(f"{label} fields must be non-empty text.")
    return copy.deepcopy(value)


def _reduce(step: dict[str, Any], event: dict[str, Any]) -> ControllerResult:
    return reduce_step(step, event)


def _check_budget(campaign: dict[str, Any], usage: dict[str, int]) -> None:
    budget = campaign["budget"]
    if (
        usage["train_trajectories"] > budget["train_trajectories"]
        or usage["initial_selection_trajectories"]
        > budget["initial_selection_trajectories"]
        or usage["candidate_selection_trajectories"]
        > budget["maximum_candidate_selection_trajectories"]
        or usage["total_trajectories"] > budget["maximum_total_trajectories"]
        or usage["candidates"] > budget["maximum_candidates"]
        or usage["learner_calls"] > budget["maximum_learner_calls"]
        or usage["test_trajectories"] != 0
    ):
        raise RuntimeContractError("Runtime exceeded the Campaign budget.")


def _candidate_event(
    candidate: dict[str, Any],
    decision: Any,
) -> dict[str, Any]:
    return {
        "type": "CANDIDATE_FROZEN",
        "candidate": copy.deepcopy(candidate),
        "proposal_reason": copy.deepcopy(decision.proposal_reason),
        "proposed_edits": copy.deepcopy(decision.proposed_edits),
        "selected_edits": copy.deepcopy(decision.selected_edits),
        "excluded_edits": copy.deepcopy(decision.excluded_edits),
        "provenance_status": decision.provenance_status,
        "provenance_audit": copy.deepcopy(decision.provenance_audit),
    }


def _no_candidate_event(decision: Any) -> dict[str, Any]:
    return {
        "type": "NO_CANDIDATE",
        "proposal_reason": copy.deepcopy(decision.proposal_reason),
        "proposed_edits": copy.deepcopy(decision.proposed_edits),
        "selected_edits": copy.deepcopy(decision.selected_edits),
        "excluded_edits": copy.deepcopy(decision.excluded_edits),
    }


def run_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """Run the shared three-Step v0.2 state machine through an adapter."""

    current_parent = copy.deepcopy(campaign["initial_parent"])
    selection_tasks = campaign["selection"]["tasks"]
    current_checkpoint = _require_artifact(
        adapter.create_initial_checkpoint(current_parent, selection_tasks),
        "Initial checkpoint",
        kind="selection_checkpoint",
        version=current_parent["version"],
    )
    usage = {
        "train_trajectories": 0,
        "initial_selection_trajectories": selection_tasks,
        "candidate_selection_trajectories": 0,
        "total_trajectories": selection_tasks,
        "candidates": 0,
        "learner_calls": 0,
        "test_trajectories": 0,
    }
    completed_steps: list[dict[str, Any]] = []
    operator = BoundedEditProposalOperator()

    for step_number in range(1, 4):
        step = register_step(
            campaign,
            batch_map,
            step=step_number,
            parent=current_parent,
            parent_checkpoint=current_checkpoint,
        )
        step = _reduce(step, {"type": "TRAIN_STARTED"}).step
        evidence = adapter.run_train(copy.deepcopy(step))
        usage["train_trajectories"] += len(step["batch"]["task_ids"])
        usage["total_trajectories"] += len(step["batch"]["task_ids"])
        _check_budget(campaign, usage)

        step = _reduce(step, {"type": "TRAIN_COMPLETED"}).step
        step = _reduce(step, {"type": "TRAIN_VALIDATED"}).step
        step = _reduce(step, {"type": "EXPERIENCE_FROZEN"}).step
        step = _reduce(step, {"type": "PROPOSAL_STARTED"}).step

        context = ProposalContext(
            candidate_id=step["candidate_id"],
            parent_skill=adapter.skill_for_parent(step["parent"]),
            current_batch_success_evidence=copy.deepcopy(evidence),
        )
        decision = operator.propose(
            context,
            lambda request, current=copy.deepcopy(step): call_bounded_learner(
                request,
                learner_call=lambda model, system_prompt, user_prompt: (
                    adapter.learner_call(
                        current,
                        request,
                        model,
                        system_prompt,
                        user_prompt,
                    )
                ),
            ),
        )
        usage["learner_calls"] += decision.learner_calls
        _check_budget(campaign, usage)

        if decision.proposal_status == "NO_CANDIDATE":
            adapter.record_proposal(copy.deepcopy(step), decision, None)
            result = _reduce(step, _no_candidate_event(decision))
        else:
            if decision.proposal_status != "CANDIDATE" or (
                decision.candidate_skill is None
            ):
                raise RuntimeContractError("Proposal returned an invalid status.")
            usage["candidates"] += 1
            candidate = _require_artifact(
                adapter.record_candidate(step, decision.candidate_skill),
                "Candidate",
                kind="candidate_skill",
                version=step["candidate_id"],
            )
            adapter.record_proposal(
                copy.deepcopy(step), decision, copy.deepcopy(candidate)
            )
            step = _reduce(step, _candidate_event(candidate, decision)).step
            step = _reduce(step, {"type": "CANDIDATE_SELECTION_STARTED"}).step
            promoted_version = _accepted_version_after(step["parent"])
            candidate_checkpoint = _require_artifact(
                adapter.run_candidate_selection(
                    copy.deepcopy(step),
                    copy.deepcopy(candidate),
                    promoted_version,
                    selection_tasks,
                ),
                "Candidate checkpoint",
                kind="selection_checkpoint",
                version=promoted_version,
            )
            usage["candidate_selection_trajectories"] += selection_tasks
            usage["total_trajectories"] += selection_tasks
            _check_budget(campaign, usage)

            adapter.validate_candidate_selection(
                copy.deepcopy(step), copy.deepcopy(candidate_checkpoint)
            )
            step = _reduce(step, {"type": "SELECTION_VALIDATED"}).step
            summary = _require_artifact(
                adapter.build_evolution_summary(
                    copy.deepcopy(step), copy.deepcopy(candidate_checkpoint)
                ),
                "Evolution summary",
                kind="evolution_summary",
                version=f"step_{step['step']:03d}",
            )
            step = _reduce(step, {"type": "EVOLUTION_SUMMARY_FROZEN"}).step
            outcome = adapter.apply_gate(copy.deepcopy(step), summary)
            if outcome not in CANDIDATE_OUTCOMES:
                raise RuntimeContractError("Gate must return ACCEPT or REJECT.")
            step = _reduce(step, {"type": "GATE_DECIDED"}).step
            completion_event: dict[str, Any] = {
                "type": "STEP_COMPLETED",
                "outcome": outcome,
            }
            if outcome == "ACCEPT":
                completion_event["candidate_checkpoint"] = candidate_checkpoint
            result = _reduce(step, completion_event)

        completed_steps.append(copy.deepcopy(result.step))
        if result.accepted_parent is None or result.accepted_parent_checkpoint is None:
            raise RuntimeContractError("Completed Step lost accepted state.")
        current_parent = result.accepted_parent
        current_checkpoint = result.accepted_parent_checkpoint

    _check_budget(campaign, usage)
    return {
        "schema_version": "autonomous_gse_runtime_report_0.2.0",
        "campaign_id": campaign["campaign_id"],
        "mode": adapter.mode,
        "status": "COMPLETED",
        "steps": completed_steps,
        "final_parent": copy.deepcopy(current_parent),
        "final_parent_checkpoint": copy.deepcopy(current_checkpoint),
        "budget_usage": usage,
        "side_effects": copy.deepcopy(adapter.side_effects),
        "runtime_trace": adapter.trace,
    }


def run_dry_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: DeterministicDryRunAdapter,
) -> dict[str, Any]:
    """Run all three v0.2 Steps entirely in memory."""

    if any(adapter.side_effects.values()):
        raise RuntimeContractError("Dry-run adapter must declare zero side effects.")
    report = run_campaign(campaign, batch_map, adapter)
    if any(adapter.side_effects.values()):
        raise RuntimeContractError("Dry run recorded a forbidden side effect.")
    report["schema_version"] = "autonomous_gse_dry_run_0.2.0"
    return report
