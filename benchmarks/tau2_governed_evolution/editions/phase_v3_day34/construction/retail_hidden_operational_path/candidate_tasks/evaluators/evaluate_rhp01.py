"""Semantic final-state evaluator for RHP-01 candidates."""

from typing import Any


def evaluate_success(spec: dict[str, Any], final_db: dict[str, Any]) -> dict[str, Any]:
    order = final_db["orders"][spec["order_id"]]
    contract = final_db["resolution_contracts"][spec["order_id"]]
    checks = {
        "resolution_matches_condition": contract["last_resolution"]
        == spec["expected_resolution"],
        "order_status_matches": order["status"] == spec["expected_status"],
        "protection_outcome_matches": contract["purchase_protection_status"]
        == spec["expected_protection_status"],
    }
    if spec["expected_resolution"] == "exchange":
        checks["exchange_target_matches"] = order["exchange_items"] == [
            spec["old_item_id"]
        ] and order["exchange_new_items"] == [spec["new_item_id"]]
    else:
        checks["return_target_matches"] = order["return_items"] == [
            spec["old_item_id"]
        ] and order["return_payment_method_id"] == spec["payment_id"]
    return {
        "success": all(checks.values()),
        "semantic_invariant": checks,
        "observed_resolution": contract["last_resolution"],
        "observed_status": order["status"],
        "observed_protection_status": contract["purchase_protection_status"],
    }
