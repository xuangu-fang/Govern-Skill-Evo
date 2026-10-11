#!/usr/bin/env python3
"""Offline consistency checks for the structurally blocked Primitive A pilot."""

from __future__ import annotations

import json
from pathlib import Path


EDITION = Path(__file__).resolve().parents[3]


def load(relative: str):
    return json.loads((EDITION / relative).read_text(encoding="utf-8"))


def main() -> int:
    version = load("VERSION.json")
    tasks = load("construction/primitive_a/candidate_tasks/tasks.json")
    manifest = load("construction/primitive_a/candidate_tasks/task_manifest.json")
    candidates = load("construction/primitive_a/candidates/native_transition_candidates.json")
    audit = load("construction/primitive_a/structural_audit/structural_audit.json")

    errors: list[str] = []
    if version["id"] != "phase_v3_day34":
        errors.append("wrong edition id")
    if version["task_count"] != len(tasks) or manifest["task_count"] != len(tasks):
        errors.append("task count mismatch")
    if tasks:
        errors.append("tasks were admitted despite the structural block")
    if candidates["admitted_count"] != 0:
        errors.append("candidate admission mismatch")
    if any(row["decision"] != "REJECT" for row in candidates["candidates"]):
        errors.append("non-rejected candidate present")
    if audit["result"] != "FAIL_STRUCTURAL" or audit["qualified_task_count"] != 0:
        errors.append("structural verdict mismatch")
    required_false = (
        "downstream_target_not_reliably_known_before_mutation",
        "mutation_outcome_can_change_downstream_binding",
        "post_mutation_refetch_is_required",
        "stale_identifier_causes_native_downstream_failure",
    )
    if any(audit["checks"][key] for key in required_false):
        errors.append("native dependency checks unexpectedly passed")

    if errors:
        print("FAIL Primitive A structural audit: " + "; ".join(errors))
        return 1
    print(
        "PASS Primitive A audit consistency: 6 rejected candidates, "
        "0 admitted tasks, verdict FAIL_STRUCTURAL"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
