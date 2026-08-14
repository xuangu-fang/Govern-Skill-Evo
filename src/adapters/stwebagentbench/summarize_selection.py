#!/usr/bin/env python3
"""Summarize validated ST-WebAgentBench Selection trajectories."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = (
    REPO_ROOT
    / "experiments"
    / "manifests"
    / "stweb_suitecrm_poc_v01.json"
)
VALIDATOR = Path(__file__).with_name("validate_selection_run.py")
OUTPUT_ROOT = (
    REPO_ROOT
    / "experiments"
    / "results"
    / "stweb_suitecrm_poc_v01"
    / "selection"
)

METHODS = (
    "no_skill",
    "human_skill",
    "outcome_only_skill",
    "filtered_skill",
)


def save_json_atomic(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")

    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    os.replace(temporary_path, path)


def save_csv_atomic(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")

    with temporary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    os.replace(temporary_path, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize four validated Selection baselines."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Expected requested model ID.",
    )
    parser.add_argument(
        "--partial",
        action="store_true",
        help="Preview completed trajectories without writing artifacts.",
    )
    return parser.parse_args()


def run_validation(
    manifest_path: Path,
    model: str,
    partial: bool,
) -> None:
    command = [
        sys.executable,
        str(VALIDATOR),
        "--manifest",
        str(manifest_path),
        "--model",
        model,
    ]
    if partial:
        command.append("--partial")

    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr, end="")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        raise RuntimeError("Selection trajectory validation failed.")


def load_expected_tasks(manifest: dict) -> dict[int, dict]:
    tasks = {}

    for template in manifest["splits"]["selection"]["templates"]:
        for task_id in template["task_ids"]:
            tasks[task_id] = {
                "task_id": task_id,
                "intent_template_id": template[
                    "intent_template_id"
                ],
                "subset": template["subset"],
            }

    if len(tasks) != 18:
        raise ValueError(f"Expected 18 Selection tasks, got {len(tasks)}")

    return tasks


def violation_categories(trajectory: dict) -> dict[str, int]:
    categories: Counter[str] = Counter()

    for report in trajectory["outcome"].get("safety_report", []):
        if not isinstance(report, dict) or report.get("violated") is not True:
            continue
        category = report.get("policy", {}).get(
            "policy_category",
            "unknown",
        )
        categories[category or "unknown"] += 1

    return dict(sorted(categories.items()))


def load_task_rows(
    manifest: dict,
    expected_tasks: dict[int, dict],
) -> list[dict]:
    raw_root = (
        REPO_ROOT
        / "artifacts"
        / manifest["manifest_id"]
        / "raw"
        / "selection"
    )
    rows = []

    for method in METHODS:
        for task_id, expected_task in expected_tasks.items():
            path = (
                raw_root
                / method
                / f"task_{task_id}"
                / "trial_01"
                / "trajectory.json"
            )
            if not path.is_file():
                continue

            trajectory = json.loads(path.read_text(encoding="utf-8"))
            outcome = trajectory["outcome"]
            violation_count = outcome["violated_policy_count"]
            task_success = outcome["task_success"] is True
            compliant = violation_count == 0
            cup = task_success and compliant

            rows.append(
                {
                    **expected_task,
                    "method": method,
                    "task_success": task_success,
                    "compliant": compliant,
                    "cup": cup,
                    "successful_but_violating": (
                        task_success and not compliant
                    ),
                    "violated_policy_count": violation_count,
                    "violation_categories": violation_categories(
                        trajectory
                    ),
                    "steps": len(trajectory["steps"]),
                    "trajectory_path": path.relative_to(
                        REPO_ROOT
                    ).as_posix(),
                    "skill_path": trajectory["run"].get("skill_path"),
                }
            )

    return rows


def summarize_rows(rows: list[dict]) -> dict:
    count = len(rows)
    task_success_count = sum(row["task_success"] for row in rows)
    compliant_count = sum(row["compliant"] for row in rows)
    cup_count = sum(row["cup"] for row in rows)
    successful_but_violating_count = sum(
        row["successful_but_violating"] for row in rows
    )
    total_violations = sum(
        row["violated_policy_count"] for row in rows
    )
    category_counts: Counter[str] = Counter()

    for row in rows:
        category_counts.update(row["violation_categories"])

    def rate(value: int) -> float | None:
        return value / count if count else None

    return {
        "tasks": count,
        "task_success_count": task_success_count,
        "task_success_rate": rate(task_success_count),
        "compliant_count": compliant_count,
        "compliance_rate": rate(compliant_count),
        "cup_count": cup_count,
        "cup_rate": rate(cup_count),
        "successful_but_violating_count": (
            successful_but_violating_count
        ),
        "total_violations": total_violations,
        "average_violations": (
            total_violations / count if count else None
        ),
        "average_steps": (
            sum(row["steps"] for row in rows) / count if count else None
        ),
        "violation_categories": dict(sorted(category_counts.items())),
    }


def summarize_method(rows: list[dict]) -> dict:
    overall = summarize_rows(rows)
    subsets = {
        subset: summarize_rows(
            [row for row in rows if row["subset"] == subset]
        )
        for subset in ("general", "difficulty")
    }
    template_ids = sorted({row["intent_template_id"] for row in rows})
    templates = {
        str(template_id): summarize_rows(
            [
                row
                for row in rows
                if row["intent_template_id"] == template_id
            ]
        )
        for template_id in template_ids
    }

    template_values = list(templates.values())

    def macro(metric: str) -> float | None:
        values = [
            template[metric]
            for template in template_values
            if template[metric] is not None
        ]
        return sum(values) / len(values) if values else None

    return {
        "overall": overall,
        "by_subset": subsets,
        "by_template": templates,
        "template_macro": {
            "templates": len(template_values),
            "task_success_rate": macro("task_success_rate"),
            "compliance_rate": macro("compliance_rate"),
            "cup_rate": macro("cup_rate"),
        },
    }


def compare_methods(
    rows: list[dict],
    candidate: str,
    reference: str,
) -> dict:
    candidate_rows = {
        row["task_id"]: row
        for row in rows
        if row["method"] == candidate
    }
    reference_rows = {
        row["task_id"]: row
        for row in rows
        if row["method"] == reference
    }
    common_ids = sorted(set(candidate_rows) & set(reference_rows))

    if not common_ids:
        return {
            "candidate": candidate,
            "reference": reference,
            "paired_tasks": 0,
        }

    def count_gain(metric: str) -> int:
        return sum(
            bool(candidate_rows[task_id][metric])
            and not bool(reference_rows[task_id][metric])
            for task_id in common_ids
        )

    def count_loss(metric: str) -> int:
        return sum(
            not bool(candidate_rows[task_id][metric])
            and bool(reference_rows[task_id][metric])
            for task_id in common_ids
        )

    def rate_delta(metric: str) -> float:
        return sum(
            int(bool(candidate_rows[task_id][metric]))
            - int(bool(reference_rows[task_id][metric]))
            for task_id in common_ids
        ) / len(common_ids)

    return {
        "candidate": candidate,
        "reference": reference,
        "paired_tasks": len(common_ids),
        "task_success": {
            "gains": count_gain("task_success"),
            "losses": count_loss("task_success"),
            "rate_delta": rate_delta("task_success"),
        },
        "compliance": {
            "gains": count_gain("compliant"),
            "losses": count_loss("compliant"),
            "rate_delta": rate_delta("compliant"),
        },
        "cup": {
            "gains": count_gain("cup"),
            "losses": count_loss("cup"),
            "rate_delta": rate_delta("cup"),
        },
        "total_violation_delta": sum(
            candidate_rows[task_id]["violated_policy_count"]
            - reference_rows[task_id]["violated_policy_count"]
            for task_id in common_ids
        ),
    }


def method_csv_rows(method_summaries: dict) -> list[dict]:
    rows = []

    for method in METHODS:
        summary = method_summaries[method]
        overall = summary["overall"]
        macro = summary["template_macro"]
        rows.append(
            {
                "method": method,
                "tasks": overall["tasks"],
                "task_success_count": overall["task_success_count"],
                "task_success_rate": overall["task_success_rate"],
                "compliant_count": overall["compliant_count"],
                "compliance_rate": overall["compliance_rate"],
                "cup_count": overall["cup_count"],
                "cup_rate": overall["cup_rate"],
                "successful_but_violating_count": overall[
                    "successful_but_violating_count"
                ],
                "total_violations": overall["total_violations"],
                "average_steps": overall["average_steps"],
                "template_macro_task_success_rate": macro[
                    "task_success_rate"
                ],
                "template_macro_compliance_rate": macro[
                    "compliance_rate"
                ],
                "template_macro_cup_rate": macro["cup_rate"],
            }
        )

    return rows


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    if not VALIDATOR.is_file():
        raise FileNotFoundError(f"Validator not found: {VALIDATOR}")
    run_validation(manifest_path, args.model, args.partial)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_tasks = load_expected_tasks(manifest)
    task_rows = load_task_rows(manifest, expected_tasks)
    method_summaries = {
        method: summarize_method(
            [row for row in task_rows if row["method"] == method]
        )
        for method in METHODS
    }
    comparisons = [
        compare_methods(task_rows, "human_skill", "no_skill"),
        compare_methods(task_rows, "outcome_only_skill", "no_skill"),
        compare_methods(task_rows, "filtered_skill", "no_skill"),
        compare_methods(
            task_rows,
            "filtered_skill",
            "outcome_only_skill",
        ),
    ]

    report = {
        "schema_version": "stweb_selection_summary_0.1.0",
        "mode": "partial" if args.partial else "strict",
        "source": {
            "manifest_id": manifest["manifest_id"],
            "requested_model": args.model,
            "expected_trajectories": 72,
            "completed_trajectories": len(task_rows),
            "primary_evaluation_unit": manifest["research_scope"][
                "primary_evaluation_unit"
            ],
        },
        "methods": method_summaries,
        "comparisons": comparisons,
    }

    console_summary = {
        "mode": report["mode"],
        "completed_trajectories": len(task_rows),
        "methods": {
            method: method_summaries[method]["overall"]
            for method in METHODS
        },
        "comparisons": comparisons,
    }
    print(json.dumps(console_summary, ensure_ascii=False, indent=2))

    if args.partial:
        print("Partial Selection summary completed; no files were written.")
        return 0

    summary_path = OUTPUT_ROOT / "summary.json"
    task_results_path = OUTPUT_ROOT / "task_results.json"
    csv_path = OUTPUT_ROOT / "method_summary.csv"
    csv_rows = method_csv_rows(method_summaries)
    csv_fields = list(csv_rows[0])

    save_json_atomic(summary_path, report)
    save_json_atomic(
        task_results_path,
        {
            "schema_version": "stweb_selection_task_results_0.1.0",
            "source": report["source"],
            "tasks": task_rows,
        },
    )
    save_csv_atomic(csv_path, csv_rows, csv_fields)

    print(f"Selection summary saved: {summary_path}")
    print(f"Selection task results saved: {task_results_path}")
    print(f"Selection method CSV saved: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
