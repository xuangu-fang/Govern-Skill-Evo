"""Tests for the common trajectory schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.trajectory.schema import (
    EnvironmentRef,
    MessageEvent,
    TaskOutcome,
    ToolCallEvent,
    ToolResultEvent,
    Trajectory,
)


TrajectoryEvent = MessageEvent | ToolCallEvent | ToolResultEvent


def make_trajectory(
    events: list[TrajectoryEvent],
) -> Trajectory:
    """Build a minimal trajectory for schema validation tests."""

    return Trajectory(
        trajectory_id="trajectory-1",
        environment=EnvironmentRef(
            name="tau2",
            domain="airline",
        ),
        task_id="task-1",
        events=events,
        outcome=TaskOutcome(score=1.0),
    )


def make_message(
    step_id: int,
    *,
    actor: str = "user",
    content: str = "hello",
) -> MessageEvent:
    """Build a minimal message event."""

    return MessageEvent(
        step_id=step_id,
        event_type="message",
        actor=actor,
        content=content,
    )


def make_tool_call(
    step_id: int,
    *,
    tool_call_id: str = "call-1",
    tool_name: str = "get_user_details",
) -> ToolCallEvent:
    """Build a minimal tool-call event."""

    return ToolCallEvent(
        step_id=step_id,
        event_type="tool_call",
        actor="agent",
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        arguments={"user_id": "user-1"},
    )


def make_tool_result(
    step_id: int,
    *,
    tool_call_id: str = "call-1",
    tool_name: str = "get_user_details",
) -> ToolResultEvent:
    """Build a minimal tool-result event."""

    return ToolResultEvent(
        step_id=step_id,
        event_type="tool_result",
        actor="tool",
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        result={"user_id": "user-1"},
    )


def test_valid_message_only_trajectory() -> None:
    """A trajectory containing one valid message should be accepted."""

    trajectory = make_trajectory(
        events=[
            make_message(step_id=0),
        ]
    )

    assert trajectory.trajectory_id == "trajectory-1"
    assert len(trajectory.events) == 1
    assert trajectory.events[0].step_id == 0


def test_valid_tool_call_and_result_sequence() -> None:
    """A matching tool call and result should be accepted."""

    trajectory = make_trajectory(
        events=[
            make_message(step_id=0),
            make_tool_call(step_id=1),
            make_tool_result(step_id=2),
        ]
    )

    assert len(trajectory.events) == 3
    assert isinstance(trajectory.events[1], ToolCallEvent)
    assert isinstance(trajectory.events[2], ToolResultEvent)


def test_state_delta_defaults_to_none() -> None:
    """Events should explicitly support an unknown state delta."""

    event = make_message(step_id=0)

    assert event.state_delta is None


def test_state_delta_accepts_json_value() -> None:
    """Events should accept a JSON-compatible state transition."""

    event = ToolResultEvent(
        step_id=0,
        event_type="tool_result",
        actor="tool",
        tool_call_id="call-1",
        tool_name="cancel_reservation",
        result={"status": "success"},
        state_delta={
            "reservation.status": {
                "before": "confirmed",
                "after": "cancelled",
            }
        },
    )

    assert event.state_delta == {
        "reservation.status": {
            "before": "confirmed",
            "after": "cancelled",
        }
    }


def test_step_ids_must_start_at_zero() -> None:
    """The first event step must be zero."""

    with pytest.raises(
        ValidationError,
        match="event step_id values must be contiguous",
    ):
        make_trajectory(
            events=[
                make_message(step_id=1),
            ]
        )


def test_step_ids_must_be_contiguous() -> None:
    """Missing step IDs should be rejected."""

    with pytest.raises(
        ValidationError,
        match="event step_id values must be contiguous",
    ):
        make_trajectory(
            events=[
                make_message(step_id=0),
                make_message(step_id=2),
            ]
        )


def test_duplicate_tool_call_id_is_rejected() -> None:
    """A tool-call ID may occur only once in a trajectory."""

    with pytest.raises(
        ValidationError,
        match="duplicate tool_call_id",
    ):
        make_trajectory(
            events=[
                make_tool_call(
                    step_id=0,
                    tool_call_id="call-duplicate",
                ),
                make_tool_call(
                    step_id=1,
                    tool_call_id="call-duplicate",
                ),
            ]
        )


def test_tool_result_requires_preceding_call() -> None:
    """A result without an earlier matching call should be rejected."""

    with pytest.raises(
        ValidationError,
        match="tool result has no preceding tool call",
    ):
        make_trajectory(
            events=[
                make_tool_result(
                    step_id=0,
                    tool_call_id="call-missing",
                ),
            ]
        )


def test_tool_result_must_follow_its_call() -> None:
    """A result appearing before its call should be rejected."""

    with pytest.raises(
        ValidationError,
        match="tool result has no preceding tool call",
    ):
        make_trajectory(
            events=[
                make_tool_result(
                    step_id=0,
                    tool_call_id="call-1",
                ),
                make_tool_call(
                    step_id=1,
                    tool_call_id="call-1",
                ),
            ]
        )


def test_multiple_results_for_one_call_are_rejected() -> None:
    """Each tool call may have at most one result."""

    with pytest.raises(
        ValidationError,
        match="multiple results found for tool call",
    ):
        make_trajectory(
            events=[
                make_tool_call(step_id=0),
                make_tool_result(step_id=1),
                make_tool_result(step_id=2),
            ]
        )


def test_tool_name_must_match_between_call_and_result() -> None:
    """Call and result tool names must be identical."""

    with pytest.raises(
        ValidationError,
        match="tool name differs between call and result",
    ):
        make_trajectory(
            events=[
                make_tool_call(
                    step_id=0,
                    tool_name="get_user_details",
                ),
                make_tool_result(
                    step_id=1,
                    tool_name="get_reservation_details",
                ),
            ]
        )


def test_unfinished_tool_call_is_allowed() -> None:
    """An interrupted trajectory may end before a tool result arrives."""

    trajectory = make_trajectory(
        events=[
            make_tool_call(step_id=0),
        ]
    )

    assert len(trajectory.events) == 1
    assert isinstance(trajectory.events[0], ToolCallEvent)


def test_unknown_event_fields_are_rejected() -> None:
    """Strict models should reject undeclared fields."""

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        MessageEvent(
            step_id=0,
            event_type="message",
            actor="user",
            content="hello",
            unknown_field="unexpected",
        )