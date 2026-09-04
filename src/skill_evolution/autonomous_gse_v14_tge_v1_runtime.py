"""Minimal GSE v0.14 adapter for the frozen TGE benchmark v1."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import traceback
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable
from benchmarks.tau2_governed_evolution.compiler.schema import CompiledTaskBundle
from benchmarks.tau2_governed_evolution.compliance.composite import (
    evaluate_composed_compliance,
)
from benchmarks.tau2_governed_evolution.compliance.oracle import (
    evaluate_target_compliance,
)
from benchmarks.tau2_governed_evolution.compliance.templates import ORACLES
from benchmarks.tau2_governed_evolution.evaluation.task_success import (
    evaluate_tge_v1_task_success,
)
from src.adapters.tau2.tau3_gse_runtime import (
    _skill_environment,
    _trajectory_model_args,
    stable_trajectory,
    task_context,
    write_rollout_artifact,
)
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    load_authoritative_domain_contexts,
)
from src.skill_evolution.autonomous_gse_v14_orchestrator import (
    EvolutionServices,
    resume_campaign,
    run_campaign,
)
from src.skill_evolution.distributional_gate_v14 import (
    DEFAULT_GATE_CONFIG,
    build_distributional_gate_decision,
)
from src.skill_evolution.joint_distribution_v14 import (
    build_joint_distribution_report,
    distribution,
    state_code,
    validate_monitor_result,
)
from src.skill_evolution.two_dimensional_gate import classify_state

ensure_tau2_importable()

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_VERSION = "autonomous_gse_v14_tge_v1"
RUNTIME_VERSION = "tge_v1_runtime_0.1.0"
ROLLOUTS_PER_TASK = 3
ROLLOUT_SEEDS = (200, 201, 202)
SPLIT_COUNTS = {"train": 48, "monitor": 20, "test": 48}
COMPOSITION_TEMPLATE = "airline.composition.booking_baggage_confirmation"
ORDERING_TEMPLATE = "airline.ordering.delayed_flight_compensation"
ACCESS_POLICY = {
    "rollout_for_evolution": {"train"},
    "diagnosis": {"train"},
    "targeted_replay": {"train"},
    "selection": {"monitor"},
    "bootstrap_gate": {"monitor"},
    "final_evaluation": {"test"},
    "plan_validation": {"train", "monitor", "test"},
}


class TGEV1RuntimeContractError(ValueError):
    """Raised when the frozen benchmark/runtime contract drifts."""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_split_access(operation: str, split: str) -> None:
    allowed = ACCESS_POLICY.get(operation)
    if allowed is None or split not in allowed:
        raise TGEV1RuntimeContractError(
            f"Operation {operation!r} cannot access frozen split {split!r}."
        )


def _benchmark_paths(campaign: dict[str, Any]) -> dict[str, Path]:
    benchmark_root = _resolve(campaign["benchmark"]["root"])
    return {
        "split_manifest": _resolve(campaign["frozen_split_manifest"]),
        "family_registry": _resolve(campaign["family_registry"]),
        "entity_assignments": _resolve(campaign["entity_assignments"]),
        **{
            f"{split}_tasks": benchmark_root / split / "tasks.json"
            for split in SPLIT_COUNTS
        },
        **{
            f"{split}_metadata": benchmark_root / split / "task_metadata.yaml"
            for split in SPLIT_COUNTS
        },
        **{
            f"{split}_bundles": benchmark_root / split / "compiled_bundles.yaml"
            for split in SPLIT_COUNTS
        },
    }


def validate_campaign_contract(campaign: dict[str, Any]) -> None:
    if (
        campaign.get("schema_version") != "autonomous_gse_tge_campaign_0.1.0"
        or campaign.get("protocol_version") != "autonomous_gse_v14"
        or campaign.get("campaign_id") != PROTOCOL_VERSION
        or campaign.get("runtime_module")
        != "src.skill_evolution.autonomous_gse_v14_tge_v1_runtime"
        or campaign.get("runtime_version") != RUNTIME_VERSION
        or campaign.get("campaign_seed") != 200
    ):
        raise TGEV1RuntimeContractError("TGE v1 campaign identity is invalid.")
    if campaign.get("benchmark", {}).get("version") != "tau2_governed_evolution_v1":
        raise TGEV1RuntimeContractError("Frozen benchmark version is invalid.")
    if campaign["benchmark"].get("domains") != ["airline"]:
        raise TGEV1RuntimeContractError("TGE v1 is an Airline-only campaign.")
    if campaign.get("schedule") != {"evolution_steps": 3}:
        raise TGEV1RuntimeContractError("TGE v1 requires exactly three steps.")
    evolution = campaign.get("evolution", {})
    if any(
        (
            evolution.get("source_split") != "train",
            evolution.get("tasks") != 48,
            evolution.get("batches") != 3,
            evolution.get("tasks_per_batch") != 16,
            evolution.get("rollouts_per_task") != 3,
            evolution.get("cumulative_evidence") is not False,
            evolution.get("replay_previous_batches") is not False,
        )
    ):
        raise TGEV1RuntimeContractError("TGE evolution workload drifted.")
    monitor = campaign.get("monitor", {})
    if any(
        (
            monitor.get("source_split") != "monitor",
            monitor.get("tasks") != 20,
            monitor.get("rollouts_per_task") != 3,
            monitor.get("fixed_across_steps") is not True,
            monitor.get("learning_access") != "forbidden",
            monitor.get("feedback_to_learner") != "forbidden",
            monitor.get("gate_enabled") is not True,
        )
    ):
        raise TGEV1RuntimeContractError("TGE fixed Monitor contract drifted.")
    test_policy = campaign.get("test_policy", {})
    if test_policy != {
        "held_out": True,
        "allowed_during_evolution": False,
        "allowed_for_selection": False,
        "allowed_for_diagnosis": False,
        "allowed_after_evolution": True,
        "automatic_execution": False,
    }:
        raise TGEV1RuntimeContractError("TGE Test access policy drifted.")
    frozen = {
        "model": "openai/deepseek-v4-flash",
        "thinking": "high",
        "reasoning_effort": "high",
        "max_tokens": 8192,
        "empty_response_retries": 2,
        "empty_response_retry_max_tokens": 8192,
    }
    for role, temperature in (("agent", 0.2), ("user_simulator", 0.0)):
        config = campaign.get(role, {})
        if config.get("temperature") != temperature or any(
            config.get(key) != value for key, value in frozen.items()
        ):
            raise TGEV1RuntimeContractError(f"Frozen {role} config drifted.")
    if campaign["agent"].get("max_steps") != 200:
        raise TGEV1RuntimeContractError("Agent max_steps drifted.")
    if campaign.get("distributional_gate") != DEFAULT_GATE_CONFIG:
        raise TGEV1RuntimeContractError("v14 Gate semantics drifted.")
    if campaign.get("compliance_evaluator") != {
        "implementation": "deterministic_tge_v1_oracles",
        "llm_judge": False,
        "routing": ["atomic", "ordering", "composition"],
    }:
        raise TGEV1RuntimeContractError("TGE compliance evaluator drifted.")


def load_frozen_assets(
    campaign: dict[str, Any], *, operation: str = "plan_validation"
) -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
    dict[str, CompiledTaskBundle],
    dict[str, set[str]],
]:
    """Load exact frozen tasks; metadata never enters the Agent request."""

    from tau2.data_model.tasks import Task

    paths = _benchmark_paths(campaign)
    tasks: dict[str, Any] = {}
    metadata: dict[str, dict[str, Any]] = {}
    bundles: dict[str, CompiledTaskBundle] = {}
    split_ids: dict[str, set[str]] = {}
    for split, expected in SPLIT_COUNTS.items():
        assert_split_access(operation, split)
        split_tasks = [
            Task.model_validate(item)
            for item in json.loads(paths[f"{split}_tasks"].read_text(encoding="utf-8"))
        ]
        split_metadata = yaml.safe_load(
            paths[f"{split}_metadata"].read_text(encoding="utf-8")
        )["metadata"]
        split_bundles = yaml.safe_load(
            paths[f"{split}_bundles"].read_text(encoding="utf-8")
        )["compiled_bundles"]
        if len(split_tasks) != expected or not (
            len(split_tasks) == len(split_metadata) == len(split_bundles)
        ):
            raise TGEV1RuntimeContractError(f"Frozen {split} count drifted.")
        split_ids[split] = {task.id for task in split_tasks}
        for task in split_tasks:
            tasks[task.id] = task
        for item in split_metadata:
            if item["assigned_split"] != split or item["source"]["calibration_only"]:
                raise TGEV1RuntimeContractError("Frozen task provenance is invalid.")
            metadata[item["task_id"]] = item
        for item in split_bundles:
            bundle = CompiledTaskBundle.from_dict(item)
            bundles[bundle.task.id] = bundle
    if len(tasks) != 116 or set(tasks) != set(metadata) or set(tasks) != set(bundles):
        raise TGEV1RuntimeContractError("Frozen Task/metadata/bundle IDs do not align.")
    manifest = yaml.safe_load(paths["split_manifest"].read_text(encoding="utf-8"))
    manifest_families = manifest.get("families", [])
    manifest_counts = {
        split: sum(item["task_count"] for item in manifest_families if item["split"] == split)
        for split in SPLIT_COUNTS
    }
    if manifest_counts != SPLIT_COUNTS:
        raise TGEV1RuntimeContractError("Frozen split manifest counts drifted.")
    return tasks, metadata, bundles, split_ids


def evaluator_route(metadata: dict[str, Any]) -> dict[str, str]:
    template = metadata["template_id"]
    if template == COMPOSITION_TEMPLATE:
        return {"task_success": "tge_v1", "compliance": "composition"}
    if template not in ORACLES:
        raise TGEV1RuntimeContractError(f"No compliance route for {template}.")
    return {
        "task_success": "tge_v1",
        "compliance": "ordering" if template == ORDERING_TEMPLATE else "atomic",
    }


def validate_batch_map(
    batch_map: dict[str, Any], campaign: dict[str, Any]
) -> dict[str, Any]:
    validate_campaign_contract(campaign)
    tasks, metadata, _, split_ids = load_frozen_assets(campaign)
    assignment = batch_map.get("assignment", {})
    if set(assignment) != {"train", "monitor", "test"}:
        raise TGEV1RuntimeContractError("Batch assignment must contain all frozen splits.")
    for split in SPLIT_COUNTS:
        if set(assignment[split]) != split_ids[split]:
            raise TGEV1RuntimeContractError(f"Batch assignment drifted from {split}.")
    flattened: list[str] = []
    family_to_batch: dict[str, str] = {}
    for index, batch in enumerate(batch_map.get("batches", []), start=1):
        tagged = batch.get("task_ids", [])
        if batch.get("batch_id") != f"batch_{index}" or len(tagged) != 16:
            raise TGEV1RuntimeContractError("Evolution batch must be fixed 16-task batch.")
        ids = [value.split(":", 1)[1] for value in tagged if value.startswith("airline:")]
        if len(ids) != 16 or not set(ids) <= split_ids["train"]:
            raise TGEV1RuntimeContractError("Evolution batch contains non-Train tasks.")
        families = sorted({metadata[task_id]["family_id"] for task_id in ids})
        mechanisms = sorted({metadata[task_id]["template_id"] for task_id in ids})
        roles = sorted({metadata[task_id]["evolution_role"] for task_id in ids})
        if batch.get("family_ids") != families or batch.get("mechanism_ids") != mechanisms or batch.get("roles") != roles:
            raise TGEV1RuntimeContractError("Batch provenance summary drifted.")
        for family in families:
            previous = family_to_batch.setdefault(family, batch["batch_id"])
            if previous != batch["batch_id"]:
                raise TGEV1RuntimeContractError("A Train family crosses Evolution batches.")
        flattened.extend(ids)
    if len(batch_map.get("batches", [])) != 3 or len(flattened) != 48 or set(flattened) != split_ids["train"]:
        raise TGEV1RuntimeContractError("Batches are not a disjoint partition of Train.")
    monitor_ids = batch_map.get("monitor", {}).get("task_ids", [])
    if {value.split(":", 1)[1] for value in monitor_ids} != split_ids["monitor"]:
        raise TGEV1RuntimeContractError("Monitor IDs drifted.")
    if set(flattened) & split_ids["monitor"] or set(flattened) & split_ids["test"]:
        raise TGEV1RuntimeContractError("Protected split leaked into Evolution batches.")
    if split_ids["monitor"] & split_ids["test"]:
        raise TGEV1RuntimeContractError("Monitor and Test overlap.")
    if len(tasks) != 116:
        raise TGEV1RuntimeContractError("Frozen benchmark size drifted.")
    expected_hash = campaign["frozen_hashes"]["batch_map"]
    batch_path = _resolve(campaign["evolution"]["batch_map"])
    if _sha256(batch_path) != expected_hash:
        raise TGEV1RuntimeContractError("Batch map hash mismatch.")
    return {"tasks": tasks, "metadata": metadata, "split_ids": split_ids}


def validate_frozen_hashes(campaign: dict[str, Any]) -> dict[str, str]:
    paths = _benchmark_paths(campaign)
    actual = {
        "split_manifest": _sha256(paths["split_manifest"]),
        "train_tasks": _sha256(paths["train_tasks"]),
        "monitor_tasks": _sha256(paths["monitor_tasks"]),
        "test_tasks": _sha256(paths["test_tasks"]),
        "batch_map": _sha256(_resolve(campaign["evolution"]["batch_map"])),
    }
    if actual != campaign.get("frozen_hashes"):
        raise TGEV1RuntimeContractError("Frozen benchmark hashes do not match campaign.")
    return actual


def _policy_rules() -> dict[str, dict[str, Any]]:
    path = REPO_ROOT / "benchmarks/tau2_governed_evolution/registry/airline_policy_registry.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {item["rule_id"]: item for item in document["rules"]}


def _compliance_result(bundle: CompiledTaskBundle, simulation: Any) -> tuple[bool, Any]:
    if bundle.template_id == COMPOSITION_TEMPLATE:
        result = evaluate_composed_compliance(bundle, simulation)
        return result.joint_compliant, result
    result = evaluate_target_compliance(bundle, simulation)
    return result.compliant, result


def _violations_for_diagnosis(result: Any) -> list[dict[str, Any]]:
    components = getattr(result, "component_results", None) or [result]
    rules = _policy_rules()
    violations = []
    for component in components:
        if component.compliant:
            continue
        rule = rules[component.rule_id]
        step_ids = sorted({
            item.get("event_index")
            for item in component.violation_evidence
            if isinstance(item.get("event_index"), int)
        })
        violations.append({
            "policy_template_id": component.rule_id,
            "policy_id": component.rule_id,
            "policy_section": rule["source_section"],
            "policy_clause": rule["policy_rule"].strip(),
            "policy_requirement": rule["policy_rule"].strip(),
            "description": rule["policy_rule"].strip(),
            "evidence_steps": step_ids,
            "reason": "; ".join(
                item.get("reason", "") for item in component.violation_evidence
                if item.get("reason")
            ),
        })
    return violations


def evaluate_tge_v1_rollout(
    *, source_id: str, task: Any, bundle: CompiledTaskBundle, simulation: Any
) -> dict[str, Any]:
    """Map independent outcome/oracle results into the unchanged v14 evidence shape."""

    success, reward_details = evaluate_tge_v1_task_success(bundle, simulation)
    compliant, compliance_result = _compliance_result(bundle, simulation)
    trajectory = stable_trajectory(simulation.model_dump(mode="json").get("messages") or [])
    violations = _violations_for_diagnosis(compliance_result)
    state = classify_state(success, compliant).value
    task_evaluation = {
        "success": success,
        "reward_details": reward_details,
        "termination_reason": getattr(
            getattr(simulation, "termination_reason", None), "value", None
        ),
        "evaluator": "tge_v1_task_success",
    }
    compliance = {
        "compliant": compliant,
        "evaluator": "deterministic_tge_v1_oracles",
        "llm_judge": False,
        "violations": violations,
    }
    return {
        "source_id": source_id,
        "state": state,
        "goal": task_context(task, domain="airline")["user_scenario"],
        "actions": [
            {"step": item["step"], "action": item["event_type"], **item}
            for item in trajectory
        ],
        "task_success": success,
        "task_evaluation": task_evaluation,
        "applicable_policies": [],
        "process_feedback": {"compliant": compliant, "violated_policies": violations},
        "compliance_evaluation": compliance,
        "trajectory": trajectory,
    }


def _run_task(
    campaign: dict[str, Any], task: Any, bundle: CompiledTaskBundle, *,
    skill: dict[str, str], rollout_index: int, rollout_seed: int, source_id: str,
) -> tuple[Any, dict[str, Any]]:
    from tau2.data_model.simulation import TextRunConfig
    from tau2.evaluator import evaluator_nl_assertions
    from tau2.run import run_single_task

    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = campaign["task_success_evaluator"]["nl_assertions_model"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
        "temperature": campaign["task_success_evaluator"]["nl_assertions_temperature"]
    }
    agent = campaign["agent"]
    user = campaign["user_simulator"]
    skill_path = None if skill["skill_version"] == "S0" else _resolve(skill["skill_path"])
    agent_args = _trajectory_model_args(agent, rollout_seed, include_max_tokens=True)
    if skill_path is not None:
        agent_args["manual_skill_path"] = str(skill_path.resolve())
    with _skill_environment(skill_path) as agent_name:
        config = TextRunConfig(
            domain="airline",
            task_ids=[task.id],
            agent=agent_name,
            user=user["implementation"],
            llm_agent=agent["model"],
            llm_args_agent=agent_args,
            llm_user=user["model"],
            llm_args_user=_trajectory_model_args(user, rollout_seed, include_max_tokens=True),
            max_steps=agent["max_steps"],
            seed=rollout_seed,
            max_retries=0,
            auto_review=False,
            log_level="WARNING",
        )
        simulation = run_single_task(config, task, seed=rollout_seed, auto_review=False)
    return simulation, evaluate_tge_v1_rollout(
        source_id=source_id, task=task, bundle=bundle, simulation=simulation
    )


class TGERolloutBackend:
    """Execute frozen Train or Monitor tasks with TGE evaluators."""

    def __init__(self, campaign: dict[str, Any], *, artifact_root: Path) -> None:
        validate_campaign_contract(campaign)
        tasks, metadata, bundles, split_ids = load_frozen_assets(campaign)
        self.campaign = copy.deepcopy(campaign)
        self.tasks = tasks
        self.metadata = metadata
        self.bundles = bundles
        self.split_ids = split_ids
        self.root = artifact_root

    def _reusable(
        self, path: Path, *, split: str, unit: dict[str, Any], skill: dict[str, str]
    ) -> bool:
        try:
            value = _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        return (
            value.get("domain") == "airline"
            and value.get("task_id") == unit["task_id"]
            and value.get("phase") == ("monitor" if split == "monitor" else "train")
            and value.get("skill_version") == skill["skill_version"]
            and value.get("rollout_index") == unit["rollout_index"]
            and value.get("rollout_seed") == unit["rollout_seed"]
            and value.get("provenance", {}).get("skill_id") == skill["skill_id"]
            and value.get("provenance", {}).get("skill_path") == skill["skill_path"]
            and value.get("provenance", {}).get("frozen_hashes")
            == self.campaign["frozen_hashes"]
        )

    def _run_one(
        self, *, split: str, unit: dict[str, Any], skill: dict[str, str], output: Path
    ) -> None:
        operation = "selection" if split == "monitor" else "rollout_for_evolution"
        assert_split_access(operation, split)
        task_id = unit["task_id"]
        if task_id not in self.split_ids[split]:
            raise TGEV1RuntimeContractError("Rollout task does not belong to requested split.")
        error_path = output.with_name(output.stem + "_error.json")
        try:
            simulation, evidence = _run_task(
                self.campaign,
                self.tasks[task_id],
                self.bundles[task_id],
                skill=skill,
                rollout_index=unit["rollout_index"],
                rollout_seed=unit["rollout_seed"],
                source_id=(
                    f"tge_{split}_{skill['skill_id']}_{task_id}_"
                    f"rollout_{unit['rollout_index']:02d}"
                ),
            )
            raw_path = output.with_name(output.stem + "_tau2_raw.json")
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
            write_rollout_artifact(
                output,
                domain="airline",
                task_id=task_id,
                phase="monitor" if split == "monitor" else "train",
                skill_version=skill["skill_version"],
                rollout_index=unit["rollout_index"],
                rollout_seed=unit["rollout_seed"],
                governed_evidence=evidence,
                provenance={
                    "campaign_id": self.campaign["campaign_id"],
                    "task_split": split,
                    "skill_id": skill["skill_id"],
                    "skill_path": skill["skill_path"],
                    "raw_tau2_result_path": raw_path.as_posix(),
                    "task_success_evaluator": "tge_v1",
                    "compliance_evaluator": "deterministic_tge_v1_oracles",
                    "frozen_hashes": copy.deepcopy(self.campaign["frozen_hashes"]),
                },
            )
            error_path.unlink(missing_ok=True)
        except Exception as error:
            _write_json(error_path, {
                "schema_version": "tge_v1_rollout_error_0.1.0",
                "campaign_id": self.campaign["campaign_id"],
                "split": split,
                "skill_id": skill["skill_id"],
                **copy.deepcopy(unit),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
            })
            raise

    def run_batch(
        self, *, split: str, task_ids: list[str], skill: dict[str, str], label: str
    ) -> list[Path]:
        operation = "selection" if split == "monitor" else "rollout_for_evolution"
        assert_split_access(operation, split)
        ids = [value.split(":", 1)[1] for value in task_ids]
        if set(ids) - self.split_ids[split]:
            raise TGEV1RuntimeContractError("Rollout batch crosses frozen split.")
        units = [
            {
                "domain": "airline",
                "task_id": task_id,
                "rollout_index": index,
                "rollout_seed": seed,
            }
            for task_id in ids
            for index, seed in enumerate(ROLLOUT_SEEDS, start=1)
        ]
        paths: list[Path] = []
        pending: list[tuple[dict[str, Any], Path]] = []
        for unit in units:
            output = self.root / (
                "monitor_rollouts" if split == "monitor" else "rollouts/train"
            ) / label / f"airline_{unit['task_id']}_rollout_{unit['rollout_index']:02d}.json"
            paths.append(output)
            if not self._reusable(output, split=split, unit=unit, skill=skill):
                pending.append((unit, output))
        with ThreadPoolExecutor(max_workers=self.campaign["execution"]["max_concurrency"]) as pool:
            tuple(pool.map(
                lambda pair: self._run_one(
                    split=split, unit=pair[0], skill=skill, output=pair[1]
                ),
                pending,
            ))
        return paths


def _rows_and_evidence(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, evidence = [], []
    for path in paths:
        value = _load_json(path)
        governed = value.get("governed_evidence")
        if not isinstance(governed, dict):
            raise TGEV1RuntimeContractError("Governed evidence is missing.")
        enriched = {
            **copy.deepcopy(governed),
            "domain": value["domain"],
            "task_id": str(value["task_id"]),
            "rollout_index": value["rollout_index"],
            "rollout_seed": value["rollout_seed"],
            "state": value["state"],
        }
        evidence.append(copy.deepcopy(enriched))
        rows.append({**enriched, "trajectory_artifact_path": path.resolve().as_posix()})
    return rows, evidence


def build_monitor_plan(campaign: dict[str, Any], batch_map: dict[str, Any]) -> dict[str, Any]:
    validate_batch_map(batch_map, campaign)
    task_ids = copy.deepcopy(batch_map["monitor"]["task_ids"])
    units = [
        {
            "domain": "airline",
            "task_id": tagged.split(":", 1)[1],
            "rollout_index": index,
            "rollout_seed": seed,
        }
        for tagged in task_ids
        for index, seed in enumerate(ROLLOUT_SEEDS, start=1)
    ]
    return {
        "schema_version": "autonomous_gse_monitor_plan_0.14.0",
        "campaign_id": campaign["campaign_id"],
        "monitor_id": "fixed_monitor_m",
        "source_split": "monitor",
        "task_ids": task_ids,
        "rollouts_per_task": 3,
        "units": units,
        "trajectory_count_per_skill": 60,
    }


def _monitor_result(
    campaign: dict[str, Any], plan: dict[str, Any], skill: dict[str, str], paths: list[Path]
) -> dict[str, Any]:
    expected = {
        (unit["domain"], unit["task_id"], unit["rollout_index"]): unit["rollout_seed"]
        for unit in plan["units"]
    }
    rows = []
    for path in paths:
        value = _load_json(path)
        key = (value["domain"], str(value["task_id"]), value["rollout_index"])
        if key not in expected or value["rollout_seed"] != expected[key]:
            raise TGEV1RuntimeContractError("Monitor rollout lineage is invalid.")
        success = value["task_evaluation"]["success"]
        compliant = value["compliance_evaluation"]["compliant"]
        rows.append({
            "source_id": value["governed_evidence"]["source_id"],
            "domain": "airline",
            "task_id": key[1],
            "rollout_index": key[2],
            "rollout_seed": value["rollout_seed"],
            "skill_id": skill["skill_id"],
            "skill_version": skill["skill_version"],
            "task_success": success,
            "compliant": compliant,
            "state": classify_state(success, compliant).value,
            "state_code": state_code(success, compliant),
            "trajectory_artifact_path": path.resolve().as_posix(),
        })
    order = {
        (unit["domain"], unit["task_id"], unit["rollout_index"]): index
        for index, unit in enumerate(plan["units"])
    }
    rows.sort(key=lambda row: order[(row["domain"], row["task_id"], row["rollout_index"])])
    result = {
        "schema_version": "autonomous_gse_monitor_result_0.14.0",
        "campaign_id": campaign["campaign_id"],
        "monitor_id": "fixed_monitor_m",
        "skill_artifact_contract": "immutable_identity",
        "skill": copy.deepcopy(skill),
        "task_ids": copy.deepcopy(plan["task_ids"]),
        "rollouts_per_task": 3,
        "rows": rows,
        "summary": distribution(rows),
    }
    validate_monitor_result(result)
    return result


def run_fixed_monitor(
    campaign: dict[str, Any], batch_map: dict[str, Any], *, skill: dict[str, str],
    backend: TGERolloutBackend, artifact_root: Path,
) -> dict[str, Any]:
    assert_split_access("selection", "monitor")
    plan = build_monitor_plan(campaign, batch_map)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", skill["skill_id"]):
        raise TGEV1RuntimeContractError("Skill ID is not path-safe.")
    result_path = artifact_root / "monitor_results" / f"{skill['skill_id']}.json"
    if result_path.is_file():
        cached = _load_json(result_path)
        try:
            validate_monitor_result(cached)
        except Exception:
            cached = None
        if cached is not None and cached.get("skill") == skill and cached.get("task_ids") == plan["task_ids"]:
            return cached
    paths = backend.run_batch(
        split="monitor", task_ids=plan["task_ids"], skill=skill, label=skill["skill_id"]
    )
    result = _monitor_result(campaign, plan, skill, paths)
    _write_json(result_path, result)
    return result


def propose_candidate(
    context: Any, *, campaign: dict[str, Any], batch_map: dict[str, Any], step: int,
    domain_contexts: dict[str, dict[str, Any]],
) -> Any:
    validate_batch_map(batch_map, campaign)
    batch_ids = batch_map["batches"][step - 1]["task_ids"]
    assert_split_access("diagnosis", "train")
    v14.validate_learner_evidence(
        context.current_batch_governed_evidence,
        batch_task_ids=batch_ids,
        protected_task_ids={
            *batch_map["monitor"]["task_ids"],
            *(f"airline:{task_id}" for task_id in batch_map["assignment"]["test"]),
        },
    )
    return v14.V14_PROPOSAL_OPERATOR.propose(
        context,
        v14.call_diagnosis,
        v14.call_governed_editor,
        domain_contexts=domain_contexts,
    )


def build_evolution_services(
    campaign: dict[str, Any], batch_map: dict[str, Any], *, artifact_root: Path
) -> EvolutionServices:
    backend = TGERolloutBackend(campaign, artifact_root=artifact_root)
    domain_contexts = load_authoritative_domain_contexts(
        _resolve(campaign["benchmark"]["tau2_root"])
    )

    def parent_rollouts(step: int, batch: dict[str, Any], skill: dict[str, str]) -> dict[str, Any]:
        paths = backend.run_batch(
            split="train",
            task_ids=batch["task_ids"],
            skill=skill,
            label=f"step_{step:02d}_parent",
        )
        rows, evidence = _rows_and_evidence(paths)
        return {"rows": rows, "evidence": evidence, "artifact_paths": [p.as_posix() for p in paths]}

    return EvolutionServices(
        parent_rollouts=parent_rollouts,
        propose=lambda context, step: propose_candidate(
            context,
            campaign=campaign,
            batch_map=batch_map,
            step=step,
            domain_contexts=domain_contexts,
        ),
        candidate_monitor=lambda skill: run_fixed_monitor(
            campaign,
            batch_map,
            skill=skill,
            backend=backend,
            artifact_root=artifact_root,
        ),
        joint_report=build_joint_distribution_report,
        gate=build_distributional_gate_decision,
    )


def build_campaign_dry_plan(
    campaign: dict[str, Any], batch_map: dict[str, Any]
) -> dict[str, Any]:
    validated = validate_batch_map(batch_map, campaign)
    hashes = validate_frozen_hashes(campaign)
    metadata = validated["metadata"]
    route_counts = {"atomic": 0, "ordering": 0, "composition": 0}
    for item in metadata.values():
        route_counts[evaluator_route(item)["compliance"]] += 1
    steps = []
    for index, batch in enumerate(batch_map["batches"], start=1):
        units = [
            {
                "task_id": task_id,
                "rollout_index": rollout_index,
                "rollout_seed": ROLLOUT_SEEDS[rollout_index - 1],
            }
            for task_id in batch["task_ids"]
            for rollout_index in range(1, 4)
        ]
        steps.append({
            "step": index,
            "batch_id": batch["batch_id"],
            "task_ids": copy.deepcopy(batch["task_ids"]),
            "family_ids": copy.deepcopy(batch["family_ids"]),
            "mechanism_ids": copy.deepcopy(batch["mechanism_ids"]),
            "roles": copy.deepcopy(batch["roles"]),
            "parent_rollout_units": units,
            "parent_trajectories": 48,
            "diagnosis_calls": 16,
            "maximum_editor_calls": 1,
        })
    return {
        "schema_version": "autonomous_gse_tge_dry_plan_0.1.0",
        "campaign_id": campaign["campaign_id"],
        "mode": "no_api_no_rollout",
        "validation": {
            "status": "PASS",
            "train_tasks": 48,
            "monitor_tasks": 20,
            "test_tasks": 48,
            "batch_sizes": [16, 16, 16],
            "batch_union_is_train": True,
            "batch_intersection_empty": True,
            "test_held_out": True,
            "test_denied_to_evolution": True,
            "test_denied_to_selection": True,
            "all_evaluator_routes_resolve": sum(route_counts.values()) == 116,
            "frozen_hashes_match": True,
            "llm_calls": 0,
            "rollouts": 0,
            "formal_run_state_created": False,
        },
        "benchmark": {"train": 48, "monitor": 20, "test": 48},
        "steps": steps,
        "monitor": {
            "tasks": 20,
            "matched_rollouts_per_task": 3,
            "trajectories_per_skill_evaluation": 60,
            "domain_strata": ["airline"],
        },
        "test": {
            "tasks": 48,
            "held_out": True,
            "accessible_during_evolution": False,
            "automatic_execution": False,
        },
        "evaluators": {
            "task_success": "TGE v1 outcome + semantic-denial adapter",
            "compliance": "deterministic atomic/ordering/composition",
            "route_counts": route_counts,
        },
        "gate": {
            **copy.deepcopy(DEFAULT_GATE_CONFIG),
            "available_domain_strata": ["airline"],
            "method_semantics_changed": False,
        },
        "estimated_rollouts": {
            "train_parent": 144,
            "monitor_per_skill_evaluation": 60,
            "candidate_monitor_worst_case_three_steps": 180,
            "candidate_current_batch_replay": 0,
            "final_test": "not executed by run/resume",
        },
        "artifact_root_default": campaign["artifact_root_default"],
        "frozen_hashes": hashes,
    }


def _runtime_lock(campaign_path: Path, campaign: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "autonomous_gse_tge_runtime_lock_0.1.0",
        "campaign_id": campaign["campaign_id"],
        "runtime_version": RUNTIME_VERSION,
        "campaign_manifest_sha256": _sha256(campaign_path),
        "frozen_hashes": validate_frozen_hashes(campaign),
        "agent": copy.deepcopy(campaign["agent"]),
        "user_simulator": copy.deepcopy(campaign["user_simulator"]),
        "distributional_gate": copy.deepcopy(campaign["distributional_gate"]),
    }


def prepare_artifact_root(
    *, mode: str, artifact_root: Path, campaign_path: Path, campaign: dict[str, Any]
) -> None:
    expected = _runtime_lock(campaign_path, campaign)
    lock_path = artifact_root / "runtime_lock.json"
    if mode == "run":
        if artifact_root.exists() and any(artifact_root.iterdir()):
            raise TGEV1RuntimeContractError("Artifact root is not empty; use resume.")
        artifact_root.mkdir(parents=True, exist_ok=True)
        _write_json(lock_path, expected)
        return
    if not lock_path.is_file() or _load_json(lock_path) != expected:
        raise TGEV1RuntimeContractError("Resume runtime/campaign/frozen hashes mismatch.")
    if not (artifact_root / "campaign_state.json").is_file():
        raise TGEV1RuntimeContractError("Resume requires campaign_state.json.")


def _campaign_files(campaign_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    campaign = _load_json(campaign_path)
    validate_campaign_contract(campaign)
    batch_map = _load_json(_resolve(campaign["evolution"]["batch_map"]))
    validate_batch_map(batch_map, campaign)
    validate_frozen_hashes(campaign)
    return campaign, batch_map


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv(REPO_ROOT / ".env", override=True)
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--campaign", type=Path, required=True)
    for command in ("run", "resume"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--campaign", type=Path, required=True)
        command_parser.add_argument("--artifact-root", type=Path)
        command_parser.add_argument("--stop-after-step", type=int, choices=(1, 2, 3))
    args = parser.parse_args(argv)
    campaign_path = args.campaign.resolve()
    campaign, batch_map = _campaign_files(campaign_path)
    if args.command == "plan":
        plan = build_campaign_dry_plan(campaign, batch_map)
        report_path = campaign_path.parent / "plan_report.json"
        _write_json(report_path, plan)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    artifact_root = (
        _resolve(campaign["artifact_root_default"])
        if args.artifact_root is None
        else args.artifact_root.resolve()
    )
    prepare_artifact_root(
        mode=args.command,
        artifact_root=artifact_root,
        campaign_path=campaign_path,
        campaign=campaign,
    )
    services = build_evolution_services(campaign, batch_map, artifact_root=artifact_root)
    result = (
        resume_campaign(
            campaign,
            batch_map,
            services,
            artifact_root=artifact_root,
            stop_after_step=args.stop_after_step,
        )
        if args.command == "resume"
        else run_campaign(
            campaign,
            batch_map,
            services,
            artifact_root=artifact_root,
            stop_after_step=args.stop_after_step,
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
