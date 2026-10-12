#!/usr/bin/env python3
"""Run P1 zero-model paths and replay all formal v3 Retail oracle paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/retail_unified_pending_mutation_gate0')
REPO = HERE.parents[4]
V3 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v3_day34"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from src.benchmark_v3.development.retail_address_propagation.candidate_tasks.evaluators.evaluate_rap01 import evaluate_success as evaluate_rap  # noqa: E402
from src.benchmark_v3.development.retail_hidden_operational_path.candidate_tasks.evaluators.evaluate_rhp01 import evaluate_success as evaluate_rhp  # noqa: E402
from src.benchmark_v3.construction.retail_unified_pending_mutation_gate0.environment import get_environment  # noqa: E402
from src.benchmark_v3.construction.retail_unified_pending_mutation_gate0.evaluator import evaluate  # noqa: E402


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_address(tools: Any, spec: dict[str, Any], target: str) -> None:
    if target == "order":
        tools.modify_pending_order_address(spec["order_id"], **spec["order_address"])
    else:
        tools.modify_user_address(spec["user_id"], **spec["profile_address"])


def apply_correct(tools: Any, spec: dict[str, Any]) -> None:
    tools.modify_pending_order_payment(spec["order_id"], spec["new_payment_id"])
    if spec["new_address"] is not None:
        tools.modify_pending_order_address(spec["order_id"], **spec["new_address"])
    tools.modify_pending_order_items(
        spec["order_id"],
        [spec["old_item_id"]],
        [spec["new_item_id"]],
        spec["new_payment_id"],
    )


def apply_wrong(tools: Any, spec: dict[str, Any]) -> str:
    tools.modify_pending_order_items(
        spec["order_id"],
        [spec["old_item_id"]],
        [spec["new_item_id"]],
        spec["new_payment_id"],
    )
    if spec["new_address"] is not None:
        tools.modify_pending_order_address(spec["order_id"], **spec["new_address"])
    try:
        tools.modify_pending_order_payment(spec["order_id"], spec["new_payment_id"])
    except ValueError as error:
        return str(error)
    raise AssertionError("items-first path unexpectedly allowed whole-order payment replacement")


def main() -> None:
    specs = load(HERE / "specs.json")["triggers"]
    paths = []
    for spec in specs:
        correct = get_environment()
        apply_correct(correct.tools, spec)
        correct_result = evaluate(spec, correct.tools.db.model_dump(mode="json"))
        assert correct_result["success"]
        paths.append(
            {
                "construction_label": spec["construction_label"],
                "path": "correct_payment_before_items",
                "label": "CS",
                "committed_item_write": True,
                "evaluation": correct_result,
            }
        )

        wrong = get_environment()
        error = apply_wrong(wrong.tools, spec)
        wrong_result = evaluate(spec, wrong.tools.db.model_dump(mode="json"))
        assert not wrong_result["success"]
        assert "exactly one payment" in error
        paths.append(
            {
                "construction_label": spec["construction_label"],
                "path": "wrong_items_before_payment",
                "label": "CF",
                "committed_item_write": True,
                "payment_rejection": error,
                "evaluation": wrong_result,
            }
        )

    retail = get_environment()
    policy = retail.policy.lower()
    assert all(
        label not in policy
        for label in ("consolidated", "partner_direct", "partner-direct", "cedar", "orbit")
    )
    assert "payment before" not in policy and "item change last" not in policy
    assert "will not be able to modify or cancel" not in policy
    assert "no longer be modified or cancelled" not in policy
    for spec in specs:
        assert spec["order_id"] in retail.tools.db.resolution_contracts
        assert spec["order_id"] in retail.tools.db.address_propagation_contracts

    rhp_specs = load(
        V3 / "construction/retail_hidden_operational_path/core_family/candidates/task_specs.json"
    )["tasks"]
    rap_specs = load(
        V3 / "construction/retail_address_propagation/core_family/candidates/task_specs.json"
    )["tasks"]
    for spec in rhp_specs:
        if spec["expected_resolution"] == "exchange":
            retail.tools.exchange_delivered_order_items(
                spec["order_id"], [spec["old_item_id"]], [spec["new_item_id"]], spec["payment_id"]
            )
        else:
            retail.tools.return_delivered_order_items(
                spec["order_id"], [spec["old_item_id"]], spec["payment_id"]
            )
        assert evaluate_rhp(spec, retail.tools.db.model_dump(mode="json"))["success"]
    for spec in rap_specs:
        for target in spec["correct_sequence"]:
            apply_address(retail.tools, spec, target)
        assert evaluate_rap(spec, retail.tools.db.model_dump(mode="json"))["success"]

    result = {
        "status": "PASS_ZERO_MODEL_GATE_0_DERIVED_UNIFIED_RETAIL_P1",
        "family_id": "C-RET-P1-PENDING-MUTATION-SEQUENCE",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "path_counts": {"CS": 2, "CF": 2},
        "paths": paths,
        "native_transition_verified": "payment_before_items",
        "family_specific_tools": False,
        "new_oracle_sidecar": False,
        "p1_orders_have_both_v3_sidecars": True,
        "hidden_v3_mapping_labels_absent_from_policy": True,
        "p1_required_sequence_absent_from_policy": True,
        "v3_retail_oracle_replay": {"RHP-01": len(rhp_specs), "RAP-01": len(rap_specs), "total": len(rhp_specs) + len(rap_specs)},
    }
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/retail_unified_pending_mutation_gate0/gate0_validation.json')).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS P1 Gate 0: CS/CF x2; v3 Retail oracle replay 16/16")


if __name__ == "__main__":
    main()
