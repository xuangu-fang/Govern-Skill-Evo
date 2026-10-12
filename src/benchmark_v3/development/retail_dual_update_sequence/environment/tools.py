"""Native Retail address/payment writes plus the isolated RDS-01 state machine."""

from typing import Any

from tau2.domains.retail.data_model import Order
from tau2.domains.retail.tools import RetailTools
from tau2.environment.toolkit import ToolType, is_tool

from src.benchmark_v3.development.retail_dual_update_sequence.environment.data_model import DualUpdateRetailDB, UpdateKind


class DualUpdateRetailTools(RetailTools):
    db: DualUpdateRetailDB

    def __init__(self, db: DualUpdateRetailDB) -> None:
        super().__init__(db)

    def _before_update(self, order_id: str, update: UpdateKind) -> None:
        contract = self.db.dual_update_contracts[order_id]
        if contract.workflow_locked:
            raise ValueError("Workflow locked after an incompatible first update")
        index = len(contract.completed_updates)
        if index >= len(contract.required_sequence):
            raise ValueError("Dual-update workflow is already complete")
        if index > 0 and update != contract.required_sequence[index]:
            raise ValueError(
                f"Unexpected second update for this workflow; expected {contract.required_sequence[index]}"
            )

    def _after_update(self, order_id: str, update: UpdateKind) -> None:
        contract = self.db.dual_update_contracts[order_id]
        contract.completed_updates.append(update)
        if len(contract.completed_updates) == 1 and update != contract.required_sequence[0]:
            contract.workflow_locked = True

    @is_tool(ToolType.READ)
    def get_dual_update_context(self, order_id: str) -> dict[str, Any]:
        """Return visible workflow revision and progress without its required sequence.

        Args:
            order_id: The pending order id, such as '#RDS1001'.
        """
        self._get_order(order_id)
        contract = self.db.dual_update_contracts[order_id]
        return {
            "order_id": order_id,
            "workflow_revision": contract.workflow_revision,
            "completed_updates": contract.completed_updates,
            "workflow_locked": contract.workflow_locked,
        }

    @is_tool(ToolType.WRITE)
    def modify_pending_order_address(
        self,
        order_id: str,
        address1: str,
        address2: str,
        city: str,
        state: str,
        country: str,
        zip: str,
    ) -> Order:
        """Apply the native pending-order address update under its workflow revision."""
        self._before_update(order_id, "address")
        order = super().modify_pending_order_address(
            order_id, address1, address2, city, state, country, zip
        )
        self._after_update(order_id, "address")
        return order

    @is_tool(ToolType.WRITE)
    def modify_pending_order_payment(
        self, order_id: str, payment_method_id: str
    ) -> Order:
        """Apply the native pending-order payment update under its workflow revision."""
        self._before_update(order_id, "payment")
        order = super().modify_pending_order_payment(order_id, payment_method_id)
        self._after_update(order_id, "payment")
        return order
