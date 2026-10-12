#!/usr/bin/env python3
"""Validate all four RDS-01 Gate 0 paths without model calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[6] / 'scripts/benchmarks/v3/development/retail_dual_update_sequence/tools'))
PRIMITIVE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34/construction/retail_dual_update_sequence')
EDITION = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/editions/phase_v3_day34')
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from tau2.domains.retail.tools import RetailTools  # noqa: E402
from tau2.registry import registry  # noqa: E402

from src.benchmark_v3.development.retail_dual_update_sequence.candidate_tasks.evaluators.evaluate_rds01 import evaluate_success  # noqa: E402
from src.benchmark_v3.development.retail_dual_update_sequence.environment.environment import DOMAIN_NAME, register_domain  # noqa: E402
from src.benchmark_v3.development.retail_dual_update_sequence.environment.fixture import build_gate0_db  # noqa: E402
from src.benchmark_v3.development.retail_dual_update_sequence.environment.tools import DualUpdateRetailTools  # noqa: E402


SPECS = PRIMITIVE / "candidates/task_specs.json"
TASKS = PRIMITIVE / "candidate_tasks/tasks.json"
RESULT = (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/retail_dual_update_sequence/structural_audit/gate0_validation.json')


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_update(
    tools: DualUpdateRetailTools, spec: dict[str, Any], update: str
) -> None:
    if update == "address":
        tools.modify_pending_order_address(spec["order_id"], **spec["new_address"])
    else:
        tools.modify_pending_order_payment(
            spec["order_id"], spec["new_payment_id"]
        )


def replay_correct(spec: dict[str, Any]) -> dict[str, Any]:
    db = build_gate0_db()
    tools = DualUpdateRetailTools(db)
    context = tools.get_dual_update_context(spec["order_id"])
    assert context["workflow_revision"] == spec["workflow_revision"]
    assert "required_sequence" not in context
    for update in spec["required_sequence"]:
        apply_update(tools, spec, update)
    evaluation = evaluate_success(spec, db.model_dump(mode="json"))
    assert evaluation["success"] is True
    return {
        "sequence": spec["required_sequence"],
        "both_writes_returned_success": True,
        "semantic_success": True,
        "workflow_locked": False,
    }


def replay_wrong(spec: dict[str, Any]) -> dict[str, Any]:
    db = build_gate0_db()
    tools = DualUpdateRetailTools(db)
    wrong_first = spec["wrong_first_update"]
    remaining = "payment" if wrong_first == "address" else "address"
    apply_update(tools, spec, wrong_first)
    committed = db.model_dump(mode="json")
    retry_error = None
    try:
        apply_update(tools, spec, remaining)
    except ValueError as error:
        retry_error = str(error)
    assert retry_error == "Workflow locked after an incompatible first update"
    assert db.model_dump(mode="json") == committed
    evaluation = evaluate_success(spec, committed)
    assert evaluation["success"] is False
    contract = committed["dual_update_contracts"][spec["order_id"]]
    assert contract["completed_updates"] == [wrong_first]
    assert contract["workflow_locked"] is True
    return {
        "first_update": wrong_first,
        "first_write_returned_success": True,
        "second_update": remaining,
        "second_write_rejected": True,
        "first_write_preserved": True,
        "semantic_success": False,
        "workflow_locked": True,
    }


def main() -> None:
    payload = load(SPECS)
    specs = payload["tasks"]
    tasks = load(TASKS)
    assert len(specs) == len(tasks) == 2
    assert {tuple(spec["required_sequence"]) for spec in specs} == {
        ("address", "payment"),
        ("payment", "address"),
    }
    rows = [
        {
            "task_id": spec["task_id"],
            "correct_path": replay_correct(spec),
            "wrong_path": replay_wrong(spec),
        }
        for spec in specs
    ]

    assert DOMAIN_NAME not in registry.get_info().domains
    register_domain(registry)
    isolated = registry.get_env_constructor(DOMAIN_NAME)()
    native = registry.get_env_constructor("retail")()
    assert isinstance(isolated.tools, DualUpdateRetailTools)
    assert type(native.tools) is RetailTools

    result = {
        "status": "READY_FOR_SKILL_NECESSITY_SMOKE",
        "mechanism_id": payload["mechanism_id"],
        "model_calls": 0,
        "formal_tasks_admitted": 0,
        "four_backend_paths": rows,
        "shortcut_wins_out_of_two": {
            "always_address_first": 1,
            "always_payment_first": 1,
        },
        "nonrecoverability": {
            "second_goal_rejected_on_both_wrong_paths": True,
            "first_write_preserved_on_both_wrong_paths": True,
        },
        "isolation": {
            "v3_domain": DOMAIN_NAME,
            "v3_toolkit": type(isolated.tools).__name__,
            "native_domain": native.get_domain_name(),
            "native_toolkit": type(native.tools).__name__,
            "native_source_modified": False,
        },
    }
    (Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_v3_day34/construction/retail_dual_update_sequence/structural_audit').mkdir(parents=True, exist_ok=True)
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS RDS-01 Gate 0: 2 correct sequences + 2 wrong committed first writes")


if __name__ == "__main__":
    main()
