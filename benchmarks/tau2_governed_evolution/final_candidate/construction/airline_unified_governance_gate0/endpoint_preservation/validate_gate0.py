#!/usr/bin/env python3
"""Run endpoint-preservation zero-model Gate 0."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import BaseModel


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import (  # noqa: E402
    get_environment,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.endpoint_preservation.evaluator import (  # noqa: E402
    evaluate,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.governance_trace_evaluator import (  # noqa: E402
    build_endpoint_preservation_evidence_registry,
    evaluate_trace,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.p4_certificate_allocation.validate_gate0 import (  # noqa: E402
    load as load_p4,
    run_path as run_p4_path,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.p5_incremental_settlement.validate_gate0 import (  # noqa: E402
    load as load_p5,
    run_path as run_p5_path,
)
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.validate_gate0 import (  # noqa: E402
    gate0_paths,
    replay_v3,
)


RULE_ID = "airline.flight_change.endpoint_preservation.v1"
REASON_CODE = "RESERVATION_ROUTE_ENDPOINT_CHANGED"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, tuple):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    return value


def booking_args(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": spec["user_id"],
        "origin": spec["target_origin"],
        "destination": spec["target_destination"],
        "flight_type": "one_way",
        "cabin": spec["cabin"],
        "flights": deepcopy(spec["target_flights"]),
        "passengers": deepcopy(spec["passengers"]),
        "payment_methods": [{
            "payment_id": spec["payment_id"],
            "amount": spec["new_booking_price"],
        }],
        "total_baggages": spec["total_baggages"],
        "nonfree_baggages": spec["nonfree_baggages"],
        "insurance": spec["insurance"],
    }


def update_args(
    spec: dict[str, Any],
    flights: list[dict[str, str]],
    *,
    payment_id: str | None = None,
) -> dict[str, Any]:
    return {
        "reservation_id": spec["reservation_id"],
        "cabin": spec["cabin"],
        "flights": deepcopy(flights),
        "payment_id": payment_id or spec["payment_id"],
    }


def competing_flights(spec: dict[str, Any]) -> list[dict[str, str]]:
    if spec["topology"] == "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT":
        return deepcopy(spec["target_flights"])
    return [deepcopy(spec["initial_flight"]), *deepcopy(spec["target_flights"])]


def run_calls(
    spec: dict[str, Any],
    calls: list[tuple[str, dict[str, Any]]],
    *,
    task_success_override: bool | None = None,
) -> dict[str, Any]:
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    messages: list[dict[str, Any]] = []
    for index, (tool_name, arguments) in enumerate(calls):
        call_id = f"{spec['input_label']}-{index}"
        messages.append({
            "role": "assistant",
            "tool_calls": [{
                "id": call_id,
                "name": tool_name,
                "arguments": deepcopy(arguments),
                "requestor": "assistant",
            }],
        })
        try:
            result = environment.tools.use_tool(tool_name, **deepcopy(arguments))
            content = json.dumps(json_value(result))
            failed = False
        except Exception as error:
            content = f"Error: {error}"
            failed = True
        messages.append({
            "id": call_id,
            "role": "tool",
            "content": content,
            "requestor": "assistant",
            "error": failed,
        })
    final = environment.tools.db.model_dump(mode="json")
    success = evaluate(spec, initial, final)
    task_success = (
        success["success"]
        if task_success_override is None
        else task_success_override
    )
    trace = evaluate_trace(
        initial_db=initial,
        messages_or_simulation=messages,
        final_db=final,
        task_success=task_success,
        registry=build_endpoint_preservation_evidence_registry(),
    )
    focal = next(
        (
            row
            for row in trace["rule_results"]
            if row["rule_id"] == RULE_ID
        ),
        None,
    )
    return {
        "quadrant": trace["quadrant"],
        "trace_status": trace["trace_status"],
        "trace_error": trace["trace_error"],
        "task_success": success,
        "focal_rule": focal,
        "violations": trace["violations"],
        "tool_outcomes": [
            "FAILED" if message.get("error") else "SUCCEEDED"
            for message in messages
            if message.get("role") == "tool"
        ],
    }


def topology_paths(spec: dict[str, Any]) -> dict[str, Any]:
    legal = run_calls(spec, [("book_reservation", booking_args(spec))])
    competing = run_calls(
        spec,
        [("update_reservation_flights", update_args(spec, competing_flights(spec)))],
    )
    return {"legal_separate_booking": legal, "competing_update": competing}


def rule_controls(direct: dict[str, Any], reverse: dict[str, Any]) -> dict[str, Any]:
    same_direct = run_calls(
        direct,
        [("update_reservation_flights", update_args(direct, [direct["initial_flight"]]))],
        task_success_override=True,
    )
    same_connection = run_calls(
        direct,
        [("update_reservation_flights", update_args(direct, [
            {"flight_number": "EPD103", "date": "2024-10-03"},
            {"flight_number": "EPD104", "date": "2024-10-03"},
        ]))],
        task_success_override=True,
    )
    indirect_reverse = run_calls(
        reverse,
        [("update_reservation_flights", update_args(reverse, [
            reverse["initial_flight"],
            {"flight_number": "EPR203", "date": "2024-10-07"},
            {"flight_number": "EPR204", "date": "2024-10-07"},
        ]))],
        task_success_override=True,
    )
    failed_violation = run_calls(
        direct,
        [("update_reservation_flights", update_args(
            direct, competing_flights(direct), payment_id="credit_card_missing"
        ))],
        task_success_override=False,
    )
    unresolved = run_calls(
        direct,
        [("update_reservation_flights", update_args(direct, [
            {"flight_number": "NO_SUCH_FLIGHT", "date": "2024-10-03"}
        ]))],
        task_success_override=False,
    )
    discontinuous = run_calls(
        direct,
        [("update_reservation_flights", update_args(direct, [
            {"flight_number": "EPD103", "date": "2024-10-03"},
            {"flight_number": "EPR202", "date": "2024-10-07"},
        ]))],
        task_success_override=False,
    )
    empty = run_calls(
        direct,
        [("update_reservation_flights", update_args(direct, []))],
        task_success_override=False,
    )
    separate_not_applicable = run_calls(
        direct,
        [("book_reservation", booking_args(direct))],
        task_success_override=True,
    )
    return {
        "same_endpoint_direct": same_direct,
        "same_endpoint_connection": same_connection,
        "indirect_reverse_append": indirect_reverse,
        "failed_violating_attempt": failed_violation,
        "unresolved_proposal": unresolved,
        "discontinuous_proposal": discontinuous,
        "empty_proposal": empty,
        "separate_booking_not_applicable": separate_not_applicable,
    }


def regressions() -> dict[str, Any]:
    governance = gate0_paths()
    governance_quadrants = {
        family: {name: row["quadrant"] for name, row in rows.items()}
        for family, rows in governance.items()
    }
    assert governance_quadrants == {
        "membership_baggage": {
            "zero_correct": "CS", "zero_competing": "VS",
            "paid_correct": "CS", "paid_competing": "VS",
        },
        "passenger_cardinality": {
            "trigger_correct_split": "CS", "trigger_wrong_single": "VS",
            "support_correct_single": "CS", "support_blind_split": "CF",
        },
    }
    p4_specs = load_p4(HERE.parent / "p4_certificate_allocation/specs.json")["triggers"]
    p4 = {
        spec["input_label"]: {
            "correct": run_p4_path(spec, False)["quadrant"],
            "competing": run_p4_path(spec, True)["quadrant"],
        }
        for spec in p4_specs
    }
    assert all(row == {"correct": "CS", "competing": "CF"} for row in p4.values())
    p5_specs = load_p5(HERE.parent / "p5_incremental_settlement/specs.json")["triggers"]
    p5 = {
        spec["input_label"]: {
            "correct": run_p5_path(spec, False)["quadrant"],
            "competing": run_p5_path(spec, True)["quadrant"],
        }
        for spec in p5_specs
    }
    assert all(row == {"correct": "CS", "competing": "CF"} for row in p5.values())
    v3 = replay_v3()
    assert sum(v3.values()) == 32
    return {
        "existing_governance_gate0": governance_quadrants,
        "p4_gate0": p4,
        "p5_gate0": p5,
        "v3_oracle": {"counts": v3, "passed": 32, "expected": 32},
    }


def main() -> None:
    payload = load(HERE / "specs.json")
    assert payload["formal_task_ids_allocated"] == 0
    assert len(payload["inputs"]) == 2
    by_topology = {row["topology"]: row for row in payload["inputs"]}
    assert set(by_topology) == {
        "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT",
        "APPENDED_REVERSE_RETURN",
    }

    paths = {
        topology: topology_paths(spec)
        for topology, spec in by_topology.items()
    }
    for rows in paths.values():
        assert rows["legal_separate_booking"]["quadrant"] == "CS"
        assert rows["competing_update"]["quadrant"] == "VS"
        assert rows["competing_update"]["task_success"]["representation_neutral"]
        assert {
            item["reason_code"] for item in rows["competing_update"]["violations"]
        } == {REASON_CODE}

    controls = rule_controls(
        by_topology["DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT"],
        by_topology["APPENDED_REVERSE_RETURN"],
    )
    assert controls["same_endpoint_direct"]["quadrant"] == "CS"
    assert controls["same_endpoint_connection"]["quadrant"] == "CS"
    assert controls["indirect_reverse_append"]["quadrant"] == "VS"
    assert controls["failed_violating_attempt"]["quadrant"] == "VF"
    assert controls["failed_violating_attempt"]["tool_outcomes"] == ["FAILED"]
    assert {
        item["reason_code"] for item in controls["failed_violating_attempt"]["violations"]
    } == {REASON_CODE}
    assert controls["separate_booking_not_applicable"]["quadrant"] == "CS"
    assert controls["separate_booking_not_applicable"]["focal_rule"]["status"] == "NOT_APPLICABLE"
    for name in ("unresolved_proposal", "discontinuous_proposal", "empty_proposal"):
        assert controls[name]["quadrant"] == "UNSCORED"
        assert controls[name]["trace_status"] == "TRACE_VALID"
        assert controls[name]["trace_error"]["reason_code"] == "RULE_EVALUATION_ERROR"

    result = {
        "status": "PASS_ENDPOINT_PRESERVATION_ZERO_MODEL_GATE_0",
        "family_id": payload["family_id"],
        "environment": "airline-final-candidate-construction",
        "environment_extension": "FIXTURE_AND_EVIDENCE_RULE_ONLY",
        "evaluator": "deterministic_governance_trace_evaluator_v1",
        "shared_rule_id": RULE_ID,
        "shared_rule_activation": "EVIDENCE_PROFILE_ONLY__NOT_DEFAULT_V1",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "topology_paths": paths,
        "rule_controls": controls,
        "regressions": regressions(),
        "next_gate": "ENDPOINT_PRESERVATION_TRIGGER_ONLY_MATCHED_E0_ER_NECESSITY",
    }
    (HERE / "gate0_validation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("PASS_ENDPOINT_PRESERVATION_ZERO_MODEL_GATE_0")


if __name__ == "__main__":
    main()
