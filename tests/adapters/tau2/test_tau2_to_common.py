"""Tests for direct tau2-to-common v0.2 conversion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.adapters.tau2.tau2_to_common import (
    convert_file,
    normalize_message_content,
)
from src.trajectory.schema import (
    MessageEvent,
    ToolCallEvent,
    ToolResultEvent,
    TrajectoryDataset,
)


def make_tau2_results() -> dict[str, Any]:
    """Build a minimal tau2 results file with one tool interaction."""
    return {
        "info": {
            "git_commit": "1d244f5dca42944b67a379b44bfeb9f5748f189d",
            "environment_info": {
                "domain_name": "airline",
            },
        },
        "simulations": [
            {
                "id": "trajectory-1",
                "task_id": "5",
                "termination_reason": "user_stop",
                "seed": 123,
                "trial": 0,
                "policy": "Airline policy text.",
                "messages": [
                    {
                        "role": "assistant",
                        "content": "How can I help?",
                        "tool_calls": None,
                        "turn_idx": 0,
                        "timestamp": "2026-07-30T14:20:00",
                    },
                    {
                        "role": "user",
                        "content": "Find my reservation.",
                        "tool_calls": None,
                        "turn_idx": 1,
                        "timestamp": "2026-07-30T14:20:01",
                    },
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "name": "get_reservation_details",
                                "arguments": {
                                    "reservation_id": "ABC123",
                                },
                            }
                        ],
                        "turn_idx": 2,
                        "timestamp": "2026-07-30T14:20:02",
                    },
                    {
                        "role": "tool",
                        "id": "call-1",
                        "content": json.dumps(
                            {
                                "reservation_id": "ABC123",
                                "status": "confirmed",
                            }
                        ),
                        "error": False,
                        "turn_idx": 3,
                        "timestamp": "2026-07-30T14:20:03",
                    },
                ],
                "reward_info": {
                    "reward": 1.0,
                    "reward_breakdown": {
                        "DB": 1.0,
                        "COMMUNICATE": 1.0,
                    },
                },
            }
        ],
    }


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('{"message":"hello"}', "hello"),
        ('{"response":"hello"}', "hello"),
        ('{"message":"hello","other":1}', '{"message":"hello","other":1}'),
    ],
)
def test_normalize_message_content_matches_v02_migration(
    source: str,
    expected: str,
) -> None:
    """Direct conversion and historical migration should normalize alike."""
    assert normalize_message_content(source) == expected


def test_convert_file_writes_valid_v02_dataset(
    tmp_path: Path,
) -> None:
    """The adapter should write schema v0.2 without an intermediate v0.1."""
    input_path = tmp_path / "results.json"
    output_path = tmp_path / "common_v02.json"
    input_path.write_text(
        json.dumps(make_tau2_results()),
        encoding="utf-8",
    )

    dataset = convert_file(input_path, output_path)
    loaded = TrajectoryDataset.model_validate_json(
        output_path.read_text(encoding="utf-8")
    )

    assert dataset == loaded
    assert loaded.schema_version == "0.2.0"
    assert loaded.migrated_from is None
    assert len(loaded.trajectories) == 1

    trajectory = loaded.trajectories[0]
    assert trajectory.environment.name == "tau2"
    assert trajectory.environment.domain == "airline"
    assert trajectory.policy_version == (
        "1d244f5dca42944b67a379b44bfeb9f5748f189d"
    )
    assert trajectory.initial_state is None
    assert trajectory.final_state is None
    assert trajectory.outcome.score == 1.0
    assert trajectory.outcome.reward_breakdown == {
        "DB": 1.0,
        "COMMUNICATE": 1.0,
    }
    assert trajectory.outcome.termination_reason == "user_stop"
    assert "messages" not in trajectory.raw_payload
    assert trajectory.raw_payload["policy"] == "Airline policy text."

    assert len(trajectory.events) == 4
    assert isinstance(trajectory.events[0], MessageEvent)
    assert isinstance(trajectory.events[2], ToolCallEvent)
    assert isinstance(trajectory.events[3], ToolResultEvent)
    assert [event.step_id for event in trajectory.events] == [0, 1, 2, 3]
    assert all(event.state_delta is None for event in trajectory.events)
    assert trajectory.events[2].raw_payload == {
        "id": "call-1",
        "name": "get_reservation_details",
        "arguments": {
            "reservation_id": "ABC123",
        },
    }


def test_day2_real_results_convert_directly_to_v02(
    tmp_path: Path,
) -> None:
    """The five real Day 2 simulations should convert without migration."""
    repository_root = Path(__file__).resolve().parents[3]
    input_path = (
        repository_root
        / "external"
        / "tau2-bench"
        / "data"
        / "simulations"
        / "20260730_day2_airline_tasks_5_9"
        / "results.json"
    )

    if not input_path.exists():
        pytest.skip("The local tau2 Day 2 results are unavailable")

    dataset = convert_file(
        input_path,
        tmp_path / "common_trajectories_v02.json",
    )

    assert dataset.schema_version == "0.2.0"
    assert len(dataset.trajectories) == 5
    assert sum(len(item.events) for item in dataset.trajectories) == 106
    assert {
        item.task_id: item.outcome.score
        for item in dataset.trajectories
    } == {
        "5": 1.0,
        "6": 1.0,
        "7": 0.0,
        "8": 1.0,
        "9": 1.0,
    }
