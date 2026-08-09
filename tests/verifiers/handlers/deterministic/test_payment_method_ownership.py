"""Tests for payment methods belonging to the target user profile."""

from __future__ import annotations

from pathlib import Path

from src.policies.schema import PolicyRuleSet, VerificationContext
from src.trajectory.schema import (
    EnvironmentRef,
    MessageEvent,
    TaskOutcome,
    ToolCallEvent,
    ToolResultEvent,
    Trajectory,
)
from src.verifiers.handlers.deterministic.payment_method_ownership import (
    check_payment_method_ownership,
)


def payment_rule():
    """Load the real v0.4 payment-method rule."""
    root = Path(__file__).resolve().parents[4]
    rule_set = PolicyRuleSet.model_validate_json(
        (root / "policies/airline/rules_v04.json").read_text(
            encoding="utf-8"
        )
    )
    return next(
        rule
        for rule in rule_set.rules
        if rule.rule_id == "airline.payment.method.001"
    )


def profile_result(
    step_id: int,
    *payment_ids: str,
    user_id: str = "user-1",
) -> ToolResultEvent:
    """Build one successful user-profile lookup result."""
    return ToolResultEvent(
        step_id=step_id,
        source_turn_idx=step_id,
        event_type="tool_result",
        actor="tool",
        tool_call_id=f"profile-{step_id}",
        tool_name="get_user_details",
        result={
            "user_id": user_id,
            "payment_methods": {
                payment_id: {
                    "id": payment_id,
                    "source": "credit_card",
                }
                for payment_id in payment_ids
            },
        },
        error=False,
    )


def profile_call(
    step_id: int,
    *,
    user_id: str = "user-1",
) -> ToolCallEvent:
    """Build the lookup call paired with a profile result."""
    return ToolCallEvent(
        step_id=step_id,
        source_turn_idx=step_id,
        event_type="tool_call",
        actor="agent",
        tool_call_id=f"profile-{step_id + 1}",
        tool_name="get_user_details",
        arguments={"user_id": user_id},
    )


def reservation_result(
    step_id: int,
    *,
    reservation_id: str = "ABC123",
    user_id: str = "user-1",
) -> ToolResultEvent:
    """Build one reservation-to-user ownership result."""
    return ToolResultEvent(
        step_id=step_id,
        source_turn_idx=step_id,
        event_type="tool_result",
        actor="tool",
        tool_call_id=f"reservation-{step_id}",
        tool_name="get_reservation_details",
        result={
            "reservation_id": reservation_id,
            "user_id": user_id,
        },
        error=False,
    )


def reservation_call(
    step_id: int,
    *,
    reservation_id: str = "ABC123",
) -> ToolCallEvent:
    """Build the lookup call paired with a reservation result."""
    return ToolCallEvent(
        step_id=step_id,
        source_turn_idx=step_id,
        event_type="tool_call",
        actor="agent",
        tool_call_id=f"reservation-{step_id + 1}",
        tool_name="get_reservation_details",
        arguments={"reservation_id": reservation_id},
    )


def booking_call(
    step_id: int,
    *payment_ids: str,
    user_id: str = "user-1",
) -> ToolCallEvent:
    """Build a booking with explicit payment IDs."""
    return ToolCallEvent(
        step_id=step_id,
        source_turn_idx=step_id,
        event_type="tool_call",
        actor="agent",
        tool_call_id=f"booking-{step_id}",
        tool_name="book_reservation",
        arguments={
            "user_id": user_id,
            "payment_methods": [
                {"payment_id": payment_id, "amount": 100}
                for payment_id in payment_ids
            ],
        },
    )


def update_call(
    step_id: int,
    payment_id: str,
    *,
    tool_name: str = "update_reservation_flights",
) -> ToolCallEvent:
    """Build a reservation update with one payment ID."""
    return ToolCallEvent(
        step_id=step_id,
        source_turn_idx=step_id,
        event_type="tool_call",
        actor="agent",
        tool_call_id=f"update-{step_id}",
        tool_name=tool_name,
        arguments={
            "reservation_id": "ABC123",
            "payment_id": payment_id,
        },
    )


def trajectory(*events) -> Trajectory:
    """Build one minimal normalized trajectory."""
    return Trajectory(
        trajectory_id="trajectory-1",
        environment=EnvironmentRef(name="tau2", domain="airline"),
        task_id="1",
        events=list(events),
        outcome=TaskOutcome(score=None),
    )


def verify(item: Trajectory):
    """Run the configured deterministic payment handler."""
    return check_payment_method_ownership(
        item,
        payment_rule(),
        VerificationContext(),
    )


def test_booking_payment_from_profile_is_compliant() -> None:
    """A booking may use every listed profile payment method."""
    verdict = verify(
        trajectory(
            profile_call(0),
            profile_result(1, "card-1", "gift-1"),
            booking_call(2, "card-1", "gift-1"),
        )
    )

    assert verdict.status == "compliant"
    assert verdict.violations == []
    assert verdict.evidence[0].value["checks"][0]["status"] == "compliant"


def test_booking_payment_outside_profile_is_violation() -> None:
    """An unknown booking payment ID produces localized evidence."""
    verdict = verify(
        trajectory(
            profile_call(0),
            profile_result(1, "card-1"),
            booking_call(2, "card-1", "card-other"),
        )
    )

    assert verdict.status == "violation"
    assert verdict.violations[0].step_id == 2
    assert "card-other" in verdict.violations[0].description
    assert {
        evidence.step_id
        for evidence in verdict.violations[0].evidence
    } == {1, 2}


def test_update_resolves_user_through_reservation() -> None:
    """Reservation updates use the owning user's retrieved profile."""
    verdict = verify(
        trajectory(
            profile_call(0),
            profile_result(1, "card-1"),
            reservation_call(2),
            reservation_result(3),
            update_call(4, "card-1"),
        )
    )

    assert verdict.status == "compliant"
    assert verdict.evidence[0].value["checks"][0]["user_id"] == "user-1"


def test_missing_profile_evidence_is_indeterminate() -> None:
    """Ownership is not guessed when the user's profile was not retrieved."""
    verdict = verify(
        trajectory(
            reservation_call(0),
            reservation_result(1),
            update_call(2, "card-1"),
        )
    )

    assert verdict.status == "indeterminate"
    assert verdict.violations == []


def test_no_payment_bearing_write_is_compliant() -> None:
    """A trajectory without covered payment writes has no violation."""
    verdict = verify(
        trajectory(
            MessageEvent(
                step_id=0,
                source_turn_idx=0,
                event_type="message",
                actor="user",
                content="Hello",
            )
        )
    )

    assert verdict.status == "compliant"
    assert verdict.evidence[0].value == {"checks": []}
