"""Migrate temporary common trajectory v0.1 to schema v0.2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.trajectory.schema import (
    EnvironmentRef,
    Event,
    MessageEvent,
    TaskOutcome,
    ToolCallEvent,
    ToolResultEvent,
    Trajectory,
    TrajectoryDataset,
)


def normalize_message_content(value: Any) -> str:
    """
    Normalize message content while preserving the original value.

    Strings such as:

        {"message": "..."}
        {"response": "..."}

    are unwrapped into ordinary message text. The original source event
    remains available through Event.raw_payload.
    """

    if not isinstance(value, str):
        raise ValueError(
            f"message content must be a string, got {type(value).__name__}"
        )

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value

    if isinstance(parsed, dict):
        for key in ("message", "response"):
            if (
                set(parsed.keys()) == {key}
                and isinstance(parsed[key], str)
            ):
                return parsed[key]

    return value


def migrate_event(raw_event: dict[str, Any]) -> Event:
    """Convert one temporary v0.1 event into a v0.2 event."""

    metadata = dict(raw_event.get("metadata") or {})

    common_fields = {
        "step_id": raw_event["step_id"],
        "source_turn_idx": metadata.pop("source_turn_idx", None),
        "timestamp": metadata.pop("timestamp", None),

        # Temporary v0.1 trajectories do not contain recoverable
        # per-event state transitions.
        "state_delta": None,

        "metadata": metadata,

        # Preserve the complete original event for step-level auditing.
        "raw_payload": dict(raw_event),
    }

    event_type = raw_event["event_type"]

    if event_type == "message":
        return MessageEvent(
            event_type="message",
            actor=raw_event["actor"],
            content=normalize_message_content(raw_event["content"]),
            **common_fields,
        )

    if event_type == "tool_call":
        return ToolCallEvent(
            event_type="tool_call",
            actor="agent",
            tool_call_id=raw_event["tool_call_id"],
            tool_name=raw_event["tool_name"],
            arguments=raw_event.get("tool_args") or {},
            **common_fields,
        )

    if event_type == "tool_result":
        # In temporary v0.1, error was stored inside metadata.
        error = bool(common_fields["metadata"].pop("error", False))

        return ToolResultEvent(
            event_type="tool_result",
            actor="tool",
            tool_call_id=raw_event["tool_call_id"],
            tool_name=raw_event["tool_name"],
            result=raw_event.get("tool_result"),
            error=error,
            **common_fields,
        )

    raise ValueError(f"unsupported event_type: {event_type!r}")


def parse_environment(value: str) -> EnvironmentRef:
    """
    Convert a temporary environment identifier into EnvironmentRef.

    Example:

        tau2_airline

    becomes:

        EnvironmentRef(name="tau2", domain="airline")
    """

    if not isinstance(value, str) or not value:
        raise ValueError(
            "environment must be a non-empty string in v0.1 data"
        )

    if "_" not in value:
        return EnvironmentRef(name=value)

    name, domain = value.split("_", maxsplit=1)

    return EnvironmentRef(
        name=name,
        domain=domain or None,
    )


def migrate_trajectory(raw: dict[str, Any]) -> Trajectory:
    """Convert one temporary v0.1 trajectory into v0.2."""

    metadata = dict(raw.get("metadata") or {})

    outcome = TaskOutcome(
        score=raw.get("task_score"),
        reward_breakdown=metadata.pop("reward_breakdown", {}),
        termination_reason=metadata.pop("termination_reason", None),
    )

    # Each original source event is already preserved in
    # Event.raw_payload. Exclude the complete old event list from the
    # trajectory-level payload to prevent duplicate storage.
    trajectory_raw_payload = {
        key: value
        for key, value in raw.items()
        if key != "events"
    }

    return Trajectory(
        trajectory_id=raw["trajectory_id"],
        environment=parse_environment(raw["environment"]),
        task_id=str(raw["task_id"]),
        policy_version=None,

        # The temporary common v0.1 file does not contain the original
        # environment state snapshots.
        initial_state=None,
        final_state=None,

        events=[
            migrate_event(event)
            for event in raw["events"]
        ],
        outcome=outcome,
        metadata=metadata,

        # Preserve only source-level trajectory fields. Original events
        # are preserved separately in each Event.raw_payload.
        raw_payload=trajectory_raw_payload,
    )


def migrate_file(
    input_path: Path,
    output_path: Path,
) -> TrajectoryDataset:
    """Migrate a v0.1 JSON file, validate it, and write v0.2 JSON."""

    raw_dataset = json.loads(
        input_path.read_text(encoding="utf-8")
    )

    source_version = raw_dataset.get("schema_version", "0.1")

    if source_version not in {"0.1", "0.1.0"}:
        raise ValueError(
            "this migration only supports common trajectory v0.1; "
            f"received schema_version={source_version!r}"
        )

    raw_trajectories = raw_dataset.get("trajectories")

    if not isinstance(raw_trajectories, list):
        raise ValueError(
            "input dataset must contain a trajectories list"
        )

    dataset = TrajectoryDataset(
        source_format=raw_dataset.get(
            "source_format",
            "unknown",
        ),
        migrated_from=source_version,
        trajectories=[
            migrate_trajectory(item)
            for item in raw_trajectories
        ],
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        dataset.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print(
        f"Migrated {len(dataset.trajectories)} trajectories "
        f"to schema {dataset.schema_version}: {output_path}"
    )

    return dataset


def main() -> None:
    """Command-line entry point."""

    parser = argparse.ArgumentParser(
        description=(
            "Migrate temporary common trajectory schema "
            "v0.1 to v0.2.0."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the v0.1 common trajectory JSON file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path at which to write the v0.2.0 JSON file.",
    )

    args = parser.parse_args()

    migrate_file(
        input_path=args.input,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()