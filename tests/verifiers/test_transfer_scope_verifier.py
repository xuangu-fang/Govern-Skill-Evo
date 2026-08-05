"""Tests for the transfer-scope verifier."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.trajectory.schema import (
    EnvironmentRef,
    MessageEvent,
    TaskOutcome,
    ToolCallEvent,
    Trajectory,
    TrajectoryDataset,
)
from src.verifiers.transfer_scope_verifier import (
    TransferScopeJudgment,
    TransferScopeJudgmentDataset,
    verify_dataset,
    verify_transfer_scope,
)


def trajectory(*, transferred: bool) -> Trajectory:
    """Build a minimal trajectory with an optional transfer call."""
    events = [
        MessageEvent(
            step_id=0,
            event_type="message",
            actor="user",
            content="Please help me.",
        )
    ]
    if transferred:
        events.append(
            ToolCallEvent(
                step_id=1,
                event_type="tool_call",
                actor="agent",
                tool_call_id="transfer-1",
                tool_name="transfer_to_human_agents",
                arguments={"summary": "User needs help."},
            )
        )

    return Trajectory(
        trajectory_id="trajectory-1",
        environment=EnvironmentRef(name="tau2", domain="airline"),
        task_id="1",
        events=events,
        outcome=TaskOutcome(score=None),
    )


def judgment(should_transfer: bool | None) -> TransferScopeJudgment:
    """Build one independent semantic input."""
    return TransferScopeJudgment(
        trajectory_id="trajectory-1",
        should_transfer=should_transfer,
        decision_step_id=0 if should_transfer is True else None,
        evidence_step_ids=[] if should_transfer is None else [0],
        rationale="Semantic scope decision.",
    )


@pytest.mark.parametrize(
    ("transferred", "should_transfer"),
    [(False, False), (True, True)],
)
def test_matching_actual_and_expected_transfer_is_compliant(
    transferred: bool,
    should_transfer: bool,
) -> None:
    """The merger accepts matching deterministic and semantic facts."""
    verdict = verify_transfer_scope(
        trajectory(transferred=transferred),
        judgment(should_transfer),
        judge_name="fake-judge",
        judge_version="0.1.0",
    )

    assert verdict.compliant is True
    assert verdict.violations == []


def test_unnecessary_transfer_is_violation() -> None:
    """An actual transfer conflicts with should_transfer=false."""
    verdict = verify_transfer_scope(
        trajectory(transferred=True),
        judgment(False),
        judge_name="fake-judge",
        judge_version="0.1.0",
    )

    assert verdict.compliant is False
    assert verdict.violations[0].rule_id == "airline.transfer.scope.001"
    assert verdict.violations[0].step_id == 1


def test_missing_required_transfer_is_violation() -> None:
    """No actual transfer conflicts with should_transfer=true."""
    verdict = verify_transfer_scope(
        trajectory(transferred=False),
        judgment(True),
        judge_name="fake-judge",
        judge_version="0.1.0",
    )

    assert verdict.compliant is False
    assert verdict.violations[0].step_id == 0


def test_uncertain_semantics_produce_unknown_compliance() -> None:
    """The pure merger must preserve an unresolved Judge answer."""
    verdict = verify_transfer_scope(
        trajectory(transferred=False),
        judgment(None),
        judge_name="fake-judge",
        judge_version="0.1.0",
    )

    assert verdict.compliant is None
    assert verdict.violations == []


def test_dataset_requires_exact_semantic_coverage() -> None:
    """Every trajectory must have exactly one external judgment."""
    dataset = TrajectoryDataset(
        source_format="test",
        trajectories=[trajectory(transferred=False)],
    )
    semantic_inputs = TransferScopeJudgmentDataset(
        judge_name="fake-judge",
        judge_version="0.1.0",
        judgments=[],
    )

    with pytest.raises(ValueError, match="coverage must exactly match"):
        verify_dataset(dataset, semantic_inputs)


def test_human_gold_and_common_trajectories_match_expected_verdicts() -> None:
    """The five adjudicated labels exercise the merger end to end."""
    root = Path(__file__).resolve().parents[2]
    trajectory_path = (
        root
        / "experiments/results/day5_schema/common_trajectories_v02.json"
    )
    gold_path = (
        root
        / "experiments/annotations/transfer_scope_v01/gold/"
        / "human_adjudicated.json"
    )
    if not trajectory_path.exists() or not gold_path.exists():
        pytest.skip("local experiment fixtures are unavailable")

    import json

    dataset = TrajectoryDataset.model_validate_json(
        trajectory_path.read_text(encoding="utf-8")
    )
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    semantic_inputs = TransferScopeJudgmentDataset(
        judge_name="human-adjudicated-gold",
        judge_version=gold["gold_version"],
        judgments=[
            TransferScopeJudgment(
                trajectory_id=label["trajectory_id"],
                should_transfer=label["should_transfer"],
                decision_step_id=(
                    label["trajectory_evidence"][-1]["step_id"]
                    if label["should_transfer"]
                    else None
                ),
                evidence_step_ids=[
                    item["step_id"]
                    for item in label["trajectory_evidence"]
                ],
                rationale=label["expected_behavior"],
            )
            for label in gold["labels"]
        ],
    )

    verdicts = verify_dataset(dataset, semantic_inputs)
    actual = {
        item.trajectory_id: item.compliant
        for item in verdicts.verdicts
    }
    expected = {
        label["trajectory_id"]: label["verdict"] == "compliant"
        for label in gold["labels"]
    }

    assert actual == expected
