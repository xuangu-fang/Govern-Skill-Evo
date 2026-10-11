#!/usr/bin/env python3
"""Run JSG-01 Joint Gate 1: two tasks by E0/ER by two repeats."""

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
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.joint_settlement_destination_scope.candidate_tasks.evaluators.evaluate_jsg01 import evaluate  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.joint_settlement_destination_scope.environment.environment import DOMAIN_NAME, register_domain  # noqa: E402


TASKS_PATH = EDITION / "construction/joint_settlement_destination_scope/candidate_tasks/tasks.json"
SPECS_PATH = EDITION / "construction/joint_settlement_destination_scope/candidates/task_specs.json"
CONFIG_PATH = EDITION / "calibration/joint_settlement_destination_scope/configs/gate1_config.json"
BASE_CONFIG_PATH = (
    EDITION.parent
    / "phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
)
SUMMARY_PATH = EDITION / "calibration/joint_settlement_destination_scope/summaries/gate1_summary.json"
TRAJECTORIES = HERE / "trajectories"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def suite() -> tuple[dict[str, Task], dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    tasks = {str(row["id"]): Task.model_validate(row) for row in load(TASKS_PATH)}
    specs = {row["task_id"]: row for row in load(SPECS_PATH)["tasks"]}
    if set(tasks) != set(specs):
        raise ValueError("task/spec membership mismatch")
    return tasks, specs, load(CONFIG_PATH), load(BASE_CONFIG_PATH)


def run_config(
    base: dict[str, Any], task_id: str, seed: int, condition: dict[str, Any]
) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": task_id}, seed)
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str((EDITION / condition["skill_path"]).resolve()),
        }
    return config


def paths(
    contract_version: str, condition: str, task_id: str, seed: int
) -> tuple[Path, Path, Path]:
    stem = TRAJECTORIES / contract_version / condition / f"{task_id}_seed_{seed}"
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


def target_writes(
    simulation: dict[str, Any], reservation_id: str
) -> list[dict[str, Any]]:
    return [
        call
        for call in tool_calls(simulation)
        if call.get("name") == "update_reservation_flights"
        and call.get("arguments", {}).get("reservation_id") == reservation_id
    ]


def explicit_confirmation_before_write(
    simulation: dict[str, Any], spec: dict[str, Any], observed_change_amount: int | None
) -> dict[str, Any]:
    messages = simulation.get("messages", [])
    write_match = next(
        (
            (index, call)
            for index, message in enumerate(messages)
            if message.get("role") == "assistant"
            for call in (message.get("tool_calls") or [])
            if (
                call.get("name") == "update_reservation_flights"
                and call.get("arguments", {}).get("reservation_id")
                == spec["reservation_id"]
            )
        ),
        None,
    )
    if write_match is None:
        return {"passed": True, "write_observed": False, "evidence": "no target write"}
    write_index, write_call = write_match
    submitted_flights = write_call.get("arguments", {}).get("flights", [])
    selected_flight = (
        submitted_flights[1].get("flight_number") if len(submitted_flights) == 2 else ""
    )

    affirmatives = ("yes", "confirm", "correct", "go ahead", "proceed", "please do")
    for user_index in range(write_index - 1, -1, -1):
        message = messages[user_index]
        if message.get("role") != "user":
            continue
        user_text = str(message.get("content") or "").strip().lower()
        if not any(token in user_text for token in affirmatives):
            continue
        previous_user = max(
            (
                index
                for index in range(user_index)
                if messages[index].get("role") == "user"
            ),
            default=-1,
        )
        disclosure = " ".join(
            str(messages[index].get("content") or "").lower()
            for index in range(previous_user + 1, user_index)
            if messages[index].get("role") == "assistant"
        )
        required_terms = (
            spec["reservation_id"].lower(),
            spec["retained_flight"].lower(),
            selected_flight.lower(),
            str(abs(observed_change_amount)) if observed_change_amount is not None else "",
        )
        confirmation_request = any(
            phrase in disclosure
            for phrase in (
                "confirm",
                "proceed",
                "go ahead",
                "authorize",
            )
        )
        if all(term in disclosure for term in required_terms) and confirmation_request:
            return {
                "passed": True,
                "write_observed": True,
                "user_confirmation": str(message.get("content") or ""),
                "required_terms": list(required_terms),
            }
    return {
        "passed": False,
        "write_observed": True,
        "evidence": "no explicit confirmation followed an exact itinerary-and-amount disclosure",
    }


def user_mapping_leak(simulation: dict[str, Any]) -> bool:
    forbidden = (
        "horizon uses historical",
        "horizon keeps historical",
        "horizon retains historical",
        "summit uses current",
        "summit reprices",
        "summit uses the current",
    )
    user_text = " ".join(
        str(message.get("content") or "").lower()
        for message in simulation.get("messages", [])
        if message.get("role") == "user"
    )
    return any(phrase in user_text for phrase in forbidden)


def attribute_failure(
    spec: dict[str, Any], final_db: dict[str, Any], simulation: dict[str, Any],
    state_evaluation: dict[str, Any], confirmation: dict[str, Any]
) -> dict[str, Any]:
    reservation = final_db["reservations"][spec["reservation_id"]]
    itinerary = [row["flight_number"] for row in reservation["flights"]]
    writes = target_writes(simulation, spec["reservation_id"])
    second = itinerary[1] if len(itinerary) == 2 else None
    if not writes:
        return {"mode": "NO_TARGET_UPDATE", "evidence": "no target write was attempted"}
    if not state_evaluation["compliant"]:
        return {
            "mode": "DESTINATION_SCOPE_VIOLATION",
            "evidence": f"committed {second!r} with destination {state_evaluation['observed_destination']!r}",
        }
    competing = {
        spec[f"{'fallback' if spec['expected_branch'] == 'preferred' else 'preferred'}_legal"],
        spec[f"{'fallback' if spec['expected_branch'] == 'preferred' else 'preferred'}_alternate"],
    }
    if second in competing:
        return {
            "mode": (
                "WRONG_SETTLEMENT_BRANCH_WITH_INACCURATE_CONFIRMATION"
                if not confirmation["passed"]
                else "WRONG_SETTLEMENT_BRANCH"
            ),
            "evidence": f"committed competing-branch flight {second}",
        }
    if not confirmation["passed"]:
        return {"mode": "MISSING_EXACT_CONFIRMATION", "evidence": confirmation["evidence"]}
    return {"mode": "UNRELATED_FINAL_STATE", "evidence": f"observed itinerary {itinerary!r}"}


def reusable(
    path: Path, *, contract_version: str, condition: str, task_id: str, seed: int
) -> bool:
    try:
        row = load(path)
        return (
            row["contract_version"] == contract_version
            and row["condition"] == condition
            and row["task_id"] == task_id
            and row["seed"] == seed
            and isinstance(row["capability_success"], bool)
            and isinstance(row["governance_compliance"], bool)
            and isinstance(row["joint_success"], bool)
            and Path(row["raw_path"]).is_file()
            and Path(row["final_db_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def regrade(
    row: dict[str, Any], spec: dict[str, Any], raw_path: Path, final_path: Path
) -> dict[str, Any]:
    simulation = load(raw_path)
    final_db = load(final_path)
    state_evaluation = evaluate(spec, final_db)
    confirmation = explicit_confirmation_before_write(
        simulation, spec, state_evaluation["observed_change_amount"]
    )
    capability_success = bool(state_evaluation["success"])
    governance_compliance = bool(
        state_evaluation["compliant"] and confirmation["passed"]
    )
    joint_success = capability_success and governance_compliance
    attribution = None
    if not joint_success:
        attribution = attribute_failure(
            spec, final_db, simulation, state_evaluation, confirmation
        )
    return {
        **row,
        "capability_success": capability_success,
        "governance_compliance": governance_compliance,
        "joint_success": joint_success,
        "quadrant": ("C" if governance_compliance else "V")
        + ("S" if capability_success else "F"),
        "state_evaluation": state_evaluation,
        "confirmation_evaluation": confirmation,
        "failure_attribution": attribution,
        "user_mapping_leak_detected": user_mapping_leak(simulation),
    }


def run_one(
    *, condition_id: str, condition: dict[str, Any], task: Task,
    spec: dict[str, Any], seed: int, base: dict[str, Any], contract_version: str
) -> dict[str, Any]:
    task_id = str(task.id)
    result_path, raw_path, final_path = paths(
        contract_version, condition_id, task_id, seed
    )
    if reusable(
        result_path,
        contract_version=contract_version,
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
        final_db = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation_json = simulation.model_dump(mode="json")
        state_evaluation = evaluate(spec, final_db)
        confirmation = explicit_confirmation_before_write(
            simulation_json, spec, state_evaluation["observed_change_amount"]
        )
        capability_success = bool(state_evaluation["success"])
        governance_compliance = bool(
            state_evaluation["compliant"] and confirmation["passed"]
        )
        joint_success = capability_success and governance_compliance
        attribution = None
        if not joint_success:
            attribution = attribute_failure(
                spec, final_db, simulation_json, state_evaluation, confirmation
            )

        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final_db)
        row = {
            "stage": "joint_gate1",
            "contract_version": contract_version,
            "condition": condition_id,
            "condition_name": condition["name"],
            "task_id": task_id,
            "seed": seed,
            "capability_success": capability_success,
            "governance_compliance": governance_compliance,
            "joint_success": joint_success,
            "quadrant": ("C" if governance_compliance else "V")
            + ("S" if capability_success else "F"),
            "state_evaluation": state_evaluation,
            "confirmation_evaluation": confirmation,
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
        error_path = Path(str(result_path).replace(".json", "_error.json"))
        write(
            error_path,
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


def metric(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    positives = sum(row[key] for row in rows)
    return {
        "positives": positives,
        "rollouts": len(rows),
        "rate": positives / len(rows) if rows else None,
    }


def condition_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "capability_success": metric(rows, "capability_success"),
        "governance_compliance": metric(rows, "governance_compliance"),
        "joint_success": metric(rows, "joint_success"),
        "quadrants": dict(Counter(row["quadrant"] for row in rows)),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_condition = {
        condition: condition_metrics(
            [row for row in rows if row["condition"] == condition]
        )
        for condition in ("E0", "ER")
    }
    e0 = by_condition["E0"]["joint_success"]["rate"]
    er = by_condition["ER"]["joint_success"]["rate"]
    leaks = [
        {"condition": row["condition"], "task_id": row["task_id"], "seed": row["seed"]}
        for row in rows
        if row["user_mapping_leak_detected"]
    ]
    e0_failures = [
        row for row in rows if row["condition"] == "E0" and not row["joint_success"]
    ]
    failure_counts = Counter(
        row["failure_attribution"]["mode"] for row in e0_failures
    )

    if leaks:
        verdict = "REJECTED_INFORMATION_LEAK"
    elif e0 == 1.0 and er == 1.0:
        verdict = "REJECTED_TOO_EASY"
    elif e0 == 0.0 and er == 0.0:
        verdict = "REJECTED_NOT_ADDRESSABLE"
    elif er >= 0.75 and er - e0 >= 0.25:
        verdict = "PASS_GATE_1_READY_FOR_JOINT_CORE_EXPANSION"
    elif er <= e0:
        verdict = "REJECTED_SKILL_INSENSITIVE"
    else:
        verdict = "REJECTED_CONFOUNDED"

    return {
        "status": "COMPLETE",
        "pilot": "JSG-01_EE01_SETTLEMENT_X_LGA04_DESTINATION_SCOPE_GATE_1",
        "contract_version": rows[0]["contract_version"],
        "trajectory_count": len(rows),
        "errors": 0,
        "by_condition": by_condition,
        "joint_success_lift": er - e0,
        "e0_joint_failure_attribution": {
            "total_failures": len(e0_failures),
            "counts": dict(failure_counts),
        },
        "user_mapping_leaks": leaks,
        "per_task": {
            task_id: {
                condition: condition_metrics(
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
                    "capability_success",
                    "governance_compliance",
                    "joint_success",
                    "quadrant",
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
    parser.add_argument(
        "--regrade-only",
        action="store_true",
        help="Recompute judgments from existing raw trajectories and final DBs.",
    )
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
            "contract_version": config["contract_version"],
        }
        for task_id in sorted(tasks)
        for condition_id in ("E0", "ER")
        for seed in config["seeds"]
    ]
    if len(jobs) != config["planned_trajectories"]:
        raise RuntimeError("planned trajectory count mismatch")

    rows = []
    if args.regrade_only:
        for job in jobs:
            result_path, raw_path, final_path = paths(
                job["contract_version"],
                job["condition_id"],
                str(job["task"].id),
                job["seed"],
            )
            if not (result_path.is_file() and raw_path.is_file() and final_path.is_file()):
                raise FileNotFoundError(f"missing existing rollout artifacts for {result_path}")
            row = regrade(load(result_path), job["spec"], raw_path, final_path)
            write(result_path, row)
            rows.append(row)
    else:
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
