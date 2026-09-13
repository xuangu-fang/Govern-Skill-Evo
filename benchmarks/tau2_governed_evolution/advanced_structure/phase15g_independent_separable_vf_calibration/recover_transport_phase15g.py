"""Recover one pre-trajectory Phase 15G provider failure without rerunning a trajectory."""

from __future__ import annotations

import datetime
import json
import threading
from pathlib import Path

from benchmarks.tau2_governed_evolution.advanced_structure.phase15g_independent_separable_vf_calibration import (
    run_phase15g as run,
)


HERE = run.HERE


def main():
    stem = "travel_request_024_02"
    trajectory_dir = HERE / "trajectories"
    started = trajectory_dir / f"{stem}_started.json"
    error_path = trajectory_dir / f"{stem}_error.json"
    result_path = trajectory_dir / f"{stem}.json"
    raw_path = trajectory_dir / f"{stem}_raw.json"
    failure = run.load(error_path)
    assert failure["error_type"] == "RateLimitError"
    assert failure["raw_exists"] is False and not raw_path.exists()
    assert not result_path.exists()

    protected_before = {
        str(path.relative_to(run.REPO)): run.sha(path) for path in run.protected_files()
    }
    recovery_dir = HERE / "runtime/transport_failures/attempt_01"
    recovery_dir.mkdir(parents=True, exist_ok=True)
    started.replace(recovery_dir / started.name)
    error_path.replace(recovery_dir / error_path.name)

    initial_summary = run.load(HERE / "runtime/run_summary.json")
    run.write(HERE / "runtime/run_summary_initial_attempt.json", initial_summary)
    run.write(
        HERE / "runtime/transport_recovery_manifest.json",
        {
            "task_id": "travel_request_024",
            "rollout_index": 2,
            "seed": 960188,
            "reason": "RateLimitError before any raw trajectory existed",
            "original_error_sha256": run.sha(
                recovery_dir / "travel_request_024_02_error.json"
            ),
            "original_started_sha256": run.sha(
                recovery_dir / "travel_request_024_02_started.json"
            ),
            "raw_trajectory_existed_before_recovery": False,
            "behavior_conditioned_rerun": False,
            "trajectory_rerun": False,
            "transport_recovery_attempts_allowed": 1,
        },
    )

    pool = run.load(PHASE15F / "independent_separable_vf_candidate_pool_v1.json")
    candidate = next(
        row for row in pool["candidates"] if row["task_id"] == "travel_request_024"
    )
    task = run.base.Task.model_validate(candidate["task"])
    spec = next(
        row for row in run.TASK_SPECS if row["task_id"] == "travel_request_024"
    )
    config = run.load(run.base.CONFIG_SOURCE)
    config["planned_rollouts"] = 6
    canonical = run.base.load_authoritative_domain_contexts(
        run.REPO / "external/tau2-bench"
    )
    run.base.HERE = HERE
    run.base.TASK_SPECS = run.TASK_SPECS
    run.base.bind_candidate_context = run.bind_frozen_context
    run.base.evaluate_success = run.evaluate_success_bound

    import tau2.utils.llm_utils as llm

    lock = threading.Lock()
    counts = {"agent_user_completion_attempts": 0, "judge_provider_calls": 0}
    original_completion = llm.completion
    original_judge = run.base.default_judge_caller

    def counted_completion(*args, **kwargs):
        with lock:
            counts["agent_user_completion_attempts"] += 1
            run.write(HERE / "runtime/transport_recovery_model_calls.json", counts)
        return original_completion(*args, **kwargs)

    def counted_judge(*args, **kwargs):
        with lock:
            counts["judge_provider_calls"] += 1
            run.write(HERE / "runtime/transport_recovery_model_calls.json", counts)
        return original_judge(*args, **kwargs)

    llm.completion = counted_completion
    run.base.default_judge_caller = counted_judge
    row = run.base.run_one(
        spec,
        candidate,
        task,
        960188,
        2,
        config,
        canonical["airline"],
    )
    assert row["status"] == "completed", row

    protected_after = {
        str(path.relative_to(run.REPO)): run.sha(path) for path in run.protected_files()
    }
    assert protected_before == protected_after
    final_results = [
        item
        for item in initial_summary["results"]
        if not (
            item["task_id"] == "travel_request_024" and item["rollout_index"] == 2
        )
    ]
    final_results.append(row)
    final_results.sort(key=lambda item: (item["task_id"], item["rollout_index"]))
    final_summary = {
        **initial_summary,
        "completed": 6,
        "errors": 0,
        "results": final_results,
        "initial_transport_errors": 1,
        "TRANSPORT_BUG": 1,
        "transport_recoveries": 1,
        "trajectory_reruns": 0,
        "protected_files_unchanged": True,
        "initial_batch_model_calls": initial_summary["model_calls"],
        "transport_recovery_model_calls": counts,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    run.write(HERE / "runtime/run_summary.json", final_summary)
    run.write(
        HERE / "runtime/transport_recovery_result.json",
        {
            "status": "RECOVERED",
            "result": row,
            "transport_recovery_model_calls": counts,
            "protected_files_unchanged": True,
            "trajectory_reruns": 0,
        },
    )
    print(json.dumps(final_summary, ensure_ascii=False, indent=2))


PHASE15F = run.PHASE15F


if __name__ == "__main__":
    main()
