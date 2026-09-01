"""Phase 5 serial orchestration for Autonomous GSE v0.14."""

from __future__ import annotations

import copy
import json
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v14_proposal import DiagnosisContractError
from src.skill_evolution.distributional_gate_v14 import build_distributional_gate_decision
from src.skill_evolution.joint_distribution_v14 import build_joint_distribution_report
from src.skill_evolution.regression_analysis_v14 import analyze_regressions
from src.skill_evolution.target_behavior_analysis_v14 import analyze_target_behaviors

PROMOTION_SOURCE = "distributional_gate_only"
REPO_ROOT = Path(__file__).resolve().parents[2]


class OrchestrationContractError(ValueError):
    """Raised when Phase 5 state or artifact lineage is invalid."""


def resolve_skill_artifact_path(skill_path_identity: str) -> Path:
    """Resolve an identity path for I/O without changing the identity string."""

    path = Path(skill_path_identity)
    return path if path.is_absolute() else REPO_ROOT / path


def learner_skill_text(artifact_text: str) -> str:
    """Convert canonical artifact text to the frozen learner's internal title."""

    return artifact_text.replace(
        "# Operational Skill", "# SuiteCRM Operational Skill", 1,
    )


def canonical_skill_text(learner_text: str) -> str:
    """Convert learner output back to the canonical artifact title."""

    return learner_text.replace(
        "# SuiteCRM Operational Skill", "# Operational Skill", 1,
    )


@dataclass(frozen=True)
class EvolutionServices:
    parent_rollouts: Callable[[int, dict[str, Any], dict[str, str]], dict[str, Any]]
    propose: Callable[[ProposalContext, int], Any]
    candidate_monitor: Callable[[dict[str, str]], dict[str, Any]]
    candidate_replay: Callable[[int, dict[str, Any], dict[str, str]], dict[str, Any]]
    target_behavior: Callable[..., dict[str, Any]] = analyze_target_behaviors
    regression: Callable[..., dict[str, Any]] = analyze_regressions
    joint_report: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = build_joint_distribution_report
    gate: Callable[[dict[str, Any]], dict[str, Any]] = build_distributional_gate_decision


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _skill_identity(value: dict[str, Any]) -> dict[str, str]:
    if not isinstance(value, dict):
        raise OrchestrationContractError("Skill identity must be a mapping.")
    skill_id = value.get("skill_id")
    skill_version = value.get("skill_version", value.get("version"))
    skill_path = value.get("skill_path", value.get("path"))
    if skill_id is None and skill_version == "S0":
        skill_id = "S0"
    result = {
        "skill_id": skill_id, "skill_version": skill_version, "skill_path": skill_path,
    }
    if any(not isinstance(item, str) or not item for item in result.values()):
        raise OrchestrationContractError("Skill identity fields must be non-empty strings.")
    return result


def _validate_rollout_bundle(
    bundle: dict[str, Any], *, batch: dict[str, Any], require_evidence: bool,
) -> None:
    rows = bundle.get("rows")
    evidence = bundle.get("evidence")
    expected = {
        (domain, task_id, rollout_index)
        for tagged in batch["task_ids"]
        for domain, task_id in (tagged.split(":", 1),)
        for rollout_index in (1, 2, 3)
    }
    if not isinstance(rows, list) or len(rows) != 60:
        raise OrchestrationContractError("Current-batch rollout bundle must contain 60 rows.")
    actual = {
        (row.get("domain"), str(row.get("task_id")), row.get("rollout_index"))
        for row in rows if isinstance(row, dict)
    }
    if actual != expected or len(actual) != len(rows):
        raise OrchestrationContractError("Current-batch rollout lineage is incomplete.")
    if require_evidence and (not isinstance(evidence, list) or len(evidence) != 60):
        raise OrchestrationContractError("Learning Path must contain 60 governed evidence rows.")
    if require_evidence:
        lineage_fields = (
            "source_id", "domain", "task_id", "rollout_index", "rollout_seed", "state",
        )
        if any(
            not isinstance(item, dict)
            or any(item.get(field) != row.get(field) for field in lineage_fields)
            for row, item in zip(rows, evidence, strict=True)
        ):
            raise OrchestrationContractError("Learning Path rows/evidence lineage drifted.")


def _validate_matched_replay(
    parent_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]],
) -> None:
    def indexed(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Any]]:
        return {
            (row.get("domain"), str(row.get("task_id")), row.get("rollout_index")): row
            for row in rows
        }

    parent, candidate = indexed(parent_rows), indexed(candidate_rows)
    if len(parent) != len(parent_rows) or len(candidate) != len(candidate_rows) or set(parent) != set(candidate):
        raise OrchestrationContractError("Parent/Candidate current-batch replay is not matched.")
    if any(parent[key].get("rollout_seed") != candidate[key].get("rollout_seed") for key in parent):
        raise OrchestrationContractError("Parent/Candidate current-batch replay seeds drifted.")


def _immutable_candidate(
    *, root: Path, step: int, candidate_text: str,
) -> dict[str, str]:
    identity = f"candidate_step_{step:02d}"
    path = root / "steps" / f"step_{step:02d}" / "candidate_skill.md"
    artifact_text = canonical_skill_text(candidate_text)
    if path.exists() and path.read_text(encoding="utf-8") != artifact_text:
        raise OrchestrationContractError("Immutable Candidate artifact would be overwritten.")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(artifact_text, encoding="utf-8")
    return {"skill_id": identity, "skill_version": identity, "skill_path": path.as_posix()}


def _monitor_path(root: Path, skill: dict[str, str]) -> str:
    return (root / "monitor_results" / f"{skill['skill_id']}.json").as_posix()


def _load_cached_proposal(
    path: Path, *, batch_id: str, parent: dict[str, str],
) -> Any | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("batch_id") != batch_id or value.get("parent_skill") != parent:
        raise OrchestrationContractError("Cached Proposal lineage drifted.")
    status = value.get("proposal_status")
    candidate_skill = value.get("candidate_skill")
    if status not in {"CANDIDATE", "NO_CANDIDATE"} or (
        status == "CANDIDATE" and (not isinstance(candidate_skill, str) or not candidate_skill)
    ) or (status == "NO_CANDIDATE" and candidate_skill is not None):
        raise OrchestrationContractError("Cached Proposal artifact is invalid.")
    return SimpleNamespace(
        proposal_status=status, proposal_reason=copy.deepcopy(value.get("proposal_reason")),
        candidate_skill=candidate_skill,
        diagnoses=copy.deepcopy(value.get("diagnoses", [])),
        applied_edits=copy.deepcopy(value.get("canonical_edits", [])),
    )


def _analysis_edits(proposal: Any) -> list[dict[str, Any]]:
    """Expand v13 patch lineage into explicit Diagnosis lineage for logging."""

    edits = copy.deepcopy(proposal.applied_edits)
    if all(
        isinstance(edit.get("derived_from_diagnosis_ids"), list)
        and edit["derived_from_diagnosis_ids"]
        for edit in edits
    ):
        return edits
    signals = {
        item.get("patch_id"): item
        for item in getattr(proposal, "raw_patches", []) if isinstance(item, dict)
    }
    for edit in edits:
        patch_ids = edit.get("derived_from_patch_ids")
        if not isinstance(patch_ids, list) or not patch_ids:
            raise OrchestrationContractError("Canonical edit patch lineage is invalid.")
        try:
            diagnoses = [signals[patch_id]["diagnosis_id"] for patch_id in patch_ids]
        except (KeyError, TypeError) as error:
            raise OrchestrationContractError("Canonical edit Diagnosis lineage is invalid.") from error
        edit["derived_from_diagnosis_ids"] = list(dict.fromkeys(diagnoses))
    return edits


def run_evolution_step(
    *, step: int, batch: dict[str, Any], parent: dict[str, str],
    parent_monitor: dict[str, Any], campaign: dict[str, Any],
    services: EvolutionServices, artifact_root: Path,
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    """Run one selection-first Step; explanation can never change its decision."""

    if step not in {1, 2, 3} or batch.get("batch_id") != f"batch_{step}":
        raise OrchestrationContractError("Evolution Step does not match its frozen batch.")
    step_root = artifact_root / "steps" / f"step_{step:02d}"
    proposal_path = step_root / "proposal.json"
    try:
        parent_bundle = services.parent_rollouts(step, copy.deepcopy(batch), copy.deepcopy(parent))
        _validate_rollout_bundle(parent_bundle, batch=batch, require_evidence=True)
        proposal = _load_cached_proposal(
            proposal_path, batch_id=batch["batch_id"], parent=parent,
        )
        if proposal is None:
            parent_text = learner_skill_text(resolve_skill_artifact_path(
                parent["skill_path"],
            ).read_text(encoding="utf-8"))
            context = ProposalContext(
                candidate_id=f"candidate_step_{step:02d}", parent_skill=parent_text,
                current_batch_governed_evidence=tuple(copy.deepcopy(parent_bundle["evidence"])),
            )
            proposal = services.propose(context, step)
    except DiagnosisContractError as error:
        contract_error_path = step_root / "diagnosis_contract_error.json"
        _write_json(contract_error_path, {
            "schema_version": "autonomous_gse_diagnosis_contract_error_0.14.0",
            "campaign_id": campaign.get("campaign_id", "autonomous_gse_v14"),
            "step": step, "batch_id": batch["batch_id"], "error_code": error.code,
            "invalid_diagnosis_ids": list(error.invalid_diagnosis_ids),
            "diagnoses": [item.as_dict() for item in error.validations],
        })
        _write_json(step_root / "execution_error.json", {
            "stage": "learning_path", "error_type": type(error).__name__,
            "error_message": str(error), "traceback": traceback.format_exc(),
            "diagnosis_contract_error_path": contract_error_path.as_posix(),
        })
        raise
    except Exception as error:
        _write_json(step_root / "execution_error.json", {
            "stage": "learning_path", "error_type": type(error).__name__,
            "error_message": str(error), "traceback": traceback.format_exc(),
        })
        raise

    if proposal.proposal_status not in {"CANDIDATE", "NO_CANDIDATE"} or (
        proposal.proposal_status == "CANDIDATE"
        and (not isinstance(proposal.candidate_skill, str) or not proposal.candidate_skill)
    ) or (
        proposal.proposal_status == "NO_CANDIDATE" and proposal.candidate_skill is not None
    ):
        error = OrchestrationContractError("Proposal result is neither a valid Candidate nor legal no-op.")
        _write_json(step_root / "execution_error.json", {
            "stage": "proposal_contract", "error_type": type(error).__name__,
            "error_message": str(error),
        })
        raise error
    canonical_edits = (
        _analysis_edits(proposal) if proposal.proposal_status == "CANDIDATE" else []
    )
    _write_json(proposal_path, {
        "batch_id": batch["batch_id"], "parent_skill": copy.deepcopy(parent),
        "proposal_status": proposal.proposal_status,
        "proposal_reason": copy.deepcopy(proposal.proposal_reason),
        "diagnoses": copy.deepcopy(getattr(proposal, "diagnoses", [])),
        "canonical_edits": copy.deepcopy(canonical_edits),
        "candidate_skill": proposal.candidate_skill,
    })
    if proposal.proposal_status == "NO_CANDIDATE":
        summary = {
            "schema_version": "autonomous_gse_step_summary_0.14.0",
            "step": step, "batch_id": batch["batch_id"], "parent_skill": copy.deepcopy(parent),
            "candidate_skill": None, "proposal_status": proposal.proposal_status,
            "selection": {
                "gate_executed": False, "decision": "RETAIN", "reason": "no_candidate_update",
            },
            "explanation": {
                "current_batch_replay_status": "not_run",
                "target_behavior_status": "not_run", "regression_analysis_status": "not_run",
            },
            "next_parent": copy.deepcopy(parent),
            "next_parent_monitor_result_path": _monitor_path(artifact_root, parent),
            "promotion_source": PROMOTION_SOURCE,
            "artifact_paths": {
                "proposal": proposal_path.as_posix(),
                "step_summary": (step_root / "step_summary.json").as_posix(),
            },
        }
        _write_json(step_root / "step_summary.json", summary)
        (step_root / "execution_error.json").unlink(missing_ok=True)
        (step_root / "diagnosis_contract_error.json").unlink(missing_ok=True)
        return summary, copy.deepcopy(parent), parent_monitor

    candidate = _immutable_candidate(
        root=artifact_root, step=step, candidate_text=proposal.candidate_skill,
    )
    selection_root = step_root / "selection"
    try:
        candidate_monitor = services.candidate_monitor(copy.deepcopy(candidate))
        joint = services.joint_report(parent_monitor, candidate_monitor)
        gate = services.gate(joint)
        decision = gate.get("gate", {}).get("decision")
        if decision not in {"ACCEPT", "RETAIN"}:
            raise OrchestrationContractError("Distributional Gate decision is invalid.")
        joint_path = selection_root / "joint_distribution.json"
        gate_path = selection_root / "distributional_gate.json"
        _write_json(joint_path, joint)
        _write_json(gate_path, gate)
        next_parent = candidate if decision == "ACCEPT" else parent
        next_monitor = candidate_monitor if decision == "ACCEPT" else parent_monitor
        selection = {
            "schema_version": "autonomous_gse_selection_decision_0.14.0",
            "step": step, "batch_id": batch["batch_id"],
            "parent_skill": copy.deepcopy(parent), "candidate_skill": copy.deepcopy(candidate),
            "parent_monitor_result_path": _monitor_path(artifact_root, parent),
            "candidate_monitor_result_path": _monitor_path(artifact_root, candidate),
            "joint_distribution_path": joint_path.as_posix(),
            "distributional_gate_path": gate_path.as_posix(),
            "gate_executed": True, "gate_decision": decision,
            "positive_probability": gate["bootstrap"]["positive_probability"],
            "threshold": gate["gate"]["positive_probability_threshold"],
            "promotion_source": PROMOTION_SOURCE,
        }
        _write_json(selection_root / "selection_decision.json", selection)
    except Exception as error:
        _write_json(selection_root / "selection_error.json", {
            "stage": "selection_path", "error_type": type(error).__name__,
            "error_message": str(error), "traceback": traceback.format_exc(),
        })
        raise

    explanation = {
        "current_batch_replay_status": "not_run",
        "target_behavior_status": "not_run", "regression_analysis_status": "not_run",
    }
    explanation_root = step_root / "explanation"
    try:
        candidate_bundle = services.candidate_replay(step, copy.deepcopy(batch), copy.deepcopy(candidate))
        _validate_rollout_bundle(candidate_bundle, batch=batch, require_evidence=False)
        _validate_matched_replay(parent_bundle["rows"], candidate_bundle["rows"])
        explanation["current_batch_replay_status"] = "complete"
    except Exception as error:
        explanation["current_batch_replay_status"] = "error"
        _write_json(explanation_root / "current_batch_replay_error.json", {
            "error_type": type(error).__name__, "error_message": str(error),
            "traceback": traceback.format_exc(),
        })
        candidate_bundle = None

    if candidate_bundle is not None:
        analysis_inputs = (
            copy.deepcopy(canonical_edits),
            copy.deepcopy(getattr(proposal, "diagnoses", [])),
            copy.deepcopy(parent_bundle["rows"]), copy.deepcopy(candidate_bundle["rows"]),
        )
        try:
            target = services.target_behavior(*analysis_inputs)
            _write_json(explanation_root / "target_behavior_analysis.json", target)
            explanation["target_behavior_status"] = "complete"
        except Exception as error:
            explanation["target_behavior_status"] = "error"
            _write_json(explanation_root / "target_behavior_analysis_error.json", {
                "error_type": type(error).__name__, "error_message": str(error),
                "traceback": traceback.format_exc(),
            })
        try:
            regression = services.regression(
                analysis_inputs[2], analysis_inputs[3], analysis_inputs[0],
            )
            _write_json(explanation_root / "regression_analysis.json", regression)
            explanation["regression_analysis_status"] = "complete"
        except Exception as error:
            explanation["regression_analysis_status"] = "error"
            _write_json(explanation_root / "regression_analysis_error.json", {
                "error_type": type(error).__name__, "error_message": str(error),
                "traceback": traceback.format_exc(),
            })

    summary = {
        "schema_version": "autonomous_gse_step_summary_0.14.0",
        "step": step, "batch_id": batch["batch_id"], "parent_skill": copy.deepcopy(parent),
        "candidate_skill": copy.deepcopy(candidate), "proposal_status": proposal.proposal_status,
        "selection": {
            "gate_executed": True, "decision": decision,
            "positive_probability": selection["positive_probability"],
            "threshold": selection["threshold"],
        },
        "explanation": explanation, "next_parent": copy.deepcopy(next_parent),
        "next_parent_monitor_result_path": _monitor_path(artifact_root, next_parent),
        "promotion_source": PROMOTION_SOURCE,
        "artifact_paths": {
            "proposal": proposal_path.as_posix(),
            "candidate_skill": candidate["skill_path"],
            "candidate_monitor_result": selection["candidate_monitor_result_path"],
            "joint_distribution": selection["joint_distribution_path"],
            "distributional_gate": selection["distributional_gate_path"],
            "selection_decision": (selection_root / "selection_decision.json").as_posix(),
            "explanation": explanation_root.as_posix(),
            "step_summary": (step_root / "step_summary.json").as_posix(),
        },
    }
    _write_json(step_root / "step_summary.json", summary)
    (step_root / "execution_error.json").unlink(missing_ok=True)
    (step_root / "diagnosis_contract_error.json").unlink(missing_ok=True)
    return summary, copy.deepcopy(next_parent), next_monitor


def run_campaign(
    campaign: dict[str, Any], batch_map: dict[str, Any], services: EvolutionServices, *,
    artifact_root: Path, resume: bool = False, stop_after_step: int | None = None,
) -> dict[str, Any]:
    """Run or resume the three frozen batches with serial Parent propagation."""

    if stop_after_step is not None and (
        not isinstance(stop_after_step, int) or isinstance(stop_after_step, bool)
        or stop_after_step not in {1, 2, 3}
    ):
        raise OrchestrationContractError("stop_after_step must be 1, 2, 3, or None.")
    target_step = 3 if stop_after_step is None else stop_after_step
    state_path = artifact_root / "campaign_state.json"
    if resume:
        if not state_path.is_file():
            raise OrchestrationContractError("Resume requires campaign_state.json.")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("campaign_id") != campaign.get("campaign_id"):
            raise OrchestrationContractError("Campaign resume identity drifted.")
        completed = state.get("completed_steps")
        parent = _skill_identity(state.get("current_parent"))
        if (
            not isinstance(completed, list) or len(completed) not in {0, 1, 2, 3}
            or state.get("current_step") != len(completed)
            or [item.get("step") for item in completed if isinstance(item, dict)]
            != list(range(1, len(completed) + 1))
        ):
            raise OrchestrationContractError("Campaign resume state is invalid.")
    else:
        if state_path.exists():
            raise OrchestrationContractError("Campaign state already exists; use resume.")
        completed = []
        parent = _skill_identity(campaign["initial_parent"])

    if resume and len(completed) >= target_step:
        return state
    parent_monitor = services.candidate_monitor(copy.deepcopy(parent))
    if not resume:
        state = {
            "schema_version": "autonomous_gse_campaign_state_0.14.0",
            "campaign_id": campaign["campaign_id"], "current_step": 0,
            "current_parent": copy.deepcopy(parent),
            "current_parent_monitor_result_path": _monitor_path(artifact_root, parent),
            "completed_steps": [], "final_skill": None,
        }
        _write_json(state_path, state)
    for step, batch in enumerate(batch_map["batches"], start=1):
        if step <= len(completed):
            continue
        if step > target_step:
            break
        summary, parent, parent_monitor = run_evolution_step(
            step=step, batch=batch, parent=parent, parent_monitor=parent_monitor,
            campaign=campaign, services=services, artifact_root=artifact_root,
        )
        completed.append(summary)
        state = {
            "schema_version": "autonomous_gse_campaign_state_0.14.0",
            "campaign_id": campaign["campaign_id"], "current_step": step,
            "current_parent": copy.deepcopy(parent),
            "current_parent_monitor_result_path": _monitor_path(artifact_root, parent),
            "completed_steps": copy.deepcopy(completed),
            "final_skill": copy.deepcopy(parent) if step == 3 else None,
        }
        _write_json(state_path, state)
        if step == target_step:
            break
    return state


def resume_campaign(
    campaign: dict[str, Any], batch_map: dict[str, Any], services: EvolutionServices, *,
    artifact_root: Path, stop_after_step: int | None = None,
) -> dict[str, Any]:
    return run_campaign(
        campaign, batch_map, services, artifact_root=artifact_root, resume=True,
        stop_after_step=stop_after_step,
    )
