"""Run the frozen v14 Parent calibration on the 25 v3 novel-policy tasks."""

from __future__ import annotations

import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[4]
TAU2_ROOT = REPO_ROOT / "external" / "tau2-bench"
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
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _load_inputs():
    from benchmarks.tau2_governed_evolution.v3.novel_policy.runtime import get_tasks

    campaign = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
    tasks = get_tasks()
    if len(tasks) != 25 or len({task.id for task in tasks}) != 25:
        raise ValueError("Novel-policy calibration requires 25 unique tasks.")
    if Counter(task.id.split("_")[1] for task in tasks) != {
        "np1": 5,
        "np3": 5,
        "np4": 5,
        "np5": 5,
        "np7": 5,
    }:
        raise ValueError("Novel-policy calibration requires five tasks per policy.")
    notes = [task.description.notes or "" for task in tasks]
    if sum("TARGET" in note for note in notes) != 20 or sum(
        "POSITIVE_BOUNDARY" in note for note in notes
    ) != 5:
        raise ValueError("Novel-policy calibration requires 20 targets and 5 boundaries.")
    return campaign, tasks


def _configure_frozen_airline_environment() -> None:
    from benchmarks.tau2_governed_evolution.v3.novel_policy.runtime import get_environment
    from tau2.registry import registry

    # The runner and official evaluator both resolve the environment here. Replacing
    # only this process-local constructor gives both the complete v3 policy while
    # retaining the original tools, DB, task initialization, and evaluator behavior.
    registry._domains["airline"] = get_environment


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
        notes = value["provenance"]["task_notes"]
        rows.append(
            {
                "task_id": value["task_id"],
                "policy_id": value["task_id"].split("_")[1].upper().removeprefix("N"),
                "role": "POSITIVE_BOUNDARY" if "POSITIVE_BOUNDARY" in notes else "TARGET",
                "seed": value["rollout_seed"],
                "success": value["task_evaluation"]["success"],
                "compliance": value["compliance_evaluation"]["compliant"],
                "quadrant": quadrant[value["state"]],
                "trajectory_path": path.relative_to(REPO_ROOT).as_posix(),
                "runtime_error": None,
                "judge_violations": value["compliance_evaluation"]["violations"],
                "mechanism_related_issue": None,
                "mechanism_label": None,
                "mechanism_recurrent_after_review": None,
                "primary_failure_attribution": None,
            }
        )
    for error in sorted(errors, key=lambda item: (item["task_id"], item["seed"])):
        task_id = error["task_id"]
        rows.append(
            {
                "task_id": task_id,
                "policy_id": task_id.split("_")[1].upper().removeprefix("N"),
                "role": "POSITIVE_BOUNDARY" if "_05_" in task_id else "TARGET",
                "seed": error["seed"],
                "success": None,
                "compliance": None,
                "quadrant": None,
                "trajectory_path": None,
                "runtime_error": {
                    "error_type": error["error_type"],
                    "error_message": error["error_message"],
                },
                "judge_violations": None,
                "mechanism_related_issue": None,
                "mechanism_label": None,
                "mechanism_recurrent_after_review": None,
                "primary_failure_attribution": "ENVIRONMENT / RUNTIME",
            }
        )
    results_path = OUTPUT_ROOT / "rollout_results.jsonl"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    counts = Counter(row["quadrant"] for row in rows)
    valid_rows = [row for row in rows if row["quadrant"] is not None]
    per_policy = {}
    for policy_id in ("P1", "P3", "P4", "P5", "P7"):
        selected = [
            row
            for row in rows
            if row["policy_id"] == policy_id and row["quadrant"] is not None
        ]
        policy_counts = Counter(row["quadrant"] for row in selected)
        per_policy[policy_id] = {
            "tasks": len({row["task_id"] for row in selected}),
            "rollouts": len(selected),
            "success": sum(row["success"] for row in selected),
            "compliant": sum(row["compliance"] for row in selected),
            **{key: policy_counts[key] for key in ("CS", "CF", "VS", "VF")},
        }
    _write_json(
        OUTPUT_ROOT / "parent_calibration_summary.json",
        {
            "run_configuration": {
                "task_count": 25,
                "seeds": list(SEEDS),
                "rollouts_per_task": 3,
                "planned_rollouts": 75,
                "policy": "benchmarks/tau2_governed_evolution/v3/novel_policy/airline_policy_v3.md",
                "parent_skill": campaign["initial_parent"],
                "agent": campaign["agent"],
                "user_simulator": campaign["user_simulator"],
                "official_evaluator": campaign["official_evaluator"],
                "compliance_judge": campaign["compliance_judge"],
            },
            "valid_rollouts": len(valid_rows),
            "runtime_errors": errors,
            "task_success": sum(row["success"] for row in rows if row["success"] is not None),
            "compliant": sum(
                row["compliance"] for row in rows if row["compliance"] is not None
            ),
            "quadrants": {key: counts[key] for key in ("CS", "CF", "VS", "VF")},
            "per_policy": per_policy,
        },
    )


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    campaign, tasks = _load_inputs()
    _configure_frozen_airline_environment()

    from benchmarks.tau2_governed_evolution.v3 import run_parent_calibration as base
    from benchmarks.tau2_governed_evolution.v3.novel_policy.runtime import POLICY_PATH, TASKS_PATH
    from src.skill_evolution.autonomous_gse_v14_benchmark_runtime import (
        load_authoritative_domain_contexts,
        validate_campaign_contract,
    )

    validate_campaign_contract(campaign)
    base.TASKS_PATH = TASKS_PATH
    base.OUTPUT_ROOT = OUTPUT_ROOT
    domain_context = load_authoritative_domain_contexts(TAU2_ROOT)["airline"]
    domain_context["original_domain_policy"] = POLICY_PATH.read_text(encoding="utf-8")
    units = [(task, seed) for task in tasks for seed in SEEDS]
    paths: list[Path] = []
    errors: list[dict[str, Any]] = []
    with ThreadPoolExecutor(
        max_workers=campaign["execution"]["max_concurrency"]
    ) as executor:
        futures = {
            executor.submit(base._run_one, task, seed, campaign, domain_context): (
                task.id,
                seed,
            )
            for task, seed in units
        }
        for future in as_completed(futures):
            task_id, seed = futures[future]
            try:
                path = future.result()
                value = json.loads(path.read_text(encoding="utf-8"))
                value["provenance"]["task_notes"] = next(
                    task.description.notes for task in tasks if task.id == task_id
                )
                _write_json(path, value)
                paths.append(path)
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
    return 0 if len(paths) == 75 and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
