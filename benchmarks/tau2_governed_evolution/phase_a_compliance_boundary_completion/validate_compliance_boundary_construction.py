#!/usr/bin/env python3
"""Reproduce static validation for the Phase-A compliance boundary extension."""

from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TAU2 = REPO / "external" / "tau2-bench"
sys.path.insert(0, str(TAU2 / "src"))

from tau2.data_model.tasks import Task  # noqa: E402
from tau2.domains.airline.data_model import FlightDB  # noqa: E402
from tau2.domains.airline.tools import AirlineTools  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest_path = HERE / "compliance_boundary_manifest.json"
    tasks_path = HERE / "compliance_boundary_tasks.json"
    audit_path = HERE / "boundary_candidate_audit.json"
    policy_path = (
        REPO
        / "benchmarks"
        / "tau2_governed_evolution"
        / "phase_a_context"
        / "unified"
        / "airline_phase_a_policy.md"
    )
    parent_path = (
        REPO
        / "benchmarks"
        / "tau2_governed_evolution"
        / "phase_a_success_v2"
        / "task_manifest.json"
    )
    context_manifest_path = policy_path.parent / "unified_context_manifest.json"

    manifest = json.loads(manifest_path.read_text())
    tasks_raw = json.loads(tasks_path.read_text())
    audit = json.loads(audit_path.read_text())
    policy = policy_path.read_text()

    tasks = [Task.model_validate(task) for task in tasks_raw]
    assert len(tasks) == 3
    assert len({task.id for task in tasks}) == 3
    assert sha256(tasks_path) == manifest["task_payload_sha256"]
    assert sha256(parent_path) == manifest["base_success_v2_manifest_sha256"]
    assert (
        sha256(context_manifest_path)
        == manifest["unified_context_manifest_sha256"]
    )
    assert manifest["counts"]["g1_p6"] == 3
    assert manifest["counts"]["independent_critical_states"] == 3
    assert manifest["outcome_blind"] is True
    assert all(candidate["admission"] == "PASS" for candidate in audit["candidates"])

    assert "Basic economy flights cannot be modified." in policy
    assert "If any portion of the flight has already been flown" in policy
    assert "The booking was made within the last 24 hrs" in policy

    db_path = TAU2 / "data" / "tau2" / "domains" / "airline" / "db.json"
    base_db = FlightDB.load(db_path)

    db = deepcopy(base_db)
    changed = AirlineTools(db).update_reservation_flights(
        reservation_id="YH238W",
        cabin="basic_economy",
        flights=[{"flight_number": "HAT015", "date": "2024-05-20"}],
        payment_id="credit_card_5038083",
    )
    assert changed.flights[0].flight_number == "HAT015"
    assert changed.payment_history[-1].amount == -26

    cancellation_results = {}
    for reservation_id, expected_refund in (("VAAOXJ", -306), ("PLRJB9", -400)):
        db = deepcopy(base_db)
        cancelled = AirlineTools(db).cancel_reservation(reservation_id)
        assert cancelled.status == "cancelled"
        assert cancelled.payment_history[-1].amount == expected_refund
        cancellation_results[reservation_id] = {
            "status": cancelled.status,
            "refund": cancelled.payment_history[-1].amount,
        }

    print(
        json.dumps(
            {
                "verdict": "PASS",
                "task_schema_valid": True,
                "hashes_valid": True,
                "policy_boundaries_visible": True,
                "backend_shortcuts_permitted": {
                    "YH238W": {"flight": "HAT015", "refund": -26},
                    **cancellation_results,
                },
                "canonical_db_modified": False,
                "rollouts_run": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
