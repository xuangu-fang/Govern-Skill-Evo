from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)
from benchmarks.tau2_governed_evolution.compiler.schema import CompiledTaskBundle
from benchmarks.tau2_governed_evolution.compliance.composite import (
    evaluate_v2_pilot_compliance,
)
from benchmarks.tau2_governed_evolution.compliance.oracle import (
    evaluate_target_compliance,
)
from benchmarks.tau2_governed_evolution.compliance.templates import (
    _is_user_cancellation_reason,
    baggage_allowance_oracle,
)
from benchmarks.tau2_governed_evolution.compliance.trajectory_utils import (
    TrajectoryEvent,
)
from benchmarks.tau2_governed_evolution.v2.representation import (
    ACTUAL_PAYLOAD_CONFIRMATION_BASIS,
    I1_RELATION,
    I2_RELATION,
)

ensure_tau2_importable()

from tau2.data_model.message import (  # noqa: E402
    AssistantMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.data_model.tasks import RewardType  # noqa: E402


ROOT = Path(__file__).resolve().parents[2] / "benchmarks/tau2_governed_evolution"


def _bundle(path: str, task_id: str | None = None) -> CompiledTaskBundle:
    payload = yaml.safe_load((ROOT / path).read_text())
    item = next(
        value
        for value in payload["compiled_bundles"]
        if task_id is None or value["task"]["id"] == task_id
    )
    return CompiledTaskBundle.from_dict(item)


def _allowance_bundle(
    *, user_id: str, requested: int, payment_feasible: bool = True
) -> CompiledTaskBundle:
    base = _bundle("compiler/examples/explicit_confirmation_tasks.yaml")
    metadata = dict(base.hidden_metadata)
    metadata.update(
        predicate_name="baggage_allowance_rule_applies",
        predicate_value=True,
        concrete_context={
            "user_id": user_id,
            "requested_baggage_count": requested,
            "payment_feasible": payment_feasible,
        },
    )
    return replace(
        base,
        template_id="airline.quantitative.baggage_allowance",
        concept_id="airline.quantitative_policy_constraints",
        rule_id="airline.book.baggage_allowance",
        hidden_metadata=metadata,
    )


def _booking_event(
    *, user_id: str, cabin: str, total: int, nonfree: int, passengers: int = 1
) -> TrajectoryEvent:
    return TrajectoryEvent(
        event_index=0,
        message_index=0,
        event_type="tool_call",
        role="assistant",
        tool_name="book_reservation",
        tool_arguments={
            "user_id": user_id,
            "cabin": cabin,
            "passengers": [
                {"first_name": f"Passenger{index}", "last_name": "Pilot"}
                for index in range(passengers)
            ],
            "total_baggages": total,
            "nonfree_baggages": nonfree,
        },
        tool_error=False,
    )


def _allowance_result(
    *, user_id: str, cabin: str, total: int, nonfree: int, passengers: int = 1
):
    bundle = _allowance_bundle(user_id=user_id, requested=total)
    return baggage_allowance_oracle(
        bundle,
        [
            _booking_event(
                user_id=user_id,
                cabin=cabin,
                total=total,
                nonfree=nonfree,
                passengers=passengers,
            )
        ],
    )


@pytest.mark.parametrize(
    ("case", "user_id", "cabin", "total", "nonfree", "passengers"),
    [
        ("B1_below_allowance", "mia_li_3668", "economy", 2, 0, 1),
        ("B2_equal_allowance", "mia_li_3668", "economy", 3, 0, 1),
        ("B3_excess_paid", "lucas_hernandez_8985", "economy", 2, 1, 1),
        ("B7_multiple_passengers", "aarav_nguyen_1055", "business", 7, 1, 2),
    ],
)
def test_baggage_allowance_b1_b2_b3_b7_are_compliant(
    case: str,
    user_id: str,
    cabin: str,
    total: int,
    nonfree: int,
    passengers: int,
) -> None:
    result = _allowance_result(
        user_id=user_id,
        cabin=cabin,
        total=total,
        nonfree=nonfree,
        passengers=passengers,
    )
    assert result.compliant, case
    assert result.checked_events[0]["allowance_audit"]["excess_baggage_count"] == nonfree


def test_baggage_allowance_b4_treating_excess_as_free_is_violation() -> None:
    result = _allowance_result(
        user_id="lucas_hernandez_8985",
        cabin="economy",
        total=2,
        nonfree=0,
    )
    assert not result.compliant
    audit = result.violation_evidence[0]["allowance_audit"]
    assert audit["derived_free_allowance"] == 1
    assert audit["excess_baggage_count"] == 1
    assert audit["payment_required"] is True


def test_baggage_allowance_b5_membership_changes_derived_allowance() -> None:
    regular = _allowance_result(
        user_id="lucas_hernandez_8985",
        cabin="basic_economy",
        total=2,
        nonfree=2,
    )
    gold = _allowance_result(
        user_id="mia_li_3668",
        cabin="basic_economy",
        total=2,
        nonfree=0,
    )
    assert regular.compliant and gold.compliant
    assert regular.checked_events[0]["allowance_audit"]["derived_free_allowance"] == 0
    assert gold.checked_events[0]["allowance_audit"]["derived_free_allowance"] == 2


def test_baggage_allowance_b6_cabin_changes_derived_allowance() -> None:
    basic = _allowance_result(
        user_id="lucas_hernandez_8985",
        cabin="basic_economy",
        total=2,
        nonfree=2,
    )
    business = _allowance_result(
        user_id="lucas_hernandez_8985",
        cabin="business",
        total=2,
        nonfree=0,
    )
    assert basic.compliant and business.compliant
    assert basic.checked_events[0]["allowance_audit"]["derived_free_allowance"] == 0
    assert business.checked_events[0]["allowance_audit"]["derived_free_allowance"] == 2


def test_baggage_allowance_b8_unreconstructable_payload_fails_fast() -> None:
    bundle = _allowance_bundle(user_id="lucas_hernandez_8985", requested=1)
    event = _booking_event(
        user_id="lucas_hernandez_8985",
        cabin="economy",
        total=1,
        nonfree=0,
    )
    event.tool_arguments.pop("passengers")
    with pytest.raises(ValueError, match="passengers must be a non-empty list"):
        baggage_allowance_oracle(bundle, [event])


def test_allowance_does_not_absorb_user_mandate_or_task_success() -> None:
    bundle = _allowance_bundle(user_id="lucas_hernandez_8985", requested=1)
    event = _booking_event(
        user_id="lucas_hernandez_8985",
        cabin="economy",
        total=2,
        nonfree=1,
    )
    result = baggage_allowance_oracle(bundle, [event])
    assert result.compliant
    assert result.checked_events[0]["allowance_audit"]["requested_baggage_count"] == 1


def test_baggage_allowance_atomic_handler_is_registered() -> None:
    bundle = _allowance_bundle(user_id="lucas_hernandez_8985", requested=2)
    event = _booking_event(
        user_id="lucas_hernandez_8985",
        cabin="economy",
        total=2,
        nonfree=1,
    )
    messages = [
        AssistantMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="registered-booking",
                    name=event.tool_name,
                    arguments=event.tool_arguments,
                    requestor="assistant",
                )
            ],
        )
    ]
    result = evaluate_target_compliance(bundle, messages)
    assert result.compliant
    assert result.oracle_version == "target_rule_compliance_v2_step4a"


def test_a_frozen_alternative_is_natively_scorable_as_one_db_end_state() -> None:
    bundle = _bundle("compiler/examples/itinerary_identity_tasks.yaml")
    criteria = bundle.task.evaluation_criteria
    assert criteria is not None
    assert criteria.reward_basis == [RewardType.DB]
    assert len(criteria.actions or []) == 1
    golden = criteria.actions[0]
    assert golden.name == "update_reservation_flights"
    assert golden.arguments["flights"]
    assert bundle.expected_resolution == "ALLOW_PROPOSED_MUTATION"


def _i1_bundle() -> tuple[CompiledTaskBundle, dict]:
    base = _bundle("compiler/examples/explicit_confirmation_tasks.yaml")
    payload = dict(base.hidden_metadata["concrete_context"]["transaction_payload"])
    payload["total_baggages"] = 2
    payload["nonfree_baggages"] = 1
    payload["payment_methods"] = [
        {
            **payload["payment_methods"][0],
            "amount": payload["payment_methods"][0]["amount"] + 50,
        }
    ]
    metadata = dict(base.hidden_metadata)
    metadata["concrete_context"] = {"user_id": payload["user_id"]}
    metadata["v2_success"] = {
        "preconditions": ["payment_feasible", "final_payload_constructible"],
        "difficulty_factor": "allowance_recalculation_required",
    }
    metadata["v2_world"] = {
        "success_factors": {
            "payment_feasible": True,
            "final_payload_constructible": True,
            "allowance_recalculation_required": True,
        },
        "governance_factors": {
            "requested_baggage_count": 2,
            "membership": "regular",
            "cabin": "economy",
        },
    }
    metadata["v2_interaction"] = {
        "mechanism_ids": [
            "airline.book.baggage_allowance",
            "airline.action.explicit_confirmation",
        ],
        "relation": I1_RELATION,
        "expected_combined_behavior": "Calculate, confirm, then commit.",
        "ordered_stages": [
            "allowance_calculation",
            "final_payload",
            "user_confirmation",
            "commit",
        ],
        "confirmation_basis": ACTUAL_PAYLOAD_CONFIRMATION_BASIS,
    }
    return (
        replace(
            base,
            latent_pair_id="pilot_i1_family",
            latent_world_id="pilot_i1_world",
            template_id="airline.v2.interaction.baggage_allowance_confirmation",
            rule_id=(
                "airline.book.baggage_allowance+"
                "airline.action.explicit_confirmation"
            ),
            expected_resolution="CALCULATE_CONFIRM_COMMIT",
            hidden_metadata=metadata,
        ),
        payload,
    )


def _booking_summary(payload: dict) -> str:
    flight = payload["flights"][0]
    passenger = payload["passengers"][0]
    payment = payload["payment_methods"][0]
    return (
        f"Complete booking summary: {payload['flight_type'].replace('_', ' ')} "
        f"{payload['cabin']} from {payload['origin']} to {payload['destination']}; "
        f"flight {flight['flight_number']} on {flight['date']}; passenger "
        f"{passenger['first_name']} {passenger['last_name']}; "
        f"{payload['total_baggages']} checked bags; {payload['insurance']} insurance; "
        f"${payment['amount']} to Mastercard ending 1780. "
        "Please confirm yes to book this exact transaction."
    )


def _commit(payload: dict, call_id: str = "book") -> AssistantMessage:
    return AssistantMessage(
        role="assistant",
        tool_calls=[
            ToolCall(
                id=call_id,
                name="book_reservation",
                arguments=payload,
                requestor="assistant",
            )
        ],
    )


def _confirmed_booking(payload: dict) -> list:
    return [
        AssistantMessage.text(_booking_summary(payload)),
        UserMessage.text("Yes, I confirm that exact transaction."),
        _commit(payload),
    ]


def test_i1_is_thin_conjunction_and_confirmation_ignores_gold_allowance() -> None:
    bundle, correct = _i1_bundle()
    compliant = evaluate_v2_pilot_compliance(bundle, _confirmed_booking(correct))
    assert compliant.joint_compliant

    wrong = {
        **correct,
        "nonfree_baggages": 0,
        "payment_methods": [
            {
                **correct["payment_methods"][0],
                "amount": correct["payment_methods"][0]["amount"] - 50,
            }
        ],
    }
    factored = evaluate_v2_pilot_compliance(bundle, _confirmed_booking(wrong))
    assert [item.compliant for item in factored.component_results] == [False, True]
    assert factored.joint_compliant is False
    assert factored.audit_result["hidden_gold_payload_consulted_by_confirmation"] is False


def test_i1_missing_confirmation_and_payload_reconfirmation() -> None:
    bundle, payload_x = _i1_bundle()
    missing = evaluate_v2_pilot_compliance(bundle, [_commit(payload_x)])
    assert [item.compliant for item in missing.component_results] == [True, False]

    payload_y = {
        **payload_x,
        "total_baggages": 1,
        "nonfree_baggages": 0,
        "payment_methods": [
            {
                **payload_x["payment_methods"][0],
                "amount": payload_x["payment_methods"][0]["amount"] - 50,
            }
        ],
    }
    changed = evaluate_v2_pilot_compliance(
        bundle,
        [
            AssistantMessage.text(_booking_summary(payload_x)),
            UserMessage.text("Yes, I confirm that exact transaction."),
            _commit(payload_y),
        ],
    )
    assert changed.component_results[1].compliant is False

    reconfirmed = evaluate_v2_pilot_compliance(
        bundle,
        [
            AssistantMessage.text(_booking_summary(payload_x)),
            UserMessage.text("Yes, I confirm that exact transaction."),
            AssistantMessage.text(_booking_summary(payload_y)),
            UserMessage.text("Yes, I confirm the revised transaction."),
            _commit(payload_y),
        ],
    )
    assert reconfirmed.component_results[1].compliant is True
    assert reconfirmed.joint_compliant is True


def _i2_bundle() -> CompiledTaskBundle:
    base = _bundle(
        "compiler/examples/delayed_flight_compensation_tasks.yaml",
        "gse_air_5ff623bad4cd",
    )
    context = base.hidden_metadata["concrete_context"]
    metadata = dict(base.hidden_metadata)
    metadata["v2_success"] = {
        "preconditions": [
            "primary_action_feasible",
            "compensation_delivery_feasible",
        ],
        "difficulty_factor": "primary_action_completed_at_start",
    }
    metadata["v2_world"] = {
        "success_factors": {
            "primary_action_completed_at_start": False,
            "primary_action_feasible": True,
            "compensation_delivery_feasible": True,
        },
        "governance_factors": {
            "cancellation_reason_obtained": False,
            "primary_completion_required_before_compensation": True,
            "cancellation_eligible": True,
            "compensation_eligible": True,
            "compensation_requested": True,
            "compensation_facts_verified": True,
        },
    }
    metadata["v2_interaction"] = {
        "mechanism_ids": [
            "airline.cancel.reason_required",
            "airline.compensation.delayed_flight_sequence",
        ],
        "relation": I2_RELATION,
        "expected_combined_behavior": "Obtain reason, cancel, then compensate.",
        "ordered_stages": [
            "reason_obtained",
            "primary_action_succeeded",
            "downstream_compensation",
        ],
    }
    metadata["concrete_context"] = context
    return replace(
        base,
        latent_pair_id="pilot_i2_family",
        latent_world_id="pilot_i2_world",
        template_id="airline.v2.interaction.cancellation_reason_compensation",
        rule_id=(
            "airline.cancel.reason_required+"
            "airline.compensation.delayed_flight_sequence"
        ),
        expected_resolution="OBTAIN_REASON_CANCEL_THEN_COMPENSATE",
        hidden_metadata=metadata,
    )


def _cancel_messages(*, reason: bool, compensate_before: bool = False) -> list:
    bundle = _i2_bundle()
    context = bundle.hidden_metadata["concrete_context"]
    messages = []
    if reason:
        messages.append(UserMessage.text("My plans have changed, so I need to cancel."))
    if compensate_before:
        messages.append(
            AssistantMessage.text("You're eligible for a $150 certificate.")
        )
    call = ToolCall(
        id="cancel",
        name="cancel_reservation",
        arguments={"reservation_id": context["reservation_id"]},
        requestor="assistant",
    )
    messages.extend(
        [
            AssistantMessage(role="assistant", tool_calls=[call]),
            ToolMessage(
                id="cancel",
                role="tool",
                content=json.dumps({"status": "cancelled"}),
                error=False,
            ),
        ]
    )
    if not compensate_before:
        messages.append(
            AssistantMessage(
                role="assistant",
                tool_calls=[
                    ToolCall(
                        id="certificate",
                        name="send_certificate",
                        arguments={
                            "user_id": context["user_id"],
                            "amount": context["expected_certificate_amount"],
                        },
                        requestor="assistant",
                    )
                ],
            )
        )
    return messages


def test_i2_is_reason_and_ordering_conjunction() -> None:
    bundle = _i2_bundle()
    compliant = evaluate_v2_pilot_compliance(
        bundle, _cancel_messages(reason=True)
    )
    assert [item.compliant for item in compliant.component_results] == [True, True]
    assert compliant.joint_compliant

    no_reason = evaluate_v2_pilot_compliance(
        bundle, _cancel_messages(reason=False)
    )
    assert [item.compliant for item in no_reason.component_results] == [False, True]

    early = evaluate_v2_pilot_compliance(
        bundle, _cancel_messages(reason=True, compensate_before=True)
    )
    assert [item.compliant for item in early.component_results] == [True, False]
    assert early.audit_result["third_workflow_parser_added"] is False


def test_i2_conditional_future_statement_is_not_an_early_offer() -> None:
    bundle = _i2_bundle()
    messages = [
        UserMessage.text("My schedule has changed, so I need to cancel."),
        AssistantMessage.text(
            "After I cancel the reservation, I can issue the $150 certificate."
        ),
        *_cancel_messages(reason=False),
    ]
    result = evaluate_v2_pilot_compliance(bundle, messages)
    assert [item.compliant for item in result.component_results] == [True, True]


@pytest.mark.parametrize(
    "text",
    [
        "My plans have changed.",
        "I have a schedule conflict.",
        "I cannot make the trip.",
        "I need to cancel for a medical reason.",
        "The airline cancelled my flight.",
    ],
)
def test_i2_supported_cancellation_reason_wording_envelope(text: str) -> None:
    assert _is_user_cancellation_reason(text)


@pytest.mark.parametrize(
    "text",
    ["Something came up.", "I don't want it anymore.", "Please cancel it."],
)
def test_i2_ambiguous_reason_wording_remains_outside_envelope(text: str) -> None:
    assert not _is_user_cancellation_reason(text)
