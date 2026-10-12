#!/usr/bin/env python3
"""Run PB-C02 smoke and matched three-condition calibration."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


HERE = ((Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_v3_day34/experiments/primitive_b_pb_c02_pilot'))
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
from src.benchmark_v3.development.primitive_b.pb_c02.candidate_tasks.evaluators.evaluate_pb_c02 import FAILURE_MODES, attribute_failure, evaluate_success


TASKS_PATH = EDITION / "construction/primitive_b/pb_c02/candidate_tasks/tasks.json"
SPECS_PATH = EDITION / "construction/primitive_b/pb_c02/candidates/task_specs.json"
CONFIG_PATH = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/primitive_b/pb_c02/configs/rollout_config.json')
BASE_CONFIG_PATH = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json')
SUMMARY_DIR = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/primitive_b/pb_c02/summaries')
TRAJECTORIES = (Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_v3_day34/experiments/primitive_b_pb_c02_pilot/trajectories')


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


def run_config(
    base: dict[str, Any], task_id: str, seed: int, condition: dict[str, Any]
) -> TextRunConfig:
    config = _config(base, {"domain": "airline", "task_id": task_id}, seed)
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str((EDITION / condition["skill_path"]).resolve()),
        }
    return config


def paths(stage: str, condition_id: str, task_id: str, seed: int) -> tuple[Path, Path, Path]:
    root = TRAJECTORIES / stage / condition_id
    stem = root / f"{task_id}_seed_{seed}"
    return Path(str(stem) + ".json"), Path(str(stem) + "_raw.json"), Path(str(stem) + "_final_db.json")


def reusable(path: Path, *, stage: str, condition_id: str, task_id: str, seed: int) -> bool:
    try:
        row = load(path)
        return (
            row["stage"] == stage
            and row["condition"] == condition_id
            and row["task_id"] == task_id
            and row["seed"] == seed
            and isinstance(row["success"], bool)
            and Path(row["raw_path"]).is_file()
            and Path(row["final_db_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(
    *, stage: str, condition_id: str, condition: dict[str, Any], task: Task,
    spec: dict[str, Any], seed: int, base: dict[str, Any]
) -> dict[str, Any]:
    task_id = str(task.id)
    result_path, raw_path, final_path = paths(stage, condition_id, task_id, seed)
    if reusable(result_path, stage=stage, condition_id=condition_id, task_id=task_id, seed=seed):
        return load(result_path)
    try:
        orchestrator = build_text_orchestrator(
            run_config(base, task_id, seed, condition), task, seed=seed
        )
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final)
        evaluation = evaluate_success(spec, initial, final)
        attribution = None if evaluation["success"] else attribute_failure(
            spec, initial, simulation.model_dump(mode="json")
        )
        row = {
            "stage": stage,
            "condition": condition_id,
            "condition_name": condition["name"],
            "task_id": task_id,
            "split": spec["split"],
            "seed": seed,
            "success": bool(evaluation["success"]),
            "success_evaluation": evaluation,
            "failure_attribution": attribution,
            "raw_path": str(raw_path.resolve()),
            "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"],
            "user_model": base["user_simulator"]["model"],
            "agent_settings": {
                key: base["agent"][key]
                for key in ("temperature", "thinking", "reasoning_effort", "max_tokens", "max_steps")
            },
        }
        write(result_path, row)
        return row
    except Exception as error:
        error_path = Path(str(result_path).replace(".json", "_error.json"))
        write(error_path, {
            "stage": stage, "condition": condition_id, "task_id": task_id,
            "seed": seed, "error_type": type(error).__name__, "error": str(error),
            "traceback": traceback.format_exc(),
        })
        raise


def run_jobs(stage: str, condition_ids: list[str], seeds: list[int], workers: int) -> list[dict[str, Any]]:
    tasks, specs, config, base = suite()
    jobs = [
        {
            "stage": stage,
            "condition_id": condition_id,
            "condition": config["conditions"][condition_id],
            "task": tasks[task_id],
            "spec": specs[task_id],
            "seed": seed,
            "base": base,
        }
        for task_id in sorted(tasks)
        for condition_id in condition_ids
        for seed in seeds
    ]
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_one, **job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"stage": stage, "completed": len(rows), "planned": len(jobs)}), flush=True)
    return sorted(rows, key=lambda row: (row["task_id"], row["condition"], row["seed"]))


def rate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "successes": sum(row["success"] for row in rows),
        "rollouts": len(rows),
        "rate": sum(row["success"] for row in rows) / len(rows) if rows else None,
    }


def analyze(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for split in ("train_like", "held_out", "overall"):
        metrics[split] = {}
        selected = rows if split == "overall" else [row for row in rows if row["split"] == split]
        for condition in ("E0", "ER", "EI"):
            metrics[split][condition] = rate([row for row in selected if row["condition"] == condition])
    s0 = metrics["overall"]["E0"]["rate"]
    sr = metrics["overall"]["ER"]["rate"]
    si = metrics["overall"]["EI"]["rate"]
    lifts = {
        "relevant": sr - s0,
        "irrelevant": si - s0,
        "specificity_gap": sr - si,
        "held_out_relevant": metrics["held_out"]["ER"]["rate"] - metrics["held_out"]["E0"]["rate"],
    }
    per_task = {}
    for task_id in sorted({row["task_id"] for row in rows}):
        per_task[task_id] = {
            condition: rate([row for row in rows if row["task_id"] == task_id and row["condition"] == condition])
            for condition in ("E0", "ER", "EI")
        }
    failures = [row for row in rows if row["condition"] == "E0" and not row["success"]]
    counts = Counter(row["failure_attribution"]["mode"] for row in failures)
    for mode in FAILURE_MODES:
        counts.setdefault(mode, 0)
    dominant_mode, dominant_count = counts.most_common(1)[0] if failures else (None, 0)
    failure_consistency = {
        "empty_total_failures": len(failures),
        "counts": dict(counts),
        "dominant_failure_mode": dominant_mode,
        "dominant_failure_count": dominant_count,
        "dominant_failure_fraction": dominant_count / len(failures) if failures else None,
    }
    if s0 > 0.75:
        verdict = "FAIL_TOO_EASY"
    elif lifts["specificity_gap"] < 0.15 and lifts["irrelevant"] > 0 and abs(lifts["relevant"] - lifts["irrelevant"]) < 0.15:
        verdict = "FAIL_GENERIC_PROMPT_EFFECT"
    elif lifts["relevant"] < 0.20:
        verdict = "FAIL_SKILL_INSENSITIVE"
    elif failures and failure_consistency["dominant_failure_fraction"] < 0.50:
        verdict = "FAIL_INCONSISTENT_FAILURE"
    elif sr >= 0.75 and lifts["specificity_gap"] >= 0.15 and lifts["held_out_relevant"] > 0:
        verdict = "PASS — Skill-addressable and transferable"
    else:
        verdict = "PARTIAL — Skill-addressable but weak transfer"
    return {
        "pilot": "PB-C02_ORIGINAL_FILTER_RANK_FALLBACK",
        "trajectory_count": len(rows),
        "metrics": metrics,
        "lifts": lifts,
        "per_task": per_task,
        "failure_consistency": failure_consistency,
        "verdict": verdict,
        "screening_reference": {
            "empty_range": [0.30, 0.75], "relevant_min": 0.75,
            "relevant_lift_min": 0.20, "specificity_gap_min": 0.15,
            "held_out_relevant_lift_positive": True,
        },
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
        smoke = run_jobs("smoke", ["E0", "ER"], [config["smoke_seed"]], args.workers)
        smoke_summary = {
            "status": "COMPLETE",
            "trajectory_count": len(smoke),
            "errors": 0,
            "by_condition": {condition: rate([row for row in smoke if row["condition"] == condition]) for condition in ("E0", "ER")},
            "rows": [{key: row[key] for key in ("task_id", "split", "condition", "seed", "success", "failure_attribution")} for row in smoke],
        }
        write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/primitive_b/pb_c02/summaries/smoke_summary.json'), smoke_summary)
        if len(smoke) != config["planned_smoke_trajectories"]:
            raise RuntimeError("smoke trajectory count mismatch")
    if args.stage in {"calibration", "all"}:
        rows = run_jobs("calibration", ["E0", "ER", "EI"], config["calibration_seeds"], args.workers)
        if len(rows) != config["planned_calibration_trajectories"]:
            raise RuntimeError("calibration trajectory count mismatch")
        summary = analyze(rows)
        write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/primitive_b/pb_c02/summaries/calibration_summary.json'), summary)
        write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/primitive_b/pb_c02/summaries/failure_attribution.json'), summary["failure_consistency"])
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.stage == "analyze":
        rows = load_stage("calibration")
        if len(rows) != config["planned_calibration_trajectories"]:
            raise RuntimeError(f"expected {config['planned_calibration_trajectories']} stored calibration rows, found {len(rows)}")
        summary = analyze(rows)
        write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/primitive_b/pb_c02/summaries/calibration_summary.json'), summary)
        write((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/calibration/primitive_b/pb_c02/summaries/failure_attribution.json'), summary["failure_consistency"])
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
