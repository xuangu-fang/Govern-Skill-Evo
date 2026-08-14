#!/usr/bin/env python3
"""Build compact Outcome + Process feedback for governed Skill learning.

The v0.1 representation deliberately keeps policy feedback at trajectory and
rule level. ST-WebAgentBench ``violating_step`` metadata is not exposed to the
Learner because it is not reliable enough for step-level attribution.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.skill_evolution.two_dimensional_gate import (
    OutcomeState,
    classify_state,
)


SCHEMA_VERSION = "governed_experience_0.1.0"


def _compact_actions(steps: Any) -> list[dict[str, Any]]:
    """Keep the observable action sequence without model reasoning."""

    if not isinstance(steps, list):
        raise ValueError("Trajectory steps must be a list.")

    actions: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("Every trajectory step must be an object.")

        step_number = step.get("step")
        action = step.get("action")
        if not isinstance(step_number, int):
            raise ValueError("Every trajectory step must have an integer step.")
        if not isinstance(action, str) or not action:
            raise ValueError("Every trajectory step must have an action.")

        observation = step.get("observation_before", {})
        if not isinstance(observation, dict):
            raise ValueError("observation_before must be an object.")

        actions.append(
            {
                "step": step_number,
                "url": observation.get("url", ""),
                "action": action,
                "action_error": step.get("last_action_error", ""),
            }
        )

    return actions


def _sanitize_for_learner(value: Any) -> Any:
    """Recursively remove fields that must not reach the Skill Learner."""

    if isinstance(value, dict):
        return {
            key: _sanitize_for_learner(item)
            for key, item in value.items()
            if key != "sensitive_data"
        }
    if isinstance(value, list):
        return [_sanitize_for_learner(item) for item in value]
    return value


def _compact_policy(report: dict[str, Any]) -> dict[str, Any]:
    """Keep the human-readable rule and sanitized evaluator specification."""

    policy = report.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("Every safety report must contain a policy object.")

    policy_spec = policy.get("eval", {})
    if not isinstance(policy_spec, dict):
        raise ValueError("Every policy eval specification must be an object.")

    return {
        "policy_template_id": policy.get("policy_template_id"),
        "category": policy.get("policy_category"),
        "source": policy.get("source"),
        "description": policy.get("description"),
        "eval_type": report.get("eval_type"),
        "policy_spec": _sanitize_for_learner(policy_spec),
    }


def build_experience(
    trajectory: dict[str, Any],
    source_id: str,
) -> dict[str, Any]:
    """Convert one ST-WebAgentBench trajectory into governed experience."""

    if trajectory.get("schema_version") != "stweb_raw_0.1.0":
        raise ValueError(
            "Expected an stweb_raw_0.1.0 trajectory, got "
            f"{trajectory.get('schema_version')!r}."
        )
    if not source_id:
        raise ValueError("source_id must not be empty.")

    initial_observation = trajectory.get("initial_observation")
    outcome = trajectory.get("outcome")
    if not isinstance(initial_observation, dict):
        raise ValueError("Trajectory must contain initial_observation.")
    if not isinstance(outcome, dict):
        raise ValueError("Trajectory must contain outcome.")

    goal = initial_observation.get("goal")
    task_success = outcome.get("task_success")
    safety_report = outcome.get("safety_report")
    violated_policy_count = outcome.get("violated_policy_count")

    if not isinstance(goal, str) or not goal:
        raise ValueError("Trajectory goal must be a non-empty string.")
    if not isinstance(task_success, bool):
        raise ValueError("outcome.task_success must be boolean.")
    if not isinstance(safety_report, list):
        raise ValueError("outcome.safety_report must be a list.")
    if not isinstance(violated_policy_count, int):
        raise ValueError("outcome.violated_policy_count must be an integer.")

    applicable_reports: list[dict[str, Any]] = []
    violated_reports: list[dict[str, Any]] = []

    for report in safety_report:
        if not isinstance(report, dict):
            raise ValueError("Every safety report must be an object.")

        dormant = report.get("dormant")
        violated = report.get("violated")
        if not isinstance(dormant, bool) or not isinstance(violated, bool):
            raise ValueError(
                "Every safety report must have boolean dormant and violated."
            )
        if dormant and violated:
            raise ValueError("A dormant policy cannot also be violated.")

        if not dormant:
            applicable_reports.append(report)
        if violated:
            violated_reports.append(report)

    if violated_policy_count != len(violated_reports):
        raise ValueError(
            "violated_policy_count does not match the safety report: "
            f"declared={violated_policy_count}, "
            f"observed={len(violated_reports)}"
        )

    compliant = not violated_reports
    state = classify_state(task_success, compliant)

    return {
        "source_id": source_id,
        "state": state.value,
        "goal": goal,
        "actions": _compact_actions(trajectory.get("steps")),
        "task_success": task_success,
        "applicable_policies": [
            _compact_policy(report)
            for report in applicable_reports
        ],
        "process_feedback": {
            "compliant": compliant,
            "violated_policies": [
                _compact_policy(report)
                for report in violated_reports
            ],
        },
    }


def build_dataset(
    trajectory_paths: list[Path],
    lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic dataset and source-provenance index."""

    loaded: list[tuple[int, Path, dict[str, Any]]] = []
    seen_task_ids: set[int] = set()

    for path in trajectory_paths:
        trajectory = json.loads(path.read_text(encoding="utf-8"))
        task = trajectory.get("task")
        task_id = task.get("task_id") if isinstance(task, dict) else None
        if not isinstance(task_id, int):
            raise ValueError(f"Trajectory has no integer task_id: {path}")
        if task_id in seen_task_ids:
            raise ValueError(f"Duplicate Task {task_id} in trajectory inputs.")

        seen_task_ids.add(task_id)
        loaded.append((task_id, path, trajectory))

    loaded.sort(key=lambda item: item[0])
    state_counts: Counter[str] = Counter()
    experiences: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []

    for index, (task_id, path, trajectory) in enumerate(loaded, start=1):
        source_id = (
            f"s1_train_task_{task_id:03d}_trial_01"
            if lineage is not None
            else f"source_{index:03d}"
        )
        experience = build_experience(trajectory, source_id)
        experiences.append(experience)
        state_counts[experience["state"]] += 1
        sources.append(
            {
                "source_id": source_id,
                "task_id": task_id,
                "path": path.as_posix(),
            }
        )

    dataset = {
        "schema_version": SCHEMA_VERSION,
        "experience_count": len(experiences),
        "state_counts": {
            state.value: state_counts[state.value]
            for state in OutcomeState
        },
        "sources": sources,
        "experiences": experiences,
    }
    if lineage is not None:
        dataset["lineage"] = lineage
    return dataset


def validate_s1_lineage(
    trajectory_paths: list[Path],
    manifest_path: Path,
) -> dict[str, Any]:
    """Require 51 fresh v03 S1 Train trajectories from accepted S1."""

    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    planned = manifest["planned_rollouts"]["train"]
    methods = planned.get("methods", [])
    if methods != ["governed_candidate_s1"]:
        raise ValueError("S1 lineage requires the single v03 S1 Train method.")
    expected_count = manifest["splits"]["train"]["task_count"]
    if len(trajectory_paths) != expected_count:
        raise ValueError(
            f"Expected {expected_count} S1 Train trajectories, "
            f"got {len(trajectory_paths)}."
        )

    parent = manifest["skill_evolution"]["parent"]
    expected = {
        "status": "completed",
        "run_kind": "formal",
        "manifest_id": manifest["manifest_id"],
        "split": "train",
        "method": parent["method"],
        "skill_version": parent["skill_version"],
        "skill_path": parent["skill_path"],
        "skill_injected": True,
    }
    expected_task_ids = {
        task_id
        for template in manifest["splits"]["train"]["templates"]
        for task_id in template["task_ids"]
    }
    observed_task_ids: set[int] = set()
    for path in trajectory_paths:
        trajectory = json.loads(path.read_text(encoding="utf-8"))
        run = trajectory.get("run", {})
        mismatches = {
            key: {"expected": value, "actual": run.get(key)}
            for key, value in expected.items()
            if run.get(key) != value
        }
        if mismatches:
            raise ValueError(
                f"Invalid S1 lineage in {path}: "
                f"{json.dumps(mismatches, ensure_ascii=False)}"
            )
        task_id = trajectory.get("task", {}).get("task_id")
        if not isinstance(task_id, int) or task_id in observed_task_ids:
            raise ValueError(f"Invalid or duplicate S1 Train task: {task_id!r}")
        observed_task_ids.add(task_id)
    if observed_task_ids != expected_task_ids:
        raise ValueError("S1 Train task IDs do not match the recorded split.")

    return {
        "manifest_id": manifest["manifest_id"],
        "manifest_path": manifest_path.relative_to(
            Path(__file__).resolve().parents[2]
        ).as_posix(),
        "split": "train",
        "method": parent["method"],
        "skill_version": parent["skill_version"],
        "skill_path": parent["skill_path"],
        "trajectory_count": len(trajectory_paths),
    }


def _save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON artifact without exposing a partially written file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temporary_path, path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build v0.1 governed experiences from ST-WebAgentBench Train "
            "trajectories."
        )
    )
    parser.add_argument(
        "--trajectory-root",
        required=True,
        type=Path,
        help="Directory containing task_*/trial_01/trajectory.json files.",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        help=(
            "When supplied, enforce strict fresh S1 Train lineage before "
            "building the dataset."
        ),
    )
    return parser.parse_args()


def main() -> int:
    """Build and save one governed-experience dataset."""

    args = _parse_args()
    trajectory_paths = list(
        args.trajectory_root.glob("task_*/trial_01/trajectory.json")
    )
    if not trajectory_paths:
        raise ValueError(
            f"No Train trajectories found under {args.trajectory_root}."
        )

    lineage = (
        validate_s1_lineage(trajectory_paths, args.manifest)
        if args.manifest
        else None
    )
    dataset = build_dataset(trajectory_paths, lineage=lineage)
    _save_json_atomic(args.output, dataset)
    print(
        f"Saved {dataset['experience_count']} governed experiences to "
        f"{args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
