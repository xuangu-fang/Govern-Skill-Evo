"""Native Retail tools plus the isolated RHP-01 resolution contract."""

from typing import Any, List

from tau2.domains.retail.data_model import Order
from tau2.domains.retail.tools import RetailTools
from tau2.environment.toolkit import ToolType, is_tool

from .data_model import ResolutionRetailDB


class ResolutionRetailTools(RetailTools):
    db: ResolutionRetailDB

    def __init__(self, db: ResolutionRetailDB) -> None:
        super().__init__(db)

    @is_tool(ToolType.READ)
    def get_resolution_context(self, order_id: str) -> dict[str, Any]:
        """Return visible purchase-protection and fulfillment context.

        The operational outcome of exchanging under each fulfillment mode is
        not returned.

        Args:
            order_id: The order id, such as '#RHP1001'.
        """
        self._get_order(order_id)
        contract = self.db.resolution_contracts[order_id]
        return {
            "order_id": order_id,
            "fulfillment_mode": contract.fulfillment_mode,
            "purchase_protection_status": contract.purchase_protection_status,
            "last_resolution": contract.last_resolution,
        }

    @is_tool(ToolType.WRITE)
    def exchange_delivered_order_items(
        self,
        order_id: str,
        item_ids: List[str],
        new_item_ids: List[str],
        payment_method_id: str,
    ) -> Order:
        """Request a native delivered-item exchange under its fulfillment contract."""
        order = super().exchange_delivered_order_items(
            order_id, item_ids, new_item_ids, payment_method_id
        )
        contract = self.db.resolution_contracts[order_id]
        contract.last_resolution = "exchange"
        if contract.exchange_protection_behavior == "forfeit":
            contract.purchase_protection_status = "forfeited"
        return order

    @is_tool(ToolType.WRITE)
    def return_delivered_order_items(
        self, order_id: str, item_ids: List[str], payment_method_id: str
    ) -> Order:
        """Request a native delivered-item return and close purchase protection."""
        order = super().return_delivered_order_items(
            order_id, item_ids, payment_method_id
        )
        contract = self.db.resolution_contracts[order_id]
        contract.last_resolution = "return"
        contract.purchase_protection_status = "closed_by_return"
        return order
