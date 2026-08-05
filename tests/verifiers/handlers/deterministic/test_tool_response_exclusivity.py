"""Tests for tool-call and user-response source-message exclusivity."""

from __future__ import annotations

from typing import Literal

from src.policies.schema import VerificationContext
from src.trajectory.schema import (
    EnvironmentRef,
    MessageEvent,
    TaskOutcome,
    ToolCallEvent,
    Trajectory,
)
from src.verifiers.handlers.deterministic.tool_response_exclusivity import (
    TOOL_RESPONSE_EXCLUSIVITY_RULE,
    check_tool_response_exclusivity,
)
from src.verifiers.schema import RuleVerdict


def message(
    step_id: int,
    *,
    actor: Literal["agent", "user"],
    content: str,
    source_turn_idx: int | None,
) -> MessageEvent:
    """Build one user or agent message with an upstream turn boundary."""
    return MessageEvent(
        step_id=step_id,
        source_turn_idx=source_turn_idx,
        event_type="message",
        actor=actor,
        content=content,
    )


def tool_call(
    step_id: int,
    *,
    source_turn_idx: int | None,
) -> ToolCallEvent:
    """Build one agent tool call."""
    return ToolCallEvent(
        step_id=step_id,
        source_turn_idx=source_turn_idx,
        event_type="tool_call",
        actor="agent",
        tool_call_id=f"call-{step_id}",
        tool_name=f"tool_{step_id}",
        arguments={},
    )


def trajectory(
    *events: MessageEvent | ToolCallEvent,
) -> Trajectory:
    """Build a minimal trajectory for the deterministic checker."""
    return Trajectory(
        trajectory_id="trajectory-1",
        environment=EnvironmentRef(name="tau2", domain="airline"),
        task_id="1",
        events=list(events),
        outcome=TaskOutcome(score=None),
    )


def verify(item: Trajectory) -> RuleVerdict:
    """Run the configured checker used by the default registry."""
    return check_tool_response_exclusivity(
        item,
        TOOL_RESPONSE_EXCLUSIVITY_RULE,
        VerificationContext(),
    )


def test_trajectory_without_tool_calls_is_compliant() -> None:
    """No tool calls means no mixed tool/reply message occurred."""
    verdict = verify(
        trajectory(
            message(
                0,
                actor="user",
                content="Hello",
                source_turn_idx=0,
            )
        )
    )

    assert verdict.status == "compliant"
    assert verdict.violations == []


def test_tool_call_without_same_message_reply_is_compliant() -> None:
    """A tool-only source message satisfies the exclusivity rule."""
    verdict = verify(
        trajectory(
            message(
                0,
                actor="user",
                content="Look this up",
                source_turn_idx=0,
            ),
            tool_call(1, source_turn_idx=1),
        )
    )

    assert verdict.status == "compliant"
    assert verdict.violations == []


def test_multiple_sequential_tool_calls_in_one_message_are_compliant() -> None:
    """A τ³ batch is allowed because Orchestrator executes calls in order."""
    verdict = verify(
        trajectory(
            message(
                0,
                actor="user",
                content="Look up both reservations",
                source_turn_idx=0,
            ),
            tool_call(1, source_turn_idx=1),
            tool_call(2, source_turn_idx=1),
        )
    )

    assert verdict.status == "compliant"
    assert verdict.violations == []
    assert verdict.evidence[0].value == {
        "tool_call_count": 2,
        "mixed_source_turn_indices": [],
        "missing_source_turn_step_ids": [],
    }


def test_reply_and_tool_call_in_same_source_message_is_violation() -> None:
    """A non-empty reply cannot accompany a tool call in one source turn."""
    verdict = verify(
        trajectory(
            message(
                0,
                actor="user",
                content="Cancel it",
                source_turn_idx=0,
            ),
            message(
                1,
                actor="agent",
                content="I will cancel it now.",
                source_turn_idx=1,
            ),
            tool_call(2, source_turn_idx=1),
        )
    )

    assert verdict.status == "violation"
    assert len(verdict.violations) == 1
    assert verdict.violations[0].step_id == 1
    assert [
        item.step_id
        for item in verdict.violations[0].evidence
    ] == [1, 2]
    assert verdict.evidence[0].value == {
        "tool_call_count": 1,
        "mixed_source_turn_indices": [1],
        "missing_source_turn_step_ids": [],
    }


def test_reply_and_tool_call_in_different_messages_are_compliant() -> None:
    """Adjacent events are allowed when their source messages differ."""
    verdict = verify(
        trajectory(
            message(
                0,
                actor="user",
                content="Cancel it",
                source_turn_idx=0,
            ),
            message(
                1,
                actor="agent",
                content="I need to check the reservation first.",
                source_turn_idx=1,
            ),
            tool_call(2, source_turn_idx=2),
        )
    )

    assert verdict.status == "compliant"
    assert verdict.violations == []


def test_blank_agent_content_is_not_a_user_visible_reply() -> None:
    """Whitespace attached to a tool-call message is not treated as a reply."""
    verdict = verify(
        trajectory(
            message(
                0,
                actor="agent",
                content="   ",
                source_turn_idx=0,
            ),
            tool_call(1, source_turn_idx=0),
        )
    )

    assert verdict.status == "compliant"
    assert verdict.violations == []


def test_missing_source_message_boundary_is_indeterminate() -> None:
    """Missing source_turn_idx cannot be interpreted as compliant."""
    verdict = verify(
        trajectory(
            message(
                0,
                actor="user",
                content="Look this up",
                source_turn_idx=0,
            ),
            tool_call(1, source_turn_idx=None),
        )
    )

    assert verdict.status == "indeterminate"
    assert verdict.violations == []
    assert verdict.evidence[0].value == {
        "tool_call_count": 1,
        "mixed_source_turn_indices": [],
        "missing_source_turn_step_ids": [1],
    }
