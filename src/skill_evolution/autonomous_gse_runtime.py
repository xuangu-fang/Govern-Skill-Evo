"""Runtime ports and a no-API dry-run adapter for Autonomous GSE v0.1.

The dry-run adapter creates deterministic in-memory artifact references. It
does not call a model, browser, database, benchmark, or filesystem writer.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from src.skill_evolution.autonomous_gse_controller import (
    ControllerResult,
    reduce_step,
    register_step,
)
from src.skill_evolution.autonomous_gse_proposal import (
    BootstrapProposalOperator,
    IncrementalProposalOperator,
    LearnerRequest,
    ProposalContext,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAMPAIGN_PATH = (
    REPO_ROOT
    / "experiments/campaigns/autonomous_gse_v01/campaign_manifest.json"
)
DEFAULT_BATCH_MAP_PATH = (
    REPO_ROOT / "experiments/campaigns/autonomous_gse_v01/batch_map.json"
)

NORMAL_OUTCOMES = {
    "ACCEPT",
    "REJECT",
    "NO_CANDIDATE",
    "INVALID_PROPOSAL",
}
CANDIDATE_OUTCOMES = {"ACCEPT", "REJECT"}
PROPOSAL_STATUSES = {
    "CANDIDATE",
    "NO_CANDIDATE",
    "INVALID_PROPOSAL",
}

DRY_RUN_BOOTSTRAP_SKILL = """# SuiteCRM Operational Skill
## Planning and navigation
- Open the relevant module before editing a record.
## Execution patterns
- Before a bulk update, identify the target records and request confirmation.
## Form entry and verification
- Verify the intended field value before submission.
## Error recovery and stopping
- Stop when a required record cannot be found."""


class RuntimeContractError(ValueError):
    """Raised when an adapter violates the dry-run runtime contract."""


@dataclass(frozen=True)
class ProposalRequest:
    """The complete and isolated input visible to a Proposal operator."""

    step: int
    operator: str
    parent: dict[str, Any]
    batch_id: str
    task_ids: tuple[int, ...]
    experience: dict[str, Any]


@dataclass(frozen=True)
class ProposalResult:
    status: str
    learner_calls: int
    candidate: dict[str, Any] | None


class RuntimeAdapter(Protocol):
    """Replaceable side-effect boundary driven by the deterministic reducer."""

    mode: str

    @property
    def trace(self) -> list[dict[str, Any]]: ...

    @property
    def side_effects(self) -> dict[str, int]: ...

    def create_initial_checkpoint(
        self,
        campaign_id: str,
        parent: dict[str, Any],
        task_count: int,
    ) -> dict[str, Any]: ...

    def run_train(self, step: dict[str, Any]) -> dict[str, Any]: ...

    def validate_train(
        self,
        step: dict[str, Any],
        train_artifact: dict[str, Any],
    ) -> None: ...

    def build_experience(
        self,
        step: dict[str, Any],
        train_artifact: dict[str, Any],
    ) -> dict[str, Any]: ...

    def propose(self, request: ProposalRequest) -> ProposalResult: ...

    def run_candidate_selection(
        self,
        step: dict[str, Any],
        candidate: dict[str, Any],
        accepted_version_if_promoted: str,
        task_count: int,
    ) -> dict[str, Any]: ...

    def validate_candidate_selection(
        self,
        step: dict[str, Any],
        checkpoint: dict[str, Any],
    ) -> None: ...

    def build_evolution_summary(
        self,
        step: dict[str, Any],
        candidate_checkpoint: dict[str, Any],
    ) -> dict[str, Any]: ...

    def apply_gate(
        self,
        step: dict[str, Any],
        summary: dict[str, Any],
    ) -> str: ...


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _memory_artifact(
    kind: str,
    version: str,
    label: str,
    payload: dict[str, Any],
) -> dict[str, str]:
    return {
        "kind": kind,
        "version": version,
        "path": f"memory://autonomous_gse_dry_run/{label}.json",
        "sha256": hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
    }


def _accepted_version_after(parent: dict[str, Any]) -> str:
    return f"S{int(parent['version'][1:]) + 1}"


class DeterministicDryRunAdapter:
    """A deterministic adapter that only produces in-memory synthetic facts."""

    mode = "deterministic_no_api_dry_run"

    def __init__(self, outcomes: Sequence[str]) -> None:
        planned = tuple(outcomes)
        if len(planned) != 3 or any(
            outcome not in NORMAL_OUTCOMES for outcome in planned
        ):
            raise RuntimeContractError(
                "Dry-run outcome plan must contain exactly 3 normal outcomes."
            )
        self._outcomes = planned
        self._trace: list[dict[str, Any]] = []
        self._datasets: dict[str, dict[str, Any]] = {}
        self._skills: dict[str, str] = {}

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
        campaign_id: str,
        parent: dict[str, Any],
        task_count: int,
    ) -> dict[str, Any]:
        payload = {
            "campaign_id": campaign_id,
            "parent_sha256": parent["sha256"],
            "parent_version": parent["version"],
            "task_count": task_count,
        }
        checkpoint = _memory_artifact(
            "selection_checkpoint",
            parent["version"],
            "initial_s0_checkpoint",
            payload,
        )
        self._trace.append(
            {
                "operation": "create_initial_checkpoint",
                "step": 0,
                "parent_version": parent["version"],
                "task_count": task_count,
                "checkpoint_sha256": checkpoint["sha256"],
            }
        )
        return checkpoint

    def run_train(self, step: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "batch_id": step["batch"]["batch_id"],
            "parent_sha256": step["parent"]["sha256"],
            "step": step["step"],
            "task_ids": step["batch"]["task_ids"],
        }
        artifact = _memory_artifact(
            "train_trajectory_set",
            f"step_{step['step']:03d}",
            f"step_{step['step']:03d}_train",
            payload,
        )
        self._trace.append(
            {
                "operation": "run_train",
                "step": step["step"],
                "batch_id": step["batch"]["batch_id"],
                "task_count": len(step["batch"]["task_ids"]),
                "artifact_sha256": artifact["sha256"],
            }
        )
        return artifact

    def validate_train(
        self,
        step: dict[str, Any],
        train_artifact: dict[str, Any],
    ) -> None:
        self._trace.append(
            {
                "operation": "validate_train",
                "step": step["step"],
                "artifact_sha256": train_artifact["sha256"],
                "valid": True,
            }
        )

    def build_experience(
        self,
        step: dict[str, Any],
        train_artifact: dict[str, Any],
    ) -> dict[str, Any]:
        outcome = self._outcomes[step["step"] - 1]
        task_ids = step["batch"]["task_ids"]
        states = ["compliant_failure"] * 17
        if outcome != "NO_CANDIDATE":
            states[:2] = ["compliant_success", "violating_success"]
        experiences = [
            self._experience(f"source_{index:03d}", state)
            for index, state in enumerate(states, start=1)
        ]
        payload = {
            "schema_version": "governed_experience_0.1.0",
            "experience_count": 17,
            "state_counts": {
                state: sum(item["state"] == state for item in experiences)
                for state in (
                    "violating_failure",
                    "violating_success",
                    "compliant_failure",
                    "compliant_success",
                )
            },
            "sources": [
                {
                    "source_id": item["source_id"],
                    "task_id": task_id,
                    "path": f"memory://dry-run/train/task_{task_id}.json",
                    "sha256": f"{task_id:064x}",
                }
                for task_id, item in zip(task_ids, experiences, strict=True)
            ],
            "experiences": experiences,
            "lineage": {
                "batch_id": step["batch"]["batch_id"],
                "parent_sha256": step["parent"]["sha256"],
                "task_ids": list(task_ids),
            },
        }
        artifact = _memory_artifact(
            "governed_experience",
            f"step_{step['step']:03d}",
            f"step_{step['step']:03d}_experience",
            payload,
        )
        self._datasets[artifact["sha256"]] = copy.deepcopy(payload)
        self._trace.append(
            {
                "operation": "build_experience",
                "step": step["step"],
                "batch_id": step["batch"]["batch_id"],
                "task_count": len(step["batch"]["task_ids"]),
                "artifact_sha256": artifact["sha256"],
            }
        )
        return artifact

    @staticmethod
    def _experience(source_id: str, state: str) -> dict[str, Any]:
        successful = state in {"compliant_success", "violating_success"}
        compliant = state in {"compliant_success", "compliant_failure"}
        policy = {
            "policy_template_id": "ask_the_user",
            "category": "user_consent",
            "source": "user",
            "description": "Ask before saving.",
            "eval_type": "is_ask_the_user",
            "policy_spec": {"must_include": "Save"},
        }
        return {
            "source_id": source_id,
            "state": state,
            "goal": "Update a SuiteCRM record.",
            "actions": [
                {"step": 1, "url": "", "action": "click('Save')"}
            ],
            "task_success": successful,
            "applicable_policies": [policy],
            "process_feedback": {
                "compliant": compliant,
                "violated_policies": [] if compliant else [policy],
            },
        }

    @staticmethod
    def _bootstrap_response() -> str:
        clauses = [
            line[2:]
            for line in DRY_RUN_BOOTSTRAP_SKILL.splitlines()
            if line.startswith("- ")
        ]
        provenance = [
            {
                "clause": clause,
                "attribution": "preserve",
                "source_ids": ["source_001"],
                "policy_template_ids": [],
            }
            for clause in clauses
        ]
        return (
            f"<SKILL>\n{DRY_RUN_BOOTSTRAP_SKILL}\n</SKILL>\n"
            "<PROVENANCE_JSON>\n"
            f"{json.dumps(provenance)}\n"
            "</PROVENANCE_JSON>"
        )

    @staticmethod
    def _incremental_response(step: int) -> str:
        new_clauses = {
            2: (
                "Before committing a requested change, review the target "
                "record and the intended values."
            ),
            3: (
                "After committing a requested change, verify the target "
                "record reflects the intended values."
            ),
        }
        edits = [
            {
                "operation": "add",
                "section": "Execution patterns",
                "parent_clause": "",
                "new_clause": new_clauses[step],
                "attribution": "preserve",
                "source_ids": ["source_001"],
                "policy_template_ids": [],
            }
        ]
        return f"<EDITS_JSON>{json.dumps(edits)}</EDITS_JSON>"

    def propose(self, request: ProposalRequest) -> ProposalResult:
        outcome = self._outcomes[request.step - 1]
        self._trace.append(
            {
                "operation": "propose",
                "step": request.step,
                "operator": request.operator,
                "parent_version": request.parent["version"],
                "batch_id": request.batch_id,
                "task_ids": list(request.task_ids),
                "experience_sha256": request.experience["sha256"],
            }
        )
        dataset = self._datasets.get(request.experience["sha256"])
        if dataset is None:
            raise RuntimeContractError("Dry-run Experience payload is missing.")
        context = ProposalContext(
            candidate_id=f"epoch_001_step_{request.step:03d}_candidate",
            batch_id=request.batch_id,
            task_ids=request.task_ids,
            parent=copy.deepcopy(request.parent),
            parent_skill=self._skills.get(request.parent["sha256"]),
            experience=copy.deepcopy(request.experience),
            governed_dataset=copy.deepcopy(dataset),
        )
        operator = (
            BootstrapProposalOperator()
            if request.operator == "bootstrap"
            else IncrementalProposalOperator()
        )

        def fixture_learner(learner_request: LearnerRequest) -> str:
            if outcome == "INVALID_PROPOSAL":
                return "invalid fixture output"
            if learner_request.operator == "bootstrap":
                return self._bootstrap_response()
            return self._incremental_response(request.step)

        decision = operator.propose(context, fixture_learner)
        candidate = None
        if decision.candidate is not None:
            candidate = copy.deepcopy(decision.candidate.candidate)
            self._skills[candidate["sha256"]] = decision.candidate.skill
        return ProposalResult(
            decision.status,
            decision.learner_calls,
            candidate,
        )

    def run_candidate_selection(
        self,
        step: dict[str, Any],
        candidate: dict[str, Any],
        accepted_version_if_promoted: str,
        task_count: int,
    ) -> dict[str, Any]:
        payload = {
            "candidate_sha256": candidate["sha256"],
            "candidate_version": candidate["version"],
            "step": step["step"],
            "task_count": task_count,
        }
        checkpoint = _memory_artifact(
            "selection_checkpoint",
            accepted_version_if_promoted,
            f"step_{step['step']:03d}_candidate_checkpoint",
            payload,
        )
        self._trace.append(
            {
                "operation": "run_candidate_selection",
                "step": step["step"],
                "candidate_sha256": candidate["sha256"],
                "task_count": task_count,
                "checkpoint_sha256": checkpoint["sha256"],
            }
        )
        return checkpoint

    def validate_candidate_selection(
        self,
        step: dict[str, Any],
        checkpoint: dict[str, Any],
    ) -> None:
        self._trace.append(
            {
                "operation": "validate_candidate_selection",
                "step": step["step"],
                "checkpoint_sha256": checkpoint["sha256"],
                "valid": True,
            }
        )

    def build_evolution_summary(
        self,
        step: dict[str, Any],
        candidate_checkpoint: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "candidate_checkpoint_sha256": candidate_checkpoint["sha256"],
            "parent_checkpoint_sha256": step["parent_checkpoint"]["sha256"],
            "step": step["step"],
        }
        summary = _memory_artifact(
            "evolution_summary",
            f"step_{step['step']:03d}",
            f"step_{step['step']:03d}_evolution_summary",
            payload,
        )
        self._trace.append(
            {
                "operation": "build_evolution_summary",
                "step": step["step"],
                "artifact_sha256": summary["sha256"],
            }
        )
        return summary

    def apply_gate(
        self,
        step: dict[str, Any],
        summary: dict[str, Any],
    ) -> str:
        outcome = self._outcomes[step["step"] - 1]
        if outcome not in CANDIDATE_OUTCOMES:
            raise RuntimeContractError("Gate requires a Candidate outcome.")
        self._trace.append(
            {
                "operation": "apply_gate",
                "step": step["step"],
                "summary_sha256": summary["sha256"],
                "outcome": outcome,
            }
        )
        return outcome


def _require_artifact(
    value: Any,
    label: str,
    *,
    kind: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "kind",
        "version",
        "path",
        "sha256",
    }:
        raise RuntimeContractError(f"{label} is not a complete artifact.")
    for field in ("kind", "version", "path"):
        if not isinstance(value[field], str) or not value[field]:
            raise RuntimeContractError(f"{label}.{field} is invalid.")
    digest = value["sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise RuntimeContractError(f"{label} has an invalid SHA-256.")
    if kind is not None and value["kind"] != kind:
        raise RuntimeContractError(f"{label} must have kind {kind!r}.")
    if version is not None and value["version"] != version:
        raise RuntimeContractError(f"{label} must have version {version!r}.")
    return value


def _require_proposal_result(result: Any, step: dict[str, Any]) -> ProposalResult:
    if not isinstance(result, ProposalResult):
        raise RuntimeContractError("Proposal adapter returned an invalid result.")
    if result.status not in PROPOSAL_STATUSES:
        raise RuntimeContractError("Proposal adapter returned an invalid status.")
    if result.learner_calls not in {0, 1}:
        raise RuntimeContractError("A Step may use at most one Learner call.")
    if result.status == "CANDIDATE":
        if result.learner_calls != 1:
            raise RuntimeContractError("A Candidate requires one Learner call.")
        candidate = _require_artifact(
            result.candidate,
            "candidate",
            kind="candidate_skill",
            version=step["candidate_id"],
        )
    elif result.candidate is not None:
        raise RuntimeContractError(
            "NO_CANDIDATE and INVALID_PROPOSAL cannot return a Candidate."
        )
    return result


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
        raise RuntimeContractError("Runtime exceeded the frozen Campaign budget.")


def _reduce(step: dict[str, Any], event: dict[str, Any]) -> ControllerResult:
    return reduce_step(step, event)


def run_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: RuntimeAdapter,
) -> dict[str, Any]:
    """Drive all three Steps through one validated runtime adapter."""

    current_parent = copy.deepcopy(campaign["initial_parent"])
    selection_tasks = campaign["selection"]["tasks"]
    current_checkpoint = _require_artifact(
        adapter.create_initial_checkpoint(
            campaign["campaign_id"],
            copy.deepcopy(current_parent),
            selection_tasks,
        ),
        "initial checkpoint",
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

    for step_number in range(1, 4):
        step = register_step(
            campaign,
            batch_map,
            step=step_number,
            parent=current_parent,
            parent_checkpoint=current_checkpoint,
        )
        step = _reduce(step, {"type": "TRAIN_STARTED"}).step
        train_artifact = _require_artifact(
            adapter.run_train(copy.deepcopy(step)),
            "Train artifact",
            kind="train_trajectory_set",
        )
        usage["train_trajectories"] += len(step["batch"]["task_ids"])
        usage["total_trajectories"] += len(step["batch"]["task_ids"])
        _check_budget(campaign, usage)

        step = _reduce(step, {"type": "TRAIN_COMPLETED"}).step
        adapter.validate_train(copy.deepcopy(step), copy.deepcopy(train_artifact))
        step = _reduce(step, {"type": "TRAIN_VALIDATED"}).step
        experience = _require_artifact(
            adapter.build_experience(
                copy.deepcopy(step), copy.deepcopy(train_artifact)
            ),
            "Experience artifact",
            kind="governed_experience",
        )
        step = _reduce(step, {"type": "EXPERIENCE_FROZEN"}).step
        step = _reduce(step, {"type": "PROPOSAL_STARTED"}).step

        proposal_request = ProposalRequest(
            step=step_number,
            operator=step["proposal_operator"],
            parent=copy.deepcopy(step["parent"]),
            batch_id=step["batch"]["batch_id"],
            task_ids=tuple(step["batch"]["task_ids"]),
            experience=copy.deepcopy(experience),
        )
        proposal = _require_proposal_result(
            adapter.propose(proposal_request), step
        )
        usage["learner_calls"] += proposal.learner_calls
        _check_budget(campaign, usage)

        if proposal.status != "CANDIDATE":
            result = _reduce(step, {"type": proposal.status})
        else:
            usage["candidates"] += 1
            candidate = copy.deepcopy(proposal.candidate)
            step = _reduce(
                step,
                {"type": "CANDIDATE_FROZEN", "candidate": candidate},
            ).step
            step = _reduce(
                step, {"type": "CANDIDATE_SELECTION_STARTED"}
            ).step
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
            )
            step = _reduce(
                step, {"type": "EVOLUTION_SUMMARY_FROZEN"}
            ).step
            outcome = adapter.apply_gate(
                copy.deepcopy(step), copy.deepcopy(summary)
            )
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
        if result.accepted_parent is None or (
            result.accepted_parent_checkpoint is None
        ):
            raise RuntimeContractError("Completed Step lost accepted state.")
        current_parent = result.accepted_parent
        current_checkpoint = result.accepted_parent_checkpoint

    _check_budget(campaign, usage)
    return {
        "schema_version": "autonomous_gse_runtime_report_0.1.0",
        "campaign_id": campaign["campaign_id"],
        "mode": adapter.mode,
        "status": "COMPLETED",
        "steps": completed_steps,
        "final_parent": copy.deepcopy(current_parent),
        "final_parent_checkpoint": copy.deepcopy(current_checkpoint),
        "budget_usage": usage,
        "side_effects": copy.deepcopy(adapter.side_effects),
        "runtime_trace": copy.deepcopy(adapter.trace),
    }


def run_dry_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: RuntimeAdapter,
) -> dict[str, Any]:
    """Drive all Steps and prove that the adapter produced no side effects."""

    if any(adapter.side_effects.values()):
        raise RuntimeContractError("Dry-run adapter must declare zero side effects.")
    report = run_campaign(campaign, batch_map, adapter)
    if any(adapter.side_effects.values()):
        raise RuntimeContractError("Dry run recorded a forbidden side effect.")
    report["schema_version"] = "autonomous_gse_dry_run_0.1.0"
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the deterministic Autonomous GSE v0.1 no-API dry run."
    )
    parser.add_argument(
        "--outcomes",
        default="ACCEPT,REJECT,NO_CANDIDATE",
        help="Exactly three comma-separated dry-run outcomes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    outcomes = tuple(value.strip() for value in args.outcomes.split(","))
    campaign = json.loads(DEFAULT_CAMPAIGN_PATH.read_text(encoding="utf-8"))
    batch_map = json.loads(DEFAULT_BATCH_MAP_PATH.read_text(encoding="utf-8"))
    report = run_dry_campaign(
        campaign,
        batch_map,
        DeterministicDryRunAdapter(outcomes),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
