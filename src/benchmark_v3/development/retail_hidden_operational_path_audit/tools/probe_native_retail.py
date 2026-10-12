#!/usr/bin/env python3
"""Replay native Retail terminal transitions in memory; never write native data."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


DATA_ROOT = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/retail_hidden_operational_path_audit')
EDITION = DATA_ROOT.parents[1]
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from tau2.domains.retail.data_model import GiftCard, RetailDB  # noqa: E402
from tau2.domains.retail.tools import RetailTools  # noqa: E402
from tau2.domains.retail.utils import RETAIL_DB_PATH  # noqa: E402


RESULT = DATA_ROOT / "native_probe.json"


def fresh() -> tuple[RetailDB, RetailTools]:
    db = RetailDB.load(RETAIL_DB_PATH)
    return db, RetailTools(db)


def find_case(status: str) -> dict[str, str]:
    db, _ = fresh()
    for order in db.orders.values():
        if order.status != status:
            continue
        user = db.users[order.user_id]
        for item in order.items:
            product = db.products[item.product_id]
            for variant in product.variants.values():
                if variant.item_id == item.item_id or not variant.available:
                    continue
                payment_id = order.payment_history[0].payment_method_id
                payment = user.payment_methods[payment_id]
                difference = variant.price - item.price
                if isinstance(payment, GiftCard) and difference > payment.balance:
                    continue
                return {
                    "order_id": order.order_id,
                    "old_item_id": item.item_id,
                    "new_item_id": variant.item_id,
                    "payment_id": payment_id,
                }
    raise RuntimeError(f"no usable {status} fixture found")


def expect_error(call: Any, expected: str) -> str:
    try:
        call()
    except ValueError as error:
        message = str(error)
        assert message == expected
        return message
    raise AssertionError("expected ValueError")


def exchange_then_return(case: dict[str, str]) -> dict[str, Any]:
    db, tools = fresh()
    tools.exchange_delivered_order_items(
        case["order_id"],
        [case["old_item_id"]],
        [case["new_item_id"]],
        case["payment_id"],
    )
    committed = db.model_dump(mode="json")
    error = expect_error(
        lambda: tools.return_delivered_order_items(
            case["order_id"], [case["old_item_id"]], case["payment_id"]
        ),
        "Non-delivered order cannot be returned",
    )
    assert db.model_dump(mode="json") == committed
    return {
        "first_write": "exchange_delivered_order_items",
        "first_status": "exchange requested",
        "opposite_retry_error": error,
        "first_write_preserved": True,
    }


def return_then_exchange(case: dict[str, str]) -> dict[str, Any]:
    db, tools = fresh()
    tools.return_delivered_order_items(
        case["order_id"], [case["old_item_id"]], case["payment_id"]
    )
    committed = db.model_dump(mode="json")
    error = expect_error(
        lambda: tools.exchange_delivered_order_items(
            case["order_id"],
            [case["old_item_id"]],
            [case["new_item_id"]],
            case["payment_id"],
        ),
        "Non-delivered order cannot be exchanged",
    )
    assert db.model_dump(mode="json") == committed
    return {
        "first_write": "return_delivered_order_items",
        "first_status": "return requested",
        "opposite_retry_error": error,
        "first_write_preserved": True,
    }


def modify_pending_once(case: dict[str, str]) -> dict[str, Any]:
    db, tools = fresh()
    tools.modify_pending_order_items(
        case["order_id"],
        [case["old_item_id"]],
        [case["new_item_id"]],
        case["payment_id"],
    )
    committed = db.model_dump(mode="json")
    second_error = expect_error(
        lambda: tools.modify_pending_order_items(
            case["order_id"],
            [case["new_item_id"]],
            [case["old_item_id"]],
            case["payment_id"],
        ),
        "Non-pending order cannot be modified",
    )
    cancel_error = expect_error(
        lambda: tools.cancel_pending_order(case["order_id"], "ordered by mistake"),
        "Non-pending order cannot be cancelled",
    )
    assert db.model_dump(mode="json") == committed
    return {
        "first_write": "modify_pending_order_items",
        "first_status": "pending (item modified)",
        "second_item_write_error": second_error,
        "cancel_after_item_write_error": cancel_error,
        "first_write_preserved": True,
    }


def main() -> None:
    delivered = find_case("delivered")
    pending = find_case("pending")
    result = {
        "status": "PASS_NATIVE_TRANSITION_PROBE",
        "model_calls": 0,
        "native_files_modified": False,
        "fixtures": {"delivered": delivered, "pending": pending},
        "paths": {
            "exchange_then_return": exchange_then_return(delivered),
            "return_then_exchange": return_then_exchange(delivered),
            "pending_item_modification": modify_pending_once(pending),
        },
        "established": [
            "exchange and return are mutually exclusive terminal choices on a delivered order",
            "pending item modification blocks a second item modification and cancellation",
            "all first writes remain committed after the rejected opposite or corrective call",
        ],
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS native Retail: exchange/return terminal paths and pending one-shot path")


if __name__ == "__main__":
    main()
