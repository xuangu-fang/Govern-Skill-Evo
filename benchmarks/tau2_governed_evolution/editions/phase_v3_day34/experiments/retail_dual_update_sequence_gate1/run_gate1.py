#!/usr/bin/env python3
"""Run the eight-rollout RDS-01 E0/ER Skill Necessity Smoke."""

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


HERE = Path(__file__).resolve().parent
EDITION = HERE.parents[1]
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_dual_update_sequence.candidate_tasks.evaluators.evaluate_rds01 import evaluate_success  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_dual_update_sequence.environment.environment import DOMAIN_NAME, register_domain  # noqa: E402


TASKS_PATH = EDITION / "construction/retail_dual_update_sequence/candidate_tasks/tasks.json"
SPECS_PATH = EDITION / "construction/retail_dual_update_sequence/candidates/task_specs.json"
CONFIG_PATH = EDITION / "calibration/retail_dual_update_sequence/configs/gate1_config.json"
BASE_CONFIG_PATH = EDITION.parent / "phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
SUMMARY_PATH = EDITION / "calibration/retail_dual_update_sequence/summaries/gate1_summary.json"
TRAJECTORIES = HERE / "trajectories"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def suite() -> tuple[
    dict[str, Task], dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]
]:
    tasks = {str(row["id"]): Task.model_validate(row) for row in load(TASKS_PATH)}
    specs = {row["task_id"]: row for row in load(SPECS_PATH)["tasks"]}
    if set(tasks) != set(specs):
        raise ValueError("task/spec membership mismatch")
    return tasks, specs, load(CONFIG_PATH), load(BASE_CONFIG_PATH)


def run_config(
    base: dict[str, Any],
    task_id: str,
    seed: int,
    condition: dict[str, Any],
) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": task_id}, seed)
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str(
                (EDITION / condition["skill_path"]).resolve()
            ),
        }
    return config


def paths(
    contract: str, condition: str, task_id: str, seed: int
) -> tuple[Path, Path, Path]:
    stem = TRAJECTORIES / contract / condition / f"{task_id}_seed_{seed}"
    return (
        Path(str(stem) + ".json"),
        Path(str(stem) + "_raw.json"),
        Path(str(stem) + "_final_db.json"),
    )


def tool_calls(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        call
        for message in simulation.get("messages", [])
        if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
    ]


def user_mapping_leak(simulation: dict[str, Any]) -> bool:
    forbidden = (
        "r1 requires address",
        "r1 is address first",
        "r1 means address first",
        "r2 requires payment",
        "r2 is payment first",
        "r2 means payment first",
    )
    user_text = " ".join(
        str(message.get("content") or "").lower()
        for message in simulation.get("messages", [])
        if message.get("role") == "user"
    )
    return any(phrase in user_text for phrase in forbidden)


def attribute_failure(
    spec: dict[str, Any],
    final_db: dict[str, Any],
    simulation: dict[str, Any],
) -> dict[str, Any]:
    contract = final_db["dual_update_contracts"][spec["order_id"]]
    writes = [
        call
        for call in tool_calls(simulation)
        if call.get("name")
        in {"modify_pending_order_address", "modify_pending_order_payment"}
        and call.get("arguments", {}).get("order_id") == spec["order_id"]
    ]
    if (
        contract["workflow_locked"]
        and contract["completed_updates"] == [spec["wrong_first_update"]]
    ):
        return {
            "mode": "WRONG_UPDATE_SEQUENCE",
            "evidence": (
                f"committed {spec['wrong_first_update']} first under "
                f"{spec['workflow_revision']} and locked the remaining goal"
            ),
        }
    if not writes:
        return {
            "mode": "NO_TARGET_UPDATES",
            "evidence": "no target address or payment write was attempted",
        }
    if len(contract["completed_updates"]) < 2:
        return {
            "mode": "INCOMPLETE_UPDATE_SEQUENCE",
            "evidence": f"completed only {contract['completed_updates']}",
        }
    return {
        "mode": "UNRELATED_FINAL_STATE",
        "evidence": f"observed updates {contract['completed_updates']}",
    }


def reusable(
    path: Path, *, contract: str, condition: str, task_id: str, seed: int
) -> bool:
    try:
        row = load(path)
        return (
            row["contract_version"] == contract
            and row["condition"] == condition
            and row["task_id"] == task_id
            and row["seed"] == seed
            and isinstance(row["success"], bool)
            and Path(row["raw_path"]).is_file()
            and Path(row["final_db_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(
    *,
    condition_id: str,
    condition: dict[str, Any],
    task: Task,
    spec: dict[str, Any],
    seed: int,
    base: dict[str, Any],
    contract: str,
) -> dict[str, Any]:
    task_id = str(task.id)
    result_path, raw_path, final_path = paths(
        contract, condition_id, task_id, seed
    )
    if reusable(
        result_path,
        contract=contract,
        condition=condition_id,
        task_id=task_id,
        seed=seed,
    ):
        return load(result_path)
    try:
        orchestrator = build_text_orchestrator(
            run_config(base, task_id, seed, condition), task, seed=seed
        )
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation_json = simulation.model_dump(mode="json")
        evaluation = evaluate_success(spec, final)
        attribution = (
            None
            if evaluation["success"]
            else attribute_failure(spec, final, simulation_json)
        )
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(
            simulation.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        write(final_path, final)
        row = {
            "stage": "gate1",
            "contract_version": contract,
            "condition": condition_id,
            "condition_name": condition["name"],
            "task_id": task_id,
            "seed": seed,
            "success": bool(evaluation["success"]),
            "success_evaluation": evaluation,
            "failure_attribution": attribution,
            "user_mapping_leak_detected": user_mapping_leak(simulation_json),
            "raw_path": str(raw_path.resolve()),
            "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"],
            "user_model": base["user_simulator"]["model"],
        }
        write(result_path, row)
        return row
    except Exception as error:
        write(
            Path(str(result_path).replace(".json", "_error.json")),
            {
                "condition": condition_id,
                "task_id": task_id,
                "seed": seed,
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        raise


def rate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successes = sum(row["success"] for row in rows)
    return {
        "successes": successes,
        "rollouts": len(rows),
        "rate": successes / len(rows) if rows else None,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_condition = {
        condition: rate([row for row in rows if row["condition"] == condition])
        for condition in ("E0", "ER")
    }
    e0 = by_condition["E0"]["rate"]
    er = by_condition["ER"]["rate"]
    e0_failures = [
        row for row in rows if row["condition"] == "E0" and not row["success"]
    ]
    failure_counts = Counter(
        row["failure_attribution"]["mode"] for row in e0_failures
    )
    focal = failure_counts.get("WRONG_UPDATE_SEQUENCE", 0)
    focal_fraction = focal / len(e0_failures) if e0_failures else None
    leaks = [
        {
            "condition": row["condition"],
            "task_id": row["task_id"],
            "seed": row["seed"],
        }
        for row in rows
        if row["user_mapping_leak_detected"]
    ]
    if leaks:
        verdict = "REJECTED_INFORMATION_LEAK"
    elif e0 == 1.0 and er == 1.0:
        verdict = "REJECTED_TOO_EASY"
    elif e0 == 0.0 and er == 0.0:
        verdict = "REJECTED_NOT_ADDRESSABLE"
    elif er >= 0.75 and er - e0 >= 0.25 and (focal_fraction or 0.0) >= 0.5:
        verdict = "PASS_GATE_1_READY_FOR_CORE_EXPANSION"
    elif er <= e0:
        verdict = "REJECTED_SKILL_INSENSITIVE"
    else:
        verdict = "REJECTED_CONFOUNDED"
    return {
        "status": "COMPLETE",
        "pilot": "RDS-01_REVISION_CONDITIONED_DUAL_UPDATE_SEQUENCE_GATE_1",
        "contract_version": rows[0]["contract_version"],
        "trajectory_count": len(rows),
        "errors": 0,
        "by_condition": by_condition,
        "relevant_lift": er - e0,
        "e0_failure_attribution": {
            "total_failures": len(e0_failures),
            "counts": dict(failure_counts),
            "focal_fraction": focal_fraction,
        },
        "user_mapping_leaks": leaks,
        "per_task": {
            task_id: {
                condition: rate(
                    [
                        row
                        for row in rows
                        if row["task_id"] == task_id
                        and row["condition"] == condition
                    ]
                )
                for condition in ("E0", "ER")
            }
            for task_id in sorted({row["task_id"] for row in rows})
        },
        "rows": [
            {
                key: row[key]
                for key in (
                    "task_id",
                    "condition",
                    "seed",
                    "success",
                    "failure_attribution",
                    "user_mapping_leak_detected",
                )
            }
            for row in rows
        ],
        "verdict": verdict,
        "formal_tasks_admitted": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    tasks, specs, config, base = suite()
    register_domain()
    jobs = [
        {
            "condition_id": condition_id,
            "condition": config["conditions"][condition_id],
            "task": tasks[task_id],
            "spec": specs[task_id],
            "seed": seed,
            "base": base,
            "contract": config["contract_version"],
        }
        for task_id in sorted(tasks)
        for condition_id in ("E0", "ER")
        for seed in config["seeds"]
    ]
    if len(jobs) != config["planned_trajectories"]:
        raise RuntimeError("planned trajectory count mismatch")
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, **job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(
                json.dumps({"completed": len(rows), "planned": len(jobs)}),
                flush=True,
            )
    rows.sort(key=lambda row: (row["task_id"], row["condition"], row["seed"]))
    summary = summarize(rows)
    write(SUMMARY_PATH, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
