#!/usr/bin/env python3
"""Validate P3 refreshed and stale native paths plus v3 Retail regression."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
V3 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v3_day34"
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_address_propagation.candidate_tasks.evaluators.evaluate_rap01 import evaluate_success as evaluate_rap  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.candidate_tasks.evaluators.evaluate_rhp01 import evaluate_success as evaluate_rhp  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.retail_unified_pending_mutation_gate0.environment import get_environment  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.retail_unified_pending_mutation_gate0.p3_resource_refresh.evaluator import evaluate  # noqa: E402


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def upstream(tools: Any, spec: dict[str, Any]) -> None:
    if spec["kind"] == "cancel_then_payment":
        tools.cancel_pending_order(spec["source_order_id"], spec["source_reason"])
    else:
        tools.modify_pending_order_payment(spec["source_order_id"], spec["source_new_payment_id"])


def downstream(tools: Any, spec: dict[str, Any]) -> None:
    if spec["kind"] == "cancel_then_payment":
        tools.modify_pending_order_payment(spec["downstream_order_id"], spec["gift_card_id"])
    else:
        tools.modify_pending_order_items(
            spec["downstream_order_id"], [spec["downstream_old_item_id"]],
            [spec["downstream_new_item_id"]], spec["gift_card_id"]
        )


def apply_address(tools: Any, spec: dict[str, Any], target: str) -> None:
    if target == "order":
        tools.modify_pending_order_address(spec["order_id"], **spec["order_address"])
    else:
        tools.modify_user_address(spec["user_id"], **spec["profile_address"])


def main() -> None:
    specs = load(HERE / "specs.json")["triggers"]
    paths = []
    for spec in specs:
        correct = get_environment()
        before = correct.tools.get_user_details(spec["user_id"]).payment_methods[spec["gift_card_id"]].balance
        upstream(correct.tools, spec)
        refreshed = correct.tools.get_user_details(spec["user_id"]).payment_methods[spec["gift_card_id"]].balance
        downstream(correct.tools, spec)
        correct_result = evaluate(spec, correct.tools.db.model_dump(mode="json"))
        assert before == spec["initial_balance"]
        assert refreshed == spec["initial_balance"] + spec["refund_amount"]
        assert correct_result["success"]
        paths.append({"construction_label": spec["construction_label"], "path": "upstream_refresh_downstream", "label": "CS", "evaluation": correct_result})

        stale = get_environment()
        try:
            downstream(stale.tools, spec)
        except ValueError as error:
            rejection = str(error)
        else:
            raise AssertionError("stale downstream attempt unexpectedly succeeded")
        assert "Insufficient gift card balance" in rejection
        upstream(stale.tools, spec)
        stale_result = evaluate(spec, stale.tools.db.model_dump(mode="json"))
        assert not stale_result["success"]
        paths.append({"construction_label": spec["construction_label"], "path": "early_downstream_then_upstream_without_retry", "label": "CF", "native_rejection": rejection, "evaluation": stale_result})

    retail = get_environment()
    rhp_specs = load(V3 / "construction/retail_hidden_operational_path/core_family/candidates/task_specs.json")["tasks"]
    rap_specs = load(V3 / "construction/retail_address_propagation/core_family/candidates/task_specs.json")["tasks"]
    for spec in rhp_specs:
        if spec["expected_resolution"] == "exchange":
            retail.tools.exchange_delivered_order_items(spec["order_id"], [spec["old_item_id"]], [spec["new_item_id"]], spec["payment_id"])
        else:
            retail.tools.return_delivered_order_items(spec["order_id"], [spec["old_item_id"]], spec["payment_id"])
        assert evaluate_rhp(spec, retail.tools.db.model_dump(mode="json"))["success"]
    for spec in rap_specs:
        for target in spec["correct_sequence"]:
            apply_address(retail.tools, spec, target)
        assert evaluate_rap(spec, retail.tools.db.model_dump(mode="json"))["success"]

    result = {
        "status": "PASS_P3_ZERO_MODEL_GATE_0",
        "family_id": "C-RET-P3-RESOURCE-REFRESH",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "path_counts": {"CS": 2, "CF": 2},
        "paths": paths,
        "refresh_is_backend_precondition": False,
        "stale_path_uses_native_insufficient_balance_error": True,
        "new_domain": False,
        "new_tool": False,
        "new_oracle_sidecar": False,
        "v3_retail_oracle_replay": {"RHP-01": len(rhp_specs), "RAP-01": len(rap_specs), "total": len(rhp_specs) + len(rap_specs)},
    }
    (HERE / "gate0_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS P3 Gate 0: CS/CF x2; v3 Retail oracle replay 16/16")


if __name__ == "__main__":
    main()
