"""Pending-order fixtures for RAP-01 Gate seeds and Capability Core."""

import json
from pathlib import Path
from typing import Any

from .data_model import AddressPropagationRetailDB


CORE_SPECS = (
    Path(__file__).resolve().parent.parent
    / "core_family/candidates/task_specs.json"
)


def _address(
    address1: str = "1 Old Street",
    address2: str = "",
    city: str = "Boston",
    state: str = "MA",
    zip_code: str = "02108",
) -> dict[str, str]:
    return {
        "address1": address1,
        "address2": address2,
        "city": city,
        "country": "USA",
        "state": state,
        "zip": zip_code,
    }


def _card(card_id: str) -> dict[str, str]:
    return {
        "source": "credit_card",
        "id": card_id,
        "brand": "visa",
        "last_four": card_id[-4:],
    }


def _user(
    user_id: str,
    first: str,
    last: str,
    email: str,
    card_id: str,
    order_id: str,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "name": {"first_name": first, "last_name": last},
        "address": _address(),
        "email": email,
        "payment_methods": {card_id: _card(card_id)},
        "orders": [order_id],
    }


def _product(product_id: str, item_id: str, name: str) -> dict[str, Any]:
    return {
        "name": name,
        "product_id": product_id,
        "variants": {
            item_id: {
                "item_id": item_id,
                "options": {"color": "black", "size": "standard"},
                "available": True,
                "price": 100.0,
            }
        },
    }


def _order(
    order_id: str,
    user_id: str,
    product_id: str,
    item_id: str,
    product_name: str,
    card_id: str,
) -> dict[str, Any]:
    return {
        "order_id": order_id,
        "user_id": user_id,
        "address": _address(),
        "items": [
            {
                "name": product_name,
                "product_id": product_id,
                "item_id": item_id,
                "price": 100.0,
                "options": {"color": "black", "size": "standard"},
            }
        ],
        "status": "pending",
        "fulfillments": [],
        "payment_history": [
            {
                "transaction_type": "payment",
                "amount": 100.0,
                "payment_method_id": card_id,
            }
        ],
    }


def build_gate0_db() -> AddressPropagationRetailDB:
    products = {
        "RAP-P01": _product("RAP-P01", "RAP-I011", "Travel Pillow"),
        "RAP-P02": _product("RAP-P02", "RAP-I021", "Reading Lamp"),
    }
    users = {
        "rap_user_a": _user(
            "rap_user_a", "Nora", "Chen", "nora.chen@example.test",
            "credit_card_8101", "#RAP1001",
        ),
        "rap_user_b": _user(
            "rap_user_b", "Evan", "Brooks", "evan.brooks@example.test",
            "credit_card_8202", "#RAP1002",
        ),
    }
    orders = {
        "#RAP1001": _order(
            "#RAP1001", "rap_user_a", "RAP-P01", "RAP-I011",
            "Travel Pillow", "credit_card_8101",
        ),
        "#RAP1002": _order(
            "#RAP1002", "rap_user_b", "RAP-P02", "RAP-I021",
            "Reading Lamp", "credit_card_8202",
        ),
    }
    contracts = {
        "#RAP1001": {
            "address_contract": "cedar",
            "propagation_source": "profile",
        },
        "#RAP1002": {
            "address_contract": "orbit",
            "propagation_source": "order",
        },
    }
    core = json.loads(CORE_SPECS.read_text(encoding="utf-8"))
    for spec in core["tasks"]:
        products[spec["product_id"]] = _product(
            spec["product_id"], spec["item_id"], spec["product_name"]
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
            spec["item_id"],
            spec["product_name"],
            spec["payment_id"],
        )
        contracts[spec["order_id"]] = {
            "address_contract": spec["address_contract"],
            "propagation_source": spec["propagation_source"],
        }
    return AddressPropagationRetailDB.model_validate(
        {
            "products": products,
            "users": users,
            "orders": orders,
            "address_propagation_contracts": contracts,
        }
    )
