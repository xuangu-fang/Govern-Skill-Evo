"""K=3 matched-replay τ³ runtime for Autonomous GSE v0.12."""

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
from src.learners.stwebagentbench.generate_governed_skill_v12 import call_governed_editor
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v12_proposal import (
    DiagnosisContractError,
    MultiRolloutDiagnosisProposalOperator,
)
from src.skill_evolution.diagnosis_v12 import call_diagnosis
from src.skill_evolution.evolution_gate_v11 import aggregate_counts
from src.skill_evolution.evolution_gate_v12 import build_evolution_decision, no_candidate_decision
from src.skill_evolution.targeted_fix_v12 import (
    TargetedFixRequest,
    TargetedFixResponseError,
    call_targeted_fix,
)

PROTOCOL_VERSION = "autonomous_gse_v12"
FORMAL_MODE = "formal_tau3_airline_retail_v12_k3_matched_replay"
REPO_ROOT = Path(__file__).resolve().parents[2]
ROLLOUTS_PER_TASK = 3


class RuntimeContractError(ValueError):
    """Raised when a v0.12 campaign/runtime invariant is violated."""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _resolved_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def validate_campaign_contract(campaign: dict[str, Any]) -> None:
    if campaign.get("schema_version") != "autonomous_gse_campaign_0.12.0" or campaign.get("protocol_version") != PROTOCOL_VERSION or campaign.get("campaign_id") != PROTOCOL_VERSION or campaign.get("campaign_seed") != 200:
        raise RuntimeContractError("τ³ v0.12 Campaign identity is invalid.")
    if campaign.get("benchmark", {}).get("name") != "tau3" or campaign["benchmark"].get("domains") != ["airline", "retail"]:
        raise RuntimeContractError("v0.12 supports only τ³ Airline/Retail.")
    if campaign.get("schedule") != {"evolution_steps": 3}:
        raise RuntimeContractError("v0.12 requires exactly three Steps.")
    evolution = campaign.get("evolution", {})
    if any((
        evolution.get("source_split") != "official_train", evolution.get("tasks") != 60,
        evolution.get("airline_tasks") != 30, evolution.get("retail_tasks") != 30,
        evolution.get("batches") != 3, evolution.get("tasks_per_batch") != 20,
        evolution.get("airline_tasks_per_batch") != 10, evolution.get("retail_tasks_per_batch") != 10,
        evolution.get("rollouts_per_task") != 3, evolution.get("cumulative_evidence") is not False,
        evolution.get("replay_previous_batches") is not False,
    )):
        raise RuntimeContractError("v0.12 Evolution workload drifted.")
    if "selection" in campaign:
        raise RuntimeContractError("v0.12 must not define Selection.")
    holdout = campaign.get("holdout", {})
    if any((
        holdout.get("source_split") != "official_test", holdout.get("tasks") != 40,
        holdout.get("airline_tasks") != 20, holdout.get("retail_tasks") != 20,
        holdout.get("rollouts_per_task") != 3, holdout.get("compare") != ["S0", "S_final"],
        holdout.get("learning_access") != "forbidden", holdout.get("feedback_to_learner") != "forbidden",
        holdout.get("automatic_execution") is not False,
    )):
        raise RuntimeContractError("v0.12 Holdout contract drifted.")
    frozen = {"model": "openai/deepseek-v4-flash", "temperature": 0.0, "thinking": "high", "reasoning_effort": "high", "max_tokens": 8192, "empty_response_retries": 2, "empty_response_retry_max_tokens": 8192}
    for role in ("agent", "user_simulator"):
        if any(campaign.get(role, {}).get(key) != value for key, value in frozen.items()):
            raise RuntimeContractError(f"Frozen {role} sampling configuration drifted.")
    if campaign.get("compliance_judge", {}) != {"model": "openai/gpt-5.6-luna", "temperature": 0, "prompt_version": "tau3_policy_grounded_judge_v3", "frozen_across_phases_and_methods": True, "failure_mode": "COMPLIANCE_JUDGE_ERROR", "fallback": "forbidden"}:
        raise RuntimeContractError("Frozen Compliance Judge drifted.")
    evaluator = campaign.get("official_evaluator", {})
    if evaluator.get("implementation") != "tau3_official_evaluator" or evaluator.get("nl_assertions_model") != "openai/gpt-5.6-luna" or evaluator.get("nl_assertions_temperature") != 0.0:
        raise RuntimeContractError("Official evaluator drifted.")
    method = campaign.get("skill_evolution", {})
    if any((
        method.get("proposal_operator") != "v12_multi_rollout_diagnosis_bounded_edit",
        method.get("diagnosis_calls_per_task") != 1, method.get("targeted_fix_unit") != "canonical_edit",
        method.get("counterevidence_enabled") is not True,
        method.get("allowed_operations") != ["add", "replace", "delete"],
        method.get("maximum_skill_rules") != 18, method.get("maximum_skill_words") != 900,
        method.get("maximum_editor_calls_per_step") != 1,
        method.get("regression_feedback_to_editor") != "forbidden",
    )):
        raise RuntimeContractError("v0.12 method semantics drifted.")
    expected_budget = {
        "evolution_parent_trajectories": 180,
        "maximum_candidate_replay_trajectories": 180,
        "maximum_evolution_trajectories": 360,
        "final_holdout_trajectories_if_authorized": 240,
        "maximum_total_including_holdout": 600,
        "maximum_candidates": 3,
        "maximum_parent_diagnosis_calls": 60,
        "maximum_editor_calls": 3,
        "maximum_targeted_fix_calls": 54,
        "maximum_regression_diagnosis_calls": 180,
    }
    if campaign.get("budget") != expected_budget:
        raise RuntimeContractError("v0.12 budget drifted.")


def derive_rollout_seeds(campaign_seed: int, execution_seed_offset: int, rollouts_per_task: int = 3) -> tuple[int, ...]:
    if rollouts_per_task != ROLLOUTS_PER_TASK:
        raise RuntimeContractError("v0.12 requires exactly three rollouts per task.")
    base = campaign_seed + execution_seed_offset
    return tuple(base + index for index in range(rollouts_per_task))


def matched_replay_plan(task_ids: list[str], campaign_seed: int, execution_seed_offset: int = 0) -> dict[str, list[dict[str, Any]]]:
    seeds = derive_rollout_seeds(campaign_seed, execution_seed_offset)
    units = [
        {"task_id": task_id, "rollout_index": index, "rollout_seed": seeds[index - 1]}
        for task_id in task_ids for index in range(1, ROLLOUTS_PER_TASK + 1)
    ]
    return {"parent": copy.deepcopy(units), "candidate": copy.deepcopy(units)}


def _validate_batch_map(batch_map: dict[str, Any], campaign: dict[str, Any]) -> None:
    if batch_map.get("schema_version") != "tau3_gse_task_split_0.12.0" or batch_map.get("campaign_seed") != campaign["campaign_seed"]:
        raise RuntimeContractError("Frozen v0.12 Batch Map identity is invalid.")
    assignment = batch_map.get("assignment", {})
    if any(len(assignment.get("evolution", {}).get(domain, [])) != 30 for domain in ("airline", "retail")) or any(len(assignment.get("holdout", {}).get(domain, [])) != 20 for domain in ("airline", "retail")):
        raise RuntimeContractError("Frozen assignment is invalid.")
    flattened = []
    for index, batch in enumerate(batch_map.get("batches", []), start=1):
        ids = batch.get("task_ids", [])
        if batch.get("batch_id") != f"batch_{index}" or len(ids) != 20 or sum(x.startswith("airline:") for x in ids) != 10 or sum(x.startswith("retail:") for x in ids) != 10:
            raise RuntimeContractError("Frozen Evolution batch is invalid.")
        flattened.extend(ids)
    if len(batch_map.get("batches", [])) != 3 or len(flattened) != 60 or len(set(flattened)) != 60:
        raise RuntimeContractError("Evolution batches are not a 60-task partition.")


def build_campaign_dry_plan(campaign: dict[str, Any], batch_map: dict[str, Any]) -> dict[str, Any]:
    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    steps = []
    for index, batch in enumerate(batch_map["batches"], start=1):
        replay = matched_replay_plan(batch["task_ids"], campaign["campaign_seed"])
        steps.append({
            "step": index, "batch_id": batch["batch_id"], "task_ids": copy.deepcopy(batch["task_ids"]),
            "parent_units": replay["parent"], "candidate_replay_units": replay["candidate"],
            "parent_trajectories": 60, "maximum_candidate_replay_trajectories": 60,
            "maximum_parent_diagnosis_calls": 20, "maximum_editor_calls": 1,
            "maximum_targeted_fix_calls": 18, "maximum_regression_diagnosis_calls": 60,
            "matched_seed_lineage": replay["parent"] == replay["candidate"], "replay_previous_batches": False,
        })
    computed = {
        "evolution_parent_trajectories": 180, "maximum_candidate_replay_trajectories": 180,
        "maximum_evolution_trajectories": 360, "final_holdout_trajectories_if_authorized": 240,
        "maximum_total_including_holdout": 600, "maximum_candidates": 3,
        "maximum_parent_diagnosis_calls": 60, "maximum_editor_calls": 3,
        "maximum_targeted_fix_calls": 54, "maximum_regression_diagnosis_calls": 180,
    }
    if computed != campaign["budget"]:
        raise RuntimeContractError("Dry-plan workload and budget disagree.")
    holdout_ids = [*(f"airline:{x}" for x in batch_map["assignment"]["holdout"]["airline"]), *(f"retail:{x}" for x in batch_map["assignment"]["holdout"]["retail"])]
    return {
        "schema_version": "autonomous_gse_dry_plan_0.12.0", "campaign_id": campaign["campaign_id"],
        "mode": "no_api_no_rollout_no_write", "steps": steps, "computed_budget": computed,
        "selection_workload": None,
        "holdout": {"authorized": False, "included_in_evolution_run": False, "task_ids": holdout_ids, "skills": ["S0", "S_final"], "trajectories_if_explicitly_authorized": 240},
    }


class Tau3RolloutAdapter:
    def __init__(self, campaign: dict[str, Any], *, repo_root: Path, judge_caller: JudgeCaller) -> None:
        from src.skill_evolution.autonomous_gse_v09_benchmark_runtime import Tau3RolloutAdapter as V09RolloutAdapter

        validate_campaign_contract(campaign)
        delegate = object.__new__(V09RolloutAdapter)
        delegate.campaign = copy.deepcopy(campaign)
        delegate.campaign["test"] = {"formal_run_authorized": True}
        delegate.repo_root = repo_root.resolve()
        delegate.tau2_root = (delegate.repo_root / campaign["benchmark"]["path"]).resolve()
        delegate.judge_caller = judge_caller
        self._delegate = delegate

    def run(self, **kwargs: Any) -> Any:
        return self._delegate.run(**kwargs)


class Tau3CampaignRolloutBackend:
    def __init__(self, campaign: dict[str, Any], *, judge_caller: JudgeCaller = default_judge_caller, artifact_root: Path | None = None) -> None:
        validate_campaign_contract(campaign)
        self.campaign = copy.deepcopy(campaign)
        self.artifact_root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "formal"
        self.max_concurrency = campaign["execution"]["max_concurrency"]
        self.rollout = Tau3RolloutAdapter(campaign, repo_root=REPO_ROOT, judge_caller=judge_caller)

    def _reusable(self, path: Path, *, domain: str, task_id: str, phase: str, version: str, rollout_index: int, seed: int) -> bool:
        try:
            value = _load_json(path)
            provenance = value["provenance"]
            raw = _load_json(_resolved_path(provenance["raw_tau3_result_path"]))
            evaluation = official_task_evaluation(raw)
            trajectory = stable_trajectory(raw.get("messages") or [])
            compliance, governed = value["compliance_evaluation"], value["governed_evidence"]
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return False
        expected_lineage = {"rollout_seed": seed, "agent_seed": seed, "user_simulator_seed": seed, "environment_seed": seed}
        if value.get("schema_version") != "tau3_gse_rollout_0.9.0" or value.get("domain") != domain or value.get("task_id") != task_id or value.get("phase") != phase or value.get("skill_version") != version or value.get("rollout_index") != rollout_index or value.get("rollout_seed") != seed or value.get("seed_lineage") != expected_lineage:
            return False
        if raw.get("task_id") != task_id or not trajectory or value.get("trajectory") != trajectory or value.get("task_evaluation") != evaluation or governed.get("trajectory") != trajectory or governed.get("task_evaluation") != evaluation or governed.get("compliance_evaluation") != compliance:
            return False
        if provenance.get("agent_config") != self.campaign["agent"] or provenance.get("user_simulator_config") != self.campaign["user_simulator"] or provenance.get("official_evaluator_config") != self.campaign["official_evaluator"]:
            return False
        if compliance.get("judge_model") != self.campaign["compliance_judge"]["model"] or compliance.get("judge_temperature") != self.campaign["compliance_judge"]["temperature"] or compliance.get("judge_prompt_version") != self.campaign["compliance_judge"]["prompt_version"] or not isinstance(compliance.get("compliant"), bool) or not isinstance(compliance.get("violations"), list):
            return False
        compliant = compliance["compliant"]
        if compliant == bool(compliance["violations"]):
            return False
        expected_state = "compliant_success" if evaluation["success"] and compliant else "violating_success" if evaluation["success"] else "compliant_failure" if compliant else "violating_failure"
        return value.get("state") == expected_state and governed.get("state") == expected_state and governed.get("task_success") is evaluation["success"]

    def run_batch(self, *, task_ids: list[str], phase: str, skill_version: str, skill_path: Path | None, execution_phase: str, execution_seed_offset: int = 0) -> list[Path]:
        seeds = derive_rollout_seeds(self.campaign["campaign_seed"], execution_seed_offset)
        paths, pending = [], []
        for domain_task in task_ids:
            domain, task_id = domain_task.split(":", 1)
            for rollout_index, seed in enumerate(seeds, start=1):
                output = self.artifact_root / "rollouts" / phase / execution_phase / f"{domain}_{task_id}_rollout_{rollout_index:02d}.json"
                paths.append(output)
                if not self._reusable(output, domain=domain, task_id=task_id, phase=phase, version=skill_version, rollout_index=rollout_index, seed=seed):
                    pending.append({"domain": domain, "task_id": task_id, "phase": phase, "skill_version": skill_version, "skill_path": None if skill_version == "S0" else skill_path, "rollout_index": rollout_index, "rollout_seed": seed, "output_path": output})
        with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            tuple(executor.map(lambda kwargs: self.rollout.run(**kwargs), pending))
        return paths


def _method_skill(text: str) -> str:
    return text.replace("# Operational Skill", "# SuiteCRM Operational Skill", 1)


def _canonical_skill(text: str) -> str:
    return text.replace("# SuiteCRM Operational Skill", "# Operational Skill", 1)


def _rows_and_evidence(paths: list[Path], *, step: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, experiences = [], []
    for path in paths:
        value = _load_json(path)
        index = value["rollout_index"]
        source_id = f"step_{step:03d}_{value['domain']}_{value['task_id']}_rollout_{index:02d}"
        experience = copy.deepcopy(value["governed_evidence"])
        experience.update({"source_id": source_id, "domain": value["domain"], "task_id": value["task_id"], "rollout_index": index, "rollout_seed": value["rollout_seed"]})
        experiences.append(experience)
        rows.append({"source_id": source_id, "domain": value["domain"], "task_id": value["task_id"], "rollout_index": index, "rollout_seed": value["rollout_seed"], "task_success": value["task_evaluation"]["success"], "compliant": value["compliance_evaluation"]["compliant"], "state": value["state"], "trajectory": experience, "artifact_path": path.as_posix()})
    return rows, experiences


def _candidate_edit_provenance(decision: Any) -> list[dict[str, Any]]:
    signals = {item["patch_id"]: item for item in decision.raw_patches}
    result = []
    for edit in decision.applied_edits:
        source = [signals[value] for value in edit["derived_from_patch_ids"]]
        result.append({**copy.deepcopy(edit), "final_text": edit.get("text", ""), "derived_from_diagnosis_ids": list(dict.fromkeys(item["diagnosis_id"] for item in source)), "objective": " | ".join(dict.fromkeys(item["objective"] for item in source)), "description": " | ".join(dict.fromkeys(item["description"] for item in source))})
    return result


def _load_completed_targeted_fix_results(
    path: Path, edits: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    report = _load_json(path)
    results = report.get("results")
    if not isinstance(results, list):
        raise RuntimeContractError("Saved Target Fix progress is invalid.")
    expected_ids = {edit["canonical_edit_id"] for edit in edits}
    completed_ids = [item.get("canonical_edit_id") for item in results if isinstance(item, dict)]
    if (
        len(completed_ids) != len(results)
        or len(completed_ids) != len(set(completed_ids))
        or not set(completed_ids) <= expected_ids
    ):
        raise RuntimeContractError("Saved Target Fix result lineage is invalid.")
    return copy.deepcopy(results)


def _evaluate_candidate_step(
    *,
    root: Path,
    step_root: Path,
    step_number: int,
    parent_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    diagnoses: list[dict[str, Any]],
    edits: list[dict[str, Any]],
    targeted_fix_judge: Callable[[TargetedFixRequest], dict[str, Any]],
    regression_judge: Callable[[Any], dict[str, Any]] | None,
    reset_targeted_fix_results: bool = False,
    reuse_regression_diagnoses: bool = False,
) -> dict[str, Any]:
    parent_by_key = {
        (row["domain"], row["task_id"], row["rollout_index"]): row
        for row in parent_rows
    }
    candidate_by_key = {
        (row["domain"], row["task_id"], row["rollout_index"]): row
        for row in candidate_rows
    }
    if set(parent_by_key) != set(candidate_by_key):
        raise RuntimeContractError("Parent/Candidate matched replay lineage is incomplete.")
    for key in parent_by_key:
        if parent_by_key[key]["rollout_seed"] != candidate_by_key[key]["rollout_seed"]:
            raise RuntimeContractError("Parent/Candidate matched replay seeds drifted.")

    diagnosis_by_id = {item["diagnosis_id"]: item for item in diagnoses}
    targeted_path = step_root / "targeted_fix_report.json"
    targeted = [] if reset_targeted_fix_results else _load_completed_targeted_fix_results(
        targeted_path, edits
    )
    completed_edit_ids = {item["canonical_edit_id"] for item in targeted}
    for edit in edits:
        edit_id = edit["canonical_edit_id"]
        if edit_id in completed_edit_ids:
            continue
        try:
            supporting = tuple(
                diagnosis_by_id[value] for value in edit["derived_from_diagnosis_ids"]
            )
        except KeyError as error:
            raise RuntimeContractError("Canonical edit Diagnosis lineage is invalid.") from error
        groups = []
        for diagnosis in supporting:
            parent_group = [
                parent_by_key[(row["domain"], row["task_id"], row["rollout_index"])]
                for row in parent_rows
                if row["source_id"] in diagnosis["source_ids"]
            ]
            keys = [
                (row["domain"], row["task_id"], row["rollout_index"])
                for row in parent_group
            ]
            groups.append({
                "diagnosis_id": diagnosis["diagnosis_id"],
                "parent_rollouts": parent_group,
                "candidate_rollouts": [candidate_by_key[key] for key in keys],
            })
        request = TargetedFixRequest(
            canonical_edit=copy.deepcopy(edit),
            supporting_diagnoses=copy.deepcopy(supporting),
            matched_replays=tuple(groups),
        )
        try:
            result = targeted_fix_judge(request)
        except TargetedFixResponseError as error:
            partial_report = {
                "schema_version": "autonomous_gse_targeted_fix_report_0.12.0",
                "complete": False,
                "results": targeted,
            }
            _write_json(targeted_path, partial_report)
            error_report = {
                "schema_version": "autonomous_gse_targeted_fix_error_0.12.0",
                "protocol_version": PROTOCOL_VERSION,
                "step": step_number,
                "canonical_edit_id": error.canonical_edit_id or edit_id,
                "error_code": error.code,
                "raw_response": error.raw_response,
                "completed_targeted_fix_results": copy.deepcopy(targeted),
            }
            _write_json(step_root / "targeted_fix_error.json", error_report)
            _write_json(root / "targeted_fix_error.json", error_report)
            raise
        if result.get("canonical_edit_id") != edit_id:
            raise RuntimeContractError("Target Fix result canonical edit lineage is invalid.")
        targeted.append(result)
        completed_edit_ids.add(edit_id)
        _write_json(targeted_path, {
            "schema_version": "autonomous_gse_targeted_fix_report_0.12.0",
            "complete": False,
            "results": targeted,
        })
    _write_json(targeted_path, {
        "schema_version": "autonomous_gse_targeted_fix_report_0.12.0",
        "complete": True,
        "results": targeted,
    })
    (step_root / "targeted_fix_error.json").unlink(missing_ok=True)
    (root / "targeted_fix_error.json").unlink(missing_ok=True)

    from src.skill_evolution.regression_diagnosis_v11 import (
        RegressionDiagnosisRequest,
        RegressionDiagnosisResponseError,
        build_regression_transition_report,
        call_regression_diagnosis,
    )

    transitions = build_regression_transition_report(parent_rows, candidate_rows)
    _write_json(step_root / "regression_transition_report.json", transitions)
    regression_path = step_root / "regression_diagnoses.json"
    if reuse_regression_diagnoses:
        if not regression_path.is_file():
            raise RuntimeContractError("Saved Regression Diagnoses are required for re-evaluation.")
        regression_diagnoses = _load_json(regression_path).get("diagnoses")
        expected_pair_ids = [item["pair_id"] for item in transitions["regression_set"]]
        actual_pair_ids = [
            item.get("pair_id") for item in regression_diagnoses
            if isinstance(item, dict)
        ] if isinstance(regression_diagnoses, list) else []
        if actual_pair_ids != expected_pair_ids:
            raise RuntimeContractError("Saved Regression Diagnosis lineage is invalid.")
    else:
        regression_judge = regression_judge or call_regression_diagnosis
        regression_diagnoses = []
    error_path = step_root / "regression_diagnosis_error.json"
    for regression in [] if reuse_regression_diagnoses else transitions["regression_set"]:
        key = (regression["domain"], regression["task_id"], regression["rollout_index"])
        before, after = parent_by_key[key], candidate_by_key[key]
        request = RegressionDiagnosisRequest(
            pair_id=regression["pair_id"],
            domain=regression["domain"],
            task_context={"domain": regression["domain"], "task_id": regression["task_id"]},
            regression_type=regression["regression_type"],
            parent_state=before["state"],
            candidate_state=after["state"],
            candidate_edits=tuple(copy.deepcopy(edits)),
            parent_trajectory=before["trajectory"],
            candidate_trajectory=after["trajectory"],
        )
        try:
            regression_diagnoses.append(regression_judge(request))
        except RegressionDiagnosisResponseError as error:
            _write_json(error_path, {
                "schema_version": "autonomous_gse_regression_diagnosis_error_0.12.0",
                "pair_id": request.pair_id,
                "error_code": error.code,
                "raw_response": error.raw_response,
                "completed_regression_diagnoses": len(regression_diagnoses),
            })
            raise
    error_path.unlink(missing_ok=True)
    _write_json(regression_path, {"diagnoses": regression_diagnoses})
    _write_json(step_root / "aggregate_metrics.json", {
        "parent": aggregate_counts(parent_rows),
        "candidate": aggregate_counts(candidate_rows),
    })
    decision = build_evolution_decision(
        applied_canonical_edits=edits,
        targeted_fix_results=targeted,
        regression_diagnoses=regression_diagnoses,
        parent_rows=parent_rows,
        candidate_rows=candidate_rows,
    )
    _write_json(step_root / "evolution_decision.json", decision)
    return decision


def run_v12_campaign(
    campaign: dict[str, Any], batch_map: dict[str, Any], *,
    backend: Tau3CampaignRolloutBackend | None = None,
    diagnoser: Callable[[Any], str] = call_diagnosis,
    editor: Callable[[Any], str] = call_governed_editor,
    targeted_fix_judge: Callable[[TargetedFixRequest], dict[str, Any]] = call_targeted_fix,
    regression_judge: Callable[[Any], dict[str, Any]] | None = None,
    artifact_root: Path | None = None, resume_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "formal"
    backend = backend or Tau3CampaignRolloutBackend(campaign, artifact_root=root)
    completed_steps, report_steps = 0, []
    if resume_state is not None:
        if resume_state.get("protocol_version") != PROTOCOL_VERSION:
            raise RuntimeContractError("v0.12 resume protocol is invalid.")
        completed_steps = resume_state.get("completed_steps")
        if not isinstance(completed_steps, int) or not 0 <= completed_steps <= 3:
            raise RuntimeContractError("v0.12 completed Step count is invalid.")
        parent, report_steps = copy.deepcopy(resume_state.get("current_parent")), copy.deepcopy(resume_state.get("steps"))
        if not isinstance(parent, dict) or not isinstance(report_steps, list) or len(report_steps) != completed_steps:
            raise RuntimeContractError("v0.12 resume state is invalid.")
    else:
        parent = copy.deepcopy(campaign["initial_parent"])
    parent_path = _resolved_path(parent["path"])
    if not parent_path.is_file():
        raise RuntimeContractError("Current Parent Skill artifact is missing.")
    operator = MultiRolloutDiagnosisProposalOperator()
    for step_number, batch in enumerate(batch_map["batches"], start=1):
        if step_number <= completed_steps:
            continue
        step_root, step_parent = root / "steps" / f"step_{step_number:03d}", copy.deepcopy(parent)
        parent_paths = backend.run_batch(task_ids=batch["task_ids"], phase="train", skill_version=parent["version"], skill_path=parent_path, execution_phase=f"step_{step_number:03d}_parent")
        parent_rows, experiences = _rows_and_evidence(parent_paths, step=step_number)
        try:
            proposal = operator.propose(ProposalContext(candidate_id=f"candidate_{step_number:03d}", parent_skill=_method_skill(parent_path.read_text(encoding="utf-8")), current_batch_governed_evidence=tuple(experiences)), diagnoser, editor)
        except DiagnosisContractError as error:
            diagnoses = [item.as_dict() for item in error.validations]
            _write_json(step_root / "diagnoses.json", {
                "diagnoses": diagnoses,
                "eligible_diagnosis_ids": [],
            })
            report = {
                "schema_version": "autonomous_gse_diagnosis_contract_error_0.12.0",
                "protocol_version": PROTOCOL_VERSION,
                "step": step_number,
                "batch_id": batch["batch_id"],
                "error_code": error.code,
                "invalid_diagnosis_ids": list(error.invalid_diagnosis_ids),
                "diagnoses": diagnoses,
            }
            _write_json(step_root / "diagnosis_contract_error.json", report)
            _write_json(root / "diagnosis_contract_error.json", report)
            raise
        _write_json(step_root / "diagnoses.json", {"diagnoses": proposal.diagnoses, "eligible_diagnosis_ids": proposal.eligible_diagnosis_ids})
        _write_json(step_root / "proposal.json", copy.deepcopy(proposal.__dict__))
        if proposal.proposal_status != "CANDIDATE" or proposal.candidate_skill is None:
            decision = no_candidate_decision()
            _write_json(step_root / "evolution_decision.json", decision)
            report_steps.append({"step": step_number, "batch_id": batch["batch_id"], "parent": step_parent, "promoted_parent": copy.deepcopy(parent), "candidate": None, **decision})
            _write_json(root / "resume_state.json", {"protocol_version": PROTOCOL_VERSION, "completed_steps": step_number, "current_parent": parent, "steps": report_steps})
            continue
        candidate_version = f"S{step_number}"
        candidate_path = step_root / "candidate_skill.md"
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(_canonical_skill(proposal.candidate_skill), encoding="utf-8")
        edits = _candidate_edit_provenance(proposal)
        _write_json(step_root / "candidate_edits.json", edits)
        candidate_paths = backend.run_batch(task_ids=batch["task_ids"], phase="train", skill_version=candidate_version, skill_path=candidate_path, execution_phase=f"step_{step_number:03d}_candidate_replay")
        candidate_rows, _ = _rows_and_evidence(candidate_paths, step=step_number)
        decision = _evaluate_candidate_step(
            root=root,
            step_root=step_root,
            step_number=step_number,
            parent_rows=parent_rows,
            candidate_rows=candidate_rows,
            diagnoses=proposal.diagnoses,
            edits=edits,
            targeted_fix_judge=targeted_fix_judge,
            regression_judge=regression_judge,
        )
        candidate = {"kind": "candidate_skill", "version": candidate_version, "path": candidate_path.as_posix()}
        if decision["decision"] == "ACCEPT":
            parent, parent_path = candidate, candidate_path
        report_steps.append({"step": step_number, "batch_id": batch["batch_id"], "parent": step_parent, "promoted_parent": copy.deepcopy(parent), "candidate": candidate, **decision})
        _write_json(root / "resume_state.json", {"protocol_version": PROTOCOL_VERSION, "completed_steps": step_number, "current_parent": parent, "steps": report_steps})
    report = {"schema_version": "autonomous_gse_formal_report_0.12.0", "protocol_version": PROTOCOL_VERSION, "campaign_id": campaign["campaign_id"], "mode": FORMAL_MODE, "steps": report_steps, "final_skill": parent, "disabled_phases": {"official_test_holdout": True}}
    _write_json(root / "campaign_report.json", report)
    return report


def reevaluate_v12_step_1_target_fix_and_gate(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    *,
    targeted_fix_judge: Callable[[TargetedFixRequest], dict[str, Any]] = call_targeted_fix,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    """Rejudge saved Step 1 Target Fix evidence and recompute its Gate only."""
    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "formal"
    if (root / "campaign_report.json").exists():
        raise RuntimeContractError("A completed campaign cannot be re-evaluated in place.")
    resume_path = root / "resume_state.json"
    if not resume_path.is_file():
        raise RuntimeContractError("Step 1 resume state is required for re-evaluation.")
    resume_state = _load_json(resume_path)
    if (
        resume_state.get("protocol_version") != PROTOCOL_VERSION
        or resume_state.get("completed_steps") != 1
        or not isinstance(resume_state.get("steps"), list)
        or len(resume_state["steps"]) != 1
    ):
        raise RuntimeContractError("Re-evaluation requires exactly one completed Step.")

    step_root = root / "steps" / "step_001"
    required = {
        "diagnoses": step_root / "diagnoses.json",
        "edits": step_root / "candidate_edits.json",
        "candidate": step_root / "candidate_skill.md",
        "targeted": step_root / "targeted_fix_report.json",
        "regression": step_root / "regression_diagnoses.json",
        "decision": step_root / "evolution_decision.json",
    }
    if not all(path.is_file() for path in required.values()):
        raise RuntimeContractError("A required saved Step 1 artifact is missing.")
    backups = {
        "targeted": step_root / "targeted_fix_report.before_prompt_grounding.json",
        "decision": step_root / "evolution_decision.before_prompt_grounding.json",
    }
    if not backups["targeted"].exists():
        _write_json(backups["targeted"], _load_json(required["targeted"]))
    if not backups["decision"].exists():
        _write_json(backups["decision"], _load_json(required["decision"]))

    diagnoses = _load_json(required["diagnoses"]).get("diagnoses")
    edits = _load_json(required["edits"])
    if not isinstance(diagnoses, list) or not isinstance(edits, list) or not edits:
        raise RuntimeContractError("Saved Step 1 Diagnosis/edit artifacts are invalid.")
    rollout_root = root / "rollouts" / "train"
    parent_paths = sorted(
        path for path in (rollout_root / "step_001_parent").glob("*.json")
        if not path.name.endswith("_tau3_raw.json")
    )
    candidate_paths = sorted(
        path for path in (rollout_root / "step_001_candidate_replay").glob("*.json")
        if not path.name.endswith("_tau3_raw.json")
    )
    if len(parent_paths) != 60 or len(candidate_paths) != 60:
        raise RuntimeContractError("Step 1 re-evaluation requires 60+60 saved rollouts.")
    parent_rows, _ = _rows_and_evidence(parent_paths, step=1)
    candidate_rows, _ = _rows_and_evidence(candidate_paths, step=1)
    decision = _evaluate_candidate_step(
        root=root,
        step_root=step_root,
        step_number=1,
        parent_rows=parent_rows,
        candidate_rows=candidate_rows,
        diagnoses=diagnoses,
        edits=edits,
        targeted_fix_judge=targeted_fix_judge,
        regression_judge=None,
        reset_targeted_fix_results=True,
        reuse_regression_diagnoses=True,
    )

    previous_step = resume_state["steps"][0]
    candidate = previous_step.get("candidate")
    parent = previous_step.get("parent")
    if not isinstance(candidate, dict) or not isinstance(parent, dict):
        raise RuntimeContractError("Saved Step 1 promotion lineage is invalid.")
    promoted_parent = candidate if decision["decision"] == "ACCEPT" else parent
    step_report = {
        "step": 1,
        "batch_id": batch_map["batches"][0]["batch_id"],
        "parent": parent,
        "promoted_parent": copy.deepcopy(promoted_parent),
        "candidate": candidate,
        **decision,
    }
    updated_resume = {
        "protocol_version": PROTOCOL_VERSION,
        "completed_steps": 1,
        "current_parent": promoted_parent,
        "steps": [step_report],
    }
    _write_json(resume_path, updated_resume)
    return {
        "schema_version": "autonomous_gse_step_1_reevaluation_0.12.0",
        "protocol_version": PROTOCOL_VERSION,
        "reused": {
            "parent_rollouts": 60,
            "candidate_rollouts": 60,
            "diagnoses": len(diagnoses),
            "canonical_edits": len(edits),
            "regression_diagnoses": len(_load_json(required["regression"])["diagnoses"]),
        },
        "step": step_report,
    }


def build_holdout_plan(campaign: dict[str, Any], batch_map: dict[str, Any], final_skill: dict[str, Any]) -> dict[str, Any]:
    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    task_ids = [*(f"airline:{x}" for x in batch_map["assignment"]["holdout"]["airline"]), *(f"retail:{x}" for x in batch_map["assignment"]["holdout"]["retail"])]
    units = matched_replay_plan(task_ids, campaign["campaign_seed"])
    return {"schema_version": "autonomous_gse_holdout_plan_0.12.0", "source_split": "official_test", "task_ids": task_ids, "skills": [copy.deepcopy(campaign["initial_parent"]), copy.deepcopy(final_skill)], "s0_units": units["parent"], "s_final_units": units["candidate"], "matched_seed_lineage": True, "trajectory_count": 240, "learning_calls": 0}


def evaluate_holdout(campaign: dict[str, Any], batch_map: dict[str, Any], final_skill: dict[str, Any], *, backend: Tau3CampaignRolloutBackend | None = None, artifact_root: Path | None = None) -> dict[str, Any]:
    plan = build_holdout_plan(campaign, batch_map, final_skill)
    root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "holdout"
    backend = backend or Tau3CampaignRolloutBackend(campaign, artifact_root=root)
    results = {}
    for label, skill in (("S0", campaign["initial_parent"]), ("S_final", final_skill)):
        paths = backend.run_batch(task_ids=plan["task_ids"], phase="test", skill_version=skill["version"], skill_path=_resolved_path(skill["path"]), execution_phase=label.casefold())
        rows, _ = _rows_and_evidence(paths, step=0)
        results[label] = {**{domain: aggregate_counts([row for row in rows if row["domain"] == domain]) for domain in ("airline", "retail")}, "overall": aggregate_counts(rows)}
    report = {"schema_version": "autonomous_gse_holdout_report_0.12.0", "campaign_id": campaign["campaign_id"], "source_split": "official_test", "task_count": 40, "trajectory_count": 240, "compare": ["S0", "S_final"], "metrics": results, "learning_calls": 0, "feedback_to_learner": "forbidden"}
    _write_json(root / "holdout_report.json", report)
    return report


def _campaign_files(campaign_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    campaign = _load_json(campaign_path)
    return campaign, _load_json(_resolved_path(campaign["evolution"]["batch_map"]))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "run", "resume", "reevaluate-step-1", "evaluate-holdout"):
        item = sub.add_parser(command)
        item.add_argument("--campaign", type=Path, required=True)
    args = parser.parse_args(argv)
    campaign, batch_map = _campaign_files(args.campaign.resolve())
    if args.command == "plan":
        print(json.dumps(build_campaign_dry_plan(campaign, batch_map), indent=2))
        return 0
    root = REPO_ROOT / "artifacts" / campaign["campaign_id"] / "formal"
    if args.command == "evaluate-holdout":
        report_path = root / "campaign_report.json"
        if not report_path.is_file():
            raise RuntimeContractError("Evolution report is required before Holdout.")
        print(json.dumps(evaluate_holdout(campaign, batch_map, _load_json(report_path)["final_skill"], artifact_root=REPO_ROOT / "artifacts" / campaign["campaign_id"] / "holdout"), indent=2))
        return 0
    if args.command == "reevaluate-step-1":
        print(json.dumps(reevaluate_v12_step_1_target_fix_and_gate(
            campaign, batch_map, artifact_root=root
        ), indent=2))
        return 0
    if args.command == "resume" and not (root / "resume_state.json").is_file():
        raise RuntimeContractError("No v0.12 resume state is available.")
    resume_state = _load_json(root / "resume_state.json") if args.command == "resume" else None
    print(json.dumps(run_v12_campaign(campaign, batch_map, artifact_root=root, resume_state=resume_state), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
