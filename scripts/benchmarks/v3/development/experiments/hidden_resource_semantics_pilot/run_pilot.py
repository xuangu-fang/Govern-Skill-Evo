#!/usr/bin/env python3
"""Run smoke, matched calibration, and analysis for Hidden Resource Semantics."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


HERE = ((Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_v3_day34/experiments/hidden_resource_semantics_pilot'))
EDITION = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')
REPO = EDITION.parents[3]
TAU2 = REPO / "external/tau2-bench"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(TAU2 / "src"))
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from scripts.benchmarks.v1.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from src.benchmark_v3.development.hidden_resource_semantics.candidate_tasks.evaluators.evaluate_hidden_resource import FAILURE_MODES, attribute_failure, evaluate_success, summarize_failures


TASKS_PATH = EDITION / "construction/hidden_resource_semantics/candidate_tasks/tasks.json"
SPECS_PATH = EDITION / "construction/hidden_resource_semantics/candidates/task_specs.json"
CONFIG_PATH = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/hidden_resource_semantics/configs/rollout_config.json')
BASE_CONFIG_PATH = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json')
SUMMARY_DIR = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/hidden_resource_semantics/summaries')
TRAJECTORIES = (Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_v3_day34/experiments/hidden_resource_semantics_pilot/trajectories')


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def suite() -> tuple[dict[str, Task], dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    tasks = {str(row["id"]): Task.model_validate(row) for row in load(TASKS_PATH)}
    specs = {row["task_id"]: row for row in load(SPECS_PATH)["tasks"]}
    if set(tasks) != set(specs):
        raise ValueError("task/spec membership mismatch")
    return tasks, specs, load(CONFIG_PATH), load(BASE_CONFIG_PATH)


def agent_visible_policy(config: dict[str, Any]) -> str:
    patch = load(EDITION / config["agent_visible_policy_patch"])
    native = (REPO / patch["base_policy"]).read_text(encoding="utf-8")
    statement = patch["remove_exactly_once"]
    if native.count(statement) != 1:
        raise ValueError("expected exactly one certificate remainder statement in native policy")
    return native.replace(statement, "")


def run_config(base: dict[str, Any], task_id: str, seed: int, condition: dict[str, Any]) -> TextRunConfig:
    config = _config(base, {"domain": "airline", "task_id": task_id}, seed)
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str((EDITION / condition["skill_path"]).resolve()),
        }
    return config


def paths(stage: str, condition_id: str, task_id: str, seed: int) -> tuple[Path, Path, Path]:
    stem = TRAJECTORIES / stage / condition_id / f"{task_id}_seed_{seed}"
    return Path(str(stem) + ".json"), Path(str(stem) + "_raw.json"), Path(str(stem) + "_final_db.json")


def reusable(path: Path, *, stage: str, condition_id: str, task_id: str, seed: int) -> bool:
    try:
        row = load(path)
        return (
            row["stage"] == stage and row["condition"] == condition_id
            and row["task_id"] == task_id and row["seed"] == seed
            and isinstance(row["success"], bool)
            and Path(row["raw_path"]).is_file() and Path(row["final_db_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(
    *, stage: str, condition_id: str, condition: dict[str, Any], task: Task,
    spec: dict[str, Any], seed: int, base: dict[str, Any], visible_policy: str,
) -> dict[str, Any]:
    task_id = str(task.id)
    result_path, raw_path, final_path = paths(stage, condition_id, task_id, seed)
    if reusable(result_path, stage=stage, condition_id=condition_id, task_id=task_id, seed=seed):
        return load(result_path)
    try:
        orchestrator = build_text_orchestrator(run_config(base, task_id, seed, condition), task, seed=seed)
        orchestrator.agent.domain_policy = visible_policy
        orchestrator.environment.policy = visible_policy
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final)
        evaluation = evaluate_success(spec, initial, final)
        attribution = None if evaluation["success"] else attribute_failure(
            spec, initial, final, simulation.model_dump(mode="json")
        )
        row = {
            "stage": stage, "condition": condition_id, "condition_name": condition["name"],
            "task_id": task_id, "role": spec["role"], "seed": seed,
            "success": bool(evaluation["success"]), "success_evaluation": evaluation,
            "failure_attribution": attribution,
            "raw_path": str(raw_path.resolve()), "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"], "user_model": base["user_simulator"]["model"],
            "agent_settings": {key: base["agent"][key] for key in ("temperature", "thinking", "reasoning_effort", "max_tokens", "max_steps")},
            "agent_visible_rule_removed": True,
        }
        write(result_path, row)
        return row
    except Exception as error:
        error_path = Path(str(result_path).replace(".json", "_error.json"))
        write(error_path, {
            "stage": stage, "condition": condition_id, "task_id": task_id, "seed": seed,
            "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc(),
        })
        raise


def run_jobs(stage: str, condition_ids: list[str], seeds: list[int], workers: int) -> list[dict[str, Any]]:
    tasks, specs, config, base = suite()
    visible_policy = agent_visible_policy(config)
    jobs = [
        {"stage": stage, "condition_id": condition_id, "condition": config["conditions"][condition_id],
         "task": tasks[task_id], "spec": specs[task_id], "seed": seed, "base": base,
         "visible_policy": visible_policy}
        for task_id in sorted(tasks) for condition_id in condition_ids for seed in seeds
    ]
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_one, **job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"stage": stage, "completed": len(rows), "planned": len(jobs)}), flush=True)
    return sorted(rows, key=lambda row: (row["task_id"], row["condition"], row["seed"]))


def rate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successes = sum(row["success"] for row in rows)
    return {"successes": successes, "rollouts": len(rows), "rate": successes / len(rows) if rows else None}


def attribution_matrix(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = {}
    for role in ("CAPABILITY_CORE", "PROTECTED_CONTROL", "HELD_OUT_TRANSFER", "OVERALL"):
        role_rows = rows if role == "OVERALL" else [row for row in rows if row["role"] == role]
        matrix[role] = {}
        for condition in ("E0", "ER", "EI"):
            selected = [row for row in role_rows if row["condition"] == condition]
            failures = [row for row in selected if not row["success"]]
            counts = Counter(row["failure_attribution"]["mode"] for row in failures)
            matrix[role][condition] = {
                "failures": len(failures),
                "rollouts": len(selected),
                "counts": {mode: counts.get(mode, 0) for mode in FAILURE_MODES},
            }
    return matrix


def analyze(rows: list[dict[str, Any]]) -> dict[str, Any]:
    roles = ("CAPABILITY_CORE", "PROTECTED_CONTROL", "HELD_OUT_TRANSFER", "OVERALL")
    metrics = {}
    for role in roles:
        selected = rows if role == "OVERALL" else [row for row in rows if row["role"] == role]
        metrics[role] = {
            condition: rate([row for row in selected if row["condition"] == condition])
            for condition in ("E0", "ER", "EI")
        }
    core = metrics["CAPABILITY_CORE"]
    controls = metrics["PROTECTED_CONTROL"]
    held = metrics["HELD_OUT_TRANSFER"]
    overall = metrics["OVERALL"]
    lifts = {
        "core_relevant": core["ER"]["rate"] - core["E0"]["rate"],
        "core_irrelevant": core["EI"]["rate"] - core["E0"]["rate"],
        "core_specificity_gap": core["ER"]["rate"] - core["EI"]["rate"],
        "held_out_relevant": held["ER"]["rate"] - held["E0"]["rate"],
        "control_regression": controls["ER"]["rate"] - controls["E0"]["rate"],
        "overall_relevant": overall["ER"]["rate"] - overall["E0"]["rate"],
        "overall_specificity_gap": overall["ER"]["rate"] - overall["EI"]["rate"],
    }
    per_task = {
        task_id: {
            condition: rate([row for row in rows if row["task_id"] == task_id and row["condition"] == condition])
            for condition in ("E0", "ER", "EI")
        }
        for task_id in sorted({row["task_id"] for row in rows})
    }
    failures = summarize_failures(rows)
    attribution = attribution_matrix(rows)
    focal_fraction = failures["dominant_failure_fraction"] or 0.0
    if core["E0"]["rate"] > 0.70:
        verdict = "FAIL_TOO_EASY"
    elif lifts["control_regression"] < -0.15:
        verdict = "FAIL_OVERGENERALIZATION"
    elif lifts["core_relevant"] < 0.20:
        verdict = "FAIL_SKILL_INSENSITIVE"
    elif lifts["core_irrelevant"] > 0 and abs(lifts["core_relevant"] - lifts["core_irrelevant"]) < 0.15:
        verdict = "FAIL_GENERIC_PLANNING_EFFECT"
    elif lifts["held_out_relevant"] <= 0:
        verdict = "PARTIAL — Skill-sensitive but weak transfer"
    elif lifts["core_specificity_gap"] >= 0.15 and focal_fraction >= 0.50:
        verdict = "PASS — Experience-grounded skill gap observed"
    else:
        verdict = "FAIL_NOT_ADDRESSABLE"
    return {
        "pilot": "HIDDEN_SINGLE_USE_RESOURCE_SEMANTICS", "trajectory_count": len(rows),
        "metrics": metrics, "lifts": lifts, "per_task": per_task,
        "failure_attribution": attribution, "failure_consistency": failures, "verdict": verdict,
    }


def load_stage(stage: str) -> list[dict[str, Any]]:
    paths = sorted((TRAJECTORIES / stage).glob("*/*.json"))
    return [load(path) for path in paths if not path.name.endswith(("_raw.json", "_final_db.json", "_error.json"))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "calibration", "analyze", "all"), default="all")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    _, _, config, _ = suite()
    if args.stage in {"smoke", "all"}:
        rows = run_jobs("smoke", ["E0", "ER"], [config["smoke_seed"]], args.workers)
        summary = {
            "status": "COMPLETE", "trajectory_count": len(rows), "errors": 0,
            "by_condition": {condition: rate([row for row in rows if row["condition"] == condition]) for condition in ("E0", "ER")},
            "by_role": {role: {condition: rate([row for row in rows if row["role"] == role and row["condition"] == condition]) for condition in ("E0", "ER")} for role in ("CAPABILITY_CORE", "PROTECTED_CONTROL", "HELD_OUT_TRANSFER")},
            "rows": [{key: row[key] for key in ("task_id", "role", "condition", "seed", "success", "failure_attribution")} for row in rows],
        }
        write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/hidden_resource_semantics/summaries/smoke_summary.json'), summary)
        if len(rows) != config["planned_smoke_trajectories"]:
            raise RuntimeError("smoke trajectory count mismatch")
    if args.stage in {"calibration", "all"}:
        rows = run_jobs("calibration", ["E0", "ER", "EI"], config["calibration_seeds"], args.workers)
        if len(rows) != config["planned_calibration_trajectories"]:
            raise RuntimeError("calibration trajectory count mismatch")
        summary = analyze(rows)
        write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/hidden_resource_semantics/summaries/calibration_summary.json'), summary)
        write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/hidden_resource_semantics/summaries/failure_attribution.json'), summary["failure_attribution"])
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.stage == "analyze":
        rows = load_stage("calibration")
        if len(rows) != config["planned_calibration_trajectories"]:
            raise RuntimeError(f"expected {config['planned_calibration_trajectories']} rows, found {len(rows)}")
        summary = analyze(rows)
        write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/hidden_resource_semantics/summaries/calibration_summary.json'), summary)
        write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/hidden_resource_semantics/summaries/failure_attribution.json'), summary["failure_attribution"])
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
