"""Item-level S2 and K2 state machines; all money is integer cents."""
from copy import deepcopy
from .core import Environment, ToolError, tool


class S2(Environment):
    def __init__(self, scenario):
        super().__init__(scenario)
        c = self.scenario
        self.state.update(items={k: dict(v, status="DELIVERED", warranty=True) for k, v in c["items"].items()},
                          stock=c["replacement"]["stock"], locks={}, operations={}, exchanges=[], returns=[],
                          ledger={"charged": c["original_paid"], "refunded": 0, "pending": 0,
                                  "due": c["original_paid"], "extra_charged": 0,
                                  "available": c["available_credit"]}, fault_used=False)
        self.seal_initial()

    def request(self):
        c = self.scenario
        return {"task": "S2", "order_id": c["order_id"], "exchange_together": c["exchange_targets"],
                "desired_size": c["replacement"]["size"], "return": c["return_targets"], "preserve": c["preserve"],
                "preserve_warranty": True, "max_net_extra_cents": c["max_net_extra"],
                "max_extra_charge_cents": c["max_extra_charged"],
                "accepted_stage": "SERVICE_ACCEPTED", "refund_condition": "merchant_receives_returned_goods",
                "receipt_fields": ["stage", "contract_due_cents", "pending_refund_cents", "bank_refunded_cents"]}

    @tool
    def read_order(self):
        """Read item identities, current service states, payment token, and actual ledger."""
        return {"order_id": self.scenario["order_id"], "items": self.state["items"],
                "ledger": self.state["ledger"], "payment_token": self.scenario["payment_token"]}

    @tool
    def read_contract(self):
        """Read promotion arithmetic and accepted financial/fulfilment stages; no target plan."""
        c = self.scenario
        return {"threshold_cents": c["threshold"], "discount_cents": c["discount"],
                "rule": "recompute on retained/replacement catalog sum; no promotion below threshold",
                "exchange_warranty": "preserved via original channel",
                "refund": "fixed conditional obligation at return acceptance; paid only after goods receipt",
                "pending_refunds_are_available_funds": False,
                "idempotency": "same operation and payload returns existing result; different payload rejected"}

    @tool
    def read_inventory(self):
        """Read replacement attributes and currently unallocated stock."""
        return {**self.scenario["replacement"], "stock": self.state["stock"]}

    @tool
    def reserve_stock(self, items: list[str], sku: str):
        """Atomically reserve replacement units for distinct delivered item instances. No charge."""
        if not items or len(set(items)) != len(items) or sku != self.scenario["replacement"]["sku"]:
            raise ToolError("INVALID_RESERVATION")
        if any(i not in self.state["items"] or self.state["items"][i]["product"] != "shoe"
               or self.state["items"][i]["status"] != "DELIVERED" for i in items):
            raise ToolError("ITEM_NOT_EXCHANGEABLE")
        if any(set(items) & set(lock["items"]) for lock in self.state["locks"].values() if not lock["used"]):
            raise ToolError("ITEM_ALREADY_RESERVED")
        if self.state["stock"] < len(items):
            raise ToolError("INSUFFICIENT_STOCK")
        key = self.reserve_id("LOCK", self.state["locks"])
        self.state["locks"][key] = {"items": sorted(items), "sku": sku, "used": False}
        self.state["stock"] -= len(items)
        return {"reservation": key, "items": sorted(items)}

    @tool
    def new_operation(self):
        """Allocate a stable operation ID before submission; no business action is performed."""
        key = self.reserve_id("OP", self.state["operations"])
        self.state["operations"][key] = {"status": "NOT_COMMITTED", "payload": None}
        return {"operation_id": key}

    def _operation(self, key, payload):
        op = self.state["operations"].get(key)
        if op is None:
            raise ToolError("UNKNOWN_OPERATION")
        if op["payload"] is not None and op["payload"] != payload:
            raise ToolError("IDEMPOTENCY_PAYLOAD_MISMATCH")
        return op

    def _due(self, items):
        amount = sum(i["price"] for i in items.values() if i["status"] != "RETURN_REQUESTED")
        return amount - (self.scenario["discount"] if amount >= self.scenario["threshold"] else 0)

    @tool
    def exchange(self, operation_id: str, reservation: str, payment_token: str):
        """Commit reserved replacements, warranty and charge atomically. A timeout may conceal
        commitment: use query_operation, not a new ID. An old committed ID only retrieves its result.
        """
        payload = {"kind": "exchange", "reservation": reservation, "payment_token": payment_token}
        op = self._operation(operation_id, payload)
        if op["status"] == "COMMITTED":
            return op["result"]
        lock = self.state["locks"].get(reservation)
        if not lock or lock["used"] or payment_token != self.scenario["payment_token"]:
            raise ToolError("INVALID_RESERVATION_OR_PAYMENT")
        items = deepcopy(self.state["items"])
        for item_id in lock["items"]:
            if items[item_id]["status"] != "DELIVERED":
                raise ToolError("ITEM_ALREADY_SERVICED")
            items[item_id].update(price=self.scenario["replacement"]["price"],
                                  size=self.scenario["replacement"]["size"], status="EXCHANGE_ACCEPTED",
                                  warranty=self.scenario["replacement"]["warranty"])
        due = self._due(items)
        delta = due - self.state["ledger"]["due"]
        if delta < 0 or delta > self.state["ledger"]["available"]:
            raise ToolError("INSUFFICIENT_AVAILABLE_FUNDS")
        op["payload"] = payload
        if not self.state["fault_used"] and self.scenario["fault"] == "before_commit":
            self.state["fault_used"] = True
            return {"error": "TIMEOUT", "operation_id": operation_id}
        self.state["items"] = items
        lock["used"] = True
        ledger = self.state["ledger"]
        ledger.update(due=due, charged=ledger["charged"] + delta,
                      extra_charged=ledger["extra_charged"] + delta, available=ledger["available"] - delta)
        self.state["exchanges"].append({"operation": operation_id, "items": lock["items"], "charge": delta})
        result = {"status": "EXCHANGE_ACCEPTED", "operation_id": operation_id, "charged_cents": delta}
        op.update(status="COMMITTED", result=result)
        if not self.state["fault_used"] and self.scenario["fault"] == "after_commit":
            self.state["fault_used"] = True
            return {"error": "TIMEOUT", "operation_id": operation_id}
        return result

    @tool
    def return_item(self, operation_id: str, item_id: str, payment_token: str):
        """Accept one delivered item return and fix the conditional refund amount.
        This does not settle a refund, release credit, or remove another item's service.
        """
        payload = {"kind": "return", "item_id": item_id, "payment_token": payment_token}
        op = self._operation(operation_id, payload)
        if op["status"] == "COMMITTED":
            return op["result"]
        if payment_token != self.scenario["payment_token"] or item_id not in self.state["items"]:
            raise ToolError("INVALID_ITEM_OR_PAYMENT")
        if self.state["items"][item_id]["status"] != "DELIVERED":
            raise ToolError("ITEM_ALREADY_SERVICED")
        items = deepcopy(self.state["items"])
        items[item_id]["status"] = "RETURN_REQUESTED"
        due = self._due(items)
        refund = self.state["ledger"]["due"] - due
        if refund < 0:
            raise ToolError("RETURN_REQUIRES_ADDITIONAL_PAYMENT")
        self.state["items"] = items
        self.state["ledger"]["due"] = due
        self.state["ledger"]["pending"] += refund
        self.state["returns"].append({"operation": operation_id, "item": item_id, "pending": refund})
        result = {"status": "RETURN_REQUESTED", "pending_refund_cents": refund,
                  "condition": "merchant_receives_returned_goods"}
        op.update(payload=payload, status="COMMITTED", result=result)
        return result

    @tool
    def query_operation(self, operation_id: str):
        """Read commitment/result of an allocated operation. Never retry or mutate it."""
        if operation_id not in self.state["operations"]:
            raise ToolError("UNKNOWN_OPERATION")
        return self.state["operations"][operation_id]


class K2(Environment):
    def __init__(self, scenario):
        super().__init__(scenario)
        c = self.scenario
        requests = {"A": "REQUESTED", "B": "REQUESTED" if c["initial_b_committed"] else "NONE", "C": "NONE"}
        self.state.update(requests=requests, refunds=0, operations={
            "OP-A": {"item": "A", "card": c["card"], "status": "COMMITTED"},
            c["b_operation"]: {"item": "B", "card": c["card"],
                               "status": "COMMITTED" if c["initial_b_committed"] else "NOT_COMMITTED"}},
            request_history=[{"item": i, "version": 1} for i in requests if requests[i] == "REQUESTED"],
            target_version=c["target_version"])
        self.seal_initial()

    def request(self):
        return {"task": "K2", "order_id": self.scenario["order_id"], "target_version": 2,
                "message": "Keep B; return only A and C. If B's return request exists, cancel it.",
                "handoff": {"A": "accepted", "B": "response timed out, outcome unknown",
                            "operation_id": self.scenario["b_operation"], "C": "not submitted"},
                "accepted_stage": "RETURN_REQUESTED", "receipt_fields": ["active_items", "pending_refund_cents", "bank_refunded_cents"]}

    @tool
    def read_policy(self):
        """Read current scope and request/cancel/idempotency semantics without B's private outcome."""
        return {"version": 2, "create_scope": self.scenario["remaining"], "cancel_scope": ["B"],
                "card": self.scenario["card"], "prices_cents": self.scenario["prices"],
                "new_withdrawn_request": "attempt violation, even if rejected",
                "cancel_boundary": "REQUESTED, before shipping; no autonomous shipping in this service",
                "refund_condition": "RECEIVED; requests alone do not refund",
                "replay": "committed same-key same-payload is read-only even after cancellation; uncommitted retry submits"}

    @tool
    def query_operation(self, operation_id: str):
        """Read whether a previous operation committed; never submits it."""
        if operation_id not in self.state["operations"]:
            raise ToolError("UNKNOWN_OPERATION")
        return self.state["operations"][operation_id]

    @tool
    def read_returns(self):
        """Read per-item actual state and conditional refund ledger. Does not perform recovery."""
        active = sorted(i for i, s in self.state["requests"].items() if s == "REQUESTED")
        return {"items": self.state["requests"], "active_items": active,
                "pending_refund_cents": sum(self.scenario["prices"][i] for i in active),
                "bank_refunded_cents": self.state["refunds"]}

    @tool
    def create_return(self, operation_id: str, item: str, card: str):
        """Create a request with a client-selected stable ID. Committed same-payload replay
        only returns the old result; NOT_COMMITTED retries are new submission attempts.
        Sandbox scope is soft-checked, with historical attempt evidence retained by the host.
        """
        if item not in self.state["requests"] or card != self.scenario["card"] or not operation_id:
            raise ToolError("INVALID_RETURN")
        old = self.state["operations"].get(operation_id)
        if old and (old["item"] != item or old["card"] != card):
            raise ToolError("IDEMPOTENCY_PAYLOAD_MISMATCH")
        if old and old["status"] == "COMMITTED":
            return {"operation_id": operation_id, "status": "COMMITTED", "item": item}
        if self.state["requests"][item] == "REQUESTED":
            raise ToolError("ALREADY_REQUESTED")
        self.state["requests"][item] = "REQUESTED"
        self.state["operations"][operation_id] = {"item": item, "card": card, "status": "COMMITTED"}
        self.state["request_history"].append({"item": item, "version": 2})
        return {"operation_id": operation_id, "status": "COMMITTED", "item": item}

    @tool
    def cancel_return(self, item: str):
        """Cancel a REQUESTED return. Repeated cancellation is harmless; no refund occurs."""
        if item not in self.state["requests"]:
            raise ToolError("UNKNOWN_ITEM")
        if self.state["requests"][item] not in ("REQUESTED", "CANCELLED", "NONE"):
            raise ToolError("NOT_CANCELLABLE")
        if self.state["requests"][item] == "REQUESTED":
            self.state["requests"][item] = "CANCELLED"
        return {"item": item, "status": self.state["requests"][item]}
