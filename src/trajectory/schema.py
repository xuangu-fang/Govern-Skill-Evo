"""Versioned common trajectory schema."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    model_validator,
)


SCHEMA_VERSION = "0.2.0"


class StrictModel(BaseModel):
    """Reject unknown fields so schema changes remain explicit."""

    model_config = ConfigDict(extra="forbid")


class EnvironmentRef(StrictModel):
    """Environment that produced the trajectory."""

    name: str = Field(min_length=1)
    domain: str | None = None
    version: str | None = None


class BaseEvent(StrictModel):
    """Fields shared by every normalized event."""

    step_id: int = Field(ge=0)

    # Position in the original provider-specific message stream.
    source_turn_idx: int | None = Field(default=None, ge=0)

    # Execution timestamp supplied by the source environment.
    timestamp: datetime | None = None

    # State change associated with this event.
    #
    # None means that the source format did not provide a recoverable
    # state transition for this event. The value may otherwise contain
    # any JSON-compatible representation, such as:
    #
    # {
    #     "reservation.status": {
    #         "before": "confirmed",
    #         "after": "cancelled",
    #     }
    # }
    state_delta: JsonValue | None = None

    # Adapter-independent auxiliary information.
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    # Exact source object from which this event was converted.
    #
    # Event-level raw payloads preserve each original source event.
    raw_payload: dict[str, JsonValue] = Field(default_factory=dict)


class MessageEvent(BaseEvent):
    """Natural-language message sent by the user or agent."""

    event_type: Literal["message"]
    actor: Literal["agent", "user"]
    content: str


class ToolCallEvent(BaseEvent):
    """Tool invocation requested by the agent."""

    event_type: Literal["tool_call"]
    actor: Literal["agent"]

    tool_call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: dict[str, JsonValue] = Field(default_factory=dict)


class ToolResultEvent(BaseEvent):
    """Result returned by a tool invocation."""

    event_type: Literal["tool_result"]
    actor: Literal["tool"]

    tool_call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    result: JsonValue
    error: bool = False


Event = Annotated[
    MessageEvent | ToolCallEvent | ToolResultEvent,
    Field(discriminator="event_type"),
]


class TaskOutcome(StrictModel):
    """Outcome reported by the upstream benchmark."""

    score: float | None = None
    reward_breakdown: dict[str, float] = Field(default_factory=dict)
    termination_reason: str | None = None


class Trajectory(StrictModel):
    """Normalized trajectory produced by an environment run."""

    trajectory_id: str = Field(min_length=1)

    environment: EnvironmentRef
    task_id: str = Field(min_length=1)

    # Unknown is different from an empty version.
    policy_version: str | None = None

    # Do not fabricate state snapshots when the source does not provide them.
    initial_state: JsonValue | None = None
    final_state: JsonValue | None = None

    events: list[Event] = Field(min_length=1)
    outcome: TaskOutcome

    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    # Original trajectory-level source fields that are not already preserved
    # by individual Event.raw_payload values.
    #
    # In particular, the original source "events" list should be excluded
    # here to avoid storing every source event twice.
    raw_payload: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_event_sequence(self) -> "Trajectory":
        """Validate event ordering and tool-call linkage."""

        actual_steps = [event.step_id for event in self.events]
        expected_steps = list(range(len(self.events)))

        if actual_steps != expected_steps:
            raise ValueError(
                "event step_id values must be contiguous and start at zero; "
                f"expected={expected_steps}, actual={actual_steps}"
            )

        calls: dict[str, ToolCallEvent] = {}
        completed_calls: set[str] = set()

        for event in self.events:
            if isinstance(event, ToolCallEvent):
                if event.tool_call_id in calls:
                    raise ValueError(
                        f"duplicate tool_call_id: {event.tool_call_id}"
                    )

                calls[event.tool_call_id] = event
                continue

            if isinstance(event, ToolResultEvent):
                call = calls.get(event.tool_call_id)

                if call is None:
                    raise ValueError(
                        "tool result has no preceding tool call: "
                        f"{event.tool_call_id}"
                    )

                if event.tool_call_id in completed_calls:
                    raise ValueError(
                        "multiple results found for tool call: "
                        f"{event.tool_call_id}"
                    )

                if call.tool_name != event.tool_name:
                    raise ValueError(
                        "tool name differs between call and result: "
                        f"{call.tool_name!r} != {event.tool_name!r}"
                    )

                completed_calls.add(event.tool_call_id)

        # An unfinished trajectory may contain a tool call without a result,
        # so unmatched calls are not rejected here.
        return self


class TrajectoryDataset(StrictModel):
    """Collection of normalized trajectories using one schema version."""

    schema_version: Literal["0.2.0"] = SCHEMA_VERSION

    # Original upstream format, such as tau2_results.
    source_format: str = Field(min_length=1)

    # Used when loading an older common representation.
    migrated_from: str | None = None

    trajectories: list[Trajectory]