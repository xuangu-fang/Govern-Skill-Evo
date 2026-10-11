#!/usr/bin/env python3
"""Run P5 Trigger-only matched E0/ER Necessity."""

from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
P5 = HERE.parent
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
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.p5_incremental_settlement.evaluator import evaluate  # noqa: E402


CONFIG = HERE / "config.json"
SPECS = P5 / "specs.json"
SUMMARY = HERE / "summary.json"
TRAJECTORIES = HERE / "trajectories"
BASE_CONFIG = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_task(spec: dict[str, Any]) -> Task:
    reason = (
        f"Please change reservation {spec['reservation_id']} to the direct {spec['origin']}-to-{spec['destination']} "
        f"flight on {spec['new_date']}. I prefer Business if the additional charge for everyone is no more than "
        f"${spec['incremental_limit']}; otherwise use Economy if its additional charge is within the same limit. "
        "If neither cabin fits, leave the reservation unchanged. Keep the same passengers, use my saved card, "
        "and do not change baggage or insurance."
    )
    return Task.model_validate({
        "id": spec["input_label"],
        "description": {
            "purpose": "Construction-only P5 Gate 1 Trigger.",
            "relevant_policies": "Derived unified Airline policy.",
            "notes": "The input label is not a benchmark task ID.",
        },
        "user_scenario": {
            "persona": "A traveler choosing a replacement cabin under an additional-charge limit.",
            "instructions": {
                "domain": DOMAIN_NAME,
                "reason_for_call": reason,
                "known_info": f"Your user ID is {spec['user_id']}. {reason}",
                "unknown_info": "You do not know stored flight prices, candidate fares, the settlement delta, or the correct cabin branch.",
                "task_instructions": (
                    "Begin with your user ID and complete request. Keep the reservation, date, route, cabin preference, limit, passengers, and preservation constraints stable. "
                    "Do not calculate, suggest, confirm, deny, or hint at a fare difference, settlement baseline, or correct cabin. "
                    "Confirm a proposal only if the route, date, cabin-selection condition, passengers, additional charge, payment method, baggage, and insurance match your request. "
                    "Remain until the completed update or a justified no-change result is reported."
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


def first_user_answer_leak(spec: dict[str, Any], simulation: dict[str, Any]) -> bool:
    first = next((str(row.get("content") or "").lower() for row in simulation.get("messages", []) if row.get("role") == "user"), "")
    amount = spec["expected_change_amount"]
    computed_amount = re.search(rf"(?:additional|difference|delta|more)[^.!?]{{0,30}}\$?{amount}\b", first)
    branch = spec["expected_cabin"]
    unconditional_branch = any(phrase in first for phrase in (f"choose {branch}", f"book {branch}", f"{branch} is within"))
    return bool(computed_amount or unconditional_branch)


def first_user_intent_stable(spec: dict[str, Any], simulation: dict[str, Any]) -> bool:
    first = next((str(row.get("content") or "").lower() for row in simulation.get("messages", []) if row.get("role") == "user"), "")
    required = (spec["user_id"].lower(), spec["reservation_id"].lower(), str(spec["incremental_limit"]))
    role_reversal = first.startswith("i'll be happy to help") or "could you confirm" in first
    return bool(all(value in first for value in required) and not role_reversal)


def focal_settlement_failure(
    spec: dict[str, Any], events: list[dict[str, Any]], outcome: dict[str, Any]
) -> bool:
    names = [row["tool_name"] for row in events]
    read_ready = "get_reservation_details" in names and "search_direct_flight" in names
    writes = [row for row in events if row["tool_name"] == "update_reservation_flights"]
    wrong_write = any(row["arguments"].get("cabin") != spec["expected_cabin"] for row in writes)
    no_write = not writes
    return bool(not outcome["success"] and read_ready and (no_write or wrong_write))


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
        row = load(path)
        if "first_user_intent_stable" not in row:
            simulation = load(Path(row["raw_path"]))
            row["first_user_intent_stable"] = first_user_intent_stable(spec, simulation)
            write(path, row)
        return row
    raw_path = path.with_name(path.stem + "_raw.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(run_config(base, spec, seed, condition), build_task(spec), seed=seed)
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation_json = simulation.model_dump(mode="json")
        events = tool_events(simulation_json)
        success = evaluate(spec, initial, final)
        compliance = evaluate_compliance(initial, events)
        row = {
            "input_label": spec["input_label"],
            "family": "C-AIR-P5-INCREMENTAL-SETTLEMENT-FEASIBILITY",
            "role": "trigger",
            "direction": spec["direction"],
            "condition": condition_id,
            "seed": seed,
            "success": success,
            "compliance": compliance,
            "quadrant": quadrant(success, compliance),
            "focal_settlement_failure": focal_settlement_failure(spec, events, success),
            "first_user_answer_leak": first_user_answer_leak(spec, simulation_json),
            "first_user_intent_stable": first_user_intent_stable(spec, simulation_json),
            "tool_names": [event["tool_name"] for event in events],
            "raw_path": str(raw_path.resolve()),
            "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"],
            "user_model": base["user_simulator"]["model"],
        }
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final)
        write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {
            "input_label": spec["input_label"],
            "condition": condition_id,
            "seed": seed,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        })
        raise


def distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["quadrant"] for row in rows)
    return {name: counts.get(name, 0) for name in ("CS", "CF", "VS", "VF")}


def summarize(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    e0 = [row for row in rows if row["condition"] == "E0"]
    er = [row for row in rows if row["condition"] == "ER_P5"]
    invalid = [row for row in rows if not row["first_user_intent_stable"]]
    focal = sum(row["focal_settlement_failure"] for row in e0 if row["first_user_intent_stable"])
    er_cs = sum(row["quadrant"] == "CS" for row in er if row["first_user_intent_stable"])
    leaks = sum(row["first_user_answer_leak"] for row in rows)
    passed = not invalid and focal >= config["e0_focal_settlement_failure_min"] and er_cs == config["er_cs_required"] and leaks == 0
    return {
        "status": "COMPLETE",
        "verdict": "PASS_P5_GATE_1_TRIGGER_NECESSITY" if passed else "HOLD_P5_GATE_1_TRIGGER_NECESSITY",
        "experiment": config["experiment"],
        "workspace_status": config["workspace_status"],
        "behavioral_rollouts": len(rows),
        "valid_behavioral_rollouts": len(rows) - len(invalid),
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "criteria": {
            "e0_focal_observed": focal,
            "e0_focal_required": config["e0_focal_settlement_failure_min"],
            "er_cs_observed": er_cs,
            "er_cs_required": config["er_cs_required"],
            "first_user_answer_leaks": leaks,
            "invalid_user_simulator_rollouts": len(invalid),
            "post_hoc_retuning_allowed": False,
        },
        "by_condition": {"E0": distribution(e0), "ER_P5": distribution(er)},
        "rows": [{
            key: row[key]
            for key in ("input_label", "direction", "condition", "seed", "quadrant", "focal_settlement_failure", "first_user_answer_leak", "first_user_intent_stable")
        } for row in rows],
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
        for spec in specs for condition_id in ("E0", "ER_P5") for seed in config["seeds"]
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
