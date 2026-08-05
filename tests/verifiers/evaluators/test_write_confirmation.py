"""Tests for write-confirmation Human-Gold evaluation."""

from __future__ import annotations

import pytest

from src.verifiers.evaluators.write_confirmation import (
    WriteConfirmationGold,
    evaluate_write_confirmation,
)
from src.verifiers.handlers.semantic.write_confirmation import (
    WriteConfirmationAssessment,
    WriteConfirmationJudgment,
    WriteConfirmationJudgmentDataset,
)


def gold_assessment(
    write_step_id: int,
    *,
    details_sufficient: bool,
    confirmation_valid: bool,
) -> dict:
    """Build one resolved Gold action."""
    return {
        "write_step_id": write_step_id,
        "details_sufficient": details_sufficient,
        "confirmation_valid": confirmation_valid,
        "details_step_ids": [write_step_id - 2]
        if details_sufficient
        else [],
        "confirmation_step_ids": [write_step_id - 1]
        if confirmation_valid
        else [],
        "compliant": details_sufficient and confirmation_valid,
        "rationale": "Gold action judgment.",
    }


def gold_label(
    trajectory_id: str,
    task_id: str,
    assessment: dict,
) -> dict:
    """Build one Gold trajectory with a single write action."""
    return {
        "trajectory_id": trajectory_id,
        "task_id": task_id,
        "rule_id": "airline.write.confirmation.001",
        "covered_write_steps": [assessment["write_step_id"]],
        "assessments": [assessment],
        "compliant": assessment["compliant"],
        "rationale": "Gold trajectory judgment.",
        "confidence": "high",
    }


def gold(*labels: dict) -> WriteConfirmationGold:
    """Build a strictly validated Gold dataset."""
    return WriteConfirmationGold.model_validate(
        {
            "gold_version": "0.1.0",
            "annotation_type": "human_adjudicated_gold",
            "domain": "airline",
            "policy_version": "policy-1",
            "rule": {
                "rule_id": "airline.write.confirmation.001",
                "rule_version": "0.1.0",
                "type": "write_confirmation",
                "policy_statement": "List details and obtain confirmation.",
            },
            "annotation_guidelines": {"standard": "test"},
            "review": {
                "status": "complete",
                "method": "human_review",
                "reviewer": "test",
                "review_date": "2026-08-05",
                "trajectory_count": len(labels),
                "covered_write_count": len(labels),
            },
            "source_trajectories": "trajectories.json",
            "labels": list(labels),
        }
    )


def prediction(
    trajectory_id: str,
    write_step_id: int,
    *,
    details_sufficient: bool | None,
    confirmation_valid: bool | None,
) -> WriteConfirmationJudgment:
    """Build one predicted action with valid positive citations."""
    return WriteConfirmationJudgment(
        trajectory_id=trajectory_id,
        assessments=[
            WriteConfirmationAssessment(
                write_step_id=write_step_id,
                details_sufficient=details_sufficient,
                confirmation_valid=confirmation_valid,
                details_step_ids=[write_step_id - 2]
                if details_sufficient is True
                else [],
                confirmation_step_ids=[write_step_id - 1]
                if confirmation_valid is True
                else [],
                rationale="Predicted action judgment.",
            )
        ],
        rationale="Predicted trajectory judgment.",
    )


def test_evaluation_compares_actions_fields_and_evidence() -> None:
    """Resolved matches and uncertain actions are reported separately."""
    human_gold = gold(
        gold_label(
            "compliant",
            "1",
            gold_assessment(
                3,
                details_sufficient=True,
                confirmation_valid=True,
            ),
        ),
        gold_label(
            "violation",
            "2",
            gold_assessment(
                6,
                details_sufficient=False,
                confirmation_valid=True,
            ),
        ),
        gold_label(
            "uncertain",
            "3",
            gold_assessment(
                9,
                details_sufficient=False,
                confirmation_valid=True,
            ),
        ),
    )
    judgments = WriteConfirmationJudgmentDataset(
        model_name="fake-model",
        semantic_version="0.1.0",
        judgments=[
            prediction(
                "compliant",
                3,
                details_sufficient=True,
                confirmation_valid=True,
            ),
            prediction(
                "violation",
                6,
                details_sufficient=False,
                confirmation_valid=True,
            ),
            prediction(
                "uncertain",
                9,
                details_sufficient=None,
                confirmation_valid=True,
            ),
        ],
    )

    report = evaluate_write_confirmation(judgments, human_gold)
    metrics = report["metrics"]

    assert metrics["trajectory_compliance"]["coverage"] == pytest.approx(
        2 / 3
    )
    assert metrics["trajectory_compliance"][
        "accuracy_on_determinate"
    ] == 1.0
    assert metrics["write_action_compliance"][
        "confusion_matrix"
    ] == {
        "true_positive": 1,
        "true_negative": 1,
        "false_positive": 0,
        "false_negative": 0,
    }
    assert metrics["write_coverage"]["trajectory_exact_match_rate"] == 1.0
    assert metrics["semantic_fields"]["details_sufficient"] == {
        "matched_actions": 3,
        "determinate_predictions": 2,
        "uncertain_predictions": 1,
        "accuracy_on_determinate": 1.0,
    }
    assert metrics["evidence_steps"]["confirmation_exact_match_rate"] == 1.0


def test_evaluation_requires_exact_trajectory_coverage() -> None:
    """Missing predictions cannot masquerade as a complete evaluation."""
    item = gold_assessment(
        3,
        details_sufficient=True,
        confirmation_valid=True,
    )
    human_gold = gold(
        gold_label("one", "1", item),
        gold_label("two", "2", item),
    )
    judgments = WriteConfirmationJudgmentDataset(
        model_name="fake-model",
        semantic_version="0.1.0",
        judgments=[
            prediction(
                "one",
                3,
                details_sufficient=True,
                confirmation_valid=True,
            )
        ],
    )

    with pytest.raises(ValueError, match="coverage must exactly match"):
        evaluate_write_confirmation(judgments, human_gold)


def test_gold_rejects_inconsistent_action_verdict() -> None:
    """Human Gold cannot contradict its resolved semantic fields."""
    item = gold_assessment(
        3,
        details_sufficient=True,
        confirmation_valid=True,
    )
    item["compliant"] = False

    with pytest.raises(ValueError, match="Gold action compliant"):
        gold(gold_label("one", "1", item))
