"""Freeze the independent Unified Phase-A Success v2 calibration inputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_success_v2_construction"
CAMPAIGN = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
SOURCE_MANIFEST = SOURCE / "success_v2_task_manifest.json"
SOURCE_TASKS = SOURCE / "success_v2_tasks.json"
TASK_MANIFEST = ROOT / "task_manifest.json"
TASKS = ROOT / "tasks.json"
SEED_MANIFEST = ROOT / "seed_manifest.json"
RUN_CONFIG = ROOT / "run_config.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    if list((ROOT / "trajectories").glob("*.json")):
        raise RuntimeError("Success v2 has trajectories; inputs are frozen")

    manifest = load(SOURCE_MANIFEST)
    tasks = load(SOURCE_TASKS)
    if len(manifest["tasks"]) != 27 or len(tasks) != 27:
        raise RuntimeError("expected exactly 27 construction tasks")
    if [row["task_id"] for row in manifest["tasks"]] != [row["id"] for row in tasks]:
        raise RuntimeError("manifest/task order mismatch")
    if len({row["id"] for row in tasks}) != 27:
        raise RuntimeError("duplicate task IDs")

    # Exact byte copies preserve the human-reviewed construction inputs.
    TASK_MANIFEST.write_bytes(SOURCE_MANIFEST.read_bytes())
    TASKS.write_bytes(SOURCE_TASKS.read_bytes())

    seeds = {
        row["task_id"]: [2200 + 3 * index + offset for offset in range(3)]
        for index, row in enumerate(manifest["tasks"])
    }
    seed_manifest = {
        "schema_version": "phase_a_success_v2_seeds_1.0",
        "freeze_status": "FROZEN_BEFORE_SUCCESS_V2_ROLLOUTS",
        "selection_method": "deterministic sequential allocation independent of v1 outcomes",
        "rollouts_per_task": 3,
        "uniform_budget": True,
        "seeds": seeds,
    }
    write(SEED_MANIFEST, seed_manifest)

    campaign = load(CAMPAIGN)
    run_config = {
        "benchmark_id": "unified_phase_a_success_v2_coverage_balanced",
        "independent_full_calibration": True,
        "reuses_v1_trajectories": False,
        "task_manifest_sha256": sha256(TASK_MANIFEST),
        "tasks_sha256": sha256(TASKS),
        "seed_manifest_sha256": sha256(SEED_MANIFEST),
        "tasks_path": str(TASKS.relative_to(PROJECT_ROOT)),
        "rollouts_per_task": 3,
        "planned_rollouts": 81,
        "skill": "EMPTY",
        "skill_injection": None,
        "context_manifest": "benchmarks/tau2_governed_evolution/phase_a_context/unified/unified_context_manifest.json",
        "agent": campaign["agent"],
        "user_simulator": campaign["user_simulator"],
        "official_evaluator": campaign["official_evaluator"],
        "compliance_judge": campaign["compliance_judge"],
    }
    write(RUN_CONFIG, run_config)
    (ROOT / "TASK_POOL_FREEZE.md").write_text(
        "# Unified Phase-A Success v2 Runtime Freeze\n\n"
        "The 27-task construction payload and manifest are exact byte copies of the human-reviewed "
        "Success v2 construction. Eighty-one seeds (three per task) were frozen before any v2 rollout. "
        "No Success v1 trajectory or outcome was used to allocate seeds.\n\n"
        f"- Task manifest SHA-256: `{run_config['task_manifest_sha256']}`\n"
        f"- Tasks SHA-256: `{run_config['tasks_sha256']}`\n"
        f"- Seed manifest SHA-256: `{run_config['seed_manifest_sha256']}`\n"
        "- Contexts: `AIRLINE_PHASE_A_UNIFIED_V1`, `RETAIL_PHASE_A_UNIFIED_V1`\n"
        "- Skill: `EMPTY`\n",
        encoding="utf-8",
    )
    print(json.dumps({"tasks": 27, "rollouts": 81, **{k: run_config[k] for k in ("task_manifest_sha256", "tasks_sha256", "seed_manifest_sha256")}}, indent=2))


if __name__ == "__main__":
    main()
