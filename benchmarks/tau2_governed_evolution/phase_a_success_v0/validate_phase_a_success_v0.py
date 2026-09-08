"""Lightweight metadata and source-evidence audit for the frozen v0 workload."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable
from benchmarks.tau2_governed_evolution.phase_a_success_v0.build_phase_a_success_v0 import (
    MANIFEST_PATH,
    PROJECT_ROOT,
    TASKS_PATH,
    build,
)


ensure_tau2_importable()

from tau2.data_model.tasks import Task  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/phase_a_success_v0/validation.json"
PRIOR_EVIDENCE = (
    "artifacts/transition_ablation_step4v/analysis_summary.json",
    "artifacts/partial_knowledge_headroom_step4w/analysis_summary.json",
    "artifacts/airline_deep_dependency_step4r/analysis_summary.json",
    "artifacts/certificate_lifecycle_step4w_s3/analysis.json",
    "artifacts/airline_phase_a_mechanism_step4s/analysis_summary.json",
    "artifacts/phase_a_capability_step4t/analysis_summary.json",
    "artifacts/cardinality_propagation_step4w_s5r/analysis.json",
)


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    build()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    values = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    tasks = {row["id"]: Task.model_validate(row) for row in values}
    if len(tasks) != len(values):
        raise ValueError("duplicate task id")
    return manifest, tasks


def validate() -> dict[str, Any]:
    manifest, tasks = load_suite()
    roles = Counter(row["task_role"] for row in manifest["tasks"])
    families = Counter(row["source_family"] for row in manifest["tasks"])
    source_states = [json.dumps(row["source_state"], sort_keys=True) for row in manifest["tasks"]]
    rows = []
    for spec in manifest["tasks"]:
        task = tasks[spec["task_id"]]
        policy_path = manifest["context_views"][spec["view_id"]]
        checks = {
            "task_materialized": task.id == spec["task_id"],
            "domain_consistent": task.user_scenario.instructions.domain == spec["domain"],
            "phase_a_complete_upfront": spec["phase_a_complete_upfront"] is True,
            "phase_a_stable_intent": spec["phase_a_stable_intent"] is True,
            "valid_context_mode": spec["context_mode"] in {"CANONICAL", "PARTIAL_OPERATIONAL"},
            "view_exists": policy_path is None or (PROJECT_ROOT / policy_path).is_file(),
            "source_task_exists": (PROJECT_ROOT / spec["source_artifact"]).is_file(),
            "source_metadata_exists": (PROJECT_ROOT / spec["source_metadata"]).is_file(),
            "evaluator_present": bool(task.evaluation_criteria.reward_basis),
        }
        rows.append({"task_id": spec["task_id"], "checks": checks, "passed": all(checks.values())})
    pool_checks = {
        "size_12_to_16": 12 <= len(manifest["tasks"]) <= 16,
        "headroom_count": roles["SKILL_HEADROOM"] == 7,
        "positive_control_count": roles["POSITIVE_CONTROL"] == 2,
        "ordinary_clean_count": roles["ORDINARY_CLEAN"] == 4,
        "four_headroom_families": all(families[name] for name in (
            "S1_PAYMENT_HISTORY_DEPENDENCY",
            "S2_TRANSACTION_BASELINE_BINDING",
            "S3_CERTIFICATE_LIFECYCLE",
            "S5_DEEP_TRANSACTION_CARDINALITY",
        )),
        "both_domains": {row["domain"] for row in manifest["tasks"]} == {"airline", "retail"},
        "unique_source_states": len(source_states) == len(set(source_states)),
        "prior_evidence_available": all((PROJECT_ROOT / path).is_file() for path in PRIOR_EVIDENCE),
        "frozen_before_rollouts": manifest["selection_status"] == "FROZEN_BEFORE_V0_EMPTY_ROLLOUTS",
    }
    passed = all(row["passed"] for row in rows) and all(pool_checks.values())
    return {"passed": passed, "pool_checks": pool_checks, "roles": roles, "families": families, "rows": rows}


def main() -> int:
    result = validate()
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
