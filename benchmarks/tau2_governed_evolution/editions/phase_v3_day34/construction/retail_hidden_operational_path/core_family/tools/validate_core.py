#!/usr/bin/env python3
"""Deterministically validate the admitted RHP-01 Capability Core."""

from __future__ import annotations

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

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.candidate_tasks.evaluators.evaluate_rhp01 import evaluate_success  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.environment.fixture import build_gate0_db  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.environment.tools import ResolutionRetailTools  # noqa: E402


SPECS = CORE / "candidates/task_specs.json"
TASKS = CORE / "candidate_tasks/tasks.json"
FORMAL_TASKS = EDITION / "benchmark/tasks.json"
EE_TASKS = (
    EDITION
    / "construction/latent_settlement_contract/core_family/candidate_tasks/tasks.json"
)
RESULT = CORE / "structural_audit/core_validation.json"


def load(path: Path) -> Any:
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
    try:
        resolve(tools, spec, opposite)
    except ValueError as error:
        retry_error = str(error)
    else:
        raise AssertionError("Opposite correction unexpectedly succeeded")
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
    }


def main() -> None:
    payload = load(SPECS)
    specs = payload["tasks"]
    built = load(TASKS)
    formal = load(FORMAL_TASKS)
    ee = load(EE_TASKS)
    formal_rhp = [task for task in formal if task["id"].startswith("RHP-01-C")]
    assert len(specs) == len(built) == len(formal_rhp) == payload["task_count"] == 8
    assert built == formal_rhp
    assert formal[: len(ee) + len(built)] == ee + built
    assert [task["id"] for task in built] == [spec["task_id"] for spec in specs]

    rows = []
    for spec in specs:
        correct = replay(spec, spec["expected_resolution"])
        wrong = replay(spec, spec["competing_resolution"])
        assert correct["semantic_success"] is True
        assert wrong["semantic_success"] is False
        rows.append(
            {
                "task_id": spec["task_id"],
                "fulfillment_mode": spec["fulfillment_mode"],
                "expected_resolution": spec["expected_resolution"],
                "correct_path": correct,
                "opposite_path": wrong,
            }
        )

    combinations = Counter(
        (row["fulfillment_mode"], row["expected_resolution"]) for row in rows
    )
    assert combinations == {
        ("consolidated", "exchange"): 4,
        ("partner_direct", "return"): 4,
    }
    shortcut_wins = {
        "always_exchange": sum(row["expected_resolution"] == "exchange" for row in rows),
        "always_return": sum(row["expected_resolution"] == "return" for row in rows),
    }
    assert set(shortcut_wins.values()) == {4}
    assert len({spec["user_id"] for spec in specs}) == 8
    assert len({spec["order_id"] for spec in specs}) == 8
    assert len({spec["product_id"] for spec in specs}) == 8
    assert Counter(spec["surface"] for spec in specs) == {1: 2, 2: 2, 3: 2, 4: 2}
    surface_modes = Counter(
        (spec["surface"], spec["fulfillment_mode"]) for spec in specs
    )
    assert set(surface_modes.values()) == {1}

    result = {
        "status": "PASS_ADMITTED_CAPABILITY_CORE",
        "mechanism_id": payload["mechanism_id"],
        "model_calls": 0,
        "formal_task_count": len(rows),
        "all_correct_paths_succeed": True,
        "all_opposite_paths_commit_then_fail_semantically": True,
        "all_corrections_blocked": True,
        "combination_counts": {
            f"{mode}_{resolution}": count
            for (mode, resolution), count in sorted(combinations.items())
        },
        "shortcut_wins_out_of_eight": shortcut_wins,
        "every_surface_spans_both_modes": True,
        "entity_counts": {"users": 8, "orders": 8, "products": 8, "surfaces": 4},
        "tasks": rows,
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS RHP-01 Core: 8/8 correct; 8/8 opposite commits fail; shortcuts 4/8")


if __name__ == "__main__":
    main()
