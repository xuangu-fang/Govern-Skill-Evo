#!/usr/bin/env python3
"""Build RAP-01 Core candidates and optionally admit them after validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[7] / 'scripts/benchmarks/v3/development/retail_address_propagation/core_family/tools'))
CORE = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/retail_address_propagation/core_family')
PRIMITIVE = CORE.parent
EDITION = PRIMITIVE.parents[1]
SPECS = CORE / "candidates/task_specs.json"
CANDIDATE_TASKS = CORE / "candidate_tasks/tasks.json"
CANDIDATE_MANIFEST = CORE / "candidate_tasks/task_manifest.json"
CORE_VALIDATION = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/retail_address_propagation/core_family/structural_audit/core_validation.json')
EE_TASKS = EDITION / "construction/latent_settlement_contract/core_family/candidate_tasks/tasks.json"
RHP_TASKS = EDITION / "construction/retail_hidden_operational_path/core_family/candidate_tasks/tasks.json"
FORMAL_TASKS = EDITION / "benchmark/tasks.json"
FORMAL_MANIFEST = EDITION / "benchmark/task_manifest.json"


SURFACE_TEMPLATES = {
    1: "Send pending order {order} to {order_address}. Also change my default profile address to {profile_address}.",
    2: "For pending order {order}, use {order_address} as its shipping destination. Separately, update my default profile address to {profile_address}.",
    3: "The delivery address for pending order {order} should become {order_address}. I also need {profile_address} saved as my default profile address.",
    4: "Please update pending order {order} so it ships to {order_address}. In addition, set my default profile address to {profile_address}.",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def address_text(address: dict[str, str]) -> str:
    pieces = [address["address1"]]
    if address["address2"]:
        pieces.append(address["address2"])
    pieces.extend(
        [address["city"], address["state"], address["zip"], address["country"]]
    )
    return ", ".join(pieces)


def address_action(name: str, spec: dict[str, Any], target: str) -> dict[str, Any]:
    address = spec[f"{target}_address"]
    identity = (
        {"order_id": spec["order_id"]}
        if target == "order"
        else {"user_id": spec["user_id"]}
    )
    return {
        "action_id": f"{spec['task_id']}-{target}",
        "requestor": "assistant",
        "name": name,
        "arguments": {**identity, **address},
    }


def task_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    request = SURFACE_TEMPLATES[spec["surface"]].format(
        order=spec["order_id"],
        order_address=address_text(spec["order_address"]),
        profile_address=address_text(spec["profile_address"]),
    )
    return {
        "id": spec["task_id"],
        "description": {
            "purpose": "RAP-01 Capability Core: preserve two distinct address goals under a hidden contract-conditioned propagation rule.",
            "relevant_policies": "Native Retail policy plus the isolated v3 address synchronization extension.",
            "notes": "RAP-01 passed Gate 0 and Gate 1; Core membership is governed by the edition manifest.",
        },
        "user_scenario": {
            "persona": "A customer with a stable temporary order destination and a different long-term profile address.",
            "instructions": {
                "domain": "retail-v3-unified",
                "reason_for_call": request,
                "known_info": (
                    f"Your name is {spec['first_name']} {spec['last_name']}, your email is "
                    f"{spec['email']}, and your current authentication ZIP is 02108. "
                    "Both requested addresses are required and remain unchanged."
                ),
                "unknown_info": "You do not know the internal propagation behavior of cedar or orbit contracts.",
                "task_instructions": (
                    "State the order-address goal before the profile-address goal. Do not "
                    "add, remove, revise, reorder, or selectively reveal either goal. "
                    "Confirm both exact changes when proposed. If asked which write should "
                    "happen first or what the contract label means, say you do not know the "
                    "internal synchronization behavior and do not choose for the agent. "
                    "Never reveal, infer, confirm, deny, or hint at the contract mapping."
                ),
            },
        },
        "initial_state": None,
        "evaluation_criteria": {
            "actions": [
                address_action("modify_pending_order_address", spec, "order"),
                address_action("modify_user_address", spec, "profile"),
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admit", action="store_true")
    args = parser.parse_args()
    payload = load(SPECS)
    rap_tasks = [task_from_spec(spec) for spec in payload["tasks"]]
    rap_ids = [task["id"] for task in rap_tasks]
    already_admitted = False
    if FORMAL_TASKS.is_file():
        formal_ids = {task["id"] for task in load(FORMAL_TASKS)}
        already_admitted = set(rap_ids).issubset(formal_ids)
    status = (
        "ADMITTED_CAPABILITY_CORE"
        if args.admit or already_admitted
        else "CORE_CANDIDATE_READY_FOR_VALIDATION"
    )
    write_json(CANDIDATE_TASKS, rap_tasks)
    write_json(
        CANDIDATE_MANIFEST,
        {
            "mechanism_id": payload["mechanism_id"],
            "status": status,
            "task_count": len(rap_tasks),
            "task_file": "tasks.json",
            "task_ids": rap_ids,
            "canonical_specs": "../candidates/task_specs.json",
        },
    )
    if not args.admit:
        print("BUILT RAP-01 Core candidates: 8 tasks; formal benchmark unchanged")
        return

    validation = load(CORE_VALIDATION)
    if validation.get("status") != "PASS_READY_FOR_FORMAL_ADMISSION":
        raise RuntimeError("RAP-01 Core must pass deterministic validation before admission")
    ee_tasks = load(EE_TASKS)
    rhp_tasks = load(RHP_TASKS)
    formal_tasks = ee_tasks + rhp_tasks + rap_tasks
    write_json(FORMAL_TASKS, formal_tasks)
    write_json(
        FORMAL_MANIFEST,
        {
            "edition": "phase_v3_day34",
            "status": "THREE_CAPABILITY_CORES_ADMITTED",
            "task_count": len(formal_tasks),
            "task_file": "benchmark/tasks.json",
            "admitted_task_ids": [task["id"] for task in formal_tasks],
            "source_families": [
                "construction/latent_settlement_contract/core_family/",
                "construction/retail_hidden_operational_path/core_family/",
                "construction/retail_address_propagation/core_family/",
            ],
            "admission_evidence": [
                "construction/latent_settlement_contract/structural_audit/gate0_validation.json",
                "calibration/latent_settlement_contract/summaries/gate1_summary.json",
                "construction/latent_settlement_contract/core_family/structural_audit/core_validation.json",
                "construction/retail_hidden_operational_path/structural_audit/gate0_validation.json",
                "calibration/retail_hidden_operational_path/summaries/gate1_summary.json",
                "construction/retail_hidden_operational_path/core_family/structural_audit/core_validation.json",
                "construction/retail_address_propagation/structural_audit/gate0_validation.json",
                "calibration/retail_address_propagation/summaries/gate1_summary.json",
                "construction/retail_address_propagation/core_family/structural_audit/core_validation.json",
            ],
            "admission_contract": "V3_CAPABILITY_DESIGN_CONTRACT.md",
            "status_report": "reports/V3_STATUS.md",
        },
    )
    print(f"ADMITTED RAP-01 Core: 8 new tasks; {len(formal_tasks)} formal tasks total")


if __name__ == "__main__":
    main()
