"""Tests for the upstream-outcome task verifier."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.trajectory.schema import (
    EnvironmentRef,
    MessageEvent,
    TaskOutcome,
    Trajectory,
    TrajectoryDataset,
)
from src.verifiers.task_verifier import (
    VERIFIER_NAME,
    VERIFIER_VERSION,
    verify_dataset,
    verify_task,
)


@pytest.mark.parametrize(
    ("score", "expected_success"),
    [(1.0, True), (0.5, False), (None, None)],
)
def test_score_mapping(
    score: float | None,
    expected_success: bool | None,
) -> None:
    """Official scores should map to success without forced guesses."""
    trajectory = Trajectory(
        trajectory_id="trajectory-1",
        environment=EnvironmentRef(name="tau2", domain="airline"),
        task_id="1",
        events=[
            MessageEvent(
                step_id=0,
                event_type="message",
                actor="user",
                content="Please help me.",
            )
        ],
        outcome=TaskOutcome(score=score),
    )

    verdict = verify_task(trajectory)

    assert verdict.success is expected_success
    assert verdict.score == score
    assert verdict.evidence[0].source == "outcome.score"
    assert verdict.evidence[0].value == score


def test_day5_scores_produce_expected_task_verdicts() -> None:
    """The ten official scores should produce evidenced task verdicts."""
    repository_root = Path(__file__).resolve().parents[2]
    trajectory_path = (
        repository_root
        / "experiments/results/day5_schema/common_trajectories_v02.json"
    )
    dataset = TrajectoryDataset.model_validate_json(
        trajectory_path.read_text(encoding="utf-8")
    )
    expected = {
        "5": (1.0, True),
        "6": (1.0, True),
        "7": (0.0, False),
        "8": (1.0, True),
        "9": (1.0, True),
        "10": (1.0, True),
        "11": (1.0, True),
        "12": (0.0, False),
        "13": (1.0, True),
        "14": (0.0, False),
    }

    result = verify_dataset(dataset)

    assert result.verifier_name == VERIFIER_NAME
    assert result.verifier_version == VERIFIER_VERSION
    assert len(dataset.trajectories) == len(result.verdicts) == 10
    assert {item.task_id for item in dataset.trajectories} == set(expected)

    for trajectory, verdict in zip(
        dataset.trajectories,
        result.verdicts,
        strict=True,
    ):
        expected_score, expected_success = expected[trajectory.task_id]
        assert trajectory.outcome.score == expected_score
        assert verdict.trajectory_id == trajectory.trajectory_id
        assert verdict.score == expected_score
        assert verdict.success is expected_success
        assert len(verdict.evidence) == 1

        evidence = verdict.evidence[0]
        assert evidence.trajectory_id == trajectory.trajectory_id
        assert evidence.step_id is None
        assert evidence.source == "outcome.score"
        assert evidence.value == expected_score
