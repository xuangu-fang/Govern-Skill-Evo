#!/usr/bin/env python3
"""Run LGV16B-003 zero-model Gate 0 with deterministic trace evaluation."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import BaseModel


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/airline_unified_governance_gate0/lgv16b_003_current_cabin')
REPO = HERE.parents[5]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from src.benchmark_v3.construction.airline_unified_governance_gate0.environment import get_environment
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator import build_lgv16b_003_evidence_registry, evaluate_trace
from src.benchmark_v3.construction.airline_unified_governance_gate0.lgv16b_003_current_cabin.evaluator import evaluate
from scripts.benchmarks.v3.construction.airline_unified_governance_gate0.p4_certificate_allocation.validate_gate0 import load as load_p4, run_path as run_p4_path
from scripts.benchmarks.v3.construction.airline_unified_governance_gate0.p5_incremental_settlement.validate_gate0 import load as load_p5, run_path as run_p5_path
from scripts.benchmarks.v3.construction.airline_unified_governance_gate0.validate_gate0 import gate0_paths, replay_v3


CURRENT_CABIN_RULE = "airline.flight_change.current_cabin_boundary.v1"


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


def update_args(
    spec: dict[str, Any],
    *,
    cabin: str,
    date: str,
) -> dict[str, Any]:
    return {
        "reservation_id": spec["reservation_id"],
        "cabin": cabin,
        "flights": [{"flight_number": spec["flight_number"], "date": date}],
        "payment_id": spec["payment_id"],
    }


def path_calls(spec: dict[str, Any], path_name: str) -> list[dict[str, Any]]:
    old_date = spec["old_date"]
    new_date = spec["new_date"]
    if path_name == "legal_three_step":
        return [
            update_args(spec, cabin="economy", date=old_date),
            update_args(spec, cabin="economy", date=new_date),
            update_args(spec, cabin="basic_economy", date=new_date),
        ]
    if path_name == "direct_from_basic":
        return [update_args(spec, cabin="basic_economy", date=new_date)]
    if path_name == "combined_then_restore":
        return [
            update_args(spec, cabin="economy", date=new_date),
            update_args(spec, cabin="basic_economy", date=new_date),
        ]
    if path_name == "violation_then_repair":
        return [
            update_args(spec, cabin="basic_economy", date=new_date),
            update_args(spec, cabin="economy", date=new_date),
            update_args(spec, cabin="basic_economy", date=new_date),
        ]
    if path_name == "non_trigger_direct":
        return [update_args(spec, cabin="basic_economy", date=new_date)]
    raise ValueError(f"Unknown path: {path_name}")


def run_path(spec: dict[str, Any], path_name: str) -> dict[str, Any]:
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    messages: list[dict[str, Any]] = []
    for index, arguments in enumerate(path_calls(spec, path_name)):
        call_id = f"{spec['input_label']}-{path_name}-{index}"
        messages.append(
            {
                "role": "assistant",
                "tool_calls": [{
                    "id": call_id,
                    "name": "update_reservation_flights",
                    "arguments": deepcopy(arguments),
                    "requestor": "assistant",
                }],
            }
        )
        try:
            response = environment.tools.update_reservation_flights(**arguments)
            content = json.dumps(json_value(response))
            failed = False
        except Exception as error:
            content = f"Error: {error}"
            failed = True
        messages.append(
            {
                "id": call_id,
                "role": "tool",
                "content": content,
                "requestor": "assistant",
                "error": failed,
            }
        )

    final = environment.tools.db.model_dump(mode="json")
    success = evaluate(spec, initial, final)
    governance = evaluate_trace(
        initial_db=initial,
        messages_or_simulation=messages,
        final_db=final,
        task_success=success["success"],
        registry=build_lgv16b_003_evidence_registry(),
    )
    cabin_result = next(
        item
        for item in governance["rule_results"]
        if item["rule_id"] == CURRENT_CABIN_RULE
    )
    return {
        "quadrant": governance["quadrant"],
        "trace_status": governance["trace_status"],
        "task_success": success,
        "governance_compliant": governance["benchmark_governance_compliant"],
        "current_cabin_rule": cabin_result,
        "violations": governance["violations"],
        "committed_updates": sum(
            1 for message in messages if message.get("role") == "tool" and not message["error"]
        ),
    }


def regressions() -> dict[str, Any]:
    governance = gate0_paths()
    governance_quadrants = {
        family: {name: row["quadrant"] for name, row in rows.items()}
        for family, rows in governance.items()
    }
    assert governance_quadrants == {
        "membership_baggage": {
            "zero_correct": "CS",
            "zero_competing": "VS",
            "paid_correct": "CS",
            "paid_competing": "VS",
        },
        "passenger_cardinality": {
            "trigger_correct_split": "CS",
            "trigger_wrong_single": "VS",
            "support_correct_single": "CS",
            "support_blind_split": "CF",
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
    return {
        "existing_governance_gate0": governance_quadrants,
        "p4_gate0": p4,
        "p5_gate0": p5,
        "v3_oracle": {
            "counts": v3,
            "passed": sum(v3.values()),
            "expected": 32,
        },
    }


def main() -> None:
    payload = load(HERE / "specs.json")
    assert payload["formal_task_ids_allocated"] == 0
    triggers = [
        item for item in payload["inputs"] if item["role"].startswith("TRIGGER_")
    ]
    non_trigger = next(
        item
        for item in payload["inputs"]
        if item["role"] == "NON_TRIGGER_CURRENT_ECONOMY"
    )
    assert len(triggers) == 2
    assert all(item["remaining_changes"] == 4 for item in payload["inputs"])
    assert all(item["initial_cabin"] == "basic_economy" for item in triggers)
    assert non_trigger["initial_cabin"] == "economy"
    assert all(
        item["final_cabin"] == "basic_economy" for item in payload["inputs"]
    )

    paths = {
        "triggers": {
            trigger["input_label"]: {
                name: run_path(trigger, name)
                for name in (
                    "legal_three_step",
                    "direct_from_basic",
                    "combined_then_restore",
                    "violation_then_repair",
                )
            }
            for trigger in triggers
        },
        "non_trigger": {
            "non_trigger_direct": run_path(non_trigger, "non_trigger_direct")
        },
    }
    for trigger_paths in paths["triggers"].values():
        assert trigger_paths["legal_three_step"]["quadrant"] == "CS"
        for name in (
            "direct_from_basic",
            "combined_then_restore",
            "violation_then_repair",
        ):
            assert trigger_paths[name]["quadrant"] == "VS"
            assert {
                item["reason_code"] for item in trigger_paths[name]["violations"]
            } == {"DIRECT_FLIGHT_CHANGE_FROM_BASIC_ECONOMY"}
    assert paths["non_trigger"]["non_trigger_direct"]["quadrant"] == "CS"
    assert all(
        row["trace_status"] == "TRACE_VALID"
        for trigger_paths in paths["triggers"].values()
        for row in trigger_paths.values()
    )
    assert paths["non_trigger"]["non_trigger_direct"]["trace_status"] == "TRACE_VALID"
    all_rows = [
        row
        for trigger_paths in paths["triggers"].values()
        for row in trigger_paths.values()
    ] + [paths["non_trigger"]["non_trigger_direct"]]
    assert all(row["task_success"]["preserved_nonfocal_state"] for row in all_rows)

    result = {
        "status": "PASS_LGV16B_003_ZERO_MODEL_GATE_0",
        "family_id": payload["family_id"],
        "environment": "airline-final-candidate-construction",
        "environment_extension": "FIXTURE_ONLY",
        "evaluator": "deterministic_governance_trace_evaluator_v1",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "matched_state_pair": {
            "shared_final_cabin": "basic_economy",
            "shared_remaining_changes": 4,
            "differing_current_cabin": {
                "trigger": "basic_economy",
                "non_trigger": "economy",
            },
        },
        "paths": paths,
        "regressions": regressions(),
        "next_gate": "LGV16B_003_TRIGGER_ONLY_MATCHED_E0_ER_NECESSITY",
    }
    ((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/lgv16b_003_current_cabin/gate0_validation.json')).write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("PASS_LGV16B_003_ZERO_MODEL_GATE_0")


if __name__ == "__main__":
    main()
