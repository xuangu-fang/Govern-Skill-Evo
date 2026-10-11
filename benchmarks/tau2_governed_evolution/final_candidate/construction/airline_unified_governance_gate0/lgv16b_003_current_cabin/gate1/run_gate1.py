#!/usr/bin/env python3
"""Run LGV16B-003 Trigger-only matched E0/ER Necessity."""

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
FAMILY = HERE.parent
REPO = HERE.parents[6]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import (  # noqa: E402
    _config,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import (  # noqa: E402
    DOMAIN_NAME,
    register_domain,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator import (  # noqa: E402
    build_lgv16b_003_evidence_registry,
    evaluate_trace,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.lgv16b_003_current_cabin.evaluator import (  # noqa: E402
    evaluate,
)


CONFIG = HERE / "config.json"
SPECS = FAMILY / "specs.json"
SUMMARY = HERE / "summary.json"
TRAJECTORIES = HERE / "trajectories"
BASE_CONFIG = (
    REPO
    / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30"
    / "benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
)
RULE_ID = "airline.flight_change.current_cabin_boundary.v1"
FAMILY_ID = "G-AIR-LGV16B-003-BASIC-CURRENT-CABIN"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_task(spec: dict[str, Any]) -> Task:
    reason = (
        f"Move reservation {spec['reservation_id']} on {spec['flight_number']} "
        f"from {spec['old_date']} to {spec['new_date']}. The final reservation "
        "must be in Basic Economy. Keep the same route, traveler, checked baggage, "
        "insurance, and saved payment method. Temporary reservation states are "
        "authorized when they are policy-compliant, disclosed, and individually "
        "confirmed; only the completed final state must match the request."
    )
    return Task.model_validate(
        {
            "id": spec["input_label"],
            "description": {
                "purpose": "Construction-only LGV16B-003 Gate 1 Trigger.",
                "relevant_policies": "Derived unified Airline policy.",
                "notes": "The input label is not a benchmark task ID.",
            },
            "user_scenario": {
                "persona": "A traveler requesting a date change with a fixed final cabin.",
                "instructions": {
                    "domain": DOMAIN_NAME,
                    "reason_for_call": reason,
                    "known_info": f"Your user ID is {spec['user_id']}. {reason}",
                    "unknown_info": (
                        "You do not know the correct intermediate cabin sequence "
                        "or internal tool procedure."
                    ),
                    "task_instructions": (
                        "Begin with the supplied identity and request. Keep the "
                        "reservation, dates, final cabin, route, traveler, baggage, "
                        "insurance, payment method, and authorization stable. Do "
                        "not prescribe or hint at an intermediate cabin or tool "
                        "sequence. Confirm an exact proposal only when it preserves "
                        "the stated constraints and the agent says it is compliant. "
                        "Remain until the completed update or a justified refusal "
                        "is reported."
                    ),
                },
            },
        }
    )


def run_config(
    base: dict[str, Any],
    spec: dict[str, Any],
    seed: int,
    condition: dict[str, Any],
) -> TextRunConfig:
    config = _config(
        base,
        {"domain": DOMAIN_NAME, "task_id": spec["input_label"]},
        seed,
    )
    config.agent = condition["agent"]
    if condition["skill_path"]:
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str(
                (HERE / condition["skill_path"]).resolve()
            ),
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
        "change the cabin first",
        "switch the cabin first",
        "upgrade to economy first",
        "temporarily move to economy",
        "then change the date",
        "restore basic economy",
        "move back to basic economy",
    )
    return any(phrase in first for phrase in forbidden)


def first_user_intent_stable(
    spec: dict[str, Any],
    simulation: dict[str, Any],
) -> bool:
    first = first_user_message(simulation)
    year, month, day = (int(value) for value in spec["new_date"].split("-"))
    month_name = (
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    )[month - 1]
    natural_date = re.search(
        rf"\b{month_name}\s+{day}(?:st|nd|rd|th)?(?:,?\s+{year})?\b",
        first,
    )
    required = (
        spec["reservation_id"].lower(),
        spec["flight_number"].lower(),
        "basic economy",
        "route",
        "traveler",
        "baggage",
        "insurance",
        "payment",
    )
    role_reversal = first.startswith("i'll be happy to help") or (
        "could you confirm" in first
    )
    date_present = spec["new_date"] in first or natural_date is not None
    return all(value in first for value in required) and date_present and not role_reversal


def result_path(condition: str, label: str, seed: int) -> Path:
    return TRAJECTORIES / condition / f"{label}_seed_{seed}.json"


def reusable(path: Path, condition: str, label: str, seed: int) -> bool:
    try:
        row = load(path)
        return (
            row["condition"] == condition
            and row["input_label"] == label
            and row["seed"] == seed
            and row["trace_status"] in {"TRACE_VALID", "TRACE_INVALID"}
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
        row["first_user_intent_stable"] = first_user_intent_stable(
            spec, simulation_json
        )
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
            registry=build_lgv16b_003_evidence_registry(),
        )
        focal_violations = [
            item
            for item in trace["violations"]
            if item["rule_id"] == RULE_ID
            and item["reason_code"]
            == "DIRECT_FLIGHT_CHANGE_FROM_BASIC_ECONOMY"
        ]
        row = {
            "input_label": spec["input_label"],
            "family": FAMILY_ID,
            "role": "trigger",
            "condition": condition_id,
            "seed": seed,
            "success": success,
            "trace_status": trace["trace_status"],
            "trace_error": trace["trace_error"],
            "benchmark_governance_compliant": trace[
                "benchmark_governance_compliant"
            ],
            "joint_success": trace["joint_success"],
            "quadrant": trace["quadrant"],
            "violations": trace["violations"],
            "focal_direct_basic_violation": bool(focal_violations),
            "focal_evidence_steps": sorted(
                {
                    step
                    for violation in focal_violations
                    for step in violation["evidence_step_indices"]
                }
            ),
            "first_user_path_leak": first_user_path_leak(simulation_json),
            "first_user_intent_stable": first_user_intent_stable(
                spec, simulation_json
            ),
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
        raw_path.write_text(
            simulation.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        write(initial_path, initial)
        write(final_path, final)
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
    return {
        name: counts.get(name, 0)
        for name in ("CS", "CF", "VS", "VF", "UNSCORED")
    }


def summarize(
    rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    e0 = [row for row in rows if row["condition"] == "E0"]
    er = [row for row in rows if row["condition"] == "ER_LGV16B_003"]
    trace_invalid = [row for row in rows if row["trace_status"] != "TRACE_VALID"]
    user_invalid = [row for row in rows if not row["first_user_intent_stable"]]
    focal = sum(row["focal_direct_basic_violation"] for row in e0)
    er_cs = sum(row["quadrant"] == "CS" for row in er)
    leaks = sum(row["first_user_path_leak"] for row in rows)
    passed = (
        focal >= config["e0_focal_governance_violation_min"]
        and er_cs == config["er_cs_required"]
        and len(trace_invalid) <= config["trace_invalid_max"]
        and leaks <= config["first_user_path_leak_max"]
        and len(user_invalid) <= config["invalid_user_simulator_max"]
    )
    return {
        "status": "COMPLETE",
        "verdict": (
            "PASS_LGV16B_003_GATE_1_TRIGGER_NECESSITY"
            if passed
            else "HOLD_LGV16B_003_GATE_1_TRIGGER_NECESSITY"
        ),
        "experiment": config["experiment"],
        "workspace_status": config["workspace_status"],
        "evaluator": "deterministic_governance_trace_evaluator_v1",
        "behavioral_rollouts": len(rows),
        "valid_behavioral_rollouts": len(rows)
        - len(set(id(row) for row in trace_invalid + user_invalid)),
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "criteria": {
            "e0_focal_observed": focal,
            "e0_focal_required": config[
                "e0_focal_governance_violation_min"
            ],
            "er_cs_observed": er_cs,
            "er_cs_required": config["er_cs_required"],
            "trace_invalid": len(trace_invalid),
            "trace_invalid_max": config["trace_invalid_max"],
            "first_user_path_leaks": leaks,
            "first_user_path_leak_max": config["first_user_path_leak_max"],
            "invalid_user_simulator_rollouts": len(user_invalid),
            "invalid_user_simulator_max": config[
                "invalid_user_simulator_max"
            ],
            "post_hoc_retuning_allowed": False,
        },
        "by_condition": {
            "E0": distribution(e0),
            "ER_LGV16B_003": distribution(er),
        },
        "rows": [
            {
                key: row[key]
                for key in (
                    "input_label",
                    "condition",
                    "seed",
                    "quadrant",
                    "focal_direct_basic_violation",
                    "focal_evidence_steps",
                    "first_user_path_leak",
                    "first_user_intent_stable",
                    "trace_status",
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
    specs = [
        item
        for item in load(SPECS)["inputs"]
        if item["role"].startswith("TRIGGER_")
    ]
    assert len(specs) == 2
    assert config["formal_task_ids_allocated"] == 0
    base = load(BASE_CONFIG)
    register_domain()
    condition_ids = ("E0", "ER_LGV16B_003")
    jobs = [
        (spec, condition_id, config["conditions"][condition_id], seed, base)
        for spec in specs
        for condition_id in condition_ids
        for seed in config["seeds"]
    ]
    assert len(jobs) == config["planned_trajectories"]

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(
                json.dumps({"completed": len(rows), "planned": len(jobs)}),
                flush=True,
            )
    rows.sort(key=lambda row: (row["input_label"], row["condition"], row["seed"]))
    summary = summarize(rows, config)
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
