"""Normalize real tau2 message trajectories into auditable events."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ..compiler.resolvers import ensure_tau2_importable

ensure_tau2_importable()

from tau2.data_model.message import (  # noqa: E402
    AssistantMessage,
    Message,
    MultiToolMessage,
    ToolMessage,
)
from tau2.data_model.simulation import SimulationRun  # noqa: E402


@dataclass
class TrajectoryEvent:
    event_index: int
    message_index: int
    event_type: str
    role: str
    tool_call_index: int | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    tool_result: str | None = None
    tool_error: bool | None = None
    assistant_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value is not None
        }


def trajectory_messages(
    trajectory: SimulationRun | Iterable[Message],
) -> list[Message]:
    if isinstance(trajectory, SimulationRun):
        return trajectory.get_messages()
    return list(trajectory)


def _tool_results(messages: list[Message]) -> dict[str, ToolMessage]:
    results: dict[str, ToolMessage] = {}
    for message in messages:
        if isinstance(message, ToolMessage):
            results[message.id] = message
        elif isinstance(message, MultiToolMessage):
            results.update({result.id: result for result in message.tool_messages})
    return results


def extract_trajectory_events(
    trajectory: SimulationRun | Iterable[Message],
) -> list[TrajectoryEvent]:
    """Extract assistant text and assistant-requested tools in message order."""

    messages = trajectory_messages(trajectory)
    results = _tool_results(messages)
    events: list[TrajectoryEvent] = []
    for message_index, message in enumerate(messages):
        if not isinstance(message, AssistantMessage):
            continue
        if message.has_text_content():
            events.append(
                TrajectoryEvent(
                    event_index=len(events),
                    message_index=message_index,
                    event_type="assistant_text",
                    role="assistant",
                    assistant_text=message.content,
                )
            )
        for call_index, call in enumerate(message.tool_calls or []):
            result = results.get(call.id)
            events.append(
                TrajectoryEvent(
                    event_index=len(events),
                    message_index=message_index,
                    event_type="tool_call",
                    role="assistant",
                    tool_call_index=call_index,
                    tool_call_id=call.id,
                    tool_name=call.name,
                    tool_arguments=dict(call.arguments),
                    tool_result=result.content if result is not None else None,
                    tool_error=result.error if result is not None else None,
                )
            )
    return events
