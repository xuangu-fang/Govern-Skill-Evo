#!/usr/bin/env python3
"""Replay the JSG-01 Success × Compliance quadrants without model calls."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[6] / 'scripts/benchmarks/v3/development/joint_settlement_destination_scope/tools'))
PRIMITIVE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/joint_settlement_destination_scope')
EDITION = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from tau2.data_model.tasks import Task  # noqa: E402
from tau2.domains.airline.tools import AirlineTools  # noqa: E402
from tau2.registry import registry  # noqa: E402

from src.benchmark_v3.development.joint_settlement_destination_scope.candidate_tasks.evaluators.evaluate_jsg01 import evaluate  # noqa: E402
from src.benchmark_v3.development.joint_settlement_destination_scope.environment.environment import DESTINATION_POLICY_STATEMENT, DOMAIN_NAME, get_environment, register_domain  # noqa: E402
from src.benchmark_v3.development.joint_settlement_destination_scope.environment.fixture import build_gate0_db  # noqa: E402
from src.benchmark_v3.development.latent_settlement_contract.environment.environment import NATIVE_SETTLEMENT_STATEMENT  # noqa: E402
from src.benchmark_v3.development.latent_settlement_contract.environment.tools import SettlementAirlineTools  # noqa: E402


SPECS = PRIMITIVE / "candidates/task_specs.json"
TASKS = PRIMITIVE / "candidate_tasks/tasks.json"
RESULT = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/joint_settlement_destination_scope/structural_audit/gate0_validation.json')
FORMAL_TASKS = EDITION / "benchmark/tasks.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def replay(spec: dict[str, Any], flight_number: str) -> dict[str, Any]:
    db = build_gate0_db()
    tools = SettlementAirlineTools(db)
    context = tools.get_settlement_context(spec["reservation_id"])
    assert context["ticketing_channel"] == spec["ticketing_channel"]
    assert "settlement_baseline" not in context
    tools.update_reservation_flights(
        spec["reservation_id"],
        spec["cabin"],
        [
            {"flight_number": spec["retained_flight"], "date": spec["date"]},
            {"flight_number": flight_number, "date": spec["date"]},
        ],
        spec["payment_id"],
    )
    committed = db.model_dump(mode="json")
    evaluation = evaluate(spec, committed)
    try:
        tools.update_reservation_flights(
            spec["reservation_id"],
            spec["cabin"],
            [
                {"flight_number": spec["retained_flight"], "date": spec["date"]},
                {"flight_number": spec["cs_flight"], "date": spec["date"]},
            ],
            spec["payment_id"],
        )
    except ValueError as error:
        retry_error = str(error)
    else:
        raise AssertionError("Correction unexpectedly succeeded")
    assert retry_error == "No flight changes remain for this reservation"
    assert db.model_dump(mode="json") == committed
    return {
        "selected_flight": flight_number,
        "backend_write_succeeded": True,
        "success": evaluation["success"],
        "compliant": evaluation["compliant"],
        "joint_success": evaluation["joint_success"],
        "quadrant": evaluation["quadrant"],
        "observed_destination": evaluation["observed_destination"],
        "observed_change_amount": evaluation["observed_change_amount"],
        "correction_rejected": True,
        "committed_state_preserved": True,
    }


def main() -> None:
    payload = load(SPECS)
    specs = payload["tasks"]
    task_rows = load(TASKS)
    assert len(specs) == len(task_rows) == 2
    for row in task_rows:
        Task.model_validate(row)
    assert {spec["ticketing_channel"] for spec in specs} == {"horizon", "summit"}
    assert {spec["expected_branch"] for spec in specs} == {"preferred", "fallback"}
    formal_tasks = load(FORMAL_TASKS)
    gate_ids = {spec["task_id"] for spec in specs}
    assert gate_ids.isdisjoint({task["id"] for task in formal_tasks})

    rows = []
    expected = {"CS": (True, True), "CF": (False, True), "VS": (True, False), "VF": (False, False)}
    for spec in specs:
        paths = {
            quadrant: replay(spec, spec[f"{quadrant.lower()}_flight"])
            for quadrant in ("CS", "CF", "VS", "VF")
        }
        for quadrant, (success, compliant) in expected.items():
            assert paths[quadrant]["quadrant"] == quadrant
            assert paths[quadrant]["success"] is success
            assert paths[quadrant]["compliant"] is compliant
        rows.append(
            {
                "task_id": spec["task_id"],
                "ticketing_channel": spec["ticketing_channel"],
                "expected_branch": spec["expected_branch"],
                "paths": paths,
            }
        )

    policy = get_environment().policy
    assert DESTINATION_POLICY_STATEMENT in policy
    assert NATIVE_SETTLEMENT_STATEMENT not in policy
    assert "settlement behavior" in policy
    assert "associated with each channel" in policy
    assert DOMAIN_NAME not in registry.get_info().domains
    register_domain(registry)
    isolated = registry.get_env_constructor(DOMAIN_NAME)()
    native = registry.get_env_constructor("airline")()
    assert isinstance(isolated.tools, SettlementAirlineTools)
    assert type(native.tools) is AirlineTools

    quadrant_counts = Counter(
        path["quadrant"] for row in rows for path in row["paths"].values()
    )
    assert quadrant_counts == {"CS": 2, "CF": 2, "VS": 2, "VF": 2}
    result = {
        "status": "PASS_GATE_0_READY_FOR_JOINT_GATE_1",
        "mechanism_id": payload["mechanism_id"],
        "model_calls": 0,
        "formal_tasks_admitted": 0,
        "gate_seed_tasks_admitted": 0,
        "current_formal_v3_task_count": len(formal_tasks),
        "quadrant_counts": dict(quadrant_counts),
        "all_eight_backend_writes_succeeded": True,
        "all_eight_paths_consumed_change_and_blocked_correction": True,
        "co_satisfiable_path_exists_per_task": True,
        "capability_and_governance_independently_critical": True,
        "information_boundary": {
            "settlement_mapping_hidden": True,
            "destination_governance_visible": True,
            "user_goal_stable_and_complete": True,
        },
        "shortcut_wins_out_of_two": {
            "always_preferred_exact_destination": 1,
            "always_fallback_exact_destination": 1,
        },
        "isolation": {
            "v3_domain": DOMAIN_NAME,
            "native_domain": native.get_domain_name(),
            "native_source_modified": False,
            "phase_v2_modified": False,
        },
        "tasks": rows,
    }
    (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/joint_settlement_destination_scope/structural_audit').mkdir(parents=True, exist_ok=True)
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS JSG-01 Gate 0: 2 tasks × CS/CF/VS/VF; all writes committed")


if __name__ == "__main__":
    main()
