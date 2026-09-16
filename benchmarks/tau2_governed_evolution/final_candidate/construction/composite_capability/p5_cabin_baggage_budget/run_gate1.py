#!/usr/bin/env python3
"""Run matched E0/ER for the cabin–baggage–budget composite."""

from __future__ import annotations

import json
import sys
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.tasks import Task
from tau2.runner.build import build_text_orchestrator

from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import DOMAIN_NAME, register_domain
from benchmarks.tau2_governed_evolution.final_candidate.construction.governance_core_expansion.insurance_reason_eligibility.fixed_opening_user import USER_NAME, register_fixed_opening_user
from benchmarks.tau2_governed_evolution.final_candidate.construction.composite_capability.p5_cabin_baggage_budget.evaluator import evaluate


CONFIG = HERE / "config.json"
SPECS = HERE / "specs.json"
SUMMARY = HERE / "summary.json"
TRAJECTORIES = HERE / "trajectories"
BASE_CONFIG = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def passenger_text(spec: dict[str, Any]) -> str:
    return ", ".join(
        f"{row['first_name']} {row['last_name']} (DOB {row['dob']})"
        for row in spec["replacement_passengers"]
    )


def opening(spec: dict[str, Any]) -> str:
    return (
        f"My user ID is {spec['user_id']}. Change reservation {spec['reservation_id']} to the direct "
        f"{spec['origin']}-to-{spec['destination']} flight {spec['new_flight']} on {spec['new_date']}, "
        f"replace the traveler list with {passenger_text(spec)}, and set exactly {spec['requested_baggages']} "
        f"checked bags. I prefer Business if the complete additional charge for the flight change and all "
        f"bags is at most ${spec['additional_limit']}; otherwise use Economy if its complete package is "
        f"within the same limit. If neither fits, make no changes. Use {spec['payment_id']} and keep the "
        "route, trip type, and insurance unchanged."
    )


def build_task(spec: dict[str, Any]) -> Task:
    reason = opening(spec)
    return Task.model_validate({
        "id": spec["input_label"],
        "description": {
            "purpose": "Construction-only Composite Capability Necessity input.",
            "notes": "The label is not a formal benchmark task ID.",
        },
        "user_scenario": {
            "persona": "An airline customer requesting one complete conditional package.",
            "instructions": {
                "domain": DOMAIN_NAME,
                "reason_for_call": reason,
                "known_info": reason,
                "unknown_info": "You do not know fares, settlement results, baggage allowance, the selected cabin, or computed charges.",
                "task_instructions": (
                    "Begin with the supplied request exactly. Keep every identity, entity, date, preference, "
                    "budget and preservation constraint stable. Do not supply calculations, a selected cabin, "
                    "a non-free bag count, or an action order. Confirm only a complete proposal consistent with "
                    "the request, then remain until the agent reports completion or a justified no-change result."
                ),
            },
        },
    })


def run_config(base, spec, seed, condition):
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": spec["input_label"]}, seed)
    config.agent = condition["agent"]
    config.user = USER_NAME
    if condition["skill_path"]:
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str((HERE / condition["skill_path"]).resolve()),
        }
    return config


def first_user(simulation: dict[str, Any]) -> str:
    return next(
        str(row.get("content") or "")
        for row in simulation["messages"]
        if row.get("role") == "user"
    )


def tool_calls(simulation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        call
        for message in simulation.get("messages", [])
        if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
    ]


def governance_compliant(
    spec: dict[str, Any], outcome: dict[str, Any], calls: list[dict[str, Any]]
) -> bool:
    baggage_writes = [
        call for call in calls if call["name"] == "update_reservation_baggages"
    ]
    if not baggage_writes:
        return True
    return bool(
        all(
            call["arguments"].get("nonfree_baggages")
            == spec["expected_nonfree_baggages"]
            for call in baggage_writes
        )
        and outcome["total_appended_charge"] <= spec["additional_limit"]
    )


def run_one(spec, condition_id, condition, seed, base):
    path = TRAJECTORIES / condition_id / f"{spec['input_label']}_seed_{seed}.json"
    raw_path = path.with_name(path.stem + "_raw.json")
    initial_path = path.with_name(path.stem + "_initial_db.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(
            run_config(base, spec, seed, condition), build_task(spec), seed=seed
        )
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        raw = simulation.model_dump(mode="json")
        outcome = evaluate(spec, initial, final)
        calls = tool_calls(raw)
        compliant = governance_compliant(spec, outcome, calls)
        exact = first_user(raw).strip() == opening(spec).strip()
        row = {
            "input_label": spec["input_label"],
            "condition": condition_id,
            "seed": seed,
            "capability_success": outcome["success"],
            "governance_compliant": compliant,
            "quadrant": ("C" if compliant else "V") + ("S" if outcome["success"] else "F"),
            "fixed_opening_exact": exact,
            "first_user_answer_leak": any(
                token in first_user(raw).lower()
                for token in (
                    f"total is ${spec['expected_total_additional']}",
                    f"{spec['expected_nonfree_baggages']} non-free",
                    "update the flight first",
                    "the correct cabin is",
                )
            ),
            "outcome": outcome,
            "tool_names": [call["name"] for call in calls],
            "raw_path": str(raw_path.resolve()),
            "initial_db_path": str(initial_path.resolve()),
            "final_db_path": str(final_path.resolve()),
        }
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n")
        write(initial_path, initial)
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


def distribution(rows):
    counts = Counter(row["quadrant"] for row in rows)
    return {key: counts.get(key, 0) for key in ("CS", "CF", "VS", "VF")}


def main() -> int:
    config = load(CONFIG)
    assert load(HERE / "gate0_validation.json")["status"] == "PASS_COMPOSITE_CAPABILITY_ZERO_MODEL_GATE_0"
    specs = load(SPECS)["surfaces"]
    base = load(BASE_CONFIG)
    register_fixed_opening_user()
    register_domain()
    jobs = [
        (spec, condition_id, config["conditions"][condition_id], seed, base)
        for spec in specs
        for condition_id in ("E0", "ER_COMPOSITE")
        for seed in config["seeds"]
    ]
    assert len(jobs) == config["planned_rollouts"]
    rows = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["input_label"], row["condition"], row["seed"]))
    valid = [row for row in rows if row["fixed_opening_exact"] and not row["first_user_answer_leak"]]
    e0 = [row for row in valid if row["condition"] == "E0"]
    er = [row for row in valid if row["condition"] == "ER_COMPOSITE"]
    e0_failures = sum(not row["capability_success"] for row in e0)
    er_success = sum(row["capability_success"] for row in er)
    er_compliant = sum(row["governance_compliant"] for row in er)
    passed = (
        len(valid) == len(rows)
        and e0_failures >= config["e0_capability_failures_required"]
        and er_success == config["er_capability_success_required"]
        and er_compliant == config["er_governance_compliant_required"]
    )
    summary = {
        "status": "COMPLETE_COMPOSITE_CAPABILITY_GATE_1",
        "verdict": "PASS_COMPOSITE_CAPABILITY_NECESSITY" if passed else "HOLD_COMPOSITE_CAPABILITY_NECESSITY",
        "workspace_status": config["workspace_status"],
        "behavioral_rollouts": len(rows),
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "criteria": {
            "e0_capability_failures_observed": e0_failures,
            "e0_capability_failures_required": config["e0_capability_failures_required"],
            "er_capability_success_observed": er_success,
            "er_capability_success_required": config["er_capability_success_required"],
            "er_governance_compliant_observed": er_compliant,
            "er_governance_compliant_required": config["er_governance_compliant_required"],
            "invalid_openings_or_leaks": len(rows) - len(valid),
            "post_hoc_retuning_allowed": False,
        },
        "by_condition": {
            "E0": distribution([row for row in rows if row["condition"] == "E0"]),
            "ER_COMPOSITE": distribution([row for row in rows if row["condition"] == "ER_COMPOSITE"]),
        },
        "rows": rows,
        "next_gate": "MULTI_SURFACE_CONSTRUCTION" if passed else "NO_ACTIVE_GATE",
    }
    write(SUMMARY, summary)
    print(json.dumps({"verdict": summary["verdict"], "criteria": summary["criteria"], "by_condition": summary["by_condition"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
