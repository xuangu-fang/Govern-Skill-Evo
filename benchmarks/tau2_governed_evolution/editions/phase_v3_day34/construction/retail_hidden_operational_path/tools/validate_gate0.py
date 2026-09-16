#!/usr/bin/env python3
"""Validate all four committed RHP-01 Gate 0 paths without model calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PRIMITIVE = HERE.parent
EDITION = HERE.parents[2]
REPO = EDITION.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from tau2.domains.retail.tools import RetailTools  # noqa: E402
from tau2.registry import registry  # noqa: E402

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.candidate_tasks.evaluators.evaluate_rhp01 import evaluate_success  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.environment.environment import DOMAIN_NAME, register_domain  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.environment.fixture import build_gate0_db  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.environment.tools import ResolutionRetailTools  # noqa: E402


SPECS = PRIMITIVE / "candidates/task_specs.json"
RESULT = PRIMITIVE / "structural_audit/gate0_validation.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(tools: ResolutionRetailTools, spec: dict[str, Any], choice: str) -> None:
    if choice == "exchange":
        tools.exchange_delivered_order_items(
            spec["order_id"],
            [spec["old_item_id"]],
            [spec["new_item_id"]],
            spec["payment_id"],
        )
    else:
        tools.return_delivered_order_items(
            spec["order_id"], [spec["old_item_id"]], spec["payment_id"]
        )


def replay(spec: dict[str, Any], choice: str) -> dict[str, Any]:
    db = build_gate0_db()
    tools = ResolutionRetailTools(db)
    context = tools.get_resolution_context(spec["order_id"])
    assert context["fulfillment_mode"] == spec["fulfillment_mode"]
    assert context["purchase_protection_status"] == "active"
    assert "exchange_protection_behavior" not in context

    resolve(tools, spec, choice)
    committed = db.model_dump(mode="json")
    evaluation = evaluate_success(spec, committed)
    opposite = "return" if choice == "exchange" else "exchange"
    retry_error = None
    try:
        resolve(tools, spec, opposite)
    except ValueError as error:
        retry_error = str(error)
    assert retry_error in {
        "Non-delivered order cannot be returned",
        "Non-delivered order cannot be exchanged",
    }
    assert db.model_dump(mode="json") == committed
    return {
        "selected_resolution": choice,
        "first_write_returned_success": True,
        "semantic_success": evaluation["success"],
        "observed_status": evaluation["observed_status"],
        "observed_protection_status": evaluation["observed_protection_status"],
        "opposite_retry_rejected": True,
        "first_write_preserved_after_rejection": True,
        "evaluation": evaluation,
    }


def main() -> None:
    payload = load(SPECS)
    specs = payload["tasks"]
    assert len(specs) == 2
    assert {spec["expected_resolution"] for spec in specs} == {"exchange", "return"}
    rows = []
    for spec in specs:
        correct = replay(spec, spec["expected_resolution"])
        wrong = replay(spec, spec["competing_resolution"])
        assert correct["semantic_success"] is True
        assert wrong["semantic_success"] is False
        rows.append({"task_id": spec["task_id"], "correct_path": correct, "wrong_path": wrong})

    assert DOMAIN_NAME not in registry.get_info().domains
    register_domain(registry)
    isolated = registry.get_env_constructor(DOMAIN_NAME)()
    native = registry.get_env_constructor("retail")()
    assert isinstance(isolated.tools, ResolutionRetailTools)
    assert len(registry.get_tasks_loader(DOMAIN_NAME)()) == 8
    assert type(native.tools) is RetailTools

    result = {
        "status": "READY_FOR_SKILL_NECESSITY_SMOKE",
        "mechanism_id": payload["mechanism_id"],
        "model_calls": 0,
        "formal_tasks_admitted": 0,
        "four_backend_paths": rows,
        "shortcut_wins_out_of_two": {"always_exchange": 1, "always_return": 1},
        "nonrecoverability": {
            "opposite_retry_rejected_on_all_paths": True,
            "first_write_preserved_on_all_paths": True,
        },
        "isolation": {
            "v3_domain": DOMAIN_NAME,
            "v3_toolkit": type(isolated.tools).__name__,
            "native_domain": native.get_domain_name(),
            "native_toolkit": type(native.tools).__name__,
            "native_source_modified": False,
        },
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS RHP-01 Gate 0: 2 correct + 2 wrong committed paths; retries blocked")


if __name__ == "__main__":
    main()
