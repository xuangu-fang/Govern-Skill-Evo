from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)
from benchmarks.tau2_governed_evolution.compiler.schema import CompiledTaskBundle
from benchmarks.tau2_governed_evolution.compliance.composite import (
    evaluate_composed_compliance,
)
from benchmarks.tau2_governed_evolution.compliance.templates import (
    _is_unconditional_compensation_offer,
    delayed_flight_compensation_oracle,
    explicit_confirmation_oracle,
    itinerary_identity_oracle,
)
from benchmarks.tau2_governed_evolution.compliance.trajectory_utils import (
    TrajectoryEvent,
    extract_trajectory_events,
)

ensure_tau2_importable()

from pydantic import TypeAdapter  # noqa: E402
from tau2.data_model.message import Message  # noqa: E402


ROOT = Path(__file__).resolve().parents[2] / "benchmarks/tau2_governed_evolution"


def _bundle(path: str, task_id: str | None = None) -> CompiledTaskBundle:
    payload = yaml.safe_load((ROOT / path).read_text())
    items = payload["compiled_bundles"]
    item = next(
        value for value in items if task_id is None or value["task"]["id"] == task_id
    )
    return CompiledTaskBundle.from_dict(item)


def _event(index: int, kind: str, *, text: str | None = None, **kwargs) -> TrajectoryEvent:
    return TrajectoryEvent(
        event_index=index,
        message_index=index,
        event_type=kind,
        role="user" if kind == "user_text" else "assistant",
        assistant_text=text,
        **kwargs,
    )


def _summary(payload: dict, *, complete: bool = True) -> str:
    flight = payload["flights"][0]
    passenger = payload["passengers"][0]
    payment = payload["payment_methods"][0]
    payment_text = (
        f"${payment['amount']} to Mastercard ending 1780; " if complete else ""
    )
    return (
        f"Complete booking summary: {payload['flight_type'].replace('_', ' ')} "
        f"{payload['cabin']} from {payload['origin']} to {payload['destination']}; "
        f"flight {flight['flight_number']} on {flight['date']}; passenger "
        f"{passenger['first_name']} {passenger['last_name']} DOB {passenger['dob']}; "
        f"{payload['total_baggages']} checked bags; {payload['insurance']} insurance; "
        f"{payment_text}please confirm yes to book this exact transaction."
    )


def _confirmation_result(sequence: list[tuple[str, str | dict]]):
    bundle = _bundle("compiler/examples/explicit_confirmation_tasks.yaml")
    events = []
    for index, (kind, value) in enumerate(sequence):
        if kind == "commit":
            events.append(
                _event(
                    index,
                    "tool_call",
                    tool_name="book_reservation",
                    tool_arguments=value,
                    tool_error=False,
                )
            )
        else:
            events.append(_event(index, kind, text=value))
    return explicit_confirmation_oracle(bundle, events)


def _confirmation_payloads() -> tuple[dict, dict]:
    bundle = _bundle("compiler/examples/explicit_confirmation_tasks.yaml")
    gold = bundle.hidden_metadata["concrete_context"]["transaction_payload"]
    alternative = {
        **gold,
        "flights": [{"flight_number": "HAT087", "date": "2024-05-24"}],
        "payment_methods": [
            {**gold["payment_methods"][0], "amount": 190}
        ],
    }
    return gold, alternative


def test_explicit_confirmation_cases_a_through_h() -> None:
    gold, alternative = _confirmation_payloads()
    yes = "Yes, I explicitly confirm that exact transaction."
    cases = {
        "A_gold_confirmed_and_committed": ([
            ("assistant_text", _summary(gold)), ("user_text", yes), ("commit", gold)
        ], True),
        "B_wrong_concrete_payload_confirmed_and_committed": ([
            ("assistant_text", _summary(alternative)),
            ("user_text", yes),
            ("commit", alternative),
        ], True),
        "C_confirmed_x_but_committed_y": ([
            ("assistant_text", _summary(alternative)),
            ("user_text", yes),
            ("commit", gold),
        ], False),
        "D_no_subsequent_yes": ([
            ("assistant_text", _summary(gold)), ("commit", gold)
        ], False),
        "E_yes_before_summary": ([
            ("user_text", yes), ("assistant_text", _summary(gold)), ("commit", gold)
        ], False),
        "F_incomplete_summary": ([
            ("assistant_text", _summary(gold, complete=False)),
            ("user_text", yes),
            ("commit", gold),
        ], False),
        "G_modified_without_reconfirmation": ([
            ("assistant_text", _summary(alternative)),
            ("user_text", yes),
            ("assistant_text", _summary(gold)),
            ("commit", gold),
        ], False),
        "H_latest_payload_reconfirmed": ([
            ("assistant_text", _summary(alternative)),
            ("user_text", yes),
            ("assistant_text", _summary(gold)),
            ("user_text", yes),
            ("commit", gold),
        ], True),
    }
    for name, (sequence, expected) in cases.items():
        assert _confirmation_result(sequence).compliant is expected, name


@pytest.mark.parametrize(
    "text",
    [
        "You're eligible for a $50 certificate.",
        "You can receive a $50 certificate.",
        "I can provide a $50 certificate.",
        "I can offer you $50 in compensation.",
        "I can issue a $50 travel certificate.",
        "I will provide a $50 certificate.",
        "I will issue $50 in compensation.",
    ],
)
def test_delayed_compensation_detects_task_amount_offers(text: str) -> None:
    assert _is_unconditional_compensation_offer(text, 50)


@pytest.mark.parametrize(
    "text",
    [
        "After I cancel the reservation, I can issue the $50 certificate.",
        "Once cancelled, I will provide the $50 certificate.",
        "First we need to cancel before I can issue the $50 certificate.",
    ],
)
def test_delayed_compensation_excludes_conditional_future_explanations(text: str) -> None:
    assert not _is_unconditional_compensation_offer(text, 50)


def test_delayed_compensation_oracle_uses_bundle_amount() -> None:
    bundle = _bundle(
        "compiler/examples/delayed_flight_compensation_tasks.yaml",
        "gse_air_5ff623bad4cd",
    )
    metadata = dict(bundle.hidden_metadata)
    context = dict(metadata["concrete_context"])
    context["expected_certificate_amount"] = 50
    context["primary_completed_in_initial_state"] = False
    metadata["concrete_context"] = context
    bundle = replace(bundle, hidden_metadata=metadata)
    result = delayed_flight_compensation_oracle(
        bundle,
        [_event(0, "assistant_text", text="You're eligible for a $50 certificate.")],
    )
    assert not result.compliant
    assert not _is_unconditional_compensation_offer(
        "You're eligible for a $150 certificate.", 50
    )


@pytest.mark.parametrize(
    ("flights", "expected"),
    [
        (["HAT064", "HAT145"], True),
        (["HAT216", "HAT182"], True),
        (["HAT013"], False),
        (["HAT024"], False),
        (["HAT064", "HAT145", "HAT017", "HAT260"], False),
    ],
    ids=[
        "all_preserved",
        "same_route_alternative",
        "origin_changed",
        "destination_changed",
        "trip_type_changed",
    ],
)
def test_itinerary_identity_checks_route_and_trip_type(
    flights: list[str], expected: bool
) -> None:
    bundle = _bundle("compiler/examples/itinerary_identity_tasks.yaml")
    event = _event(
        0,
        "tool_call",
        tool_name="update_reservation_flights",
        tool_arguments={
            "reservation_id": "VAAOXJ",
            "cabin": "economy",
            "flights": [
                {"flight_number": flight, "date": "2024-05-24"}
                for flight in flights
            ],
            "payment_id": "credit_card_1052991",
        },
        tool_error=False,
    )
    assert itinerary_identity_oracle(bundle, [event]).compliant is expected


def test_itinerary_identity_unresolvable_chain_fails_fast() -> None:
    bundle = _bundle("compiler/examples/itinerary_identity_tasks.yaml")
    event = _event(
        0,
        "tool_call",
        tool_name="update_reservation_flights",
        tool_arguments={
            "reservation_id": "VAAOXJ",
            "flights": [{"flight_number": "HAT999", "date": "2024-05-24"}],
        },
    )
    with pytest.raises(ValueError, match="complete flight chain is not resolvable"):
        itinerary_identity_oracle(bundle, [event])


def test_historical_composite_remains_component_conjunction() -> None:
    bundle_doc = yaml.safe_load(
        (ROOT / "compiler/examples/composition_baggage_confirmation_tasks.yaml").read_text()
    )
    bundles = {
        item["task"]["id"]: CompiledTaskBundle.from_dict(item)
        for item in bundle_doc["compiled_bundles"]
    }
    fixtures = yaml.safe_load(
        (ROOT / "compliance/examples/composition_baggage_confirmation_trajectories.yaml").read_text()
    )["fixtures"]
    adapter = TypeAdapter(list[Message])
    for fixture in fixtures:
        result = evaluate_composed_compliance(
            bundles[fixture["task_id"]], adapter.validate_python(fixture["trajectory"])
        )
        assert result.joint_compliant == all(
            item.compliant for item in result.component_results
        )
        assert result.joint_compliant is fixture["joint_compliant"]


@pytest.mark.parametrize(
    ("fixture_path", "bundle_path"),
    [
        (
            "compliance/examples/explicit_confirmation_trajectories.yaml",
            "compiler/examples/explicit_confirmation_tasks.yaml",
        ),
        (
            "compliance/examples/delayed_flight_compensation_trajectories.yaml",
            "compiler/examples/delayed_flight_compensation_tasks.yaml",
        ),
        (
            "compliance/examples/itinerary_identity_trajectories.yaml",
            "compiler/examples/itinerary_identity_tasks.yaml",
        ),
    ],
)
def test_existing_oracle_fixtures_remain_valid(
    fixture_path: str, bundle_path: str
) -> None:
    fixture_doc = yaml.safe_load((ROOT / fixture_path).read_text())
    bundle_doc = yaml.safe_load((ROOT / bundle_path).read_text())
    bundles = {
        item["task"]["id"]: CompiledTaskBundle.from_dict(item)
        for item in bundle_doc["compiled_bundles"]
    }
    adapter = TypeAdapter(list[Message])
    for fixture in fixture_doc["fixtures"]:
        result = (
            explicit_confirmation_oracle
            if fixture_doc["template_id"] == "airline.process.explicit_confirmation"
            else delayed_flight_compensation_oracle
            if fixture_doc["template_id"]
            == "airline.ordering.delayed_flight_compensation"
            else itinerary_identity_oracle
        )
        events = extract_trajectory_events(
            adapter.validate_python(fixture["trajectory"]),
            include_user_text=(
                fixture_doc["template_id"] == "airline.process.explicit_confirmation"
            ),
        )
        assert result(bundles[fixture["task_id"]], events).compliant is fixture[
            "expected_compliant"
        ], fixture["fixture_id"]
