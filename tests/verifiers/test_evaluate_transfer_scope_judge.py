"""Tests for Judge-versus-Gold evaluation."""

from __future__ import annotations

import pytest

from src.verifiers.evaluate_transfer_scope_judge import evaluate_judge
from src.verifiers.transfer_scope_verifier import (
    TransferScopeJudgment,
    TransferScopeJudgmentDataset,
)


def judgment(
    trajectory_id: str,
    should_transfer: bool | None,
) -> TransferScopeJudgment:
    """Build one semantic prediction."""
    return TransferScopeJudgment(
        trajectory_id=trajectory_id,
        should_transfer=should_transfer,
        decision_step_id=0 if should_transfer is True else None,
        evidence_step_ids=[] if should_transfer is None else [0],
        rationale="test judgment",
    )


def gold(*ids_and_labels: tuple[str, bool]) -> dict:
    """Build a completed minimal human-Gold object."""
    return {
        "gold_version": "0.1.0",
        "rule": {"rule_id": "airline.transfer.scope.001"},
        "review": {"status": "complete"},
        "labels": [
            {
                "trajectory_id": trajectory_id,
                "task_id": str(index),
                "rule_id": "airline.transfer.scope.001",
                "should_transfer": should_transfer,
            }
            for index, (trajectory_id, should_transfer) in enumerate(
                ids_and_labels,
                start=1,
            )
        ],
    }


def test_evaluate_judge_reports_coverage_accuracy_and_confusion() -> None:
    """Uncertain answers reduce coverage but are not forced incorrect."""
    dataset = TransferScopeJudgmentDataset(
        judge_name="fake-model",
        judge_version="0.1.0",
        judgments=[
            judgment("tp", True),
            judgment("tn", False),
            judgment("fp", True),
            judgment("fn", False),
            judgment("uncertain", None),
        ],
    )
    human_gold = gold(
        ("tp", True),
        ("tn", False),
        ("fp", False),
        ("fn", True),
        ("uncertain", True),
    )

    report = evaluate_judge(dataset, human_gold)
    metrics = report["metrics"]

    assert metrics["total"] == 5
    assert metrics["determinate_predictions"] == 4
    assert metrics["uncertain_predictions"] == 1
    assert metrics["coverage"] == pytest.approx(0.8)
    assert metrics["accuracy_on_determinate"] == pytest.approx(0.5)
    assert metrics["confusion_matrix"] == {
        "true_positive": 1,
        "true_negative": 1,
        "false_positive": 1,
        "false_negative": 1,
    }
    assert report["cases"][-1]["correct"] is None


def test_evaluate_judge_requires_exact_gold_coverage() -> None:
    """A partial judge run must not masquerade as a full evaluation."""
    dataset = TransferScopeJudgmentDataset(
        judge_name="fake-model",
        judge_version="0.1.0",
        judgments=[judgment("only-one", False)],
    )

    with pytest.raises(ValueError, match="coverage must exactly match"):
        evaluate_judge(
            dataset,
            gold(("only-one", False), ("missing", True)),
        )
