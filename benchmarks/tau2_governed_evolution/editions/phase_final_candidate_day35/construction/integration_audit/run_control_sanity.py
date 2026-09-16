#!/usr/bin/env python3
"""Run one fresh E0 rollout per formal Protected Control."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
EDITION = HERE.parents[1]
REPO = EDITION.parents[3]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.environment import register_domains  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_final_candidate_day35.construction.integration_audit.control_evaluator import evaluate  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402


TASKS = EDITION / "benchmark/control_tasks.json"
SUMMARY = HERE / "control_e0_sanity_summary.json"
TRAJECTORIES = HERE / "control_e0/trajectories"
BASE_CONFIG = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
SEED = 5211


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_config(base: dict[str, Any], task: Task) -> TextRunConfig:
    config = _config(base, {"domain": task.user_scenario.instructions.domain, "task_id": task.id}, SEED)
    config.agent = "llm_agent"
    return config


def run_one(task_payload: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    task = Task.model_validate(task_payload)
    path = TRAJECTORIES / f"{task.id}_seed_{SEED}.json"
    try:
        orchestrator = build_text_orchestrator(run_config(base, task), task, seed=SEED)
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        outcome = evaluate(task.id, initial, final)
        raw = simulation.model_dump(mode="json")
        first_user = next((str(row.get("content") or "") for row in raw.get("messages", []) if row.get("role") == "user"), "")
        row = {
            "task_id": task.id,
            "seed": SEED,
            "task_success": outcome["success"],
            "label": "CS" if outcome["success"] else "CF",
            "checks": outcome["checks"],
            "first_user_present": bool(first_user.strip()),
            "agent_model": base["agent"]["model"],
            "user_model": base["user_simulator"]["model"],
        }
        write(path.with_name(path.stem + "_raw.json"), raw)
        write(path.with_name(path.stem + "_final_db.json"), final)
        write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {"task_id": task.id, "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--task-id", action="append", dest="task_ids")
    args = parser.parse_args()
    all_tasks = load(TASKS)
    requested = set(args.task_ids or [])
    known = {task["id"] for task in all_tasks}
    unknown = requested - known
    if unknown:
        parser.error(f"unknown task ids: {sorted(unknown)}")
    tasks = [task for task in all_tasks if not requested or task["id"] in requested]
    base = load(BASE_CONFIG)
    register_domains()
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, task, base) for task in tasks]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(tasks)}), flush=True)
    if requested:
        # Preserve already-valid one-rollout results for untouched controls.
        rows = [
            load(TRAJECTORIES / f"{task['id']}_seed_{SEED}.json")
            for task in all_tasks
        ]
    rows.sort(key=lambda row: row["task_id"])
    passed = sum(row["task_success"] for row in rows)
    total = len(rows)
    result = {
        "status": "PASS_9_CONTROL_E0_SANITY" if passed == 9 else "HOLD_CONTROL_E0_SANITY",
        "condition": "E0",
        "learner_enabled": False,
        "seed": SEED,
        "rollout_count": total,
        "task_success_count": passed,
        "distribution": {"CS": passed, "CF": total - passed},
        "rows": rows,
    }
    write(SUMMARY, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed == 9 else 1


if __name__ == "__main__":
    raise SystemExit(main())
