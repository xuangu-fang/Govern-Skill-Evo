"""Freeze the Compliance Boundary Rollout inputs before any model call."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_compliance_boundary_completion"
SOURCE_MANIFEST = SOURCE / "compliance_boundary_manifest.json"
SOURCE_TASKS = SOURCE / "compliance_boundary_tasks.json"
CAMPAIGN = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    trajectories = ROOT / "trajectories"
    if trajectories.exists() and any(trajectories.glob("*.json")):
        raise RuntimeError("Boundary rollout already has trajectories; inputs are frozen")

    manifest = load(SOURCE_MANIFEST)
    tasks = load(SOURCE_TASKS)
    ids = [row["task_id"] for row in manifest["tasks"]]
    if len(ids) != 3 or ids != [row["id"] for row in tasks] or len(set(ids)) != 3:
        raise RuntimeError("expected the three reviewed boundary tasks in matching order")

    task_manifest = ROOT / "task_manifest.json"
    task_payload = ROOT / "tasks.json"
    task_manifest.write_bytes(SOURCE_MANIFEST.read_bytes())
    task_payload.write_bytes(SOURCE_TASKS.read_bytes())

    seeds = {
        task_id: [2281 + 3 * index + offset for offset in range(3)]
        for index, task_id in enumerate(ids)
    }
    seed_manifest = {
        "schema_version": "phase_a_compliance_boundary_seeds_1.0",
        "freeze_status": "FROZEN_BEFORE_BOUNDARY_ROLLOUT",
        "selection_method": "deterministic sequential allocation after Success-v2 seed range; independent of all outcomes",
        "rollouts_per_task": 3,
        "uniform_budget": True,
        "seeds": seeds,
    }
    seed_path = ROOT / "seed_manifest.json"
    write(seed_path, seed_manifest)

    campaign = load(CAMPAIGN)
    config = {
        "benchmark_id": "phase_a_compliance_boundary_rollout_v1",
        "task_manifest_sha256": sha256(task_manifest),
        "tasks_sha256": sha256(task_payload),
        "seed_manifest_sha256": sha256(seed_path),
        "tasks": 3,
        "rollouts_per_task": 3,
        "planned_rollouts": 9,
        "skill": "EMPTY",
        "skill_injection": None,
        "context_id": "AIRLINE_PHASE_A_UNIFIED_V1",
        "context_manifest": "benchmarks/tau2_governed_evolution/phase_a_context/unified/unified_context_manifest.json",
        "agent": campaign["agent"],
        "user_simulator": campaign["user_simulator"],
        "official_evaluator": campaign["official_evaluator"],
        "compliance_judge": campaign["compliance_judge"],
        "construction_inputs_unchanged": True,
    }
    write(ROOT / "run_config.json", config)
    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
