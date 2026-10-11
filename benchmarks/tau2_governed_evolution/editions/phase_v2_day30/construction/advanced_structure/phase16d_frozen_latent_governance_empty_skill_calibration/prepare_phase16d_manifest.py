#!/usr/bin/env python3
"""Create the immutable Phase 16D task-by-seed manifest before any rollout."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[6]
P16C = HERE.parent / "phase16c_latent_governance_variant_family_realization"
CONFIG = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
TASKS = P16C / "tasks/candidate_tasks.json"
POOL = P16C / "latent_governance_variant_family_pool_v1.json"
VISIBILITY = P16C / "latent_visibility_contract_v1.json"
HISTORY = P16C / "historical_evidence_recoverability_contract_v1.json"
EVALUATORS = P16C / "evaluators.py"
GOALS = P16C / "oracle_goal_specs.json"


def load(path):
    return json.loads(path.read_text())


def main():
    target = HERE / "phase16d_calibration_manifest.json"
    assert not target.exists(), "immutable calibration manifest already exists"
    assert not list((HERE / "trajectories").glob("*_started.json")), "rollout already started"
    tasks = load(TASKS)
    pool = load(POOL)
    config = load(CONFIG)
    assert len(tasks) == pool["task_episode_count"] == 11
    assert config["skill"] == "EMPTY" and config["skill_injection"] is None
    family = {row["task_id"]: next(f["family_id"] for f in pool["families"] if row["task_id"] in f["task_ids"])
              for row in pool["candidates"]}
    task_map = {t["id"]: t for t in tasks}
    seeds = iter(range(960190, 960223))
    records = []
    for task_id in sorted(task_map):
        for rollout_index in range(1, 4):
            records.append({"task_id": task_id, "family_id": family[task_id],
                "rollout_index": rollout_index, "seed": next(seeds)})
    assert len(records) == 33 and [x["seed"] for x in records] == list(range(960190, 960223))
    manifest = {"phase": "16D", "name": "Frozen Latent Governance Empty-Skill Calibration",
        "status": "FROZEN_BEFORE_FIRST_ROLLOUT", "candidate_pool": pool["name"],
        "candidate_tasks": 11, "rollouts_per_task": 3, "rollouts_requested": 33,
        "skill": "EMPTY", "skill_injection": None,
        "base_runtime_configuration": config,
        "seed_policy": "sequential continuation after Phase15G 960189; task-major order",
        "recovery_policy": "Only confirmed transport/infra failure may retry the same task, seed, and config; behavioral outcomes never rerun.",
        "no_cross_episode_history_for_base": True, "empirical_learnability_tested": False,
        "formal_admission": False, "Skill_Evolution": False,
        "bounded_feedback_review": "NOT RUN", "records": records}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"records": len(records), "seeds": "960190..960222"}, indent=2))


if __name__ == "__main__":
    main()
