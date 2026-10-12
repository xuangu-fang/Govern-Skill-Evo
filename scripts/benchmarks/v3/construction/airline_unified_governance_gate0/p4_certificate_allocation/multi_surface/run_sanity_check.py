#!/usr/bin/env python3
"""Run one E0 sanity rollout for each P4 pre-ID Trigger candidate."""

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


HERE = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface')
REPO = HERE.parents[6]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from scripts.benchmarks.v1.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.environment import DOMAIN_NAME, register_domain  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, quadrant  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.p4_certificate_allocation.evaluator import evaluate  # noqa: E402


CONFIG = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface/sanity_config.json')
SPECS = HERE / "specs.json"
INPUTS = HERE / "candidate_inputs.json"
SUMMARY = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface/sanity_summary.json')
TRAJECTORIES = (Path(__file__).resolve().parents[7] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface/sanity/trajectories')
BASE_CONFIG = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json')


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_task(spec: dict[str, Any], reason: str) -> Task:
    return Task.model_validate({
        "id": spec["label"],
        "description": {"purpose": "Construction-only P4 pre-ID sanity input.", "relevant_policies": "Derived unified Airline policy.", "notes": "Not a benchmark task ID."},
        "user_scenario": {
            "persona": "A user requiring two bookings with a restricted stored-value resource set.",
            "instructions": {
                "domain": DOMAIN_NAME,
                "reason_for_call": reason,
                "known_info": f"Your user ID is {spec['user_id']}. {reason}",
                "unknown_info": "You do not know resource balances, fare prices, or the correct allocation.",
                "task_instructions": (
                    "Begin with your user ID and complete request. Keep both trips, resource restriction, preference, and traveler details stable. "
                    "Do not calculate, suggest, confirm, deny, or hint at a payment allocation. Confirm concrete proposals only when all requested details and permitted resources match. "
                    "Remain until both booking results are reported."
                ),
            },
        },
    })


def tool_events(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"tool_name": call["name"], "arguments": call["arguments"]} for message in simulation.get("messages", []) if message.get("role") == "assistant" for call in (message.get("tool_calls") or [])]


def first_user_leak(simulation: dict[str, Any]) -> bool:
    first = next((str(row.get("content") or "").lower() for row in simulation.get("messages", []) if row.get("role") == "user"), "")
    return any(value in first for value in ("gift card for the first", "certificate for the second", "save the certificate", "reserve the certificate", "certificate is one-time", "certificate is consumed"))


def focal_failure(spec: dict[str, Any], initial: dict[str, Any], final: dict[str, Any], success: dict[str, Any]) -> bool:
    old = set(initial["reservations"])
    created = [value for key, value in final["reservations"].items() if key not in old and value["user_id"] == spec["user_id"]]
    first_used_certificate = any(
        reservation["flights"][0]["flight_number"] == spec["trips"][0]["flight_number"]
        and any(payment["payment_id"] == spec["certificate_id"] for payment in reservation["payment_history"])
        for reservation in created
    )
    missing = spec["certificate_id"] not in final["users"][spec["user_id"]]["payment_methods"]
    return bool(not success["success"] and first_used_certificate and missing)


def run_config(base: dict[str, Any], label: str, seed: int) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": label}, seed)
    config.agent = "llm_agent"
    return config


def run_one(spec: dict[str, Any], reason: str, seed: int, base: dict[str, Any]) -> dict[str, Any]:
    path = (Path(__file__).resolve().parents[7] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface/sanity/trajectories/E0') / f"{spec['label']}_seed_{seed}.json"
    raw_path = path.with_name(path.stem + "_raw.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(run_config(base, spec["label"], seed), build_task(spec, reason), seed=seed)
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation_json = simulation.model_dump(mode="json")
        success = evaluate(spec, initial, final)
        compliance = evaluate_compliance(initial, tool_events(simulation_json))
        row = {
            "construction_label": spec["label"], "condition": "E0", "seed": seed,
            "success": success, "compliance": compliance, "quadrant": quadrant(success, compliance),
            "focal_early_certificate_failure": focal_failure(spec, initial, final, success),
            "first_user_allocation_leak": first_user_leak(simulation_json),
            "raw_path": str(raw_path.resolve()), "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"], "user_model": base["user_simulator"]["model"],
        }
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(final_path, final)
        write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {"construction_label": spec["label"], "seed": seed, "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(CONFIG)
    specs = load(SPECS)["candidates"]
    reasons = {row["construction_label"]: row["reason_for_call"] for row in load(INPUTS)["inputs"]}
    base = load(BASE_CONFIG)
    register_domain()
    jobs = [(spec, reasons[spec["label"]], config["seeds"][0], base) for spec in specs]
    assert config["formal_task_ids_allocated"] == 0 and len(jobs) == config["planned_trajectories"] == 8
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: row["construction_label"])
    focal = sum(row["focal_early_certificate_failure"] for row in rows)
    leaks = sum(row["first_user_allocation_leak"] for row in rows)
    criteria = {"focal_early_certificate_cf_at_least_5_of_8": focal >= 5, "no_first_user_allocation_leaks": leaks == 0}
    counts = Counter(row["quadrant"] for row in rows)
    summary = {
        "status": "PASS_P4_PRE_ID_SANITY_CHECK" if all(criteria.values()) else "HOLD_P4_PRE_ID_SANITY_CHECK",
        "workspace_status": "CONSTRUCTION_ONLY_NOT_AN_EDITION", "formal_task_ids_allocated": 0, "learner_enabled": False,
        "sanity_rollouts": len(rows), "predeclared_criteria": criteria,
        "counts": {"focal_early_certificate_cf": focal, "first_user_allocation_leaks": leaks},
        "overall_e0": {name: counts.get(name, 0) for name in ("CS", "CF", "VS", "VF")},
        "candidates_requiring_review": [row["construction_label"] for row in rows if not row["focal_early_certificate_failure"] or row["first_user_allocation_leak"]],
        "rows": [{key: row[key] for key in ("construction_label", "condition", "seed", "quadrant", "focal_early_certificate_failure", "first_user_allocation_leak")} for row in rows],
    }
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
