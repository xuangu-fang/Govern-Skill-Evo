#!/usr/bin/env python3
"""Run one serial E0 sanity rollout for each v3-derived Control candidate."""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


HERE = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/regression_control_gap_realization')
REPO = HERE.parents[4]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from scripts.benchmarks.v1.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from src.benchmark_v3.construction.regression_control_gap_realization.environment import register_domains  # noqa: E402
from src.benchmark_v3.construction.regression_control_gap_realization.evaluator import evaluate_airline, evaluate_retail  # noqa: E402


TASKS = HERE / "tasks.json"
SPECS = HERE / "specs.json"
SUMMARY = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/regression_control_gap_realization/e0_sanity_summary.json')
TRAJECTORIES = (Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/regression_control_gap_realization/e0/trajectories')
BASE_CONFIG = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json')
SEEDS = {"v3-gap-air-pre-01": 5311, "v3-gap-ret-pre-01": 5312}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_config(base: dict[str, Any], task: Task, seed: int) -> TextRunConfig:
    config = _config(
        base,
        {"domain": task.user_scenario.instructions.domain, "task_id": task.id},
        seed,
    )
    config.agent = "llm_agent"
    return config


def run_one(task_payload: dict[str, Any], spec: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    task = Task.model_validate(task_payload)
    seed = SEEDS[task.id]
    path = TRAJECTORIES / f"{task.id}_seed_{seed}.json"
    try:
        orchestrator = build_text_orchestrator(run_config(base, task, seed), task, seed=seed)
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        outcome = evaluate_airline(spec, final) if spec["domain"] == "airline" else evaluate_retail(spec, final)
        raw = simulation.model_dump(mode="json")
        row = {
            "label": task.id,
            "lineage": spec["lineage"],
            "seed": seed,
            "task_success": outcome["success"],
            "result": "CS" if outcome["success"] else "CF",
            "checks": outcome,
            "agent_model": base["agent"]["model"],
            "user_model": base["user_simulator"]["model"],
        }
        write(path.with_name(path.stem + "_raw.json"), raw)
        write(path.with_name(path.stem + "_final_db.json"), final)
        write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {
            "label": task.id,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        })
        raise


def main() -> int:
    tasks = load(TASKS)
    specs = {row["label"]: row for row in load(SPECS)["candidates"]}
    base = load(BASE_CONFIG)
    register_domains()
    rows = [run_one(task, specs[task["id"]], base) for task in tasks]
    passed = sum(row["task_success"] for row in rows)
    result = {
        "status": "PASS_2_V3_GAP_CONTROL_E0_SANITY" if passed == 2 else "HOLD_V3_GAP_CONTROL_E0_SANITY",
        "condition": "E0",
        "learner_enabled": False,
        "rollout_count": 2,
        "task_success_count": passed,
        "distribution": {"CS": passed, "CF": 2 - passed},
        "rows": rows,
        "formal_task_ids_allocated": 0,
    }
    write(SUMMARY, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed == 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
