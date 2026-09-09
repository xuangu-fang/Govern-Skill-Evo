"""Static validation for the frozen Unified Phase-A Success v1 pool."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable
from benchmarks.tau2_governed_evolution.phase_a_context.validate_unified_phase_a_context import validate as validate_context
from benchmarks.tau2_governed_evolution.phase_a_success_v1.build_task_pool import (
    CAPABILITY_TASKS,
    CAMPAIGN,
    CONTEXT_IDS,
    DIRECTORY,
    NATIVE_RETAIL_TASKS,
    OPERATIONAL_TASKS,
    PROJECT_ROOT,
    RUN_CONFIG,
    SEED_MANIFEST,
    TASK_MANIFEST,
    TASKS_PATH,
    V0_TASKS,
)


ensure_tau2_importable()
from tau2.data_model.tasks import Task  # noqa: E402


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    manifest = _load(TASK_MANIFEST)
    values = _load(TASKS_PATH)
    tasks = {row["id"]: Task.model_validate(row) for row in values}
    if len(values) != len(tasks):
        raise ValueError("duplicate task id")
    return manifest, tasks


def validate() -> dict[str, Any]:
    context = validate_context()
    manifest, tasks = load_suite()
    seeds = _load(SEED_MANIFEST)
    run_config = _load(RUN_CONFIG)
    campaign = _load(CAMPAIGN)
    source_cache: dict[str, dict[str, Any]] = {}
    rows = []
    for spec in manifest["tasks"]:
        task = tasks[spec["task_id"]]
        source_artifact = spec["source_artifact"]
        if source_artifact not in source_cache:
            source_cache[source_artifact] = {
                row["id"]: row for row in _load(PROJECT_ROOT / source_artifact)
            }
        source_task = source_cache[source_artifact][spec["task_id"]]
        checks = {
            "source_task_unchanged": task.model_dump(mode="json") == Task.model_validate(source_task).model_dump(mode="json"),
            "domain_consistent": task.user_scenario.instructions.domain == spec["domain"],
            "complete_upfront": spec["phase_a_complete_upfront"] is True,
            "stable_intent": spec["phase_a_stable_intent"] is True,
            "procedure_neutral": spec["procedure_neutral"] is True,
            "valid_role": spec["task_role"] in {"KNOWN_ANCHOR", "PROTECTED_GOOD_CASE", "ORDINARY_CLEAN"},
            "unified_context_only": spec["context_id"] == CONTEXT_IDS[spec["domain"]],
            "reward_basis_present": bool(task.evaluation_criteria.reward_basis),
            "three_fixed_seeds": len(seeds["seeds"][spec["task_id"]]) == 3,
        }
        rows.append({"task_id": spec["task_id"], "checks": checks, "passed": all(checks.values())})

    domain_counts = Counter(row["domain"] for row in manifest["tasks"])
    role_counts = Counter(row["task_role"] for row in manifest["tasks"])
    all_seeds = [seed for values in seeds["seeds"].values() for seed in values]
    pool_checks = {
        "unified_context_valid": context["UNIFIED_PHASE_A_CONTEXT_VERDICT"] == "READY_FOR_SUCCESS_V1",
        "frozen_before_rollouts": manifest["freeze_status"] == "FROZEN_BEFORE_UNIFIED_V1_ROLLOUTS",
        "outcome_blind": manifest["outcome_blind"] is True,
        "task_count_24": len(manifest["tasks"]) == 24,
        "domain_balance_12_12": domain_counts == {"airline": 12, "retail": 12},
        "role_vocabulary_only": set(role_counts) == {"KNOWN_ANCHOR", "PROTECTED_GOOD_CASE", "ORDINARY_CLEAN"},
        "unique_task_ids": len(tasks) == 24,
        "seed_keys_exact": set(seeds["seeds"]) == set(tasks),
        "uniform_three_rollouts": seeds["rollouts_per_task"] == 3 and seeds["uniform_budget"] is True,
        "seeds_unique_and_predeclared": len(all_seeds) == 72 and len(set(all_seeds)) == 72,
        "manifest_hash_bound": run_config["task_manifest_sha256"] == _sha256(TASK_MANIFEST),
        "seed_hash_bound": run_config["seed_manifest_sha256"] == _sha256(SEED_MANIFEST),
        "empty_skill_only": run_config["skill"] == "EMPTY" and run_config["skill_injection"] is None,
        "base_config_reused": run_config["agent"] == campaign["agent"] and run_config["user_simulator"] == campaign["user_simulator"],
        "three_rollouts_config": run_config["rollouts_per_task"] == 3,
    }
    passed = all(row["passed"] for row in rows) and all(pool_checks.values())
    return {
        "passed": passed,
        "domains": dict(domain_counts),
        "roles": dict(role_counts),
        "pool_checks": pool_checks,
        "rows": rows,
    }


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
