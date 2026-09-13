"""Run exactly six frozen Phase 15G Empty-Skill calibration trajectories."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from benchmarks.tau2_governed_evolution.advanced_structure.phase14_cs_reachable_empty_skill_calibration import (
    run_phase14 as base,
)
from benchmarks.tau2_governed_evolution.advanced_structure.phase15f_independent_cross_axis_realization import (
    evaluators,
)
from src.skill_evolution.information_boundary_v15 import (
    INFORMATION_BOUNDARY_VERSION,
    LEARNER_SETTING,
    agent_payload,
    capture_agent_visible_view,
)


HERE = Path(__file__).resolve().parent
REPO = base.REPO
PHASE15F = HERE.parent / "phase15f_independent_cross_axis_realization"
NATIVE_POLICY = REPO / "external/tau2-bench/data/tau2/domains/airline/policy.md"
TASK_SPECS = (
    {
        "task_id": "travel_request_023",
        "domain": "airline",
        "source_candidate_id": "IG15E_001",
        "seeds": [960184, 960185, 960186],
    },
    {
        "task_id": "travel_request_024",
        "domain": "airline",
        "source_candidate_id": "IG15E_002",
        "seeds": [960187, 960188, 960189],
    },
)

load, write, sha = base.load, base.write, base.sha
GOAL_SPECS = load(PHASE15F / "oracle_goal_specs.json")


def protected_files():
    paths = base.protected_files()
    paths += [
        path
        for path in PHASE15F.rglob("*")
        if path.is_file() and "__pycache__" not in str(path)
    ]
    paths += [
        path
        for path in REPO.rglob("*")
        if path.is_file()
        and "v15" in str(path.relative_to(REPO)).lower()
        and "__pycache__" not in str(path)
    ]
    return sorted(set(paths))


def preflight():
    formal = load(base.FORMAL / "expanded_benchmark_manifest.json")
    formal_tasks = load(base.FORMAL / "tasks/expanded_tasks.json")
    pool = load(PHASE15F / "independent_separable_vf_candidate_pool_v1.json")
    tasks = {
        row["task_id"]: base.Task.model_validate(row["task"])
        for row in pool["candidates"]
    }
    expected = {row["task_id"] for row in TASK_SPECS}
    assert formal["total_tasks"] == len(formal_tasks) == 54
    assert pool["pool_id"] == "INDEPENDENT_SEPARABLE_VF_CANDIDATE_POOL_V1"
    assert pool["task_count"] == 2 and pool["status"] == "PRE_CALIBRATION"
    assert set(tasks) == expected == {row["task_id"] for row in pool["candidates"]}
    assert not expected.intersection(row["id"] for row in formal_tasks)
    assert [seed for row in TASK_SPECS for seed in row["seeds"]] == list(
        range(960184, 960190)
    )
    assert not list((HERE / "trajectories").glob("*_started.json")), (
        "Phase 15G trajectories already started"
    )
    config = load(base.CONFIG_SOURCE)
    assert config["skill"] == "EMPTY" and config["skill_injection"] is None
    assert config["agent"]["model"] == "openai/deepseek-v4-flash"
    assert config["user_simulator"]["model"] == "openai/deepseek-v4-flash"
    assert config["compliance_judge"]["model"] == "openai/deepseek-v4-pro"
    return formal, pool, tasks, config


def bind_frozen_context(orchestrator, candidate):
    formal_context_id = base.bind_agent_context(orchestrator, "airline")
    orchestrator.agent.domain_policy = NATIVE_POLICY.read_text()
    envelope = capture_agent_visible_view(orchestrator.agent, "airline")
    view = agent_payload(envelope)
    phase15f_audit = load(PHASE15F / "independent_vf_information_boundary_audit.json")
    expected = phase15f_audit["public_surface"]
    assert hashlib.sha256(view["visible_policy"].encode()).hexdigest() == expected[
        "policy_sha256"
    ]
    assert len(view["public_tools"]) == expected["public_tool_count"]
    assert [item["function"]["name"] for item in view["public_tools"]] == expected[
        "public_tool_names"
    ]
    return {
        "context_id": f'{candidate["task_id"]}_PHASE15F_VISIBLE_V1',
        "policy_path": str(NATIVE_POLICY.relative_to(REPO)),
        "formal_tool_context_id": formal_context_id,
        "v15_view_digest": hashlib.sha256(envelope.payload.encode()).hexdigest(),
        "v15_payload_keys": sorted(view),
        "visible_policy_sha256": hashlib.sha256(
            view["visible_policy"].encode()
        ).hexdigest(),
        "public_tool_schema_sha256": hashlib.sha256(
            json.dumps(view["public_tools"], sort_keys=True).encode()
        ).hexdigest(),
        "phase15f_snapshot_validated": True,
    }, view


def evaluate_success_bound(task_id, initial_db, final_db):
    return evaluators.evaluate_success(task_id, initial_db, final_db, GOAL_SPECS)


def main():
    formal, pool, tasks, config = preflight()
    before = {str(path.relative_to(REPO)): sha(path) for path in protected_files()}
    write(HERE / "runtime/protected_before.json", before)
    write(
        HERE / "runtime/run_manifest.json",
        {
            "phase": "15G",
            "name": "Independent Separable VF Empty-Skill Calibration",
            "formal_benchmark": formal["benchmark_id"],
            "formal_benchmark_task_count": 54,
            "candidate_pool": pool["pool_id"],
            "skill": "EMPTY",
            "skill_injection": None,
            "rollouts_per_task": 3,
            "planned_trajectories": 6,
            "tasks": list(TASK_SPECS),
            "seed_scheme": "continue after Phase-15C seeds 960178-960183",
            "base_agent_config_unchanged": True,
            "user_simulator_config_unchanged": True,
            "runtime_unchanged": True,
            "native_db_unchanged": True,
            "task_prompt_visibility_parameters_unchanged": True,
            "success_evaluator": "phase15f.evaluators.evaluate_success",
            "success_evaluator_unchanged": True,
            "compliance_judge_unchanged": True,
            "learner_setting": LEARNER_SETTING,
            "information_boundary_version": INFORMATION_BOUNDARY_VERSION,
            "formal_admission": False,
            "Skill_Evolution": False,
            "BOUNDED_FEEDBACK_LEARNABILITY_NOT_TESTED": True,
        },
    )
    run_config = copy.deepcopy(config)
    run_config["planned_rollouts"] = 6
    write(HERE / "runtime/run_config.json", run_config)

    candidates = {row["task_id"]: row for row in pool["candidates"]}
    canonical = base.load_authoritative_domain_contexts(REPO / "external/tau2-bench")
    base.HERE = HERE
    base.TASK_SPECS = TASK_SPECS
    base.bind_candidate_context = bind_frozen_context
    base.evaluate_success = evaluate_success_bound

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
                jobs.append(
                    executor.submit(
                        base.run_one,
                        spec,
                        candidate,
                        task,
                        seed,
                        index,
                        run_config,
                        canonical["airline"],
                    )
                )
        assert len(jobs) == 6
        for future in as_completed(jobs):
            rows.append(future.result())
            rows.sort(key=lambda row: (row["task_id"], row["rollout_index"]))
            write(HERE / "runtime/run_progress.json", rows)
            print(
                json.dumps({"finished": len(rows), "total": 6, "last": rows[-1]}),
                flush=True,
            )

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
    assert summary["refused_reruns"] == 0
    assert summary["protected_files_unchanged"]


if __name__ == "__main__":
    main()
