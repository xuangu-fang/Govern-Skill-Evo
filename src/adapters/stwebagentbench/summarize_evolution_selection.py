#!/usr/bin/env python3
"""Summarize a paired Parent -> Candidate Selection experiment.

This command reads two completed Selection trajectory sets, pairs them by
task_id, computes the requested capability/governance statistics, and saves
both a machine-readable JSON report and a human-readable Markdown report.

It intentionally does not run the standalone Selection validator.  The only
input checks here are the structural checks required to avoid producing
statistics from missing, duplicated, or unpaired tasks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from src.skill_evolution.two_dimensional_gate import (
    OutcomeState,
    STATE_ORDER,
    classify_state,
    classify_transition,
)
from src.skill_evolution.implementation_binding import (
    require_implementation_binding,
)


DEFAULT_MANIFEST = (
    REPO_ROOT
    / "experiments"
    / "manifests"
    / "stweb_suitecrm_poc_v02.json"
)

STATE_ABBREVIATIONS = {
    OutcomeState.VIOLATING_FAILURE: "VF",
    OutcomeState.VIOLATING_SUCCESS: "VS",
    OutcomeState.COMPLIANT_FAILURE: "CF",
    OutcomeState.COMPLIANT_SUCCESS: "CS",
}
STATE_LABELS = {
    "VF": "Violating Failure",
    "VS": "Violating Success",
    "CF": "Compliant Failure",
    "CS": "Compliant Success",
}
CATEGORY_LABELS = {
    "strict_execution": "Strict Execution",
    "hierarchy_adherence": "Hierarchy Adherence",
    "user_consent": "User Consent",
    "error_handling_and_safety_nets": (
        "Error Handling and Safety Nets"
    ),
}
CATEGORY_ORDER = tuple(CATEGORY_LABELS)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_text_atomic(path: Path, text: str) -> None:
    """Atomically save UTF-8 text."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    temporary_path.write_text(text, encoding="utf-8")
    os.replace(temporary_path, path)


def save_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Atomically save indented JSON."""

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    save_text_atomic(path, text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize paired Parent and Candidate Selection trajectories "
            "without "
            "running the standalone validator."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Frozen experiment manifest.",
    )
    parser.add_argument(
        "--reference",
        help="Reference method. Defaults to manifest skill_evolution.",
    )
    parser.add_argument(
        "--candidate",
        help="Candidate method. Defaults to manifest skill_evolution.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Output directory. Defaults to "
            "experiments/results/<manifest_id>/selection."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate Parent/Candidate configuration without reading trajectories.",
    )
    return parser.parse_args()


def _selection_tasks(manifest: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Index the manifest's Selection tasks by task_id."""

    tasks: dict[int, dict[str, Any]] = {}
    templates = manifest["splits"]["selection"]["templates"]

    for template in templates:
        for task_id in template["task_ids"]:
            if task_id in tasks:
                raise ValueError(
                    f"Duplicate Selection task_id in manifest: {task_id}"
                )
            tasks[task_id] = {
                "task_id": task_id,
                "intent_template_id": template["intent_template_id"],
                "subset": template["subset"],
            }

    expected_count = manifest["splits"]["selection"].get("task_count")
    if expected_count is not None and len(tasks) != expected_count:
        raise ValueError(
            "Selection task_count does not match the listed task IDs: "
            f"expected {expected_count}, found {len(tasks)}"
        )

    if not tasks:
        raise ValueError("Manifest contains no Selection tasks.")

    return tasks


def _violation_categories(
    violated_policies: list[dict[str, Any]],
) -> dict[str, int]:
    categories: Counter[str] = Counter()

    for report in violated_policies:
        policy = report.get("policy", {})
        category = policy.get("policy_category") or "unknown"
        categories[category] += 1

    return dict(sorted(categories.items()))


def _load_method_rows(
    manifest: dict[str, Any],
    expected_tasks: dict[int, dict[str, Any]],
    method: str,
    repo_root: Path = REPO_ROOT,
) -> list[dict[str, Any]]:
    """Load one completed trajectory for every expected task."""

    raw_root = (
        repo_root
        / "artifacts"
        / manifest["manifest_id"]
        / "raw"
        / "selection"
        / method
    )
    rows: list[dict[str, Any]] = []

    for task_id, expected_task in sorted(expected_tasks.items()):
        path = (
            raw_root
            / f"task_{task_id}"
            / "trial_01"
            / "trajectory.json"
        )
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing Selection trajectory for {method} Task "
                f"{task_id}: {path}"
            )

        trajectory = json.loads(path.read_text(encoding="utf-8"))
        recorded_task_id = trajectory.get("task", {}).get("task_id")
        recorded_method = trajectory.get("run", {}).get("method")
        if recorded_task_id != task_id:
            raise ValueError(
                f"Trajectory at {path} records Task {recorded_task_id!r}, "
                f"expected {task_id}."
            )
        if recorded_method != method:
            raise ValueError(
                f"Trajectory at {path} records method "
                f"{recorded_method!r}, expected {method!r}."
            )

        outcome = trajectory.get("outcome")
        if not isinstance(outcome, dict):
            raise ValueError(f"Trajectory has no outcome object: {path}")

        task_success = outcome.get("task_success")
        violated_policies = outcome.get("violated_policies")
        steps = trajectory.get("steps")
        if not isinstance(task_success, bool):
            raise ValueError(
                f"Trajectory has no binary task_success verdict: {path}"
            )
        if not isinstance(violated_policies, list):
            raise ValueError(
                f"Trajectory has no violated_policies list: {path}"
            )
        if not isinstance(steps, list):
            raise ValueError(f"Trajectory has no steps list: {path}")

        violation_count = len(violated_policies)
        compliant = violation_count == 0
        rows.append(
            {
                **expected_task,
                "method": method,
                "task_success": task_success,
                "compliant": compliant,
                "cup": task_success and compliant,
                "successful_but_violating": (
                    task_success and not compliant
                ),
                "violation_count": violation_count,
                "violation_categories": _violation_categories(
                    violated_policies
                ),
                "steps": len(steps),
                "trajectory_path": path.relative_to(repo_root).as_posix(),
            }
        )

    return rows


def _metric(count: int, total: int) -> dict[str, int | float]:
    return {
        "count": count,
        "total": total,
        "rate": count / total,
    }


def _summarize_method(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    if count == 0:
        raise ValueError("Cannot summarize an empty trajectory set.")

    task_success = sum(row["task_success"] for row in rows)
    compliance = sum(row["compliant"] for row in rows)
    cup = sum(row["cup"] for row in rows)
    successful_but_violating = sum(
        row["successful_but_violating"] for row in rows
    )
    total_violations = sum(row["violation_count"] for row in rows)
    total_steps = sum(row["steps"] for row in rows)
    category_counts: Counter[str] = Counter()
    state_counts: Counter[OutcomeState] = Counter()

    for row in rows:
        category_counts.update(row["violation_categories"])
        state_counts.update(
            [classify_state(row["task_success"], row["compliant"])]
        )

    return {
        "task_count": count,
        "task_success": _metric(task_success, count),
        "compliance": _metric(compliance, count),
        "cup": _metric(cup, count),
        "successful_but_violating": successful_but_violating,
        "total_violation_instances": total_violations,
        "average_steps": total_steps / count,
        "state_distribution": {
            STATE_ABBREVIATIONS[state]: state_counts[state]
            for state in STATE_ORDER
        },
        "violation_categories": dict(sorted(category_counts.items())),
    }


def _transition_explanation(
    before: OutcomeState,
    after: OutcomeState,
    candidate_label: str = "S1",
) -> str:
    """Return a deterministic explanation based only on verifier states."""

    explanations = {
        (
            OutcomeState.VIOLATING_FAILURE,
            OutcomeState.VIOLATING_SUCCESS,
        ): f"{candidate_label}完成了任务，但仍然存在违规。",
        (
            OutcomeState.VIOLATING_SUCCESS,
            OutcomeState.VIOLATING_FAILURE,
        ): f"{candidate_label}未能完成任务，并且仍然存在违规。",
        (
            OutcomeState.VIOLATING_FAILURE,
            OutcomeState.COMPLIANT_SUCCESS,
        ): "Task Success和Compliance同时改善，并产生新的CuP。",
        (
            OutcomeState.VIOLATING_FAILURE,
            OutcomeState.COMPLIANT_FAILURE,
        ): f"{candidate_label}避免了违规，但没有完成任务。",
        (
            OutcomeState.VIOLATING_SUCCESS,
            OutcomeState.COMPLIANT_SUCCESS,
        ): f"{candidate_label}保留Task Success并修复了Governance违规。",
        (
            OutcomeState.COMPLIANT_FAILURE,
            OutcomeState.COMPLIANT_SUCCESS,
        ): f"{candidate_label}在保持Compliance的同时完成了任务。",
        (
            OutcomeState.COMPLIANT_SUCCESS,
            OutcomeState.VIOLATING_SUCCESS,
        ): f"{candidate_label}保持Task Success，但出现Governance退化。",
    }
    return explanations.get(
        (before, after),
        "Capability与Governance状态发生变化。",
    )


def _index_rows(
    rows: list[dict[str, Any]],
    label: str,
) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        task_id = row.get("task_id")
        if not isinstance(task_id, int):
            raise ValueError(f"Invalid task_id in {label}: {task_id!r}")
        if task_id in indexed:
            raise ValueError(f"Duplicate Task {task_id} in {label}.")
        indexed[task_id] = row
    return indexed


def build_report(
    reference_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    reference_method: str,
    candidate_method: str,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the complete paired experiment summary."""

    reference_index = _index_rows(reference_rows, reference_method)
    candidate_index = _index_rows(candidate_rows, candidate_method)
    if reference_index.keys() != candidate_index.keys():
        missing_candidate = sorted(
            reference_index.keys() - candidate_index.keys()
        )
        missing_reference = sorted(
            candidate_index.keys() - reference_index.keys()
        )
        raise ValueError(
            "Reference and candidate task IDs do not match. "
            f"Missing candidate: {missing_candidate}; "
            f"missing reference: {missing_reference}."
        )

    reference = _summarize_method(reference_rows)
    candidate = _summarize_method(candidate_rows)
    aggregate_deltas = {
        "task_success": (
            candidate["task_success"]["count"]
            - reference["task_success"]["count"]
        ),
        "compliance": (
            candidate["compliance"]["count"]
            - reference["compliance"]["count"]
        ),
        "cup": candidate["cup"]["count"] - reference["cup"]["count"],
        "successful_but_violating": (
            candidate["successful_but_violating"]
            - reference["successful_but_violating"]
        ),
        "total_violation_instances": (
            candidate["total_violation_instances"]
            - reference["total_violation_instances"]
        ),
        "average_steps": (
            candidate["average_steps"] - reference["average_steps"]
        ),
    }

    state_deltas = {
        abbreviation: (
            candidate["state_distribution"][abbreviation]
            - reference["state_distribution"][abbreviation]
        )
        for abbreviation in STATE_LABELS
    }

    categories = set(reference["violation_categories"]) | set(
        candidate["violation_categories"]
    )
    category_reference = {
        category: reference["violation_categories"].get(category, 0)
        for category in categories
    }
    category_candidate = {
        category: candidate["violation_categories"].get(category, 0)
        for category in categories
    }
    category_deltas = {
        category: category_candidate[category] - category_reference[category]
        for category in categories
    }

    tasks = []
    transition_counts: Counter[str] = Counter()
    for task_id in sorted(reference_index):
        before_row = reference_index[task_id]
        after_row = candidate_index[task_id]
        before = classify_state(
            before_row["task_success"], before_row["compliant"]
        )
        after = classify_state(
            after_row["task_success"], after_row["compliant"]
        )
        transition_type = classify_transition(before, after)
        transition_counts[transition_type] += 1
        tasks.append(
            {
                "task_id": task_id,
                "from_state": STATE_ABBREVIATIONS[before],
                "to_state": STATE_ABBREVIATIONS[after],
                "transition_type": transition_type,
                "changed": before != after,
                "explanation": (
                    _transition_explanation(
                        before,
                        after,
                        _method_short_label(candidate_method),
                    )
                    if before != after
                    else "状态保持不变。"
                ),
            }
        )

    changed_tasks = [task for task in tasks if task["changed"]]
    report_source = dict(source or {})
    report_source.update(
        {
            "reference_method": reference_method,
            "candidate_method": candidate_method,
            "primary_evaluation_unit": "task_id",
        }
    )

    return {
        "schema_version": "stweb_evolution_selection_summary_0.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": report_source,
        "aggregate": {
            "reference": reference,
            "candidate": candidate,
            "deltas": aggregate_deltas,
        },
        "state_distribution": {
            "reference": reference["state_distribution"],
            "candidate": candidate["state_distribution"],
            "deltas": state_deltas,
        },
        "task_evolution_transitions": {
            "paired_task_count": len(tasks),
            "stable_task_count": len(tasks) - len(changed_tasks),
            "changed_task_count": len(changed_tasks),
            "transition_type_counts": dict(sorted(transition_counts.items())),
            "tasks": tasks,
            "changed_tasks": changed_tasks,
        },
        "violation_categories": {
            "reference": dict(sorted(category_reference.items())),
            "candidate": dict(sorted(category_candidate.items())),
            "deltas": dict(sorted(category_deltas.items())),
        },
    }


def _method_label(method: str) -> str:
    labels = {
        "no_skill": "S0 No Skill",
        "governed_candidate_s1": "S1 Governed Candidate",
        "governed_candidate_s2": "S2 Governed Candidate",
    }
    return labels.get(method, method)


def _method_short_label(method: str) -> str:
    labels = {
        "no_skill": "S0",
        "governed_candidate_s1": "S1",
        "governed_candidate_s2": "S2",
    }
    return labels.get(method, method)


def _format_metric(metric: dict[str, int | float]) -> str:
    count = int(metric["count"])
    total = int(metric["total"])
    rate = float(metric["rate"])
    return f"{count}/{total}（{rate:.2%}）"


def _format_delta(value: int | float) -> str:
    if value > 0:
        return f"+{value:g}"
    return f"{value:g}"


def _ordered_categories(report: dict[str, Any]) -> list[str]:
    available = set(report["violation_categories"]["reference"]) | set(
        report["violation_categories"]["candidate"]
    )
    preferred = [
        category for category in CATEGORY_ORDER if category in available
    ]
    return preferred + sorted(available - set(preferred))


def render_markdown(report: dict[str, Any]) -> str:
    """Render the summary as a compact experiment-report section."""

    source = report["source"]
    reference_method = source["reference_method"]
    candidate_method = source["candidate_method"]
    reference_label = _method_label(reference_method)
    candidate_label = _method_label(candidate_method)
    reference_short = _method_short_label(reference_method)
    candidate_short = _method_short_label(candidate_method)
    aggregate = report["aggregate"]
    reference = aggregate["reference"]
    candidate = aggregate["candidate"]
    deltas = aggregate["deltas"]

    lines = [
        f"# {reference_short}→{candidate_short} Selection结果汇总",
        "",
        "#### 聚合结果",
        "",
        f"| 指标 | {reference_label} | {candidate_label} | 变化 |",
        "|---|---:|---:|---:|",
        (
            "| Task Success / CR | "
            f"{_format_metric(reference['task_success'])} | "
            f"{_format_metric(candidate['task_success'])} | "
            f"{_format_delta(deltas['task_success'])} |"
        ),
        (
            "| Compliance | "
            f"{_format_metric(reference['compliance'])} | "
            f"{_format_metric(candidate['compliance'])} | "
            f"{_format_delta(deltas['compliance'])} |"
        ),
        (
            "| CuP | "
            f"{_format_metric(reference['cup'])} | "
            f"{_format_metric(candidate['cup'])} | "
            f"{_format_delta(deltas['cup'])} |"
        ),
        (
            "| Successful but Violating | "
            f"{reference['successful_but_violating']} | "
            f"{candidate['successful_but_violating']} | "
            f"{_format_delta(deltas['successful_but_violating'])} |"
        ),
        (
            "| 违规实例总数 | "
            f"{reference['total_violation_instances']} | "
            f"{candidate['total_violation_instances']} | "
            f"{_format_delta(deltas['total_violation_instances'])} |"
        ),
        (
            "| 平均步骤数 | "
            f"{reference['average_steps']:.2f} | "
            f"{candidate['average_steps']:.2f} | / |"
        ),
        "",
        "#### 四状态分布",
        "",
        f"| 状态 | {reference_short} | {candidate_short} | 变化 |",
        "|---|---:|---:|---:|",
    ]

    state_distribution = report["state_distribution"]
    for abbreviation, label in STATE_LABELS.items():
        lines.append(
            f"| {label}（{abbreviation}） | "
            f"{state_distribution['reference'][abbreviation]} | "
            f"{state_distribution['candidate'][abbreviation]} | "
            f"{_format_delta(state_distribution['deltas'][abbreviation])} |"
        )

    transitions = report["task_evolution_transitions"]
    lines.extend(
        [
            "",
            "#### Task evolution transitions",
            "",
            (
                f"{transitions['paired_task_count']}个Task中有"
                f"{transitions['stable_task_count']}个保持在原状态，"
                f"{transitions['changed_task_count']}个发生状态变化："
            ),
            "",
            f"| Task | {reference_short} → {candidate_short} | 解释 |",
            "|---:|---|---|",
        ]
    )
    for task in transitions["changed_tasks"]:
        lines.append(
            f"| {task['task_id']} | {task['from_state']} → "
            f"{task['to_state']} | {task['explanation']} |"
        )

    lines.extend(
        [
            "",
            "#### 违规类型变化",
            "",
            f"| Policy category | {reference_short} | {candidate_short} | 变化 |",
            "|---|---:|---:|---:|",
        ]
    )
    category_summary = report["violation_categories"]
    for category in _ordered_categories(report):
        label = CATEGORY_LABELS.get(
            category,
            category.replace("_", " ").title(),
        )
        lines.append(
            f"| {label} | {category_summary['reference'][category]} | "
            f"{category_summary['candidate'][category]} | "
            f"{_format_delta(category_summary['deltas'][category])} |"
        )

    return "\n".join(lines) + "\n"


def _resolve_methods(
    manifest: dict[str, Any],
    reference: str | None,
    candidate: str | None,
) -> tuple[str, str]:
    evolution = manifest.get("skill_evolution", {})
    reference_method = reference or evolution.get("reference", {}).get(
        "method"
    ) or evolution.get("parent", {}).get("method")
    candidate_method = candidate or evolution.get("candidate", {}).get(
        "method"
    )
    if not reference_method or not candidate_method:
        raise ValueError(
            "Reference and candidate methods must be supplied by CLI or "
            "manifest skill_evolution."
        )

    planned_methods = manifest.get("planned_rollouts", {}).get(
        "selection", {}
    ).get("methods", [])
    for method in (reference_method, candidate_method):
        if method not in planned_methods:
            raise ValueError(
                f"Method {method!r} is not a planned Selection method."
            )

    return reference_method, candidate_method


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not args.dry_run:
        require_implementation_binding(manifest_path, manifest)
    reference_method, candidate_method = _resolve_methods(
        manifest,
        args.reference,
        args.candidate,
    )
    expected_tasks = _selection_tasks(manifest)
    if args.dry_run:
        print(json.dumps({
            "mode": "dry_run",
            "manifest_id": manifest["manifest_id"],
            "reference_method": reference_method,
            "candidate_method": candidate_method,
            "paired_task_count": len(expected_tasks),
            "output_dir": (
                args.output_dir.resolve().relative_to(REPO_ROOT).as_posix()
                if args.output_dir
                else f"experiments/results/{manifest['manifest_id']}/selection"
            ),
        }, ensure_ascii=False, indent=2))
        print("Evolution summary dry-run passed.")
        return 0
    reference_rows = _load_method_rows(
        manifest,
        expected_tasks,
        reference_method,
    )
    candidate_rows = _load_method_rows(
        manifest,
        expected_tasks,
        candidate_method,
    )

    source = {
        "manifest_id": manifest["manifest_id"],
        "manifest_path": manifest_path.relative_to(REPO_ROOT).as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
        "reference_trajectory_root": (
            f"artifacts/{manifest['manifest_id']}/raw/selection/"
            f"{reference_method}"
        ),
        "candidate_trajectory_root": (
            f"artifacts/{manifest['manifest_id']}/raw/selection/"
            f"{candidate_method}"
        ),
    }
    report = build_report(
        reference_rows,
        candidate_rows,
        reference_method,
        candidate_method,
        source,
    )

    output_dir = args.output_dir
    if output_dir is None:
        output_dir = (
            REPO_ROOT
            / "experiments"
            / "results"
            / manifest["manifest_id"]
            / "selection"
        )
    else:
        output_dir = output_dir.resolve()

    json_path = output_dir / "evolution_summary.json"
    markdown_path = output_dir / "evolution_summary.md"
    save_json_atomic(json_path, report)
    save_text_atomic(markdown_path, render_markdown(report))

    print(
        json.dumps(
            {
                "reference_method": reference_method,
                "candidate_method": candidate_method,
                "paired_task_count": report[
                    "task_evolution_transitions"
                ]["paired_task_count"],
                "stable_task_count": report[
                    "task_evolution_transitions"
                ]["stable_task_count"],
                "changed_task_count": report[
                    "task_evolution_transitions"
                ]["changed_task_count"],
                "json_output": json_path.relative_to(REPO_ROOT).as_posix(),
                "markdown_output": markdown_path.relative_to(
                    REPO_ROOT
                ).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
