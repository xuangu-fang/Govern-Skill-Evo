"""Combine all formal Retail entities under both hidden sidecar schemas."""

from typing import Any

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_address_propagation.environment.fixture import build_gate0_db as build_rap_db
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.environment.fixture import build_gate0_db as build_rhp_db

from .data_model import UnifiedRetailDB


def build_unified_retail_db() -> UnifiedRetailDB:
    rhp = build_rhp_db().model_dump(mode="json")
    rap = build_rap_db().model_dump(mode="json")
    products = {**rhp["products"], **rap["products"]}
    users = {**rhp["users"], **rap["users"]}
    orders = {**rhp["orders"], **rap["orders"]}
    resolution_contracts: dict[str, Any] = dict(rhp["resolution_contracts"])
    address_contracts: dict[str, Any] = dict(rap["address_propagation_contracts"])

    for order_id in orders:
        resolution_contracts.setdefault(
            order_id,
            {
                "fulfillment_mode": "consolidated",
                "exchange_protection_behavior": "preserve",
                "purchase_protection_status": "active",
                "last_resolution": None,
            },
        )
        address_contracts.setdefault(
            order_id,
            {
                "address_contract": "cedar",
                "propagation_source": "profile",
                "written_targets": [],
                "session_closed": False,
            },
        )
    return UnifiedRetailDB.model_validate(
        {
            "products": products,
            "users": users,
            "orders": orders,
            "resolution_contracts": resolution_contracts,
            "address_propagation_contracts": address_contracts,
        }
    )
