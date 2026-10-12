"""Semantic final-state evaluator for RDS-01 candidates."""

from typing import Any


def evaluate_success(spec: dict[str, Any], final_db: dict[str, Any]) -> dict[str, Any]:
    order = final_db["orders"][spec["order_id"]]
    contract = final_db["dual_update_contracts"][spec["order_id"]]
    address = order["address"]
    expected_address = spec["new_address"]
    payment_history = order["payment_history"]
    checks = {
        "address_updated": all(
            address[field] == expected_address[field]
            for field in ("address1", "address2", "city", "state", "country", "zip")
        ),
        "new_payment_committed": any(
            payment["transaction_type"] == "payment"
            and payment["payment_method_id"] == spec["new_payment_id"]
            for payment in payment_history
        ),
        "original_payment_refunded": any(
            payment["transaction_type"] == "refund"
            and payment["payment_method_id"] == spec["old_payment_id"]
            for payment in payment_history
        ),
        "required_sequence_completed": contract["completed_updates"]
        == spec["required_sequence"],
        "workflow_not_locked": contract["workflow_locked"] is False,
    }
    return {
        "success": all(checks.values()),
        "semantic_invariant": checks,
        "observed_completed_updates": contract["completed_updates"],
        "observed_workflow_locked": contract["workflow_locked"],
    }
