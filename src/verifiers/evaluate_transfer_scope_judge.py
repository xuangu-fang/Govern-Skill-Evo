"""Evaluate transfer-scope semantic judgments against human Gold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.verifiers.transfer_scope_verifier import (
    RULE_ID,
    TransferScopeJudgmentDataset,
)


EVALUATION_VERSION = "0.2.0"


def load_gold(gold_path: Path) -> dict[str, Any]:
    """Load and validate the minimal human-Gold contract used here."""
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    if not isinstance(gold, dict):
        raise ValueError("Gold file must contain one JSON object")

    rule = gold.get("rule")
    if not isinstance(rule, dict) or rule.get("rule_id") != RULE_ID:
        raise ValueError(f"Gold file must target {RULE_ID}")
    if (gold.get("review") or {}).get("status") != "complete":
        raise ValueError("Gold review must have status=complete")
    if not isinstance(gold.get("labels"), list):
        raise ValueError("Gold file must contain a labels list")
    return gold


def evaluate_judge(
    judgments: TransferScopeJudgmentDataset,
    gold: dict[str, Any],
) -> dict[str, Any]:
    """Compare only semantic should_transfer predictions with human Gold."""
    if judgments.rule_id != RULE_ID:
        raise ValueError(f"judgments must target {RULE_ID}")

    gold_by_id: dict[str, dict[str, Any]] = {}
    for label in gold.get("labels", []):
        if not isinstance(label, dict):
            raise ValueError("each Gold label must be an object")
        trajectory_id = label.get("trajectory_id")
        should_transfer = label.get("should_transfer")
        if not isinstance(trajectory_id, str) or not trajectory_id:
            raise ValueError("each Gold label needs a trajectory_id")
        if trajectory_id in gold_by_id:
            raise ValueError(f"duplicate Gold trajectory_id: {trajectory_id}")
        if not isinstance(should_transfer, bool):
            raise ValueError(
                "Gold should_transfer must be a resolved boolean: "
                f"{trajectory_id}"
            )
        if label.get("rule_id") != RULE_ID:
            raise ValueError(
                f"Gold label {trajectory_id} must target {RULE_ID}"
            )
        gold_by_id[trajectory_id] = label

    predicted_by_id = {
        item.trajectory_id: item
        for item in judgments.judgments
    }
    missing = set(gold_by_id) - set(predicted_by_id)
    unexpected = set(predicted_by_id) - set(gold_by_id)
    if missing or unexpected:
        raise ValueError(
            "judge coverage must exactly match Gold; "
            f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )

    true_positive = true_negative = false_positive = false_negative = 0
    uncertain = 0
    cases: list[dict[str, Any]] = []

    for trajectory_id, gold_label in gold_by_id.items():
        prediction = predicted_by_id[trajectory_id]
        gold_value = gold_label["should_transfer"]
        predicted_value = prediction.should_transfer

        if predicted_value is None:
            uncertain += 1
            correct: bool | None = None
        else:
            correct = predicted_value == gold_value
            if predicted_value and gold_value:
                true_positive += 1
            elif not predicted_value and not gold_value:
                true_negative += 1
            elif predicted_value:
                false_positive += 1
            else:
                false_negative += 1

        cases.append(
            {
                "trajectory_id": trajectory_id,
                "task_id": gold_label.get("task_id"),
                "gold_should_transfer": gold_value,
                "predicted_should_transfer": predicted_value,
                "correct": correct,
                "decision_step_id": prediction.decision_step_id,
                "evidence_step_ids": prediction.evidence_step_ids,
                "rationale": prediction.rationale,
            }
        )

    total = len(cases)
    determinate = total - uncertain
    correct_count = true_positive + true_negative
    metrics = {
        "total": total,
        "determinate_predictions": determinate,
        "uncertain_predictions": uncertain,
        "coverage": determinate / total if total else None,
        "accuracy_on_determinate": (
            correct_count / determinate if determinate else None
        ),
        "confusion_matrix": {
            "true_positive": true_positive,
            "true_negative": true_negative,
            "false_positive": false_positive,
            "false_negative": false_negative,
        },
    }

    return {
        "evaluation_version": EVALUATION_VERSION,
        "rule_id": RULE_ID,
        "gold_version": gold.get("gold_version"),
        "judge_name": judgments.judge_name,
        "judge_version": judgments.judge_version,
        "metrics": metrics,
        "cases": cases,
    }


def evaluate_file(
    judgment_path: Path,
    gold_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Evaluate serialized judgments and write a JSON report."""
    judgments = TransferScopeJudgmentDataset.model_validate_json(
        judgment_path.read_text(encoding="utf-8")
    )
    report = evaluate_judge(judgments, load_gold(gold_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> None:
    """Evaluate a completed judge run against human Gold."""
    parser = argparse.ArgumentParser(
        description=(
            "Compare transfer-scope Judge predictions with human Gold. "
            "This command does not call a model or run the transfer-scope "
            "verifier."
        )
    )
    parser.add_argument("--judgments", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    report = evaluate_file(args.judgments, args.gold, args.output)
    metrics = report["metrics"]
    print(
        "Evaluated "
        f"{metrics['total']} predictions; "
        f"coverage={metrics['coverage']}, "
        f"accuracy_on_determinate={metrics['accuracy_on_determinate']}: "
        f"{args.output}"
    )


if __name__ == "__main__":
    main()
