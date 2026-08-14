#!/usr/bin/env python3
"""Build deterministic learning-input indexes from formal Train trajectories."""

from __future__ import annotations

import argparse
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
VALIDATOR = Path(__file__).with_name("validate_train_run.py")


def save_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")

    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    os.replace(temporary_path, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare Outcome-only and Filtered learning-input indexes "
            "from formal Train trajectories."
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
        help=(
            "Preview eligibility using currently completed trajectories. "
            "Partial mode never writes output files."
        ),
    )
    return parser.parse_args()


def load_train_tasks(manifest: dict) -> list[dict]:
    tasks = []
    seen_ids = set()

    for template in manifest["splits"]["train"]["templates"]:
        for task_id in template["task_ids"]:
            if task_id in seen_ids:
                raise ValueError(f"Duplicate Train Task ID: {task_id}")
            seen_ids.add(task_id)
            tasks.append(
                {
                    "task_id": task_id,
                    "intent_template_id": template["intent_template_id"],
                    "subset": template["subset"],
                }
            )

    expected_count = manifest["splits"]["train"]["task_count"]
    if expected_count != 51 or len(tasks) != expected_count:
        raise ValueError(
            "Expected exactly 51 Train tasks: "
            f"manifest={expected_count}, expanded={len(tasks)}"
        )

    return tasks


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

    subprocess.run(command, cwd=REPO_ROOT, check=True)


def violation_categories(safety_report: list) -> dict[str, int]:
    categories: Counter[str] = Counter()

    for report in safety_report:
        if not isinstance(report, dict) or report.get("violated") is not True:
            continue

        category = report.get("policy", {}).get(
            "policy_category",
            "unknown",
        )
        categories[category or "unknown"] += 1

    return dict(sorted(categories.items()))


def build_entry(
    path: Path,
    trajectory: dict,
    expected_task: dict,
) -> tuple[dict, dict]:
    outcome = trajectory["outcome"]
    task_success = outcome["task_success"] is True
    violated_policy_count = outcome["violated_policy_count"]

    outcome_only_eligible = task_success
    filtered_eligible = task_success and violated_policy_count == 0

    outcome_only_exclusion_reasons = []
    filtered_exclusion_reasons = []

    if not task_success:
        outcome_only_exclusion_reasons.append("task_not_successful")
        filtered_exclusion_reasons.append("task_not_successful")

    if violated_policy_count > 0:
        filtered_exclusion_reasons.append("policy_violations")

    source_entry = {
        **expected_task,
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "final_reward": outcome["final_reward"],
        "task_success": task_success,
        "violated_policy_count": violated_policy_count,
        "violation_categories": violation_categories(
            outcome.get("safety_report", [])
        ),
    }

    audit_entry = {
        **source_entry,
        "outcome_only_eligible": outcome_only_eligible,
        "outcome_only_exclusion_reasons": (
            outcome_only_exclusion_reasons
        ),
        "filtered_eligible": filtered_eligible,
        "filtered_exclusion_reasons": filtered_exclusion_reasons,
    }

    return source_entry, audit_entry


def build_dataset_manifest(
    dataset_id: str,
    selection_rule: str,
    entries: list[dict],
    source_metadata: dict,
) -> dict:
    return {
        "schema_version": "stweb_learning_input_manifest_0.1.0",
        "dataset_id": dataset_id,
        "source": source_metadata,
        "selection_rule": selection_rule,
        "trajectory_count": len(entries),
        "trajectories": entries,
    }


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    if not VALIDATOR.is_file():
        raise FileNotFoundError(f"Validator not found: {VALIDATOR}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "completed":
        raise ValueError(
            f"Manifest must be completed, got {manifest.get('status')!r}"
        )

    train_tasks = load_train_tasks(manifest)

    # Strict mode cannot produce indexes unless all 51 source trajectories
    # pass the authoritative validation. Partial mode is preview-only.
    run_validation(manifest_path, args.model, args.partial)

    raw_root = (
        REPO_ROOT
        / "artifacts"
        / manifest["manifest_id"]
        / "raw"
        / "train"
        / "no_skill"
    )

    outcome_only_entries = []
    filtered_entries = []
    eligibility_audit = []
    available_trajectories = []

    for expected_task in train_tasks:
        task_id = expected_task["task_id"]
        path = raw_root / f"task_{task_id}" / "trial_01" / "trajectory.json"

        if not path.is_file():
            continue

        trajectory = json.loads(path.read_text(encoding="utf-8"))
        source_entry, audit_entry = build_entry(
            path,
            trajectory,
            expected_task,
        )

        available_trajectories.append(trajectory)
        eligibility_audit.append(audit_entry)

        if audit_entry["outcome_only_eligible"]:
            outcome_only_entries.append(source_entry)

        if audit_entry["filtered_eligible"]:
            filtered_entries.append(source_entry)

    first_run = (
        available_trajectories[0]["run"]
        if available_trajectories
        else {}
    )
    source_metadata = {
        "manifest_id": manifest["manifest_id"],
        "split": "train",
        "method": "no_skill",
        "expected_trajectory_count": 51,
        "available_trajectory_count": len(available_trajectories),
        "requested_model": args.model,
        "resolved_model": first_run.get("resolved_model"),
        "headless": first_run.get("headless"),
    }

    summary = {
        "schema_version": "stweb_learning_eligibility_0.1.0",
        "source": source_metadata,
        "outcome_only": {
            "selection_rule": "task_success == true",
            "eligible_count": len(outcome_only_entries),
            "excluded_count": (
                len(available_trajectories) - len(outcome_only_entries)
            ),
        },
        "filtered": {
            "selection_rule": (
                "task_success == true and violated_policy_count == 0"
            ),
            "eligible_count": len(filtered_entries),
            "excluded_count": (
                len(available_trajectories) - len(filtered_entries)
            ),
        },
        "trajectories": eligibility_audit,
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.partial:
        print(
            "Partial eligibility preview completed; no files were written."
        )
        return 0

    output_dir = (
        REPO_ROOT
        / "artifacts"
        / manifest["manifest_id"]
        / "learning_inputs"
    )

    outcome_only_manifest = build_dataset_manifest(
        dataset_id="stweb_suitecrm_poc_v01_outcome_only",
        selection_rule="task_success == true",
        entries=outcome_only_entries,
        source_metadata=source_metadata,
    )
    filtered_manifest = build_dataset_manifest(
        dataset_id="stweb_suitecrm_poc_v01_filtered",
        selection_rule=(
            "task_success == true and violated_policy_count == 0"
        ),
        entries=filtered_entries,
        source_metadata=source_metadata,
    )

    save_json_atomic(
        output_dir / "outcome_only_manifest.json",
        outcome_only_manifest,
    )
    save_json_atomic(
        output_dir / "filtered_manifest.json",
        filtered_manifest,
    )
    save_json_atomic(
        output_dir / "eligibility_summary.json",
        summary,
    )

    print(f"Learning-input indexes saved under: {output_dir}")

    if not outcome_only_entries:
        print(
            "No Outcome-only eligible trajectories were found.",
            file=sys.stderr,
        )
        return 2

    if not filtered_entries:
        print(
            "No Filtered eligible trajectories were found; "
            "the selection rule was not relaxed.",
            file=sys.stderr,
        )
        return 2

    print("Learning-input preparation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
