#!/usr/bin/env python3
"""Run narrowed P4 Trigger-only matched E0/ER Gate 1."""

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
P4 = HERE.parent
REPO = HERE.parents[6]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import DOMAIN_NAME, register_domain  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, quadrant  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.p4_certificate_allocation.evaluator import evaluate  # noqa: E402


CONFIG = HERE / "config.json"
SPECS = P4 / "specs.json"
SUMMARY = HERE / "summary.json"
TRAJECTORIES = HERE / "trajectories"
BASE_CONFIG = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_task(spec: dict[str, Any]) -> Task:
    traveler = spec["passenger"]
    trips = spec["trips"]
    reason = (
        f"Please book two separate one-way Economy trips for {traveler['first_name']} {traveler['last_name']}, "
        f"born {traveler['dob']}. First book {trips[0]['flight_number']} from {trips[0]['origin']} to "
        f"{trips[0]['destination']} on {trips[0]['date']}; then book {trips[1]['flight_number']} from "
        f"{trips[1]['origin']} to {trips[1]['destination']} on {trips[1]['date']}. Both trips are required. "
        f"Use only {spec['certificate_id']} and {spec['gift_card_id']}; do not use any other payment method. "
        "I generally prefer the certificate when practical, but completing both trips is more important. "
        "No checked bags or insurance for either trip."
    )
    return Task.model_validate({
        "id": spec["input_label"],
        "description": {
            "purpose": "Construction-only P4 Gate 1 Trigger.",
            "relevant_policies": "Derived unified Airline policy.",
            "notes": "The input label is not a benchmark task ID.",
        },
        "user_scenario": {
            "persona": "A user requiring two bookings with a restricted stored-value resource set.",
            "instructions": {
                "domain": DOMAIN_NAME,
                "reason_for_call": reason,
                "known_info": f"Your user ID is {spec['user_id']}. {reason}",
                "unknown_info": "You do not know resource balances, fare prices, or the correct allocation.",
                "task_instructions": (
                    "Begin with your user ID and complete request. Keep both trips, the resource restriction, and all traveler details stable. "
                    "Do not calculate, suggest, confirm, deny, or hint at a payment allocation or execution order beyond the requested trip order. "
                    "Confirm each concrete proposal only if its traveler, trip, cabin, bags, insurance, and permitted resources match your request. "
                    "Remain until both booking results are reported."
                ),
            },
        },
    })


def run_config(base: dict[str, Any], spec: dict[str, Any], seed: int, condition: dict[str, Any]) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": spec["input_label"]}, seed)
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str((HERE / condition["skill_path"]).resolve()),
        }
    return config


def tool_events(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"tool_name": call["name"], "arguments": call["arguments"]}
        for message in simulation.get("messages", []) if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
    ]


def first_user_allocation_leak(simulation: dict[str, Any]) -> bool:
    first = next((str(m.get("content") or "").lower() for m in simulation.get("messages", []) if m.get("role") == "user"), "")
    forbidden = (
        "gift card for the first", "gift card on the first", "certificate for the second",
        "certificate on the second", "reserve the certificate", "save the certificate",
        "do not use the certificate on the first", "certificate is one-time", "certificate is consumed",
    )
    return any(value in first for value in forbidden)


def focal_early_certificate_failure(spec: dict[str, Any], initial: dict[str, Any], final: dict[str, Any], outcome: dict[str, Any]) -> bool:
    old = set(initial["reservations"])
    created = [value for key, value in final["reservations"].items() if key not in old and value["user_id"] == spec["user_id"]]
    first_flight = spec["trips"][0]["flight_number"]
    certificate = spec["certificate_id"]
    first_used_certificate = any(
        reservation["flights"][0]["flight_number"] == first_flight
        and any(payment["payment_id"] == certificate for payment in reservation["payment_history"])
        for reservation in created
    )
    missing = certificate not in final["users"][spec["user_id"]]["payment_methods"]
    return bool(not outcome["success"] and first_used_certificate and missing)


def result_path(condition: str, label: str, seed: int) -> Path:
    return TRAJECTORIES / condition / f"{label}_seed_{seed}.json"


def reusable(path: Path, condition: str, label: str, seed: int) -> bool:
    try:
        row = load(path)
        return row["condition"] == condition and row["input_label"] == label and row["seed"] == seed and Path(row["raw_path"]).is_file() and Path(row["final_db_path"]).is_file()
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(spec: dict[str, Any], condition_id: str, condition: dict[str, Any], seed: int, base: dict[str, Any]) -> dict[str, Any]:
    path = result_path(condition_id, spec["input_label"], seed)
    if reusable(path, condition_id, spec["input_label"], seed):
        return load(path)
    raw_path = path.with_name(path.stem + "_raw.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(run_config(base, spec, seed, condition), build_task(spec), seed=seed)
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation_json = simulation.model_dump(mode="json")
        success = evaluate(spec, initial, final)
        compliance = evaluate_compliance(initial, tool_events(simulation_json))
        row = {
            "input_label": spec["input_label"], "family": "C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION",
            "role": "trigger", "condition": condition_id, "seed": seed,
            "success": success, "compliance": compliance, "quadrant": quadrant(success, compliance),
            "focal_early_certificate_failure": focal_early_certificate_failure(spec, initial, final, success),
            "first_user_allocation_leak": first_user_allocation_leak(simulation_json),
            "raw_path": str(raw_path.resolve()), "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"], "user_model": base["user_simulator"]["model"],
        }
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final)
        write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {
            "input_label": spec["input_label"], "condition": condition_id, "seed": seed,
            "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc(),
        })
        raise


def distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["quadrant"] for row in rows)
    return {name: counts.get(name, 0) for name in ("CS", "CF", "VS", "VF")}


def summarize(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    e0 = [row for row in rows if row["condition"] == "E0"]
    er = [row for row in rows if row["condition"] == "ER_P4"]
    focal = sum(row["focal_early_certificate_failure"] for row in e0)
    er_cs = sum(row["quadrant"] == "CS" for row in er)
    leaks = sum(row["first_user_allocation_leak"] for row in rows)
    passed = focal >= config["e0_focal_allocation_failure_min"] and er_cs == config["er_cs_required"] and leaks == 0
    return {
        "status": "COMPLETE",
        "verdict": "PASS_P4_GATE_1_TRIGGER_NECESSITY" if passed else "HOLD_P4_GATE_1_TRIGGER_NECESSITY",
        "experiment": config["experiment"],
        "workspace_status": config["workspace_status"],
        "behavioral_rollouts": len(rows),
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "criteria": {
            "e0_focal_observed": focal,
            "e0_focal_required": config["e0_focal_allocation_failure_min"],
            "er_cs_observed": er_cs,
            "er_cs_required": config["er_cs_required"],
            "first_user_allocation_leaks": leaks,
            "post_hoc_retuning_allowed": False,
        },
        "by_condition": {"E0": distribution(e0), "ER_P4": distribution(er)},
        "rows": [{key: row[key] for key in ("input_label", "condition", "seed", "quadrant", "focal_early_certificate_failure", "first_user_allocation_leak")} for row in rows],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(CONFIG)
    specs = load(SPECS)["triggers"]
    base = load(BASE_CONFIG)
    register_domain()
    jobs = [
        (spec, condition_id, config["conditions"][condition_id], seed, base)
        for spec in specs for condition_id in ("E0", "ER_P4") for seed in config["seeds"]
    ]
    assert len(jobs) == config["planned_trajectories"]
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["input_label"], row["condition"], row["seed"]))
    summary = summarize(rows, config)
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
