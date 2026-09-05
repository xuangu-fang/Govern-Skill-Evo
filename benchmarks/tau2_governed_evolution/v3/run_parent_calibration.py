"""Run the frozen v14 Parent configuration on the 20 v3 Airline tasks."""

from __future__ import annotations

import copy
import json
import sys
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
TAU2_ROOT = REPO_ROOT / "external" / "tau2-bench"
TASKS_PATH = Path(__file__).with_name("airline_augmented_tasks.json")
OUTPUT_ROOT = Path(__file__).with_name("parent_calibration")
CAMPAIGN_PATH = (
    REPO_ROOT
    / "experiments"
    / "campaigns"
    / "autonomous_gse_v14"
    / "campaign_manifest.json"
)
SEEDS = (200, 201, 202)
sys.path.insert(0, str(REPO_ROOT))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_inputs():
    sys.path.insert(0, str((TAU2_ROOT / "src").resolve()))
    from tau2.data_model.tasks import Task

    campaign = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
    tasks = [
        Task.model_validate(item)
        for item in json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    ]
    if len(tasks) != 20 or len({task.id for task in tasks}) != 20:
        raise ValueError("V3 calibration requires exactly 20 unique tasks.")
    if Counter(task.id.split("_")[1] for task in tasks) != {
        "m1": 4,
        "m2": 4,
        "m3": 4,
        "m4": 4,
        "m5": 4,
    }:
        raise ValueError("V3 calibration requires four tasks per mechanism.")
    return campaign, tasks


def _artifact_path(task_id: str, seed: int) -> Path:
    return OUTPUT_ROOT / "trajectories" / task_id / f"seed_{seed}.json"


def _is_complete(path: Path, *, task_id: str, seed: int) -> bool:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        success = value["task_evaluation"]["success"]
        compliant = value["compliance_evaluation"]["compliant"]
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return (
        value.get("task_id") == task_id
        and value.get("rollout_seed") == seed
        and value.get("skill_version") == "S0"
        and isinstance(success, bool)
        and isinstance(compliant, bool)
    )


def _run_one(task, seed: int, campaign: dict[str, Any], domain_context: dict[str, Any]):
    from tau2.data_model.simulation import TextRunConfig
    from tau2.evaluator import evaluator_nl_assertions
    from tau2.run import run_single_task

    from src.adapters.tau2.tau3_gse_runtime import (
        _skill_environment,
        _trajectory_model_args,
        write_rollout_artifact,
    )
    from src.adapters.tau2.tau3_compliance_judge_v13 import default_judge_caller
    from src.skill_evolution.autonomous_gse_v14_benchmark_runtime import (
        _monitor_governed_evidence,
    )

    output_path = _artifact_path(task.id, seed)
    error_path = output_path.with_name(f"seed_{seed}_error.json")
    raw_path = output_path.with_name(f"seed_{seed}_tau3_raw.json")
    if _is_complete(output_path, task_id=task.id, seed=seed):
        return output_path

    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = campaign[
        "official_evaluator"
    ]["nl_assertions_model"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
        "temperature": campaign["official_evaluator"][
            "nl_assertions_temperature"
        ]
    }
    agent_args = _trajectory_model_args(
        campaign["agent"], seed, include_max_tokens=True
    )
    user_args = _trajectory_model_args(
        campaign["user_simulator"], seed, include_max_tokens=True
    )
    config = TextRunConfig(
        domain="airline",
        task_split_name=None,
        task_ids=[task.id],
        agent="llm_agent",
        user="user_simulator",
        llm_agent=campaign["agent"]["model"],
        llm_args_agent=agent_args,
        llm_user=campaign["user_simulator"]["model"],
        llm_args_user=user_args,
        max_steps=campaign["agent"]["max_steps"],
        seed=seed,
        max_retries=0,
        auto_review=False,
    )
    try:
        with _skill_environment(None):
            simulation = run_single_task(config, task, seed=seed)
        evidence = _monitor_governed_evidence(
            source_id=f"v3_parent_{task.id}_seed_{seed}",
            domain="airline",
            task=task,
            simulation=simulation,
            domain_context=domain_context,
            judge_caller=default_judge_caller,
        )
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write_rollout_artifact(
            output_path,
            domain="airline",
            task_id=task.id,
            phase="parent_calibration",
            skill_version="S0",
            rollout_index=SEEDS.index(seed) + 1,
            rollout_seed=seed,
            governed_evidence=evidence,
            provenance={
                "campaign_id": campaign["campaign_id"],
                "task_pool": TASKS_PATH.relative_to(REPO_ROOT).as_posix(),
                "skill_id": "S0",
                "skill_path": campaign["initial_parent"]["path"],
                "agent_config": copy.deepcopy(campaign["agent"]),
                "user_simulator_config": copy.deepcopy(campaign["user_simulator"]),
                "official_evaluator_config": copy.deepcopy(
                    campaign["official_evaluator"]
                ),
                "judge_config": copy.deepcopy(campaign["compliance_judge"]),
                "raw_tau3_result_path": raw_path.relative_to(REPO_ROOT).as_posix(),
            },
        )
        error_path.unlink(missing_ok=True)
        return output_path
    except Exception as error:
        _write_json(
            error_path,
            {
                "task_id": task.id,
                "rollout_seed": seed,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        raise


def _write_rollup(paths: list[Path], errors: list[dict[str, Any]], campaign):
    quadrant = {
        "compliant_success": "CS",
        "compliant_failure": "CF",
        "violating_success": "VS",
        "violating_failure": "VF",
    }
    rows = []
    for path in sorted(paths):
        value = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "task_id": value["task_id"],
                "mechanism": value["task_id"].split("_")[1].upper(),
                "seed": value["rollout_seed"],
                "task_success": value["task_evaluation"]["success"],
                "compliant": value["compliance_evaluation"]["compliant"],
                "quadrant": quadrant[value["state"]],
                "termination_reason": value["task_evaluation"]["termination_reason"],
                "judge_violations": value["compliance_evaluation"]["violations"],
                "trajectory_path": path.relative_to(REPO_ROOT).as_posix(),
            }
        )
    results_path = OUTPUT_ROOT / "rollout_results.jsonl"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    counts = Counter(row["quadrant"] for row in rows)
    _write_json(
        OUTPUT_ROOT / "parent_calibration_summary.json",
        {
            "run_configuration": {
                "task_count": 20,
                "seeds": list(SEEDS),
                "rollouts_per_task": 3,
                "planned_rollouts": 60,
                "parent_skill": campaign["initial_parent"],
                "agent": campaign["agent"],
                "user_simulator": campaign["user_simulator"],
                "official_evaluator": campaign["official_evaluator"],
                "compliance_judge": campaign["compliance_judge"],
            },
            "valid_rollouts": len(rows),
            "runtime_errors": errors,
            "task_success": sum(row["task_success"] for row in rows),
            "compliant": sum(row["compliant"] for row in rows),
            "quadrants": {key: counts[key] for key in ("CS", "CF", "VS", "VF")},
        },
    )


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    campaign, tasks = _load_inputs()
    from src.skill_evolution.autonomous_gse_v14_benchmark_runtime import (
        load_authoritative_domain_contexts,
        validate_campaign_contract,
    )

    validate_campaign_contract(campaign)
    domain_context = load_authoritative_domain_contexts(TAU2_ROOT)["airline"]
    units = [(task, seed) for task in tasks for seed in SEEDS]
    paths: list[Path] = []
    errors: list[dict[str, Any]] = []
    with ThreadPoolExecutor(
        max_workers=campaign["execution"]["max_concurrency"]
    ) as executor:
        futures = {
            executor.submit(_run_one, task, seed, campaign, domain_context): (
                task.id,
                seed,
            )
            for task, seed in units
        }
        for future in as_completed(futures):
            task_id, seed = futures[future]
            try:
                paths.append(future.result())
                print(f"PASS {task_id} seed={seed}", flush=True)
            except Exception as error:
                errors.append(
                    {
                        "task_id": task_id,
                        "seed": seed,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                )
                print(f"ERROR {task_id} seed={seed}: {error}", flush=True)
    _write_rollup(paths, errors, campaign)
    return 0 if len(paths) == 60 and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
