"""τ³ benchmark adapter for Autonomous GSE v0.9."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import traceback
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from src.adapters.tau2.tau3_compliance_judge import (
    JudgeCaller,
    default_judge_caller,
)
from src.adapters.tau2.tau3_gse_runtime import (
    evaluate_simulation,
    official_task_evaluation,
    policy_provenance,
    run_official_rollout,
    stable_trajectory,
    write_rollout_artifact,
)
from src.skill_evolution.autonomous_gse_v03_proposal import ProposalContext
from src.skill_evolution.autonomous_gse_v03_benchmark_runtime import RolloutRequest
from src.skill_evolution.autonomous_gse_v03_runtime import RuntimeContractError
import src.skill_evolution.autonomous_gse_v07_benchmark_runtime as v07
from src.skill_evolution.autonomous_gse_v07_proposal import (
    DiagnosisEditor,
    DiagnosisDrivenProposalOperator,
)
from src.skill_evolution.diagnosis import Diagnoser


PROTOCOL_VERSION = "autonomous_gse_v09"
FORMAL_MODE = "formal_tau3_airline_retail_v09"
REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_REPORT_FILENAME = "campaign_report.json"
RESUME_STATE_FILENAME = "resume_state.json"
CANONICAL_SKILL_TITLE = "# Operational Skill"
V07_METHOD_SKILL_TITLE = "# SuiteCRM Operational Skill"
OUTCOME_STATES = (
    "compliant_success",
    "violating_success",
    "compliant_failure",
    "violating_failure",
)

# These are intentionally imported, not copied or forked.
REUSED_METHOD_FILES = (
    "src/skill_evolution/autonomous_gse_v07_proposal.py",
    "src/skill_evolution/diagnosis.py",
    "src/learners/stwebagentbench/generate_governed_skill_v07.py",
    "src/skill_evolution/two_dimensional_gate.py",
)


def validate_campaign_contract(campaign: dict[str, Any]) -> None:
    if (
        campaign.get("schema_version") != "autonomous_gse_campaign_0.9.0"
        or campaign.get("protocol_version") != "autonomous_gse_v09"
        or campaign.get("campaign_id") != PROTOCOL_VERSION
        or campaign.get("campaign_seed") != 200
    ):
        raise RuntimeContractError("τ³ v0.9 Campaign identity is invalid.")
    if campaign.get("benchmark", {}).get("name") != "tau3" or campaign[
        "benchmark"
    ].get("domains") != ["airline", "retail"]:
        raise RuntimeContractError("τ³ v0.9 supports only Airline and Retail.")
    execution = campaign.get("execution", {})
    if (
        execution.get("parallelism_unit") != "task_x_rollout"
        or execution.get("max_concurrency") != 6
    ):
        raise RuntimeContractError(
            "τ³ v0.9 requires task_x_rollout parallelism with max_concurrency=6."
        )
    train = campaign.get("train", {})
    selection = campaign.get("selection", {})
    if (
        train.get("tasks") != 51
        or train.get("batches") != 3
        or train.get("tasks_per_batch") != 17
        or train.get("rollouts_per_task") != 3
        or selection.get("tasks") != 18
        or selection.get("rollouts_per_task") != 3
        or selection.get("parent_candidate_seed_matching") is not True
    ):
        raise RuntimeContractError("τ³ v0.9 workload drifted.")
    if campaign.get("schedule") != {"evolution_steps": 3}:
        raise RuntimeContractError("τ³ v0.9 must run exactly three Steps.")
    test = campaign.get("test", {})
    if (
        test.get("tasks") != 60
        or test.get("learning_access") != "forbidden"
        or test.get("formal_run_authorized") is not False
    ):
        raise RuntimeContractError("Official Test must remain held out and disabled.")
    judge = campaign.get("compliance_judge", {})
    if judge != {
        "model": "openai/gpt-5.6-luna",
        "temperature": 0,
        "prompt_version": "tau3_policy_grounded_judge_v3",
        "frozen_across_phases_and_methods": True,
        "failure_mode": "COMPLIANCE_JUDGE_ERROR",
        "fallback": "forbidden",
    }:
        raise RuntimeContractError("Frozen Compliance Judge configuration drifted.")
    evaluator = campaign.get("official_evaluator", {})
    if (
        evaluator.get("implementation") != "tau3_official_evaluator"
        or evaluator.get("nl_assertions_model") != "openai/gpt-5.6-luna"
        or evaluator.get("nl_assertions_temperature") != 0.0
    ):
        raise RuntimeContractError("Official evaluator configuration drifted.")
    budget = campaign.get("budget", {})
    expected_budget = {
        "train_trajectories": 153,
        "initial_selection_trajectories": 54,
        "maximum_candidate_selection_trajectories": 162,
        "maximum_total_trajectories": 369,
        "maximum_candidates": 3,
        "maximum_learner_calls": 156,
        "unused_budget_reallocation": "forbidden",
    }
    if budget != expected_budget:
        raise RuntimeContractError("τ³ v0.9 budget drifted.")
    agent = campaign.get("agent", {})
    if (
        agent.get("model") != "openai/deepseek-v4-flash"
        or agent.get("temperature") != 0.0
        or agent.get("thinking") != "high"
        or agent.get("reasoning_effort") != "high"
        or agent.get("max_tokens") != 8192
        or agent.get("empty_response_retries") != 2
        or agent.get("empty_response_retry_max_tokens") != 8192
    ):
        raise RuntimeContractError("Frozen Agent configuration drifted.")
    user_simulator = campaign.get("user_simulator", {})
    if (
        user_simulator.get("model") != "openai/deepseek-v4-flash"
        or user_simulator.get("temperature") != 0.0
        or user_simulator.get("thinking") != "high"
        or user_simulator.get("reasoning_effort") != "high"
        or user_simulator.get("max_tokens") != 8192
        or user_simulator.get("empty_response_retries") != 2
        or user_simulator.get("empty_response_retry_max_tokens") != 8192
    ):
        raise RuntimeContractError("Frozen UserSimulator configuration drifted.")
    method = campaign.get("skill_evolution", {})
    if (
        method.get("proposal_operator") != "diagnosis_driven_bounded_edit"
        or method.get("diagnosis_calls_per_train_rollout") != 1
        or method.get("maximum_editor_calls_per_step") != 1
        or method.get("allowed_operations") != ["add", "replace", "delete"]
        or method.get("maximum_skill_rules") != 18
        or method.get("maximum_skill_words") != 900
    ):
        raise RuntimeContractError("v0.9 Skill Evolution semantics drifted.")


def derive_rollout_seeds(
    campaign_seed: int, execution_seed_offset: int, rollouts_per_task: int = 3
) -> tuple[int, ...]:
    """Preserve the established base+offset+rollout-index seed philosophy."""

    if rollouts_per_task != 3:
        raise RuntimeContractError("v0.9 requires exactly three rollouts per task.")
    return tuple(
        campaign_seed + execution_seed_offset + rollout_index
        for rollout_index in range(rollouts_per_task)
    )


def matched_selection_plan(
    task_ids: list[str], campaign_seed: int, execution_seed_offset: int
) -> dict[str, list[dict[str, Any]]]:
    seeds = derive_rollout_seeds(campaign_seed, execution_seed_offset)
    units = [
        {"task_id": task_id, "rollout_index": index, "rollout_seed": seed}
        for task_id in task_ids
        for index, seed in enumerate(seeds, start=1)
    ]
    return {"parent": copy.deepcopy(units), "candidate": copy.deepcopy(units)}


def build_campaign_dry_plan(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, Any]:
    """Expand the complete v0.9 workload without API calls or file writes."""

    validate_campaign_contract(campaign)
    if (
        batch_map.get("schema_version") != "tau3_gse_task_split_0.9.0"
        or batch_map.get("campaign_seed") != campaign["campaign_seed"]
        or batch_map.get("source_split") != "official_train"
    ):
        raise RuntimeContractError("Frozen Batch Map identity is invalid.")
    batches = batch_map.get("batches")
    if not isinstance(batches, list) or len(batches) != 3:
        raise RuntimeContractError("Dry plan requires exactly three batches.")
    assignment = batch_map.get("assignment", {})
    selection = assignment.get("selection", {})
    selection_task_ids = [
        *[f"airline:{task_id}" for task_id in selection.get("airline", [])],
        *[f"retail:{task_id}" for task_id in selection.get("retail", [])],
    ]
    if len(selection_task_ids) != 18 or len(set(selection_task_ids)) != 18:
        raise RuntimeContractError("Frozen Selection task set is invalid.")

    campaign_seed = campaign["campaign_seed"]
    rollout_seeds = derive_rollout_seeds(campaign_seed, 0)
    steps = []
    all_train_tasks: list[str] = []
    for index, batch in enumerate(batches, start=1):
        task_ids = batch.get("task_ids")
        if (
            batch.get("batch_id") != f"batch_{index}"
            or not isinstance(task_ids, list)
            or len(task_ids) != 17
            or len(set(task_ids)) != 17
        ):
            raise RuntimeContractError("Frozen Train batch is invalid.")
        all_train_tasks.extend(task_ids)
        train_units = [
            {
                "task_id": task_id,
                "rollout_index": rollout_index,
                "rollout_seed": rollout_seed,
            }
            for task_id in task_ids
            for rollout_index, rollout_seed in enumerate(rollout_seeds, start=1)
        ]
        selection_plan = matched_selection_plan(
            selection_task_ids, campaign_seed, 0
        )
        steps.append(
            {
                "step": index,
                "batch_id": batch["batch_id"],
                "train_task_ids": copy.deepcopy(task_ids),
                "train_units": train_units,
                "train_trajectories": len(train_units),
                "maximum_diagnosis_calls": len(train_units),
                "maximum_editor_calls": 1,
                "selection": selection_plan,
                "candidate_selection_trajectories": len(
                    selection_plan["candidate"]
                ),
                "parent_candidate_seed_matching": (
                    selection_plan["parent"] == selection_plan["candidate"]
                ),
            }
        )
    if len(all_train_tasks) != 51 or len(set(all_train_tasks)) != 51:
        raise RuntimeContractError("Train batches do not partition 51 tasks.")

    initial_selection = matched_selection_plan(selection_task_ids, campaign_seed, 0)[
        "parent"
    ]
    computed_budget = {
        "train_trajectories": sum(step["train_trajectories"] for step in steps),
        "initial_selection_trajectories": len(initial_selection),
        "maximum_candidate_selection_trajectories": sum(
            step["candidate_selection_trajectories"] for step in steps
        ),
        "maximum_total_trajectories": (
            sum(step["train_trajectories"] for step in steps)
            + len(initial_selection)
            + sum(step["candidate_selection_trajectories"] for step in steps)
        ),
        "maximum_learner_calls": sum(
            step["maximum_diagnosis_calls"] + step["maximum_editor_calls"]
            for step in steps
        ),
    }
    for key, value in computed_budget.items():
        if campaign["budget"][key] != value:
            raise RuntimeContractError(f"Dry-plan budget mismatch: {key}.")
    return {
        "schema_version": "autonomous_gse_dry_plan_0.9.0",
        "campaign_id": campaign["campaign_id"],
        "mode": "no_api_no_rollout_no_write",
        "execution": copy.deepcopy(campaign["execution"]),
        "rollout_seeds": list(rollout_seeds),
        "initial_selection_task_ids": selection_task_ids,
        "initial_selection_units": initial_selection,
        "steps": steps,
        "computed_budget": computed_budget,
        "test": {
            "authorized": False,
            "task_count": campaign["test"]["tasks"],
            "included_in_plan": False,
        },
    }


def _metric_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise RuntimeContractError("Cannot aggregate an empty evaluation group.")
    states = Counter(row["state"] for row in rows)
    count = len(rows)
    return {
        "count": count,
        "task_success": sum(bool(row["task_success"]) for row in rows) / count,
        "compliance": sum(bool(row["compliant"]) for row in rows) / count,
        "cup": sum(
            bool(row["task_success"] and row["compliant"]) for row in rows
        )
        / count,
        "four_state_distribution": {
            state: states[state] for state in OUTCOME_STATES
        },
        "severity_status": "unavailable",
        "severe_task_ids": [],
    }


def aggregate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        domain = row.get("domain")
        if domain not in {"airline", "retail"}:
            raise RuntimeContractError("Evaluation row has an invalid domain.")
        by_domain[domain].append(row)
    if set(by_domain) != {"airline", "retail"}:
        raise RuntimeContractError("Both Airline and Retail results are required.")
    return {
        "airline": _metric_group(by_domain["airline"]),
        "retail": _metric_group(by_domain["retail"]),
        "overall": _metric_group(rows),
    }


def transition_matrix(
    parent_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]
) -> dict[str, dict[str, int]]:
    def index(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], str]:
        result = {}
        for row in rows:
            key = (row["domain"], str(row["task_id"]), row["rollout_index"])
            if key in result:
                raise RuntimeContractError("Duplicate Selection rollout lineage.")
            result[key] = row["state"]
        return result

    parent = index(parent_rows)
    candidate = index(candidate_rows)
    if parent.keys() != candidate.keys():
        raise RuntimeContractError("Parent/Candidate Selection units are not matched.")
    matrix = {
        before: {after: 0 for after in OUTCOME_STATES}
        for before in OUTCOME_STATES
    }
    for key, before in parent.items():
        matrix[before][candidate[key]] += 1
    return matrix


def apply_existing_evolution_gate(
    parent_metrics: dict[str, Any], candidate_metrics: dict[str, Any]
) -> dict[str, Any]:
    metrics = ("task_success", "compliance", "cup")
    deltas = {
        metric: candidate_metrics[metric] - parent_metrics[metric]
        for metric in metrics
    }
    regressions = [metric for metric, delta in deltas.items() if delta < 0]
    improvements = [metric for metric, delta in deltas.items() if delta > 0]
    eligible = not regressions and bool(improvements)
    return {
        "eligible": eligible,
        "decision": "continue_evolution" if eligible else "reject",
        "deltas": deltas,
        "reasons": (
            [f"aggregate_{metric}_regression" for metric in regressions]
            if regressions
            else ["aggregate_pareto_progress"]
            if improvements
            else ["no_aggregate_progress"]
        ),
    }


class Tau3RolloutAdapter:
    """One-rollout adapter used identically by Train, Selection, and Test."""

    def __init__(
        self,
        campaign: dict[str, Any],
        *,
        repo_root: Path,
        judge_caller: JudgeCaller,
    ) -> None:
        validate_campaign_contract(campaign)
        self.campaign = copy.deepcopy(campaign)
        self.repo_root = repo_root.resolve()
        self.tau2_root = (self.repo_root / campaign["benchmark"]["path"]).resolve()
        self.judge_caller = judge_caller

    def run(
        self,
        *,
        domain: str,
        task_id: str,
        phase: str,
        skill_version: str,
        skill_path: Path | None,
        rollout_index: int,
        rollout_seed: int,
        output_path: Path,
    ) -> dict[str, Any]:
        if phase == "test" and not self.campaign["test"]["formal_run_authorized"]:
            raise RuntimeContractError("Official Test execution is not authorized.")
        error_path = output_path.with_name(output_path.stem + "_error.json")
        try:
            task, simulation = run_official_rollout(
                tau2_root=self.tau2_root,
                domain=domain,
                task_id=task_id,
                rollout_seed=rollout_seed,
                agent_config=self.campaign["agent"],
                user_simulator_config=self.campaign["user_simulator"],
                official_evaluator_config=self.campaign["official_evaluator"],
                skill_path=None if skill_version == "S0" else skill_path,
                task_split="test" if phase == "test" else "train",
            )
        except Exception as error:
            _write_json(
                error_path,
                {
                    "schema_version": "tau3_gse_rollout_error_0.9.0",
                    "domain": domain,
                    "task_id": str(task_id),
                    "phase": phase,
                    "skill_version": skill_version,
                    "rollout_index": rollout_index,
                    "rollout_seed": rollout_seed,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "error_details": copy.deepcopy(
                        getattr(error, "details", None)
                    ),
                    "traceback": traceback.format_exc(),
                    "agent_config": copy.deepcopy(self.campaign["agent"]),
                    "user_simulator_config": copy.deepcopy(
                        self.campaign["user_simulator"]
                    ),
                    "official_evaluator_config": copy.deepcopy(
                        self.campaign["official_evaluator"]
                    ),
                },
            )
            raise
        policy_path = self.tau2_root / f"data/tau2/domains/{domain}/policy.md"
        policy = policy_path.read_text(encoding="utf-8")
        source_id = (
            f"{phase}_{domain}_{task_id}_rollout_{rollout_index:02d}"
        )
        evidence = evaluate_simulation(
            source_id=source_id,
            domain=domain,
            task=task,
            simulation=simulation,
            domain_policy=policy,
            judge_caller=self.judge_caller,
        )
        raw_result_path = output_path.with_name(output_path.stem + "_tau3_raw.json")
        raw_result_path.parent.mkdir(parents=True, exist_ok=True)
        raw_result_path.write_text(
            simulation.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        provenance = {
            "raw_tau3_result_path": raw_result_path.as_posix(),
            **policy_provenance(policy_path),
            "task_split": "official_train" if phase != "test" else "official_test",
            "tau3_commit": self.campaign["benchmark"]["commit"],
            "gse_commit": self.campaign["provenance"]["gse_commit"],
            "judge_config": copy.deepcopy(self.campaign["compliance_judge"]),
            "agent_config": copy.deepcopy(self.campaign["agent"]),
            "user_simulator_config": copy.deepcopy(
                self.campaign["user_simulator"]
            ),
            "official_evaluator_config": copy.deepcopy(
                self.campaign["official_evaluator"]
            ),
        }
        write_rollout_artifact(
            output_path,
            domain=domain,
            task_id=task_id,
            phase=phase,
            skill_version=skill_version,
            rollout_index=rollout_index,
            rollout_seed=rollout_seed,
            governed_evidence=evidence,
            provenance=provenance,
        )
        error_path.unlink(missing_ok=True)
        return evidence


def proposal_operator() -> DiagnosisDrivenProposalOperator:
    """Expose the established diagnosis-driven operator without a fork."""

    return DiagnosisDrivenProposalOperator()


def propose_candidate(
    context: ProposalContext,
    diagnoser: Diagnoser,
    editor: DiagnosisEditor,
) -> Any:
    """Send τ³ governed evidence through the diagnosis-driven operator."""

    return proposal_operator().propose(context, diagnoser, editor)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _stored_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolved_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _artifact(kind: str, version: str, path: Path) -> dict[str, str]:
    return {"kind": kind, "version": version, "path": _stored_path(path)}


def _to_v07_method_skill(skill: str) -> str:
    if skill.startswith(CANONICAL_SKILL_TITLE):
        return skill.replace(
            CANONICAL_SKILL_TITLE, V07_METHOD_SKILL_TITLE, 1
        )
    if skill.startswith(V07_METHOD_SKILL_TITLE):
        return skill
    raise RuntimeContractError("Skill title is invalid.")


def _to_canonical_skill(skill: str) -> str:
    if skill.startswith(V07_METHOD_SKILL_TITLE):
        return skill.replace(
            V07_METHOD_SKILL_TITLE, CANONICAL_SKILL_TITLE, 1
        )
    if skill.startswith(CANONICAL_SKILL_TITLE):
        return skill
    raise RuntimeContractError("Skill title is invalid.")


def _task_maps(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, dict[int, str]]:
    build_campaign_dry_plan(campaign, batch_map)
    train_refs = [
        task_id for batch in batch_map["batches"] for task_id in batch["task_ids"]
    ]
    selection = batch_map["assignment"]["selection"]
    selection_refs = [
        *[f"airline:{task_id}" for task_id in selection["airline"]],
        *[f"retail:{task_id}" for task_id in selection["retail"]],
    ]
    return {
        "train": {index: ref for index, ref in enumerate(train_refs, start=1)},
        "selection": {
            1000 + index: ref
            for index, ref in enumerate(selection_refs, start=1)
        },
    }


def _v07_method_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    """Project only method settings onto the unchanged v0.7 implementation."""

    manifest = REPO_ROOT / (
        "experiments/campaigns/autonomous_gse_v07/campaign_manifest.json"
    )
    projected = v07._expand_campaign(
        json.loads(manifest.read_text(encoding="utf-8"))
    )
    projected["campaign_seed"] = campaign["campaign_seed"]
    projected["status"] = campaign["status"]
    projected["initial_parent"] = {
        key: campaign["initial_parent"][key]
        for key in ("kind", "version", "path")
    }
    projected["budget"] = copy.deepcopy(campaign["budget"])
    return projected


def _controller_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    return v07._controller_campaign(_v07_method_campaign(campaign))


def _controller_batch_map(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, Any]:
    """Give the v0.7 controller stable integer IDs without changing τ³ IDs."""

    maps = _task_maps(campaign, batch_map)
    controller = _controller_campaign(campaign)
    train_lookup = {ref: task_id for task_id, ref in maps["train"].items()}
    batches = []
    for index, batch in enumerate(batch_map["batches"], start=1):
        batches.append(
            {
                "batch_id": f"batch_{index:03d}",
                "assignments": [
                    {
                        "task_id": train_lookup[ref],
                        "intent_template_id": position,
                    }
                    for position, ref in enumerate(batch["task_ids"], start=1)
                ],
            }
        )
    return {
        "schema_version": "autonomous_gse_batch_map_0.2.0",
        "campaign_id": "autonomous_gse_v02",
        "status": "ready",
        "source": {
            "path": controller["train"]["source_manifest"],
            "split": controller["train"]["source_split"],
        },
        "batches": batches,
    }


class Tau3CampaignRolloutBackend:
    """Expand one controller request into official τ³ task × rollout units."""

    def __init__(
        self,
        campaign: dict[str, Any],
        batch_map: dict[str, Any],
        *,
        judge_caller: JudgeCaller = default_judge_caller,
        artifact_root: Path | None = None,
    ) -> None:
        validate_campaign_contract(campaign)
        self._campaign = copy.deepcopy(campaign)
        self._maps = _task_maps(campaign, batch_map)
        self._artifact_root = artifact_root or (
            REPO_ROOT / "artifacts" / campaign["campaign_id"] / "formal"
        )
        self._max_concurrency = campaign["execution"]["max_concurrency"]
        self._rollout = Tau3RolloutAdapter(
            campaign, repo_root=REPO_ROOT, judge_caller=judge_caller
        )

    def _is_reusable(
        self,
        path: Path,
        *,
        domain: str,
        task_id: str,
        split: str,
        skill_version: str,
        rollout_index: int,
        rollout_seed: int,
    ) -> bool:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            provenance = value["provenance"]
            raw_path = _resolved_path(provenance["raw_tau3_result_path"])
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            raw_evaluation = official_task_evaluation(raw)
            raw_trajectory = stable_trajectory(raw.get("messages") or [])
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return False

        expected_lineage = {
            "rollout_seed": rollout_seed,
            "agent_seed": rollout_seed,
            "user_simulator_seed": rollout_seed,
            "environment_seed": rollout_seed,
        }
        if (
            value.get("schema_version") != "tau3_gse_rollout_0.9.0"
            or value.get("domain") != domain
            or value.get("task_id") != str(task_id)
            or value.get("phase") != split
            or value.get("skill_version") != skill_version
            or value.get("rollout_index") != rollout_index
            or value.get("rollout_seed") != rollout_seed
            or value.get("seed_lineage") != expected_lineage
            or raw.get("task_id") != str(task_id)
            or not raw_trajectory
        ):
            return False

        evaluation = value.get("task_evaluation")
        compliance = value.get("compliance_evaluation")
        governed = value.get("governed_evidence")
        if (
            evaluation != raw_evaluation
            or not isinstance(compliance, dict)
            or not isinstance(compliance.get("compliant"), bool)
            or not isinstance(compliance.get("violations"), list)
            or compliance.get("judge_model")
            != self._campaign["compliance_judge"]["model"]
            or compliance.get("judge_temperature")
            != self._campaign["compliance_judge"]["temperature"]
            or compliance.get("judge_prompt_version")
            != self._campaign["compliance_judge"]["prompt_version"]
            or not isinstance(governed, dict)
            or value.get("trajectory") != raw_trajectory
            or governed.get("trajectory") != raw_trajectory
            or governed.get("task_evaluation") != evaluation
            or governed.get("compliance_evaluation") != compliance
            or provenance.get("agent_config") != self._campaign["agent"]
            or provenance.get("user_simulator_config")
            != self._campaign["user_simulator"]
            or provenance.get("official_evaluator_config")
            != self._campaign["official_evaluator"]
        ):
            return False

        compliant = compliance["compliant"]
        violations = compliance["violations"]
        if compliant == bool(violations):
            return False
        expected_state = (
            "compliant_success"
            if evaluation["success"] and compliant
            else "violating_success"
            if evaluation["success"]
            else "compliant_failure"
            if compliant
            else "violating_failure"
        )
        return (
            value.get("state") == expected_state
            and governed.get("state") == expected_state
            and governed.get("task_success") is evaluation["success"]
        )

    def __call__(self, request: RolloutRequest) -> Sequence[Path]:
        task_map = self._maps.get(request.split)
        if task_map is None:
            raise RuntimeContractError("v0.9 runs only Train and Selection.")
        missing = [task_id for task_id in request.task_ids if task_id not in task_map]
        if missing:
            raise RuntimeContractError(f"Unknown {request.split} task IDs: {missing}")
        phase = request.execution_phase or request.method
        skill_path = (
            None
            if request.artifact["version"] == "S0"
            else _resolved_path(request.artifact["path"])
        )
        paths = []
        pending = []
        for surrogate_id in request.task_ids:
            domain, task_id = task_map[surrogate_id].split(":", 1)
            for rollout_index, rollout_seed in enumerate(
                derive_rollout_seeds(
                    self._campaign["campaign_seed"], request.execution_seed_offset
                ),
                start=1,
            ):
                output = (
                    self._artifact_root
                    / "rollouts"
                    / request.split
                    / phase
                    / f"{domain}_{task_id}_rollout_{rollout_index:02d}.json"
                )
                if self._is_reusable(
                    output,
                    domain=domain,
                    task_id=task_id,
                    split=request.split,
                    skill_version=request.artifact["version"],
                    rollout_index=rollout_index,
                    rollout_seed=rollout_seed,
                ):
                    paths.append(output)
                    continue
                pending.append(
                    {
                        "domain": domain,
                        "task_id": task_id,
                        "phase": request.split,
                        "skill_version": request.artifact["version"],
                        "skill_path": skill_path,
                        "rollout_index": rollout_index,
                        "rollout_seed": rollout_seed,
                        "output_path": output,
                    }
                )
                paths.append(output)
        with ThreadPoolExecutor(max_workers=self._max_concurrency) as executor:
            tuple(executor.map(lambda kwargs: self._rollout.run(**kwargs), pending))
        return tuple(paths)


class FormalTau3BenchmarkRuntimeAdapter:
    """τ³ ports for the reused v0.7 three-Step campaign controller."""

    mode = FORMAL_MODE

    def __init__(
        self,
        campaign: dict[str, Any],
        batch_map: dict[str, Any],
        *,
        rollout_backend: Callable[[RolloutRequest], Sequence[Path]],
        learner: Any | None,
        artifact_root: Path | None = None,
    ) -> None:
        validate_campaign_contract(campaign)
        self._campaign = copy.deepcopy(campaign)
        self._maps = _task_maps(campaign, batch_map)
        self._rollout = rollout_backend
        self._learner = learner
        self._artifact_root = artifact_root or (
            REPO_ROOT / "artifacts" / campaign["campaign_id"] / "formal"
        )
        self._trace: list[dict[str, Any]] = []
        self._side_effects = {
            "api_calls": 0,
            "browser_calls": 0,
            "database_calls": 0,
            "filesystem_writes": 0,
        }
        self._checkpoints: dict[str, dict[str, Any]] = {}
        self._summaries: dict[str, dict[str, Any]] = {}
        self._current_sources: dict[str, dict[str, Any]] = {}

    @property
    def trace(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._trace)

    @property
    def side_effects(self) -> dict[str, int]:
        return copy.deepcopy(self._side_effects)

    @staticmethod
    def _method(artifact: dict[str, Any]) -> str:
        if artifact["version"] == "S0":
            return "s0_empty_skill"
        return artifact["version"].casefold()

    def _run(
        self,
        split: str,
        artifact: dict[str, Any],
        task_ids: Sequence[int],
        *,
        execution_phase: str,
    ) -> tuple[Path, ...]:
        paths = tuple(
            self._rollout(
                RolloutRequest(
                    split=split,
                    method=self._method(artifact),
                    artifact=copy.deepcopy(artifact),
                    task_ids=tuple(task_ids),
                    execution_phase=execution_phase,
                )
            )
        )
        expected = len(task_ids) * 3
        if len(paths) != expected:
            raise RuntimeContractError("τ³ rollout backend returned wrong count.")
        self._side_effects["browser_calls"] += expected
        self._side_effects["database_calls"] += expected
        self._side_effects["filesystem_writes"] += expected
        return paths

    def _load_rollout(
        self,
        path: Path,
        surrogate_id: int,
        rollout_index: int,
        split: str,
        artifact: dict[str, Any],
    ) -> dict[str, Any]:
        if not path.is_file():
            raise RuntimeContractError(f"Missing τ³ rollout artifact: {path}")
        value = json.loads(path.read_text(encoding="utf-8"))
        domain, task_id = self._maps[split][surrogate_id].split(":", 1)
        if (
            value.get("schema_version") != "tau3_gse_rollout_0.9.0"
            or value.get("domain") != domain
            or value.get("task_id") != task_id
            or value.get("phase") != split
            or value.get("skill_version") != artifact["version"]
            or value.get("rollout_index") != rollout_index
            or not isinstance(value.get("governed_evidence"), dict)
        ):
            raise RuntimeContractError(f"τ³ rollout lineage mismatch: {path}")
        return value

    def _checkpoint(
        self,
        artifact: dict[str, Any],
        task_ids: Sequence[int],
        *,
        execution_phase: str,
        filename: str,
    ) -> dict[str, Any]:
        paths = self._run(
            "selection", artifact, task_ids, execution_phase=execution_phase
        )
        rows = []
        sources = []
        units = [
            (task_id, rollout_index)
            for task_id in task_ids
            for rollout_index in range(1, 4)
        ]
        for (surrogate_id, rollout_index), path in zip(units, paths, strict=True):
            value = self._load_rollout(
                path, surrogate_id, rollout_index, "selection", artifact
            )
            evaluation = value["task_evaluation"]
            compliance = value["compliance_evaluation"]
            rows.append(
                {
                    "domain": value["domain"],
                    "task_id": value["task_id"],
                    "rollout_index": rollout_index,
                    "rollout_seed": value["rollout_seed"],
                    "task_success": evaluation["success"],
                    "compliant": compliance["compliant"],
                    "state": value["state"],
                }
            )
            sources.append(
                {
                    "domain": value["domain"],
                    "task_id": value["task_id"],
                    "rollout_index": rollout_index,
                    "path": _stored_path(path),
                }
            )
        payload = {
            "schema_version": "autonomous_gse_selection_checkpoint_0.9.0",
            "campaign_id": self._campaign["campaign_id"],
            "parent": copy.deepcopy(artifact),
            "task_count": len(task_ids),
            "trajectory_count": len(rows),
            "rows": rows,
            "sources": sources,
            "metrics": aggregate_metrics(rows),
        }
        path = self._artifact_root / "checkpoints" / filename
        _write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1
        checkpoint = _artifact("selection_checkpoint", artifact["version"], path)
        self._checkpoints[checkpoint["path"]] = payload
        return checkpoint

    def run_fresh_initial_checkpoint(self) -> dict[str, Any]:
        checkpoint = self._checkpoint(
            {
                key: self._campaign["initial_parent"][key]
                for key in ("kind", "version", "path")
            },
            tuple(self._maps["selection"]),
            execution_phase="initial_selection",
            filename="s0_empty_skill.json",
        )
        self._trace.append({"operation": "create_initial_checkpoint"})
        return checkpoint

    def create_initial_checkpoint(
        self, parent: dict[str, Any], task_count: int
    ) -> dict[str, Any]:
        path = self._artifact_root / "checkpoints/s0_empty_skill.json"
        if task_count != 18 or not path.is_file():
            raise RuntimeContractError("Initial S0 checkpoint is unavailable.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("schema_version")
            != "autonomous_gse_selection_checkpoint_0.9.0"
            or payload.get("trajectory_count") != 54
            or payload.get("parent", {}).get("version") != parent.get("version")
        ):
            raise RuntimeContractError("Initial S0 checkpoint is invalid.")
        checkpoint = _artifact("selection_checkpoint", "S0", path)
        self._checkpoints[checkpoint["path"]] = payload
        self._trace.append({"operation": "load_initial_checkpoint"})
        return checkpoint

    def restore_checkpoint(
        self, checkpoint: dict[str, Any], parent: dict[str, Any]
    ) -> None:
        path = _resolved_path(checkpoint["path"])
        if (
            checkpoint.get("kind") != "selection_checkpoint"
            or checkpoint.get("version") != parent.get("version")
            or not path.is_file()
        ):
            raise RuntimeContractError("Resume checkpoint lineage is invalid.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        stored_parent = payload.get("parent", {})
        if (
            payload.get("schema_version")
            != "autonomous_gse_selection_checkpoint_0.9.0"
            or payload.get("trajectory_count") != 54
            or stored_parent.get("version") != parent.get("version")
            or stored_parent.get("path") != parent.get("path")
        ):
            raise RuntimeContractError("Resume checkpoint content is invalid.")
        self._checkpoints[checkpoint["path"]] = payload
        self._trace.append({"operation": "restore_selection_checkpoint"})

    def run_train(self, step: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        task_ids = step["batch"]["task_ids"]
        paths = self._run(
            "train",
            step["parent"],
            task_ids,
            execution_phase=f"step_{step['step']:03d}_train",
        )
        units = [
            (task_id, rollout_index)
            for task_id in task_ids
            for rollout_index in range(1, 4)
        ]
        experiences = []
        sources = []
        for (surrogate_id, rollout_index), path in zip(units, paths, strict=True):
            value = self._load_rollout(
                path, surrogate_id, rollout_index, "train", step["parent"]
            )
            experience = copy.deepcopy(value["governed_evidence"])
            source_id = (
                f"step_{step['step']:03d}_{value['domain']}_{value['task_id']}_"
                f"rollout_{rollout_index:02d}"
            )
            experience["source_id"] = source_id
            experiences.append(experience)
            sources.append(
                {
                    "source_id": source_id,
                    "domain": value["domain"],
                    "task_id": value["task_id"],
                    "rollout_index": rollout_index,
                    "state": value["state"],
                    "path": _stored_path(path),
                }
            )
        self._current_sources = {item["source_id"]: item for item in sources}
        root = self._artifact_root / "steps" / f"step_{step['step']:03d}"
        _write_json(
            root / "train_set.json",
            {
                "step": step["step"],
                "batch_id": step["batch"]["batch_id"],
                "parent": copy.deepcopy(step["parent"]),
                "training_tasks": len(task_ids),
                "training_trajectories": len(experiences),
                "sources": sources,
            },
        )
        _write_json(
            root / "governed_experience.json",
            {
                "schema_version": "governed_experience_0.9.0",
                "experience_count": len(experiences),
                "experiences": experiences,
                "sources": sources,
            },
        )
        self._side_effects["filesystem_writes"] += 2
        self._trace.append({"operation": "run_train", "step": step["step"]})
        return tuple(experiences)

    def skill_for_parent(self, parent: dict[str, Any]) -> str:
        text = _resolved_path(parent["path"]).read_text(encoding="utf-8")
        if not text.strip():
            raise RuntimeContractError("Parent Skill is empty.")
        return _to_v07_method_skill(text)

    def learner_call(
        self,
        step: dict[str, Any],
        request: Any,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str, dict[str, Any] | None]:
        if self._learner is None:
            raise RuntimeContractError("Learner is unavailable for a formal run.")
        response = self._learner.call(request, model, system_prompt, user_prompt)
        role = (
            f"{request.diagnosis_id}_diagnosis"
            if getattr(request, "diagnosis_id", None)
            else "editor"
        )
        root = self._artifact_root / "steps" / f"step_{step['step']:03d}"
        if self._learner.last_call is not None:
            _write_json(root / f"{role}_call.json", self._learner.last_call)
        if self._learner.last_response is not None:
            (root / f"{role}_response.txt").write_text(
                self._learner.last_response + "\n", encoding="utf-8"
            )
        self._side_effects["api_calls"] += 1
        self._side_effects["filesystem_writes"] += 2
        return response

    def record_candidate(
        self, step: dict[str, Any], candidate_skill: str
    ) -> dict[str, Any]:
        path = (
            self._artifact_root
            / "candidates"
            / step["candidate_id"]
            / "skill.md"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_to_canonical_skill(candidate_skill), encoding="utf-8")
        self._side_effects["filesystem_writes"] += 1
        return _artifact("candidate_skill", step["candidate_id"], path)

    def record_proposal(
        self,
        step: dict[str, Any],
        decision: Any,
        candidate: dict[str, Any] | None,
    ) -> None:
        payload = {
            "schema_version": "autonomous_gse_proposal_record_0.9.0",
            "step": step["step"],
            "candidate": copy.deepcopy(candidate),
            "proposal_status": decision.proposal_status,
            "proposal_reason": copy.deepcopy(decision.proposal_reason),
            "diagnosis_calls": decision.diagnosis_calls,
            "editor_calls": decision.editor_calls,
            "diagnoses": copy.deepcopy(decision.diagnoses),
            "eligible_diagnosis_ids": copy.deepcopy(
                decision.eligible_diagnosis_ids
            ),
            "preserve_constraints": copy.deepcopy(decision.preserve_constraints),
            "canonical_edits": copy.deepcopy(decision.canonical_edits),
            "applied_edits": copy.deepcopy(decision.applied_edits),
            "excluded_edits": copy.deepcopy(decision.excluded_edits),
            "source_provenance": copy.deepcopy(self._current_sources),
        }
        path = (
            self._artifact_root
            / "steps"
            / f"step_{step['step']:03d}"
            / "proposal.json"
        )
        _write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1

    def run_candidate_selection(
        self,
        step: dict[str, Any],
        candidate: dict[str, Any],
        promoted_version: str,
        task_count: int,
    ) -> dict[str, Any]:
        if task_count != 18:
            raise RuntimeContractError("Selection task budget is invalid.")
        promoted = {**candidate, "version": promoted_version}
        return self._checkpoint(
            promoted,
            tuple(self._maps["selection"]),
            execution_phase=f"step_{step['step']:03d}_candidate_selection",
            filename=f"step_{step['step']:03d}_{promoted_version}.json",
        )

    def validate_candidate_selection(
        self, step: dict[str, Any], checkpoint: dict[str, Any]
    ) -> None:
        del step
        if checkpoint["path"] not in self._checkpoints:
            raise RuntimeContractError("Candidate checkpoint is unavailable.")

    def build_evolution_summary(
        self, step: dict[str, Any], candidate_checkpoint: dict[str, Any]
    ) -> dict[str, Any]:
        parent = self._checkpoints.get(step["parent_checkpoint"]["path"])
        candidate = self._checkpoints.get(candidate_checkpoint["path"])
        if parent is None or candidate is None:
            raise RuntimeContractError("Selection checkpoint lineage is missing.")
        parent_metrics = parent["metrics"]
        candidate_metrics = candidate["metrics"]
        gate = apply_existing_evolution_gate(
            parent_metrics["overall"], candidate_metrics["overall"]
        )
        payload = {
            "schema_version": "autonomous_gse_evolution_summary_0.9.0",
            "step": step["step"],
            "parent_checkpoint": copy.deepcopy(step["parent_checkpoint"]),
            "candidate_checkpoint": copy.deepcopy(candidate_checkpoint),
            "parent_metrics": parent_metrics,
            "candidate_metrics": candidate_metrics,
            "transition_matrix": transition_matrix(
                parent["rows"], candidate["rows"]
            ),
            "analysis": {
                "aggregate": {
                    "reference": parent_metrics["overall"],
                    "candidate": candidate_metrics["overall"],
                    "deltas": gate["deltas"],
                },
                "evolution_gate": gate,
            },
        }
        path = (
            self._artifact_root
            / "steps"
            / f"step_{step['step']:03d}"
            / "evolution_summary.json"
        )
        _write_json(path, payload)
        self._side_effects["filesystem_writes"] += 1
        summary = _artifact(
            "evolution_summary", f"step_{step['step']:03d}", path
        )
        self._summaries[summary["path"]] = payload
        return summary

    def apply_gate(self, step: dict[str, Any], summary: dict[str, Any]) -> str:
        del step
        payload = self._summaries.get(summary["path"])
        if payload is None:
            raise RuntimeContractError("Evolution summary is unavailable.")
        decision = payload["analysis"]["evolution_gate"]["decision"]
        return {"continue_evolution": "ACCEPT", "reject": "REJECT"}[decision]


def run_v09_campaign(
    campaign: dict[str, Any],
    batch_map: dict[str, Any],
    adapter: FormalTau3BenchmarkRuntimeAdapter,
    *,
    scheduled_steps: int = 3,
    resume_state: dict[str, Any] | None = None,
    on_step_completed: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run τ³ evidence through the unchanged v0.7 campaign state machine."""

    validate_campaign_contract(campaign)
    report = v07.run_v07_campaign(
        _controller_campaign(campaign),
        _controller_batch_map(campaign, batch_map),
        adapter,
        scheduled_steps=scheduled_steps,
        maximum_learner_calls=campaign["budget"]["maximum_learner_calls"],
        resume_state=resume_state,
        on_step_completed=on_step_completed,
    )
    report["schema_version"] = "autonomous_gse_formal_report_0.9.0"
    report["protocol_version"] = PROTOCOL_VERSION
    report["campaign_id"] = campaign["campaign_id"]
    report["mode"] = FORMAL_MODE
    for step in report["steps"]:
        step["schema_version"] = "autonomous_gse_step_0.9.0"
        step["protocol_version"] = PROTOCOL_VERSION
        step["campaign_id"] = campaign["campaign_id"]
    usage = report["budget_usage"]
    usage["train_trajectories"] *= 3
    usage["initial_selection_trajectories"] *= 3
    usage["candidate_selection_trajectories"] *= 3
    usage["total_trajectories"] = (
        usage["train_trajectories"]
        + usage["initial_selection_trajectories"]
        + usage["candidate_selection_trajectories"]
    )
    if usage["total_trajectories"] > campaign["budget"]["maximum_total_trajectories"]:
        raise RuntimeContractError("v0.9 rollout budget was exceeded.")
    report["disabled_phases"] = {"official_test": True}
    return report


def _campaign_paths(
    campaign: dict[str, Any], artifact_root: Path | None = None
) -> dict[str, Path]:
    root = artifact_root or (
        REPO_ROOT / "artifacts" / campaign["campaign_id"] / "formal"
    )
    return {
        "checkpoint": root / "checkpoints/s0_empty_skill.json",
        "resume": root / RESUME_STATE_FILENAME,
        "report": root / CAMPAIGN_REPORT_FILENAME,
    }


def run_initial_checkpoint(
    campaign_path: Path,
    *,
    rollout_backend: Callable[[RolloutRequest], Sequence[Path]] | None = None,
    judge_caller: JudgeCaller = default_judge_caller,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    campaign = json.loads(campaign_path.resolve().read_text(encoding="utf-8"))
    validate_campaign_contract(campaign)
    batch_map = json.loads(
        _resolved_path(campaign["train"]["batch_map"]).read_text(encoding="utf-8")
    )
    paths = _campaign_paths(campaign, artifact_root)
    if paths["checkpoint"].exists():
        raise RuntimeContractError("Initial S0 checkpoint already exists.")
    backend = rollout_backend or Tau3CampaignRolloutBackend(
        campaign,
        batch_map,
        judge_caller=judge_caller,
        artifact_root=artifact_root,
    )
    adapter = FormalTau3BenchmarkRuntimeAdapter(
        campaign,
        batch_map,
        rollout_backend=backend,
        learner=None,
        artifact_root=artifact_root,
    )
    checkpoint = adapter.run_fresh_initial_checkpoint()
    return {"status": "S0_CHECKPOINT_CREATED", "checkpoint": checkpoint}


def rejudge_initial_checkpoint(
    campaign_path: Path,
    *,
    judge_caller: JudgeCaller = default_judge_caller,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    """Rebuild S0 governed artifacts from frozen raw results using Judge v3."""

    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env", override=False)
    campaign = json.loads(campaign_path.resolve().read_text(encoding="utf-8"))
    validate_campaign_contract(campaign)
    paths = _campaign_paths(campaign, artifact_root)
    if not paths["checkpoint"].is_file():
        raise RuntimeContractError("Initial S0 checkpoint is missing.")
    checkpoint = json.loads(paths["checkpoint"].read_text(encoding="utf-8"))
    sources = checkpoint.get("sources")
    if (
        checkpoint.get("schema_version")
        != "autonomous_gse_selection_checkpoint_0.9.0"
        or checkpoint.get("parent", {}).get("version") != "S0"
        or checkpoint.get("trajectory_count") != 54
        or not isinstance(sources, list)
        or len(sources) != 54
    ):
        raise RuntimeContractError("Initial S0 checkpoint cannot be rejudged.")

    artifact_root_path = paths["checkpoint"].parents[1]
    artifact_root_path.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    rows = []
    with tempfile.TemporaryDirectory(
        prefix="rejudge_v3_", dir=artifact_root_path
    ) as directory:
        staging_root = Path(directory)
        for index, source in enumerate(sources, start=1):
            target = _resolved_path(source["path"])
            value = json.loads(target.read_text(encoding="utf-8"))
            compliance = value.get("compliance_evaluation", {})
            if compliance.get("judge_prompt_version") != (
                "tau3_policy_grounded_judge_v2"
            ):
                raise RuntimeContractError(
                    f"Expected Judge v2 artifact before rejudging: {target}"
                )
            raw_path = _resolved_path(
                value["provenance"]["raw_tau3_result_path"]
            )
            simulation = json.loads(raw_path.read_text(encoding="utf-8"))
            domain = value["domain"]
            task_id = str(value["task_id"])
            policy_path = (
                REPO_ROOT
                / campaign["benchmark"]["path"]
                / f"data/tau2/domains/{domain}/policy.md"
            )
            task = {
                "id": task_id,
                "user_scenario": copy.deepcopy(
                    value["governed_evidence"]["goal"]
                ),
            }
            evidence = evaluate_simulation(
                source_id=(
                    f"selection_{domain}_{task_id}_rollout_"
                    f"{value['rollout_index']:02d}"
                ),
                domain=domain,
                task=task,
                simulation=simulation,
                domain_policy=policy_path.read_text(encoding="utf-8"),
                judge_caller=judge_caller,
            )
            provenance = copy.deepcopy(value["provenance"])
            provenance.update(
                {
                    **policy_provenance(policy_path),
                    "judge_config": copy.deepcopy(campaign["compliance_judge"]),
                    "agent_config": copy.deepcopy(campaign["agent"]),
                    "user_simulator_config": copy.deepcopy(
                        campaign["user_simulator"]
                    ),
                    "official_evaluator_config": copy.deepcopy(
                        campaign["official_evaluator"]
                    ),
                }
            )
            staged_path = staging_root / f"{index:02d}.json"
            write_rollout_artifact(
                staged_path,
                domain=domain,
                task_id=task_id,
                phase="selection",
                skill_version="S0",
                rollout_index=value["rollout_index"],
                rollout_seed=value["rollout_seed"],
                governed_evidence=evidence,
                provenance=provenance,
            )
            staged.append((staged_path, target))
            rows.append(
                {
                    "domain": domain,
                    "task_id": task_id,
                    "rollout_index": value["rollout_index"],
                    "rollout_seed": value["rollout_seed"],
                    "task_success": evidence["task_evaluation"]["success"],
                    "compliant": evidence["compliance_evaluation"]["compliant"],
                    "state": evidence["state"],
                }
            )

        rebuilt_checkpoint = {
            **checkpoint,
            "rows": rows,
            "metrics": aggregate_metrics(rows),
        }
        backup = paths["checkpoint"].with_name("s0_empty_skill.judge_v2.json")
        if backup.exists():
            raise RuntimeContractError("Judge v2 checkpoint backup already exists.")
        shutil.copy2(paths["checkpoint"], backup)
        for staged_path, target in staged:
            staged_path.replace(target)
        _write_json(paths["checkpoint"], rebuilt_checkpoint)

    return {
        "status": "S0_CHECKPOINT_REJUDGED",
        "judge_prompt_version": campaign["compliance_judge"]["prompt_version"],
        "trajectory_count": len(rows),
        "checkpoint": _artifact(
            "selection_checkpoint", "S0", paths["checkpoint"]
        ),
        "backup": _artifact("selection_checkpoint", "S0", backup),
        "metrics": rebuilt_checkpoint["metrics"],
    }


def run_formal_campaign_cli(
    campaign_path: Path,
    *,
    rollout_backend: Callable[[RolloutRequest], Sequence[Path]] | None = None,
    learner: Any | None = None,
    judge_caller: JudgeCaller = default_judge_caller,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    campaign = json.loads(campaign_path.resolve().read_text(encoding="utf-8"))
    validate_campaign_contract(campaign)
    batch_map = json.loads(
        _resolved_path(campaign["train"]["batch_map"]).read_text(encoding="utf-8")
    )
    paths = _campaign_paths(campaign, artifact_root)
    if not paths["checkpoint"].is_file():
        raise RuntimeContractError("Initial S0 checkpoint is missing.")
    if paths["report"].exists():
        raise RuntimeContractError("Campaign report already exists.")
    if learner is None:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env", override=False)
        learner = v07.SeededLearnerAdapter(_v07_method_campaign(campaign))
    backend = rollout_backend or Tau3CampaignRolloutBackend(
        campaign,
        batch_map,
        judge_caller=judge_caller,
        artifact_root=artifact_root,
    )
    adapter = FormalTau3BenchmarkRuntimeAdapter(
        campaign,
        batch_map,
        rollout_backend=backend,
        learner=learner,
        artifact_root=artifact_root,
    )
    resume_state = (
        json.loads(paths["resume"].read_text(encoding="utf-8"))
        if paths["resume"].is_file()
        else None
    )
    report = run_v09_campaign(
        campaign,
        batch_map,
        adapter,
        resume_state=resume_state,
        on_step_completed=lambda state: _write_json(paths["resume"], state),
    )
    _write_json(paths["report"], report)
    return {
        "status": "AUTONOMOUS_GSE_V09_CAMPAIGN_COMPLETED",
        "report": _artifact("campaign_report", campaign["campaign_id"], paths["report"]),
        "step_outcomes": [step["outcome"] for step in report["steps"]],
        "final_parent": report["final_parent"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    default_campaign = REPO_ROOT / (
        "experiments/campaigns/autonomous_gse_v09/campaign_manifest.json"
    )
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "initial-checkpoint", "rejudge-initial-checkpoint", "run"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--campaign", type=Path, default=default_campaign)
    args = parser.parse_args(argv)
    campaign = json.loads(args.campaign.resolve().read_text(encoding="utf-8"))
    if args.command == "plan":
        batch_map = json.loads(
            _resolved_path(campaign["train"]["batch_map"]).read_text(
                encoding="utf-8"
            )
        )
        result = build_campaign_dry_plan(campaign, batch_map)
    elif args.command == "initial-checkpoint":
        result = run_initial_checkpoint(args.campaign)
    elif args.command == "rejudge-initial-checkpoint":
        result = rejudge_initial_checkpoint(args.campaign)
    else:
        result = run_formal_campaign_cli(args.campaign)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
