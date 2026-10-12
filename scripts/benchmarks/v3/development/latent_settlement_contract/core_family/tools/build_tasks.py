#!/usr/bin/env python3
"""Build the eight admitted EE-01 Capability Core tasks from canonical specs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[7] / 'scripts/benchmarks/v3/development/latent_settlement_contract/core_family/tools'))
CORE = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/latent_settlement_contract/core_family')
PRIMITIVE = CORE.parent
EDITION = PRIMITIVE.parents[1]
SPECS = CORE / "candidates/task_specs.json"
CANDIDATE_TASKS = CORE / "candidate_tasks/tasks.json"
CANDIDATE_MANIFEST = CORE / "candidate_tasks/task_manifest.json"
RHP_TASKS = (
    EDITION
    / "construction/retail_hidden_operational_path/core_family/candidate_tasks/tasks.json"
)
FORMAL_TASKS = EDITION / "benchmark/tasks.json"
FORMAL_MANIFEST = EDITION / "benchmark/task_manifest.json"


SURFACE_TEMPLATES = {
    1: "Keep {retained} as the first segment of reservation {reservation}. For the second segment, use {preferred} if the additional charge for the complete itinerary is at most ${threshold}; otherwise use {fallback}.",
    2: "On reservation {reservation}, leave the first leg {retained} untouched. My preferred replacement is {preferred}, but only when the full-itinerary change costs no more than ${threshold}. If it exceeds that limit, book {fallback} instead.",
    3: "Please preserve {retained} on reservation {reservation}. Replace only the onward leg: choose {preferred} when the complete revised itinerary adds ${threshold} or less, and choose {fallback} when it adds more.",
    4: "For {reservation}, I am keeping flight {retained}. I want {preferred} for the remaining leg provided the total itinerary price difference does not exceed ${threshold}; otherwise my accepted backup is {fallback}.",
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def task_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    request = SURFACE_TEMPLATES[spec["surface"]].format(
        retained=spec["retained_flight"],
        reservation=spec["reservation_id"],
        preferred=spec["preferred_flight"],
        fallback=spec["fallback_flight"],
        threshold=spec["threshold"],
    )
    return {
        "id": spec["task_id"],
        "description": {
            "purpose": "EE-01 Capability Core: infer channel-conditioned settlement before an irreversible flight change.",
            "relevant_policies": "Native Airline policy plus the isolated v3 settlement-contract extension.",
            "notes": "Formally admitted after EE-01 Gate 0 and matched Gate 1 Reference-Skill necessity passed.",
        },
        "user_scenario": {
            "persona": "The user owns the reservation and knows the conditional travel preference, but not the ticketing channel's internal settlement calculation.",
            "instructions": {
                "domain": "airline-v3-unified",
                "reason_for_call": request,
                "known_info": (
                    f"Your user ID is {spec['user_id']}. Use payment method "
                    f"{spec['payment_id']}. The retained flight and both acceptable "
                    "replacement candidates are exactly those in your request."
                ),
                "unknown_info": "You do not know how Horizon or Summit ticketing channels settle retained versus replacement segments.",
                "task_instructions": (
                    "State the request and identifiers naturally. If asked to choose between "
                    "the preferred and fallback flights, restate the conditional rule; do not "
                    "calculate the settlement or choose for the agent. Confirm once when the "
                    "agent presents a complete itinerary that keeps the retained flight and uses "
                    "either named replacement. Reject only a proposal that drops the retained "
                    "flight, uses another flight, or changes an explicit fact. Never reveal, "
                    "infer, confirm, deny, or hint at the hidden channel mapping. Remain until "
                    "the agent reports completion."
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
                            {
                                "flight_number": spec["retained_flight"],
                                "date": spec["date"],
                            },
                            {
                                "flight_number": spec["expected_flight"],
                                "date": spec["date"],
                            },
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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    payload = load(SPECS)
    tasks = [task_from_spec(spec) for spec in payload["tasks"]]
    ids = [task["id"] for task in tasks]
    rhp_tasks = load(RHP_TASKS)
    formal_tasks = tasks + rhp_tasks
    candidate_manifest = {
        "mechanism_id": payload["mechanism_id"],
        "status": "ADMITTED_CAPABILITY_CORE",
        "task_count": len(tasks),
        "task_file": "tasks.json",
        "task_ids": ids,
        "canonical_specs": "../candidates/task_specs.json",
    }
    formal_manifest = {
        "edition": "phase_v3_day34",
        "status": "EE_01_AND_RHP_01_CAPABILITY_CORES_ADMITTED",
        "task_count": len(formal_tasks),
        "task_file": "benchmark/tasks.json",
        "admitted_task_ids": [task["id"] for task in formal_tasks],
        "source_families": [
            "construction/latent_settlement_contract/core_family/",
            "construction/retail_hidden_operational_path/core_family/",
        ],
        "admission_evidence": [
            "construction/latent_settlement_contract/structural_audit/gate0_validation.json",
            "calibration/latent_settlement_contract/summaries/gate1_summary.json",
            "construction/latent_settlement_contract/core_family/structural_audit/core_validation.json",
            "construction/retail_hidden_operational_path/structural_audit/gate0_validation.json",
            "calibration/retail_hidden_operational_path/summaries/gate1_summary.json",
            "construction/retail_hidden_operational_path/core_family/structural_audit/core_validation.json",
        ],
        "admission_contract": "V3_CAPABILITY_DESIGN_CONTRACT.md",
        "status_report": "reports/V3_STATUS.md",
    }
    write_json(CANDIDATE_TASKS, tasks)
    write_json(CANDIDATE_MANIFEST, candidate_manifest)
    write_json(FORMAL_TASKS, formal_tasks)
    write_json(FORMAL_MANIFEST, formal_manifest)
    print(f"BUILT EE-01 Core: 8 EE tasks; {len(formal_tasks)} formal tasks total")


if __name__ == "__main__":
    main()
