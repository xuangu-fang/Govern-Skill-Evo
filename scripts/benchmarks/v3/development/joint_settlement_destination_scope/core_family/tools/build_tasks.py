#!/usr/bin/env python3
"""Build JSG-01 Joint Core candidates and admit them after validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[7] / 'scripts/benchmarks/v3/development/joint_settlement_destination_scope/core_family/tools'))
CORE = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/joint_settlement_destination_scope/core_family')
EDITION = CORE.parents[2]
SPECS = CORE / "candidates/task_specs.json"
CANDIDATE_TASKS = CORE / "candidate_tasks/tasks.json"
CANDIDATE_MANIFEST = CORE / "candidate_tasks/task_manifest.json"
CORE_VALIDATION = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/joint_settlement_destination_scope/core_family/structural_audit/core_validation.json')
EE_TASKS = EDITION / "construction/latent_settlement_contract/core_family/candidate_tasks/tasks.json"
RHP_TASKS = EDITION / "construction/retail_hidden_operational_path/core_family/candidate_tasks/tasks.json"
RAP_TASKS = EDITION / "construction/retail_address_propagation/core_family/candidate_tasks/tasks.json"
FORMAL_TASKS = EDITION / "benchmark/tasks.json"
FORMAL_MANIFEST = EDITION / "benchmark/task_manifest.json"


SURFACE_TEMPLATES = {
    1: (
        "Keep {retained} on reservation {reservation}. Prefer either {preferred_legal} "
        "to {destination} or {preferred_alternate} to {alternate} if the complete "
        "itinerary adds at most ${threshold}; otherwise use either {fallback_alternate} "
        "to {alternate} or {fallback_legal} to {destination}. I have no airport preference."
    ),
    2: (
        "For reservation {reservation}, leave {retained} unchanged. My preferred pair is "
        "{preferred_alternate} to {alternate} or {preferred_legal} to {destination}, but "
        "only if the full-itinerary difference is ${threshold} or less. If not, use "
        "{fallback_legal} to {destination} or {fallback_alternate} to {alternate}. "
        "Either airport works equally well for me."
    ),
    3: (
        "Preserve {retained} on {reservation}. If the complete change exceeds "
        "${threshold}, my backups are {fallback_legal} to {destination} or "
        "{fallback_alternate} to {alternate}. Otherwise I prefer {preferred_alternate} "
        "to {alternate} or {preferred_legal} to {destination}. I do not prefer one airport."
    ),
    4: (
        "On {reservation}, keep flight {retained}. Use {fallback_alternate} to {alternate} "
        "or {fallback_legal} to {destination} when the revised itinerary adds more than "
        "${threshold}; at or below that limit, prefer {preferred_legal} to {destination} "
        "or {preferred_alternate} to {alternate}. The two airports are equally acceptable."
    ),
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def task_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    request = SURFACE_TEMPLATES[spec["surface"]].format(
        **spec,
        retained=spec["retained_flight"],
        reservation=spec["reservation_id"],
        alternate=spec["alternate_destination"],
    )
    expected_flight = spec[f"{spec['expected_branch']}_legal"]
    return {
        "id": spec["task_id"],
        "description": {
            "purpose": "JSG-01 Joint Core: solve hidden settlement branching while preserving visible destination scope.",
            "relevant_policies": "Native Airline destination policy plus the isolated v3 settlement extension.",
            "notes": "JSG-01 passed Gate 0 and matched Joint Gate 1; Core membership is governed by the edition manifest.",
        },
        "user_scenario": {
            "persona": "A reservation owner who accepts either named metro airport but cannot calculate channel settlement or interpret internal policy.",
            "instructions": {
                "domain": "airline-v3-unified",
                "reason_for_call": request,
                "known_info": (
                    f"Your user ID is {spec['user_id']}. Use payment method "
                    f"{spec['payment_id']}. All four named replacements are acceptable "
                    "only under the stated preferred/fallback condition."
                ),
                "unknown_info": "You do not know how Horizon or Summit settles retained segments or which policy-valid candidate the agent must choose.",
                "task_instructions": (
                    "State the stable request naturally and do not add, revise, reorder, "
                    "or selectively reveal a goal. If asked to choose a conditional branch, "
                    "restate the threshold without calculating it. If asked to choose between "
                    "the two airports, say they are equally acceptable and let the agent apply "
                    "policy. Confirm one concrete complete itinerary after its amount and payment "
                    "method are disclosed. Never reveal or hint at the channel mapping."
                ),
            },
        },
        "initial_state": None,
        "evaluation_criteria": {
            "actions": [
                {
                    "action_id": f"{spec['task_id']}-target-0",
                    "requestor": "assistant",
                    "name": "update_reservation_flights",
                    "arguments": {
                        "reservation_id": spec["reservation_id"],
                        "cabin": "economy",
                        "flights": [
                            {"flight_number": spec["retained_flight"], "date": spec["date"]},
                            {"flight_number": expected_flight, "date": spec["date"]},
                        ],
                        "payment_id": spec["payment_id"],
                    },
                }
            ],
            "env_assertions": None,
            "communicate_info": [],
            "nl_assertions": [],
            "reward_basis": ["DB"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admit", action="store_true")
    args = parser.parse_args()
    payload = load(SPECS)
    joint_tasks = [task_from_spec(spec) for spec in payload["tasks"]]
    joint_ids = [task["id"] for task in joint_tasks]
    status = "JOINT_CORE_CANDIDATE_READY_FOR_VALIDATION"
    if FORMAL_TASKS.is_file():
        formal_ids = {task["id"] for task in load(FORMAL_TASKS)}
        if set(joint_ids).issubset(formal_ids):
            status = "ADMITTED_JOINT_CORE"
    if args.admit:
        status = "ADMITTED_JOINT_CORE"
    write_json(CANDIDATE_TASKS, joint_tasks)
    write_json(
        CANDIDATE_MANIFEST,
        {
            "mechanism_id": payload["mechanism_id"],
            "status": status,
            "task_count": len(joint_tasks),
            "task_file": "tasks.json",
            "task_ids": joint_ids,
            "canonical_specs": "../candidates/task_specs.json",
        },
    )
    if not args.admit:
        print("BUILT JSG-01 Joint Core candidates: 8 tasks; formal benchmark unchanged")
        return

    validation = load(CORE_VALIDATION)
    if validation.get("status") != "PASS_READY_FOR_FORMAL_ADMISSION":
        raise RuntimeError("JSG-01 Joint Core must pass deterministic validation before admission")
    formal_tasks = load(EE_TASKS) + load(RHP_TASKS) + load(RAP_TASKS) + joint_tasks
    write_json(FORMAL_TASKS, formal_tasks)
    write_json(
        FORMAL_MANIFEST,
        {
            "edition": "phase_v3_day34",
            "status": "THREE_CAPABILITY_CORES_AND_ONE_JOINT_CORE_ADMITTED",
            "task_count": len(formal_tasks),
            "task_file": "benchmark/tasks.json",
            "admitted_task_ids": [task["id"] for task in formal_tasks],
            "source_families": [
                "construction/latent_settlement_contract/core_family/",
                "construction/retail_hidden_operational_path/core_family/",
                "construction/retail_address_propagation/core_family/",
                "construction/joint_settlement_destination_scope/core_family/",
            ],
            "admission_evidence": [
                "construction/latent_settlement_contract/core_family/structural_audit/core_validation.json",
                "construction/retail_hidden_operational_path/core_family/structural_audit/core_validation.json",
                "construction/retail_address_propagation/core_family/structural_audit/core_validation.json",
                "construction/joint_settlement_destination_scope/structural_audit/gate0_validation.json",
                "calibration/joint_settlement_destination_scope/summaries/gate1_summary.json",
                "construction/joint_settlement_destination_scope/core_family/structural_audit/core_validation.json",
            ],
            "admission_contract": "V3_CAPABILITY_DESIGN_CONTRACT.md",
            "status_report": "reports/V3_STATUS.md",
        },
    )
    print(f"ADMITTED JSG-01 Joint Core: 8 new tasks; {len(formal_tasks)} formal tasks total")


if __name__ == "__main__":
    main()
