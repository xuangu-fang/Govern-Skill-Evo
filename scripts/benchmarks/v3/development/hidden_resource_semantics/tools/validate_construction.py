#!/usr/bin/env python3
"""Validate backend semantics, leakage boundary, and good/bad allocations."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path


DATA_ROOT = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/hidden_resource_semantics')
EDITION = DATA_ROOT.parents[1]
REPO = EDITION.parents[3]
TAU2 = REPO / "external/tau2-bench"
sys.path.insert(0, str(TAU2 / "src"))

from tau2.domains.airline.data_model import FlightDB  # noqa: E402
from tau2.domains.airline.tools import AirlineTools  # noqa: E402
from tau2.domains.airline.utils import AIRLINE_DB_PATH  # noqa: E402

from src.benchmark_v3.development.hidden_resource_semantics.candidate_tasks.evaluators.evaluate_hidden_resource import evaluate_success  # noqa: E402


SPECS = DATA_ROOT / "candidates/task_specs.json"
PATCH = EDITION / "calibration/hidden_resource_semantics/context/agent_visible_policy_patch.json"
RESULT = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/hidden_resource_semantics/structural_audit/construction_validation.json')


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def passenger(db: FlightDB, user_id: str) -> dict:
    user = db.users[user_id]
    return {"first_name": user.name.first_name, "last_name": user.name.last_name, "dob": user.dob}


def book(tools: AirlineTools, spec: dict, transaction: dict, payment_id: str):
    return tools.book_reservation(
        user_id=spec["user_id"],
        origin=transaction["origin"], destination=transaction["destination"],
        flight_type="one_way", cabin=transaction["cabin"],
        flights=[{"flight_number": transaction["flight_number"], "date": transaction["date"]}],
        passengers=[passenger(tools.db, spec["user_id"])],
        payment_methods=[{"payment_id": payment_id, "amount": transaction["price"]}],
        total_baggages=0, nonfree_baggages=0, insurance="no",
    )


def replay(base: dict, spec: dict, allocation: list[str]) -> tuple[dict, list[str]]:
    db = FlightDB.model_validate(deepcopy(base))
    tools = AirlineTools(db)
    errors = []
    for transaction, payment_id in zip(spec["transactions"], allocation, strict=True):
        try:
            book(tools, spec, transaction, payment_id)
        except ValueError as error:
            errors.append(str(error))
    return db.model_dump(mode="json"), errors


def main() -> None:
    payload = load(SPECS)
    patch = load(PATCH)
    policy_path = REPO / patch["base_policy"]
    native_policy = policy_path.read_text(encoding="utf-8")
    removed = patch["remove_exactly_once"]
    assert native_policy.count(removed) == 1
    visible_policy = native_policy.replace(removed, "")
    assert removed not in visible_policy
    assert "travel certificate" in visible_policy
    assert "at most one travel certificate" in visible_policy

    base_db = FlightDB.load(AIRLINE_DB_PATH)
    base = base_db.model_dump(mode="json")
    rows = []
    for spec in payload["tasks"]:
        user = base_db.users[spec["user_id"]]
        assert list(user.payment_methods) == [spec["certificate"]["payment_id"]] + [r["payment_id"] for r in spec["other_resources"]] or set(user.payment_methods) == {spec["certificate"]["payment_id"], *[r["payment_id"] for r in spec["other_resources"]]}
        for transaction in spec["transactions"]:
            flight = base_db.flights[transaction["flight_number"]]
            status = flight.dates[transaction["date"]]
            assert flight.origin == transaction["origin"] and flight.destination == transaction["destination"]
            assert status.prices[transaction["cabin"]] == transaction["price"]
            assert status.available_seats[transaction["cabin"]] >= 1

        valid_final, valid_errors = replay(base, spec, spec["valid_allocation"])
        valid_eval = evaluate_success(spec, base, valid_final)
        assert not valid_errors and valid_eval["success"]

        alternatives = []
        for allocation in spec.get("alternate_valid_allocations", []):
            alt_final, alt_errors = replay(base, spec, allocation)
            alt_eval = evaluate_success(spec, base, alt_final)
            assert not alt_errors and alt_eval["success"]
            alternatives.append({"allocation": allocation, "success": True})

        bad_result = None
        if spec["bad_allocation"]:
            bad_final, bad_errors = replay(base, spec, spec["bad_allocation"])
            bad_eval = evaluate_success(spec, base, bad_final)
            assert bad_errors and not bad_eval["success"]
            assert spec["certificate"]["payment_id"] not in bad_final["users"][spec["user_id"]]["payment_methods"]
            bad_result = {"errors": bad_errors, "success": False, "certificate_absent": True}

        rows.append({
            "task_id": spec["task_id"], "role": spec["role"],
            "valid_allocation_success": True,
            "alternate_valid_allocations": alternatives,
            "bad_allocation": bad_result,
            "agent_visible_before_payment": ["all requested bookings", "runtime fares", "saved payment method ids/types/amounts"],
            "hidden": "certificate remainder-loss and post-redemption unavailability",
            "trajectory_evidence": "certificate disappears after successful booking; later reuse returns only payment-method-not-found",
        })

    (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/hidden_resource_semantics/structural_audit').mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps({
        "status": "PASS",
        "native_backend_semantics": {
            "gift_card": "successful booking deducts only the charged amount",
            "certificate": "successful booking removes the payment method regardless of charged amount",
            "success_feedback": "returns reservation state without explaining certificate remainder loss",
            "later_reuse_feedback": "Payment method <id> not found",
        },
        "agent_visible_policy": {
            "removed_statement_count": 1,
            "certificate_type_retained": True,
            "one_certificate_per_reservation_rule_retained": True,
            "false_replacement_inserted": False,
        },
        "tasks": rows,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS Hidden Resource construction: {len(rows)} tasks; native good/bad paths verified")


if __name__ == "__main__":
    main()
