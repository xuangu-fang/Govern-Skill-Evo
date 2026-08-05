"""Tests for the temporary v0.1 to v0.2 migration."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from src.trajectory.migrations.v01_to_v02 import (
    migrate_file,
    normalize_message_content,
)
from src.trajectory.schema import (
    MessageEvent,
    ToolCallEvent,
    ToolResultEvent,
    TrajectoryDataset,
)


def make_v01_dataset() -> dict[str, Any]:
    """Build a small temporary v0.1 dataset for migration tests."""

    return {
        "schema_version": "0.1",
        "source_format": "tau2_results",
        "trajectories": [
            {
                "trajectory_id": "trajectory-1",
                "environment": "tau2_airline",
                "task_id": 5,
                "events": [
                    {
                        "actor": "user",
                        "event_type": "message",
                        "content": '{"message":"Please find my reservation."}',
                        "tool_call_id": None,
                        "tool_name": None,
                        "tool_args": None,
                        "tool_result": None,
                        "metadata": {
                            "source_turn_idx": 0,
                            "timestamp": "2026-07-30T14:20:00",
                        },
                        "step_id": 0,
                    },
                    {
                        "actor": "agent",
                        "event_type": "tool_call",
                        "content": None,
                        "tool_call_id": "call-1",
                        "tool_name": "get_reservation_details",
                        "tool_args": {
                            "reservation_id": "ABC123",
                        },
                        "tool_result": None,
                        "metadata": {
                            "source_turn_idx": 1,
                            "timestamp": "2026-07-30T14:20:01",
                        },
                        "step_id": 1,
                    },
                    {
                        "actor": "tool",
                        "event_type": "tool_result",
                        "content": None,
                        "tool_call_id": "call-1",
                        "tool_name": "get_reservation_details",
                        "tool_args": None,
                        "tool_result": {
                            "reservation_id": "ABC123",
                            "status": "confirmed",
                        },
                        "metadata": {
                            "source_turn_idx": 2,
                            "timestamp": "2026-07-30T14:20:02",
                            "error": False,
                            "provider_tag": "preserved",
                        },
                        "step_id": 2,
                    },
                ],
                "task_score": 1.0,
                "metadata": {
                    "termination_reason": "user_stop",
                    "reward_breakdown": {
                        "DB": 1.0,
                        "COMMUNICATE": 1.0,
                    },
                    "seed": 123,
                    "trial": 0,
                },
            }
        ],
    }


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    """Write JSON test data using UTF-8."""

    path.write_text(
        json.dumps(value, indent=2),
        encoding="utf-8",
    )


def test_normalize_plain_message() -> None:
    """Ordinary message strings should remain unchanged."""

    assert normalize_message_content("hello") == "hello"


def test_normalize_message_wrapper() -> None:
    """A single-key message wrapper should be unwrapped."""

    assert (
        normalize_message_content('{"message":"hello"}')
        == "hello"
    )


def test_normalize_response_wrapper() -> None:
    """A single-key response wrapper should be unwrapped."""

    assert (
        normalize_message_content('{"response":"hello"}')
        == "hello"
    )


def test_normalize_multi_key_json_is_not_unwrapped() -> None:
    """JSON objects with additional fields should remain unchanged."""

    value = '{"message":"hello","other":"value"}'

    assert normalize_message_content(value) == value


def test_normalize_non_string_is_rejected() -> None:
    """Message content must be a string."""

    with pytest.raises(
        ValueError,
        match="message content must be a string",
    ):
        normalize_message_content(
            {
                "message": "hello",
            }
        )


def test_migrate_file_converts_v01_to_v02(
    tmp_path: Path,
) -> None:
    """The migration should normalize and validate a v0.1 dataset."""

    input_path = tmp_path / "input_v01.json"
    output_path = tmp_path / "output_v02.json"

    raw_dataset = make_v01_dataset()
    write_json(input_path, raw_dataset)

    migrated = migrate_file(
        input_path=input_path,
        output_path=output_path,
    )

    assert output_path.exists()

    assert migrated.schema_version == "0.2.0"
    assert migrated.source_format == "tau2_results"
    assert migrated.migrated_from == "0.1"
    assert len(migrated.trajectories) == 1

    trajectory = migrated.trajectories[0]

    assert trajectory.trajectory_id == "trajectory-1"
    assert trajectory.environment.name == "tau2"
    assert trajectory.environment.domain == "airline"
    assert trajectory.environment.version is None
    assert trajectory.task_id == "5"

    assert trajectory.policy_version is None
    assert trajectory.initial_state is None
    assert trajectory.final_state is None

    assert trajectory.outcome.score == 1.0
    assert trajectory.outcome.reward_breakdown == {
        "DB": 1.0,
        "COMMUNICATE": 1.0,
    }
    assert trajectory.outcome.termination_reason == "user_stop"

    # Fields promoted into TaskOutcome should be removed from normalized
    # trajectory metadata.
    assert trajectory.metadata == {
        "seed": 123,
        "trial": 0,
    }

    # Trajectory-level raw payload preserves the old top-level fields,
    # but excludes the old event list to avoid duplicate storage.
    assert "events" not in trajectory.raw_payload
    assert trajectory.raw_payload["trajectory_id"] == "trajectory-1"
    assert trajectory.raw_payload["environment"] == "tau2_airline"
    assert trajectory.raw_payload["task_id"] == 5
    assert trajectory.raw_payload["task_score"] == 1.0
    assert trajectory.raw_payload["metadata"] == raw_dataset[
        "trajectories"
    ][0]["metadata"]


def test_migration_normalizes_event_fields(
    tmp_path: Path,
) -> None:
    """Provider-specific event fields should be normalized."""

    input_path = tmp_path / "input_v01.json"
    output_path = tmp_path / "output_v02.json"

    raw_dataset = make_v01_dataset()
    write_json(input_path, raw_dataset)

    dataset = migrate_file(
        input_path=input_path,
        output_path=output_path,
    )

    events = dataset.trajectories[0].events

    assert len(events) == 3

    message = events[0]
    tool_call = events[1]
    tool_result = events[2]

    assert isinstance(message, MessageEvent)
    assert message.content == "Please find my reservation."
    assert message.source_turn_idx == 0
    assert message.timestamp == datetime.fromisoformat(
        "2026-07-30T14:20:00"
    )
    assert message.state_delta is None
    assert message.metadata == {}

    assert isinstance(tool_call, ToolCallEvent)
    assert tool_call.tool_call_id == "call-1"
    assert tool_call.tool_name == "get_reservation_details"
    assert tool_call.arguments == {
        "reservation_id": "ABC123",
    }
    assert tool_call.source_turn_idx == 1
    assert tool_call.state_delta is None

    assert isinstance(tool_result, ToolResultEvent)
    assert tool_result.tool_call_id == "call-1"
    assert tool_result.tool_name == "get_reservation_details"
    assert tool_result.result == {
        "reservation_id": "ABC123",
        "status": "confirmed",
    }
    assert tool_result.error is False
    assert tool_result.source_turn_idx == 2
    assert tool_result.state_delta is None

    # source_turn_idx, timestamp, and error are promoted, while unrelated
    # metadata remains.
    assert tool_result.metadata == {
        "provider_tag": "preserved",
    }


def test_migration_preserves_each_original_event(
    tmp_path: Path,
) -> None:
    """Every normalized event should retain its original source object."""

    input_path = tmp_path / "input_v01.json"
    output_path = tmp_path / "output_v02.json"

    raw_dataset = make_v01_dataset()
    write_json(input_path, raw_dataset)

    dataset = migrate_file(
        input_path=input_path,
        output_path=output_path,
    )

    original_events = raw_dataset["trajectories"][0]["events"]
    migrated_events = dataset.trajectories[0].events

    assert len(original_events) == len(migrated_events)

    for original, migrated in zip(
        original_events,
        migrated_events,
        strict=True,
    ):
        assert migrated.raw_payload == original


def test_written_output_can_be_loaded_again(
    tmp_path: Path,
) -> None:
    """The JSON written by the migration should pass schema validation."""

    input_path = tmp_path / "input_v01.json"
    output_path = tmp_path / "output_v02.json"

    write_json(input_path, make_v01_dataset())

    migrate_file(
        input_path=input_path,
        output_path=output_path,
    )

    loaded = TrajectoryDataset.model_validate_json(
        output_path.read_text(encoding="utf-8")
    )

    assert loaded.schema_version == "0.2.0"
    assert len(loaded.trajectories) == 1
    assert len(loaded.trajectories[0].events) == 3


def test_unsupported_source_version_is_rejected(
    tmp_path: Path,
) -> None:
    """The migration should reject inputs that are not common v0.1."""

    input_path = tmp_path / "input_v02.json"
    output_path = tmp_path / "output.json"

    write_json(
        input_path,
        {
            "schema_version": "0.2.0",
            "source_format": "tau2_results",
            "trajectories": [],
        },
    )

    with pytest.raises(
        ValueError,
        match="only supports common trajectory v0.1",
    ):
        migrate_file(
            input_path=input_path,
            output_path=output_path,
        )


def test_missing_trajectories_list_is_rejected(
    tmp_path: Path,
) -> None:
    """The input must contain a trajectories list."""

    input_path = tmp_path / "invalid.json"
    output_path = tmp_path / "output.json"

    write_json(
        input_path,
        {
            "schema_version": "0.1",
            "source_format": "tau2_results",
            "trajectories": {},
        },
    )

    with pytest.raises(
        ValueError,
        match="must contain a trajectories list",
    ):
        migrate_file(
            input_path=input_path,
            output_path=output_path,
        )


def test_day4_real_dataset_migration(
    tmp_path: Path,
) -> None:
    """
    Optionally validate the real Day 4 dataset.

    The test is skipped when generated experiment files are unavailable,
    such as in a clean CI checkout.
    """

    repository_root = Path(__file__).resolve().parents[2]

    input_path = (
        repository_root
        / "experiments"
        / "results"
        / "day4_trace2skill"
        / "common_trajectories.json"
    )

    if not input_path.exists():
        pytest.skip(
            "Day 4 generated trajectory file is not available"
        )

    output_path = tmp_path / "common_trajectories_v02.json"

    dataset = migrate_file(
        input_path=input_path,
        output_path=output_path,
    )

    events = [
        event
        for trajectory in dataset.trajectories
        for event in trajectory.events
    ]

    tool_calls = [
        event
        for event in events
        if isinstance(event, ToolCallEvent)
    ]

    tool_results = [
        event
        for event in events
        if isinstance(event, ToolResultEvent)
    ]

    assert dataset.schema_version == "0.2.0"
    assert len(dataset.trajectories) == 5
    assert len(events) == 106

    assert len(tool_calls) == 29
    assert len(tool_results) == 29

    assert all(
        event.state_delta is None
        for event in events
    )

    assert all(
        event.raw_payload
        for event in events
    )

    assert all(
        "events" not in trajectory.raw_payload
        for trajectory in dataset.trajectories
    )

    scores = {
        trajectory.task_id: trajectory.outcome.score
        for trajectory in dataset.trajectories
    }

    assert scores == {
        "5": 1.0,
        "6": 1.0,
        "7": 0.0,
        "8": 1.0,
        "9": 1.0,
    }