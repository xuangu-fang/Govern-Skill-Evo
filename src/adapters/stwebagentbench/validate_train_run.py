#!/usr/bin/env python3
"""Validate formal ST-WebAgentBench Train trajectories."""

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
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate formal no_skill Train trajectories."
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
        help="Allow missing trajectories while a batch is still running.",
    )
    return parser.parse_args()


def load_expected_tasks(manifest: dict) -> dict[int, dict]:
    expected_tasks: dict[int, dict] = {}

    for template in manifest["splits"]["train"]["templates"]:
        for task_id in template["task_ids"]:
            if task_id in expected_tasks:
                raise ValueError(f"Duplicate Train Task ID: {task_id}")

            expected_tasks[task_id] = {
                "task_id": task_id,
                "intent_template_id": template["intent_template_id"],
                "subset": template["subset"],
            }

    manifest_count = manifest["splits"]["train"]["task_count"]

    if manifest_count != 51:
        raise ValueError(
            f"Expected manifest Train count 51, got {manifest_count}."
        )

    if len(expected_tasks) != manifest_count:
        raise ValueError(
            "Expanded Train task count does not match manifest: "
            f"expected={manifest_count}, actual={len(expected_tasks)}"
        )

    return expected_tasks


def validate_trajectory(
    path: Path,
    trajectory: dict,
    expected_task: dict,
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
        "status": "completed",
        "run_kind": "formal",
        "manifest_id": manifest["manifest_id"],
        "benchmark_commit": manifest["benchmark"]["commit"],
        "split": "train",
        "method": "no_skill",
        "trial": 1,
        "requested_model": expected_model,
    }

    for key, expected_value in expected_run_fields.items():
        if run.get(key) != expected_value:
            errors.append(
                f"Task {task_id}: run.{key} expected "
                f"{expected_value!r}, got {run.get(key)!r}"
            )

    if trajectory.get("schema_version") != "stweb_raw_0.1.0":
        errors.append(
            f"Task {task_id}: unexpected schema_version "
            f"{trajectory.get('schema_version')!r}"
        )

    for key, expected_value in expected_task.items():
        if task.get(key) != expected_value:
            errors.append(
                f"Task {task_id}: task.{key} expected "
                f"{expected_value!r}, got {task.get(key)!r}"
            )

    if not isinstance(run.get("headless"), bool):
        errors.append(f"Task {task_id}: run.headless must be boolean")

    if not isinstance(steps, list) or not 1 <= len(steps) <= 20:
        errors.append(
            f"Task {task_id}: expected 1-20 steps, got "
            f"{len(steps) if isinstance(steps, list) else type(steps).__name__}"
        )

    if not outcome.get("terminated") and not outcome.get("truncated"):
        errors.append(f"Task {task_id}: trajectory did not terminate")

    final_reward = float(outcome.get("final_reward", 0.0))
    expected_task_success = final_reward == 1.0

    if outcome.get("task_success") is not expected_task_success:
        errors.append(
            f"Task {task_id}: task_success is inconsistent with final_reward"
        )

    safety_report = outcome.get("safety_report", [])
    if not isinstance(safety_report, list):
        errors.append(f"Task {task_id}: safety_report must be a list")
        safety_report = []

    expected_violations = [
        report
        for report in safety_report
        if isinstance(report, dict) and report.get("violated") is True
    ]

    if outcome.get("violated_policy_count") != len(expected_violations):
        errors.append(
            f"Task {task_id}: violated_policy_count expected "
            f"{len(expected_violations)}, got "
            f"{outcome.get('violated_policy_count')!r}"
        )

    if outcome.get("violated_policies") != expected_violations:
        errors.append(
            f"Task {task_id}: violated_policies does not match safety_report"
        )

    expected_cup = expected_task_success and not expected_violations
    if outcome.get("success_under_policies") is not expected_cup:
        errors.append(
            f"Task {task_id}: success_under_policies expected "
            f"{expected_cup}, got "
            f"{outcome.get('success_under_policies')!r}"
        )

    if errors:
        errors.insert(0, f"Invalid trajectory: {path}")

    return errors


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

    expected_tasks = load_expected_tasks(manifest)

    raw_root = (
        REPO_ROOT
        / "artifacts"
        / manifest["manifest_id"]
        / "raw"
        / "train"
        / "no_skill"
    )

    trajectory_paths = sorted(
        raw_root.glob("task_*/trial_01/trajectory.json")
    )
    failure_paths = sorted(raw_root.glob("task_*/trial_01/failure_*.json"))

    trajectories: dict[int, tuple[Path, dict]] = {}
    errors: list[str] = []

    for path in trajectory_paths:
        try:
            trajectory = json.loads(path.read_text(encoding="utf-8"))
            task_id = int(trajectory.get("task", {}).get("task_id"))
        except Exception as exc:
            errors.append(f"Cannot read {path}: {type(exc).__name__}: {exc}")
            continue

        if task_id in trajectories:
            errors.append(
                f"Duplicate trajectory for Task {task_id}: "
                f"{trajectories[task_id][0]} and {path}"
            )
            continue

        trajectories[task_id] = (path, trajectory)

    actual_ids = set(trajectories)
    expected_ids = set(expected_tasks)
    missing_ids = sorted(expected_ids - actual_ids)
    extra_ids = sorted(actual_ids - expected_ids)

    if extra_ids:
        errors.append(f"Unexpected formal Task IDs: {extra_ids}")

    if missing_ids and not args.partial:
        errors.append(f"Missing formal Task IDs: {missing_ids}")

    for task_id in sorted(actual_ids & expected_ids):
        path, trajectory = trajectories[task_id]
        errors.extend(
            validate_trajectory(
                path,
                trajectory,
                expected_tasks[task_id],
                manifest,
                args.model,
            )
        )

    headless_values = {
        trajectory["run"].get("headless")
        for _, trajectory in trajectories.values()
    }
    resolved_models = {
        trajectory["run"].get("resolved_model")
        for _, trajectory in trajectories.values()
    }
    if len(headless_values) > 1:
        errors.append(f"Multiple headless settings found: {headless_values}")
    if len(resolved_models) > 1:
        errors.append(f"Multiple resolved models found: {resolved_models}")
    task_success_count = sum(
        bool(trajectory["outcome"].get("task_success"))
        for _, trajectory in trajectories.values()
    )
    cup_count = sum(
        bool(trajectory["outcome"].get("success_under_policies"))
        for _, trajectory in trajectories.values()
    )
    step_counts = [
        len(trajectory.get("steps", []))
        for _, trajectory in trajectories.values()
    ]

    violation_categories: Counter[str] = Counter()
    for _, trajectory in trajectories.values():
        for report in trajectory["outcome"].get("safety_report", []):
            if not isinstance(report, dict) or report.get("violated") is not True:
                continue
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
            errors.append(f"Cannot infer Task ID from failure: {failure_path}")
            continue

        if task_id in trajectories:
            recovered_failure_count += 1
        else:
            unresolved_failure_count += 1

    completed_count = len(trajectories)
    summary = {
        "mode": "partial" if args.partial else "strict",
        "expected_tasks": len(expected_tasks),
        "completed_tasks": completed_count,
        "missing_tasks": missing_ids,
        "extra_tasks": extra_ids,
        "task_success_count": task_success_count,
        "task_success_rate": (
            task_success_count / completed_count if completed_count else None
        ),
        "cup_count": cup_count,
        "cup_rate": cup_count / completed_count if completed_count else None,
        "average_steps": (
            sum(step_counts) / completed_count if completed_count else None
        ),
        "violation_categories": dict(sorted(violation_categories.items())),
        "failure_files": len(failure_paths),
        "unresolved_failures": unresolved_failure_count,
        "recovered_failures": recovered_failure_count,
        "headless_values": sorted(str(value) for value in headless_values),
        "resolved_models": sorted(str(value) for value in resolved_models),
        "validation_errors": len(errors),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if errors:
        print("\nValidation errors:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if args.partial:
        print("Partial Train trajectory validation passed.")
    else:
        print("Strict Train trajectory validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
