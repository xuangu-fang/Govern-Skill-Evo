"""Evaluate write-confirmation judgments against Human Gold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    model_validator,
)

from src.verifiers.handlers.semantic.write_confirmation import (
    RULE_ID,
    WriteConfirmationAssessment,
    WriteConfirmationJudgment,
    WriteConfirmationJudgmentDataset,
)


EVALUATION_VERSION = "0.1.0"


class StrictModel(BaseModel):
    """Reject undeclared Human-Gold fields."""

    model_config = ConfigDict(extra="forbid")


class GoldRule(StrictModel):
    """Rule identity recorded by the Human Gold."""

    rule_id: Literal["airline.write.confirmation.001"] = RULE_ID
    rule_version: str = Field(min_length=1)
    type: Literal["write_confirmation"]
    policy_statement: str = Field(min_length=1)


class GoldReview(StrictModel):
    """Completed-review metadata used to guard evaluation inputs."""

    status: Literal["complete"]
    method: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    review_date: str = Field(min_length=1)
    trajectory_count: int = Field(ge=0)
    covered_write_count: int = Field(ge=0)


class GoldWriteAssessment(StrictModel):
    """Resolved human judgment for one covered write operation."""

    write_step_id: int = Field(ge=0)
    details_sufficient: bool
    confirmation_valid: bool
    details_step_ids: list[int] = Field(default_factory=list)
    confirmation_step_ids: list[int] = Field(default_factory=list)
    compliant: bool
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_consistency(self) -> "GoldWriteAssessment":
        """Keep the resolved action verdict consistent with its fields."""
        if self.compliant != (
            self.details_sufficient and self.confirmation_valid
        ):
            raise ValueError(
                "Gold action compliant must equal details_sufficient "
                "and confirmation_valid"
            )
        if self.details_sufficient and not self.details_step_ids:
            raise ValueError(
                "sufficient Gold details require details_step_ids"
            )
        if self.confirmation_valid and not self.confirmation_step_ids:
            raise ValueError(
                "valid Gold confirmation requires confirmation_step_ids"
            )
        if len(set(self.details_step_ids)) != len(self.details_step_ids):
            raise ValueError("duplicate Gold details_step_ids")
        if len(set(self.confirmation_step_ids)) != len(
            self.confirmation_step_ids
        ):
            raise ValueError("duplicate Gold confirmation_step_ids")
        return self


class GoldLabel(StrictModel):
    """Resolved Human Gold for one trajectory."""

    trajectory_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    rule_id: Literal["airline.write.confirmation.001"] = RULE_ID
    covered_write_steps: list[int] = Field(default_factory=list)
    assessments: list[GoldWriteAssessment] = Field(default_factory=list)
    compliant: bool
    rationale: str = Field(min_length=1)
    confidence: Literal["low", "medium", "high"]

    @model_validator(mode="after")
    def validate_consistency(self) -> "GoldLabel":
        """Require exact action coverage and a derived trajectory verdict."""
        assessment_steps = [
            assessment.write_step_id
            for assessment in self.assessments
        ]
        if self.covered_write_steps != assessment_steps:
            raise ValueError(
                "Gold covered_write_steps must match assessment steps"
            )
        if len(set(assessment_steps)) != len(assessment_steps):
            raise ValueError("duplicate Gold write_step_id")
        if self.compliant != all(
            assessment.compliant
            for assessment in self.assessments
        ):
            raise ValueError(
                "Gold trajectory compliant must aggregate its assessments"
            )
        return self


class WriteConfirmationGold(StrictModel):
    """Strict Human-Gold dataset for the write-confirmation rule."""

    gold_version: str = Field(min_length=1)
    annotation_type: Literal["human_adjudicated_gold"]
    domain: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    rule: GoldRule
    annotation_guidelines: dict[str, JsonValue]
    review: GoldReview
    source_trajectories: str = Field(min_length=1)
    labels: list[GoldLabel]

    @model_validator(mode="after")
    def validate_coverage(self) -> "WriteConfirmationGold":
        """Match review counts and reject duplicate trajectories."""
        trajectory_ids = [label.trajectory_id for label in self.labels]
        if len(set(trajectory_ids)) != len(trajectory_ids):
            raise ValueError("duplicate Gold trajectory_id")
        if self.review.trajectory_count != len(self.labels):
            raise ValueError(
                "Gold review trajectory_count does not match labels"
            )
        write_count = sum(
            len(label.assessments)
            for label in self.labels
        )
        if self.review.covered_write_count != write_count:
            raise ValueError(
                "Gold review covered_write_count does not match assessments"
            )
        return self


def load_gold(gold_path: Path) -> WriteConfirmationGold:
    """Load and strictly validate write-confirmation Human Gold."""
    return WriteConfirmationGold.model_validate_json(
        gold_path.read_text(encoding="utf-8")
    )


def _action_compliant(
    assessment: WriteConfirmationAssessment,
) -> bool | None:
    """Derive one predicted action verdict from its semantic fields."""
    if (
        assessment.details_sufficient is False
        or assessment.confirmation_valid is False
    ):
        return False
    if (
        assessment.details_sufficient is None
        or assessment.confirmation_valid is None
    ):
        return None
    return True


def _trajectory_compliant(
    judgment: WriteConfirmationJudgment,
) -> bool | None:
    """Aggregate predicted action verdicts using Process Verifier rules."""
    action_verdicts = [
        _action_compliant(assessment)
        for assessment in judgment.assessments
    ]
    if any(value is False for value in action_verdicts):
        return False
    if any(value is None for value in action_verdicts):
        return None
    return True


def _ratio(numerator: int, denominator: int) -> float | None:
    """Return a metric ratio without inventing zero-denominator values."""
    return numerator / denominator if denominator else None


def _classification_metrics(
    true_positive: int,
    true_negative: int,
    false_positive: int,
    false_negative: int,
    uncertain: int,
) -> dict[str, JsonValue]:
    """Build resolved binary metrics with explicit uncertain coverage."""
    determinate = (
        true_positive
        + true_negative
        + false_positive
        + false_negative
    )
    total = determinate + uncertain
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None
        and recall is not None
        and precision + recall
        else None
    )
    return {
        "total": total,
        "determinate_predictions": determinate,
        "uncertain_predictions": uncertain,
        "coverage": _ratio(determinate, total),
        "accuracy_on_determinate": _ratio(
            true_positive + true_negative,
            determinate,
        ),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": {
            "true_positive": true_positive,
            "true_negative": true_negative,
            "false_positive": false_positive,
            "false_negative": false_negative,
        },
    }


def evaluate_write_confirmation(
    judgments: WriteConfirmationJudgmentDataset,
    gold: WriteConfirmationGold,
) -> dict[str, JsonValue]:
    """Compare model semantics, action verdicts, and cited evidence to Gold."""
    if judgments.rule_id != RULE_ID or gold.rule.rule_id != RULE_ID:
        raise ValueError(f"inputs must target {RULE_ID}")

    gold_by_id = {label.trajectory_id: label for label in gold.labels}
    predicted_by_id = {
        judgment.trajectory_id: judgment
        for judgment in judgments.judgments
    }
    missing = set(gold_by_id) - set(predicted_by_id)
    unexpected = set(predicted_by_id) - set(gold_by_id)
    if missing or unexpected:
        raise ValueError(
            "write-confirmation judgment coverage must exactly match Gold; "
            f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )

    trajectory_counts = {
        "tp": 0,
        "tn": 0,
        "fp": 0,
        "fn": 0,
        "uncertain": 0,
    }
    action_counts = {
        "tp": 0,
        "tn": 0,
        "fp": 0,
        "fn": 0,
        "uncertain": 0,
    }
    field_counts = {
        "details_sufficient": {"correct": 0, "determinate": 0},
        "confirmation_valid": {"correct": 0, "determinate": 0},
    }
    evidence_counts = {
        "details_step_ids": 0,
        "confirmation_step_ids": 0,
    }
    exact_write_coverage = 0
    matched_action_count = 0
    predicted_write_count = 0
    cases: list[dict[str, JsonValue]] = []

    for gold_label in gold.labels:
        prediction = predicted_by_id[gold_label.trajectory_id]
        predicted_compliant = _trajectory_compliant(prediction)
        if predicted_compliant is None:
            trajectory_counts["uncertain"] += 1
            trajectory_correct: bool | None = None
        elif predicted_compliant is False and gold_label.compliant is False:
            trajectory_counts["tp"] += 1
            trajectory_correct = True
        elif predicted_compliant is True and gold_label.compliant is True:
            trajectory_counts["tn"] += 1
            trajectory_correct = True
        elif predicted_compliant is False:
            trajectory_counts["fp"] += 1
            trajectory_correct = False
        else:
            trajectory_counts["fn"] += 1
            trajectory_correct = False

        gold_by_step = {
            assessment.write_step_id: assessment
            for assessment in gold_label.assessments
        }
        predicted_assessments = {
            assessment.write_step_id: assessment
            for assessment in prediction.assessments
        }
        predicted_steps = list(predicted_assessments)
        predicted_write_count += len(predicted_steps)
        coverage_correct = predicted_steps == gold_label.covered_write_steps
        if coverage_correct:
            exact_write_coverage += 1

        action_cases: list[dict[str, JsonValue]] = []
        for write_step_id in sorted(
            set(gold_by_step) & set(predicted_assessments)
        ):
            matched_action_count += 1
            gold_assessment = gold_by_step[write_step_id]
            predicted_assessment = predicted_assessments[write_step_id]
            predicted_action_compliant = _action_compliant(
                predicted_assessment
            )
            if predicted_action_compliant is None:
                action_counts["uncertain"] += 1
                action_correct: bool | None = None
            elif (
                predicted_action_compliant is False
                and gold_assessment.compliant is False
            ):
                action_counts["tp"] += 1
                action_correct = True
            elif (
                predicted_action_compliant is True
                and gold_assessment.compliant is True
            ):
                action_counts["tn"] += 1
                action_correct = True
            elif predicted_action_compliant is False:
                action_counts["fp"] += 1
                action_correct = False
            else:
                action_counts["fn"] += 1
                action_correct = False

            field_matches: dict[str, bool | None] = {}
            for field_name in field_counts:
                predicted_value = getattr(predicted_assessment, field_name)
                gold_value = getattr(gold_assessment, field_name)
                if predicted_value is None:
                    field_matches[field_name] = None
                else:
                    field_counts[field_name]["determinate"] += 1
                    matched = predicted_value == gold_value
                    field_matches[field_name] = matched
                    if matched:
                        field_counts[field_name]["correct"] += 1

            details_evidence_match = set(
                predicted_assessment.details_step_ids
            ) == set(gold_assessment.details_step_ids)
            confirmation_evidence_match = set(
                predicted_assessment.confirmation_step_ids
            ) == set(gold_assessment.confirmation_step_ids)
            if details_evidence_match:
                evidence_counts["details_step_ids"] += 1
            if confirmation_evidence_match:
                evidence_counts["confirmation_step_ids"] += 1

            action_cases.append(
                {
                    "write_step_id": write_step_id,
                    "gold_compliant": gold_assessment.compliant,
                    "predicted_compliant": predicted_action_compliant,
                    "correct": action_correct,
                    "field_matches": field_matches,
                    "gold_details_step_ids": (
                        gold_assessment.details_step_ids
                    ),
                    "predicted_details_step_ids": (
                        predicted_assessment.details_step_ids
                    ),
                    "details_evidence_match": details_evidence_match,
                    "gold_confirmation_step_ids": (
                        gold_assessment.confirmation_step_ids
                    ),
                    "predicted_confirmation_step_ids": (
                        predicted_assessment.confirmation_step_ids
                    ),
                    "confirmation_evidence_match": (
                        confirmation_evidence_match
                    ),
                    "rationale": predicted_assessment.rationale,
                }
            )

        cases.append(
            {
                "trajectory_id": gold_label.trajectory_id,
                "task_id": gold_label.task_id,
                "gold_compliant": gold_label.compliant,
                "predicted_compliant": predicted_compliant,
                "correct": trajectory_correct,
                "gold_write_steps": gold_label.covered_write_steps,
                "predicted_write_steps": predicted_steps,
                "write_coverage_correct": coverage_correct,
                "missing_write_steps": sorted(
                    set(gold_by_step) - set(predicted_assessments)
                ),
                "unexpected_write_steps": sorted(
                    set(predicted_assessments) - set(gold_by_step)
                ),
                "assessments": action_cases,
                "rationale": prediction.rationale,
            }
        )

    trajectory_metrics = _classification_metrics(
        trajectory_counts["tp"],
        trajectory_counts["tn"],
        trajectory_counts["fp"],
        trajectory_counts["fn"],
        trajectory_counts["uncertain"],
    )
    action_metrics = _classification_metrics(
        action_counts["tp"],
        action_counts["tn"],
        action_counts["fp"],
        action_counts["fn"],
        action_counts["uncertain"],
    )
    semantic_field_metrics: dict[str, JsonValue] = {}
    for field_name, counts in field_counts.items():
        semantic_field_metrics[field_name] = {
            "matched_actions": matched_action_count,
            "determinate_predictions": counts["determinate"],
            "uncertain_predictions": (
                matched_action_count - counts["determinate"]
            ),
            "accuracy_on_determinate": _ratio(
                counts["correct"],
                counts["determinate"],
            ),
        }

    return {
        "evaluation_version": EVALUATION_VERSION,
        "rule_id": RULE_ID,
        "gold_version": gold.gold_version,
        "model_name": judgments.model_name,
        "semantic_version": judgments.semantic_version,
        "metrics": {
            "trajectory_compliance": trajectory_metrics,
            "write_coverage": {
                "gold_write_count": gold.review.covered_write_count,
                "predicted_write_count": predicted_write_count,
                "matched_write_count": matched_action_count,
                "trajectory_exact_matches": exact_write_coverage,
                "trajectory_total": len(gold.labels),
                "trajectory_exact_match_rate": _ratio(
                    exact_write_coverage,
                    len(gold.labels),
                ),
            },
            "write_action_compliance": action_metrics,
            "semantic_fields": semantic_field_metrics,
            "evidence_steps": {
                "matched_actions": matched_action_count,
                "details_exact_matches": evidence_counts[
                    "details_step_ids"
                ],
                "details_exact_match_rate": _ratio(
                    evidence_counts["details_step_ids"],
                    matched_action_count,
                ),
                "confirmation_exact_matches": evidence_counts[
                    "confirmation_step_ids"
                ],
                "confirmation_exact_match_rate": _ratio(
                    evidence_counts["confirmation_step_ids"],
                    matched_action_count,
                ),
            },
        },
        "cases": cases,
    }


def evaluate_file(
    judgment_path: Path,
    gold_path: Path,
    output_path: Path,
) -> dict[str, JsonValue]:
    """Evaluate saved judgments and write one JSON report."""
    judgments = WriteConfirmationJudgmentDataset.model_validate_json(
        judgment_path.read_text(encoding="utf-8")
    )
    report = evaluate_write_confirmation(judgments, load_gold(gold_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> None:
    """Compare write-confirmation judgments with completed Human Gold."""
    parser = argparse.ArgumentParser(
        description=(
            "Compare write-confirmation judgments with Human Gold. "
            "This command does not call a model."
        )
    )
    parser.add_argument("--judgments", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    report = evaluate_file(args.judgments, args.gold, args.output)
    metrics = report["metrics"]
    trajectory_metrics = metrics["trajectory_compliance"]
    write_metrics = metrics["write_action_compliance"]
    print(
        "Evaluated write confirmation against Human Gold: "
        f"trajectory_accuracy="
        f"{trajectory_metrics['accuracy_on_determinate']}, "
        f"write_action_accuracy="
        f"{write_metrics['accuracy_on_determinate']}: "
        f"{args.output}"
    )


if __name__ == "__main__":
    main()
