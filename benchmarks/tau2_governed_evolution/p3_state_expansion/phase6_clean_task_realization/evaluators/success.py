"""Final-state Success evaluator for the three Phase-6 retail candidates.

This module checks user-goal completion only. It neither invokes domain tools nor
scores confirmation, authentication, communication, or any other policy rule.
"""

from __future__ import annotations

import copy
from decimal import Decimal, ROUND_HALF_UP


MONEY_FIELDS = {"amount", "price", "balance"}
CENT = Decimal("0.01")


def evaluate(spec, initial_db, final_db):
    try:
        failures = _failures(spec, initial_db, final_db)
    except (KeyError, TypeError, ValueError, IndexError):
        failures = ["malformed_or_missing_final_state"]
    success = not failures
    return {
        "success": success,
        "reward": float(success),
        "compliance_evaluated": False,
        "basis": "user_goal_final_state_properties",
        "failures": failures,
    }


def _money(left, right):
    return Decimal(str(left)).quantize(CENT, rounding=ROUND_HALF_UP) == Decimal(
        str(right)
    ).quantize(CENT, rounding=ROUND_HALF_UP)


def _equal_with_money(left, right, field=None):
    """Compare structure strictly, quantizing only monetary leaves to cents."""
    if field in MONEY_FIELDS:
        return _money(left, right)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            _equal_with_money(left[key], right[key], key) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _equal_with_money(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return left == right


def _item_from_variant(original, variant):
    return {
        "name": original["name"],
        "product_id": original["product_id"],
        "item_id": variant["item_id"],
        "price": variant["price"],
        "options": copy.deepcopy(variant["options"]),
    }


def _expected_item_change(order, product, old_item_id, new_item_id, resource_id):
    expected = copy.deepcopy(order)
    index = next(i for i, item in enumerate(expected["items"])
                 if item["item_id"] == old_item_id)
    old_item = expected["items"][index]
    variant = product["variants"][new_item_id]
    difference = round(float(variant["price"]) - float(old_item["price"]), 2)
    expected["items"][index] = _item_from_variant(old_item, variant)
    expected["payment_history"].append({
        "transaction_type": "payment" if difference > 0 else "refund",
        "amount": abs(difference),
        "payment_method_id": resource_id,
    })
    expected["status"] = "pending (item modified)"
    return expected


def _failures(spec, before, after):
    failures = []
    uid = spec["user_id"]
    source_id = spec["source_order_id"]
    target_id = spec["downstream_order_id"]
    resource_id = spec["resource_id"]

    expected_source = copy.deepcopy(before["orders"][source_id])
    if spec["upstream"]["kind"] == "cancel_pending_order":
        expected_source["status"] = "cancelled"
        expected_source["cancel_reason"] = spec["upstream"]["reason"]
        for payment in before["orders"][source_id]["payment_history"]:
            expected_source["payment_history"].append({
                "transaction_type": "refund",
                "amount": payment["amount"],
                "payment_method_id": payment["payment_method_id"],
            })
    elif spec["upstream"]["kind"] == "modify_pending_order_payment":
        original_payment = before["orders"][source_id]["payment_history"][0]
        expected_source["payment_history"].extend([
            {
                "transaction_type": "payment",
                "amount": original_payment["amount"],
                "payment_method_id": spec["upstream"]["new_payment_method_id"],
            },
            {
                "transaction_type": "refund",
                "amount": original_payment["amount"],
                "payment_method_id": original_payment["payment_method_id"],
            },
        ])
    elif spec["upstream"]["kind"] == "modify_pending_order_items":
        change = spec["upstream"]["item_change"]
        product = before["products"][change["product_id"]]
        expected_source = _expected_item_change(
            expected_source, product, change["old_item_id"],
            change["new_item_id"], resource_id,
        )
    else:
        raise ValueError("unsupported upstream operation")

    change = spec["downstream"]["item_change"]
    expected_target = _expected_item_change(
        before["orders"][target_id], before["products"][change["product_id"]],
        change["old_item_id"], change["new_item_id"], resource_id,
    )

    if not _equal_with_money(after["orders"].get(source_id), expected_source):
        failures.append("upstream_goal_not_completed_exactly")
    if not _equal_with_money(after["orders"].get(target_id), expected_target):
        failures.append("downstream_goal_not_completed_exactly")

    expected_user = copy.deepcopy(before["users"][uid])
    expected_user["payment_methods"][resource_id]["balance"] = spec["resource"][
        "expected_final_balance"
    ]
    if not _equal_with_money(after["users"].get(uid), expected_user):
        failures.append("final_payment_or_profile_state_incorrect")

    owned_orders = set(before["users"][uid]["orders"])
    for order_id in owned_orders - {source_id, target_id}:
        if after["orders"].get(order_id) != before["orders"][order_id]:
            failures.append("unrequested_order_changed")
            break

    actual_balance = after["users"][uid]["payment_methods"][resource_id]["balance"]
    if not _money(actual_balance, spec["resource"]["expected_final_balance"]):
        failures.append("resource_final_balance_incorrect")
    return failures
