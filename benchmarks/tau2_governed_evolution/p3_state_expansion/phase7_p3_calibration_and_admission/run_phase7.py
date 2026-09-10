"""Run only the three Phase-6 P3 candidates with the frozen Empty-Skill setup."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
PHASE6 = HERE.parent / "phase6_clean_task_realization"
REPO = HERE.parents[3]
load_dotenv(REPO / ".env", override=True)
os.environ.pop("TAU2_AGENT_SKILL_PATH", None)

from loguru import logger

logger.remove()

from tau2.data_model.simulation import RewardInfo
from tau2.data_model.tasks import Task
from tau2.runner.build import build_text_orchestrator

from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import _config
from benchmarks.tau2_governed_evolution.p3_state_expansion.phase6_clean_task_realization.benchmark_adapter import (
    bind_agent_context,
    build_task_request,
    evaluate_success,
)
from src.adapters.tau2.tau3_compliance_judge_v13 import default_judge_caller
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    _build_governed_evidence,
    load_authoritative_domain_contexts,
)


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest():
    pool = load(PHASE6 / "p3_state_expansion_candidate_pool_v1.json")
    seeds = iter(range(960145, 960154))
    tasks = []
    for candidate in pool["candidates"]:
        tasks.append({
            "task_id": candidate["task_id"],
            "domain": "retail",
            "mechanism": "P3",
            "canonical_mechanism_definition": "Mutation-Induced Resource Refresh Dependency",
            "native_state_id": candidate["native_state_id"],
            "manifestation_type": candidate["manifestation_type"],
            "resource_before": candidate["resource_before"],
            "resource_after_upstream": candidate["resource_after_upstream"],
            "downstream_delta": candidate["downstream_delta"],
            "seeds": [next(seeds), next(seeds), next(seeds)],
        })
    assert len(tasks) == 3 and [seed for row in tasks for seed in row["seeds"]] == list(range(960145, 960154))
    return {
        "phase": "Phase 7 — P3 Empty-Skill Calibration & Admission",
        "skill": "EMPTY",
        "old_benchmark_tasks_rerun": False,
        "old_state_expansion_trajectories_rerun": False,
        "old_P3_trajectories_rerun": False,
        "rollouts_per_task": 3,
        "planned_trajectories": 9,
        "seed_scheme": "continue frozen unified-calibration sequence after 960144",
        "tasks": tasks,
    }


def preflight(tasks):
    from tau2.domains.retail.tools import RetailTools

    schemas = [tool.openai_schema for tool in RetailTools(None).get_tools().values()]
    banned = re.compile(
        r"(?<![A-Za-z0-9])P3(?![A-Za-z0-9])|Mutation-Induced Resource Refresh Dependency"
        r"|manifestation|state[ _-]expansion|stale[ _-]state|construction metadata",
        re.I,
    )
    rows = []
    for index, task in enumerate(tasks.values(), 1):
        request = build_task_request(task.model_dump(mode="json"), f"T{index:03d}", schemas)
        phase6_request = load(PHASE6 / "requests" / f"{task.id}.json")
        assert request == phase6_request
        write(HERE / "requests" / f"{task.id}.json", request)
        matches = sorted(set(match.group(0) for match in banned.finditer(json.dumps(request))))
        rows.append({"task_id": task.id, "request": f"requests/{task.id}.json", "matches": matches})
    result = {
        "requests": len(rows),
        "construction_metadata_leakage_matches": sum(len(row["matches"]) for row in rows),
        "phase6_requests_reused_byte_equivalent_json": True,
        "rows": rows,
    }
    write(HERE / "runtime/learner_safe_preflight.json", result)
    assert result["requests"] == 3 and result["construction_metadata_leakage_matches"] == 0


def judge_evidence(task, simulation, contexts, source_id):
    build_attempts = []
    provider_attempts = []
    original_invalid = None
    evidence = None
    for build_attempt in range(1, 4):
        def caller(model, system, user, temperature):
            for provider_attempt in range(1, 4):
                response = default_judge_caller(model, system, user, temperature)
                provider_attempts.append({
                    "build_attempt": build_attempt,
                    "provider_attempt": provider_attempt,
                    "empty": not bool(response and response.strip()),
                })
                if response and response.strip():
                    return response
            raise RuntimeError("JUDGE_EMPTY_AFTER_3_ATTEMPTS")

        try:
            evidence = _build_governed_evidence(
                source_id=source_id,
                domain="retail",
                task=task,
                simulation=simulation,
                domain_policy=contexts["retail"]["original_domain_policy"],
                available_tool_contracts=contexts["retail"]["available_tool_contracts"],
                judge_caller=caller,
            )
            build_attempts.append({"attempt": build_attempt, "status": "valid"})
            break
        except Exception as error:
            item = {"attempt": build_attempt, "status": "invalid", "error_type": type(error).__name__, "message": str(error)}
            build_attempts.append(item)
            if original_invalid is None:
                original_invalid = item
    if evidence is None:
        raise RuntimeError(f"COMPLIANCE_EVALUATOR_RECOVERY_EXHAUSTED: {build_attempts}")
    return evidence, build_attempts, provider_attempts, original_invalid


def run_one(spec, task, seed, rollout_index, config, contexts):
    stem = HERE / "trajectories" / f"{task.id}_{rollout_index:02d}"
    started = Path(str(stem) + "_started.json")
    raw = Path(str(stem) + "_raw.json")
    final_db_path = Path(str(stem) + "_final_db.json")
    result_path = Path(str(stem) + ".json")
    if started.exists():
        return {"task_id": task.id, "rollout_index": rollout_index, "status": "REFUSED_RERUN"}
    write(started, {"seed": seed, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    try:
        orchestrator = build_text_orchestrator(_config(config, spec, seed), task, seed=seed)
        context_id = bind_agent_context(orchestrator, "retail")
        initial_db = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        simulation.policy = orchestrator.agent.domain_policy
        write(raw, simulation.model_dump(mode="json"))
        final_db = orchestrator.environment.tools.db.model_dump(mode="json")
        write(final_db_path, final_db)
        success = evaluate_success(task, initial_db, final_db)
        simulation.reward_info = RewardInfo(
            reward=float(success["success"]), info={"candidate_goal_predicate": success}
        )
        write(HERE / "evaluations/success" / f"{task.id}_{rollout_index:02d}.json", success)

        evidence, build_attempts, provider_attempts, original_invalid = judge_evidence(
            task, simulation, contexts, f"{task.id}_{rollout_index:02d}"
        )
        compliance = evidence["compliance_evaluation"]
        write(HERE / "evaluations/compliance" / f"{task.id}_{rollout_index:02d}.json", compliance)
        recovery = original_invalid is not None or any(row["empty"] for row in provider_attempts)
        if recovery:
            write(HERE / "runtime/recoveries" / f"{task.id}_{rollout_index:02d}.json", {
                "task_id": task.id,
                "rollout_index": rollout_index,
                "JUDGE_EVALUATOR_RECOVERY": True,
                "RECOVERY_REASON": original_invalid or "empty judge response",
                "ORIGINAL_INVALID_ARTIFACT": original_invalid,
                "RECOVERY_COUNT": len([row for row in build_attempts if row["status"] == "invalid"])
                                  + len([row for row in provider_attempts if row["empty"]]),
                "trajectory_rerun": False,
                "raw_sha256": sha256(raw),
            })
        result = {
            "task_id": task.id,
            "rollout_index": rollout_index,
            "seed": seed,
            "mechanism": "P3",
            "manifestation_type": spec["manifestation_type"],
            "native_state_id": spec["native_state_id"],
            "context_id": context_id,
            "success": bool(success["success"]),
            "compliance": bool(compliance["compliant"]),
            "judge_build_attempts": build_attempts,
            "judge_provider_attempts": provider_attempts,
            "judge_evaluator_recovery": recovery,
            "raw_sha256": sha256(raw),
            "evidence": evidence,
        }
        write(result_path, result)
        return {"task_id": task.id, "rollout_index": rollout_index, "status": "completed", "path": str(result_path)}
    except Exception as error:
        write(Path(str(stem) + "_error.json"), {
            "task_id": task.id,
            "rollout_index": rollout_index,
            "seed": seed,
            "error_type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "raw_exists": raw.exists(),
            "trajectory_rerun": False,
        })
        return {"task_id": task.id, "rollout_index": rollout_index, "status": "error", "error_type": type(error).__name__, "raw_exists": raw.exists()}


def main():
    manifest = build_manifest()
    write(HERE / "runtime/run_manifest.json", manifest)
    config = load(REPO / "benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/calibration/run_config.json")
    config["planned_rollouts"] = 9
    write(HERE / "runtime/run_config.json", config)
    tasks = {row["id"]: Task.model_validate(row) for row in load(PHASE6 / "tasks/candidate_tasks.json")}
    assert set(tasks) == {row["task_id"] for row in manifest["tasks"]}
    preflight(tasks)
    contexts = load_authoritative_domain_contexts(REPO / "external/tau2-bench")
    jobs = [(spec, tasks[spec["task_id"]], seed, index)
            for spec in manifest["tasks"]
            for index, seed in enumerate(spec["seeds"], 1)]
    assert len(jobs) == 9
    rows = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_one, spec, task, seed, index, config, contexts)
                   for spec, task, seed, index in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            rows.sort(key=lambda row: (row["task_id"], row["rollout_index"]))
            write(HERE / "runtime/run_progress.json", rows)
            print(json.dumps({"finished": len(rows), "total": len(jobs), "last": rows[-1]}), flush=True)
    write(HERE / "runtime/run_summary.json", rows)


if __name__ == "__main__":
    main()
