#!/usr/bin/env python3
"""Run the eight-rollout matched P1 Trigger-only Necessity experiment."""

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
CONSTRUCTION = HERE.parent
REPO = HERE.parents[5]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.retail_unified_pending_mutation_gate0.environment import DOMAIN_NAME, register_domain  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.retail_unified_pending_mutation_gate0.evaluator import evaluate  # noqa: E402


BASE_CONFIG = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
TRAJECTORIES = HERE / "trajectories"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_config(
    base: dict[str, Any], label: str, seed: int, condition: dict[str, Any]
) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": label}, seed)
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str((HERE / condition["skill_path"]).resolve()),
        }
    return config


def tool_calls(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        call
        for message in simulation.get("messages", [])
        if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
    ]


def mapping_leak(simulation: dict[str, Any]) -> bool:
    user_text = " ".join(
        str(message.get("content") or "").lower()
        for message in simulation.get("messages", [])
        if message.get("role") == "user"
    )
    forbidden = (
        "payment before item",
        "payment first",
        "item change last",
        "items last",
        "change the card first",
    )
    return any(phrase in user_text for phrase in forbidden)


def attribution(spec: dict[str, Any], final_db: dict[str, Any], simulation: dict[str, Any]) -> dict[str, Any]:
    order = final_db["orders"][spec["order_id"]]
    target_writes = [
        call["name"]
        for call in tool_calls(simulation)
        if call.get("arguments", {}).get("order_id") == spec["order_id"]
        and call.get("name", "").startswith("modify_pending_order_")
    ]
    item_index = target_writes.index("modify_pending_order_items") if "modify_pending_order_items" in target_writes else None
    payment_index = target_writes.index("modify_pending_order_payment") if "modify_pending_order_payment" in target_writes else None
    has_new_item = any(item["item_id"] == spec["new_item_id"] for item in order["items"])
    has_new_whole_payment = any(
        row["transaction_type"] == "payment"
        and row["payment_method_id"] == spec["new_payment_id"]
        and row["amount"] == order["payment_history"][0]["amount"]
        for row in order["payment_history"][1:]
    )
    if has_new_item and not has_new_whole_payment and (
        payment_index is None or (item_index is not None and item_index < payment_index)
    ):
        mode = "FOCAL_ITEMS_BEFORE_PAYMENT"
    elif not target_writes:
        mode = "NO_TARGET_WRITES"
    else:
        mode = "OTHER_INCOMPLETE_FINAL_STATE"
    return {"mode": mode, "observed_target_writes": target_writes}


def paths(condition: str, label: str, seed: int) -> tuple[Path, Path, Path]:
    stem = TRAJECTORIES / condition / f"{label}_seed_{seed}"
    return Path(str(stem) + ".json"), Path(str(stem) + "_raw.json"), Path(str(stem) + "_final_db.json")


def run_one(
    condition_id: str,
    condition: dict[str, Any],
    task: Task,
    spec: dict[str, Any],
    seed: int,
    base: dict[str, Any],
    contract: str,
) -> dict[str, Any]:
    label = str(task.id)
    result_path, raw_path, final_path = paths(condition_id, label, seed)
    try:
        orchestrator = build_text_orchestrator(
            run_config(base, label, seed, condition), task, seed=seed
        )
        simulation = orchestrator.run()
        simulation_json = simulation.model_dump(mode="json")
        final_db = orchestrator.environment.tools.db.model_dump(mode="json")
        outcome = evaluate(spec, final_db)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final_db)
        row = {
            "contract_version": contract,
            "condition": condition_id,
            "construction_label": label,
            "seed": seed,
            "success": bool(outcome["success"]),
            "evaluation": outcome,
            "failure_attribution": None if outcome["success"] else attribution(spec, final_db, simulation_json),
            "user_mapping_leak_detected": mapping_leak(simulation_json),
            "raw_path": str(raw_path.resolve()),
            "final_db_path": str(final_path.resolve()),
        }
        write(result_path, row)
        return row
    except Exception as error:
        write(
            Path(str(result_path).replace(".json", "_error.json")),
            {"condition": condition_id, "construction_label": label, "seed": seed, "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()},
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(HERE / "config.json")
    base = load(BASE_CONFIG)
    tasks = {str(row["id"]): Task.model_validate(row) for row in load(HERE / "tasks.json")}
    specs = {row["construction_label"]: row for row in load(CONSTRUCTION / "specs.json")["triggers"]}
    assert set(tasks) == set(specs)
    register_domain()
    jobs = [
        (condition_id, config["conditions"][condition_id], tasks[label], specs[label], seed, base, config["contract_version"])
        for label in sorted(tasks)
        for condition_id in ("E0", "ER")
        for seed in config["seeds"]
    ]
    assert len(jobs) == config["planned_trajectories"]
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["construction_label"], row["condition"], row["seed"]))
    condition_counts = {
        condition: {
            "successes": sum(row["success"] for row in rows if row["condition"] == condition),
            "rollouts": sum(row["condition"] == condition for row in rows),
        }
        for condition in ("E0", "ER")
    }
    e0_failures = [row for row in rows if row["condition"] == "E0" and not row["success"]]
    focal = sum(row["failure_attribution"]["mode"] == "FOCAL_ITEMS_BEFORE_PAYMENT" for row in e0_failures)
    leaks = sum(row["user_mapping_leak_detected"] for row in rows)
    passed = condition_counts["E0"]["successes"] <= 1 and focal >= 3 and condition_counts["ER"]["successes"] == 4 and leaks == 0
    summary = {
        "status": "COMPLETE",
        "verdict": "PASS_GATE_1_TRIGGER_NECESSITY" if passed else "HOLD_GATE_1_TRIGGER_NECESSITY",
        "family_id": "C-RET-P1-PENDING-MUTATION-SEQUENCE",
        "contract_version": config["contract_version"],
        "formal_task_ids_allocated": 0,
        "support_rollouts": 0,
        "trajectory_count": len(rows),
        "by_condition": condition_counts,
        "e0_failure_attribution": {"total_failures": len(e0_failures), "focal_failures": focal, "counts": dict(Counter(row["failure_attribution"]["mode"] for row in e0_failures))},
        "user_mapping_leaks": leaks,
        "rows": [{key: row[key] for key in ("construction_label", "condition", "seed", "success", "failure_attribution", "user_mapping_leak_detected")} for row in rows],
    }
    write(HERE / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
