#!/usr/bin/env python3
"""Run correct-path and targeted-regression audits for all formal Controls."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction/integration_audit'))
EDITION = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/editions/phase_final_candidate_day35')
REPO = EDITION.parents[3]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from tau2.data_model.tasks import Task  # noqa: E402

from src.benchmark_v3.final.environment.airline import get_environment as get_airline  # noqa: E402
from src.benchmark_v3.final.environment.retail import get_environment as get_retail  # noqa: E402

from src.benchmark_v3.final.integration_audit.control_evaluator import evaluate  # noqa: E402


TASKS = EDITION / "benchmark/control_tasks.json"
SPECS = EDITION / "benchmark/control_specs.json"
RESULT = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction/integration_audit/control_regression_validation.json')


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def apply(tools: Any, target: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        tools.use_tool(target["name"], **deepcopy(target["arguments"]))
        return True, None
    except Exception as error:
        return False, str(error)


def execute_correct(task: dict[str, Any]) -> dict[str, Any]:
    environment = get_airline() if "AIR" in task["id"] else get_retail()
    initial = environment.tools.db.model_dump(mode="json")
    calls = []
    for action in task["evaluation_criteria"]["actions"]:
        succeeded, error = apply(environment.tools, action)
        calls.append({"name": action["name"], "succeeded": succeeded, "error": error})
    final = environment.tools.db.model_dump(mode="json")
    outcome = evaluate(task["id"], initial, final)
    return {"success": outcome["success"], "checks": outcome["checks"], "calls": calls}


def execute_regression(task: dict[str, Any]) -> dict[str, Any]:
    task_id = task["id"]
    if task_id == "CTRL-AIR-C06":
        scenarios = []
        for name, replacement in (
            ("FORCE_OPPOSITE_SETTLEMENT_BRANCH", "XG105"),
            ("SUBSTITUTE_ALTERNATE_DESTINATION", "XG104"),
        ):
            environment = get_airline()
            initial = environment.tools.db.model_dump(mode="json")
            target = deepcopy(task["evaluation_criteria"]["actions"][0])
            target["arguments"]["flights"][1]["flight_number"] = replacement
            succeeded, error = apply(environment.tools, target)
            outcome = evaluate(task_id, initial, environment.tools.db.model_dump(mode="json"))
            scenarios.append({
                "name": name,
                "detected": not outcome["success"],
                "checks": outcome["checks"],
                "calls": [{"name": target["name"], "succeeded": succeeded, "error": error}],
            })
        return {
            "detected": all(row["detected"] for row in scenarios),
            "scenario_count": len(scenarios),
            "scenarios": scenarios,
        }
    environment = get_airline() if "AIR" in task_id else get_retail()
    initial = environment.tools.db.model_dump(mode="json")
    targets = deepcopy(task["evaluation_criteria"]["actions"])
    if task_id == "CTRL-AIR-C01":
        targets[0]["arguments"]["flights"][0]["flight_number"] = "CTA111"
    elif task_id == "CTRL-AIR-C02":
        targets[0]["arguments"]["flights"][0]["flight_number"] = "CTA212"
    elif task_id == "CTRL-AIR-C03":
        targets = targets[:2]
    elif task_id == "CTRL-RET-C01":
        targets[0]["arguments"]["item_ids"] = ["CTR-I011"]
        targets[0]["arguments"]["new_item_ids"] = ["CTR-I019"]
    elif task_id == "CTRL-AIR-C04":
        targets = [{"name": "transfer_to_human_agents", "arguments": {"summary": "Cancellation requires human handling."}}]
    elif task_id == "CTRL-AIR-C05":
        targets[0]["arguments"]["payment_methods"] = [{"payment_id": "gift_card_5005", "amount": 90}]
        targets[1]["arguments"]["payment_id"] = "certificate_5005"
    elif task_id == "CTRL-RET-C02":
        targets.append({
            "name": "modify_user_address",
            "arguments": {"user_id": "ctrl_ret_gio_7007", "address1": "99 Drift Road", "address2": "", "city": "Denver", "state": "CO", "country": "USA", "zip": "80202"},
        })
    elif task_id == "CTRL-RET-C03":
        targets = [{
            "name": "exchange_delivered_order_items",
            "arguments": {
                "order_id": "#GAPR8201",
                "item_ids": ["GAPR-I011"],
                "new_item_ids": ["GAPR-I012"],
                "payment_method_id": "credit_card_8208",
            },
        }]
    calls = []
    for target in targets:
        succeeded, error = apply(environment.tools, target)
        calls.append({"name": target["name"], "succeeded": succeeded, "error": error})
    final = environment.tools.db.model_dump(mode="json")
    outcome = evaluate(task_id, initial, final)
    return {"detected": not outcome["success"], "scenario_count": 1, "would_pass": outcome["success"], "checks": outcome["checks"], "calls": calls}


def main() -> None:
    tasks = load(TASKS)
    specs = load(SPECS)["controls"]
    assert len(tasks) == len(specs) == 9
    assert {row["id"] for row in tasks} == {row["task_id"] for row in specs}
    assert len({row["lineage"] for row in specs}) == 9
    for task in tasks:
        Task.model_validate(task)
    rows = {}
    for task in tasks:
        correct = execute_correct(task)
        regression = execute_regression(task)
        assert correct["success"]
        assert regression["detected"]
        rows[task["id"]] = {"correct_path": correct, "targeted_regression": regression}
    regression_count = sum(row["targeted_regression"]["scenario_count"] for row in rows.values())
    result = {
        "status": "PASS_9_PROTECTED_CONTROL_REALIZATION_AND_10_REGRESSION_AUDIT",
        "model_calls": 0,
        "formal_control_count": 9,
        "fresh_entity_realizations": 9,
        "correct_paths_passed": 9,
        "targeted_regressions_detected": regression_count,
        "included_in_core_improvement_rates": False,
        "rows": rows,
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"])


if __name__ == "__main__":
    main()
