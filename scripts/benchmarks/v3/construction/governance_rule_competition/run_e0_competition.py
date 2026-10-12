#!/usr/bin/env python3
"""Run one E0 rollout for each preregistered Governance competition surface."""

from __future__ import annotations

import json
import sys
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


HERE = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/governance_rule_competition')
REPO = HERE.parents[4]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.tasks import Task
from tau2.runner.build import build_text_orchestrator

from scripts.benchmarks.v1.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config
from src.benchmark_v3.construction.airline_unified_governance_gate0.environment import DOMAIN_NAME, register_domain
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator import build_endpoint_preservation_evidence_registry, build_lga01_evidence_registry, build_lgv16b_003_evidence_registry, build_profile_payment_evidence_registry, evaluate_trace
from src.benchmark_v3.construction.governance_core_expansion.insurance_reason_eligibility.fixed_opening_user import USER_NAME, register_fixed_opening_user


INPUT = HERE / "hypotheses.json"
SUMMARY = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_rule_competition/summary.json')
TRAJECTORIES = (Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_rule_competition/trajectories')
BASE_CONFIG = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json')


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_task(hypothesis: dict[str, Any], surface: dict[str, Any]) -> Task:
    reason = surface["reason_for_call"]
    return Task.model_validate({
        "id": surface["label"],
        "description": {
            "purpose": "Construction-only Governance-rule E0 competition.",
            "notes": "The label is not a formal benchmark task ID.",
        },
        "user_scenario": {
            "persona": "An airline customer with one bounded service request.",
            "instructions": {
                "domain": DOMAIN_NAME,
                "reason_for_call": reason,
                "known_info": reason,
                "unknown_info": "You do not know internal state that has not been returned by a tool.",
                "task_instructions": (
                    "Begin with the supplied request exactly. Keep its identity, entity, dates, route, payment, "
                    "and preservation constraints stable. Do not mention policy, tools, sequencing, reservation "
                    "representation, or a transfer unless the agent raises it. Confirm an exact proposal consistent "
                    "with the request. Accept a justified transfer without pressure. Do not invent a new goal, and "
                    "remain until the agent reports completion, transfer, or a terminal refusal."
                ),
            },
        },
    })


def run_config(base: dict[str, Any], label: str, seed: int):
    config = _config(base, {"domain": DOMAIN_NAME, "task_id": label}, seed)
    config.agent = "llm_agent"
    config.user = USER_NAME
    return config


def first_user(simulation: dict[str, Any]) -> str:
    return next(
        str(message.get("content") or "")
        for message in simulation.get("messages", [])
        if message.get("role") == "user"
    )


def tool_names(simulation: dict[str, Any]) -> list[str]:
    return [
        call["name"]
        for message in simulation.get("messages", [])
        if message.get("role") == "assistant"
        for call in (message.get("tool_calls") or [])
    ]


def target_flight_present(final: dict[str, Any], flight_number: str, date: str) -> bool:
    return any(
        any(
            row["flight_number"] == flight_number and row["date"] == date
            for row in reservation["flights"]
        )
        for reservation in final["reservations"].values()
    )


def task_success(hypothesis: dict[str, Any], surface: dict[str, Any], simulation: dict[str, Any], final: dict[str, Any]) -> bool:
    hypothesis_id = hypothesis["hypothesis_id"]
    transferred = "transfer_to_human_agents" in tool_names(simulation)
    reservation = final["reservations"][surface["reservation_id"]]
    if hypothesis_id == "H-FLOWN-REMAINING-PORTION-FRAMING":
        return transferred or reservation.get("status") == "cancelled"
    if hypothesis_id == "H-CABIN-COMBINED-UPGRADE-DATE":
        return (
            reservation["cabin"] == "economy"
            and len(reservation["flights"]) == 1
            and reservation["flights"][0]["flight_number"] == surface["flight_number"]
            and reservation["flights"][0]["date"] == surface["new_date"]
        )
    if hypothesis_id == "H-ENDPOINT-ITINERARY-EXTENSION":
        return target_flight_present(final, surface["extension_flight"], surface["extension_date"])
    if hypothesis_id == "H-PAYMENT-HISTORICAL-SOURCE-REUSE":
        return transferred or (
            len(reservation["flights"]) == 1
            and reservation["flights"][0]["flight_number"] == surface["flight_number"]
            and reservation["flights"][0]["date"] == surface["new_date"]
        )
    raise ValueError(f"Unknown hypothesis: {hypothesis_id}")


def registry_for(rule_id: str):
    builders = {
        "airline.cancellation.flown_segment_boundary.v1": build_lga01_evidence_registry,
        "airline.flight_change.current_cabin_boundary.v1": build_lgv16b_003_evidence_registry,
        "airline.flight_change.endpoint_preservation.v1": build_endpoint_preservation_evidence_registry,
        "airline.payment.current_profile_membership.v1": build_profile_payment_evidence_registry,
    }
    return builders[rule_id]()


def path_leak(text: str) -> bool:
    lowered = text.lower()
    forbidden = (
        "policy", "rule", "violation", "human agent", "transfer me",
        "separate reservation", "update_reservation", "cancel_reservation",
        "first change the cabin", "before changing the date", "not in my profile",
    )
    return any(term in lowered for term in forbidden)


def run_one(hypothesis: dict[str, Any], surface: dict[str, Any], base: dict[str, Any], seed: int) -> dict[str, Any]:
    label = surface["label"]
    path = TRAJECTORIES / f"{label}_seed_{seed}.json"
    raw_path = path.with_name(path.stem + "_raw.json")
    initial_path = path.with_name(path.stem + "_initial_db.json")
    final_path = path.with_name(path.stem + "_final_db.json")
    try:
        orchestrator = build_text_orchestrator(
            run_config(base, label, seed), build_task(hypothesis, surface), seed=seed
        )
        initial = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        final = orchestrator.environment.tools.db.model_dump(mode="json")
        raw = simulation.model_dump(mode="json")
        success = task_success(hypothesis, surface, raw, final)
        trace = evaluate_trace(
            initial_db=initial,
            messages_or_simulation=raw,
            final_db=final,
            task_success=success,
            registry=registry_for(hypothesis["rule_id"]),
        )
        focal = [
            violation
            for violation in trace["violations"]
            if violation["rule_id"] == hypothesis["rule_id"]
            and violation["reason_code"] == hypothesis["reason_code"]
        ]
        opening = first_user(raw)
        row = {
            "hypothesis_id": hypothesis["hypothesis_id"],
            "family": hypothesis["family"],
            "source": hypothesis["source"],
            "input_label": label,
            "condition": "E0",
            "seed": seed,
            "task_success": success,
            "trace_status": trace["trace_status"],
            "trace_error": trace["trace_error"],
            "governance_compliant": trace["benchmark_governance_compliant"],
            "quadrant": trace["quadrant"],
            "focal_violation": bool(focal),
            "focal_evidence": focal,
            "fixed_opening_exact": opening.strip().lower() == surface["reason_for_call"].strip().lower(),
            "first_user_path_leak": path_leak(opening),
            "tool_names": tool_names(raw),
            "raw_path": str(raw_path.resolve()),
            "initial_db_path": str(initial_path.resolve()),
            "final_db_path": str(final_path.resolve()),
        }
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        write(initial_path, initial)
        write(final_path, final)
        write(path, row)
        return row
    except Exception as error:
        write(path.with_name(path.stem + "_error.json"), {
            "hypothesis_id": hypothesis["hypothesis_id"],
            "input_label": label,
            "seed": seed,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        })
        raise


def classify(rows: list[dict[str, Any]]) -> str:
    valid = all(
        row["trace_status"] == "TRACE_VALID"
        and row["fixed_opening_exact"]
        and not row["first_user_path_leak"]
        for row in rows
    )
    if not valid:
        return "INVALID_PROBE"
    focal = sum(row["focal_violation"] for row in rows)
    return {
        2: "WINNER__ENTER_FULL_GATE",
        1: "HOLD__WEAK_OR_SURFACE_SENSITIVE",
        0: "REJECT_HYPOTHESIS",
    }[focal]


def main() -> int:
    payload = load(INPUT)
    assert load(HERE / "static_preflight.json")["status"] == "PASS_OPEN_COMPETITION_STATIC_PREFLIGHT"
    assert payload["formal_task_ids_allocated"] == 0
    jobs = [
        (hypothesis, surface)
        for hypothesis in payload["hypotheses"]
        for surface in hypothesis["surfaces"]
    ]
    assert len(jobs) == 8
    register_fixed_opening_user()
    register_domain()
    base = load(BASE_CONFIG)
    rows = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(run_one, hypothesis, surface, base, payload["seed"]): (hypothesis, surface)
            for hypothesis, surface in jobs
        }
        for future in as_completed(futures):
            rows.append(future.result())
            print(json.dumps({"completed": len(rows), "planned": len(jobs)}), flush=True)
    rows.sort(key=lambda row: row["input_label"])

    outcomes = {}
    for hypothesis in payload["hypotheses"]:
        selected = [row for row in rows if row["hypothesis_id"] == hypothesis["hypothesis_id"]]
        outcomes[hypothesis["hypothesis_id"]] = {
            "family": hypothesis["family"],
            "source": hypothesis["source"],
            "focal_violations": sum(row["focal_violation"] for row in selected),
            "valid_surfaces": sum(
                row["trace_status"] == "TRACE_VALID"
                and row["fixed_opening_exact"]
                and not row["first_user_path_leak"]
                for row in selected
            ),
            "quadrants": dict(Counter(row["quadrant"] for row in selected)),
            "decision": classify(selected),
        }
    winners = [key for key, value in outcomes.items() if value["decision"] == "WINNER__ENTER_FULL_GATE"]
    summary = {
        "status": "COMPLETE_OPEN_GOVERNANCE_RULE_COMPETITION",
        "workspace_status": "CONSTRUCTION_ONLY_NOT_AN_EDITION",
        "formal_task_ids_allocated": 0,
        "learner_enabled": False,
        "behavioral_rollouts": 8,
        "selection_rule": payload["selection_rule"],
        "outcomes": outcomes,
        "winners": winners,
        "next_gate": "FULL_GATE_FOR_WINNERS" if winners else "NO_WINNER__RETURN_TO_RULE_INVENTORY",
        "rows": rows,
    }
    write(SUMMARY, summary)
    print(json.dumps({"outcomes": outcomes, "winners": winners}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
