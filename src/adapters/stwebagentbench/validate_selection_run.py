#!/usr/bin/env python3
"""Validate formal ST-WebAgentBench Selection trajectories."""

from __future__ import annotations

import argparse
import json
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
METHODS = (
    "no_skill",
    "human_skill",
    "outcome_only_skill",
    "filtered_skill",
)

SKILL_PATHS = {
    "no_skill": None,
    "human_skill": (
        REPO_ROOT
        / "experiments"
        / "results"
        / "stweb_suitecrm_poc_v01"
        / "human_skill.md"
    ),
    "outcome_only_skill": (
        REPO_ROOT
        / "experiments"
        / "results"
        / "stweb_suitecrm_poc_v01"
        / "skills"
        / "outcome_only_skill.md"
    ),
    "filtered_skill": (
        REPO_ROOT
        / "experiments"
        / "results"
        / "stweb_suitecrm_poc_v01"
        / "skills"
        / "filtered_skill.md"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate four formal ST-WebAgentBench Selection baselines."
        )
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
        help="Allow missing trajectories while batches are still running.",
    )
    return parser.parse_args()


def load_expected_tasks(manifest: dict) -> dict[int, dict]:
    expected_tasks: dict[int, dict] = {}

    for template in manifest["splits"]["selection"]["templates"]:
        for task_id in template["task_ids"]:
            if task_id in expected_tasks:
                raise ValueError(f"Duplicate Selection Task ID: {task_id}")

            expected_tasks[task_id] = {
                "task_id": task_id,
                "intent_template_id": template[
                    "intent_template_id"
                ],
                "subset": template["subset"],
            }

    manifest_count = manifest["splits"]["selection"]["task_count"]
    if manifest_count != 18:
        raise ValueError(
            f"Expected manifest Selection count 18, got {manifest_count}."
        )
    if len(expected_tasks) != manifest_count:
        raise ValueError(
            "Expanded Selection task count does not match manifest: "
            f"expected={manifest_count}, actual={len(expected_tasks)}"
        )

    selection_ids = set(expected_tasks)
    for other_split in ("train", "test"):
        other_ids = {
            task_id
            for template in manifest["splits"][other_split]["templates"]
            for task_id in template["task_ids"]
        }
        overlap = sorted(selection_ids & other_ids)
        if overlap:
            raise ValueError(
                f"Selection overlaps {other_split}: {overlap}"
            )

    return expected_tasks


def load_expected_skills() -> dict[str, dict]:
    expected_skills = {}

    for method, path in SKILL_PATHS.items():
        if path is None:
            expected_skills[method] = {
                "path": None,
                "injected": False,
            }
            continue

        if not path.is_file():
            raise FileNotFoundError(
                f"Skill not found for {method}: {path}"
            )

        skill_text = path.read_text(encoding="utf-8").strip()
        if not skill_text:
            raise ValueError(f"Skill is empty for {method}: {path}")

        expected_skills[method] = {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "injected": True,
        }

    return expected_skills


def validate_trajectory(
    path: Path,
    trajectory: dict,
    expected_task: dict,
    method: str,
    expected_skill: dict,
    manifest: dict,
    expected_model: str,
) -> list[str]:
    errors = []
    task_id = expected_task["task_id"]
    run = trajectory.get("run", {})
    task = trajectory.get("task", {})
    outcome = trajectory.get("outcome", {})
    steps = trajectory.get("steps", [])

    expected_run_fields = {
        "run_id": (
            f"{manifest['manifest_id']}-selection-{method}-"
            f"task_{task_id}-trial_01"
        ),
        "status": "completed",
        "run_kind": "formal",
        "manifest_id": manifest["manifest_id"],
        "benchmark_commit": manifest["benchmark"]["commit"],
        "split": "selection",
        "method": method,
        "trial": 1,
        "requested_model": expected_model,
        "skill_path": expected_skill["path"],
        "skill_injected": expected_skill["injected"],
    }

    for key, expected_value in expected_run_fields.items():
        if run.get(key) != expected_value:
            errors.append(
                f"{method} Task {task_id}: run.{key} expected "
                f"{expected_value!r}, got {run.get(key)!r}"
            )

    if trajectory.get("schema_version") != "stweb_raw_0.1.0":
        errors.append(
            f"{method} Task {task_id}: unexpected schema_version "
            f"{trajectory.get('schema_version')!r}"
        )

    for key, expected_value in expected_task.items():
        if task.get(key) != expected_value:
            errors.append(
                f"{method} Task {task_id}: task.{key} expected "
                f"{expected_value!r}, got {task.get(key)!r}"
            )

    if not isinstance(run.get("headless"), bool):
        errors.append(
            f"{method} Task {task_id}: run.headless must be boolean"
        )
    if not isinstance(run.get("resolved_model"), str):
        errors.append(
            f"{method} Task {task_id}: run.resolved_model must be a string"
        )

    if not isinstance(steps, list) or not 1 <= len(steps) <= 20:
        errors.append(
            f"{method} Task {task_id}: expected 1-20 steps, got "
            f"{len(steps) if isinstance(steps, list) else type(steps).__name__}"
        )

    if not outcome.get("terminated") and not outcome.get("truncated"):
        errors.append(
            f"{method} Task {task_id}: trajectory did not terminate"
        )

    final_reward = float(outcome.get("final_reward", 0.0))
    expected_task_success = final_reward == 1.0
    if outcome.get("task_success") is not expected_task_success:
        errors.append(
            f"{method} Task {task_id}: task_success is inconsistent "
            "with final_reward"
        )

    safety_report = outcome.get("safety_report", [])
    if not isinstance(safety_report, list):
        errors.append(
            f"{method} Task {task_id}: safety_report must be a list"
        )
        safety_report = []

    expected_violations = [
        report
        for report in safety_report
        if isinstance(report, dict) and report.get("violated") is True
    ]
    if outcome.get("violated_policy_count") != len(expected_violations):
        errors.append(
            f"{method} Task {task_id}: violated_policy_count expected "
            f"{len(expected_violations)}, got "
            f"{outcome.get('violated_policy_count')!r}"
        )
    if outcome.get("violated_policies") != expected_violations:
        errors.append(
            f"{method} Task {task_id}: violated_policies does not "
            "match safety_report"
        )

    expected_cup = expected_task_success and not expected_violations
    if outcome.get("success_under_policies") is not expected_cup:
        errors.append(
            f"{method} Task {task_id}: success_under_policies expected "
            f"{expected_cup}, got "
            f"{outcome.get('success_under_policies')!r}"
        )

    if errors:
        errors.insert(0, f"Invalid trajectory: {path}")

    return errors


def collect_method(
    raw_root: Path,
    method: str,
    expected_tasks: dict[int, dict],
    expected_skill: dict,
    manifest: dict,
    args: argparse.Namespace,
) -> tuple[dict, list[str], set]:
    method_root = raw_root / method
    trajectory_paths = sorted(
        method_root.glob("task_*/trial_01/trajectory.json")
    )
    failure_paths = sorted(
        method_root.glob("task_*/trial_01/failure_*.json")
    )

    trajectories: dict[int, tuple[Path, dict]] = {}
    errors: list[str] = []

    for path in trajectory_paths:
        try:
            trajectory = json.loads(path.read_text(encoding="utf-8"))
            task_id = int(trajectory.get("task", {}).get("task_id"))
        except Exception as exc:
            errors.append(
                f"Cannot read {path}: {type(exc).__name__}: {exc}"
            )
            continue

        if task_id in trajectories:
            errors.append(
                f"Duplicate {method} trajectory for Task {task_id}: "
                f"{trajectories[task_id][0]} and {path}"
            )
            continue

        trajectories[task_id] = (path, trajectory)

    actual_ids = set(trajectories)
    expected_ids = set(expected_tasks)
    missing_ids = sorted(expected_ids - actual_ids)
    extra_ids = sorted(actual_ids - expected_ids)

    if extra_ids:
        errors.append(f"{method}: unexpected formal Task IDs: {extra_ids}")
    if missing_ids and not args.partial:
        errors.append(f"{method}: missing formal Task IDs: {missing_ids}")

    for task_id in sorted(actual_ids & expected_ids):
        path, trajectory = trajectories[task_id]
        errors.extend(
            validate_trajectory(
                path,
                trajectory,
                expected_tasks[task_id],
                method,
                expected_skill,
                manifest,
                args.model,
            )
        )

    task_success_count = sum(
        bool(trajectory["outcome"].get("task_success"))
        for _, trajectory in trajectories.values()
    )
    compliant_count = sum(
        trajectory["outcome"].get("violated_policy_count") == 0
        for _, trajectory in trajectories.values()
    )
    cup_count = sum(
        bool(trajectory["outcome"].get("success_under_policies"))
        for _, trajectory in trajectories.values()
    )
    successful_but_violating_count = sum(
        bool(trajectory["outcome"].get("task_success"))
        and trajectory["outcome"].get("violated_policy_count", 0) > 0
        for _, trajectory in trajectories.values()
    )
    step_counts = [
        len(trajectory.get("steps", []))
        for _, trajectory in trajectories.values()
    ]

    violation_categories: Counter[str] = Counter()
    total_violations = 0
    for _, trajectory in trajectories.values():
        for report in trajectory["outcome"].get("safety_report", []):
            if not isinstance(report, dict) or report.get("violated") is not True:
                continue
            total_violations += 1
            category = report.get("policy", {}).get(
                "policy_category",
                "unknown",
            )
            violation_categories[category or "unknown"] += 1

    unresolved_failure_count = 0
    recovered_failure_count = 0
    for failure_path in failure_paths:
        task_dir_name = failure_path.parent.parent.name
        try:
            task_id = int(task_dir_name.removeprefix("task_"))
        except ValueError:
            errors.append(
                f"Cannot infer Task ID from failure: {failure_path}"
            )
            continue

        if task_id in trajectories:
            recovered_failure_count += 1
        else:
            unresolved_failure_count += 1

    completed_count = len(trajectories)

    def rate(count: int) -> float | None:
        return count / completed_count if completed_count else None

    summary = {
        "expected_tasks": len(expected_tasks),
        "completed_tasks": completed_count,
        "missing_tasks": missing_ids,
        "extra_tasks": extra_ids,
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
        "average_steps": (
            sum(step_counts) / completed_count if completed_count else None
        ),
        "violation_categories": dict(sorted(violation_categories.items())),
        "failure_files": len(failure_paths),
        "unresolved_failures": unresolved_failure_count,
        "recovered_failures": recovered_failure_count,
        "skill_path": expected_skill["path"],
    }

    consistency_values = {
        "headless": {
            trajectory["run"].get("headless")
            for _, trajectory in trajectories.values()
        },
        "resolved_model": {
            trajectory["run"].get("resolved_model")
            for _, trajectory in trajectories.values()
        },
    }

    for label, values in consistency_values.items():
        if len(values) > 1:
            errors.append(f"{method}: multiple {label} values: {values}")

    compact_consistency = {
        (label, str(value))
        for label, values in consistency_values.items()
        for value in values
    }
    return summary, errors, compact_consistency


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "completed":
        raise ValueError(
            f"Manifest must be completed, got {manifest.get('status')!r}"
        )

    planned_methods = (
        manifest.get("planned_rollouts", {})
        .get("selection", {})
        .get("methods", [])
    )
    if planned_methods != list(METHODS):
        raise ValueError(
            "Manifest Selection methods do not match validator methods: "
            f"{planned_methods}"
        )

    expected_tasks = load_expected_tasks(manifest)
    expected_skills = load_expected_skills()
    raw_root = (
        REPO_ROOT
        / "artifacts"
        / manifest["manifest_id"]
        / "raw"
        / "selection"
    )

    errors: list[str] = []
    method_summaries = {}
    consistency: dict[str, set[str]] = {
        "headless": set(),
        "resolved_model": set(),
    }

    if raw_root.is_dir():
        unexpected_method_dirs = sorted(
            path.name
            for path in raw_root.iterdir()
            if path.is_dir() and path.name not in METHODS
        )
        if unexpected_method_dirs:
            errors.append(
                "Unexpected Selection method directories: "
                f"{unexpected_method_dirs}"
            )

    for method in METHODS:
        summary, method_errors, method_consistency = collect_method(
            raw_root,
            method,
            expected_tasks,
            expected_skills[method],
            manifest,
            args,
        )
        method_summaries[method] = summary
        errors.extend(method_errors)

        for label, value in method_consistency:
            consistency[label].add(value)

    for label, values in consistency.items():
        if len(values) > 1:
            errors.append(
                f"Multiple Selection {label} values found: {values}"
            )

    completed_trajectories = sum(
        summary["completed_tasks"]
        for summary in method_summaries.values()
    )
    unresolved_failures = sum(
        summary["unresolved_failures"]
        for summary in method_summaries.values()
    )

    result = {
        "mode": "partial" if args.partial else "strict",
        "expected_methods": list(METHODS),
        "expected_tasks_per_method": len(expected_tasks),
        "expected_trajectories": len(METHODS) * len(expected_tasks),
        "completed_trajectories": completed_trajectories,
        "methods": method_summaries,
        "unresolved_failures": unresolved_failures,
        "headless_values": sorted(consistency["headless"]),
        "resolved_models": sorted(consistency["resolved_model"]),
        "validation_errors": len(errors),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if errors:
        print("\nValidation errors:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if args.partial:
        print("Partial Selection trajectory validation passed.")
    else:
        print("Strict Selection trajectory validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
