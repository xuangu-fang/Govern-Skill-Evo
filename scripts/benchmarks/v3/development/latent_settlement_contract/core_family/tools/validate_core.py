#!/usr/bin/env python3
"""Deterministically validate every admitted EE-01 Core task and shortcut balance."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[7] / 'scripts/benchmarks/v3/development/latent_settlement_contract/core_family/tools'))
CORE = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/latent_settlement_contract/core_family')
EDITION = CORE.parents[2]
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from src.benchmark_v3.development.latent_settlement_contract.candidate_tasks.evaluators.evaluate_latent_settlement import evaluate_success  # noqa: E402
from src.benchmark_v3.development.latent_settlement_contract.environment.fixture import build_gate0_db  # noqa: E402
from src.benchmark_v3.development.latent_settlement_contract.environment.tools import SettlementAirlineTools  # noqa: E402


SPECS = CORE / "candidates/task_specs.json"
TASKS = CORE / "candidate_tasks/tasks.json"
FORMAL_TASKS = EDITION / "benchmark/tasks.json"
RESULT = (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/latent_settlement_contract/core_family/structural_audit/core_validation.json')


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def update(tools: SettlementAirlineTools, spec: dict[str, Any], choice: str) -> None:
    tools.update_reservation_flights(
        reservation_id=spec["reservation_id"],
        cabin="economy",
        flights=[
            {"flight_number": spec["retained_flight"], "date": spec["date"]},
            {"flight_number": choice, "date": spec["date"]},
        ],
        payment_id=spec["payment_id"],
    )


def replay(spec: dict[str, Any], choice: str) -> dict[str, Any]:
    db = build_gate0_db()
    tools = SettlementAirlineTools(db)
    visible = tools.get_settlement_context(spec["reservation_id"])
    assert visible["ticketing_channel"] == spec["ticketing_channel"]
    assert "settlement_baseline" not in visible
    update(tools, spec, choice)
    committed = db.model_dump(mode="json")
    evaluation = evaluate_success(spec, committed)
    retry_error = None
    try:
        update(tools, spec, spec["expected_flight"])
    except ValueError as error:
        retry_error = str(error)
    assert retry_error == "No flight changes remain for this reservation"
    assert db.model_dump(mode="json") == committed
    return {
        "selected_flight": choice,
        "tool_write_succeeded": True,
        "semantic_success": evaluation["success"],
        "observed_change_amount": evaluation["observed_change_amount"],
        "correction_blocked": True,
    }


def alternative_preferred_charge(spec: dict[str, Any]) -> int:
    old_total = spec["retained_historical_price"] + spec["replaced_historical_price"]
    if spec["settlement_baseline"] == "retained_historical":
        alternative_total = (
            spec["retained_current_price"] + spec["preferred_current_price"]
        )
    else:
        alternative_total = (
            spec["retained_historical_price"] + spec["preferred_current_price"]
        )
    return alternative_total - old_total


def main() -> None:
    payload = load(SPECS)
    specs = payload["tasks"]
    built = load(TASKS)
    formal = load(FORMAL_TASKS)
    formal_ee = [task for task in formal if task["id"].startswith("EE-01-C")]
    assert len(specs) == len(built) == len(formal_ee) == payload["task_count"] == 8
    assert built == formal_ee
    assert [task["id"] for task in formal_ee] == [spec["task_id"] for spec in specs]

    rows = []
    for spec in specs:
        correct = replay(spec, spec["expected_flight"])
        wrong = replay(spec, spec["competing_mapping_choice"])
        assert correct["semantic_success"] is True
        assert correct["observed_change_amount"] == spec["expected_change_amount"]
        assert wrong["semantic_success"] is False

        expected_preferred = spec["expected_flight"] == spec["preferred_flight"]
        alternative_preferred = alternative_preferred_charge(spec)
        alternative_would_choose_preferred = alternative_preferred <= spec["threshold"]
        assert alternative_would_choose_preferred != expected_preferred
        rows.append(
            {
                "task_id": spec["task_id"],
                "ticketing_channel": spec["ticketing_channel"],
                "expected_branch": "preferred" if expected_preferred else "fallback",
                "correct_path": correct,
                "opposite_path": wrong,
                "preferred_charge_under_competing_mapping": alternative_preferred,
                "competing_mapping_flips_branch": True,
            }
        )

    combinations = Counter(
        (row["ticketing_channel"], row["expected_branch"]) for row in rows
    )
    assert combinations == {
        ("horizon", "preferred"): 2,
        ("horizon", "fallback"): 2,
        ("summit", "preferred"): 2,
        ("summit", "fallback"): 2,
    }
    surface_branches = Counter(
        (
            spec["surface"],
            "preferred" if spec["expected_flight"] == spec["preferred_flight"] else "fallback",
        )
        for spec in specs
    )
    surface_channels = Counter(
        (spec["surface"], spec["ticketing_channel"]) for spec in specs
    )
    assert set(surface_branches.values()) == {1}
    assert set(surface_channels.values()) == {1}
    shortcut_wins = {
        "always_preferred": sum(row["expected_branch"] == "preferred" for row in rows),
        "always_fallback": sum(row["expected_branch"] == "fallback" for row in rows),
        "treat_all_as_horizon": sum(
            (row["ticketing_channel"] == "horizon") for row in rows
        ),
        "treat_all_as_summit": sum(
            (row["ticketing_channel"] == "summit") for row in rows
        ),
    }
    assert set(shortcut_wins.values()) == {4}

    result = {
        "status": "PASS_ADMITTED_CAPABILITY_CORE",
        "mechanism_id": payload["mechanism_id"],
        "model_calls": 0,
        "formal_task_count": len(rows),
        "all_correct_paths_succeed": True,
        "all_opposite_paths_commit_then_fail_semantically": True,
        "all_corrections_blocked": True,
        "all_competing_mappings_flip_the_required_branch": True,
        "combination_counts": {
            f"{channel}_{branch}": count
            for (channel, branch), count in sorted(combinations.items())
        },
        "shortcut_wins_out_of_eight": shortcut_wins,
        "every_surface_spans_both_channels_and_branches": True,
        "tasks": rows,
    }
    (Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/latent_settlement_contract/core_family/structural_audit').mkdir(parents=True, exist_ok=True)
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS EE-01 Core: 8/8 correct; 8/8 opposite commits fail; shortcuts 4/8")


if __name__ == "__main__":
    main()
