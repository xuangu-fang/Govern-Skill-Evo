#!/usr/bin/env python3
"""Run matched Empty/Reference P3 Trigger-only Necessity rollouts."""

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
P3 = HERE.parent
REPO = HERE.parents[6]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.retail_unified_pending_mutation_gate0.environment import DOMAIN_NAME, register_domain  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.retail_unified_pending_mutation_gate0.p3_resource_refresh.evaluator import evaluate  # noqa: E402


BASE_CONFIG = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
TRAJECTORIES = HERE / "trajectories"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_config(base: dict[str, Any], label: str, seed: int, condition: dict[str, Any]) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": label}, seed)
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {**config.llm_args_agent, "manual_skill_path": str((HERE / condition["skill_path"]).resolve())}
    return config


def calls(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    return [call for message in simulation.get("messages", []) if message.get("role") == "assistant" for call in (message.get("tool_calls") or [])]


def first_user_leak(simulation: dict[str, Any]) -> bool:
    text = next((str(message.get("content") or "").lower() for message in simulation.get("messages", []) if message.get("role") == "user"), "")
    return any(phrase in text for phrase in ("refresh", "re-read", "do the cancellation first", "change the payment first", "balance will", "refund will make"))


def focal_failure(spec: dict[str, Any], final_db: dict[str, Any], simulation: dict[str, Any]) -> dict[str, Any]:
    source = final_db["orders"][spec["source_order_id"]]
    downstream = final_db["orders"][spec["downstream_order_id"]]
    gift = final_db["users"][spec["user_id"]]["payment_methods"][spec["gift_card_id"]]
    if spec["kind"] == "cancel_then_payment":
        upstream_done = source["status"] == "cancelled"
        downstream_done = any(row["transaction_type"] == "payment" and row["payment_method_id"] == spec["gift_card_id"] for row in downstream["payment_history"][1:])
    else:
        upstream_done = any(row["transaction_type"] == "payment" and row["payment_method_id"] == spec["source_new_payment_id"] for row in source["payment_history"][1:])
        downstream_done = any(item["item_id"] == spec["downstream_new_item_id"] for item in downstream["items"])
    observed = [call["name"] for call in calls(simulation) if call.get("arguments", {}).get("order_id") in {spec["source_order_id"], spec["downstream_order_id"]}]
    focal = upstream_done and not downstream_done and gift["balance"] == spec["initial_balance"] + spec["refund_amount"]
    return {"mode": "FOCAL_STALE_RESOURCE_NO_DOWNSTREAM" if focal else "OTHER_INCOMPLETE_FINAL_STATE", "upstream_done": upstream_done, "downstream_done": downstream_done, "final_gift_balance": gift["balance"], "observed_target_calls": observed}


def path(condition: str, label: str, seed: int) -> Path:
    return TRAJECTORIES / condition / f"{label}_seed_{seed}.json"


def run_one(condition_id: str, condition: dict[str, Any], task: Task, spec: dict[str, Any], seed: int, base: dict[str, Any], contract: str) -> dict[str, Any]:
    result_path = path(condition_id, str(task.id), seed)
    raw_path = result_path.with_name(result_path.stem + "_raw.json")
    final_path = result_path.with_name(result_path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(run_config(base, str(task.id), seed, condition), task, seed=seed)
        simulation = orchestrator.run()
        simulation_json = simulation.model_dump(mode="json")
        final_db = orchestrator.environment.tools.db.model_dump(mode="json")
        outcome = evaluate(spec, final_db)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final_db)
        row = {
            "contract_version": contract, "condition": condition_id, "construction_label": str(task.id), "seed": seed,
            "success": bool(outcome["success"]), "evaluation": outcome,
            "failure_attribution": None if outcome["success"] else focal_failure(spec, final_db, simulation_json),
            "first_user_mapping_leak": first_user_leak(simulation_json),
            "raw_path": str(raw_path.resolve()), "final_db_path": str(final_path.resolve()),
        }
        write(result_path, row)
        return row
    except Exception as error:
        write(result_path.with_name(result_path.stem + "_error.json"), {"condition": condition_id, "construction_label": str(task.id), "seed": seed, "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(HERE / "config.json")
    base = load(BASE_CONFIG)
    tasks = {str(row["id"]): Task.model_validate(row) for row in load(HERE / "tasks.json")}
    specs = {row["construction_label"]: row for row in load(P3 / "specs.json")["triggers"]}
    assert set(tasks) == set(specs)
    register_domain()
    jobs = [(condition_id, config["conditions"][condition_id], tasks[label], specs[label], seed, base, config["contract_version"]) for label in sorted(tasks) for condition_id in ("E0", "ER") for seed in config["seeds"]]
    assert len(jobs) == config["planned_trajectories"]
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["construction_label"], row["condition"], row["seed"]))
    counts = {condition: {"successes": sum(row["success"] for row in rows if row["condition"] == condition), "rollouts": sum(row["condition"] == condition for row in rows)} for condition in ("E0", "ER")}
    e0_failures = [row for row in rows if row["condition"] == "E0" and not row["success"]]
    focal = sum(row["failure_attribution"]["mode"] == "FOCAL_STALE_RESOURCE_NO_DOWNSTREAM" for row in e0_failures)
    leaks = sum(row["first_user_mapping_leak"] for row in rows)
    passed = focal >= config["e0_focal_min"] and counts["ER"]["successes"] == config["er_success_required"] and leaks == 0
    summary = {
        "status": "COMPLETE",
        "verdict": "PASS_P3_GATE_1_TRIGGER_NECESSITY" if passed else "HOLD_P3_GATE_1_TRIGGER_NECESSITY",
        "family_id": "C-RET-P3-RESOURCE-REFRESH", "contract_version": config["contract_version"],
        "formal_task_ids_allocated": 0, "support_rollouts": 0, "trajectory_count": len(rows),
        "by_condition": counts,
        "e0_failure_attribution": {"total_failures": len(e0_failures), "focal_failures": focal, "counts": dict(Counter(row["failure_attribution"]["mode"] for row in e0_failures))},
        "first_user_mapping_leaks": leaks,
        "rows": [{key: row[key] for key in ("construction_label", "condition", "seed", "success", "failure_attribution", "first_user_mapping_leak")} for row in rows],
    }
    write(HERE / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
