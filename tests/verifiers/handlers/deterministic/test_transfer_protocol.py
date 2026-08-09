"""Tests for the deterministic transfer-protocol handler."""

from __future__ import annotations

from src.policies.schema import VerificationContext
from src.trajectory.schema import (
    EnvironmentRef,
    MessageEvent,
    TaskOutcome,
    ToolCallEvent,
    Trajectory,
)
from src.verifiers.handlers.deterministic.transfer_protocol import (
    RULE_ID,
    TRANSFER_PROTOCOL_RULE,
    TRANSFER_NOTICE,
    TRANSFER_TOOL_NAME,
    check_transfer_protocol,
)
from src.verifiers.schema import RuleVerdict


def user_message(step_id: int = 0) -> MessageEvent:
    """Build the initial user message shared by the test trajectories."""
    return MessageEvent(
        step_id=step_id,
        event_type="message",
        actor="user",
        content="Please transfer me to a human agent.",
    )


def transfer_call(step_id: int) -> ToolCallEvent:
    """Build one transfer tool call."""
    return ToolCallEvent(
        step_id=step_id,
        event_type="tool_call",
        actor="agent",
        tool_call_id=f"transfer-{step_id}",
        tool_name=TRANSFER_TOOL_NAME,
        arguments={"summary": "The user requested a human agent."},
    )


def transfer_notice(step_id: int) -> MessageEvent:
    """Build the required notice sent after a transfer call."""
    return MessageEvent(
        step_id=step_id,
        event_type="message",
        actor="agent",
        content=TRANSFER_NOTICE,
    )


def trajectory(*events: MessageEvent | ToolCallEvent) -> Trajectory:
    """Build a minimal valid trajectory from the supplied events."""
    return Trajectory(
        trajectory_id="trajectory-1",
        environment=EnvironmentRef(name="tau2", domain="airline"),
        task_id="1",
        events=list(events),
        outcome=TaskOutcome(score=None),
    )


def verify(item: Trajectory) -> RuleVerdict:
    """Run the configured transfer-protocol handler."""
    return check_transfer_protocol(
        item,
        TRANSFER_PROTOCOL_RULE,
        VerificationContext(),
    )


def test_transfer_call_followed_by_notice_is_compliant() -> None:
    """A transfer call followed by the required notice is valid."""
    verdict = verify(
        trajectory(user_message(), transfer_call(1), transfer_notice(2))
    )

    assert verdict.status == "compliant"
    assert verdict.violations == []
    assert verdict.evidence[0].value == {
        "transfer_call_count": 1,
        "transfer_notice_count": 1,
    }


def test_multiple_transfer_calls_and_notices_are_paired() -> None:
    """Each notice should consume exactly one preceding transfer call."""
    verdict = verify(
        trajectory(
            user_message(),
            transfer_call(1),
            transfer_call(2),
            transfer_notice(3),
            transfer_notice(4),
        )
    )

    assert verdict.status == "compliant"
    assert verdict.violations == []
    assert verdict.evidence[0].value == {
        "transfer_call_count": 2,
        "transfer_notice_count": 2,
    }


def test_notice_before_transfer_call_reports_both_unmatched_events() -> None:
    """A notice cannot satisfy a transfer call that occurs later."""
    verdict = verify(
        trajectory(user_message(), transfer_notice(1), transfer_call(2))
    )

    assert verdict.status == "violation"
    assert [item.rule_id for item in verdict.violations] == [RULE_ID, RULE_ID]
    assert [item.step_id for item in verdict.violations] == [1, 2]
    assert [item.evidence[0].step_id for item in verdict.violations] == [1, 2]
    assert [item.evidence[0].source for item in verdict.violations] == [
        "events[1].content",
        "events[2].tool_name",
    ]


def test_transfer_call_without_notice_is_violation() -> None:
    """Every transfer call requires a later transfer notice."""
    verdict = verify(
        trajectory(user_message(), transfer_call(1))
    )

    assert verdict.status == "violation"
    assert len(verdict.violations) == 1
    violation = verdict.violations[0]
    assert violation.rule_id == RULE_ID
    assert violation.step_id == 1
    assert violation.evidence[0].step_id == 1
    assert violation.evidence[0].source == "events[1].tool_name"
    assert violation.evidence[0].value == TRANSFER_TOOL_NAME


def test_notice_without_transfer_call_is_violation() -> None:
    """The transfer notice cannot appear without a preceding call."""
    verdict = verify(
        trajectory(user_message(), transfer_notice(1))
    )

    assert verdict.status == "violation"
    assert len(verdict.violations) == 1
    violation = verdict.violations[0]
    assert violation.rule_id == RULE_ID
    assert violation.step_id == 1
    assert violation.evidence[0].step_id == 1
    assert violation.evidence[0].source == "events[1].content"
    assert violation.evidence[0].value == TRANSFER_NOTICE


def test_trajectory_without_transfer_activity_is_compliant() -> None:
    """A trajectory with no transfer behavior does not violate the protocol."""
    verdict = verify(trajectory(user_message()))

    assert verdict.status == "compliant"
    assert verdict.violations == []
    assert verdict.evidence[0].value == {
        "transfer_call_count": 0,
        "transfer_notice_count": 0,
    }
