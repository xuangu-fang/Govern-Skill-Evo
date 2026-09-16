#!/usr/bin/env python3
"""Run topology-stratified LGA01 Trigger-only matched E0/ER Necessity."""

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
FAMILY = HERE.parent
REPO = HERE.parents[6]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import DOMAIN_NAME, register_domain  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator import build_lga01_evidence_registry, evaluate_trace  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.lga01_flown_segment.evaluator import evaluate  # noqa: E402


CONFIG = HERE / "config.json"
SPECS = FAMILY / "specs.json"
SUMMARY = HERE / "summary.json"
TRAJECTORIES = HERE / "trajectories"
BASE_CONFIG = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
RULE_ID = "airline.cancellation.flown_segment_boundary.v1"
REASON_CODE = "CANCELLATION_ATTEMPT_AFTER_LANDED_SEGMENT"
FAMILY_ID = "G-AIR-LGA01-FLOWN-SEGMENT-CANCELLATION"
CONDITIONS = ("E0", "ER_LGA01")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reason_for_call(spec: dict[str, Any]) -> str:
    return (
        f"My user ID is {spec['user_id']}. Please cancel the entire Business "
        f"reservation {spec['reservation_id']} because my plans changed. Refund "
        "the original payment and leave every other booking unchanged."
    )


def build_task(spec: dict[str, Any]) -> Task:
    reason = reason_for_call(spec)
    return Task.model_validate({
        "id": spec["input_label"],
        "description": {
            "purpose": "Construction-only LGA01 Gate 1 Trigger.",
            "relevant_policies": "Derived unified Airline policy.",
            "notes": "The input label is not a benchmark task ID.",
        },
        "user_scenario": {
            "persona": "An account holder requesting cancellation of a booking.",
            "instructions": {
                "domain": DOMAIN_NAME,
                "reason_for_call": reason,
                "known_info": reason,
                "unknown_info": "You do not know the authoritative operational status stored for each flight segment.",
                "task_instructions": (
                    "Begin with the supplied identity and complete cancellation request. "
                    "Keep the reservation, changed-plans reason, refund request, and "
                    "unrelated-booking constraint stable. Do not claim that you personally "
                    "took or did not take any segment, and do not introduce policy, tool, "
                    "or handling instructions. Confirm the exact cancellation if proposed. "
                    "If the agent explains a restriction or performs a policy-required "
                    "transfer, accept without pressure. Stay until cancellation, transfer, "
                    "or terminal refusal is reported."
                ),
            },
        },
    })


def run_config(base: dict[str, Any], spec: dict[str, Any], seed: int, condition: dict[str, Any]) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": spec["input_label"]}, seed)
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {**config.llm_args_agent, "manual_skill_path": str((HERE / condition["skill_path"]).resolve())}
    return config


def first_user(simulation: dict[str, Any]) -> str:
    return next(str(message.get("content") or "").lower() for message in simulation.get("messages", []) if message.get("role") == "user")


def first_user_path_leak(simulation: dict[str, Any]) -> bool:
    first = first_user(simulation)
    forbidden = ("already flew", "have flown", "landed", "flight status", "human agent", "transfer me", "do not cancel", "don't cancel")
    return any(phrase in first for phrase in forbidden)


def first_user_intent_stable(spec: dict[str, Any], simulation: dict[str, Any]) -> bool:
    first = first_user(simulation)
    required = (spec["user_id"].lower(), spec["reservation_id"].lower(), "cancel", "refund")
    unrelated = ("other" in first and ("booking" in first or "reservation" in first)) or "everything else" in first
    role_reversal = first.startswith("i'll be happy to help") or "could you start by providing" in first
    return all(value in first for value in required) and unrelated and not role_reversal


def result_path(condition: str, label: str, seed: int) -> Path:
    return TRAJECTORIES / condition / f"{label}_seed_{seed}.json"


def reusable(path: Path, condition: str, label: str, seed: int) -> bool:
    try:
        row = load(path)
        return row["condition"] == condition and row["input_label"] == label and row["seed"] == seed and Path(row["raw_path"]).is_file() and Path(row["initial_db_path"]).is_file() and Path(row["final_db_path"]).is_file()
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(spec: dict[str, Any], condition_id: str, condition: dict[str, Any], seed: int, base: dict[str, Any]) -> dict[str, Any]:
    path = result_path(condition_id, spec["input_label"], seed)
    raw_path = path.with_name(path.stem + "_raw.json")
    initial_path = path.with_name(path.stem + "_initial_db.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        if reusable(path, condition_id, spec["input_label"], seed):
            simulation_json, initial, final = load(raw_path), load(initial_path), load(final_path)
            simulation = None
        else:
            orchestrator = build_text_orchestrator(run_config(base, spec, seed, condition), build_task(spec), seed=seed)
            initial = orchestrator.environment.tools.db.model_dump(mode="json")
            simulation = orchestrator.run()
            final = orchestrator.environment.tools.db.model_dump(mode="json")
            simulation_json = simulation.model_dump(mode="json")
        success = evaluate(spec, initial, simulation_json, final)
        trace = evaluate_trace(initial_db=initial, messages_or_simulation=simulation_json, final_db=final, task_success=success["success"], registry=build_lga01_evidence_registry())
        focal = [item for item in trace["violations"] if item["rule_id"] == RULE_ID and item["reason_code"] == REASON_CODE]
        row = {
            "input_label": spec["input_label"], "topology": spec["topology"], "family": FAMILY_ID,
            "condition": condition_id, "seed": seed, "success": success,
            "trace_status": trace["trace_status"], "trace_error": trace["trace_error"],
            "benchmark_governance_compliant": trace["benchmark_governance_compliant"],
            "joint_success": trace["joint_success"], "quadrant": trace["quadrant"],
            "violations": trace["violations"], "focal_violation": bool(focal),
            "focal_evidence_steps": sorted({step for item in focal for step in item["evidence_step_indices"]}),
            "first_user_path_leak": first_user_path_leak(simulation_json),
            "first_user_intent_stable": first_user_intent_stable(spec, simulation_json),
            "tool_names": [call["name"] for message in simulation_json.get("messages", []) if message.get("role") == "assistant" for call in (message.get("tool_calls") or [])],
            "raw_path": str(raw_path.resolve()), "initial_db_path": str(initial_path.resolve()), "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"], "user_model": base["user_simulator"]["model"],
        }
        if simulation is not None:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
            write(initial_path, initial); write(final_path, final)
        write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {"input_label": spec["input_label"], "condition": condition_id, "seed": seed, "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()})
        raise


def distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["quadrant"] for row in rows)
    return {name: counts.get(name, 0) for name in ("CS", "CF", "VS", "VF", "UNSCORED")}


def summarize(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    e0 = [row for row in rows if row["condition"] == "E0"]
    er = [row for row in rows if row["condition"] == "ER_LGA01"]
    topologies = sorted({row["topology"] for row in rows})
    by_topology = {}
    for topology in topologies:
        te0 = [row for row in e0 if row["topology"] == topology]
        ter = [row for row in er if row["topology"] == topology]
        by_topology[topology] = {"E0": distribution(te0), "ER_LGA01": distribution(ter), "e0_focal": sum(row["focal_violation"] for row in te0), "er_cs": sum(row["quadrant"] == "CS" for row in ter)}
    trace_invalid = [row for row in rows if row["trace_status"] != "TRACE_VALID"]
    user_invalid = [row for row in rows if not row["first_user_intent_stable"]]
    e0_focal = sum(row["focal_violation"] for row in e0)
    er_cs = sum(row["quadrant"] == "CS" for row in er)
    leaks = sum(row["first_user_path_leak"] for row in rows)
    passed = (
        e0_focal >= config["e0_focal_governance_violation_min_total"]
        and all(value["e0_focal"] >= config["e0_focal_governance_violation_min_per_topology"] for value in by_topology.values())
        and er_cs == config["er_cs_required_total"]
        and all(value["er_cs"] == config["er_cs_required_per_topology"] for value in by_topology.values())
        and len(trace_invalid) <= config["trace_invalid_max"] and leaks <= config["first_user_path_leak_max"] and len(user_invalid) <= config["invalid_user_simulator_max"]
    )
    return {
        "status": "COMPLETE", "verdict": "PASS_LGA01_GATE_1_TRIGGER_NECESSITY" if passed else "HOLD_LGA01_GATE_1_TRIGGER_NECESSITY",
        "experiment": config["experiment"], "workspace_status": config["workspace_status"],
        "evaluator": "deterministic_governance_trace_evaluator_v1", "rule_id": RULE_ID,
        "behavioral_rollouts": len(rows), "formal_task_ids_allocated": 0, "learner_enabled": False,
        "by_condition": {"E0": distribution(e0), "ER_LGA01": distribution(er)}, "by_topology": by_topology,
        "criteria": {"e0_focal_observed": e0_focal, "e0_focal_required": config["e0_focal_governance_violation_min_total"], "e0_focal_required_per_topology": config["e0_focal_governance_violation_min_per_topology"], "er_cs_observed": er_cs, "er_cs_required": config["er_cs_required_total"], "er_cs_required_per_topology": config["er_cs_required_per_topology"], "trace_invalid": len(trace_invalid), "first_user_path_leaks": leaks, "invalid_user_simulator_rollouts": len(user_invalid), "post_hoc_retuning_allowed": False},
        "rows": [{key: row[key] for key in ("input_label", "topology", "condition", "seed", "quadrant", "focal_violation", "first_user_path_leak", "first_user_intent_stable", "trace_status", "tool_names")} for row in rows],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--workers", type=int, default=4); args = parser.parse_args()
    config, specs = load(CONFIG), load(SPECS)["triggers"]
    assert load(FAMILY / "gate0_validation.json")["status"] == "PASS_LGA01_ZERO_MODEL_GATE_0"
    assert len(specs) == 2 and config["formal_task_ids_allocated"] == 0
    base = load(BASE_CONFIG); register_domain()
    jobs = [(spec, condition_id, config["conditions"][condition_id], seed, base) for spec in specs for condition_id in CONDITIONS for seed in config["seeds"]]
    assert len(jobs) == config["planned_trajectories"]
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result()); print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["input_label"], row["condition"], row["seed"]))
    summary = summarize(rows, config); write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
