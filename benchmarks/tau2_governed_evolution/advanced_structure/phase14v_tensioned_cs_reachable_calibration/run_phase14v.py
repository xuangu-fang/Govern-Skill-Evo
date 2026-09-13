"""Run exactly six frozen Phase-14V Empty-Skill calibration trajectories."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from benchmarks.tau2_governed_evolution.advanced_structure.phase14_cs_reachable_empty_skill_calibration import run_phase14 as base
from benchmarks.tau2_governed_evolution.advanced_structure.phase14t_tensioned_cs_reachable_realization import context_adapter
from benchmarks.tau2_governed_evolution.advanced_structure.phase14t_tensioned_cs_reachable_realization import evaluators
from src.skill_evolution.information_boundary_v15 import agent_payload


HERE = Path(__file__).resolve().parent
REPO = base.REPO
PHASE14T = HERE.parent / "phase14t_tensioned_cs_reachable_realization"
TASK_SPECS = (
    {"task_id": "travel_request_019", "domain": "airline", "source_candidate_id": "TCS14S_001", "seeds": [960172, 960173, 960174]},
    {"task_id": "travel_request_020", "domain": "airline", "source_candidate_id": "TCS14S_002", "seeds": [960175, 960176, 960177]},
)

load, write, sha = base.load, base.write, base.sha


def protected_files():
    paths = base.protected_files()
    paths += [p for p in PHASE14T.rglob("*") if p.is_file() and "__pycache__" not in str(p)]
    paths += [p for p in REPO.rglob("*") if p.is_file() and "v15" in str(p.relative_to(REPO)).lower() and "__pycache__" not in str(p)]
    return sorted(set(paths))


def preflight():
    formal = load(base.FORMAL / "expanded_benchmark_manifest.json")
    pool = load(PHASE14T / "tensioned_cs_reachable_candidate_pool_v1.json")
    tasks = {row["id"]: base.Task.model_validate(row) for row in load(PHASE14T / "tasks/candidate_tasks.json")}
    expected = {row["task_id"] for row in TASK_SPECS}
    assert formal["total_tasks"] == 54
    assert pool["pool_id"] == "TENSIONED_CS_REACHABLE_CANDIDATE_POOL_V1" and pool["task_count"] == 2
    assert set(tasks) == expected == {row["task_id"] for row in pool["candidates"]}
    assert not expected.intersection(row["id"] for row in load(base.FORMAL / "tasks/expanded_tasks.json"))
    assert [seed for row in TASK_SPECS for seed in row["seeds"]] == list(range(960172, 960178))
    assert not list((HERE / "trajectories").glob("*_started.json")), "Phase 14V trajectories already started"
    config = load(base.CONFIG_SOURCE)
    assert config["skill"] == "EMPTY" and config["skill_injection"] is None
    return formal, pool, tasks, config


def bind_frozen_context(orchestrator, candidate):
    envelope = context_adapter.bind_candidate_context(orchestrator.agent)
    view = agent_payload(envelope)
    expected = load(PHASE14T / "contexts/agent_visible_view.json")
    assert view == expected
    return {
        "context_id": f'{candidate["task_id"]}_PHASE14T_VISIBLE_V1',
        "policy_path": candidate["learner_visible_context_path"],
        "formal_tool_context_id": "phase14t_frozen_native_airline_surface",
        "v15_view_digest": hashlib.sha256(envelope.payload.encode()).hexdigest(),
        "v15_payload_keys": sorted(view),
        "visible_policy_sha256": hashlib.sha256(view["visible_policy"].encode()).hexdigest(),
        "public_tool_schema_sha256": hashlib.sha256(json.dumps(view["public_tools"], sort_keys=True).encode()).hexdigest(),
        "phase14t_snapshot_validated": True,
    }, view


def main():
    formal, pool, tasks, config = preflight()
    before = {str(path.relative_to(REPO)): sha(path) for path in protected_files()}
    write(HERE / "runtime/protected_before.json", before)
    write(HERE / "runtime/run_manifest.json", {
        "phase": "14V",
        "name": "2-Task / 6-Trajectory Tensioned CS-Reachable Empty-Skill Calibration",
        "formal_benchmark": formal["benchmark_id"],
        "formal_benchmark_task_count": 54,
        "candidate_pool": pool["pool_id"],
        "skill": "EMPTY",
        "skill_injection": None,
        "rollouts_per_task": 3,
        "planned_trajectories": 6,
        "tasks": list(TASK_SPECS),
        "seed_scheme": "continue after Phase-14 seeds 960163-960171",
        "base_agent_config_unchanged": True,
        "user_simulator_config_unchanged": True,
        "runtime_unchanged": True,
        "native_db_unchanged": True,
        "success_evaluator": "phase14t.evaluators.evaluate_success",
        "compliance_judge_unchanged": True,
        "information_boundary_version": "v15_learner_safe",
        "formal_admission": False,
        "Skill_Evolution": False,
        "BOUNDED_FEEDBACK_LEARNABILITY_NOT_TESTED": True,
    })
    run_config = copy.deepcopy(config)
    run_config["planned_rollouts"] = 6
    write(HERE / "runtime/run_config.json", run_config)

    candidates = {row["task_id"]: row for row in pool["candidates"]}
    canonical = base.load_authoritative_domain_contexts(REPO / "external/tau2-bench")
    base.HERE = HERE
    base.TASK_SPECS = TASK_SPECS
    base.bind_candidate_context = bind_frozen_context
    base.evaluate_success = evaluators.evaluate_success

    import tau2.utils.llm_utils as llm
    lock = threading.Lock()
    counts = {"agent_user_completion_attempts": 0, "judge_provider_calls": 0}
    original_completion = llm.completion
    original_judge = base.default_judge_caller

    def counted_completion(*args, **kwargs):
        with lock:
            counts["agent_user_completion_attempts"] += 1
            write(HERE / "runtime/model_calls.json", counts)
        return original_completion(*args, **kwargs)

    def counted_judge(*args, **kwargs):
        with lock:
            counts["judge_provider_calls"] += 1
            write(HERE / "runtime/model_calls.json", counts)
        return original_judge(*args, **kwargs)

    llm.completion = counted_completion
    base.default_judge_caller = counted_judge
    rows = []
    jobs = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for spec in TASK_SPECS:
            candidate = candidates[spec["task_id"]]
            task = tasks[spec["task_id"]]
            for index, seed in enumerate(spec["seeds"], 1):
                jobs.append(executor.submit(base.run_one, spec, candidate, task, seed, index, run_config, canonical["airline"]))
        assert len(jobs) == 6
        for future in as_completed(jobs):
            rows.append(future.result())
            rows.sort(key=lambda row: (row["task_id"], row["rollout_index"]))
            write(HERE / "runtime/run_progress.json", rows)
            print(json.dumps({"finished": len(rows), "total": 6, "last": rows[-1]}), flush=True)

    after = {str(path.relative_to(REPO)): sha(path) for path in protected_files()}
    write(HERE / "runtime/protected_after.json", after)
    summary = {
        "planned": 6,
        "completed": sum(row["status"] == "completed" for row in rows),
        "errors": sum(row["status"] == "error" for row in rows),
        "refused_reruns": sum(row["status"] == "REFUSED_RERUN" for row in rows),
        "trajectory_reruns": 0,
        "protected_files_unchanged": before == after,
        "results": rows,
        "model_calls": counts,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    write(HERE / "runtime/run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    assert summary["completed"] == 6 and summary["errors"] == 0
    assert summary["refused_reruns"] == 0 and summary["protected_files_unchanged"]


if __name__ == "__main__":
    main()
