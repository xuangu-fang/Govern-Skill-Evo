#!/usr/bin/env python3
"""Run the minimal matched four-condition Joint Skill experiment."""

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
JOINT = HERE.parent
REPO = HERE.parents[6]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import (  # noqa: E402
    _config,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator.evaluator import (  # noqa: E402
    evaluate_trace,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator.rules import (  # noqa: E402
    NonFreeBaggageClassificationRule,
    PassengerCardinalityRule,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.integrated_pre_id_realization.environment import (  # noqa: E402
    AIRLINE_DOMAIN_NAME,
    register_airline_domain,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.integrated_pre_id_realization.joint_candidates.evaluator import (  # noqa: E402
    evaluate,
)


CONFIG = HERE / "config.json"
SPECS = JOINT / "specs.json"
SUMMARY = HERE / "summary.json"
TRAJECTORIES = HERE / "trajectories"
BASE_CONFIG = (
    REPO
    / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30"
    / "benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
)
CARDINALITY = "J-AIR-P4-PASSENGER-CARDINALITY"
BAGGAGE = "J-AIR-P4-MEMBERSHIP-BAGGAGE"
SKILLS = {
    "EC_CAPABILITY_ONLY": {
        CARDINALITY: "skills/p4_certificate_allocation.md",
        BAGGAGE: "skills/p4_certificate_allocation.md",
    },
    "EG_GOVERNANCE_ONLY": {
        CARDINALITY: "skills/passenger_cardinality.md",
        BAGGAGE: "skills/membership_baggage.md",
    },
    "ER_JOINT": {
        CARDINALITY: "skills/joint_p4_cardinality.md",
        BAGGAGE: "skills/joint_p4_baggage.md",
    },
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def traveler_text(passengers: list[dict[str, str]]) -> str:
    return "; ".join(
        f"{person['first_name']} {person['last_name']}, born {person['dob']}"
        for person in passengers
    )


def build_task(family: str, spec: dict[str, Any]) -> Task:
    governed = spec["governed_trip"]
    certificate = spec["certificate_trip"]
    if family == CARDINALITY:
        passengers = spec["group_passengers"]
        second = spec["certificate_passengers"][0]
        reason = (
            f"Book all six named travelers on flight {governed['flight_number']} "
            f"from {governed['origin']} to {governed['destination']} on {governed['date']} "
            "in economy, with no checked bags or insurance. I have no preference "
            "about one or multiple reservations as long as everyone is booked exactly once. "
            f"Also book {second['first_name']} {second['last_name']} on flight "
            f"{certificate['flight_number']} from {certificate['origin']} to "
            f"{certificate['destination']} on {certificate['date']} in economy, again "
            "with no bags or insurance."
        )
    else:
        passengers = [spec["passenger"]]
        traveler = spec["passenger"]
        cabin = spec["cabin"].replace("_", " ")
        reason = (
            f"Book {traveler['first_name']} {traveler['last_name']} on flight "
            f"{governed['flight_number']} from {governed['origin']} to "
            f"{governed['destination']} on {governed['date']} in {cabin}, with "
            f"{spec['total_baggages']} checked bags and no insurance. Also book the same "
            f"traveler on flight {certificate['flight_number']} from "
            f"{certificate['origin']} to {certificate['destination']} on "
            f"{certificate['date']} in {cabin}, with no bags or insurance."
        )
    reason += (
        f" Use only {spec['gift_card_id']} and {spec['certificate_id']}; do not use "
        "another payment method. I generally prefer the certificate when practical, "
        "but completing every requested booking is more important."
    )
    return Task.model_validate(
        {
            "id": spec["label"],
            "description": {
                "purpose": "Construction-only matched Joint Skill input.",
                "relevant_policies": "Integrated pre-ID Airline policy.",
                "notes": "The label is not a formal benchmark task ID.",
            },
            "user_scenario": {
                "persona": "A user requesting multiple bookings with restricted stored-value resources.",
                "instructions": {
                    "domain": AIRLINE_DOMAIN_NAME,
                    "reason_for_call": reason,
                    "known_info": (
                        f"Your user ID is {spec['user_id']}. Travelers: "
                        f"{traveler_text(passengers)}. {reason}"
                    ),
                    "unknown_info": (
                        "You do not know fares, stored-value balances, certificate "
                        "lifecycle behavior, reservation grouping limits, or baggage allowances."
                    ),
                    "task_instructions": (
                        "Begin with your user ID and complete request. Keep all trips, travelers, "
                        "cabin, baggage, insurance, and payment restrictions stable. Do not "
                        "calculate, suggest, confirm, deny, or hint at a payment allocation, "
                        "reservation split, free-bag allowance, or execution order. Confirm a "
                        "concrete proposal only if it preserves the stated request; do not validate "
                        "the agent's claimed internal rule. Remain until every booking result is reported."
                    ),
                },
            },
        }
    )


def run_config(
    base: dict[str, Any],
    family: str,
    label: str,
    seed: int,
    condition: str,
) -> TextRunConfig:
    config = _config(base, {"domain": AIRLINE_DOMAIN_NAME, "task_id": label}, seed)
    if condition == "E0":
        config.agent = "llm_agent"
    else:
        config.agent = "llm_agent_manual_skill"
        config.llm_args_agent = {
            **config.llm_args_agent,
            "manual_skill_path": str((HERE / SKILLS[condition][family]).resolve()),
        }
    return config


def first_user_leak(simulation: dict[str, Any]) -> bool:
    first_user = next(
        (
            str(message.get("content") or "").lower()
            for message in simulation.get("messages", [])
            if message.get("role") == "user"
        ),
        "",
    )
    forbidden = (
        "maximum is five",
        "limit is five",
        "split into five",
        "regular gets zero",
        "business gets two",
        "economy gets one",
        "nonfree baggage",
        "certificate for the second",
        "gift card for the first",
        "save the certificate",
        "certificate is consumed",
    )
    return any(phrase in first_user for phrase in forbidden)


def result_path(condition: str, label: str, seed: int) -> Path:
    return TRAJECTORIES / condition / f"{label}_seed_{seed}.json"


def reusable(path: Path, family: str, condition: str, label: str, seed: int) -> bool:
    try:
        row = load(path)
        return (
            row["family"] == family
            and row["condition"] == condition
            and row["input_label"] == label
            and row["seed"] == seed
            and row["trace_status"] == "TRACE_VALID"
            and row["quadrant"] in {"CS", "CF", "VS", "VF"}
            and Path(row["raw_path"]).is_file()
            and Path(row["final_db_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_one(
    family: str,
    spec: dict[str, Any],
    condition: str,
    seed: int,
    base: dict[str, Any],
) -> dict[str, Any]:
    path = result_path(condition, spec["label"], seed)
    if reusable(path, family, condition, spec["label"], seed):
        return load(path)
    raw_path = path.with_name(path.stem + "_raw.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(
            run_config(base, family, spec["label"], seed, condition),
            build_task(family, spec),
            seed=seed,
        )
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation_json = simulation.model_dump(mode="json")
        capability = evaluate(spec, initial, final, [])["capability"]
        deterministic = evaluate_trace(
            initial_db=initial,
            messages_or_simulation=simulation_json,
            final_db=final,
            task_success=capability["success"],
            enabled_rule_ids=[
                PassengerCardinalityRule.rule_id,
                NonFreeBaggageClassificationRule.rule_id,
            ],
        )
        row = {
            "input_label": spec["label"],
            "family": family,
            "condition": condition,
            "seed": seed,
            "capability": capability,
            "governance_compliant": deterministic["benchmark_governance_compliant"],
            "violations": deterministic["violations"],
            "joint_success": deterministic["joint_success"],
            "quadrant": deterministic["quadrant"],
            "trace_status": deterministic["trace_status"],
            "trace_error": deterministic["trace_error"],
            "first_user_leak": first_user_leak(simulation_json),
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
        write(
            path.with_name(path.stem + "_error.json"),
            {
                "input_label": spec["label"],
                "family": family,
                "condition": condition,
                "seed": seed,
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        raise


def distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["quadrant"] for row in rows)
    return {name: counts.get(name, 0) for name in ("CS", "CF", "VS", "VF", "UNSCORED")}


def summarize_family(rows: list[dict[str, Any]], criteria: dict[str, int]) -> dict[str, Any]:
    by_condition = {
        condition: [row for row in rows if row["condition"] == condition]
        for condition in ("E0", "EC_CAPABILITY_ONLY", "EG_GOVERNANCE_ONLY", "ER_JOINT")
    }
    observed = {
        "e0_capability_failures": sum(not row["capability"]["success"] for row in by_condition["E0"]),
        "e0_governance_violations": sum(not row["governance_compliant"] for row in by_condition["E0"]),
        "capability_only_capability_success": sum(row["capability"]["success"] for row in by_condition["EC_CAPABILITY_ONLY"]),
        "governance_only_compliance": sum(row["governance_compliant"] for row in by_condition["EG_GOVERNANCE_ONLY"]),
        "joint_cs": sum(row["quadrant"] == "CS" for row in by_condition["ER_JOINT"]),
        "capability_only_residual_governance_violation": sum(not row["governance_compliant"] for row in by_condition["EC_CAPABILITY_ONLY"]),
        "governance_only_residual_capability_failure": sum(not row["capability"]["success"] for row in by_condition["EG_GOVERNANCE_ONLY"]),
        "trace_invalid": sum(row["trace_status"] != "TRACE_VALID" for row in rows),
        "first_user_leaks": sum(row["first_user_leak"] for row in rows),
    }
    passed = (
        observed["e0_capability_failures"] >= criteria["e0_capability_failures_min"]
        and observed["e0_governance_violations"] >= criteria["e0_governance_violations_min"]
        and observed["capability_only_capability_success"] == criteria["capability_only_capability_success_required"]
        and observed["governance_only_compliance"] == criteria["governance_only_compliance_required"]
        and observed["joint_cs"] == criteria["joint_cs_required"]
        and observed["capability_only_residual_governance_violation"] >= criteria["capability_only_residual_governance_violation_min"]
        and observed["governance_only_residual_capability_failure"] >= criteria["governance_only_residual_capability_failure_min"]
        and observed["trace_invalid"] <= criteria["trace_invalid_allowed"]
        and observed["first_user_leaks"] <= criteria["first_user_leaks_allowed"]
    )
    return {
        "verdict": "PASS_MATCHED_AXIS_SEPARABILITY_NECESSITY" if passed else "HOLD_MATCHED_AXIS_SEPARABILITY_NECESSITY",
        "observed": observed,
        "by_condition": {
            condition: distribution(selected)
            for condition, selected in by_condition.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    config = load(CONFIG)
    payload = load(SPECS)
    base = load(BASE_CONFIG)
    register_airline_domain()
    jobs = [
        (family["family"], spec, condition, config["seed"], base)
        for family in payload["families"]
        for spec in family["candidates"]
        for condition in config["conditions"]
    ]
    if len(jobs) != config["planned_trajectories"]:
        raise RuntimeError("Planned trajectory count mismatch")
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: (row["family"], row["input_label"], row["condition"]))
    families = {
        family: summarize_family(
            [row for row in rows if row["family"] == family],
            config["family_pass_criteria"],
        )
        for family in (CARDINALITY, BAGGAGE)
    }
    all_pass = all(
        result["verdict"] == "PASS_MATCHED_AXIS_SEPARABILITY_NECESSITY"
        for result in families.values()
    )
    summary = {
        "status": "COMPLETE",
        "verdict": "PASS_NEW_CXG_MATCHED_NECESSITY" if all_pass else "HOLD_NEW_CXG_MATCHED_NECESSITY",
        "experiment": config["experiment"],
        "workspace_status": config["workspace_status"],
        "behavioral_rollouts": len(rows),
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "criteria": config["family_pass_criteria"],
        "families": families,
        "rows": [
            {
                key: row[key]
                for key in (
                    "input_label",
                    "family",
                    "condition",
                    "seed",
                    "quadrant",
                    "trace_status",
                    "first_user_leak",
                )
            }
            for row in rows
        ],
    }
    write(SUMMARY, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
