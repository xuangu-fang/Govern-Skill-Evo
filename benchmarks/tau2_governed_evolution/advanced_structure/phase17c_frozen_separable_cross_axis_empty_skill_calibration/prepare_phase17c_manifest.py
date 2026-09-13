#!/usr/bin/env python3
"""Create the immutable Phase 17C task-by-seed manifest before any rollout."""

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
P17B = HERE.parent / "phase17b_separable_cross_axis_v2_clean_realization"
CONFIG = REPO / "benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/calibration/run_config.json"


def load(path: Path):
    return json.loads(path.read_text())


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def combined_hash(paths):
    return stable({str(path.relative_to(REPO)): sha(path) for path in paths})


def main():
    target = HERE / "phase17c_calibration_manifest.json"
    assert not target.exists(), "immutable Phase 17C calibration manifest already exists"
    assert not list((HERE / "trajectories").glob("*_started.json")), "rollout already started"

    tasks_path = P17B / "tasks/candidate_tasks.json"
    pool_path = P17B / "separable_cross_axis_family_pool_v2.json"
    goals_path = P17B / "oracle_goal_specs.json"
    evaluator_path = P17B / "evaluators.py"
    boundary_path = P17B / "cross_axis_information_boundary_audit.json"
    tasks = load(tasks_path)
    pool = load(pool_path)
    config = load(CONFIG)
    assert len(tasks) == pool["task_count"] == 2
    assert config["skill"] == "EMPTY" and config["skill_injection"] is None

    task_map = {row["id"]: row for row in tasks}
    family_map = {row["task_id"]: row for row in pool["families"]}
    seeds = iter(range(960223, 960229))
    records = []
    evaluator_hash = combined_hash([evaluator_path, goals_path])
    for task_id in sorted(task_map):
        family = family_map[task_id]
        context_path = P17B / family["visible_policy_path"]
        family_path = P17B / f'{family["family_id"].lower()}_realization.json'
        information_boundary_hash = combined_hash([boundary_path, context_path])
        for rollout_index in range(1, 4):
            records.append({
                "task_id": task_id,
                "family_id": family["family_id"],
                "rollout_index": rollout_index,
                "seed": next(seeds),
                "task_hash": stable(task_map[task_id]),
                "base_config_hash": stable(config),
                "evaluator_hash": evaluator_hash,
                "information_boundary_hash": information_boundary_hash,
                "phase17b_family_hash": sha(family_path),
            })

    manifest = {
        "phase": "17C",
        "name": "Frozen Separable Cross-axis Empty-Skill Calibration",
        "status": "FROZEN_BEFORE_FIRST_BEHAVIORAL_ROLLOUT",
        "candidate_tasks": 2,
        "rollouts_per_task": 3,
        "rollouts_requested": 6,
        "skill": "EMPTY",
        "skill_injection": None,
        "base_runtime_configuration": config,
        "seed_policy": "sequential continuation after Phase16D seed 960222; immutable task-major order",
        "freeze_sources": {
            "tasks": sha(tasks_path),
            "family_pool": sha(pool_path),
            "oracle_goal_specs": sha(goals_path),
            "evaluators": sha(evaluator_path),
            "information_boundary_audit": sha(boundary_path),
            "base_config": sha(CONFIG),
            "visible_policy_036": sha(P17B / "contexts/travel_request_036_visible_policy.md"),
            "visible_policy_037": sha(P17B / "contexts/travel_request_037_visible_policy.md"),
            "family_001": sha(P17B / "scvf17b_001_realization.json"),
            "family_002": sha(P17B / "scvf17b_002_realization.json"),
        },
        "recovery_policy": "Only confirmed infra/transport failure may retry the same task, seed, and frozen config; behavioral outcomes never rerun.",
        "base_prior": "ordinary task prompt + frozen visible policy + public tool schemas only",
        "phase17b_fixtures_visible_to_base": False,
        "cross_episode_history_visible_to_base": False,
        "empirical_learner_recoverability_tested": False,
        "formal_admission": False,
        "Skill_Evolution": False,
        "bounded_feedback_review": "NOT RUN",
        "records": records,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    digest = sha(target)
    (HERE / "phase17c_calibration_manifest.sha256").write_text(
        digest + "  phase17c_calibration_manifest.json\n"
    )
    print(json.dumps({"manifest_sha256": digest, "records": 6, "seeds": "960223..960228"}, indent=2))


if __name__ == "__main__":
    main()
