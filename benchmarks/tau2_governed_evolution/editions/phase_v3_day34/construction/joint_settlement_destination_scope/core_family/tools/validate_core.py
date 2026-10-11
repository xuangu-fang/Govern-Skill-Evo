#!/usr/bin/env python3
"""Deterministically validate the JSG-01 Joint Core and shortcut balance."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
CORE = HERE.parent
EDITION = CORE.parents[2]
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from tau2.data_model.tasks import Task  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.joint_settlement_destination_scope.candidate_tasks.evaluators.evaluate_jsg01 import evaluate  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.joint_settlement_destination_scope.environment.fixture import build_core_db  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.latent_settlement_contract.environment.tools import SettlementAirlineTools  # noqa: E402


SPECS = CORE / "candidates/task_specs.json"
TASKS = CORE / "candidate_tasks/tasks.json"
RESULT = CORE / "structural_audit/core_validation.json"
FORMAL_TASKS = EDITION / "benchmark/tasks.json"
EE_TASKS = EDITION / "construction/latent_settlement_contract/core_family/candidate_tasks/tasks.json"
RHP_TASKS = EDITION / "construction/retail_hidden_operational_path/core_family/candidate_tasks/tasks.json"
RAP_TASKS = EDITION / "construction/retail_address_propagation/core_family/candidate_tasks/tasks.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def update(tools: SettlementAirlineTools, spec: dict[str, Any], flight: str) -> None:
    tools.update_reservation_flights(
        reservation_id=spec["reservation_id"],
        cabin="economy",
        flights=[
            {"flight_number": spec["retained_flight"], "date": spec["date"]},
            {"flight_number": flight, "date": spec["date"]},
        ],
        payment_id=spec["payment_id"],
    )


def replay(spec: dict[str, Any], flight: str) -> dict[str, Any]:
    db = build_core_db()
    tools = SettlementAirlineTools(db)
    context = tools.get_settlement_context(spec["reservation_id"])
    assert context["ticketing_channel"] == spec["ticketing_channel"]
    assert "settlement_baseline" not in context
    update(tools, spec, flight)
    committed = db.model_dump(mode="json")
    evaluation = evaluate(spec, committed)
    try:
        update(tools, spec, spec[f"{spec['expected_branch']}_legal"])
    except ValueError as error:
        correction_error = str(error)
    else:
        raise AssertionError("post-commit correction unexpectedly succeeded")
    assert correction_error == "No flight changes remain for this reservation"
    assert db.model_dump(mode="json") == committed
    return {
        "selected_flight": flight,
        "tool_write_succeeded": True,
        "success": evaluation["success"],
        "compliant": evaluation["compliant"],
        "joint_success": evaluation["joint_success"],
        "quadrant": evaluation["quadrant"],
        "observed_change_amount": evaluation["observed_change_amount"],
        "correction_blocked": True,
        "committed_state_preserved": True,
    }


def alternative_preferred_charge(spec: dict[str, Any]) -> int:
    old_total = spec["retained_historical_price"] + spec["replaced_historical_price"]
    if spec["settlement_baseline"] == "retained_historical":
        total = spec["retained_current_price"] + spec["preferred_current_price"]
    else:
        total = spec["retained_historical_price"] + spec["preferred_current_price"]
    return total - old_total


def verify_admission(built: list[dict[str, Any]]) -> None:
    expected = load(EE_TASKS) + load(RHP_TASKS) + load(RAP_TASKS) + built
    assert load(FORMAL_TASKS) == expected
    assert len(expected) == 32


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-admission", action="store_true")
    args = parser.parse_args()
    payload = load(SPECS)
    specs = payload["tasks"]
    built = load(TASKS)
    assert len(specs) == len(built) == payload["task_count"] == 8
    assert [task["id"] for task in built] == [spec["task_id"] for spec in specs]
    for task in built:
        Task.model_validate(task)

    rows = []
    for spec in specs:
        expected = spec["expected_branch"]
        competing = "fallback" if expected == "preferred" else "preferred"
        paths = {
            "CS": replay(spec, spec[f"{expected}_legal"]),
            "CF": replay(spec, spec[f"{competing}_legal"]),
            "VS": replay(spec, spec[f"{expected}_alternate"]),
            "VF": replay(spec, spec[f"{competing}_alternate"]),
        }
        assert {label: path["quadrant"] for label, path in paths.items()} == {
            "CS": "CS", "CF": "CF", "VS": "VS", "VF": "VF"
        }
        assert paths["CS"]["observed_change_amount"] == spec["expected_change_amount"]
        competing_preferred = alternative_preferred_charge(spec)
        assert (competing_preferred <= spec["threshold"]) != (expected == "preferred")
        rows.append(
            {
                "task_id": spec["task_id"],
                "surface": spec["surface"],
                "ticketing_channel": spec["ticketing_channel"],
                "expected_branch": expected,
                "paths": paths,
                "competing_mapping_flips_branch": True,
            }
        )

    combinations = Counter(
        (spec["ticketing_channel"], spec["expected_branch"]) for spec in specs
    )
    assert combinations == {
        ("horizon", "preferred"): 2,
        ("horizon", "fallback"): 2,
        ("summit", "preferred"): 2,
        ("summit", "fallback"): 2,
    }
    surfaces = Counter(spec["surface"] for spec in specs)
    assert surfaces == {1: 2, 2: 2, 3: 2, 4: 2}
    for surface in range(1, 5):
        pair = [spec for spec in specs if spec["surface"] == surface]
        assert {spec["ticketing_channel"] for spec in pair} == {"horizon", "summit"}
        assert {spec["expected_branch"] for spec in pair} == {"preferred", "fallback"}
    parity_combinations = Counter(
        (int(spec["task_id"][-1]) % 2, spec["ticketing_channel"], spec["expected_branch"])
        for spec in specs
    )
    assert set(parity_combinations.values()) == {1}

    text_first_branch = {1: "preferred", 2: "preferred", 3: "fallback", 4: "fallback"}
    text_first_airport_is_legal = {1: True, 2: False, 3: True, 4: False}
    display_first_branch = {
        spec["task_id"]: min(
            (spec["candidate_order"].index("preferred_legal"), "preferred"),
            (spec["candidate_order"].index("fallback_legal"), "fallback"),
        )[1]
        for spec in specs
    }
    shortcuts = {
        "always_preferred": sum(spec["expected_branch"] == "preferred" for spec in specs),
        "always_fallback": sum(spec["expected_branch"] == "fallback" for spec in specs),
        "cheapest_replacement": sum(spec["expected_branch"] == "fallback" for spec in specs),
        "first_branch_in_request": sum(
            spec["expected_branch"] == text_first_branch[spec["surface"]] for spec in specs
        ),
        "first_airport_named_in_expected_branch": sum(
            text_first_airport_is_legal[spec["surface"]] for spec in specs
        ),
        "first_legal_candidate_displayed": sum(
            spec["expected_branch"] == display_first_branch[spec["task_id"]] for spec in specs
        ),
        "odd_id_preferred_even_id_fallback": sum(
            (int(spec["task_id"][-1]) % 2 == 1) == (spec["expected_branch"] == "preferred")
            for spec in specs
        ),
    }
    assert set(shortcuts.values()) == {4}
    assert len({spec["user_id"] for spec in specs}) == 8
    assert len({spec["reservation_id"] for spec in specs}) == 8
    assert len({spec["retained_flight"] for spec in specs}) == 8
    assert len({spec["destination"] for spec in specs}) >= 5

    if args.verify_admission:
        verify_admission(built)
    result = {
        "status": "PASS_READY_FOR_FORMAL_ADMISSION",
        "mechanism_id": payload["mechanism_id"],
        "model_calls": 0,
        "core_task_count": 8,
        "formal_admission_verified": args.verify_admission,
        "all_cs_paths_succeed_and_comply": True,
        "all_cf_paths_commit_then_fail_capability": True,
        "all_vs_paths_commit_then_violate_destination_scope": True,
        "all_vf_paths_commit_then_fail_both_axes": True,
        "all_post_commit_corrections_blocked": True,
        "all_competing_mappings_flip_required_branch": True,
        "combination_counts": {
            f"{channel}_{branch}": count
            for (channel, branch), count in sorted(combinations.items())
        },
        "surface_counts": {str(key): value for key, value in sorted(surfaces.items())},
        "shortcut_wins_out_of_eight": shortcuts,
        "entity_counts": {"users": 8, "reservations": 8, "retained_flights": 8},
        "tasks": rows,
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    stage = " and formal admission" if args.verify_admission else ""
    print(
        f"PASS JSG-01 Joint Core{stage}: 8 tasks × CS/CF/VS/VF; all shortcuts 4/8"
    )


if __name__ == "__main__":
    main()
