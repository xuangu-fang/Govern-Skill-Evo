#!/usr/bin/env python3
"""Run frozen matched-seed Phase 17 axis-specific Reference Skill treatments."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from benchmarks.tau2_governed_evolution.editions.phase_v2_day30.construction.advanced_structure.phase14_cs_reachable_empty_skill_calibration import run_phase14 as base
from benchmarks.tau2_governed_evolution.editions.phase_v2_day30.construction.advanced_structure.phase17c_frozen_separable_cross_axis_empty_skill_calibration import run_phase17c as p17c


HERE = Path(__file__).resolve().parent
REPO = base.REPO
P17B = p17c.P17B
P17C = P17B.parent / "phase17c_frozen_separable_cross_axis_empty_skill_calibration"
SKILLS = HERE / "reference_skills"
TREATMENTS = [
    {"id": "036_C_ONLY", "task_id": "travel_request_036", "skill": "C_CERTIFICATE_ALLOCATION"},
    {"id": "036_G_ONLY", "task_id": "travel_request_036", "skill": "G_BASIC_STATE_TRANSITION"},
    {"id": "036_JOINT", "task_id": "travel_request_036", "skill": "JOINT_CERTIFICATE_AND_BASIC"},
    {"id": "037_C_ONLY", "task_id": "travel_request_037", "skill": "C_CERTIFICATE_ALLOCATION"},
]


def protected_files() -> list[Path]:
    roots = [P17B, P17C, REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/benchmark"]
    return sorted({p for root in roots for p in root.rglob("*") if p.is_file() and "__pycache__" not in str(p)})


def aggregate_hash(rows: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def main() -> None:
    frozen = base.load(P17C / "phase17c_calibration_manifest.json")
    assert frozen["status"] == "FROZEN_BEFORE_FIRST_BEHAVIORAL_ROLLOUT"
    assert not list((HERE / "treatments").glob("**/*_started.json")), "Axis experiment already started; immutable rerun refused"
    tasks = {row["id"]: base.Task.model_validate(row) for row in base.load(P17B / "tasks/candidate_tasks.json")}
    pool = base.load(P17B / "separable_cross_axis_family_pool_v2.json")
    family_by_task = {row["task_id"]: row for row in pool["families"]}
    e0_by_task = {}
    for task_id in tasks:
        e0_by_task[task_id] = sorted((r for r in frozen["records"] if r["task_id"] == task_id), key=lambda r: r["rollout_index"])
        assert len(e0_by_task[task_id]) == 3

    skill_hashes = {p.stem: base.sha(p) for p in sorted(SKILLS.glob("*.md"))}
    records = [
        {
            "treatment": treatment["id"], "task_id": treatment["task_id"],
            "family_id": family_by_task[treatment["task_id"]]["family_id"],
            "skill_id": treatment["skill"], "skill_sha256": skill_hashes[treatment["skill"]],
            "rollout_index": e0["rollout_index"], "seed": e0["seed"],
            "paired_e0_task_hash": e0["task_hash"], "paired_e0_config_hash": e0["base_config_hash"],
        }
        for treatment in TREATMENTS for e0 in e0_by_task[treatment["task_id"]]
    ]
    assert len(records) == 12
    before = {str(p.relative_to(REPO)): base.sha(p) for p in protected_files()}
    manifest = {
        "schema_version": "phase17_axis_reference_skill_necessity_v1",
        "status": "FROZEN_BEFORE_FIRST_ROLLOUT",
        "design": "Matched E0 task/index/seed/config; 036 gets C-only, G-only, Joint; 037 gets C-only",
        "rollouts_requested": 12,
        "treatments": TREATMENTS,
        "skill_scope": "No task IDs, entity/payment/flight IDs, dates, prices, budgets, or oracle outputs",
        "skill_sha256": skill_hashes,
        "records": records,
        "protected_before": {"count": len(before), "aggregate_sha256": aggregate_hash(before)},
        "recovery_policy": "Only confirmed pre-behavioral infrastructure failure may retry the identical record; behavioral outcomes are immutable.",
    }
    base.write(HERE / "axis_reference_manifest.json", manifest)
    base.write(HERE / "runtime/protected_before.json", before)

    config = copy.deepcopy(frozen["base_runtime_configuration"])
    config["skill"] = "AXIS_MINIMAL_REFERENCE_SKILL"
    config["skill_injection"] = "manual_skill_path"
    config["planned_rollouts"] = 12
    base.write(HERE / "runtime/run_config.json", config)
    original_config = base._config

    def reference_config(campaign, spec, seed):
        run_config = original_config(campaign, spec, seed)
        run_config.agent = "llm_agent_manual_skill"
        run_config.llm_args_agent = dict(run_config.llm_args_agent)
        run_config.llm_args_agent["manual_skill_path"] = str((SKILLS / f"{spec['skill_id']}.md").resolve())
        return run_config

    base._config = reference_config
    base.bind_candidate_context = p17c.bind_frozen_context
    base.evaluate_success = p17c.evaluate_success_bound
    canonical = base.load_authoritative_domain_contexts(REPO / "external/tau2-bench")

    import tau2.utils.llm_utils as llm
    lock = threading.Lock()
    counts = {"agent_user_completion_attempts": 0, "judge_provider_calls": 0}
    original_completion = llm.completion
    original_judge = base.default_judge_caller

    def counted_completion(*args, **kwargs):
        with lock:
            counts["agent_user_completion_attempts"] += 1
            base.write(HERE / "runtime/model_calls.json", counts)
        return original_completion(*args, **kwargs)

    def counted_judge(*args, **kwargs):
        with lock:
            counts["judge_provider_calls"] += 1
            base.write(HERE / "runtime/model_calls.json", counts)
        return original_judge(*args, **kwargs)

    llm.completion = counted_completion
    base.default_judge_caller = counted_judge
    progress = []
    for treatment in TREATMENTS:
        task_id = treatment["task_id"]
        family = family_by_task[task_id]
        candidate = {
            "task_id": task_id, "source_candidate_id": family["family_id"],
            "family_id": family["family_id"], "domain": "airline",
            "learner_visible_context_path": str((P17B / family["visible_policy_path"]).relative_to(REPO)),
        }
        spec = {
            "task_id": task_id, "domain": "airline", "source_candidate_id": family["family_id"],
            "skill_id": treatment["skill"], "seeds": [r["seed"] for r in e0_by_task[task_id]],
        }
        treatment_root = HERE / "treatments" / treatment["id"]
        base.HERE = treatment_root
        jobs = [
            (spec, candidate, tasks[task_id], row["seed"], row["rollout_index"], config, canonical["airline"])
            for row in e0_by_task[task_id]
        ]
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(base.run_one, *job) for job in jobs]
            for future in as_completed(futures):
                result = future.result()
                if result["status"] == "completed":
                    path = Path(result["path"])
                    artifact = base.load(path)
                    artifact.update({
                        "skill": "AXIS_MINIMAL_REFERENCE_SKILL",
                        "skill_id": treatment["skill"],
                        "skill_sha256": skill_hashes[treatment["skill"]],
                        "treatment": treatment["id"],
                        "paired_e0_seed": artifact["seed"],
                    })
                    base.write(path, artifact)
                progress.append({"treatment": treatment["id"], **result})
                progress.sort(key=lambda x: (x["treatment"], x["rollout_index"]))
                base.write(HERE / "runtime/run_progress.json", progress)
                print(json.dumps({"finished": len(progress), "total": 12, "treatment": treatment["id"], "result": result}), flush=True)

    after = {str(p.relative_to(REPO)): base.sha(p) for p in protected_files()}
    summary = {
        "planned": 12,
        "completed": sum(r["status"] == "completed" for r in progress),
        "errors": sum(r["status"] == "error" for r in progress),
        "refused_reruns": sum(r["status"] == "REFUSED_RERUN" for r in progress),
        "behavioral_trajectory_reruns": 0,
        "protected_files_unchanged": before == after,
        "model_calls": counts,
        "results": progress,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    base.write(HERE / "runtime/protected_after.json", after)
    base.write(HERE / "runtime/run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if summary["completed"] != 12 or summary["errors"] or summary["refused_reruns"] or not summary["protected_files_unchanged"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
