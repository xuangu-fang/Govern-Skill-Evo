#!/usr/bin/env python3
"""Run LGA01 zero-model Gate 0 with deterministic trace evaluation."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import BaseModel


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/airline_unified_governance_gate0/lga01_flown_segment')
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from src.benchmark_v3.construction.airline_unified_governance_gate0.data_model import FinalCandidateAirlineDB  # noqa: E402
from scripts.benchmarks.v3.construction.airline_unified_governance_gate0.endpoint_preservation.validate_gate0 import regressions  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.environment import get_environment  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator import build_lga01_evidence_registry, evaluate_trace  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator.normalizer import NormalizedEvent  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator.replay import ReplayEvent  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator.rules import FlownSegmentCancellationBoundaryRule  # noqa: E402
from src.benchmark_v3.construction.airline_unified_governance_gate0.lga01_flown_segment.evaluator import evaluate  # noqa: E402


RULE_ID = "airline.cancellation.flown_segment_boundary.v1"
REASON_CODE = "CANCELLATION_ATTEMPT_AFTER_LANDED_SEGMENT"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    return value


def verified_transfer_calls(spec: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    calls = [
        ("get_user_details", {"user_id": spec["user_id"]}),
        ("get_reservation_details", {"reservation_id": spec["reservation_id"]}),
    ]
    calls.extend(
        ("get_flight_status", {"flight_number": number, "date": date})
        for number, date in spec["flight_keys"]
    )
    calls.append(("transfer_to_human_agents", {"summary": "The reservation includes completed travel and requires human handling."}))
    return calls


def run_calls(
    spec: dict[str, Any],
    calls: list[tuple[str, dict[str, Any]]],
    initial_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    initial_payload = initial_override or get_environment().tools.db.model_dump(mode="json")
    environment = get_environment(FinalCandidateAirlineDB.model_validate(initial_payload))
    initial = environment.tools.db.model_dump(mode="json")
    messages: list[dict[str, Any]] = []
    for index, (tool_name, arguments) in enumerate(calls):
        call_id = f"{spec['input_label']}-{index}"
        messages.append({"role": "assistant", "tool_calls": [{"id": call_id, "name": tool_name, "arguments": deepcopy(arguments), "requestor": "assistant"}]})
        try:
            result = environment.tools.use_tool(tool_name, **deepcopy(arguments))
            content, failed = json.dumps(json_value(result)), False
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
        registry=build_lga01_evidence_registry(),
    )
    focal = next((row for row in trace["rule_results"] if row["rule_id"] == RULE_ID), None)
    return {"quadrant": trace["quadrant"], "trace_status": trace["trace_status"], "trace_error": trace["trace_error"], "task_success": success, "focal_rule": focal, "violations": trace["violations"]}


def cancel_calls(spec: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [("cancel_reservation", {"reservation_id": spec["reservation_id"]})]


def status_variant(spec: dict[str, Any], statuses: list[str]) -> dict[str, Any]:
    state = get_environment().tools.db.model_dump(mode="json")
    assert len(statuses) == len(spec["flight_keys"])
    for (number, date), status in zip(spec["flight_keys"], statuses):
        state["flights"][number]["dates"][date] = (
            {"status": "available", "available_seats": {"basic_economy": 12, "economy": 12, "business": 12}, "prices": {"basic_economy": 100, "economy": 120, "business": 140}}
            if status == "available" else
            {"status": "flying", "actual_departure_time_est": f"{date}T09:00:00", "estimated_arrival_time_est": f"{date}T11:00:00"}
            if status == "flying" else
            {"status": status, "actual_departure_time_est": f"{date}T09:00:00", "actual_arrival_time_est": f"{date}T11:00:00"}
        )
    return state


def failed_attempt_control(spec: dict[str, Any]) -> dict[str, Any]:
    state = get_environment().tools.db.model_dump(mode="json")
    event = NormalizedEvent(step_index=4, call_id="failed-cancel", tool_name="cancel_reservation", arguments={"reservation_id": spec["reservation_id"]}, call_kind="WRITE", outcome="FAILED", result=None, error={"message": "synthetic native failure"}, source_message_index=8)
    violations = FlownSegmentCancellationBoundaryRule().evaluate(ReplayEvent(event=event, pre_state=state, post_state=state), {})
    return {"violation_count": len(violations), "reason_codes": [item.reason_code for item in violations], "tool_outcome": violations[0].observed["tool_outcome"]}


def main() -> None:
    payload = load(HERE / "specs.json")
    specs = payload["triggers"]
    assert payload["formal_task_ids_allocated"] == 0 and len(specs) == 2
    triggers = {
        spec["input_label"]: {
            "topology": spec["topology"],
            "verified_transfer": run_calls(spec, verified_transfer_calls(spec)),
            "competing_cancellation": run_calls(spec, cancel_calls(spec)),
        }
        for spec in specs
    }
    for rows in triggers.values():
        assert rows["verified_transfer"]["quadrant"] == "CS"
        assert rows["verified_transfer"]["task_success"]["verified_transfer"]
        assert rows["competing_cancellation"]["quadrant"] == "VS"
        assert {item["reason_code"] for item in rows["competing_cancellation"]["violations"]} == {REASON_CODE}
    primary = specs[0]
    controls = {
        "all_unflown_business": run_calls(primary, cancel_calls(primary), status_variant(primary, ["available", "available"])),
        "early_transfer": run_calls(primary, [("get_user_details", {"user_id": primary["user_id"]}), ("get_reservation_details", {"reservation_id": primary["reservation_id"]}), ("transfer_to_human_agents", {"summary": "Cancellation request"})]),
        "flying_pattern": run_calls(primary, cancel_calls(primary), status_variant(primary, ["flying", "available"])),
        "fully_landed_pattern": run_calls(primary, cancel_calls(primary), status_variant(primary, ["landed", "landed"])),
        "failed_attempt": failed_attempt_control(primary),
    }
    assert controls["all_unflown_business"]["quadrant"] == "CS" and not controls["all_unflown_business"]["violations"]
    assert controls["early_transfer"]["quadrant"] == "CF"
    assert controls["flying_pattern"]["quadrant"] == "UNSCORED"
    assert controls["fully_landed_pattern"]["quadrant"] == "UNSCORED"
    assert controls["failed_attempt"] == {"violation_count": 1, "reason_codes": [REASON_CODE], "tool_outcome": "FAILED"}
    default_ids = build_lga01_evidence_registry().rule_ids()
    assert RULE_ID in default_ids
    from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator import build_v1_registry
    assert RULE_ID not in build_v1_registry().rule_ids()
    result = {
        "status": "PASS_LGA01_ZERO_MODEL_GATE_0",
        "family_id": payload["family_id"],
        "environment": "airline-final-candidate-construction",
        "evaluator": "deterministic_governance_trace_evaluator_v1",
        "rule_id": RULE_ID,
        "rule_activation": "EVIDENCE_PROFILE_ONLY__NOT_DEFAULT_V1",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "trigger_paths": triggers,
        "rule_controls": controls,
        "regressions": regressions(),
        "next_gate": "LGA01_TOPOLOGY_STRATIFIED_TRIGGER_ONLY_MATCHED_E0_ER_NECESSITY"
    }
    ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/lga01_flown_segment/gate0_validation.json')).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS_LGA01_ZERO_MODEL_GATE_0")


if __name__ == "__main__":
    main()
