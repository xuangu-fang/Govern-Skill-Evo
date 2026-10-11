"""Final-state evaluator for P1 construction triggers."""

from typing import Any


def evaluate(spec: dict[str, Any], final_db: dict[str, Any]) -> dict[str, Any]:
    order = final_db["orders"][spec["order_id"]]
    item_ids = [item["item_id"] for item in order["items"]]
    payments = order["payment_history"]
    checks = {
        "requested_variant_present": spec["new_item_id"] in item_ids,
        "old_variant_absent": spec["old_item_id"] not in item_ids,
        "new_whole_order_payment_committed": any(
            row["transaction_type"] == "payment"
            and row["payment_method_id"] == spec["new_payment_id"]
            and row["amount"] == payments[0]["amount"]
            for row in payments[1:]
        ),
        "old_whole_order_payment_refunded": any(
            row["transaction_type"] == "refund"
            and row["payment_method_id"] == spec["old_payment_id"]
            and row["amount"] == payments[0]["amount"]
            for row in payments[1:]
        ),
        "unrequested_items_preserved": all(
            item_id in item_ids for item_id in spec["unrequested_item_ids"]
        ),
    }
    if spec["new_address"] is not None:
        checks["requested_address_present"] = all(
            order["address"][key] == value
            for key, value in spec["new_address"].items()
        )
    if spec.get("expected_profile_address") is not None:
        profile = final_db["users"][spec["user_id"]]["address"]
        checks["unrequested_profile_address_preserved"] = all(
            profile[key] == value
            for key, value in spec["expected_profile_address"].items()
        )
    return {"success": all(checks.values()), "checks": checks}
