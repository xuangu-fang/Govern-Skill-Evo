#!/usr/bin/env python3
"""Deterministically validate the RAP-01 Capability Core."""

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

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_address_propagation.candidate_tasks.evaluators.evaluate_rap01 import evaluate_success  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_address_propagation.environment.fixture import build_gate0_db  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_address_propagation.environment.tools import AddressPropagationRetailTools  # noqa: E402


SPECS = CORE / "candidates/task_specs.json"
TASKS = CORE / "candidate_tasks/tasks.json"
FORMAL_TASKS = EDITION / "benchmark/tasks.json"
EE_TASKS = EDITION / "construction/latent_settlement_contract/core_family/candidate_tasks/tasks.json"
RHP_TASKS = EDITION / "construction/retail_hidden_operational_path/core_family/candidate_tasks/tasks.json"
RESULT = CORE / "structural_audit/core_validation.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_write(tools: AddressPropagationRetailTools, spec: dict[str, Any], target: str) -> None:
    if target == "order":
        tools.modify_pending_order_address(spec["order_id"], **spec["order_address"])
    else:
        tools.modify_user_address(spec["user_id"], **spec["profile_address"])


def replay(spec: dict[str, Any], sequence: list[str]) -> dict[str, Any]:
    db = build_gate0_db()
    tools = AddressPropagationRetailTools(db)
    context = tools.get_address_propagation_context(spec["order_id"])
    assert context["address_contract"] == spec["address_contract"]
    assert "propagation_source" not in context
    for target in sequence:
        apply_write(tools, spec, target)
    committed = db.model_dump(mode="json")
    evaluation = evaluate_success(spec, committed)
    correction_target = "order" if spec["propagation_source"] == "profile" else "profile"
    try:
        apply_write(tools, spec, correction_target)
    except ValueError as error:
        correction_error = str(error)
    else:
        raise AssertionError("Post-session correction unexpectedly succeeded")
    assert correction_error == "Address synchronization session is closed"
    assert db.model_dump(mode="json") == committed
    return {
        "sequence": sequence,
        "both_writes_returned_success": True,
        "semantic_success": evaluation["success"],
        "correction_target": correction_target,
        "correction_rejected": True,
        "committed_state_preserved": True,
    }


def verify_admission(built: list[dict[str, Any]]) -> None:
    formal = load(FORMAL_TASKS)
    expected = load(EE_TASKS) + load(RHP_TASKS) + built
    assert formal[: len(expected)] == expected
    assert len(expected) == 24


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

    tasks_by_id = {task["id"]: task for task in built}
    rows = []
    for spec in specs:
        task = tasks_by_id[spec["task_id"]]
        reason = task["user_scenario"]["instructions"]["reason_for_call"]
        assert reason.index(spec["order_address"]["address1"]) < reason.index(
            spec["profile_address"]["address1"]
        )
        assert [action["name"] for action in task["evaluation_criteria"]["actions"]] == [
            "modify_pending_order_address",
            "modify_user_address",
        ]
        correct = replay(spec, spec["correct_sequence"])
        opposite = replay(spec, spec["wrong_sequence"])
        assert correct["semantic_success"] is True
        assert opposite["semantic_success"] is False
        rows.append(
            {
                "task_id": spec["task_id"],
                "surface": spec["surface"],
                "address_contract": spec["address_contract"],
                "correct_path": correct,
                "opposite_path": opposite,
            }
        )

    contracts = Counter(spec["address_contract"] for spec in specs)
    surfaces = Counter(spec["surface"] for spec in specs)
    surface_contracts = Counter(
        (spec["surface"], spec["address_contract"]) for spec in specs
    )
    assert contracts == {"cedar": 4, "orbit": 4}
    assert surfaces == {1: 2, 2: 2, 3: 2, 4: 2}
    assert all(surface_contracts[(surface, contract)] == 1 for surface in range(1, 5) for contract in ("cedar", "orbit"))
    parity_contracts = Counter(
        (int(spec["task_id"][-1]) % 2, spec["address_contract"]) for spec in specs
    )
    assert set(parity_contracts.values()) == {2}
    assert len({spec["user_id"] for spec in specs}) == 8
    assert len({spec["order_id"] for spec in specs}) == 8
    assert len({spec["product_id"] for spec in specs}) == 8
    assert len(
        {
            spec[target]["address1"]
            for spec in specs
            for target in ("order_address", "profile_address")
        }
    ) == 16
    shortcuts = {
        "always_order_first": contracts["orbit"],
        "always_profile_first": contracts["cedar"],
        "request_text_order": contracts["orbit"],
        "task_id_odd_as_cedar_even_as_orbit": sum(
            (int(spec["task_id"][-1]) % 2 == 1) == (spec["address_contract"] == "cedar")
            for spec in specs
        ),
    }
    assert set(shortcuts.values()) == {4}

    if args.verify_admission:
        verify_admission(built)
    result = {
        "status": "PASS_READY_FOR_FORMAL_ADMISSION",
        "mechanism_id": payload["mechanism_id"],
        "model_calls": 0,
        "core_task_count": 8,
        "formal_admission_verified": args.verify_admission,
        "all_correct_paths_succeed": True,
        "all_opposite_paths_commit_then_fail_semantically": True,
        "all_post_session_corrections_blocked": True,
        "contract_counts": dict(contracts),
        "surface_counts": {str(key): value for key, value in sorted(surfaces.items())},
        "shortcut_wins_out_of_eight": shortcuts,
        "entity_counts": {"users": 8, "orders": 8, "products": 8, "target_addresses": 16, "surfaces": 4},
        "tasks": rows,
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    stage = " and formal admission" if args.verify_admission else ""
    print(f"PASS RAP-01 Core{stage}: 8/8 correct; 8/8 opposite commits fail; shortcuts 4/8")


if __name__ == "__main__":
    main()
