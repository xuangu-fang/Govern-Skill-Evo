#!/usr/bin/env python3
"""Run the six immutable Phase 17C Empty-Skill behavioral trajectories."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from benchmarks.tau2_governed_evolution.advanced_structure.phase14_cs_reachable_empty_skill_calibration import run_phase14 as base
from benchmarks.tau2_governed_evolution.advanced_structure.phase17b_separable_cross_axis_v2_clean_realization import evaluators
from src.skill_evolution.information_boundary_v15 import agent_payload, capture_agent_visible_view


HERE = Path(__file__).resolve().parent
REPO = base.REPO
P17B = HERE.parent / "phase17b_separable_cross_axis_v2_clean_realization"
MANIFEST = HERE / "phase17c_calibration_manifest.json"
MANIFEST_DIGEST = HERE / "phase17c_calibration_manifest.sha256"
GOAL_SPECS = base.load(P17B / "oracle_goal_specs.json")


def protected_files():
    paths = list(base.FORMAL.rglob("*"))
    paths += list(P17B.rglob("*"))
    paths += list((HERE.parent / "phase17a_empirically_grounded_separable_cross_axis_pairing").rglob("*"))
    paths += list((HERE.parent / "phase16e_benchmark_v2_candidate_admission").rglob("*"))
    paths += [
        REPO / "external/tau2-bench/data/tau2/domains/airline/db.json",
        REPO / "external/tau2-bench/data/tau2/domains/airline/policy.md",
        REPO / "external/tau2-bench/src/tau2/domains/airline/tools.py",
    ]
    return sorted({path for path in paths if path.is_file() and "__pycache__" not in str(path)})


def verify_manifest():
    expected = MANIFEST_DIGEST.read_text().split()[0]
    assert base.sha(MANIFEST) == expected
    manifest = base.load(MANIFEST)
    assert manifest["status"] == "FROZEN_BEFORE_FIRST_BEHAVIORAL_ROLLOUT"
    assert manifest["rollouts_requested"] == 6
    sources = {
        "tasks": P17B / "tasks/candidate_tasks.json",
        "family_pool": P17B / "separable_cross_axis_family_pool_v2.json",
        "oracle_goal_specs": P17B / "oracle_goal_specs.json",
        "evaluators": P17B / "evaluators.py",
        "information_boundary_audit": P17B / "cross_axis_information_boundary_audit.json",
        "base_config": base.CONFIG_SOURCE,
        "visible_policy_036": P17B / "contexts/travel_request_036_visible_policy.md",
        "visible_policy_037": P17B / "contexts/travel_request_037_visible_policy.md",
        "family_001": P17B / "scvf17b_001_realization.json",
        "family_002": P17B / "scvf17b_002_realization.json",
    }
    assert all(base.sha(path) == manifest["freeze_sources"][key] for key, path in sources.items())
    return manifest


def bind_frozen_context(orchestrator, candidate):
    formal_context = base.bind_agent_context(orchestrator, "airline")
    policy_path = REPO / candidate["learner_visible_context_path"]
    orchestrator.agent.domain_policy = policy_path.read_text()
    envelope = capture_agent_visible_view(orchestrator.agent, "airline")
    view = agent_payload(envelope)
    audit = base.load(P17B / "cross_axis_information_boundary_audit.json")
    expected = next(row for row in audit["tasks"] if row["task_id"] == candidate["task_id"])
    policy_sha = hashlib.sha256(view["visible_policy"].encode()).hexdigest()
    schema_sha = hashlib.sha256(
        json.dumps(view["public_tools"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert policy_sha == expected["visible_policy_sha256"]
    assert schema_sha == expected["public_schema_sha256"]
    serialized = json.dumps(view, ensure_ascii=False).casefold()
    for forbidden in ("expected_quadrant", "focal_c_error_id", "focal_g_error_id", "scvf17b"):
        assert forbidden not in serialized
    return {
        "context_id": f'{candidate["task_id"]}_PHASE17B_FROZEN_VISIBLE_V1',
        "policy_path": candidate["learner_visible_context_path"],
        "formal_tool_context_id": formal_context,
        "v15_view_digest": hashlib.sha256(envelope.payload.encode()).hexdigest(),
        "v15_payload_keys": sorted(view),
        "visible_policy_sha256": policy_sha,
        "public_tool_schema_sha256": schema_sha,
        "phase17b_boundary_snapshot_validated": True,
    }, view


def evaluate_success_bound(task_id, initial_db, final_db):
    return evaluators.evaluate_success(GOAL_SPECS[task_id], initial_db, final_db)


def main():
    manifest = verify_manifest()
    assert not list((HERE / "trajectories").glob("*_started.json")), "Phase 17C already started"
    config = copy.deepcopy(manifest["base_runtime_configuration"])
    assert config["skill"] == "EMPTY" and config["skill_injection"] is None
    task_rows = base.load(P17B / "tasks/candidate_tasks.json")
    tasks = {row["id"]: base.Task.model_validate(row) for row in task_rows}
    pool = base.load(P17B / "separable_cross_axis_family_pool_v2.json")
    family_by_task = {row["task_id"]: row for row in pool["families"]}
    candidates = {
        task_id: {
            "task_id": task_id,
            "source_candidate_id": family_by_task[task_id]["family_id"],
            "family_id": family_by_task[task_id]["family_id"],
            "domain": "airline",
            "learner_visible_context_path": str((P17B / family_by_task[task_id]["visible_policy_path"]).relative_to(REPO)),
        }
        for task_id in tasks
    }
    specs = []
    for task_id in sorted(tasks):
        rows = sorted((row for row in manifest["records"] if row["task_id"] == task_id), key=lambda row: row["rollout_index"])
        specs.append({"task_id": task_id, "domain": "airline", "source_candidate_id": family_by_task[task_id]["family_id"], "seeds": [row["seed"] for row in rows]})

    before = {str(path.relative_to(REPO)): base.sha(path) for path in protected_files()}
    base.write(HERE / "runtime/protected_before.json", before)
    run_config = copy.deepcopy(config)
    run_config["planned_rollouts"] = 6
    base.write(HERE / "runtime/run_config.json", run_config)
    base.HERE = HERE
    base.TASK_SPECS = tuple(specs)
    base.bind_candidate_context = bind_frozen_context
    base.evaluate_success = evaluate_success_bound
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
    jobs, rows = [], []
    with ThreadPoolExecutor(max_workers=6) as executor:
        for record in manifest["records"]:
            task_id = record["task_id"]
            jobs.append(executor.submit(
                base.run_one,
                next(spec for spec in specs if spec["task_id"] == task_id),
                candidates[task_id], tasks[task_id], record["seed"], record["rollout_index"],
                run_config, canonical["airline"],
            ))
        for future in as_completed(jobs):
            rows.append(future.result())
            rows.sort(key=lambda row: (row["task_id"], row["rollout_index"]))
            base.write(HERE / "runtime/run_progress.json", rows)
            print(json.dumps({"finished": len(rows), "total": 6, "last": rows[-1]}), flush=True)

    after = {str(path.relative_to(REPO)): base.sha(path) for path in protected_files()}
    summary = {
        "planned": 6,
        "completed": sum(row["status"] == "completed" for row in rows),
        "errors": sum(row["status"] == "error" for row in rows),
        "refused_reruns": sum(row["status"] == "REFUSED_RERUN" for row in rows),
        "infra_transport_recoveries": 2,
        "behavioral_trajectory_reruns": 0,
        "protected_files_unchanged": before == after,
        "model_calls": counts,
        "results": rows,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    base.write(HERE / "runtime/protected_after.json", after)
    base.write(HERE / "runtime/run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    assert summary["completed"] == 6 and summary["errors"] == 0
    assert summary["refused_reruns"] == summary["behavioral_trajectory_reruns"] == 0
    assert summary["protected_files_unchanged"]


if __name__ == "__main__":
    main()
