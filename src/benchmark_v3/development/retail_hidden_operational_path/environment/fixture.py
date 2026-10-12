"""Delivered-order fixtures for RHP-01 Gate seeds and Capability Core."""

import json
from pathlib import Path
from typing import Any

from src.benchmark_v3.development.retail_hidden_operational_path.environment.data_model import ResolutionRetailDB


CORE_SPECS = (
    (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/retail_hidden_operational_path/core_family/candidates/task_specs.json')
)


def _address() -> dict[str, str]:
    return {
        "address1": "1 Test Way",
        "address2": "",
        "city": "Boston",
        "country": "USA",
        "state": "MA",
        "zip": "02108",
    }


def _user(
    user_id: str, first: str, last: str, email: str, card_id: str, order_id: str
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "name": {"first_name": first, "last_name": last},
        "address": _address(),
        "email": email,
        "payment_methods": {
            card_id: {
                "source": "credit_card",
                "id": card_id,
                "brand": "visa",
                "last_four": card_id[-4:],
            }
        },
        "orders": [order_id],
    }


def _product(
    product_id: str,
    name: str,
    old_id: str,
    new_id: str,
    old_options: dict[str, str] | None = None,
    new_options: dict[str, str] | None = None,
    old_price: float = 100.0,
    new_price: float = 110.0,
) -> dict[str, Any]:
    old_options = old_options or {"color": "navy", "size": "medium"}
    new_options = new_options or {"color": "navy", "size": "large"}
    return {
        "name": name,
        "product_id": product_id,
        "variants": {
            old_id: {
                "item_id": old_id,
                "options": old_options,
                "available": True,
                "price": old_price,
            },
            new_id: {
                "item_id": new_id,
                "options": new_options,
                "available": True,
                "price": new_price,
            },
        },
    }


def _order(
    order_id: str,
    user_id: str,
    product_id: str,
    product_name: str,
    old_id: str,
    card_id: str,
    old_options: dict[str, str] | None = None,
    old_price: float = 100.0,
) -> dict[str, Any]:
    old_options = old_options or {"color": "navy", "size": "medium"}
    return {
        "order_id": order_id,
        "user_id": user_id,
        "address": _address(),
        "items": [
            {
                "name": product_name,
                "product_id": product_id,
                "item_id": old_id,
                "price": old_price,
                "options": old_options,
            }
        ],
        "status": "delivered",
        "fulfillments": [{"tracking_id": [f"TRACK-{order_id[-1]}"], "item_ids": [old_id]}],
        "payment_history": [
            {
                "transaction_type": "payment",
                "amount": old_price,
                "payment_method_id": card_id,
            }
        ],
    }


def build_gate0_db() -> ResolutionRetailDB:
    products = {
        "RHP-P01": _product("RHP-P01", "Travel Jacket", "RHP-I011", "RHP-I012"),
        "RHP-P02": _product("RHP-P02", "Trail Sweater", "RHP-I021", "RHP-I022"),
    }
    users = {
        "rhp_user_a": _user(
            "rhp_user_a", "Erin", "Cole", "erin.cole@example.test", "credit_card_5101", "#RHP1001"
        ),
        "rhp_user_b": _user(
            "rhp_user_b", "Noah", "Reed", "noah.reed@example.test", "credit_card_5202", "#RHP1002"
        ),
    }
    orders = {
        "#RHP1001": _order(
            "#RHP1001", "rhp_user_a", "RHP-P01", "Travel Jacket", "RHP-I011", "credit_card_5101"
        ),
        "#RHP1002": _order(
            "#RHP1002", "rhp_user_b", "RHP-P02", "Trail Sweater", "RHP-I021", "credit_card_5202"
        ),
    }
    contracts = {
        "#RHP1001": {
            "fulfillment_mode": "consolidated",
            "exchange_protection_behavior": "preserve",
            "purchase_protection_status": "active",
        },
        "#RHP1002": {
            "fulfillment_mode": "partner_direct",
            "exchange_protection_behavior": "forfeit",
            "purchase_protection_status": "active",
        },
    }

    core = json.loads(CORE_SPECS.read_text(encoding="utf-8"))
    for spec in core["tasks"]:
        products[spec["product_id"]] = _product(
            spec["product_id"],
            spec["product_name"],
            spec["old_item_id"],
            spec["new_item_id"],
            spec["old_options"],
            spec["new_options"],
            spec["old_price"],
            spec["new_price"],
        )
        users[spec["user_id"]] = _user(
            spec["user_id"],
            spec["first_name"],
            spec["last_name"],
            spec["email"],
            spec["payment_id"],
            spec["order_id"],
        )
        orders[spec["order_id"]] = _order(
            spec["order_id"],
            spec["user_id"],
            spec["product_id"],
            spec["product_name"],
            spec["old_item_id"],
            spec["payment_id"],
            spec["old_options"],
            spec["old_price"],
        )
        contracts[spec["order_id"]] = {
            "fulfillment_mode": spec["fulfillment_mode"],
            "exchange_protection_behavior": spec["exchange_protection_behavior"],
            "purchase_protection_status": "active",
        }
    return ResolutionRetailDB.model_validate(
        {
            "products": products,
            "users": users,
            "orders": orders,
            "resolution_contracts": contracts,
        }
    )
