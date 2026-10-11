#!/usr/bin/env python3
"""Offline structural and oracle-path validation for benchmark v4."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from tau2.data_model.tasks import Task

from benchmarks.tau2_governed_evolution.editions.phase_v4_day36.environment.joint_airline import get_environment
from benchmarks.tau2_governed_evolution.final_candidate.construction.joint_capability_experience_mapping_v1.joint_gate.evaluator import evaluate


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SOURCE = REPO / "benchmarks/tau2_governed_evolution/final_candidate/construction/joint_capability_experience_mapping_v1/replication_v1"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def call(messages, tools, index, name, arguments):
    call_id = f"oracle-{index}"
    messages.append({"role": "assistant", "tool_calls": [{"id": call_id, "name": name, "arguments": arguments, "requestor": "assistant"}]})
    try:
        result = tools.use_tool(name, **arguments)
        content = json.dumps(result.model_dump(mode="json") if hasattr(result, "model_dump") else result)
        error = False
    except Exception as exc:
        content, error = f"Error: {exc}", True
    messages.append({"id": call_id, "role": "tool", "content": content, "requestor": "assistant", "error": error})


def oracle(spec):
    environment = get_environment()
    tools = environment.tools
    initial = tools.db.model_dump(mode="json")
    messages = [{"role": "user", "content": spec["reason_text"]}]
    for trip in spec["trips"]:
        payment = spec["gift_card_id"] if trip["cabin"] == "basic_economy" else spec["certificate_id"]
        call(messages, tools, len(messages), "book_reservation", {
            "user_id": spec["user_id"], "origin": trip["origin"], "destination": trip["destination"],
            "flight_type": "one_way", "cabin": trip["cabin"],
            "flights": [{"flight_number": trip["flight_number"], "date": trip["date"]}],
            "passengers": [spec["passenger"]],
            "payment_methods": [{"payment_id": payment, "amount": trip["price"]}],
            "total_baggages": 0, "nonfree_baggages": 0, "insurance": "no",
        })
    call(messages, tools, len(messages), "get_user_details", {"user_id": spec["user_id"]})
    call(messages, tools, len(messages), "get_reservation_details", {"reservation_id": spec["cancel_reservation_id"]})
    call(messages, tools, len(messages), "get_flight_status", {"flight_number": spec["cancel_flight_number"], "date": spec["cancel_flight_date"]})
    call(messages, tools, len(messages), "transfer_to_human_agents", {"summary": "Changed scheduling plans are not an insured cancellation ground; factual checks completed."})
    final = tools.db.model_dump(mode="json")
    return evaluate(spec, initial, {"messages": messages}, final, reason_source_message_index=0)


def main() -> int:
    tasks = load(HERE / "benchmark/tasks.json") + load(HERE / "benchmark/control_tasks.json")
    splits = load(HERE / "benchmark/splits.json")
    specs = load(HERE / "benchmark/joint_family_specs.json")["tasks"]
    decision = load(HERE / "benchmark/admission_decision.json")
    source_summary = load(SOURCE / "summary.json")
    ids = [row["id"] for row in tasks]
    assert len(tasks) == len(set(ids)) == 81
    assert len(splits["splits"]["train"]) == 36
    assert len(splits["splits"]["monitor"]) == 45
    assert len(splits["monitor_roles"]["CORE_GENERALIZATION"]) == 36
    assert len(splits["monitor_roles"]["REGRESSION_GUARD"]) == 9
    assert set(splits["splits"]["train"]).isdisjoint(splits["splits"]["monitor"])
    assert set(splits["splits"]["train"] + splits["splits"]["monitor"]) == set(ids)
    assert Counter(task_id.rsplit("-C", 1)[0] for task_id in ids if not task_id.startswith("CTRL-")) == {
        "EE-01": 8, "RHP-01": 8, "RAP-01": 8, "JSG-01": 8,
        "P4-01": 8, "GPC-01": 8, "GMB-01": 8, "GIR-01": 8, "JRA-01": 8,
    }
    assert all(Task.model_validate(row) for row in tasks)
    assert source_summary["verdict"] == "HOLD_REPLICATION"
    assert decision["contract_v3_result_preserved"] == "HOLD_REPLICATION"
    assert decision["decision"] == "ADMIT_TO_BENCHMARK_V4"
    results = [oracle(spec) for spec in specs]
    assert all(row["success"] and row["booking_success"] for row in results)
    assert all(row["trace"]["trace_status"] == "TRACE_VALID" for row in results)
    assert all(row["trace"]["benchmark_governance_compliant"] for row in results)
    output = {
        "status": "PASS_BENCHMARK_V4_INTEGRATION",
        "model_calls": 0, "task_count": 81, "core_task_count": 72,
        "split_counts": {"train": 36, "monitor": 45, "test": 0},
        "jra_oracle_cs": len(results), "jra_task_count": len(specs),
        "contract_v3_result": source_summary["verdict"],
        "admission_decision": decision["decision"],
    }
    (HERE / "integration_validation.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
