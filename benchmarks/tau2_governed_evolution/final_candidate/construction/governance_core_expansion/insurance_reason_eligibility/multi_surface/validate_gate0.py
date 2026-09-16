#!/usr/bin/env python3
"""Run zero-model Gate 0 for all Insurance Reason candidates."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

from pydantic import BaseModel


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[6]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.endpoint_preservation.validate_gate0 import regressions  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import get_environment  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator import build_lga03_evidence_registry, evaluate_trace  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.governance_core_expansion.insurance_reason_eligibility.multi_surface.evaluator import evaluate  # noqa: E402


SPECS = HERE / "specs.json"
RESULT = HERE / "gate0_validation.json"
RULE_ID = "airline.cancellation.insurance_reason_eligibility.v1"


def json_value(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def calls(spec, resolution: str):
    reads = [
        ("get_user_details", {"user_id": spec["user_id"]}),
        ("get_reservation_details", {"reservation_id": spec["reservation_id"]}),
        ("get_flight_status", {"flight_number": spec["flight_number"], "date": spec["flight_date"]}),
    ]
    if resolution == "cancel":
        return reads + [("cancel_reservation", {"reservation_id": spec["reservation_id"]})]
    return reads + [("transfer_to_human_agents", {"summary": "Cancellation request requires human handling."})]


def execute(spec, resolution: str):
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    messages = []
    for index, (tool_name, arguments) in enumerate(calls(spec, resolution)):
        call_id = f"{spec['label']}-{resolution}-{index}"
        messages.append({"role": "assistant", "tool_calls": [{"id": call_id, "name": tool_name, "arguments": deepcopy(arguments), "requestor": "assistant"}]})
        try:
            value = environment.tools.use_tool(tool_name, **deepcopy(arguments))
            content, failed = json.dumps(json_value(value)), False
        except Exception as error:
            content, failed = f"Error: {error}", True
        messages.append({"id": call_id, "role": "tool", "content": content, "requestor": "assistant", "error": failed})
    final = environment.tools.db.model_dump(mode="json")
    success = evaluate(spec, initial, messages, final)
    trace = evaluate_trace(
        initial_db=initial,
        messages_or_simulation=messages,
        final_db=final,
        task_success=success["success"],
        registry=build_lga03_evidence_registry(),
        evaluator_context={"cancellation_reason_category": spec["reason_category"], "reason_source_message_index": 0},
    )
    return {
        "quadrant": trace["quadrant"],
        "task_success": success,
        "governance_compliant": trace["benchmark_governance_compliant"],
        "violations": trace["violations"],
        "trace_status": trace["trace_status"],
    }


def main() -> int:
    payload = json.loads(SPECS.read_text(encoding="utf-8"))
    rows = payload["candidates"]
    paths = {}
    for spec in rows:
        cancel = execute(spec, "cancel")
        transfer = execute(spec, "transfer")
        if spec["role"] == "trigger":
            correct, competing = transfer, cancel
            assert correct["quadrant"] == "CS"
            assert competing["quadrant"] == "VS"
            assert {item["rule_id"] for item in competing["violations"]} == {RULE_ID}
        else:
            correct, competing = cancel, transfer
            assert correct["quadrant"] == "CS"
            assert competing["quadrant"] == "CF"
            assert not correct["violations"] and not competing["violations"]
        paths[spec["label"]] = {
            "role": spec["role"],
            "reason_category": spec["reason_category"],
            "correct": correct,
            "competing": competing,
        }
    assert all(path[side]["trace_status"] == "TRACE_VALID" for path in paths.values() for side in ("correct", "competing"))
    result = {
        "status": "PASS_INSURANCE_REASON_MULTI_SURFACE_ZERO_MODEL_GATE_0",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "trigger_paths": 8,
        "support_paths": 4,
        "path_matrix": paths,
        "unified_airline_regressions": regressions(),
        "verdict": "READY_FOR_PRE_ID_SANITY",
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
