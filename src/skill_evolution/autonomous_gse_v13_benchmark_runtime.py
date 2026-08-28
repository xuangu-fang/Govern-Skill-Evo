"""K=3 matched-replay τ³ runtime for Autonomous GSE v0.13."""

from __future__ import annotations

import argparse
import ast
import copy
import json
import shutil
import traceback
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from src.adapters.tau2.tau3_compliance_judge_v13 import (
    ComplianceJudgeError, JUDGE_MODEL, JUDGE_PROMPT_VERSION, JUDGE_TEMPERATURE, JudgeCaller,
    compatibility_policy_id, default_judge_caller, judge_compliance,
    policy_clause_is_excluded,
)
from src.adapters.tau2.tau3_gse_runtime import (
    official_task_evaluation, stable_trajectory, task_context,
)
from src.learners.stwebagentbench.generate_governed_skill_v13 import call_governed_editor
from src.skill_evolution import autonomous_gse_v09_benchmark_runtime as v09
from src.skill_evolution import autonomous_gse_v12_benchmark_runtime as v12
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v13_proposal import (
    DiagnosisContractError, MultiRolloutDiagnosisProposalOperator,
)
from src.skill_evolution.diagnosis_v13 import call_diagnosis
from src.skill_evolution.evolution_gate_v11 import aggregate_counts
from src.skill_evolution.evolution_gate_v13 import build_evolution_decision, no_candidate_decision
from src.skill_evolution.targeted_fix_v13 import (
    TargetedFixRequest, TargetedFixResponseError, call_targeted_fix,
)
from src.skill_evolution.two_dimensional_gate import classify_state

PROTOCOL_VERSION = "autonomous_gse_v13"
FORMAL_MODE = "formal_tau3_airline_retail_v13_k3_matched_behavior_replay"
REPO_ROOT = Path(__file__).resolve().parents[2]
ROLLOUTS_PER_TASK = 3
EVIDENCE_CONTRACT_VERSION = "policy_tool_behavior_grounded_v13"


class RuntimeContractError(ValueError):
    """Raised when a v0.13 campaign/runtime invariant is violated."""


def _tool_contracts_from_authoritative_source(tools_path: Path) -> tuple[dict[str, Any], ...]:
    """Extract the public @is_tool interface without importing or sending Python source."""

    module = ast.parse(tools_path.read_text(encoding="utf-8"), filename=tools_path.as_posix())
    contracts: list[dict[str, Any]] = []
    for node in ast.walk(module):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        is_tool = any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, (ast.Name, ast.Attribute))
            and getattr(decorator.func, "id", getattr(decorator.func, "attr", None)) == "is_tool"
            for decorator in node.decorator_list
        )
        if not is_tool:
            continue
        positional = [argument.arg for argument in node.args.args if argument.arg not in {"self", "cls"}]
        defaults_start = len(positional) - len(node.args.defaults)
        required = positional[:defaults_start]
        optional = positional[defaults_start:]
        kwonly = [argument.arg for argument in node.args.kwonlyargs]
        for name, default in zip(kwonly, node.args.kw_defaults):
            (required if default is None else optional).append(name)
        description = ast.get_docstring(node, clean=True) or ""
        description = description.split("\nArgs:", 1)[0].split("\nReturns:", 1)[0].strip()
        contracts.append({
            "tool_name": node.name,
            "arguments": [*positional, *kwonly],
            "required_arguments": required,
            "optional_arguments": optional,
            "description": " ".join(description.split()),
        })
    return tuple(sorted(contracts, key=lambda item: item["tool_name"]))


def load_authoritative_domain_contexts(
    tau2_root: Path,
) -> dict[str, dict[str, Any]]:
    contexts: dict[str, dict[str, Any]] = {}
    for domain in ("airline", "retail"):
        policy_path = tau2_root / f"data/tau2/domains/{domain}/policy.md"
        tools_path = tau2_root / f"src/tau2/domains/{domain}/tools.py"
        if not policy_path.is_file() or not tools_path.is_file():
            raise RuntimeContractError(f"Authoritative {domain} Policy/tool definitions are missing.")
        contexts[domain] = {
            "original_domain_policy": policy_path.read_text(encoding="utf-8"),
            "available_tool_contracts": _tool_contracts_from_authoritative_source(tools_path),
        }
    return contexts


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
        campaign.get("schema_version") != "autonomous_gse_campaign_0.13.0"
        or campaign.get("protocol_version") != PROTOCOL_VERSION
        or campaign.get("campaign_id") != PROTOCOL_VERSION
        or campaign.get("campaign_seed") != 200
    ):
        raise RuntimeContractError("τ³ v0.13 Campaign identity is invalid.")
    if campaign.get("benchmark", {}).get("name") != "tau3" or campaign["benchmark"].get("domains") != ["airline", "retail"]:
        raise RuntimeContractError("v0.13 supports only τ³ Airline/Retail.")
    if campaign.get("schedule") != {"evolution_steps": 3}:
        raise RuntimeContractError("v0.13 requires exactly three Steps.")
    evolution = campaign.get("evolution", {})
    if any((
        evolution.get("source_split") != "official_train", evolution.get("tasks") != 60,
        evolution.get("airline_tasks") != 30, evolution.get("retail_tasks") != 30,
        evolution.get("batches") != 3, evolution.get("tasks_per_batch") != 20,
        evolution.get("airline_tasks_per_batch") != 10, evolution.get("retail_tasks_per_batch") != 10,
        evolution.get("rollouts_per_task") != 3, evolution.get("cumulative_evidence") is not False,
        evolution.get("replay_previous_batches") is not False,
    )):
        raise RuntimeContractError("v0.13 Evolution workload drifted.")
    if "selection" in campaign:
        raise RuntimeContractError("v0.13 must not define Selection.")
    holdout = campaign.get("holdout", {})
    if any((
        holdout.get("source_split") != "official_test", holdout.get("tasks") != 40,
        holdout.get("airline_tasks") != 20, holdout.get("retail_tasks") != 20,
        holdout.get("rollouts_per_task") != 3, holdout.get("compare") != ["S0", "S_final"],
        holdout.get("learning_access") != "forbidden", holdout.get("feedback_to_learner") != "forbidden",
        holdout.get("automatic_execution") is not False,
    )):
        raise RuntimeContractError("v0.13 Holdout contract drifted.")
    frozen = {
        "model": "openai/deepseek-v4-flash", "temperature": 0.0, "thinking": "high",
        "reasoning_effort": "high", "max_tokens": 8192, "empty_response_retries": 2,
        "empty_response_retry_max_tokens": 8192,
    }
    for role in ("agent", "user_simulator"):
        if any(campaign.get(role, {}).get(key) != value for key, value in frozen.items()):
            raise RuntimeContractError(f"Frozen {role} sampling configuration drifted.")
    if campaign.get("compliance_judge", {}) != {
        "model": JUDGE_MODEL, "temperature": JUDGE_TEMPERATURE,
        "prompt_version": JUDGE_PROMPT_VERSION,
        "frozen_across_phases_and_methods": True,
        "failure_mode": "COMPLIANCE_JUDGE_ERROR", "fallback": "forbidden",
    }:
        raise RuntimeContractError("v0.13 Compliance Judge drifted.")
    evaluator = campaign.get("official_evaluator", {})
    if evaluator.get("implementation") != "tau3_official_evaluator" or evaluator.get("nl_assertions_model") != "openai/gpt-5.6-luna" or evaluator.get("nl_assertions_temperature") != 0.0:
        raise RuntimeContractError("Official evaluator drifted.")
    method = campaign.get("skill_evolution", {})
    if any((
        method.get("proposal_operator") != "v13_dual_axis_mechanism_preserving_bounded_edit",
        method.get("diagnosis_calls_per_task") != 1,
        method.get("targeted_fix_unit") != "canonical_edit_matched_behavior",
        method.get("counterevidence_enabled") is not True,
        method.get("allowed_operations") != ["add", "replace", "delete"],
        method.get("maximum_skill_rules") != 18, method.get("maximum_skill_words") != 900,
        method.get("maximum_editor_calls_per_step") != 1,
        method.get("regression_feedback_to_editor") != "forbidden",
    )):
        raise RuntimeContractError("v0.13 method semantics drifted.")
    expected_budget = {
        "evolution_parent_trajectories": 180, "maximum_candidate_replay_trajectories": 180,
        "maximum_evolution_trajectories": 360, "final_holdout_trajectories_if_authorized": 240,
        "maximum_total_including_holdout": 600, "maximum_candidates": 3,
        "maximum_parent_diagnosis_calls": 60, "maximum_editor_calls": 3,
        "maximum_targeted_fix_calls": 54, "maximum_regression_diagnosis_calls": 180,
    }
    if campaign.get("budget") != expected_budget:
        raise RuntimeContractError("v0.13 budget drifted.")


def derive_rollout_seeds(campaign_seed: int, execution_seed_offset: int, rollouts_per_task: int = 3) -> tuple[int, ...]:
    if rollouts_per_task != ROLLOUTS_PER_TASK:
        raise RuntimeContractError("v0.13 requires exactly three rollouts per task.")
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
    if batch_map.get("schema_version") != "tau3_gse_task_split_0.13.0" or batch_map.get("campaign_seed") != campaign["campaign_seed"]:
        raise RuntimeContractError("Frozen v0.13 Batch Map identity is invalid.")
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
            "matched_seed_lineage": replay["parent"] == replay["candidate"],
            "replay_previous_batches": False,
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
    holdout_ids = [
        *(f"airline:{x}" for x in batch_map["assignment"]["holdout"]["airline"]),
        *(f"retail:{x}" for x in batch_map["assignment"]["holdout"]["retail"]),
    ]
    return {
        "schema_version": "autonomous_gse_dry_plan_0.13.0",
        "campaign_id": campaign["campaign_id"], "mode": "no_api_no_rollout_no_write",
        "steps": steps, "computed_budget": computed, "selection_workload": None,
        "holdout": {
            "authorized": False, "included_in_evolution_run": False,
            "task_ids": holdout_ids, "skills": ["S0", "S_final"],
            "trajectories_if_explicitly_authorized": 240,
        },
    }


def build_policy_grounded_recovery_plan(
    campaign: dict[str, Any], batch_map: dict[str, Any], resume_state: dict[str, Any],
) -> dict[str, Any]:
    """Describe the required restart without running a rollout or model call."""

    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    if (
        resume_state.get("protocol_version") != PROTOCOL_VERSION
        or resume_state.get("completed_steps") != 2
        or resume_state.get("current_parent", {}).get("version") != "S0"
    ):
        raise RuntimeContractError("Policy-grounded recovery expects the paused two-Step S0 run.")
    identity_fields = ["task_id", "initial_state", "rollout_index", "rollout_seed"]
    return {
        "schema_version": "autonomous_gse_policy_grounded_recovery_plan_0.13.0",
        "protocol_version": PROTOCOL_VERSION,
        "run_label": "v13 pre-policy-grounded-diagnosis debugging run",
        "step_3_paused": True,
        "formal_execution_authorized": False,
        "preserve_existing_artifacts": True,
        "restart": [
            "reuse_saved_step_1_s0_raw_parent_trajectories",
            "rerun_compliance_judge_with_policy_and_tool_contracts",
            "regenerate_four_state_evidence",
            "rerun_step_1_diagnosis_and_editor",
            "generate_a_new_candidate_without_reusing_old_candidate_lineage",
            "run_new_matched_candidate_replay_and_existing_downstream_checks",
        ],
        "step_2_parent_rule": {
            "if_new_step_1_rejects": {
                "parent": "S0",
                "reuse_saved_step_2_s0_raw_parent_trajectories_when_identity_matches": identity_fields,
                "then": ["rerun_compliance_judge", "rerun_diagnosis"],
            },
            "if_new_step_1_accepts": {
                "parent": "S1",
                "reuse_old_step_2_s0_parent_trajectories": False,
                "then": ["generate_new_step_2_parent_rollouts"],
            },
        },
    }


def _build_governed_evidence(
    *, source_id: str, domain: str, task: Any, simulation: Any,
    domain_policy: str, available_tool_contracts: Sequence[dict[str, Any]],
    judge_caller: JudgeCaller,
) -> dict[str, Any]:
    simulation_value = simulation.model_dump(mode="json") if hasattr(simulation, "model_dump") else simulation
    evaluation = official_task_evaluation(simulation_value)
    trajectory = stable_trajectory(simulation_value.get("messages") or [])
    judgment = judge_compliance(
        domain_policy, task_context(task, domain=domain), trajectory,
        available_tool_contracts=available_tool_contracts,
        domain=domain, caller=judge_caller,
    )
    violations = []
    for violation in judgment.violations:
        policy_id = compatibility_policy_id(domain, violation.policy_clause)
        violations.append({
            "policy_template_id": policy_id, "policy_id": policy_id,
            "policy_section": violation.policy_section,
            "policy_clause": violation.policy_clause,
            "policy_requirement": violation.policy_clause,
            "description": violation.policy_clause,
            "evidence_steps": list(violation.evidence_steps), "reason": violation.reason,
        })
    state = classify_state(evaluation["success"], judgment.compliant).value
    return {
        "source_id": source_id, "state": state,
        "goal": task_context(task, domain=domain)["user_scenario"],
        "actions": [{"step": item["step"], "action": item["event_type"], **item} for item in trajectory],
        "task_success": evaluation["success"], "task_evaluation": evaluation,
        "applicable_policies": [],
        "process_feedback": {"compliant": judgment.compliant, "violated_policies": violations},
        "compliance_evaluation": {
            "compliant": judgment.compliant, "judge_model": JUDGE_MODEL,
            "judge_temperature": JUDGE_TEMPERATURE,
            "judge_prompt_version": JUDGE_PROMPT_VERSION, "violations": violations,
        },
        "trajectory": trajectory,
    }


class Tau3RolloutAdapter:
    def __init__(self, campaign: dict[str, Any], *, repo_root: Path, judge_caller: JudgeCaller) -> None:
        validate_campaign_contract(campaign)
        self.campaign = copy.deepcopy(campaign)
        self.repo_root = repo_root.resolve()
        self.tau2_root = (self.repo_root / campaign["benchmark"]["path"]).resolve()
        self.judge_caller = judge_caller
        self.domain_contexts = load_authoritative_domain_contexts(self.tau2_root)

    def run(
        self, *, domain: str, task_id: str, phase: str, skill_version: str,
        skill_path: Path | None, rollout_index: int, rollout_seed: int, output_path: Path,
    ) -> dict[str, Any]:
        error_path = output_path.with_name(output_path.stem + "_error.json")
        try:
            task, simulation = v09.run_official_rollout(
                tau2_root=self.tau2_root, domain=domain, task_id=task_id,
                rollout_seed=rollout_seed, agent_config=self.campaign["agent"],
                user_simulator_config=self.campaign["user_simulator"],
                official_evaluator_config=self.campaign["official_evaluator"],
                skill_path=None if skill_version == "S0" else skill_path,
                task_split="test" if phase == "test" else "train",
            )
            policy_path = self.tau2_root / f"data/tau2/domains/{domain}/policy.md"
            domain_context = self.domain_contexts[domain]
            policy = domain_context["original_domain_policy"]
            source_id = f"{phase}_{domain}_{task_id}_rollout_{rollout_index:02d}"
            evidence = _build_governed_evidence(
                source_id=source_id, domain=domain, task=task, simulation=simulation,
                domain_policy=policy,
                available_tool_contracts=domain_context["available_tool_contracts"],
                judge_caller=self.judge_caller,
            )
            raw_result_path = output_path.with_name(output_path.stem + "_tau3_raw.json")
            raw_result_path.parent.mkdir(parents=True, exist_ok=True)
            raw_result_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
            provenance = {
                "raw_tau3_result_path": raw_result_path.as_posix(),
                **v09.policy_provenance(policy_path),
                "task_split": "official_train" if phase != "test" else "official_test",
                "judge_config": copy.deepcopy(self.campaign["compliance_judge"]),
                "agent_config": copy.deepcopy(self.campaign["agent"]),
                "user_simulator_config": copy.deepcopy(self.campaign["user_simulator"]),
                "official_evaluator_config": copy.deepcopy(self.campaign["official_evaluator"]),
            }
            v09.write_rollout_artifact(
                output_path, domain=domain, task_id=task_id, phase=phase,
                skill_version=skill_version, rollout_index=rollout_index,
                rollout_seed=rollout_seed, governed_evidence=evidence, provenance=provenance,
            )
            error_path.unlink(missing_ok=True)
            return evidence
        except Exception as error:
            report = {
                "schema_version": "tau3_gse_rollout_error_0.13.0",
                "domain": domain, "task_id": str(task_id), "phase": phase,
                "skill_version": skill_version, "rollout_index": rollout_index,
                "rollout_seed": rollout_seed, "error_type": type(error).__name__,
                "error_message": str(error), "traceback": traceback.format_exc(),
            }
            if isinstance(error, ComplianceJudgeError):
                report.update({
                    "validation_code": error.validation_code,
                    "raw_judge_response": error.raw_judge_response,
                    "failed_policy_clause": error.failed_policy_clause,
                })
            _write_json(error_path, report)
            raise


class Tau3CampaignRolloutBackend:
    _reusable = v12.Tau3CampaignRolloutBackend._reusable

    def __init__(
        self, campaign: dict[str, Any], *, judge_caller: JudgeCaller = default_judge_caller,
        artifact_root: Path | None = None,
    ) -> None:
        validate_campaign_contract(campaign)
        self.campaign = copy.deepcopy(campaign)
        self.artifact_root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "formal"
        self.max_concurrency = campaign["execution"]["max_concurrency"]
        self.rollout = Tau3RolloutAdapter(campaign, repo_root=REPO_ROOT, judge_caller=judge_caller)

    def run_batch(
        self, *, task_ids: list[str], phase: str, skill_version: str,
        skill_path: Path | None, execution_phase: str, execution_seed_offset: int = 0,
    ) -> list[Path]:
        seeds = derive_rollout_seeds(self.campaign["campaign_seed"], execution_seed_offset)
        paths, pending = [], []
        for domain_task in task_ids:
            domain, task_id = domain_task.split(":", 1)
            for rollout_index, seed in enumerate(seeds, start=1):
                output = self.artifact_root / "rollouts" / phase / execution_phase / f"{domain}_{task_id}_rollout_{rollout_index:02d}.json"
                paths.append(output)
                if not self._reusable(output, domain=domain, task_id=task_id, phase=phase, version=skill_version, rollout_index=rollout_index, seed=seed):
                    pending.append({
                        "domain": domain, "task_id": task_id, "phase": phase,
                        "skill_version": skill_version,
                        "skill_path": None if skill_version == "S0" else skill_path,
                        "rollout_index": rollout_index, "rollout_seed": seed,
                        "output_path": output,
                    })
        with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            tuple(executor.map(lambda kwargs: self.rollout.run(**kwargs), pending))
        return paths


def _rows_and_evidence(paths: list[Path], *, step: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return v12._rows_and_evidence(paths, step=step)


def _candidate_edit_provenance(decision: Any) -> list[dict[str, Any]]:
    return v12._candidate_edit_provenance(decision)


def _validated_targeted_fix_prefix(
    results: Any, edits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(results, list):
        raise RuntimeContractError("Target Fix partial results must be a list.")
    expected_ids = [edit.get("canonical_edit_id") for edit in edits]
    result_ids = [result.get("canonical_edit_id") for result in results if isinstance(result, dict)]
    if len(result_ids) != len(results) or result_ids != expected_ids[:len(result_ids)]:
        raise RuntimeContractError(
            "Target Fix partial results are not a continuous prefix of the current canonical edits."
        )
    for result in results:
        if result.get("status") not in {"FIXED", "NOT_FIXED", "NOT_EXERCISED"}:
            raise RuntimeContractError("Target Fix partial result status is invalid.")
        if not isinstance(result.get("pair_transitions"), list):
            raise RuntimeContractError("Target Fix partial result transitions are invalid.")
    return copy.deepcopy(results)


def _load_targeted_fix_prefix(
    *, root: Path, step_root: Path, step_number: int, edits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    report_path = step_root / "targeted_fix_report.json"
    if report_path.is_file():
        report = _load_json(report_path)
        return _validated_targeted_fix_prefix(report.get("results"), edits)
    for error_path in (step_root / "targeted_fix_error.json", root / "targeted_fix_error.json"):
        if not error_path.is_file():
            continue
        report = _load_json(error_path)
        if report.get("protocol_version") != PROTOCOL_VERSION or report.get("step") != step_number:
            raise RuntimeContractError("Target Fix error checkpoint does not belong to this Step.")
        return _validated_targeted_fix_prefix(
            report.get("completed_targeted_fix_results"), edits,
        )
    return []


def _write_targeted_fix_report(
    path: Path, *, results: list[dict[str, Any]], complete: bool,
) -> None:
    _write_json(path, {
        "schema_version": "autonomous_gse_targeted_fix_report_0.13.0",
        "complete": complete, "results": copy.deepcopy(results),
    })


def _evaluate_candidate_step(
    *, root: Path, step_root: Path, step_number: int,
    parent_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]],
    diagnoses: list[dict[str, Any]], edits: list[dict[str, Any]],
    targeted_fix_judge: Callable[[TargetedFixRequest], dict[str, Any]],
    regression_judge: Callable[[Any], dict[str, Any]] | None,
    resume_targeted_fix_results: bool = False,
) -> dict[str, Any]:
    parent_by_key = {(row["domain"], row["task_id"], row["rollout_index"]): row for row in parent_rows}
    candidate_by_key = {(row["domain"], row["task_id"], row["rollout_index"]): row for row in candidate_rows}
    if set(parent_by_key) != set(candidate_by_key):
        raise RuntimeContractError("Parent/Candidate matched replay lineage is incomplete.")
    for key in parent_by_key:
        if parent_by_key[key]["rollout_seed"] != candidate_by_key[key]["rollout_seed"]:
            raise RuntimeContractError("Parent/Candidate matched replay seeds drifted.")
    diagnosis_by_id = {item["diagnosis_id"]: item for item in diagnoses}
    target_report_path = step_root / "targeted_fix_report.json"
    targeted = (
        _load_targeted_fix_prefix(
            root=root, step_root=step_root, step_number=step_number, edits=edits,
        )
        if resume_targeted_fix_results else []
    )
    for edit in edits[len(targeted):]:
        try:
            supporting = tuple(diagnosis_by_id[value] for value in edit["derived_from_diagnosis_ids"])
        except KeyError as error:
            raise RuntimeContractError("Canonical edit Diagnosis lineage is invalid.") from error
        groups = []
        for diagnosis in supporting:
            parent_group = [
                row for row in parent_rows if row["source_id"] in diagnosis["source_ids"]
            ]
            keys = [(row["domain"], row["task_id"], row["rollout_index"]) for row in parent_group]
            groups.append({
                "diagnosis_id": diagnosis["diagnosis_id"],
                "parent_rollouts": parent_group,
                "candidate_rollouts": [candidate_by_key[key] for key in keys],
            })
        request = TargetedFixRequest(
            canonical_edit=copy.deepcopy(edit), supporting_diagnoses=copy.deepcopy(supporting),
            matched_replays=tuple(groups),
        )
        try:
            result = targeted_fix_judge(request)
        except TargetedFixResponseError as error:
            _write_targeted_fix_report(target_report_path, results=targeted, complete=False)
            report = {
                "schema_version": "autonomous_gse_targeted_fix_error_0.13.0",
                "protocol_version": PROTOCOL_VERSION, "step": step_number,
                "canonical_edit_id": error.canonical_edit_id or edit["canonical_edit_id"],
                "error_code": error.code, "raw_response": error.raw_response,
                "completed_targeted_fix_results": copy.deepcopy(targeted),
            }
            _write_json(step_root / "targeted_fix_error.json", report)
            _write_json(root / "targeted_fix_error.json", report)
            raise
        if result.get("canonical_edit_id") != edit["canonical_edit_id"]:
            raise RuntimeContractError("Target Fix result canonical edit lineage is invalid.")
        targeted.append(result)
        _write_targeted_fix_report(target_report_path, results=targeted, complete=False)
    _write_targeted_fix_report(target_report_path, results=targeted, complete=True)
    for error_path in (step_root / "targeted_fix_error.json", root / "targeted_fix_error.json"):
        if error_path.is_file():
            error_path.unlink()
    from src.skill_evolution.regression_diagnosis_v11 import (
        RegressionDiagnosisRequest, build_regression_transition_report,
        call_regression_diagnosis,
    )
    transitions = build_regression_transition_report(parent_rows, candidate_rows)
    _write_json(step_root / "regression_transition_report.json", transitions)
    regression_judge = regression_judge or call_regression_diagnosis
    regression_diagnoses = []
    for regression in transitions["regression_set"]:
        key = (regression["domain"], regression["task_id"], regression["rollout_index"])
        before, after = parent_by_key[key], candidate_by_key[key]
        request = RegressionDiagnosisRequest(
            pair_id=regression["pair_id"], domain=regression["domain"],
            task_context={"domain": regression["domain"], "task_id": regression["task_id"]},
            regression_type=regression["regression_type"], parent_state=before["state"],
            candidate_state=after["state"], candidate_edits=tuple(copy.deepcopy(edits)),
            parent_trajectory=before["trajectory"], candidate_trajectory=after["trajectory"],
        )
        regression_diagnoses.append(regression_judge(request))
    _write_json(step_root / "regression_diagnoses.json", {"diagnoses": regression_diagnoses})
    _write_json(step_root / "aggregate_metrics.json", {
        "parent": aggregate_counts(parent_rows), "candidate": aggregate_counts(candidate_rows),
    })
    decision = build_evolution_decision(
        applied_canonical_edits=edits, targeted_fix_results=targeted,
        regression_diagnoses=regression_diagnoses,
        parent_rows=parent_rows, candidate_rows=candidate_rows,
    )
    _write_json(step_root / "evolution_decision.json", decision)
    return decision


def run_v13_campaign(
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
            raise RuntimeContractError("v0.13 resume protocol is invalid.")
        if resume_state.get("evidence_contract_version") != EVIDENCE_CONTRACT_VERSION:
            raise RuntimeContractError(
                "The paused pre-policy-grounded v13 run cannot continue to Step 3; restart from Step 1 raw Parent trajectories."
            )
        completed_steps = resume_state.get("completed_steps")
        if not isinstance(completed_steps, int) or not 0 <= completed_steps <= 3:
            raise RuntimeContractError("v0.13 completed Step count is invalid.")
        parent = copy.deepcopy(resume_state.get("current_parent"))
        report_steps = copy.deepcopy(resume_state.get("steps"))
        if not isinstance(parent, dict) or not isinstance(report_steps, list) or len(report_steps) != completed_steps:
            raise RuntimeContractError("v0.13 resume state is invalid.")
    else:
        parent = copy.deepcopy(campaign["initial_parent"])
    parent_path = _resolved_path(parent["path"])
    if not parent_path.is_file():
        raise RuntimeContractError("Current Parent Skill artifact is missing.")
    operator = MultiRolloutDiagnosisProposalOperator()
    domain_contexts = load_authoritative_domain_contexts(
        _resolved_path(campaign["benchmark"]["path"])
    )
    for step_number, batch in enumerate(batch_map["batches"], start=1):
        if step_number <= completed_steps:
            continue
        step_root, step_parent = root / "steps" / f"step_{step_number:03d}", copy.deepcopy(parent)
        parent_paths = backend.run_batch(
            task_ids=batch["task_ids"], phase="train", skill_version=parent["version"],
            skill_path=parent_path, execution_phase=f"step_{step_number:03d}_parent",
        )
        parent_rows, experiences = _rows_and_evidence(parent_paths, step=step_number)
        try:
            proposal = operator.propose(
                ProposalContext(
                    candidate_id=f"candidate_{step_number:03d}",
                    parent_skill=v12._method_skill(parent_path.read_text(encoding="utf-8")),
                    current_batch_governed_evidence=tuple(experiences),
                ), diagnoser, editor, domain_contexts=domain_contexts,
            )
        except DiagnosisContractError as error:
            diagnoses = [item.as_dict() for item in error.validations]
            report = {
                "schema_version": "autonomous_gse_diagnosis_contract_error_0.13.0",
                "protocol_version": PROTOCOL_VERSION, "step": step_number,
                "batch_id": batch["batch_id"], "error_code": error.code,
                "invalid_diagnosis_ids": list(error.invalid_diagnosis_ids),
                "diagnoses": diagnoses,
            }
            _write_json(step_root / "diagnosis_contract_error.json", report)
            _write_json(root / "diagnosis_contract_error.json", report)
            raise
        _write_json(step_root / "diagnoses.json", {
            "diagnoses": proposal.diagnoses,
            "eligible_diagnosis_ids": proposal.eligible_diagnosis_ids,
        })
        _write_json(step_root / "proposal.json", copy.deepcopy(proposal.__dict__))
        if proposal.proposal_status != "CANDIDATE" or proposal.candidate_skill is None:
            decision = no_candidate_decision()
            _write_json(step_root / "evolution_decision.json", decision)
            report_steps.append({
                "step": step_number, "batch_id": batch["batch_id"], "parent": step_parent,
                "promoted_parent": copy.deepcopy(parent), "candidate": None, **decision,
            })
            _write_json(root / "resume_state.json", {
                "protocol_version": PROTOCOL_VERSION, "completed_steps": step_number,
                "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
                "current_parent": parent, "steps": report_steps,
            })
            continue
        candidate_version = f"S{step_number}"
        candidate_path = step_root / "candidate_skill.md"
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(v12._canonical_skill(proposal.candidate_skill), encoding="utf-8")
        edits = _candidate_edit_provenance(proposal)
        _write_json(step_root / "candidate_edits.json", edits)
        candidate_paths = backend.run_batch(
            task_ids=batch["task_ids"], phase="train", skill_version=candidate_version,
            skill_path=candidate_path, execution_phase=f"step_{step_number:03d}_candidate_replay",
        )
        candidate_rows, _ = _rows_and_evidence(candidate_paths, step=step_number)
        decision = _evaluate_candidate_step(
            root=root, step_root=step_root, step_number=step_number,
            parent_rows=parent_rows, candidate_rows=candidate_rows,
            diagnoses=proposal.diagnoses, edits=edits,
            targeted_fix_judge=targeted_fix_judge, regression_judge=regression_judge,
        )
        candidate = {"kind": "candidate_skill", "version": candidate_version, "path": candidate_path.as_posix()}
        if decision["decision"] == "ACCEPT":
            parent, parent_path = candidate, candidate_path
        report_steps.append({
            "step": step_number, "batch_id": batch["batch_id"], "parent": step_parent,
            "promoted_parent": copy.deepcopy(parent), "candidate": candidate, **decision,
        })
        _write_json(root / "resume_state.json", {
            "protocol_version": PROTOCOL_VERSION, "completed_steps": step_number,
            "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
            "current_parent": parent, "steps": report_steps,
        })
    report = {
        "schema_version": "autonomous_gse_formal_report_0.13.0",
        "protocol_version": PROTOCOL_VERSION, "campaign_id": campaign["campaign_id"],
        "mode": FORMAL_MODE, "steps": report_steps, "final_skill": parent,
        "disabled_phases": {"official_test_holdout": True},
    }
    _write_json(root / "campaign_report.json", report)
    return report


def prepare_v13_step1_restart_from_parent(
    campaign: dict[str, Any], batch_map: dict[str, Any], *, artifact_root: Path | None = None,
) -> dict[str, Any]:
    """Archive contaminated Step 1 outputs and rescore its saved Parent S0 artifacts."""
    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "formal"
    if (root / "campaign_report.json").is_file():
        raise RuntimeContractError("A completed campaign cannot be restarted in place.")
    resume_path = root / "resume_state.json"
    if not resume_path.is_file():
        raise RuntimeContractError("Step 1 restart requires the completed contaminated resume state.")
    resume = _load_json(resume_path)
    if (
        resume.get("protocol_version") != PROTOCOL_VERSION
        or resume.get("completed_steps") != 1
        or resume.get("current_parent", {}).get("version") != campaign["initial_parent"]["version"]
    ):
        raise RuntimeContractError("Step 1 restart requires rejected S1 with S0 still promoted.")

    step_root = root / "steps" / "step_001"
    rollout_root = root / "rollouts" / "train"
    parent_root = rollout_root / "step_001_parent"
    candidate_root = rollout_root / "step_001_candidate_replay"
    archive_root = root / "invalidated" / "step_001_before_one_tool_scope_exclusion"
    if archive_root.exists():
        raise RuntimeContractError("The Step 1 scope-exclusion archive already exists.")
    if not step_root.is_dir() or not candidate_root.is_dir() or not parent_root.is_dir():
        raise RuntimeContractError("Step 1 restart artifacts are incomplete.")
    parent_paths = sorted(
        path for path in parent_root.glob("*.json")
        if not path.name.endswith(("_tau3_raw.json", "_error.json"))
    )
    expected = len(batch_map["batches"][0]["task_ids"]) * ROLLOUTS_PER_TASK
    if len(parent_paths) != expected:
        raise RuntimeContractError(f"Step 1 restart requires exactly {expected} Parent S0 artifacts.")

    parent_archive = archive_root / "parent_rollouts_before_scope_exclusion"
    parent_archive.mkdir(parents=True)
    for path in parent_paths:
        shutil.copy2(path, parent_archive / path.name)
    shutil.move(step_root.as_posix(), (archive_root / "step_001").as_posix())
    shutil.move(candidate_root.as_posix(), (archive_root / "step_001_candidate_replay").as_posix())
    report_archive = archive_root / "root_reports"
    report_archive.mkdir()
    for name in ("resume_state.json", "diagnosis_contract_error.json", "targeted_fix_error.json"):
        path = root / name
        if path.exists():
            shutil.move(path.as_posix(), (report_archive / name).as_posix())

    removed_violations = 0
    compliance_flips = 0
    for path in parent_paths:
        value = _load_json(path)
        compliance = value.get("compliance_evaluation")
        governed = value.get("governed_evidence")
        if not isinstance(compliance, dict) or not isinstance(governed, dict):
            raise RuntimeContractError("Saved Parent compliance artifact is invalid.")
        violations = compliance.get("violations")
        if not isinstance(violations, list) or any(not isinstance(item, dict) for item in violations):
            raise RuntimeContractError("Saved Parent violations are invalid.")
        retained = [
            copy.deepcopy(item) for item in violations
            if not policy_clause_is_excluded(str(item.get("policy_clause", "")))
        ]
        removed_violations += len(violations) - len(retained)
        was_compliant = compliance.get("compliant")
        compliant = not retained
        compliance_flips += was_compliant is not compliant
        compliance["compliant"] = compliant
        compliance["violations"] = retained
        compliance["judge_prompt_version"] = JUDGE_PROMPT_VERSION
        success = value.get("task_evaluation", {}).get("success")
        if not isinstance(success, bool):
            raise RuntimeContractError("Saved Parent Task Success is invalid.")
        state = classify_state(success, compliant).value
        value["state"] = state
        governed["state"] = state
        governed["process_feedback"] = {
            "compliant": compliant, "violated_policies": copy.deepcopy(retained),
        }
        governed["compliance_evaluation"] = copy.deepcopy(compliance)
        provenance = value.get("provenance")
        if isinstance(provenance, dict) and isinstance(provenance.get("judge_config"), dict):
            provenance["judge_config"]["prompt_version"] = JUDGE_PROMPT_VERSION
            provenance["compliance_scope_rescore"] = {
                "kind": "deterministic_one_tool_call_scope_exclusion",
                "source_artifact": (parent_archive / path.name).as_posix(),
            }
        _write_json(path, value)

    report = {
        "schema_version": "autonomous_gse_step_1_restart_0.13.0",
        "protocol_version": PROTOCOL_VERSION,
        "restart_boundary": "step_001_diagnosis",
        "archive_path": archive_root.as_posix(),
        "reused_parent_rollouts": len(parent_paths),
        "removed_one_tool_call_violations": removed_violations,
        "parent_compliance_flips": compliance_flips,
        "parent_rollouts_rerun": 0,
        "invalidated": [
            "diagnoses", "editor_proposal", "candidate_skill", "candidate_replay",
            "targeted_fix", "regression", "aggregate", "evolution_gate",
        ],
    }
    _write_json(root / "step_001_restart_report.json", report)
    _write_json(archive_root / "restart_report.json", report)
    return report


def resume_v13_target_fix_and_gate(
    campaign: dict[str, Any], batch_map: dict[str, Any], *, step_number: int,
    targeted_fix_judge: Callable[[TargetedFixRequest], dict[str, Any]] = call_targeted_fix,
    regression_judge: Callable[[Any], dict[str, Any]] | None = None,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    """Resume a saved Step at the first unfinished Target Fix edit, then recompute its Gate."""
    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    if not 1 <= step_number <= len(batch_map["batches"]):
        raise RuntimeContractError("Target Fix resume Step is invalid.")
    root = artifact_root or REPO_ROOT / "artifacts" / PROTOCOL_VERSION / "formal"
    step_root = root / "steps" / f"step_{step_number:03d}"
    diagnoses_path = step_root / "diagnoses.json"
    edits_path = step_root / "candidate_edits.json"
    candidate_path = step_root / "candidate_skill.md"
    if not all(path.is_file() for path in (diagnoses_path, edits_path, candidate_path)):
        raise RuntimeContractError("Target Fix resume requires saved Diagnosis, edit, and Candidate artifacts.")
    diagnoses = _load_json(diagnoses_path).get("diagnoses")
    edits = _load_json(edits_path)
    if not isinstance(diagnoses, list) or not isinstance(edits, list) or not edits:
        raise RuntimeContractError("Saved Target Fix Diagnosis/edit artifacts are invalid.")

    resume_path = root / "resume_state.json"
    if step_number == 1:
        parent = copy.deepcopy(campaign["initial_parent"])
        report_steps: list[dict[str, Any]] = []
        if resume_path.is_file():
            prior = _load_json(resume_path)
            if prior.get("completed_steps") not in (0, None):
                raise RuntimeContractError("Step 1 Target Fix cannot overwrite a completed campaign Step.")
    else:
        if not resume_path.is_file():
            raise RuntimeContractError("Target Fix resume requires the preceding completed Steps.")
        prior = _load_json(resume_path)
        if (
            prior.get("protocol_version") != PROTOCOL_VERSION
            or prior.get("completed_steps") != step_number - 1
            or not isinstance(prior.get("current_parent"), dict)
            or not isinstance(prior.get("steps"), list)
            or len(prior["steps"]) != step_number - 1
        ):
            raise RuntimeContractError("Target Fix resume state does not end before the requested Step.")
        parent = copy.deepcopy(prior["current_parent"])
        report_steps = copy.deepcopy(prior["steps"])

    rollout_root = root / "rollouts" / "train"
    def saved_rollouts(execution_phase: str) -> list[Path]:
        return sorted(
            path for path in (rollout_root / execution_phase).glob("*.json")
            if not path.name.endswith(("_tau3_raw.json", "_error.json"))
        )

    parent_paths = saved_rollouts(f"step_{step_number:03d}_parent")
    candidate_paths = saved_rollouts(f"step_{step_number:03d}_candidate_replay")
    expected_rollouts = len(batch_map["batches"][step_number - 1]["task_ids"]) * ROLLOUTS_PER_TASK
    if len(parent_paths) != expected_rollouts or len(candidate_paths) != expected_rollouts:
        raise RuntimeContractError(
            f"Target Fix resume requires {expected_rollouts}+{expected_rollouts} saved matched rollouts."
        )
    parent_rows, _ = _rows_and_evidence(parent_paths, step=step_number)
    candidate_rows, _ = _rows_and_evidence(candidate_paths, step=step_number)
    decision = _evaluate_candidate_step(
        root=root, step_root=step_root, step_number=step_number,
        parent_rows=parent_rows, candidate_rows=candidate_rows,
        diagnoses=diagnoses, edits=edits,
        targeted_fix_judge=targeted_fix_judge, regression_judge=regression_judge,
        resume_targeted_fix_results=True,
    )
    candidate = {
        "kind": "candidate_skill", "version": f"S{step_number}",
        "path": candidate_path.as_posix(),
    }
    promoted_parent = candidate if decision["decision"] == "ACCEPT" else parent
    batch = batch_map["batches"][step_number - 1]
    step_report = {
        "step": step_number, "batch_id": batch["batch_id"], "parent": parent,
        "promoted_parent": copy.deepcopy(promoted_parent), "candidate": candidate, **decision,
    }
    report_steps.append(step_report)
    _write_json(resume_path, {
        "protocol_version": PROTOCOL_VERSION, "completed_steps": step_number,
        "current_parent": promoted_parent, "steps": report_steps,
    })
    report = {
        "schema_version": "autonomous_gse_target_fix_resume_0.13.0",
        "protocol_version": PROTOCOL_VERSION, "step": step_number,
        "reused": {
            "parent_rollouts": len(parent_paths), "candidate_rollouts": len(candidate_paths),
            "diagnoses": len(diagnoses), "canonical_edits": len(edits),
        },
        "step_report": step_report,
    }
    _write_json(step_root / "targeted_fix_resume_report.json", report)
    return report


def build_holdout_plan(campaign: dict[str, Any], batch_map: dict[str, Any], final_skill: dict[str, Any]) -> dict[str, Any]:
    validate_campaign_contract(campaign)
    _validate_batch_map(batch_map, campaign)
    task_ids = [
        *(f"airline:{x}" for x in batch_map["assignment"]["holdout"]["airline"]),
        *(f"retail:{x}" for x in batch_map["assignment"]["holdout"]["retail"]),
    ]
    units = matched_replay_plan(task_ids, campaign["campaign_seed"])
    return {
        "schema_version": "autonomous_gse_holdout_plan_0.13.0",
        "source_split": "official_test", "task_ids": task_ids,
        "skills": [copy.deepcopy(campaign["initial_parent"]), copy.deepcopy(final_skill)],
        "s0_units": units["parent"], "s_final_units": units["candidate"],
        "matched_seed_lineage": True, "trajectory_count": 240, "learning_calls": 0,
    }


def _campaign_files(campaign_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    campaign = _load_json(campaign_path)
    return campaign, _load_json(_resolved_path(campaign["evolution"]["batch_map"]))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "run", "resume"):
        item = sub.add_parser(command)
        item.add_argument("--campaign", type=Path, required=True)
    targeted_resume = sub.add_parser("resume-target-fix")
    targeted_resume.add_argument("--campaign", type=Path, required=True)
    targeted_resume.add_argument("--step", type=int, required=True)
    restart_step1 = sub.add_parser("restart-step1-from-parent")
    restart_step1.add_argument("--campaign", type=Path, required=True)
    args = parser.parse_args(argv)
    campaign, batch_map = _campaign_files(args.campaign.resolve())
    if args.command == "plan":
        print(json.dumps(build_campaign_dry_plan(campaign, batch_map), indent=2))
        return 0
    root = REPO_ROOT / "artifacts" / campaign["campaign_id"] / "formal"
    if args.command == "resume-target-fix":
        print(json.dumps(resume_v13_target_fix_and_gate(
            campaign, batch_map, step_number=args.step, artifact_root=root,
        ), indent=2))
        return 0
    if args.command == "restart-step1-from-parent":
        restart = prepare_v13_step1_restart_from_parent(
            campaign, batch_map, artifact_root=root,
        )
        report = run_v13_campaign(campaign, batch_map, artifact_root=root)
        print(json.dumps({"restart": restart, "campaign": report}, indent=2))
        return 0
    if args.command == "resume" and not (root / "resume_state.json").is_file():
        raise RuntimeContractError("No v0.13 resume state is available.")
    resume_state = _load_json(root / "resume_state.json") if args.command == "resume" else None
    print(json.dumps(run_v13_campaign(
        campaign, batch_map, artifact_root=root, resume_state=resume_state
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
