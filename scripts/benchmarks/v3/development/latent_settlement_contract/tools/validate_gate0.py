#!/usr/bin/env python3
"""Deterministically validate all four EE-01 Gate 0 backend paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[6] / 'scripts/benchmarks/v3/development/latent_settlement_contract/tools'))
EDITION = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from tau2.domains.airline.tools import AirlineTools  # noqa: E402
from tau2.registry import registry  # noqa: E402

from src.benchmark_v3.development.latent_settlement_contract.candidate_tasks.evaluators.evaluate_latent_settlement import evaluate_success  # noqa: E402
from src.benchmark_v3.development.latent_settlement_contract.environment.environment import DOMAIN_NAME, NATIVE_SETTLEMENT_STATEMENT, V3_NEUTRAL_SETTLEMENT_STATEMENT, register_domain  # noqa: E402
from src.benchmark_v3.development.latent_settlement_contract.environment.fixture import build_gate0_db  # noqa: E402
from src.benchmark_v3.development.latent_settlement_contract.environment.tools import SettlementAirlineTools  # noqa: E402


SPECS = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/latent_settlement_contract/candidates/task_specs.json')
RESULT = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/latent_settlement_contract/structural_audit/gate0_validation.json')


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def update(tools: SettlementAirlineTools, spec: dict[str, Any], choice: str) -> None:
    tools.update_reservation_flights(
        reservation_id=spec["reservation_id"],
        cabin=spec["cabin"],
        flights=[
            {"flight_number": spec["retained_flight"], "date": spec["date"]},
            {"flight_number": choice, "date": spec["date"]},
        ],
        payment_id=spec["payment_id"],
    )


def replay(spec: dict[str, Any], choice: str) -> dict[str, Any]:
    db = build_gate0_db()
    tools = SettlementAirlineTools(db)
    context = tools.get_settlement_context(spec["reservation_id"])
    assert context["ticketing_channel"] == spec["ticketing_channel"]
    assert context["remaining_changes"] == 1
    assert "settlement_baseline" not in context

    update(tools, spec, choice)
    committed = db.model_dump(mode="json")
    evaluation = evaluate_success(spec, committed)
    contract = committed["settlement_contracts"][spec["reservation_id"]]
    assert contract["remaining_changes"] == 0

    corrective_choice = (
        spec["fallback_flight"]
        if choice == spec["preferred_flight"]
        else spec["preferred_flight"]
    )
    retry_error = None
    try:
        update(tools, spec, corrective_choice)
    except ValueError as error:
        retry_error = str(error)
    assert retry_error == "No flight changes remain for this reservation"
    assert db.model_dump(mode="json") == committed

    return {
        "selected_flight": choice,
        "first_write_returned_success": True,
        "semantic_success": evaluation["success"],
        "observed_change_amount": contract["last_change_amount"],
        "remaining_changes": contract["remaining_changes"],
        "corrective_second_write_rejected": True,
        "first_write_preserved_after_rejection": True,
        "evaluation": evaluation,
    }


def main() -> None:
    payload = load(SPECS)
    tasks = payload["tasks"]
    assert len(tasks) == 2
    expected_is_preferred = {
        task["expected_flight"] == task["preferred_flight"] for task in tasks
    }
    assert expected_is_preferred == {True, False}

    rows = []
    for spec in tasks:
        correct = replay(spec, spec["expected_flight"])
        wrong = replay(spec, spec["competing_mapping_choice"])
        assert correct["semantic_success"] is True
        assert wrong["semantic_success"] is False
        rows.append(
            {
                "task_id": spec["task_id"],
                "correct_path": correct,
                "wrong_path": wrong,
            }
        )

    shortcut_wins = {
        "always_preferred": sum(
            task["expected_flight"] == task["preferred_flight"] for task in tasks
        ),
        "always_fallback": sum(
            task["expected_flight"] == task["fallback_flight"] for task in tasks
        ),
        "always_first_candidate": sum(
            task["expected_flight"] == task["candidate_display_order"][0]
            for task in tasks
        ),
        "always_second_candidate": sum(
            task["expected_flight"] == task["candidate_display_order"][1]
            for task in tasks
        ),
    }
    assert set(shortcut_wins.values()) == {1}

    assert DOMAIN_NAME not in registry.get_info().domains
    register_domain(registry)
    isolated = registry.get_env_constructor(DOMAIN_NAME)()
    native = registry.get_env_constructor("airline")()
    assert isolated.get_domain_name() == DOMAIN_NAME
    assert isinstance(isolated.tools, SettlementAirlineTools)
    assert NATIVE_SETTLEMENT_STATEMENT not in isolated.get_policy()
    assert V3_NEUTRAL_SETTLEMENT_STATEMENT in isolated.get_policy()
    assert {"get_settlement_context", "update_reservation_flights"} <= {
        tool.name for tool in isolated.get_tools()
    }
    assert len(registry.get_tasks_loader(DOMAIN_NAME)()) == 8
    assert type(native.tools) is AirlineTools
    assert "settlement" not in native.get_domain_name()

    result = {
        "status": "READY_FOR_SKILL_NECESSITY_SMOKE",
        "mechanism_id": payload["mechanism_id"],
        "model_calls": 0,
        "formal_tasks_admitted": 0,
        "four_backend_paths": rows,
        "nonrecoverability": {
            "second_update_rejected_on_all_paths": True,
            "first_write_preserved_on_all_paths": True,
        },
        "shortcut_wins_out_of_two": shortcut_wins,
        "isolation": {
            "v3_domain": DOMAIN_NAME,
            "v3_toolkit": type(isolated.tools).__name__,
            "process_local_registration_succeeded": True,
            "formal_task_set_registration_succeeded": True,
            "native_settlement_statement_neutralized_in_v3_only": True,
            "native_domain": native.get_domain_name(),
            "native_toolkit": type(native.tools).__name__,
            "native_source_modified": False,
        },
    }
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS EE-01 Gate 0: 2 correct + 2 wrong committed paths; retries blocked")


if __name__ == "__main__":
    main()
