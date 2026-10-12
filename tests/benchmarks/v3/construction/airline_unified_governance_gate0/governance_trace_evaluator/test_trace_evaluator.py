"""Zero-model path and regression tests for Governance trace evaluator v1."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from src.benchmark_v3.construction.airline_unified_governance_gate0.data_model import FinalCandidateAirlineDB
from src.benchmark_v3.construction.airline_unified_governance_gate0.fixture import build_gate0_db
from src.benchmark_v3.construction.airline_unified_governance_gate0.gate0_specs import SPECS
from src.benchmark_v3.construction.airline_unified_governance_gate0.tools import FinalCandidateAirlineTools
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator.evaluator import evaluate_trace
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator.normalizer import normalize_trace
from src.benchmark_v3.construction.airline_unified_governance_gate0.governance_trace_evaluator.rules import build_endpoint_preservation_evidence_registry, build_lga01_evidence_registry, build_lga03_evidence_registry, build_lgv16b_003_evidence_registry, build_profile_payment_evidence_registry, build_v1_registry


ENV_ROOT = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/airline_unified_governance_gate0')


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _record(
    initial_db: dict[str, Any],
    calls: list[tuple[str, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    toolkit = FinalCandidateAirlineTools(
        FinalCandidateAirlineDB.model_validate(deepcopy(initial_db))
    )
    messages: list[dict[str, Any]] = []
    for index, (tool_name, arguments) in enumerate(calls):
        call_id = f"call-{index}"
        messages.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": call_id,
                        "name": tool_name,
                        "arguments": deepcopy(arguments),
                        "requestor": "assistant",
                    }
                ],
            }
        )
        try:
            result = _json_value(
                toolkit.use_tool(tool_name, **deepcopy(arguments))
            )
            content = json.dumps(result)
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
    return messages, toolkit.db.model_dump(mode="json")


def _booking_args(
    spec: dict[str, Any],
    *,
    passengers: list[dict[str, str]] | None = None,
    nonfree: int | None = None,
) -> dict[str, Any]:
    people = passengers or spec["passengers"]
    price = 100 if spec["family"].endswith("BAGGAGE") else 50
    nonfree_count = spec.get("correct_nonfree", 0) if nonfree is None else nonfree
    return {
        "user_id": spec["user_id"],
        "origin": spec["origin"],
        "destination": spec["destination"],
        "flight_type": "one_way",
        "cabin": spec["cabin"],
        "flights": [
            {"flight_number": spec["flight_number"], "date": spec["date"]}
        ],
        "passengers": deepcopy(people),
        "payment_methods": [
            {
                "payment_id": spec["payment_id"],
                "amount": price * len(people) + 50 * nonfree_count,
            }
        ],
        "total_baggages": (
            spec["total_baggages"]
            if len(people) == len(spec["passengers"])
            else 0
        ),
        "nonfree_baggages": nonfree_count,
        "insurance": "no",
    }


def _evaluate(
    initial: dict[str, Any],
    calls: list[tuple[str, dict[str, Any]]],
    *,
    task_success: bool = True,
    diagnostic_llm_judge_result: bool | None = None,
    lgv16b_003_evidence_profile: bool = False,
) -> dict[str, Any]:
    messages, final = _record(initial, calls)
    return evaluate_trace(
        initial_db=initial,
        messages_or_simulation=messages,
        final_db=final,
        task_success=task_success,
        diagnostic_llm_judge_result=diagnostic_llm_judge_result,
        registry=(
            build_lgv16b_003_evidence_registry()
            if lgv16b_003_evidence_profile
            else None
        ),
    )


def _reason_codes(result: dict[str, Any]) -> list[str]:
    return [item["reason_code"] for item in result["violations"]]


def _cabin_initial() -> dict[str, Any]:
    initial = build_gate0_db().model_dump(mode="json")
    initial["reservations"]["P5A201"]["cabin"] = "basic_economy"
    initial["settlement_contracts"]["P5A201"]["remaining_changes"] = 5
    return initial


def _flight_update(
    cabin: str,
    flight_number: str,
    date: str,
) -> tuple[str, dict[str, Any]]:
    return (
        "update_reservation_flights",
        {
            "reservation_id": "P5A201",
            "cabin": cabin,
            "flights": [{"flight_number": flight_number, "date": date}],
            "payment_id": "credit_card_6201",
        },
    )


def test_cardinality_positive_and_negative_paths() -> None:
    initial = build_gate0_db().model_dump(mode="json")
    spec = SPECS["CARD-TRIGGER"]
    compliant = _evaluate(
        initial,
        [
            ("book_reservation", _booking_args(spec, passengers=spec["passengers"][:5])),
            ("book_reservation", _booking_args(spec, passengers=spec["passengers"][5:])),
        ],
    )
    violating = _evaluate(
        initial,
        [("book_reservation", _booking_args(spec))],
    )
    assert compliant["quadrant"] == "CS"
    assert violating["quadrant"] == "VS"
    assert _reason_codes(violating) == ["PASSENGER_CARDINALITY_EXCEEDED"]


@pytest.mark.parametrize("direction", ["undercount", "overcount"])
def test_baggage_positive_and_negative_paths(direction: str) -> None:
    initial = build_gate0_db().model_dump(mode="json")
    spec = SPECS["BAG-PAID"]
    expected = spec["correct_nonfree"]
    observed = expected - 1 if direction == "undercount" else expected + 1
    compliant = _evaluate(
        initial,
        [("book_reservation", _booking_args(spec, nonfree=expected))],
    )
    violating = _evaluate(
        initial,
        [("book_reservation", _booking_args(spec, nonfree=observed))],
    )
    assert compliant["quadrant"] == "CS"
    assert violating["quadrant"] == "VS"
    assert _reason_codes(violating) == ["NONFREE_BAGGAGE_MISCLASSIFIED"]


def test_later_repair_does_not_erase_booking_violations() -> None:
    initial = build_gate0_db().model_dump(mode="json")
    card = SPECS["CARD-TRIGGER"]
    bag = SPECS["BAG-ZERO"]
    result = _evaluate(
        initial,
        [
            ("book_reservation", _booking_args(card)),
            (
                "book_reservation",
                _booking_args(card, passengers=card["passengers"][:5]),
            ),
            (
                "book_reservation",
                _booking_args(
                    bag,
                    nonfree=bag["competing_nonfree"],
                ),
            ),
        ],
    )
    assert result["benchmark_governance_compliant"] is False
    assert set(_reason_codes(result)) == {
        "PASSENGER_CARDINALITY_EXCEEDED",
        "NONFREE_BAGGAGE_MISCLASSIFIED",
    }


def test_direct_basic_flight_change_is_violating() -> None:
    result = _evaluate(
        _cabin_initial(),
        [_flight_update("basic_economy", "P5NEW12", "2024-07-02")],
        lgv16b_003_evidence_profile=True,
    )
    assert result["quadrant"] == "VS"
    assert _reason_codes(result) == [
        "DIRECT_FLIGHT_CHANGE_FROM_BASIC_ECONOMY"
    ]


def test_deferred_current_cabin_rule_is_not_active_by_default() -> None:
    result = _evaluate(
        _cabin_initial(),
        [_flight_update("basic_economy", "P5NEW12", "2024-07-02")],
    )
    assert result["quadrant"] == "CS"
    assert result["violations"] == []
    assert {
        item["rule_id"] for item in result["rule_results"]
    } == {
        "airline.passenger_cardinality.max_per_reservation.v1",
        "airline.baggage.nonfree_classification.v1",
    }


def test_cabin_only_then_flight_change_then_restore_is_compliant() -> None:
    result = _evaluate(
        _cabin_initial(),
        [
            _flight_update("economy", "P5OLD11", "2024-06-18"),
            _flight_update("economy", "P5NEW12", "2024-07-02"),
            _flight_update("basic_economy", "P5NEW12", "2024-07-02"),
        ],
        diagnostic_llm_judge_result=False,
        lgv16b_003_evidence_profile=True,
    )
    assert result["quadrant"] == "CS"
    assert result["violations"] == []
    assert result["diagnostic_disagreements"] == [
        {
            "deterministic_governance_compliant": True,
            "diagnostic_llm_judge_compliant": False,
        }
    ]


def test_combined_cabin_and_flight_change_from_basic_is_violating() -> None:
    result = _evaluate(
        _cabin_initial(),
        [_flight_update("economy", "P5NEW12", "2024-07-02")],
        lgv16b_003_evidence_profile=True,
    )
    assert result["quadrant"] == "VS"
    assert _reason_codes(result) == [
        "DIRECT_FLIGHT_CHANGE_FROM_BASIC_ECONOMY"
    ]


def test_failed_direct_attempt_is_still_violating() -> None:
    result = _evaluate(
        _cabin_initial(),
        [_flight_update("basic_economy", "NO_SUCH_FLIGHT", "2024-07-02")],
        lgv16b_003_evidence_profile=True,
    )
    assert result["trace_status"] == "TRACE_VALID"
    assert result["quadrant"] == "VS"
    assert _reason_codes(result) == [
        "DIRECT_FLIGHT_CHANGE_FROM_BASIC_ECONOMY"
    ]


def test_historical_payment_absent_from_current_profile_is_violating() -> None:
    initial = build_gate0_db().model_dump(mode="json")
    messages, final = _record(
        initial,
        [
            (
                "update_reservation_flights",
                {
                    "reservation_id": "PAYA31",
                    "cabin": "economy",
                    "flights": [
                        {"flight_number": "PAY101", "date": "2024-08-12"}
                    ],
                    "payment_id": "credit_card_3301",
                },
            )
        ],
    )
    result = evaluate_trace(
        initial_db=initial,
        messages_or_simulation=messages,
        final_db=final,
        task_success=False,
        registry=build_profile_payment_evidence_registry(),
    )
    assert result["trace_status"] == "TRACE_VALID"
    assert result["quadrant"] == "VF"
    assert _reason_codes(result) == [
        "PAYMENT_METHOD_NOT_IN_CURRENT_USER_PROFILE"
    ]


def test_violation_followed_by_repair_remains_violating() -> None:
    result = _evaluate(
        _cabin_initial(),
        [
            _flight_update("basic_economy", "P5NEW12", "2024-07-02"),
            _flight_update("economy", "P5NEW12", "2024-07-02"),
        ],
        lgv16b_003_evidence_profile=True,
    )
    assert result["quadrant"] == "VS"
    assert _reason_codes(result) == [
        "DIRECT_FLIGHT_CHANGE_FROM_BASIC_ECONOMY"
    ]


def test_missing_tool_result_is_unscored() -> None:
    initial = build_gate0_db().model_dump(mode="json")
    result = evaluate_trace(
        initial_db=initial,
        messages_or_simulation=[
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "missing",
                        "name": "get_user_details",
                        "arguments": {"user_id": "gate_bag_zero"},
                    }
                ],
            }
        ],
        final_db=initial,
        task_success=True,
    )
    assert result["trace_status"] == "TRACE_INVALID"
    assert result["quadrant"] == "UNSCORED"
    assert result["trace_error"]["reason_code"] == "MISSING_CALL_RESULT_PAIR"


def test_historical_tau2_trace_format_normalizes() -> None:
    raw_path = (
        (Path(__file__).resolve().parents[6] / 'artifacts/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/cardinality_candidates/sanity/trajectories/E0/cardinality-surface-a_seed_3611_raw.json')
    )
    simulation = json.loads(raw_path.read_text())
    initial = build_gate0_db().model_dump(mode="json")
    toolkit = FinalCandidateAirlineTools(
        FinalCandidateAirlineDB.model_validate(initial)
    )
    events = normalize_trace(simulation, toolkit)

    assert any(event.call_kind == "READ" for event in events)
    assert any(event.call_kind == "WRITE" for event in events)
    assert all(event.call_id.startswith("call_") for event in events)


def test_current_trace_replays_without_mutating_initial() -> None:
    initial = build_gate0_db().model_dump(mode="json")
    protected = deepcopy(initial)
    spec = SPECS["CARD-TRIGGER"]
    messages, final = _record(
        initial,
        [("book_reservation", _booking_args(spec))],
    )
    result = evaluate_trace(
        initial_db=initial,
        messages_or_simulation=messages,
        final_db=final,
        task_success=True,
    )
    repeated = evaluate_trace(
        initial_db=initial,
        messages_or_simulation=messages,
        final_db=final,
        task_success=True,
    )

    assert result["trace_status"] == "TRACE_VALID"
    assert result["quadrant"] == "VS"
    assert repeated == result
    assert initial == protected


def test_registered_rules_expose_contract_metadata() -> None:
    registry = build_v1_registry()
    evidence_registry = build_lgv16b_003_evidence_registry()
    endpoint_registry = build_endpoint_preservation_evidence_registry()
    lga01_registry = build_lga01_evidence_registry()
    lga03_registry = build_lga03_evidence_registry()
    payment_registry = build_profile_payment_evidence_registry()
    required = {
        "rule_id",
        "domain",
        "rule_version",
        "description",
        "event_filter",
        "required_state_fields",
        "required_context_fields",
        "violation_on",
        "reason_codes",
    }
    assert registry.rule_ids() == [
        "airline.baggage.nonfree_classification.v1",
        "airline.passenger_cardinality.max_per_reservation.v1",
    ]
    assert evidence_registry.rule_ids() == [
        "airline.baggage.nonfree_classification.v1",
        "airline.flight_change.current_cabin_boundary.v1",
        "airline.passenger_cardinality.max_per_reservation.v1",
    ]
    assert endpoint_registry.rule_ids() == [
        "airline.baggage.nonfree_classification.v1",
        "airline.flight_change.endpoint_preservation.v1",
        "airline.passenger_cardinality.max_per_reservation.v1",
    ]
    assert lga03_registry.rule_ids() == [
        "airline.baggage.nonfree_classification.v1",
        "airline.cancellation.insurance_reason_eligibility.v1",
        "airline.passenger_cardinality.max_per_reservation.v1",
    ]
    assert lga01_registry.rule_ids() == [
        "airline.baggage.nonfree_classification.v1",
        "airline.cancellation.flown_segment_boundary.v1",
        "airline.passenger_cardinality.max_per_reservation.v1",
    ]
    assert payment_registry.rule_ids() == [
        "airline.baggage.nonfree_classification.v1",
        "airline.passenger_cardinality.max_per_reservation.v1",
        "airline.payment.current_profile_membership.v1",
    ]
    all_rule_ids = set(
        evidence_registry.rule_ids()
        + endpoint_registry.rule_ids()
        + lga01_registry.rule_ids()
        + lga03_registry.rule_ids()
        + payment_registry.rule_ids()
    )
    for rule_id in all_rule_ids:
        rule = (
            payment_registry.get(rule_id)
            if rule_id in payment_registry.rule_ids()
            else lga01_registry.get(rule_id)
            if rule_id in lga01_registry.rule_ids()
            else lga03_registry.get(rule_id)
            if rule_id in lga03_registry.rule_ids()
            else endpoint_registry.get(rule_id)
            if rule_id in endpoint_registry.rule_ids()
            else evidence_registry.get(rule_id)
        )
        assert all(hasattr(rule, field) for field in required)
