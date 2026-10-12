#!/usr/bin/env python3
"""Build and admit the eight RHP-01 Capability Core tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[7] / 'scripts/benchmarks/v3/development/retail_hidden_operational_path/core_family/tools'))
CORE = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/retail_hidden_operational_path/core_family')
PRIMITIVE = CORE.parent
EDITION = PRIMITIVE.parents[1]
SPECS = CORE / "candidates/task_specs.json"
CANDIDATE_TASKS = CORE / "candidate_tasks/tasks.json"
CANDIDATE_MANIFEST = CORE / "candidate_tasks/task_manifest.json"
EE_TASKS = (
    EDITION
    / "construction/latent_settlement_contract/core_family/candidate_tasks/tasks.json"
)
FORMAL_TASKS = EDITION / "benchmark/tasks.json"
FORMAL_MANIFEST = EDITION / "benchmark/task_manifest.json"


SURFACE_TEMPLATES = {
    1: "For delivered order {order}, exchange my {old_variant} {product} for the {new_variant} version if that keeps the original purchase protection active. Otherwise, return it to my card ending {last_four}.",
    2: "I need help with delivered order {order}. I prefer to replace the {old_variant} {product} with {new_variant}, but only if my original purchase protection survives the exchange; if not, please return the original item to the card ending {last_four}.",
    3: "On order {order}, can you change my {product} from {old_variant} to {new_variant} while preserving its original purchase protection? If an exchange would lose that protection, return the original item to my card ending {last_four} instead.",
    4: "Please resolve delivered order {order}: use an exchange from {old_variant} to {new_variant} for the {product} when the existing purchase protection remains active, and otherwise process a return to the card ending {last_four}.",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def variant_text(options: dict[str, str]) -> str:
    return ", ".join(options.values())


def task_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    request = SURFACE_TEMPLATES[spec["surface"]].format(
        order=spec["order_id"],
        product=spec["product_name"],
        old_variant=variant_text(spec["old_options"]),
        new_variant=variant_text(spec["new_options"]),
        last_four=spec["payment_id"][-4:],
    )
    action = {
        "action_id": f"{spec['task_id']}-target-0",
        "requestor": "assistant",
        "name": (
            "exchange_delivered_order_items"
            if spec["expected_resolution"] == "exchange"
            else "return_delivered_order_items"
        ),
        "arguments": {
            "order_id": spec["order_id"],
            "item_ids": [spec["old_item_id"]],
            "payment_method_id": spec["payment_id"],
        },
    }
    if spec["expected_resolution"] == "exchange":
        action["arguments"]["new_item_ids"] = [spec["new_item_id"]]
    return {
        "id": spec["task_id"],
        "description": {
            "purpose": "RHP-01 Capability Core: infer the fulfillment-conditioned exchange or return path before an irreversible resolution.",
            "relevant_policies": "Native Retail policy plus the isolated v3 fulfillment-resolution extension.",
            "notes": "Formally admitted after RHP-01 Gate 0 and matched Gate 1 Reference-Skill necessity passed.",
        },
        "user_scenario": {
            "persona": "A customer with a stable conditional resolution request who cannot validate internal fulfillment consequences.",
            "instructions": {
                "domain": "retail-v3-unified",
                "reason_for_call": request,
                "known_info": (
                    f"Your name is {spec['first_name']} {spec['last_name']}, your email is "
                    f"{spec['email']}, your ZIP is 02108, and the refund or exchange "
                    f"payment method is {spec['payment_id']}."
                ),
                "unknown_info": "You do not know how consolidated or partner-direct fulfillment affects purchase protection.",
                "task_instructions": (
                    "State the request and authentication details naturally. Do not add or "
                    "change the goal. If asked to choose exchange or return, restate the same "
                    "condition and do not choose for the agent. Confirm once when the agent "
                    "presents the exact exchange or return proposal; you cannot validate its "
                    "claim about protection. Never reveal, infer, confirm, deny, or hint at "
                    "the fulfillment-mode mapping. Remain until completion is reported."
                ),
            },
        },
        "initial_state": None,
        "evaluation_criteria": {
            "actions": [action],
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
    rhp_tasks = [task_from_spec(spec) for spec in payload["tasks"]]
    rhp_ids = [task["id"] for task in rhp_tasks]
    ee_tasks = load(EE_TASKS)
    formal_tasks = ee_tasks + rhp_tasks
    write_json(CANDIDATE_TASKS, rhp_tasks)
    write_json(
        CANDIDATE_MANIFEST,
        {
            "mechanism_id": payload["mechanism_id"],
            "status": "ADMITTED_CAPABILITY_CORE",
            "task_count": len(rhp_tasks),
            "task_file": "tasks.json",
            "task_ids": rhp_ids,
            "canonical_specs": "../candidates/task_specs.json",
        },
    )
    write_json(FORMAL_TASKS, formal_tasks)
    write_json(
        FORMAL_MANIFEST,
        {
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
        },
    )
    print(f"BUILT RHP-01 Core: 8 new tasks; {len(formal_tasks)} formal tasks total")


if __name__ == "__main__":
    main()
