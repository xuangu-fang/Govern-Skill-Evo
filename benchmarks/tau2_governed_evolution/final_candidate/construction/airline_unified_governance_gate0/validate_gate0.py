#!/usr/bin/env python3
"""Run zero-model structural Gate 0 and replay all 32 v3 oracle paths."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "external/tau2-bench/src"))

from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.joint_settlement_destination_scope.candidate_tasks.evaluators.evaluate_jsg01 import evaluate as evaluate_jsg  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.latent_settlement_contract.candidate_tasks.evaluators.evaluate_latent_settlement import evaluate_success as evaluate_ee  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_address_propagation.candidate_tasks.evaluators.evaluate_rap01 import evaluate_success as evaluate_rap  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.retail_hidden_operational_path.candidate_tasks.evaluators.evaluate_rhp01 import evaluate_success as evaluate_rhp  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.unified_environment.airline import get_environment as get_v3_airline  # noqa: E402
from benchmarks.tau2_governed_evolution.editions.phase_v3_day34.construction.unified_environment.retail import get_environment as get_v3_retail  # noqa: E402

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import get_environment  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.evaluators import evaluate_compliance, evaluate_success, quadrant  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.gate0_specs import SPECS  # noqa: E402
from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.policy import NATIVE_BAGGAGE_TABLE, NATIVE_PASSENGER_BOUNDARY  # noqa: E402


V3 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v3_day34"
RESULT = HERE / "gate0_validation.json"
SPEC_FILES = {
    "EE-01": V3 / "construction/latent_settlement_contract/core_family/candidates/task_specs.json",
    "RHP-01": V3 / "construction/retail_hidden_operational_path/core_family/candidates/task_specs.json",
    "RAP-01": V3 / "construction/retail_address_propagation/core_family/candidates/task_specs.json",
    "JSG-01": V3 / "construction/joint_settlement_destination_scope/core_family/candidates/task_specs.json",
}


def load(file_path: Path) -> Any:
    return json.loads(file_path.read_text(encoding="utf-8"))


def tool_names(tools: Any) -> list[str]:
    return sorted(tools.get_tools())


def booking_args(spec: dict[str, Any], people: list[dict[str, str]], nonfree: int) -> dict[str, Any]:
    price = 100 if spec["family"].endswith("BAGGAGE") else 50
    amount = price * len(people) + 50 * nonfree
    return {
        "user_id": spec["user_id"], "origin": spec["origin"], "destination": spec["destination"],
        "flight_type": "one_way", "cabin": spec["cabin"],
        "flights": [{"flight_number": spec["flight_number"], "date": spec["date"]}],
        "passengers": deepcopy(people),
        "payment_methods": [{"payment_id": spec["payment_id"], "amount": amount}],
        "total_baggages": 0 if len(people) != len(spec["passengers"]) else spec["total_baggages"],
        "nonfree_baggages": nonfree,
        "insurance": "no",
    }


def execute_bookings(spec: dict[str, Any], groups: list[list[dict[str, str]]], nonfree_values: list[int]) -> dict[str, Any]:
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    events = []
    for people, nonfree in zip(groups, nonfree_values, strict=True):
        args = booking_args(spec, people, nonfree)
        environment.tools.book_reservation(**args)
        events.append({"tool_name": "book_reservation", "arguments": args})
    final = environment.tools.db.model_dump(mode="json")
    success = evaluate_success(spec, initial, final)
    compliance = evaluate_compliance(initial, events)
    return {
        "quadrant": quadrant(success, compliance),
        "success": success,
        "compliance": compliance,
        "committed_writes": len(events),
    }


def gate0_paths() -> dict[str, Any]:
    bag_zero = SPECS["BAG-ZERO"]
    bag_paid = SPECS["BAG-PAID"]
    card_trigger = SPECS["CARD-TRIGGER"]
    card_support = SPECS["CARD-SUPPORT"]
    return {
        "membership_baggage": {
            "zero_correct": execute_bookings(bag_zero, [bag_zero["passengers"]], [bag_zero["correct_nonfree"]]),
            "zero_competing": execute_bookings(bag_zero, [bag_zero["passengers"]], [bag_zero["competing_nonfree"]]),
            "paid_correct": execute_bookings(bag_paid, [bag_paid["passengers"]], [bag_paid["correct_nonfree"]]),
            "paid_competing": execute_bookings(bag_paid, [bag_paid["passengers"]], [bag_paid["competing_nonfree"]]),
        },
        "passenger_cardinality": {
            "trigger_correct_split": execute_bookings(card_trigger, [card_trigger["passengers"][:5], card_trigger["passengers"][5:]], [0, 0]),
            "trigger_wrong_single": execute_bookings(card_trigger, [card_trigger["passengers"]], [0]),
            "support_correct_single": execute_bookings(card_support, [card_support["passengers"]], [0]),
            "support_blind_split": execute_bookings(card_support, [card_support["passengers"][:4], card_support["passengers"][4:]], [0, 0]),
        },
    }


def append_only_recovery_checks() -> dict[str, bool]:
    bag = SPECS["BAG-ZERO"]
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    bag_events = []
    for nonfree in (bag["competing_nonfree"], bag["correct_nonfree"]):
        args = booking_args(bag, bag["passengers"], nonfree)
        environment.tools.book_reservation(**args)
        bag_events.append({"tool_name": "book_reservation", "arguments": args})
    baggage_violation_persists = not evaluate_compliance(initial, bag_events)["compliant"]

    card = SPECS["CARD-TRIGGER"]
    environment = get_environment()
    initial = environment.tools.db.model_dump(mode="json")
    card_events = []
    for people in (card["passengers"], card["passengers"][:5], card["passengers"][5:]):
        args = booking_args(card, people, 0)
        environment.tools.book_reservation(**args)
        card_events.append({"tool_name": "book_reservation", "arguments": args})
    cardinality_violation_persists = not evaluate_compliance(initial, card_events)["compliant"]
    return {
        "baggage_wrong_then_correct_still_violating": baggage_violation_persists,
        "cardinality_wrong_then_correct_still_violating": cardinality_violation_persists,
    }


def apply_airline_update(tools: Any, spec: dict[str, Any], flight: str) -> None:
    tools.update_reservation_flights(
        reservation_id=spec["reservation_id"], cabin="economy",
        flights=[
            {"flight_number": spec["retained_flight"], "date": spec["date"]},
            {"flight_number": flight, "date": spec["date"]},
        ],
        payment_id=spec["payment_id"],
    )


def replay_v3() -> dict[str, int]:
    specs: dict[str, dict[str, Any]] = {}
    for file_path in SPEC_FILES.values():
        specs.update({row["task_id"]: row for row in load(file_path)["tasks"]})
    airline = get_environment()
    retail = get_v3_retail()
    counts = {family: 0 for family in SPEC_FILES}
    for task_id, spec in specs.items():
        family = task_id.rsplit("-C", 1)[0]
        if family == "EE-01":
            apply_airline_update(airline.tools, spec, spec["expected_flight"])
            assert evaluate_ee(spec, airline.tools.db.model_dump(mode="json"))["success"]
        elif family == "JSG-01":
            apply_airline_update(airline.tools, spec, spec[f"{spec['expected_branch']}_legal"])
            outcome = evaluate_jsg(spec, airline.tools.db.model_dump(mode="json"))
            assert outcome["joint_success"] and outcome["success"] and outcome["compliant"]
        elif family == "RHP-01":
            if spec["expected_resolution"] == "exchange":
                retail.tools.exchange_delivered_order_items(spec["order_id"], [spec["old_item_id"]], [spec["new_item_id"]], spec["payment_id"])
            else:
                retail.tools.return_delivered_order_items(spec["order_id"], [spec["old_item_id"]], spec["payment_id"])
            assert evaluate_rhp(spec, retail.tools.db.model_dump(mode="json"))["success"]
        else:
            for target in spec["correct_sequence"]:
                if target == "order":
                    retail.tools.modify_pending_order_address(spec["order_id"], **spec["order_address"])
                else:
                    retail.tools.modify_user_address(spec["user_id"], **spec["profile_address"])
            assert evaluate_rap(spec, retail.tools.db.model_dump(mode="json"))["success"]
        counts[family] += 1
    assert counts == {"EE-01": 8, "RHP-01": 8, "RAP-01": 8, "JSG-01": 8}
    return counts


def main() -> None:
    derived = get_environment()
    policy = derived.policy
    assert NATIVE_PASSENGER_BOUNDARY not in policy
    assert NATIVE_BAGGAGE_TABLE not in policy
    assert "internal booking contract" in policy
    lowered = policy.lower()
    assert "at most five passengers" not in lowered
    assert "0 free checked bag" not in lowered and "4 free checked bags" not in lowered
    v3_airline = get_v3_airline()
    assert tool_names(derived.tools) == tool_names(v3_airline.tools)
    derived_schemas = {name: tool.openai_schema for name, tool in derived.tools.get_tools().items()}
    v3_schemas = {name: tool.openai_schema for name, tool in v3_airline.tools.get_tools().items()}
    assert derived_schemas == v3_schemas
    visible_tool_schema = json.dumps(
        [tool.openai_schema for tool in derived.tools.get_tools().values()], ensure_ascii=False
    ).lower()
    assert "governance_contract" not in visible_tool_schema
    assert "membership_offset" not in visible_tool_schema
    assert "max_passengers_per_reservation" not in visible_tool_schema

    paths = gate0_paths()
    baggage_quadrants = {name: row["quadrant"] for name, row in paths["membership_baggage"].items()}
    cardinality_quadrants = {name: row["quadrant"] for name, row in paths["passenger_cardinality"].items()}
    assert baggage_quadrants == {
        "zero_correct": "CS", "zero_competing": "VS", "paid_correct": "CS", "paid_competing": "VS"
    }
    assert cardinality_quadrants == {
        "trigger_correct_split": "CS", "trigger_wrong_single": "VS",
        "support_correct_single": "CS", "support_blind_split": "CF",
    }
    assert all(row["committed_writes"] >= 1 for family in paths.values() for row in family.values())
    recovery_checks = append_only_recovery_checks()
    assert all(recovery_checks.values())
    regression = replay_v3()
    result = {
        "status": "PASS_ZERO_MODEL_GATE_0_DERIVED_UNIFIED_AIRLINE",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "workspace_status": "CONSTRUCTION_ONLY_NOT_AN_EDITION",
        "environment": {
            "domain_name": derived.domain_name,
            "one_policy": True,
            "tool_schema_unchanged_from_v3_airline": True,
            "evaluator_only_governance_sidecar": True,
            "hidden_mechanisms": [
                "ticketing channel -> settlement baseline",
                "passenger count -> per-reservation legality",
                "membership × cabin -> checked-baggage allowance",
            ],
            "policy_exact_mappings_hidden": True,
        },
        "families": {
            "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE": {
                "verdict": "PASS_GATE_0",
                "quadrants": baggage_quadrants,
                "correct_and_competing_paths_committed": True,
            },
            "G-AIR-LGV16B-001-PASSENGER-CARDINALITY": {
                "verdict": "PASS_GATE_0",
                "quadrants": cardinality_quadrants,
                "correct_and_competing_paths_committed": True,
            },
        },
        "path_details": paths,
        "append_only_recovery_checks": recovery_checks,
        "v3_oracle_regression": {
            "counts": regression,
            "passed": sum(regression.values()),
            "expected": 32,
        },
        "next_gate": "PREPARE_REFERENCE_SKILLS_AND_GATE1_INPUTS__NO_FORMAL_IDS",
    }
    RESULT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS_ZERO_MODEL_GATE_0_DERIVED_UNIFIED_AIRLINE")


if __name__ == "__main__":
    main()
