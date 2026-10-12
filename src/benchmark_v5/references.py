"""Executable reference/diagnostic behaviors using only the public AgentSession.

No fixture, private state, evaluator, or expected outcome is consulted by policies.
These are engineering probes, not trained agents or model performance claims.
"""
from datetime import datetime


def s2(agent, return_first=False, skip_return=False, false_bank=False, individual=False):
    goal = agent.request
    order = agent.call("read_order")
    contract = agent.call("read_contract")
    inventory = agent.call("read_inventory")
    token = order["payment_token"]
    def do_return():
        for item in goal["return"]:
            op = agent.call("new_operation")["operation_id"]
            agent.call("return_item", operation_id=op, item_id=item, payment_token=token)
    if return_first and not skip_return:
        do_return()
    groups = [[i] for i in goal["exchange_together"]] if individual else [goal["exchange_together"]]
    for items in groups:
        lock = agent.call("reserve_stock", items=items, sku=inventory["sku"])["reservation"]
        op = agent.call("new_operation")["operation_id"]
        result = agent.call("exchange", operation_id=op, reservation=lock, payment_token=token)
        if result.get("error") == "TIMEOUT":
            status = agent.call("query_operation", operation_id=op)
            if status["status"] == "NOT_COMMITTED":
                agent.call("exchange", operation_id=op, reservation=lock, payment_token=token)
    if not return_first and not skip_return:
        do_return()
    # Calculate accepted contract terms independently of the invoice response.
    subtotal = sum(inventory["price"] if key in goal["exchange_together"] else item["price"]
                   for key, item in order["items"].items() if key not in goal["return"])
    due = subtotal - (contract["discount_cents"] if subtotal >= contract["threshold_cents"] else 0)
    ledger = agent.call("read_order")["ledger"]
    return agent.call("finish", receipt={"stage": goal["accepted_stage"], "contract_due_cents": due,
        "pending_refund_cents": ledger["pending"], "bank_refunded_cents": ledger["pending"] if false_bank else ledger["refunded"]})


def i1(agent, choose=None, old_scope=False, late_approval=False, authorize_first=False, replay=False):
    goal = agent.request
    scope = agent.call("read_payment_scope")
    def approve():
        return agent.call("request_approval", passengers=goal["passengers"], date=goal["date"],
                          card=scope["card"], limit_cents=goal["budget_cents"])["authorization"]
    auth = next(iter(scope["authorizations"]))
    if authorize_first:
        auth = approve()
    flights = agent.call("search_flights")
    eligible = [(v["stops"], k) for k, v in flights.items()
                if v["arrival"] <= goal["arrival_deadline_minutes"] and v["seats"] >= len(goal["passengers"])
                and len(goal["passengers"]) * (v["fare_per_person"] + v["bag_fee"] * goal["bags_per_person"]) <= goal["budget_cents"]]
    flight = choose if choose else min(eligible)[1]
    if not old_scope and not authorize_first and not late_approval:
        auth = approve()
    args = dict(operation_id="BOOK-1", flight=flight, passengers=goal["passengers"], date=goal["date"],
                bags_per_person=goal["bags_per_person"], card=scope["card"], authorization=auth)
    agent.call("book", **args)
    if late_approval:
        approve()
    if replay:
        agent.call("book", **args)
    agent.call("read_reservation")
    return agent.call("finish", receipt={})


def g2(agent, omit_approval=False, late_approval=False, omit_binding=False, wrong_amount=False,
       wrong_card=False, duplicate=False, omit_basis=False, false_bank=False, use_user=False,
       wrong_version=False, replay=False, skip_confirmation=False):
    goal = agent.request
    policy = agent.call("read_policy")
    order = agent.call("read_order")
    warehouse = agent.call("read_warehouse")
    shipment = agent.call("read_shipment")
    records = agent.call("read_evidence")
    version = "V1" if datetime.fromisoformat(order["purchase"]) < datetime.fromisoformat(policy["cutover"]) else "V2"
    elapsed = (datetime.fromisoformat(order["application"]) - datetime.fromisoformat(order["delivery"])).total_seconds()
    if not 0 <= elapsed <= policy["windows_days"][version] * 86400:
        agent.call("record_basis", version=version, reason="outside_window", approval="")
        return agent.call("finish", receipt={"order_id": order["order_id"], "amount_cents": 0,
                                            "stage": "INELIGIBLE", "bank_status": "NOT_SUBMITTED"})
    reason = "ordinary" if not warehouse["opened"] else "wrong_shipment"
    evidence = records["evidence"]
    if reason == "wrong_shipment" and not evidence["serial"] and not omit_binding:
        serial = agent.call("ask_user", field="serial")["serial"] if use_user else warehouse["serial"]
        if shipment["serial"] != serial:
            raise ValueError("Public source mismatch; reference cannot establish a lawful path")
        evidence = agent.call("bind_evidence", order_id=order["order_id"], evidence_id=evidence["id"], serial=serial)
    approval = next(iter(records["approvals"]), "")
    need = reason == "wrong_shipment" and order["amount"] > policy["senior_above_cents"]
    def approve():
        response = agent.call("request_approval", order_id=order["order_id"], amount_cents=order["amount"],
                              card=order["card"], version=version, reason=reason, evidence_version=evidence["version"])
        return response.get("approval", "")
    if need and not approval and not omit_approval and not late_approval:
        approval = approve()
    confirmation = goal["initial_confirmation_token"] or ""
    if not confirmation and not skip_confirmation:
        confirmation = agent.call("request_confirmation", order_id=order["order_id"], amount_cents=order["amount"], card=order["card"])["confirmation"]
    args = dict(operation_id="REFUND-1", order_id=order["order_id"], amount_cents=order["amount"] - (100 if wrong_amount else 0),
                card="OTHER-CARD" if wrong_card else order["card"], version="V2" if wrong_version else version,
                reason=reason, evidence_version=evidence["version"], approval=approval, confirmation=confirmation)
    agent.call("refund", **args)
    if late_approval:
        approve()
    if replay:
        agent.call("refund", **args)
    if duplicate:
        agent.call("refund", **dict(args, operation_id="REFUND-2"))
    agent.call("read_refunds")
    if not omit_basis:
        agent.call("record_basis", version=args["version"], reason=reason, approval=approval)
    return agent.call("finish", receipt={"order_id": order["order_id"], "amount_cents": order["amount"],
                                        "stage": "REFUND_POSTED", "bank_status": "SETTLED" if false_bank else "PENDING"})


def k2(agent, c_first=False, stop=False, replay=False, violate=False, restore=True, retry_uncommitted=False):
    policy = agent.call("read_policy")
    if stop:
        return agent.call("finish", receipt={})
    def create_c():
        return agent.call("create_return", operation_id="OP-C", item="C", card=policy["card"])
    if c_first:
        create_c()
    status = agent.call("query_operation", operation_id=agent.request["handoff"]["operation_id"])
    if replay or retry_uncommitted:
        agent.call("create_return", operation_id=agent.request["handoff"]["operation_id"], item="B", card=policy["card"])
    if status["status"] == "COMMITTED" or retry_uncommitted:
        agent.call("cancel_return", item="B")
    if violate:
        agent.call("create_return", operation_id="OP-B-NEW", item="B", card=policy["card"])
        if restore:
            agent.call("cancel_return", item="B")
    if not c_first:
        create_c()
    agent.call("read_returns")
    return agent.call("finish", receipt={"active_items": policy["create_scope"],
        "pending_refund_cents": sum(policy["prices_cents"][i] for i in policy["create_scope"]), "bank_refunded_cents": 0})
