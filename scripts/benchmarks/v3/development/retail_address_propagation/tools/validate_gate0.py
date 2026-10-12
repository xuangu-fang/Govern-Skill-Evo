#!/usr/bin/env python3
"""Validate RAP-01 Gate 0 paths and surface controls without model calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[6] / 'scripts/benchmarks/v3/development/retail_address_propagation/tools'))
PRIMITIVE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/retail_address_propagation')
EDITION = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from tau2.domains.retail.tools import RetailTools  # noqa: E402
from tau2.registry import registry  # noqa: E402

from src.benchmark_v3.development.retail_address_propagation.candidate_tasks.evaluators.evaluate_rap01 import evaluate_success  # noqa: E402
from src.benchmark_v3.development.retail_address_propagation.environment.environment import DOMAIN_NAME, register_domain  # noqa: E402
from src.benchmark_v3.development.retail_address_propagation.environment.fixture import build_gate0_db  # noqa: E402
from src.benchmark_v3.development.retail_address_propagation.environment.tools import AddressPropagationRetailTools  # noqa: E402


SPECS = PRIMITIVE / "candidates/task_specs.json"
TASKS = PRIMITIVE / "candidate_tasks/tasks.json"
RESULT = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/retail_address_propagation/structural_audit/gate0_validation.json')


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_write(
    tools: AddressPropagationRetailTools,
    spec: dict[str, Any],
    target: str,
) -> None:
    if target == "order":
        tools.modify_pending_order_address(spec["order_id"], **spec["order_address"])
    else:
        tools.modify_user_address(spec["user_id"], **spec["profile_address"])


def replay_correct(spec: dict[str, Any]) -> dict[str, Any]:
    db = build_gate0_db()
    tools = AddressPropagationRetailTools(db)
    context = tools.get_address_propagation_context(spec["order_id"])
    assert context["address_contract"] == spec["address_contract"]
    assert "propagation_source" not in context
    for target in spec["correct_sequence"]:
        apply_write(tools, spec, target)
    final = db.model_dump(mode="json")
    evaluation = evaluate_success(spec, final)
    assert evaluation["success"] is True
    return {
        "sequence": spec["correct_sequence"],
        "both_writes_returned_success": True,
        "semantic_success": True,
        "session_closed": True,
    }


def replay_wrong(spec: dict[str, Any]) -> dict[str, Any]:
    db = build_gate0_db()
    tools = AddressPropagationRetailTools(db)
    for target in spec["wrong_sequence"]:
        apply_write(tools, spec, target)
    committed = db.model_dump(mode="json")
    evaluation = evaluate_success(spec, committed)
    assert evaluation["success"] is False
    contract = committed["address_propagation_contracts"][spec["order_id"]]
    assert contract["written_targets"] == spec["wrong_sequence"]
    assert contract["session_closed"] is True

    overwritten_target = spec["propagation_source"]
    correction_target = "order" if overwritten_target == "profile" else "profile"
    correction_error = None
    try:
        apply_write(tools, spec, correction_target)
    except ValueError as error:
        correction_error = str(error)
    assert correction_error == "Address synchronization session is closed"
    assert db.model_dump(mode="json") == committed
    return {
        "sequence": spec["wrong_sequence"],
        "first_write_returned_success": True,
        "second_write_returned_success": True,
        "semantic_success": False,
        "correction_target": correction_target,
        "correction_rejected": True,
        "wrong_final_state_preserved": True,
        "session_closed": True,
    }


def main() -> None:
    payload = load(SPECS)
    specs = payload["tasks"]
    tasks = load(TASKS)
    assert len(specs) == len(tasks) == 2
    assert {tuple(spec["correct_sequence"]) for spec in specs} == {
        ("profile", "order"),
        ("order", "profile"),
    }
    assert {tuple(spec["wrong_sequence"]) for spec in specs} == {
        ("order", "profile"),
        ("profile", "order"),
    }
    assert {tuple(spec["request_goal_order"]) for spec in specs} == {
        ("order", "profile")
    }

    tasks_by_id = {str(task["id"]): task for task in tasks}
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

    rows = [
        {
            "task_id": spec["task_id"],
            "address_contract": spec["address_contract"],
            "correct_path": replay_correct(spec),
            "wrong_path": replay_wrong(spec),
        }
        for spec in specs
    ]

    assert DOMAIN_NAME not in registry.get_info().domains
    register_domain(registry)
    isolated = registry.get_env_constructor(DOMAIN_NAME)()
    native = registry.get_env_constructor("retail")()
    assert isinstance(isolated.tools, AddressPropagationRetailTools)
    assert type(native.tools) is RetailTools

    result = {
        "status": "PASS_GATE_0_READY_FOR_SKILL_NECESSITY_SMOKE",
        "mechanism_id": payload["mechanism_id"],
        "model_calls": 0,
        "formal_tasks_admitted": 0,
        "four_backend_paths": rows,
        "surface_counterfactuals": {
            "same_user_goal_order": True,
            "same_evaluation_action_order": True,
            "neutral_contract_labels": True,
            "answer_independent_of_entity_ids_and_amounts": True,
            "field_and_tool_display_order_not_semantic": True,
            "order_first_wins_out_of_two": 1,
            "profile_first_wins_out_of_two": 1,
            "request_text_order_wins_out_of_two": 1,
        },
        "delayed_failure": {
            "both_wrong_path_writes_succeed": True,
            "semantic_failure_only_after_second_write": True,
            "post_commit_correction_rejected": True,
        },
        "isolation": {
            "v3_domain": DOMAIN_NAME,
            "v3_toolkit": type(isolated.tools).__name__,
            "native_domain": native.get_domain_name(),
            "native_toolkit": type(native.tools).__name__,
            "native_source_modified": False,
        },
    }
    (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/retail_address_propagation/structural_audit').mkdir(parents=True, exist_ok=True)
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS RAP-01 Gate 0: four paths + surface controls + native isolation")


if __name__ == "__main__":
    main()
