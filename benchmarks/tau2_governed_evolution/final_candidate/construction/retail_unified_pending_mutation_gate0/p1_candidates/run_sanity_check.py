#!/usr/bin/env python3
"""Run one Empty-Skill rollout for each pre-ID P1 trigger candidate."""

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
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.retail_unified_pending_mutation_gate0.environment import DOMAIN_NAME, register_domain  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.retail_unified_pending_mutation_gate0.evaluator import evaluate  # noqa: E402


CONFIG = HERE / "sanity_config.json"
SPECS = HERE / "specs.json"
INPUTS = HERE / "candidate_inputs.json"
SUMMARY = HERE / "sanity_summary.json"
TRAJECTORIES = HERE / "sanity/trajectories"
BASE_CONFIG = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_task(spec: dict[str, Any], reason: str) -> Task:
    return Task.model_validate({
        "id": spec["label"],
        "description": {
            "purpose": "Construction-only P1 pre-ID sanity input.",
            "relevant_policies": "Native Retail policy and common unified Retail extensions.",
            "notes": "The construction label is not a benchmark task ID.",
        },
        "user_scenario": {
            "persona": "A customer with a complete stable final-state request who does not prescribe workflow order.",
            "instructions": {
                "domain": DOMAIN_NAME,
                "reason_for_call": reason,
                "known_info": (
                    f"Every requested change is required and stable. The target payment method ID is "
                    f"{spec['new_payment_id']}."
                ),
                "unknown_info": "You do not know the backend mutation dependencies and must not choose a workflow order for the agent.",
                "task_instructions": (
                    "State the complete request naturally in the first turn. Do not add, remove, or revise a goal. "
                    "Do not prescribe tool order or say which change should happen first or last. Confirm the exact "
                    "complete proposal when asked. Never reveal, infer, confirm, deny, or hint at an internal mutation "
                    "sequence. Remain until every requested change is reported complete or the agent cannot continue."
                ),
            },
        },
    })


def run_config(base: dict[str, Any], label: str, seed: int, condition: dict[str, Any]) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": label}, seed)
    config.agent = condition["agent"]
    return config


def tool_calls(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        call
        for message in simulation.get("messages", [])
        if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
    ]


def first_user_mapping_leak(simulation: dict[str, Any]) -> bool:
    first_user = next(
        (str(message.get("content") or "").lower() for message in simulation.get("messages", []) if message.get("role") == "user"),
        "",
    )
    forbidden = ("payment first", "items first", "item change last", "payment before item", "items before payment")
    return any(phrase in first_user for phrase in forbidden)


def attribution(spec: dict[str, Any], final_db: dict[str, Any], simulation: dict[str, Any]) -> dict[str, Any]:
    order = final_db["orders"][spec["order_id"]]
    writes = [
        call["name"]
        for call in tool_calls(simulation)
        if call.get("arguments", {}).get("order_id") == spec["order_id"]
        and call.get("name", "").startswith("modify_pending_order_")
    ]
    item_index = writes.index("modify_pending_order_items") if "modify_pending_order_items" in writes else None
    payment_index = writes.index("modify_pending_order_payment") if "modify_pending_order_payment" in writes else None
    item_committed = any(item["item_id"] == spec["new_item_id"] for item in order["items"])
    whole_payment_committed = any(
        row["transaction_type"] == "payment"
        and row["payment_method_id"] == spec["new_payment_id"]
        and row["amount"] == order["payment_history"][0]["amount"]
        for row in order["payment_history"][1:]
    )
    focal = item_committed and not whole_payment_committed and (
        payment_index is None or (item_index is not None and item_index < payment_index)
    )
    return {
        "mode": "FOCAL_ITEMS_BEFORE_PAYMENT" if focal else "OTHER_INCOMPLETE_FINAL_STATE",
        "observed_target_writes": writes,
    }


def result_path(label: str, seed: int) -> Path:
    return TRAJECTORIES / "E0" / f"{label}_seed_{seed}.json"


def reusable(path: Path, label: str, seed: int) -> bool:
    try:
        row = load(path)
        return (
            row["construction_label"] == label and row["seed"] == seed
            and isinstance(row["success"], bool) and Path(row["raw_path"]).is_file()
            and Path(row["final_db_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(spec: dict[str, Any], reason: str, condition: dict[str, Any], seed: int, base: dict[str, Any]) -> dict[str, Any]:
    path = result_path(spec["label"], seed)
    if reusable(path, spec["label"], seed):
        return load(path)
    raw_path = path.with_name(path.stem + "_raw.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(
            run_config(base, spec["label"], seed, condition), build_task(spec, reason), seed=seed
        )
        simulation = orchestrator.run()
        simulation_json = simulation.model_dump(mode="json")
        final_db = orchestrator.environment.tools.db.model_dump(mode="json")
        outcome = evaluate(spec, final_db)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final_db)
        row = {
            "construction_label": spec["label"],
            "request_relation": spec["request_relation"],
            "condition": "E0",
            "seed": seed,
            "success": bool(outcome["success"]),
            "evaluation": outcome,
            "failure_attribution": None if outcome["success"] else attribution(spec, final_db, simulation_json),
            "first_user_mapping_leak": first_user_mapping_leak(simulation_json),
            "raw_path": str(raw_path.resolve()),
            "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"],
            "user_model": base["user_simulator"]["model"],
        }
        write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {
            "construction_label": spec["label"], "condition": "E0", "seed": seed,
            "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc(),
        })
        raise


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    focal = sum(
        not row["success"]
        and row["failure_attribution"] is not None
        and row["failure_attribution"]["mode"] == "FOCAL_ITEMS_BEFORE_PAYMENT"
        for row in rows
    )
    leaks = sum(row["first_user_mapping_leak"] for row in rows)
    successes = sum(row["success"] for row in rows)
    review = [
        row["construction_label"]
        for row in rows
        if row["success"] or row["failure_attribution"]["mode"] != "FOCAL_ITEMS_BEFORE_PAYMENT"
    ]
    passed = len(rows) == 8 and focal >= 5 and leaks == 0
    return {
        "status": "PASS_P1_PURE_SURFACE_PRE_ID_SANITY_CHECK" if passed else "HOLD_P1_PURE_SURFACE_PRE_ID_SANITY_CHECK",
        "family_id": "C-RET-P1-PENDING-MUTATION-SEQUENCE",
        "workspace_status": "CONSTRUCTION_ONLY_NOT_AN_EDITION",
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "sanity_rollouts": len(rows),
        "predeclared_criteria": {
            "focal_failures_at_least_5_of_8": focal >= 5,
            "no_first_user_mapping_leaks": leaks == 0,
        },
        "counts": {"focal_failures": focal, "successes": successes, "other_failures": len(rows) - focal - successes},
        "by_request_relation": {
            relation: {
                "rollouts": sum(row["request_relation"] == relation for row in rows),
                "focal_failures": sum(
                    row["request_relation"] == relation and not row["success"]
                    and row["failure_attribution"]["mode"] == "FOCAL_ITEMS_BEFORE_PAYMENT"
                    for row in rows
                ),
                "successes": sum(row["request_relation"] == relation and row["success"] for row in rows),
            }
            for relation in ("item_before_payment", "payment_before_item")
        },
        "first_user_mapping_leaks": leaks,
        "candidates_requiring_review": review,
        "rows": [
            {key: row[key] for key in ("construction_label", "request_relation", "condition", "seed", "success", "failure_attribution", "first_user_mapping_leak")}
            for row in rows
        ],
        "verdict": "READY_FOR_FINAL_REALIZATION" if passed else "PORTFOLIO_DECISION_DOWNGRADE_OR_DROP_P1",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(CONFIG)
    specs = load(SPECS)["candidates"]
    reasons = {row["construction_label"]: row["reason_for_call"] for row in load(INPUTS)["inputs"]}
    base = load(BASE_CONFIG)
    register_domain()
    jobs = [
        (spec, reasons[spec["label"]], config["conditions"]["E0"], seed, base)
        for spec in specs for seed in config["seeds"]
    ]
    assert config["formal_task_ids_allocated"] == 0 and len(jobs) == config["planned_trajectories"]
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: row["construction_label"])
    summary = summarize(rows)
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
