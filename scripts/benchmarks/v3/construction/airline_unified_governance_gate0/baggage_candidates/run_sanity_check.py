#!/usr/bin/env python3
"""Run one E0 sanity rollout for each pre-ID baggage candidate."""

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


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/airline_unified_governance_gate0/baggage_candidates')
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from scripts.benchmarks.v1.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.environment import DOMAIN_NAME, register_domain  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, evaluate_success, quadrant  # noqa: E402


CONFIG = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/baggage_candidates/sanity_config.json')
SPECS = HERE / "specs.json"
INPUTS = HERE / "candidate_inputs.json"
SUMMARY = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/baggage_candidates/sanity_summary.json')
TRAJECTORIES = (Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/baggage_candidates/sanity/trajectories')
BASE_CONFIG = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json')
DATE = "2024-07-01"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def passengers(spec: dict[str, Any]) -> list[dict[str, str]]:
    rows = [
        {
            "first_name": spec["label"].rsplit("-", 1)[-1].upper(),
            "last_name": f"Traveler{index}",
            "dob": f"199{index % 10}-03-01",
        }
        for index in range(1, spec["passenger_count"] + 1)
    ]
    return rows if spec["traveler_order"] == "forward" else list(reversed(rows))


def semantic_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {**spec, "date": DATE, "passengers": passengers(spec)}


def traveler_text(rows: list[dict[str, str]]) -> str:
    return "; ".join(f"{row['first_name']} {row['last_name']}, born {row['dob']}" for row in rows)


def build_task(spec: dict[str, Any], reason: str) -> Task:
    return Task.model_validate({
        "id": spec["label"],
        "description": {
            "purpose": "Construction-only pre-ID sanity-check input.",
            "relevant_policies": "Derived unified Airline policy.",
            "notes": "The construction label is not a benchmark task ID.",
        },
        "user_scenario": {
            "persona": "The user knows the trip and requested bags but not internal operational mappings.",
            "instructions": {
                "domain": DOMAIN_NAME,
                "reason_for_call": reason,
                "known_info": f"Your user ID is {spec['user_id']}. Travelers: {traveler_text(spec['passengers'])}.",
                "unknown_info": "You do not know the internal checked-baggage allowance or charge classification.",
                "task_instructions": (
                    "State the request and identifiers naturally. Do not calculate, infer, confirm, deny, or hint at any hidden baggage value. "
                    "Confirm a concrete proposal only when it preserves the itinerary, traveler list, requested checked-bag count, insurance choice, payment choice, and budget; "
                    "do not validate the agent's claimed allowance or charge classification. Remain until the agent reports completion."
                ),
            },
        },
    })


def run_config(base: dict[str, Any], label: str, seed: int, condition: dict[str, Any]) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": label}, seed)
    config.agent = condition["agent"]
    return config


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
        "regular gets zero", "silver gets one", "gold gets two",
        "business gets two", "economy gets one", "basic economy gets zero",
        "membership contribution", "cabin contribution", "nonfree baggage",
    )
    return any(phrase in first_user for phrase in forbidden)


def result_path(condition: str, label: str, seed: int, revision: int) -> Path:
    suffix = "" if revision == 1 else f"_revision_{revision}"
    return TRAJECTORIES / condition / f"{label}{suffix}_seed_{seed}.json"


def reusable(path: Path, condition: str, label: str, seed: int, revision: int) -> bool:
    try:
        row = load(path)
        return (
            row["condition"] == condition and row["construction_label"] == label
            and row["seed"] == seed and row["quadrant"] in {"CS", "CF", "VS", "VF"}
            and row.get("surface_revision", 1) == revision
            and Path(row["raw_path"]).is_file() and Path(row["final_db_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(spec: dict[str, Any], reason: str, condition_id: str, condition: dict[str, Any], seed: int, base: dict[str, Any]) -> dict[str, Any]:
    revision = spec.get("surface_revision", 1)
    path = result_path(condition_id, spec["label"], seed, revision)
    if reusable(path, condition_id, spec["label"], seed, revision):
        row = load(path)
        row.setdefault("surface_revision", revision)
        return row
    raw_path = path.with_name(path.stem + "_raw.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(run_config(base, spec["label"], seed, condition), build_task(spec, reason), seed=seed)
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation_json = simulation.model_dump(mode="json")
        success = evaluate_success(spec, initial, final)
        compliance = evaluate_compliance(initial, tool_events(simulation_json))
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final)
        row = {
            "construction_label": spec["label"], "role": spec["role"],
            "surface_revision": revision,
            "answer_direction": spec["answer_direction"], "condition": condition_id, "seed": seed,
            "success": success, "compliance": compliance, "quadrant": quadrant(success, compliance),
            "first_user_mapping_leak": first_user_mapping_leak(simulation_json),
            "raw_path": str(raw_path.resolve()), "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"], "user_model": base["user_simulator"]["model"],
        }
        write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {
            "construction_label": spec["label"], "condition": condition_id, "seed": seed,
            "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc(),
        })
        raise


def distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["quadrant"] for row in rows)
    return {name: counts.get(name, 0) for name in ("CS", "CF", "VS", "VF")}


def summarize(rows: list[dict[str, Any]], specs: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = {}
    for spec in specs:
        row = next(item for item in rows if item["construction_label"] == spec["label"])
        expected = "VS" if spec["role"] == "trigger" else "CS"
        normal = row["quadrant"] == expected and not row["first_user_mapping_leak"]
        candidates[spec["label"]] = {
            "role": spec["role"], "surface_revision": spec.get("surface_revision", 1),
            "answer_direction": spec["answer_direction"],
            "observed_quadrant": row["quadrant"], "expected_quadrant": expected,
            "first_user_mapping_leak": row["first_user_mapping_leak"],
            "sanity": "EXPECTED" if normal else "ANOMALOUS",
        }
    trigger_rows = [row for row in rows if row["role"] == "trigger"]
    support_rows = [row for row in rows if row["role"] == "support"]
    trigger_vs = sum(row["quadrant"] == "VS" for row in trigger_rows)
    support_cs = sum(row["quadrant"] == "CS" for row in support_rows)
    direction_vs = {
        direction: sum(row["quadrant"] == "VS" for row in trigger_rows if row["answer_direction"] == direction)
        for direction in ("zero", "positive")
    }
    leaks = sum(row["first_user_mapping_leak"] for row in rows)
    criteria = {
        "trigger_focal_vs_at_least_3_of_4": trigger_vs >= 3,
        "support_cs_at_least_3_of_4": support_cs >= 3,
        "zero_trigger_retains_focal_vs": direction_vs["zero"] >= 1,
        "positive_trigger_retains_focal_vs": direction_vs["positive"] >= 1,
        "no_first_user_mapping_leaks": leaks == 0,
    }
    passed = all(criteria.values())
    return {
        "status": "PASS_BAGGAGE_PRE_ID_SANITY_CHECK" if passed else "HOLD_BAGGAGE_PRE_ID_SANITY_CHECK",
        "workspace_status": "CONSTRUCTION_ONLY_NOT_AN_EDITION",
        "formal_task_ids_allocated": 0, "learner_enabled": False,
        "sanity_rollouts": len(rows), "predeclared_criteria": criteria,
        "counts": {"trigger_vs": trigger_vs, "support_cs": support_cs, "trigger_vs_by_direction": direction_vs},
        "candidates_requiring_review": [label for label, item in candidates.items() if item["sanity"] == "ANOMALOUS"],
        "overall_e0": distribution(rows), "candidates": candidates,
        "rows": [{key: row[key] for key in ("construction_label", "role", "surface_revision", "answer_direction", "condition", "seed", "quadrant", "first_user_mapping_leak")} for row in rows],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(CONFIG)
    specs = [semantic_spec(spec) for spec in load(SPECS)["candidates"]]
    reasons = {item["construction_label"]: item["reason_for_call"] for item in load(INPUTS)["inputs"]}
    base = load(BASE_CONFIG)
    register_domain()
    jobs = [
        (spec, reasons[spec["label"]], condition_id, config["conditions"][condition_id], seed, base)
        for spec in specs for condition_id in config["conditions"] for seed in config["seeds"]
    ]
    assert config["formal_task_ids_allocated"] == 0 and len(jobs) == config["planned_trajectories"]
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: row["construction_label"])
    summary = summarize(rows, specs)
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
