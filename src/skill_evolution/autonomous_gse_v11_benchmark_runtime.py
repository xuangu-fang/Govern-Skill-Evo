"""Single-rollout matched-replay τ³ runtime for Autonomous GSE v0.11."""

from __future__ import annotations

import argparse
import copy
import json
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from src.adapters.tau2.tau3_compliance_judge import JudgeCaller, default_judge_caller
from src.adapters.tau2.tau3_gse_runtime import official_task_evaluation, stable_trajectory
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v03_runtime import RuntimeContractError
from src.skill_evolution.autonomous_gse_v09_benchmark_runtime import Tau3RolloutAdapter as V09RolloutAdapter
from src.skill_evolution.autonomous_gse_v11_proposal import DiagnosisDrivenProposalOperator
from src.skill_evolution.diagnosis_v11 import call_diagnosis
from src.skill_evolution.evolution_gate_v11 import (
    aggregate_counts,
    build_evolution_decision,
    no_candidate_decision,
)
from src.skill_evolution.regression_diagnosis_v11 import (
    RegressionDiagnosisRequest,
    RegressionDiagnosisResponseError,
    build_regression_transition_report,
    call_regression_diagnosis,
)
from src.skill_evolution.targeted_fix_v11 import TargetedFixRequest, call_targeted_fix
from src.learners.stwebagentbench.generate_governed_skill_v11 import call_governed_editor

PROTOCOL_VERSION = "autonomous_gse_v11"
FORMAL_MODE = "formal_tau3_airline_retail_v11_single_rollout_matched_replay"
REPO_ROOT = Path(__file__).resolve().parents[2]
OUTCOME_STATES = (
    "compliant_success", "violating_success", "compliant_failure", "violating_failure"
)
REUSED_V09_BENCHMARK_COMPONENTS = (
    "src/adapters/tau2/tau3_gse_runtime.py",
    "src/adapters/tau2/tau3_compliance_judge.py",
    "src/skill_evolution/autonomous_gse_v09_benchmark_runtime.py:Tau3RolloutAdapter.run",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _resolved_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def validate_campaign_contract(campaign: dict[str, Any]) -> None:
    if (
        campaign.get("schema_version") != "autonomous_gse_campaign_0.11.0"
        or campaign.get("protocol_version") != PROTOCOL_VERSION
        or campaign.get("campaign_id") != PROTOCOL_VERSION
        or campaign.get("campaign_seed") != 200
    ):
        raise RuntimeContractError("τ³ v0.11 Campaign identity is invalid.")
    if campaign.get("benchmark", {}).get("name") != "tau3" or campaign["benchmark"].get(
        "domains"
    ) != ["airline", "retail"]:
        raise RuntimeContractError("v0.11 supports only τ³ Airline/Retail.")
    if campaign.get("schedule") != {"evolution_steps": 3}:
        raise RuntimeContractError("v0.11 requires exactly three Steps.")
    evolution = campaign.get("evolution", {})
    if (
        evolution.get("source_split") != "official_train"
        or evolution.get("tasks") != 60
        or evolution.get("airline_tasks") != 30
        or evolution.get("retail_tasks") != 30
        or evolution.get("batches") != 3
        or evolution.get("tasks_per_batch") != 20
        or evolution.get("airline_tasks_per_batch") != 10
        or evolution.get("retail_tasks_per_batch") != 10
        or evolution.get("rollouts_per_task") != 1
        or evolution.get("cumulative_evidence") is not False
        or evolution.get("replay_previous_batches") is not False
    ):
        raise RuntimeContractError("v0.11 Evolution workload drifted.")
    if "selection" in campaign:
        raise RuntimeContractError("v0.11 must not define a Selection workload.")
    holdout = campaign.get("holdout", {})
    if (
        holdout.get("source_split") != "official_test"
        or holdout.get("tasks") != 40
        or holdout.get("airline_tasks") != 20
        or holdout.get("retail_tasks") != 20
        or holdout.get("rollouts_per_task") != 1
        or holdout.get("compare") != ["S0", "S_final"]
        or holdout.get("learning_access") != "forbidden"
        or holdout.get("feedback_to_learner") != "forbidden"
        or holdout.get("automatic_execution") is not False
    ):
        raise RuntimeContractError("v0.11 Holdout contract drifted.")
    frozen_model = {
        "model": "openai/deepseek-v4-flash",
        "temperature": 0.0,
        "thinking": "high",
        "reasoning_effort": "high",
        "max_tokens": 8192,
        "empty_response_retries": 2,
        "empty_response_retry_max_tokens": 8192,
    }
    for role in ("agent", "user_simulator"):
        if any(campaign.get(role, {}).get(key) != value for key, value in frozen_model.items()):
            raise RuntimeContractError(f"Frozen {role} sampling configuration drifted.")
    if campaign.get("compliance_judge", {}) != {
        "model": "openai/gpt-5.6-luna",
        "temperature": 0,
        "prompt_version": "tau3_policy_grounded_judge_v3",
        "frozen_across_phases_and_methods": True,
        "failure_mode": "COMPLIANCE_JUDGE_ERROR",
        "fallback": "forbidden",
    }:
        raise RuntimeContractError("Frozen Compliance Judge drifted.")
    evaluator = campaign.get("official_evaluator", {})
    if (
        evaluator.get("implementation") != "tau3_official_evaluator"
        or evaluator.get("nl_assertions_model") != "openai/gpt-5.6-luna"
        or evaluator.get("nl_assertions_temperature") != 0.0
    ):
        raise RuntimeContractError("Official evaluator drifted.")
    method = campaign.get("skill_evolution", {})
    if (
        method.get("allowed_operations") != ["add", "replace", "delete"]
        or method.get("maximum_skill_rules") != 18
        or method.get("maximum_skill_words") != 900
        or method.get("maximum_editor_calls_per_step") != 1
        or method.get("preserve_constraints") != "forbidden"
        or method.get("regression_feedback_to_editor") != "forbidden"
    ):
        raise RuntimeContractError("v0.11 bounded-edit semantics drifted.")
    expected_budget = {
        "evolution_parent_trajectories": 60,
        "maximum_candidate_replay_trajectories": 60,
        "maximum_evolution_trajectories": 120,
        "final_holdout_trajectories_if_authorized": 80,
        "maximum_total_including_holdout": 200,
        "maximum_candidates": 3,
        "maximum_parent_diagnosis_calls": 60,
        "maximum_editor_calls": 3,
        "maximum_targeted_fix_calls": 60,
        "maximum_regression_diagnosis_calls": 60,
    }
    if campaign.get("budget") != expected_budget:
        raise RuntimeContractError("v0.11 budget drifted.")
def derive_rollout_seeds(
    campaign_seed: int, execution_seed_offset: int, rollouts_per_task: int = 1
) -> tuple[int, ...]:
    if rollouts_per_task != 1:
        raise RuntimeContractError("v0.11 requires exactly one rollout per task.")
    return (campaign_seed + execution_seed_offset,)


def matched_replay_plan(
    task_ids: list[str], campaign_seed: int, execution_seed_offset: int = 0
) -> dict[str, list[dict[str, Any]]]:
    seed = derive_rollout_seeds(campaign_seed, execution_seed_offset)[0]
    units = [
        {"task_id": task_id, "rollout_index": 1, "rollout_seed": seed}
        for task_id in task_ids
    ]
    return {"parent": copy.deepcopy(units), "candidate": copy.deepcopy(units)}


def _validate_batch_map(batch_map: dict[str, Any], campaign: dict[str, Any]) -> None:
    if (
        batch_map.get("schema_version") != "tau3_gse_task_split_0.11.0"
        or batch_map.get("campaign_seed") != campaign["campaign_seed"]
    ):
        raise RuntimeContractError("Frozen v0.11 Batch Map identity is invalid.")
    assignment = batch_map.get("assignment", {})
    evolution = assignment.get("evolution", {})
    holdout = assignment.get("holdout", {})
    if any(len(evolution.get(domain, [])) != 30 for domain in ("airline", "retail")):
        raise RuntimeContractError("Frozen Evolution assignment is invalid.")
    if any(len(holdout.get(domain, [])) != 20 for domain in ("airline", "retail")):
        raise RuntimeContractError("Frozen Holdout assignment is invalid.")
    batches = batch_map.get("batches", [])
    flattened = []
    for index, batch in enumerate(batches, start=1):
        ids = batch.get("task_ids", [])
        if (
            batch.get("batch_id") != f"batch_{index}"
            or len(ids) != 20
            or sum(item.startswith("airline:") for item in ids) != 10
            or sum(item.startswith("retail:") for item in ids) != 10
        ):
            raise RuntimeContractError("Frozen Evolution batch is invalid.")
        flattened.extend(ids)
    if len(batches) != 3 or len(flattened) != 60 or len(set(flattened)) != 60:
        raise RuntimeContractError("Evolution batches are not a 60-task partition.")


def build_campaign_dry_plan(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, Any]:
    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    steps = []
    for index, batch in enumerate(batch_map["batches"], start=1):
        replay = matched_replay_plan(batch["task_ids"], campaign["campaign_seed"])
        steps.append(
            {
                "step": index,
                "batch_id": batch["batch_id"],
                "task_ids": copy.deepcopy(batch["task_ids"]),
                "parent_units": replay["parent"],
                "candidate_replay_units": replay["candidate"],
                "parent_trajectories": 20,
                "maximum_candidate_replay_trajectories": 20,
                "maximum_parent_diagnosis_calls": 20,
                "maximum_editor_calls": 1,
                "maximum_targeted_fix_calls": 20,
                "maximum_regression_diagnosis_calls": 20,
                "matched_seed_lineage": replay["parent"] == replay["candidate"],
                "replay_previous_batches": False,
            }
        )
    computed = {
        "evolution_parent_trajectories": sum(x["parent_trajectories"] for x in steps),
        "maximum_candidate_replay_trajectories": sum(
            x["maximum_candidate_replay_trajectories"] for x in steps
        ),
        "maximum_evolution_trajectories": 120,
        "final_holdout_trajectories_if_authorized": 80,
        "maximum_total_including_holdout": 200,
        "maximum_candidates": 3,
        "maximum_parent_diagnosis_calls": 60,
        "maximum_editor_calls": 3,
        "maximum_targeted_fix_calls": 60,
        "maximum_regression_diagnosis_calls": 60,
    }
    if computed != campaign["budget"]:
        raise RuntimeContractError("Dry-plan workload and budget disagree.")
    holdout_ids = [
        *(f"airline:{value}" for value in batch_map["assignment"]["holdout"]["airline"]),
        *(f"retail:{value}" for value in batch_map["assignment"]["holdout"]["retail"]),
    ]
    return {
        "schema_version": "autonomous_gse_dry_plan_0.11.0",
        "campaign_id": campaign["campaign_id"],
        "mode": "no_api_no_rollout_no_write",
        "steps": steps,
        "computed_budget": computed,
        "selection_workload": None,
        "holdout": {
            "authorized": False,
            "included_in_evolution_run": False,
            "task_ids": holdout_ids,
            "skills": ["S0", "S_final"],
            "trajectories_if_explicitly_authorized": 80,
        },
    }


class Tau3RolloutAdapter(V09RolloutAdapter):
    """Reuse the v0.9 official rollout/evaluation implementation without its workflow."""

    def __init__(
        self, campaign: dict[str, Any], *, repo_root: Path, judge_caller: JudgeCaller
    ) -> None:
        validate_campaign_contract(campaign)
        self.campaign = copy.deepcopy(campaign)
        # The v0.9 implementation checks this key only when an explicitly
        # dispatched Holdout unit uses phase="test".
        self.campaign["test"] = {"formal_run_authorized": True}
        self.repo_root = repo_root.resolve()
        self.tau2_root = (self.repo_root / campaign["benchmark"]["path"]).resolve()
        self.judge_caller = judge_caller


class Tau3CampaignRolloutBackend:
    """Run one matched unit per task, with artifact reuse and concurrency."""

    def __init__(
        self,
        campaign: dict[str, Any],
        *,
        judge_caller: JudgeCaller = default_judge_caller,
        artifact_root: Path | None = None,
    ) -> None:
        validate_campaign_contract(campaign)
        self.campaign = copy.deepcopy(campaign)
        self.artifact_root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "formal"
        self.max_concurrency = campaign["execution"]["max_concurrency"]
        self.rollout = Tau3RolloutAdapter(campaign, repo_root=REPO_ROOT, judge_caller=judge_caller)

    def _reusable(
        self,
        path: Path, *, domain: str, task_id: str, phase: str, version: str, seed: int
    ) -> bool:
        try:
            value = _load_json(path)
            provenance = value["provenance"]
            raw_path = _resolved_path(provenance["raw_tau3_result_path"])
            raw = _load_json(raw_path)
            evaluation = official_task_evaluation(raw)
            trajectory = stable_trajectory(raw.get("messages") or [])
            compliance = value["compliance_evaluation"]
            governed = value["governed_evidence"]
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return False
        if (
            value.get("schema_version") != "tau3_gse_rollout_0.9.0"
            or value.get("domain") != domain
        ):
            return False
        if (
            value.get("task_id") != task_id
            or value.get("phase") != phase
            or value.get("skill_version") != version
            or value.get("rollout_index") != 1
            or value.get("rollout_seed") != seed
            or value.get("seed_lineage") != {
                "rollout_seed": seed,
                "agent_seed": seed,
                "user_simulator_seed": seed,
                "environment_seed": seed,
            }
            or raw.get("task_id") != task_id
            or not trajectory
            or value.get("trajectory") != trajectory
            or value.get("task_evaluation") != evaluation
            or governed.get("trajectory") != trajectory
            or governed.get("task_evaluation") != evaluation
            or governed.get("compliance_evaluation") != compliance
            or provenance.get("agent_config") != self.campaign["agent"]
            or provenance.get("user_simulator_config") != self.campaign["user_simulator"]
            or provenance.get("official_evaluator_config") != self.campaign["official_evaluator"]
            or compliance.get("judge_model") != self.campaign["compliance_judge"]["model"]
            or compliance.get("judge_temperature") != self.campaign["compliance_judge"]["temperature"]
            or compliance.get("judge_prompt_version") != self.campaign["compliance_judge"]["prompt_version"]
            or not isinstance(compliance.get("compliant"), bool)
            or not isinstance(compliance.get("violations"), list)
        ):
            return False
        compliant = compliance["compliant"]
        if compliant == bool(compliance["violations"]):
            return False
        expected_state = (
            "compliant_success" if evaluation["success"] and compliant
            else "violating_success" if evaluation["success"]
            else "compliant_failure" if compliant
            else "violating_failure"
        )
        return (
            value.get("state") == expected_state
            and governed.get("state") == expected_state
            and governed.get("task_success") is evaluation["success"]
        )

    def run_batch(
        self,
        *,
        task_ids: list[str],
        phase: str,
        skill_version: str,
        skill_path: Path | None,
        execution_phase: str,
        execution_seed_offset: int = 0,
    ) -> list[Path]:
        seed = derive_rollout_seeds(self.campaign["campaign_seed"], execution_seed_offset)[0]
        paths: list[Path] = []
        pending = []
        for domain_task in task_ids:
            domain, task_id = domain_task.split(":", 1)
            output = (
                self.artifact_root / "rollouts" / phase / execution_phase
                / f"{domain}_{task_id}_rollout_01.json"
            )
            paths.append(output)
            if not self._reusable(
                output, domain=domain, task_id=task_id, phase=phase,
                version=skill_version, seed=seed
            ):
                pending.append({
                    "domain": domain,
                    "task_id": task_id,
                    "phase": phase,
                    "skill_version": skill_version,
                    "skill_path": None if skill_version == "S0" else skill_path,
                    "rollout_index": 1,
                    "rollout_seed": seed,
                    "output_path": output,
                })
        with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            tuple(executor.map(lambda kwargs: self.rollout.run(**kwargs), pending))
        return paths


def _method_skill(text: str) -> str:
    return text.replace("# Operational Skill", "# SuiteCRM Operational Skill", 1)


def _canonical_skill(text: str) -> str:
    return text.replace("# SuiteCRM Operational Skill", "# Operational Skill", 1)


def _rows_and_evidence(paths: list[Path], *, step: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    experiences = []
    for path in paths:
        value = _load_json(path)
        source_id = f"step_{step:03d}_{value['domain']}_{value['task_id']}_rollout_01"
        experience = copy.deepcopy(value["governed_evidence"])
        experience["source_id"] = source_id
        experiences.append(experience)
        rows.append({
            "source_id": source_id,
            "domain": value["domain"],
            "task_id": value["task_id"],
            "rollout_index": 1,
            "rollout_seed": value["rollout_seed"],
            "task_success": value["task_evaluation"]["success"],
            "compliant": value["compliance_evaluation"]["compliant"],
            "state": value["state"],
            "trajectory": copy.deepcopy(value["governed_evidence"]),
            "artifact_path": path.as_posix(),
        })
    return rows, experiences


def _candidate_edit_provenance(decision: Any) -> list[dict[str, Any]]:
    signals = {item["patch_id"]: item for item in decision.raw_patches}
    result = []
    for edit in decision.applied_edits:
        patch_ids = edit["derived_from_patch_ids"]
        source = [signals[value] for value in patch_ids]
        result.append({
            **copy.deepcopy(edit),
            "final_text": edit.get("text", ""),
            "derived_from_diagnosis_ids": list(dict.fromkeys(
                item["diagnosis_id"] for item in source
            )),
            "objective": " | ".join(dict.fromkeys(item["objective"] for item in source)),
            "description": " | ".join(dict.fromkeys(item["description"] for item in source)),
        })
    return result


def run_v11_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    *,
    backend: Tau3CampaignRolloutBackend | None = None,
    diagnoser: Callable[[Any], str] = call_diagnosis,
    editor: Callable[[Any], str] = call_governed_editor,
    targeted_fix_judge: Callable[[TargetedFixRequest], dict[str, Any]] = call_targeted_fix,
    regression_judge: Callable[[RegressionDiagnosisRequest], dict[str, Any]] = call_regression_diagnosis,
    artifact_root: Path | None = None,
    resume_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run only three Evolution Steps; Holdout is never entered here."""

    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "formal"
    backend = backend or Tau3CampaignRolloutBackend(campaign, artifact_root=root)
    completed_steps = 0
    report_steps: list[dict[str, Any]] = []
    if resume_state is not None:
        if resume_state.get("protocol_version") != PROTOCOL_VERSION:
            raise RuntimeContractError("v0.11 resume protocol is invalid.")
        completed_steps = resume_state.get("completed_steps")
        if not isinstance(completed_steps, int) or not 0 <= completed_steps <= 3:
            raise RuntimeContractError("v0.11 completed Step count is invalid.")
        parent = copy.deepcopy(resume_state.get("current_parent"))
        if not isinstance(parent, dict):
            raise RuntimeContractError("v0.11 resume Parent is invalid.")
        stored_steps = resume_state.get("steps")
        if not isinstance(stored_steps, list) or len(stored_steps) != completed_steps:
            raise RuntimeContractError("v0.11 resume Step records are invalid.")
        report_steps = copy.deepcopy(stored_steps)
    else:
        parent = copy.deepcopy(campaign["initial_parent"])
    parent_path = _resolved_path(parent["path"])
    if not parent_path.is_file():
        raise RuntimeContractError("Current Parent Skill artifact is missing.")
    operator = DiagnosisDrivenProposalOperator()
    for step_number, batch in enumerate(batch_map["batches"], start=1):
        if step_number <= completed_steps:
            continue
        step_root = root / "steps" / f"step_{step_number:03d}"
        step_parent = copy.deepcopy(parent)
        parent_paths = backend.run_batch(
            task_ids=batch["task_ids"], phase="train", skill_version=parent["version"],
            skill_path=parent_path, execution_phase=f"step_{step_number:03d}_parent"
        )
        parent_rows, experiences = _rows_and_evidence(parent_paths, step=step_number)
        parent_skill = _method_skill(parent_path.read_text(encoding="utf-8"))
        proposal = operator.propose(
            ProposalContext(
                candidate_id=f"candidate_{step_number:03d}",
                parent_skill=parent_skill,
                current_batch_governed_evidence=tuple(experiences),
            ),
            diagnoser,
            editor,
        )
        _write_json(step_root / "diagnoses.json", {
            "diagnoses": proposal.diagnoses,
            "eligible_diagnosis_ids": proposal.eligible_diagnosis_ids,
        })
        _write_json(step_root / "proposal.json", copy.deepcopy(proposal.__dict__))
        if proposal.proposal_status != "CANDIDATE" or proposal.candidate_skill is None:
            decision = no_candidate_decision()
            _write_json(step_root / "evolution_decision.json", decision)
            report_steps.append({
                "step": step_number, "batch_id": batch["batch_id"],
                "parent": step_parent, "promoted_parent": copy.deepcopy(parent),
                "candidate": None, **decision,
            })
            _write_json(root / "resume_state.json", {
                "protocol_version": PROTOCOL_VERSION,
                "completed_steps": step_number,
                "current_parent": parent,
                "steps": report_steps,
            })
            continue

        candidate_version = f"S{step_number}"
        candidate_path = step_root / "candidate_skill.md"
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(_canonical_skill(proposal.candidate_skill), encoding="utf-8")
        edits = _candidate_edit_provenance(proposal)
        _write_json(step_root / "candidate_edits.json", edits)
        candidate_paths = backend.run_batch(
            task_ids=batch["task_ids"], phase="train", skill_version=candidate_version,
            skill_path=candidate_path, execution_phase=f"step_{step_number:03d}_candidate_replay"
        )
        candidate_rows, _ = _rows_and_evidence(candidate_paths, step=step_number)
        parent_by_source = {row["source_id"]: row for row in parent_rows}
        candidate_by_key = {
            (row["domain"], row["task_id"], row["rollout_index"]): row for row in candidate_rows
        }
        targeted = []
        diagnosis_by_id = {
            item["diagnosis_id"]: item for item in proposal.diagnoses
            if item["diagnosis_id"] in proposal.eligible_diagnosis_ids
        }
        for diagnosis_id in proposal.eligible_diagnosis_ids:
            diagnosis = diagnosis_by_id[diagnosis_id]
            parent_row = parent_by_source[diagnosis["source_id"]]
            candidate_row = candidate_by_key[
                (parent_row["domain"], parent_row["task_id"], parent_row["rollout_index"])
            ]
            targeted.append(targeted_fix_judge(TargetedFixRequest(
                diagnosis_id=diagnosis_id,
                source_id=diagnosis["source_id"],
                task_context={"domain": parent_row["domain"], "task_id": parent_row["task_id"]},
                update_diagnosis=diagnosis["structured_output"],
                candidate_edits=tuple(
                    edit for edit in edits if diagnosis_id in edit["derived_from_diagnosis_ids"]
                ),
                parent_trajectory=parent_row["trajectory"],
                candidate_trajectory=candidate_row["trajectory"],
                parent_state=parent_row["state"],
                candidate_state=candidate_row["state"],
            )))
        _write_json(step_root / "targeted_fix_report.json", {"results": targeted})

        transitions = build_regression_transition_report(parent_rows, candidate_rows)
        _write_json(step_root / "regression_transition_report.json", transitions)
        regression_diagnoses = []
        parent_by_key = {
            (row["domain"], row["task_id"], row["rollout_index"]): row for row in parent_rows
        }
        regression_error_path = step_root / "regression_diagnosis_error.json"
        for regression in transitions["regression_set"]:
            key = (regression["domain"], regression["task_id"], regression["rollout_index"])
            before, after = parent_by_key[key], candidate_by_key[key]
            request = RegressionDiagnosisRequest(
                pair_id=regression["pair_id"], domain=regression["domain"],
                task_context={"domain": regression["domain"], "task_id": regression["task_id"]},
                regression_type=regression["regression_type"],
                parent_state=before["state"], candidate_state=after["state"],
                candidate_edits=tuple(copy.deepcopy(edits)),
                parent_trajectory=before["trajectory"], candidate_trajectory=after["trajectory"],
            )
            try:
                regression_diagnoses.append(regression_judge(request))
            except RegressionDiagnosisResponseError as error:
                _write_json(regression_error_path, {
                    "schema_version": "autonomous_gse_regression_diagnosis_error_0.11.0",
                    "pair_id": request.pair_id,
                    "domain": request.domain,
                    "parent_state": request.parent_state,
                    "candidate_state": request.candidate_state,
                    "regression_type": request.regression_type,
                    "error_code": error.code,
                    "raw_response": error.raw_response,
                    "completed_regression_diagnoses": len(regression_diagnoses),
                })
                raise
        regression_error_path.unlink(missing_ok=True)
        _write_json(step_root / "regression_diagnoses.json", {"diagnoses": regression_diagnoses})
        aggregate = {
            "parent": aggregate_counts(parent_rows),
            "candidate": aggregate_counts(candidate_rows),
        }
        _write_json(step_root / "aggregate_metrics.json", aggregate)
        decision = build_evolution_decision(
            targeted_fix_results=targeted,
            regression_diagnoses=regression_diagnoses,
            parent_rows=parent_rows,
            candidate_rows=candidate_rows,
        )
        _write_json(step_root / "evolution_decision.json", decision)
        candidate = {"kind": "candidate_skill", "version": candidate_version, "path": candidate_path.as_posix()}
        if decision["decision"] == "ACCEPT":
            parent = candidate
            parent_path = candidate_path
        report_steps.append({
            "step": step_number, "batch_id": batch["batch_id"],
            "parent": step_parent, "promoted_parent": copy.deepcopy(parent),
            "candidate": candidate, **decision,
        })
        _write_json(root / "resume_state.json", {
            "protocol_version": PROTOCOL_VERSION,
            "completed_steps": step_number,
            "current_parent": parent,
            "steps": report_steps,
        })
    report = {
        "schema_version": "autonomous_gse_formal_report_0.11.0",
        "protocol_version": PROTOCOL_VERSION,
        "campaign_id": campaign["campaign_id"],
        "mode": FORMAL_MODE,
        "steps": report_steps,
        "final_skill": parent,
        "disabled_phases": {"official_test_holdout": True},
    }
    _write_json(root / "campaign_report.json", report)
    return report


def build_holdout_plan(campaign: dict[str, Any], batch_map: dict[str, Any], final_skill: dict[str, Any]) -> dict[str, Any]:
    """Build an explicit S0-vs-S_final Holdout plan without executing it."""
    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    task_ids = [
        *(f"airline:{x}" for x in batch_map["assignment"]["holdout"]["airline"]),
        *(f"retail:{x}" for x in batch_map["assignment"]["holdout"]["retail"]),
    ]
    units = matched_replay_plan(task_ids, campaign["campaign_seed"])
    return {
        "schema_version": "autonomous_gse_holdout_plan_0.11.0",
        "source_split": "official_test",
        "task_ids": task_ids,
        "skills": [copy.deepcopy(campaign["initial_parent"]), copy.deepcopy(final_skill)],
        "s0_units": units["parent"],
        "s_final_units": units["candidate"],
        "matched_seed_lineage": True,
        "trajectory_count": 80,
        "learning_calls": 0,
    }


def evaluate_holdout(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    final_skill: dict[str, Any],
    *,
    backend: Tau3CampaignRolloutBackend | None = None,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    """Explicitly execute official_test for S0 and S_final, with no learner calls."""

    plan = build_holdout_plan(campaign, batch_map, final_skill)
    root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "holdout"
    backend = backend or Tau3CampaignRolloutBackend(campaign, artifact_root=root)
    results: dict[str, Any] = {}
    for label, skill in (("S0", campaign["initial_parent"]), ("S_final", final_skill)):
        skill_path = _resolved_path(skill["path"])
        paths = backend.run_batch(
            task_ids=plan["task_ids"],
            phase="test",
            skill_version=skill["version"],
            skill_path=skill_path,
            execution_phase=label.casefold(),
        )
        rows, _ = _rows_and_evidence(paths, step=0)
        by_domain = {
            domain: aggregate_counts([row for row in rows if row["domain"] == domain])
            for domain in ("airline", "retail")
        }
        results[label] = {**by_domain, "overall": aggregate_counts(rows)}
    report = {
        "schema_version": "autonomous_gse_holdout_report_0.11.0",
        "campaign_id": campaign["campaign_id"],
        "source_split": "official_test",
        "task_count": 40,
        "trajectory_count": 80,
        "compare": ["S0", "S_final"],
        "metrics": results,
        "learning_calls": 0,
        "feedback_to_learner": "forbidden",
    }
    _write_json(root / "holdout_report.json", report)
    return report


def _campaign_files(campaign_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    campaign = _load_json(campaign_path)
    batch_map = _load_json(_resolved_path(campaign["evolution"]["batch_map"]))
    return campaign, batch_map


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "run", "resume", "evaluate-holdout"):
        item = sub.add_parser(command)
        item.add_argument("--campaign", type=Path, required=True)
    args = parser.parse_args(argv)
    campaign_path = args.campaign.resolve()
    campaign, batch_map = _campaign_files(campaign_path)
    if args.command == "plan":
        print(json.dumps(build_campaign_dry_plan(campaign, batch_map), indent=2))
        return 0
    root = REPO_ROOT / "artifacts" / campaign["campaign_id"] / "formal"
    if args.command == "evaluate-holdout":
        report_path = root / "campaign_report.json"
        if not report_path.is_file():
            raise RuntimeContractError("Evolution report is required before Holdout.")
        report = evaluate_holdout(
            campaign,
            batch_map,
            _load_json(report_path)["final_skill"],
            artifact_root=REPO_ROOT / "artifacts" / campaign["campaign_id"] / "holdout",
        )
        print(json.dumps(report, indent=2))
        return 0
    if args.command == "resume" and not (root / "resume_state.json").is_file():
        raise RuntimeContractError("No v0.11 resume state is available.")
    resume_state = _load_json(root / "resume_state.json") if args.command == "resume" else None
    report = run_v11_campaign(
        campaign, batch_map, artifact_root=root, resume_state=resume_state
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
