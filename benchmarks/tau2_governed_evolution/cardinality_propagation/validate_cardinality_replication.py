"""Lightweight static checks for the bounded S5-R prompt intervention."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.cardinality_propagation.build_cardinality_replication_tasks import (
    MANIFEST_PATH,
    PROJECT_ROOT,
    SOURCE_MANIFEST_PATH,
    TASKS_PATH,
    build,
)
from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable


ensure_tau2_importable()

from tau2.data_model.tasks import Task  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/cardinality_propagation_step4w_s5r/validation.json"
FORBIDDEN_SCAFFOLD = (
    "old fare per passenger",
    "new fare per passenger",
    "passenger count",
    "multiply by",
    "fare breakdown",
    "show the calculation",
)


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    build()
    manifest = json.loads(MANIFEST_PATH.read_text())
    tasks = {row["id"]: Task.model_validate(row) for row in json.loads(TASKS_PATH.read_text())}
    return manifest, tasks


def validate() -> dict:
    manifest, tasks = load_suite()
    source_manifest = json.loads(SOURCE_MANIFEST_PATH.read_text())
    source_by_id = {row["task_id"]: row for row in source_manifest["tasks"]}
    rows = []
    for spec in manifest["tasks"]:
        candidate = spec["candidate"]
        source = source_by_id[spec["replicates_task_id"]]
        prompt = spec["scenario"]["task_instructions"].lower()
        task = tasks[spec["task_id"]]
        checks = {
            "same_candidate_metadata": candidate == source["candidate"],
            "same_reads": spec["reads"] == source["reads"],
            "same_wrong_update": spec["wrong_update"] == source["wrong_update"],
            "target_visible": candidate["target_flight"].lower() in prompt,
            "threshold_visible": str(candidate["threshold"]) in prompt,
            "entire_reservation_visible": "entire reservation" in prompt,
            "fallback_visible": "leave the reservation unchanged" in prompt,
            "protected_state_visible": all(word in prompt for word in ("passengers", "cabin", "baggage", "insurance")),
            "payment_visible": candidate["payment_id"].lower() in prompt,
            "no_cardinality_scaffold": not any(phrase in prompt for phrase in FORBIDDEN_SCAFFOLD),
            "no_passenger_count_leak": not re.search(
                rf"\b{candidate['passenger_count']}\s+passengers?\b", prompt, re.I
            ),
            "no_total_delta_leak": str(candidate["total_delta"]) not in prompt,
            "same_evaluator_geometry": str(candidate["total_delta"]) in task.evaluation_criteria.nl_assertions[0],
            "oracle_branch_unchanged": candidate["total_delta"] > candidate["threshold"],
        }
        rows.append({"task_id": spec["task_id"], "checks": checks, "passed": all(checks.values())})
    return {"passed": all(row["passed"] for row in rows), "rows": rows}


def main() -> int:
    result = validate()
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
