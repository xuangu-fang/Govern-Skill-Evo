"""Native final-state evaluator for P3 construction triggers."""

from typing import Any


def evaluate(spec: dict[str, Any], final_db: dict[str, Any]) -> dict[str, Any]:
    source = final_db["orders"][spec["source_order_id"]]
    downstream = final_db["orders"][spec["downstream_order_id"]]
    gift = final_db["users"][spec["user_id"]]["payment_methods"][spec["gift_card_id"]]
    checks = {"gift_card_final_balance": gift["balance"] == spec["expected_final_balance"]}
    if spec["kind"] == "cancel_then_payment":
        checks.update({
            "source_cancelled": source["status"] == "cancelled" and source["cancel_reason"] == spec["source_reason"],
            "source_refund_committed": any(
                row["transaction_type"] == "refund"
                and row["payment_method_id"] == spec["gift_card_id"]
                and row["amount"] == spec["refund_amount"]
                for row in source["payment_history"]
            ),
            "downstream_gift_payment_committed": any(
                row["transaction_type"] == "payment"
                and row["payment_method_id"] == spec["gift_card_id"]
                and row["amount"] == spec["downstream_need"]
                for row in downstream["payment_history"][1:]
            ),
            "downstream_old_payment_refunded": any(
                row["transaction_type"] == "refund"
                and row["payment_method_id"] == spec["downstream_old_payment_id"]
                and row["amount"] == spec["downstream_need"]
                for row in downstream["payment_history"][1:]
            ),
            "downstream_item_preserved": [item["item_id"] for item in downstream["items"]] == ["P3-I1102"],
        })
    else:
        checks.update({
            "source_new_payment_committed": any(
                row["transaction_type"] == "payment"
                and row["payment_method_id"] == spec["source_new_payment_id"]
                and row["amount"] == spec["refund_amount"]
                for row in source["payment_history"][1:]
            ),
            "source_gift_refund_committed": any(
                row["transaction_type"] == "refund"
                and row["payment_method_id"] == spec["gift_card_id"]
                and row["amount"] == spec["refund_amount"]
                for row in source["payment_history"][1:]
            ),
            "downstream_new_item_present": [item["item_id"] for item in downstream["items"]] == [spec["downstream_new_item_id"]],
            "downstream_delta_paid_by_gift": any(
                row["transaction_type"] == "payment"
                and row["payment_method_id"] == spec["gift_card_id"]
                and row["amount"] == spec["downstream_need"]
                for row in downstream["payment_history"][1:]
            ),
        })
    return {"success": all(checks.values()), "checks": checks}
