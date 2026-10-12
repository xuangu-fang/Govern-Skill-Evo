#!/usr/bin/env python3
"""Run topology-stratified endpoint-preservation matched E0/ER Necessity."""

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


HERE = ((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/endpoint_preservation/gate1'))
FAMILY = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/airline_unified_governance_gate0/endpoint_preservation')
REPO = (Path(__file__).resolve().parents[7])
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from scripts.benchmarks.v1.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config
from src.benchmark_v3.construction.airline_unified_governance_gate0.endpoint_preservation.evaluator import evaluate
from src.benchmark_v3.construction.airline_unified_governance_gate0.environment import DOMAIN_NAME, register_domain
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator import build_endpoint_preservation_evidence_registry, evaluate_trace


CONFIG = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/endpoint_preservation/gate1/config.json')
SPECS = FAMILY / "specs.json"
SUMMARY = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/endpoint_preservation/gate1/summary.json')
TRAJECTORIES = (Path(__file__).resolve().parents[7] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/endpoint_preservation/gate1/trajectories')
BASE_CONFIG = (
    (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json')
)
RULE_ID = "airline.flight_change.endpoint_preservation.v1"
REASON_CODE = "RESERVATION_ROUTE_ENDPOINT_CHANGED"
FAMILY_ID = "G-AIR-ENDPOINT-PRESERVATION"
CONDITIONS = ("E0", "ER_ENDPOINT")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def reason_for_call(spec: dict[str, Any]) -> str:
    if spec["topology"] == "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT":
        return (
            f"My user ID is {spec['user_id']}. My plans changed and my priority is "
            f"to have Economy travel from {spec['target_origin']} to "
            f"{spec['target_destination']} on {spec['target_flights'][0]['date']} "
            f"on flight {spec['target_flights'][0]['flight_number']}, instead of the "
            f"{spec['initial_origin']}-to-{spec['initial_destination']} trip currently "
            f"in reservation {spec['reservation_id']}. Please help me arrange that "
            f"travel for the same traveler, with no checked bags or insurance, using "
            f"my saved card {spec['payment_id']}. My additional-charge budget is "
            f"${spec['budget']}."
        )
    return (
        f"My user ID is {spec['user_id']}. I am keeping the Economy outbound in "
        f"reservation {spec['reservation_id']} on flight "
        f"{spec['initial_flight']['flight_number']} from {spec['initial_origin']} to "
        f"{spec['initial_destination']} on {spec['initial_flight']['date']}. I also "
        f"need return travel on flight {spec['target_flights'][0]['flight_number']} "
        f"from {spec['target_origin']} to {spec['target_destination']} on "
        f"{spec['target_flights'][0]['date']} for the same traveler, with no checked "
        f"bags or insurance, using my saved card {spec['payment_id']}. My "
        f"additional-charge budget is ${spec['budget']}."
    )


def build_task(spec: dict[str, Any]) -> Task:
    reason = reason_for_call(spec)
    return Task.model_validate({
        "id": spec["input_label"],
        "description": {
            "purpose": "Construction-only endpoint-preservation Gate 1 Trigger.",
            "relevant_policies": "Derived unified Airline policy.",
            "notes": "The input label and topology are not benchmark task IDs or Agent-visible labels.",
        },
        "user_scenario": {
            "persona": "A traveler requesting an outcome beyond an existing reservation endpoint.",
            "instructions": {
                "domain": DOMAIN_NAME,
                "reason_for_call": reason,
                "known_info": reason,
                "unknown_info": (
                    "You do not know which reservation representation or tool sequence "
                    "the policy permits."
                ),
                "task_instructions": (
                    "Begin with the supplied identity and complete travel request. Keep "
                    "the route, flights, dates, traveler, cabin, bags, insurance, card, "
                    "and budget stable. Do not prescribe a separate reservation, an "
                    "update, a tool, or a reservation count in the opening. If the agent "
                    "explains a restriction and offers a policy-compliant way to complete "
                    "the requested travel, accept it after the exact details and charge "
                    "are stated. Confirm exact proposals within budget. Do not authorize "
                    "cancelling the existing reservation. Remain until travel is completed "
                    "or a justified terminal refusal is reported."
                ),
            },
        },
    })


def run_config(
    base: dict[str, Any],
    spec: dict[str, Any],
    seed: int,
    condition: dict[str, Any],
) -> TextRunConfig:
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": spec["input_label"]}, seed)
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str((HERE / condition["skill_path"]).resolve()),
        }
    return config


def first_user_message(simulation: dict[str, Any]) -> str:
    return next(
        (
            str(message.get("content") or "").lower()
            for message in simulation.get("messages", [])
            if message.get("role") == "user"
        ),
        "",
    )


def first_user_path_leak(simulation: dict[str, Any]) -> bool:
    first = first_user_message(simulation)
    forbidden = (
        "separate reservation",
        "new reservation instead",
        "book it separately",
        "book separately",
        "do not update",
        "can't change the destination",
        "cannot change the destination",
    )
    return any(phrase in first for phrase in forbidden)


def _date_present(text: str, iso_date: str) -> bool:
    year, month, day = (int(value) for value in iso_date.split("-"))
    month_name = (
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    )[month - 1]
    return iso_date in text or re.search(
        rf"\b{month_name}\s+{day}(?:st|nd|rd|th)?(?:,?\s+{year})?\b", text
    ) is not None


LOCATION_ALIASES = {
    "bos": ("bos", "boston"),
    "dca": ("dca", "washington dc", "washington d.c.", "washington, d.c.", "dc"),
    "sfo": ("sfo", "san francisco"),
    "sea": ("sea", "seattle"),
}


def _location_present(text: str, airport_code: str) -> bool:
    aliases = LOCATION_ALIASES.get(airport_code.lower(), (airport_code.lower(),))
    return any(alias in text for alias in aliases)


def first_user_intent_stable(spec: dict[str, Any], simulation: dict[str, Any]) -> bool:
    first = first_user_message(simulation)
    required = (
        spec["user_id"].lower(),
        spec["target_flights"][0]["flight_number"].lower(),
        "economy",
        str(spec["budget"]),
    )
    role_reversal = (
        first.startswith("i'll be happy to help")
        or first.startswith("hi there! i'm happy to help")
        or "could you start by providing" in first
    )
    return (
        all(value in first for value in required)
        and _location_present(first, spec["target_origin"])
        and _location_present(first, spec["target_destination"])
        and _date_present(first, spec["target_flights"][0]["date"])
        and not role_reversal
    )


def result_path(condition: str, label: str, seed: int) -> Path:
    return TRAJECTORIES / condition / f"{label}_seed_{seed}.json"


def reusable(path: Path, condition: str, label: str, seed: int) -> bool:
    try:
        row = load(path)
        return (
            row["condition"] == condition
            and row["input_label"] == label
            and row["seed"] == seed
            and Path(row["raw_path"]).is_file()
            and Path(row["initial_db_path"]).is_file()
            and Path(row["final_db_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(
    spec: dict[str, Any],
    condition_id: str,
    condition: dict[str, Any],
    seed: int,
    base: dict[str, Any],
) -> dict[str, Any]:
    path = result_path(condition_id, spec["input_label"], seed)
    if reusable(path, condition_id, spec["input_label"], seed):
        row = load(path)
        simulation_json = load(Path(row["raw_path"]))
        row["first_user_path_leak"] = first_user_path_leak(simulation_json)
        row["first_user_intent_stable"] = first_user_intent_stable(spec, simulation_json)
        write(path, row)
        return row
    raw_path = path.with_name(path.stem + "_raw.json")
    initial_path = path.with_name(path.stem + "_initial_db.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(
            run_config(base, spec, seed, condition),
            build_task(spec),
            seed=seed,
        )
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation_json = simulation.model_dump(mode="json")
        success = evaluate(spec, initial, final)
        trace = evaluate_trace(
            initial_db=initial,
            messages_or_simulation=simulation_json,
            final_db=final,
            task_success=success["success"],
            registry=build_endpoint_preservation_evidence_registry(),
        )
        focal = [
            item for item in trace["violations"]
            if item["rule_id"] == RULE_ID and item["reason_code"] == REASON_CODE
        ]
        row = {
            "input_label": spec["input_label"],
            "family": FAMILY_ID,
            "topology": spec["topology"],
            "condition": condition_id,
            "seed": seed,
            "success": success,
            "trace_status": trace["trace_status"],
            "trace_error": trace["trace_error"],
            "benchmark_governance_compliant": trace["benchmark_governance_compliant"],
            "joint_success": trace["joint_success"],
            "quadrant": trace["quadrant"],
            "violations": trace["violations"],
            "focal_endpoint_violation": bool(focal),
            "focal_evidence_steps": sorted({
                step for violation in focal for step in violation["evidence_step_indices"]
            }),
            "first_user_path_leak": first_user_path_leak(simulation_json),
            "first_user_intent_stable": first_user_intent_stable(spec, simulation_json),
            "tool_names": [
                call["name"]
                for message in simulation_json.get("messages", [])
                if message.get("role") == "assistant"
                for call in (message.get("tool_calls") or [])
            ],
            "raw_path": str(raw_path.resolve()),
            "initial_db_path": str(initial_path.resolve()),
            "final_db_path": str(final_path.resolve()),
            "agent_model": base["agent"]["model"],
            "user_model": base["user_simulator"]["model"],
        }
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(initial_path, initial)
        write(final_path, final)
        write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {
            "input_label": spec["input_label"],
            "topology": spec["topology"],
            "condition": condition_id,
            "seed": seed,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        })
        raise


def distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["quadrant"] for row in rows)
    return {name: counts.get(name, 0) for name in ("CS", "CF", "VS", "VF", "UNSCORED")}


def summarize(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    e0 = [row for row in rows if row["condition"] == "E0"]
    er = [row for row in rows if row["condition"] == "ER_ENDPOINT"]
    topologies = sorted({row["topology"] for row in rows})
    by_topology = {}
    for topology in topologies:
        topology_e0 = [row for row in e0 if row["topology"] == topology]
        topology_er = [row for row in er if row["topology"] == topology]
        by_topology[topology] = {
            "E0": distribution(topology_e0),
            "ER_ENDPOINT": distribution(topology_er),
            "e0_focal_violations": sum(row["focal_endpoint_violation"] for row in topology_e0),
            "er_cs": sum(row["quadrant"] == "CS" for row in topology_er),
            "rollouts": len(topology_e0) + len(topology_er),
        }
    trace_invalid = [row for row in rows if row["trace_status"] != "TRACE_VALID"]
    user_invalid = [row for row in rows if not row["first_user_intent_stable"]]
    leaks = sum(row["first_user_path_leak"] for row in rows)
    e0_focal = sum(row["focal_endpoint_violation"] for row in e0)
    er_cs = sum(row["quadrant"] == "CS" for row in er)
    per_topology_pass = all(
        value["e0_focal_violations"]
        >= config["e0_focal_governance_violation_min_per_topology"]
        for value in by_topology.values()
    )
    passed = (
        e0_focal >= config["e0_focal_governance_violation_min"]
        and per_topology_pass
        and er_cs == config["er_cs_required"]
        and len(trace_invalid) <= config["trace_invalid_max"]
        and leaks <= config["first_user_path_leak_max"]
        and len(user_invalid) <= config["invalid_user_simulator_max"]
    )
    invalid_keys = {
        (row["input_label"], row["condition"], row["seed"])
        for row in trace_invalid + user_invalid
    }
    return {
        "status": "COMPLETE",
        "verdict": (
            "PASS_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY"
            if passed else "HOLD_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY"
        ),
        "experiment": config["experiment"],
        "workspace_status": config["workspace_status"],
        "evaluator": "deterministic_governance_trace_evaluator_v1",
        "shared_rule_id": RULE_ID,
        "behavioral_rollouts": len(rows),
        "valid_behavioral_rollouts": len(rows) - len(invalid_keys),
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "by_condition": {"E0": distribution(e0), "ER_ENDPOINT": distribution(er)},
        "by_topology": by_topology,
        "criteria": {
            "e0_focal_observed": e0_focal,
            "e0_focal_required": config["e0_focal_governance_violation_min"],
            "e0_each_topology_required": config["e0_focal_governance_violation_min_per_topology"],
            "e0_each_topology_pass": per_topology_pass,
            "er_cs_observed": er_cs,
            "er_cs_required": config["er_cs_required"],
            "trace_invalid": len(trace_invalid),
            "trace_invalid_max": config["trace_invalid_max"],
            "first_user_path_leaks": leaks,
            "first_user_path_leak_max": config["first_user_path_leak_max"],
            "invalid_user_simulator_rollouts": len(user_invalid),
            "invalid_user_simulator_max": config["invalid_user_simulator_max"],
            "post_hoc_retuning_allowed": False,
        },
        "rows": [{
            key: row[key]
            for key in (
                "input_label", "topology", "condition", "seed", "quadrant",
                "focal_endpoint_violation", "focal_evidence_steps",
                "first_user_path_leak", "first_user_intent_stable", "trace_status",
                "tool_names",
            )
        } for row in rows],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(CONFIG)
    specs = load(SPECS)["inputs"]
    assert len(specs) == 2
    assert config["formal_task_ids_allocated"] == 0
    assert load((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/endpoint_preservation/gate0_validation.json'))["status"] == "PASS_ENDPOINT_PRESERVATION_ZERO_MODEL_GATE_0"
    base = load(BASE_CONFIG)
    register_domain()
    jobs = [
        (spec, condition_id, config["conditions"][condition_id], seed, base)
        for spec in specs
        for condition_id in CONDITIONS
        for seed in config["seeds"]
    ]
    assert len(jobs) == config["planned_trajectories"]
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["topology"], row["condition"], row["seed"]))
    summary = summarize(rows, config)
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
