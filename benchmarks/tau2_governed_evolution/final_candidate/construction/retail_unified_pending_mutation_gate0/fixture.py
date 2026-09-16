"""Add final-candidate P1 and P3 construction states to unified Retail."""

from typing import Any

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.unified_environment.data_model import UnifiedRetailDB
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.unified_environment.fixture import build_unified_retail_db


def _address(
    address1: str = "10 Market Street",
    address2: str = "",
    city: str = "Boston",
    state: str = "MA",
    zip_code: str = "02108",
) -> dict[str, str]:
    return {
        "address1": address1,
        "address2": address2,
        "city": city,
        "state": state,
        "country": "USA",
        "zip": zip_code,
    }


def _card(card_id: str, brand: str) -> dict[str, str]:
    return {
        "source": "credit_card",
        "id": card_id,
        "brand": brand,
        "last_four": card_id[-4:],
    }


def _gift_card(card_id: str, balance: float) -> dict[str, Any]:
    return {"source": "gift_card", "id": card_id, "balance": balance}


def _paypal(payment_id: str) -> dict[str, str]:
    return {"source": "paypal", "id": payment_id}


def _product(
    product_id: str,
    name: str,
    old_item_id: str,
    new_item_id: str,
    old_price: float,
    new_price: float,
    old_options: dict[str, str],
    new_options: dict[str, str],
) -> dict[str, Any]:
    return {
        "name": name,
        "product_id": product_id,
        "variants": {
            old_item_id: {
                "item_id": old_item_id,
                "options": old_options,
                "available": True,
                "price": old_price,
            },
            new_item_id: {
                "item_id": new_item_id,
                "options": new_options,
                "available": True,
                "price": new_price,
            },
        },
    }


def build_gate0_db() -> UnifiedRetailDB:
    payload = build_unified_retail_db().model_dump(mode="json")
    fixtures = [
        {
            "user_id": "p1_user_cedar",
            "name": {"first_name": "Maya", "last_name": "Sato"},
            "email": "maya.sato.p1@example.test",
            "order_id": "#P1C1001",
            "product_id": "P1-P1001",
            "product_name": "Electric Kettle",
            "old_item_id": "P1-I1001",
            "new_item_id": "P1-I1002",
            "old_options": {"material": "steel", "capacity": "1.5 liter"},
            "new_options": {"material": "glass", "capacity": "2 liter"},
            "old_price": 80.0,
            "new_price": 105.0,
            "old_card": "credit_card_4101",
            "new_card": "credit_card_4191",
            "address": _address(),
            "new_address": None,
        },
        {
            "user_id": "p1_user_orbit",
            "name": {"first_name": "Caleb", "last_name": "Morgan"},
            "email": "caleb.morgan@example.test",
            "order_id": "#P1C1002",
            "product_id": "P1-P1002",
            "product_name": "Desk Lamp",
            "old_item_id": "P1-I2001",
            "new_item_id": "P1-I2002",
            "old_options": {"color": "black", "power": "corded"},
            "new_options": {"color": "white", "power": "rechargeable"},
            "old_price": 120.0,
            "new_price": 95.0,
            "old_card": "credit_card_4202",
            "new_card": "credit_card_4292",
            "address": _address("6 Beacon Road", city="Seattle", state="WA", zip_code="98101"),
            "new_address": _address("44 Pine Avenue", "Unit 7", "Portland", "OR", "97205"),
        },
        {
            "user_id": "p1_user_harbor",
            "name": {"first_name": "Priya", "last_name": "Nair"},
            "email": "priya.nair.p1@example.test",
            "order_id": "#P1C2303",
            "product_id": "P1-P3003",
            "product_name": "Travel Backpack",
            "old_item_id": "P1-I3005",
            "new_item_id": "P1-I3006",
            "old_options": {"color": "navy", "capacity": "28 liter"},
            "new_options": {"color": "sand", "capacity": "36 liter"},
            "old_price": 90.0,
            "new_price": 125.0,
            "old_card": "credit_card_5303",
            "new_card": "credit_card_5393",
            "address": _address("83 Lake Street", city="Madison", state="WI", zip_code="53703"),
            "new_address": _address("17 Oak Court", "Apt 2", "Denver", "CO", "80203"),
        },
        {
            "user_id": "p1_user_juniper",
            "name": {"first_name": "Owen", "last_name": "Brooks"},
            "email": "owen.brooks.p1@example.test",
            "order_id": "#P1C3404",
            "product_id": "P1-P4004",
            "product_name": "Coffee Grinder",
            "old_item_id": "P1-I4007",
            "new_item_id": "P1-I4008",
            "old_options": {"color": "silver", "setting": "manual"},
            "new_options": {"color": "charcoal", "setting": "automatic"},
            "old_price": 140.0,
            "new_price": 110.0,
            "old_card": "credit_card_6404",
            "new_card": "credit_card_6494",
            "address": _address("51 King Drive", city="Austin", state="TX", zip_code="78701"),
            "new_address": None,
        },
        {
            "user_id": "p1_user_linden",
            "name": {"first_name": "Elena", "last_name": "Rossi"},
            "email": "elena.rossi.p1@example.test",
            "order_id": "#P1C4505",
            "product_id": "P1-P5005",
            "product_name": "Yoga Mat",
            "old_item_id": "P1-I5009",
            "new_item_id": "P1-I5010",
            "old_options": {"color": "green", "thickness": "4 mm"},
            "new_options": {"color": "plum", "thickness": "6 mm"},
            "old_price": 45.0,
            "new_price": 70.0,
            "old_card": "credit_card_7505",
            "new_card": "credit_card_7595",
            "address": _address("29 River Lane", city="Boise", state="ID", zip_code="83702"),
            "new_address": None,
        },
        {
            "user_id": "p1_user_meadow",
            "name": {"first_name": "Marcus", "last_name": "Lee"},
            "email": "marcus.lee.p1@example.test",
            "order_id": "#P1C5606",
            "product_id": "P1-P6006",
            "product_name": "Noise-Canceling Headphones",
            "old_item_id": "P1-I6011",
            "new_item_id": "P1-I6012",
            "old_options": {"color": "black", "fit": "over ear"},
            "new_options": {"color": "blue", "fit": "on ear"},
            "old_price": 210.0,
            "new_price": 175.0,
            "old_card": "credit_card_8606",
            "new_card": "credit_card_8696",
            "address": _address("64 Walnut Way", city="Columbus", state="OH", zip_code="43215"),
            "new_address": _address("205 Elm Street", "Suite 3", "Nashville", "TN", "37203"),
        },
        {
            "user_id": "p1_user_quartz",
            "name": {"first_name": "Sofia", "last_name": "Alvarez"},
            "email": "sofia.alvarez.p1@example.test",
            "order_id": "#P1C6708",
            "product_id": "P1-P7007",
            "product_name": "Throw Blanket",
            "old_item_id": "P1-I7013",
            "new_item_id": "P1-I7014",
            "old_options": {"color": "cream", "size": "twin"},
            "new_options": {"color": "rust", "size": "queen"},
            "old_price": 85.0,
            "new_price": 60.0,
            "old_card": "credit_card_9708",
            "new_card": "credit_card_9798",
            "address": _address("12 Birch Place", city="Tucson", state="AZ", zip_code="85701"),
            "new_address": _address("71 Aspen Walk", "Apt 4", "Reno", "NV", "89501"),
        },
        {
            "user_id": "p1_user_timber",
            "name": {"first_name": "Noah", "last_name": "Williams"},
            "email": "noah.williams.p1@example.test",
            "order_id": "#P1C7809",
            "product_id": "P1-P8008",
            "product_name": "Cast-Iron Skillet",
            "old_item_id": "P1-I8015",
            "new_item_id": "P1-I8016",
            "old_options": {"diameter": "10 inch", "finish": "seasoned"},
            "new_options": {"diameter": "12 inch", "finish": "enameled"},
            "old_price": 150.0,
            "new_price": 175.0,
            "old_card": "credit_card_1809",
            "new_card": "credit_card_1899",
            "address": _address("37 Cedar Avenue", city="Richmond", state="VA", zip_code="23219"),
            "new_address": None,
        },
    ]

    for row in fixtures:
        payload["products"][row["product_id"]] = _product(
            row["product_id"],
            row["product_name"],
            row["old_item_id"],
            row["new_item_id"],
            row["old_price"],
            row["new_price"],
            row["old_options"],
            row["new_options"],
        )
        payload["users"][row["user_id"]] = {
            "user_id": row["user_id"],
            "name": row["name"],
            "address": row["address"],
            "email": row["email"],
            "payment_methods": {
                row["old_card"]: _card(row["old_card"], "visa"),
                row["new_card"]: _card(row["new_card"], "mastercard"),
            },
            "orders": [row["order_id"]],
        }
        payload["orders"][row["order_id"]] = {
            "order_id": row["order_id"],
            "user_id": row["user_id"],
            "address": row["address"],
            "items": [
                {
                    "name": row["product_name"],
                    "product_id": row["product_id"],
                    "item_id": row["old_item_id"],
                    "price": row["old_price"],
                    "options": row["old_options"],
                }
            ],
            "status": "pending",
            "fulfillments": [],
            "payment_history": [
                {
                    "transaction_type": "payment",
                    "amount": row["old_price"],
                    "payment_method_id": row["old_card"],
                }
            ],
        }
        payload["resolution_contracts"][row["order_id"]] = {
            "fulfillment_mode": "consolidated",
            "exchange_protection_behavior": "preserve",
            "purchase_protection_status": "active",
            "last_resolution": None,
        }
        payload["address_propagation_contracts"][row["order_id"]] = {
            "address_contract": "cedar",
            "propagation_source": "profile",
            "written_targets": [],
            "session_closed": False,
        }

    p3_users = [
        {
            "user_id": "p3_user_brook",
            "name": {"first_name": "Iris", "last_name": "Bennett"},
            "email": "iris.bennett.p3@example.test",
            "address": _address("18 Harbor Street", city="Providence", state="RI", zip_code="02903"),
            "gift_id": "gift_card_3817",
            "gift_balance": 40.0,
            "card_id": "credit_card_3847",
            "paypal_id": "paypal_3887",
            "source_order_id": "#P3C1101",
            "downstream_order_id": "#P3C1102",
        },
        {
            "user_id": "p3_user_cove",
            "name": {"first_name": "Daniel", "last_name": "Kim"},
            "email": "daniel.kim.p3@example.test",
            "address": _address("72 Summit Avenue", city="Raleigh", state="NC", zip_code="27601"),
            "gift_id": "gift_card_4928",
            "gift_balance": 30.0,
            "card_id": "credit_card_4958",
            "paypal_id": "paypal_4998",
            "source_order_id": "#P3C2201",
            "downstream_order_id": "#P3C2202",
        },
    ]
    for row in p3_users:
        payload["users"][row["user_id"]] = {
            "user_id": row["user_id"],
            "name": row["name"],
            "address": row["address"],
            "email": row["email"],
            "payment_methods": {
                row["gift_id"]: _gift_card(row["gift_id"], row["gift_balance"]),
                row["card_id"]: _card(row["card_id"], "visa"),
                row["paypal_id"]: _paypal(row["paypal_id"]),
            },
            "orders": [row["source_order_id"], row["downstream_order_id"]],
        }

    p3_products = [
        ("P3-P1101", "Smart Speaker", "P3-I1101", "P3-I1103", 180.0, 180.0, {"color": "black"}, {"color": "white"}),
        ("P3-P1102", "Notebook Set", "P3-I1102", "P3-I1104", 120.0, 120.0, {"cover": "blue"}, {"cover": "green"}),
        ("P3-P2201", "Coffee Maker", "P3-I2201", "P3-I2203", 240.0, 240.0, {"finish": "steel"}, {"finish": "black"}),
        ("P3-P2202", "Carry-On Suitcase", "P3-I2202", "P3-I2204", 200.0, 280.0, {"shell": "soft", "size": "small"}, {"shell": "hard", "size": "small"}),
    ]
    for args in p3_products:
        product_id, name, old_item_id, new_item_id, old_price, new_price, old_options, new_options = args
        payload["products"][product_id] = _product(
            product_id, name, old_item_id, new_item_id, old_price, new_price, old_options, new_options
        )

    p3_orders = [
        ("#P3C1101", "p3_user_brook", "P3-P1101", "Smart Speaker", "P3-I1101", 180.0, {"color": "black"}, "gift_card_3817"),
        ("#P3C1102", "p3_user_brook", "P3-P1102", "Notebook Set", "P3-I1102", 120.0, {"cover": "blue"}, "credit_card_3847"),
        ("#P3C2201", "p3_user_cove", "P3-P2201", "Coffee Maker", "P3-I2201", 240.0, {"finish": "steel"}, "gift_card_4928"),
        ("#P3C2202", "p3_user_cove", "P3-P2202", "Carry-On Suitcase", "P3-I2202", 200.0, {"shell": "soft", "size": "small"}, "credit_card_4958"),
    ]
    for order_id, user_id, product_id, name, item_id, price, options, payment_id in p3_orders:
        address = payload["users"][user_id]["address"]
        payload["orders"][order_id] = {
            "order_id": order_id,
            "user_id": user_id,
            "address": address,
            "items": [{"name": name, "product_id": product_id, "item_id": item_id, "price": price, "options": options}],
            "status": "pending",
            "fulfillments": [],
            "payment_history": [{"transaction_type": "payment", "amount": price, "payment_method_id": payment_id}],
        }
        payload["resolution_contracts"][order_id] = {
            "fulfillment_mode": "consolidated",
            "exchange_protection_behavior": "preserve",
            "purchase_protection_status": "active",
            "last_resolution": None,
        }
        payload["address_propagation_contracts"][order_id] = {
            "address_contract": "cedar",
            "propagation_source": "profile",
            "written_targets": [],
            "session_closed": False,
        }
    return UnifiedRetailDB.model_validate(payload)
