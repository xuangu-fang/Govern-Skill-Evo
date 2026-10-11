"""Two matched pending-order fixtures for RDS-01 Gate 0 and Gate 1."""

from typing import Any

from .data_model import DualUpdateRetailDB


def _address(number: str = "1", street: str = "Old Street") -> dict[str, str]:
    return {
        "address1": f"{number} {street}",
        "address2": "",
        "city": "Boston",
        "country": "USA",
        "state": "MA",
        "zip": "02108",
    }


def _card(card_id: str, brand: str) -> dict[str, str]:
    return {
        "source": "credit_card",
        "id": card_id,
        "brand": brand,
        "last_four": card_id[-4:],
    }


def _user(
    user_id: str,
    first: str,
    last: str,
    email: str,
    old_card: str,
    new_card: str,
    order_id: str,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "name": {"first_name": first, "last_name": last},
        "address": _address(),
        "email": email,
        "payment_methods": {
            old_card: _card(old_card, "visa"),
            new_card: _card(new_card, "mastercard"),
        },
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
    old_card: str,
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
                "payment_method_id": old_card,
            }
        ],
    }


def build_gate0_db() -> DualUpdateRetailDB:
    products = {
        "RDS-P01": _product("RDS-P01", "RDS-I011", "Desk Lamp"),
        "RDS-P02": _product("RDS-P02", "RDS-I021", "Kitchen Scale"),
    }
    users = {
        "rds_user_a": _user(
            "rds_user_a", "Iris", "Wong", "iris.wong@example.test",
            "credit_card_7101", "credit_card_7191", "#RDS1001",
        ),
        "rds_user_b": _user(
            "rds_user_b", "Miles", "Turner", "miles.turner@example.test",
            "credit_card_7202", "credit_card_7292", "#RDS1002",
        ),
    }
    orders = {
        "#RDS1001": _order(
            "#RDS1001", "rds_user_a", "RDS-P01", "RDS-I011", "Desk Lamp",
            "credit_card_7101",
        ),
        "#RDS1002": _order(
            "#RDS1002", "rds_user_b", "RDS-P02", "RDS-I021", "Kitchen Scale",
            "credit_card_7202",
        ),
    }
    return DualUpdateRetailDB.model_validate(
        {
            "products": products,
            "users": users,
            "orders": orders,
            "dual_update_contracts": {
                "#RDS1001": {
                    "workflow_revision": "R1",
                    "required_sequence": ["address", "payment"],
                },
                "#RDS1002": {
                    "workflow_revision": "R2",
                    "required_sequence": ["payment", "address"],
                },
            },
        }
    )
