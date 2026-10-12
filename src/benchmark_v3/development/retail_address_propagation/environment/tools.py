"""Native Retail address writes plus isolated RAP-01 propagation semantics."""

from copy import deepcopy
from typing import Any

from tau2.domains.retail.data_model import Order, User
from tau2.domains.retail.tools import RetailTools
from tau2.environment.toolkit import ToolType, is_tool

from src.benchmark_v3.development.retail_address_propagation.environment.data_model import AddressPropagationRetailDB, AddressTarget


class AddressPropagationRetailTools(RetailTools):
    db: AddressPropagationRetailDB

    def __init__(self, db: AddressPropagationRetailDB) -> None:
        super().__init__(db)

    def _order_for_user(self, user_id: str) -> str:
        user = self._get_user(user_id)
        candidates = [
            order_id
            for order_id in user.orders
            if order_id in self.db.address_propagation_contracts
        ]
        if len(candidates) != 1:
            raise ValueError("Expected one active address synchronization session")
        return candidates[0]

    def _before_write(self, order_id: str, target: AddressTarget) -> None:
        contract = self.db.address_propagation_contracts[order_id]
        if contract.session_closed:
            raise ValueError("Address synchronization session is closed")
        if target in contract.written_targets:
            raise ValueError("Address target already written in this session")

    def _after_write(self, order_id: str, target: AddressTarget) -> None:
        contract = self.db.address_propagation_contracts[order_id]
        contract.written_targets.append(target)
        if len(contract.written_targets) == 2:
            contract.session_closed = True

    @is_tool(ToolType.READ)
    def get_address_propagation_context(self, order_id: str) -> dict[str, Any]:
        """Return the visible contract label and synchronization progress.

        Args:
            order_id: The pending order id, such as '#RAP1001'.
        """
        self._get_order(order_id)
        contract = self.db.address_propagation_contracts[order_id]
        return {
            "order_id": order_id,
            "address_contract": contract.address_contract,
            "written_targets": contract.written_targets,
            "session_closed": contract.session_closed,
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
        """Apply the native pending-order address write in its sync session."""
        self._before_write(order_id, "order")
        order = super().modify_pending_order_address(
            order_id, address1, address2, city, state, country, zip
        )
        contract = self.db.address_propagation_contracts[order_id]
        if contract.propagation_source == "order":
            self._get_user(order.user_id).address = deepcopy(order.address)
        self._after_write(order_id, "order")
        return order

    @is_tool(ToolType.WRITE)
    def modify_user_address(
        self,
        user_id: str,
        address1: str,
        address2: str,
        city: str,
        state: str,
        country: str,
        zip: str,
    ) -> User:
        """Apply the native profile-address write in its sync session."""
        order_id = self._order_for_user(user_id)
        self._before_write(order_id, "profile")
        user = super().modify_user_address(
            user_id, address1, address2, city, state, country, zip
        )
        contract = self.db.address_propagation_contracts[order_id]
        if contract.propagation_source == "profile":
            self._get_order(order_id).address = deepcopy(user.address)
        self._after_write(order_id, "profile")
        return user
