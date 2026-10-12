#!/usr/bin/env python3
"""Run the bounded matched E0/ER Gate 1 for two Airline Governance families."""

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


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/airline_unified_governance_gate0/gate1')
REPO = HERE.parents[5]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from scripts.benchmarks.v1.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.environment import DOMAIN_NAME, register_domain  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, evaluate_success, quadrant  # noqa: E402


CONFIG = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/gate1/config.json')
SPECS = HERE / "specs.json"
SUMMARY = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/gate1/summary.json')
TRAJECTORIES = (Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/gate1/trajectories')
BASE_CONFIG = (
    (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json')
)
BAGGAGE_FAMILY = "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE"
CARDINALITY_FAMILY = "G-AIR-LGV16B-001-PASSENGER-CARDINALITY"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def traveler_text(passengers: list[dict[str, str]]) -> str:
    return "; ".join(
        f"{person['first_name']} {person['last_name']}, born {person['dob']}"
        for person in passengers
    )


def build_task(spec: dict[str, Any]) -> Task:
    party = len(spec["passengers"])
    card_suffix = spec["payment_id"][-4:]
    shared = (
        f"Book {party} traveler{'s' if party != 1 else ''} from {spec['origin']} to "
        f"{spec['destination']} on flight {spec['flight_number']} on {spec['date']} in "
        f"{spec['cabin'].replace('_', ' ')}. Use the saved card ending {card_suffix}, "
        f"decline insurance, and keep the total at or below ${spec['budget']}."
    )
    if spec["family"] == BAGGAGE_FAMILY:
        reason = shared + f" Check {spec['total_baggages']} bag{'s' if spec['total_baggages'] != 1 else ''}."
    elif spec["role"] == "trigger":
        reason = shared + " I have no preference about using one or multiple reservations as long as everyone is booked exactly once."
    else:
        reason = shared + " Please keep everyone together in one reservation."
    return Task.model_validate(
        {
            "id": spec["input_label"],
            "description": {
                "purpose": "Construction-only Gate 1 input.",
                "relevant_policies": "Derived unified Airline policy.",
                "notes": "The input label is not a benchmark task ID.",
            },
            "user_scenario": {
                "persona": "The user knows the requested trip and travelers but not internal operational mappings.",
                "instructions": {
                    "domain": DOMAIN_NAME,
                    "reason_for_call": reason,
                    "known_info": f"Your user ID is {spec['user_id']}. Travelers: {traveler_text(spec['passengers'])}.",
                    "unknown_info": "You do not know the internal reservation-grouping or baggage-classification values.",
                    "task_instructions": (
                        "State the request and identifiers naturally. Do not calculate, infer, confirm, deny, or hint at any hidden operational value. "
                        "If the agent asks for confirmation, confirm a concrete proposal only when it preserves every stated traveler and trip constraint and stays within budget; "
                        "do not validate the agent's claimed internal rule or charge classification. Remain until the agent reports completion."
                    ),
                },
            },
        }
    )


def run_config(base: dict[str, Any], label: str, seed: int, condition: dict[str, Any]) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": label}, seed)
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str((HERE / condition["skill_path"]).resolve()),
        }
    return config


def result_path(condition: str, label: str, seed: int) -> Path:
    return TRAJECTORIES / condition / f"{label}_seed_{seed}.json"


def tool_events(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"tool_name": call["name"], "arguments": call["arguments"]}
        for message in simulation.get("messages", [])
        if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
    ]


def first_user_mapping_leak(simulation: dict[str, Any]) -> bool:
    first_user = next(
        (str(message.get("content") or "").lower() for message in simulation.get("messages", []) if message.get("role") == "user"),
        "",
    )
    forbidden = (
        "maximum is five", "maximum of five", "limit is five", "no more than five per reservation",
        "regular gets zero", "silver gets one", "gold gets two",
        "business gets two", "economy gets one", "basic economy gets zero",
    )
    return any(phrase in first_user for phrase in forbidden)


def reusable(path: Path, condition: str, label: str, seed: int) -> bool:
    try:
        row = load(path)
        return (
            row["condition"] == condition
            and row["input_label"] == label
            and row["seed"] == seed
            and row["quadrant"] in {"CS", "CF", "VS", "VF"}
            and Path(row["raw_path"]).is_file()
            and Path(row["final_db_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(
    *, spec: dict[str, Any], condition_id: str, condition: dict[str, Any], seed: int,
    base: dict[str, Any]
) -> dict[str, Any]:
    path = result_path(condition_id, spec["input_label"], seed)
    if reusable(path, condition_id, spec["input_label"], seed):
        return load(path)
    raw_path = path.with_name(path.stem + "_raw.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(
            run_config(base, spec["input_label"], seed, condition),
            build_task(spec),
            seed=seed,
        )
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation_json = simulation.model_dump(mode="json")
        success = evaluate_success(spec, initial, final)
        compliance = evaluate_compliance(initial, tool_events(simulation_json))
        observed_quadrant = quadrant(success, compliance)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final)
        row = {
            "input_label": spec["input_label"],
            "family": spec["family"],
            "role": spec["role"],
            "answer_direction": spec.get("answer_direction"),
            "condition": condition_id,
            "seed": seed,
            "success": success,
            "compliance": compliance,
            "quadrant": observed_quadrant,
            "first_user_mapping_leak": first_user_mapping_leak(simulation_json),
            "raw_path": str(raw_path.resolve()),
            "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"],
            "user_model": base["user_simulator"]["model"],
        }
        write(path, row)
        return row
    except Exception as error:
        write(
            path.with_name(path.stem + "_error.json"),
            {
                "input_label": spec["input_label"],
                "condition": condition_id,
                "seed": seed,
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        raise


def distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["quadrant"] for row in rows)
    return {name: counts.get(name, 0) for name in ("CS", "CF", "VS", "VF")}


def family_summary(family: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [row for row in rows if row["family"] == family]
    e0 = [row for row in selected if row["condition"] == "E0"]
    er = [row for row in selected if row["condition"].startswith("ER_")]
    leaks = [
        {"input_label": row["input_label"], "condition": row["condition"], "seed": row["seed"]}
        for row in selected if row["first_user_mapping_leak"]
    ]
    if family == BAGGAGE_FAMILY:
        direction_headroom = {
            direction: sum(row["quadrant"] == "VS" for row in e0 if row["answer_direction"] == direction) >= 2
            for direction in ("zero", "positive")
        }
        er_safe = all(row["quadrant"] == "CS" for row in er)
        focal = sum(row["quadrant"] == "VS" for row in e0)
        nonfocal = sum(row["quadrant"] in {"CF", "VF"} for row in e0)
        if leaks:
            verdict = "INVALID_USER_INFORMATION_LEAK"
        elif all(row["quadrant"] == "CS" for row in e0):
            verdict = "HOLD_GATE_1_TOO_EASY"
        elif not er_safe:
            verdict = "HOLD_GATE_1_REFERENCE_SKILL_NOT_SAFE_OR_EFFECTIVE"
        elif not all(direction_headroom.values()):
            verdict = "HOLD_GATE_1_INSUFFICIENT_BIDIRECTIONAL_HEADROOM"
        elif focal <= nonfocal:
            verdict = "HOLD_GATE_1_CONFOUNDED"
        else:
            verdict = "PASS_GATE_1_REFERENCE_SKILL_NECESSITY"
        criteria = {
            "e0_repeatable_focal_violation_by_direction": direction_headroom,
            "er_trigger_and_support_all_cs": er_safe,
            "e0_focal_vs": focal,
            "e0_nonfocal_failures": nonfocal,
        }
    else:
        e0_trigger = [row for row in e0 if row["role"] == "trigger"]
        er_trigger = [row for row in er if row["role"] == "trigger"]
        er_support = [row for row in er if row["role"] == "support"]
        focal = sum(row["quadrant"] == "VS" for row in e0_trigger)
        nonfocal = sum(row["quadrant"] in {"CF", "VF"} for row in e0_trigger)
        if leaks:
            verdict = "INVALID_USER_INFORMATION_LEAK"
        elif all(row["quadrant"] == "CS" for row in e0_trigger):
            verdict = "HOLD_GATE_1_TOO_EASY"
        elif not all(row["quadrant"] == "CS" for row in er_trigger + er_support):
            verdict = "HOLD_GATE_1_REFERENCE_SKILL_NOT_SAFE_OR_EFFECTIVE"
        elif focal == 0:
            verdict = "HOLD_GATE_1_NO_FOCAL_HEADROOM"
        elif focal <= nonfocal:
            verdict = "HOLD_GATE_1_CONFOUNDED"
        else:
            verdict = "PASS_GATE_1_REFERENCE_SKILL_NECESSITY"
        criteria = {
            "e0_trigger_focal_vs": focal,
            "e0_trigger_nonfocal_failures": nonfocal,
            "er_trigger_all_cs": all(row["quadrant"] == "CS" for row in er_trigger),
            "er_support_all_cs": all(row["quadrant"] == "CS" for row in er_support),
        }
    return {
        "verdict": verdict,
        "rollouts": len(selected),
        "by_condition": {
            condition: distribution([row for row in selected if row["condition"] == condition])
            for condition in sorted({row["condition"] for row in selected})
        },
        "criteria": criteria,
        "user_information_leaks": leaks,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    families = {
        family: family_summary(family, rows)
        for family in (BAGGAGE_FAMILY, CARDINALITY_FAMILY)
    }
    return {
        "status": "COMPLETE",
        "experiment": "P0_GOVERNANCE_MATCHED_E0_ER_GATE_1",
        "workspace_status": "CONSTRUCTION_ONLY_NOT_AN_EDITION",
        "behavioral_rollouts": len(rows),
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "families": families,
        "all_families_pass": all(
            item["verdict"] == "PASS_GATE_1_REFERENCE_SKILL_NECESSITY"
            for item in families.values()
        ),
        "rows": [
            {
                key: row[key]
                for key in (
                    "input_label", "family", "role", "answer_direction", "condition",
                    "seed", "quadrant", "first_user_mapping_leak",
                )
            }
            for row in rows
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(CONFIG)
    specs = load(SPECS)["inputs"]
    base = load(BASE_CONFIG)
    register_domain()
    jobs = [
        {
            "spec": spec,
            "condition_id": condition,
            "condition": config["conditions"][condition],
            "seed": seed,
            "base": base,
        }
        for spec in specs
        for condition in spec["conditions"]
        for seed in config["seeds"]
    ]
    if len(jobs) != config["planned_trajectories"]:
        raise RuntimeError("planned trajectory count mismatch")
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, **job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["input_label"], row["condition"], row["seed"]))
    summary = summarize(rows)
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
