"""Run only the 14 Phase-3 candidate tasks with the frozen Empty-Skill setup."""
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
PHASE2 = HERE.parent / "phase2_clean_task_realization"
REPO = HERE.parents[3]
load_dotenv(REPO / ".env", override=True)
os.environ.pop("TAU2_AGENT_SKILL_PATH", None)

from loguru import logger
logger.remove()
from tau2.data_model.simulation import RewardInfo
from tau2.data_model.tasks import Task
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
from tau2.orchestrator.modes import CommunicationMode
from tau2.runner.build import build_text_orchestrator

from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import _config
from benchmarks.tau2_governed_evolution.existing_mechanism_state_expansion.phase2_clean_task_realization.benchmark_adapter import (
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
    provenance = load(PHASE2 / "provenance/realization_provenance.json")
    topology_rows = load(HERE.parent / "phase2_5_pre_calibration_structural_audit/structural_topology_matrix.json")
    if isinstance(topology_rows, dict):
        topology_rows = topology_rows.get("tasks", topology_rows.get("rows", []))
    topology = {row["task_id"]: row["TOPOLOGY_CLASS"] for row in topology_rows}
    tasks = []
    next_seed = 960103
    for row in provenance:
        task_id = row["task_id"]
        tasks.append({
            "task_id": task_id,
            "domain": "airline",
            "mechanism": row["mechanism"],
            "polarity": row.get("polarity"),
            "topology": topology[task_id],
            "source_native_state": row["source_native_state"],
            "seeds": [next_seed, next_seed + 1, next_seed + 2],
        })
        next_seed += 3
    assert len(tasks) == 14 and next_seed == 960145
    return {
        "phase": "Existing Mechanism State Expansion Phase 3",
        "skill": "EMPTY",
        "old_34_tasks_rerun": False,
        "original_102_parent_trajectories_reused_or_untouched": True,
        "rollouts_per_task": 3,
        "planned_trajectories": 42,
        "seed_scheme": "continue frozen unified-calibration sequence",
        "tasks": tasks,
    }


def preflight(tasks):
    from tau2.domains.airline.tools import AirlineTools

    schemas = [tool.openai_schema for tool in AirlineTools(None).get_tools().values()]
    banned = re.compile(
        r"\b(P4|LGA01|LGA03|LGA04|ACTIVE|INACTIVE|CO_SATISFIABLE|POLICY_CONFLICT)\b"
        r"|state expansion|candidate pool|future monitor|mechanism|polarity|construction metadata",
        re.I,
    )
    rows = []
    for index, task in enumerate(tasks.values(), 1):
        request = build_task_request(task.model_dump(mode="json"), f"T{index:03d}", schemas)
        write(HERE / "requests" / f"{task.id}.json", request)
        matches = sorted(set(match.group(0) for match in banned.finditer(json.dumps(request))))
        rows.append({"task_id": task.id, "request": f"requests/{task.id}.json", "matches": matches})
    result = {"requests": len(rows), "construction_metadata_leakage_matches": sum(len(r["matches"]) for r in rows), "rows": rows}
    write(HERE / "runtime/learner_safe_preflight.json", result)
    assert result["requests"] == 14 and result["construction_metadata_leakage_matches"] == 0
    return result


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
        context_id = bind_agent_context(orchestrator, "airline")
        initial_db = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        simulation.policy = orchestrator.agent.domain_policy
        write(raw, simulation.model_dump(mode="json"))
        final_db = orchestrator.environment.tools.db.model_dump(mode="json")
        write(final_db_path, final_db)
        success = evaluate_success(task, initial_db, final_db)
        simulation.reward_info = RewardInfo(reward=float(success["success"]), info={"candidate_goal_predicate": success})
        write(HERE / "evaluations/success" / f"{task.id}_{rollout_index:02d}.json", success)

        attempts = []
        def caller(model, system, user, temperature):
            for attempt in range(1, 4):
                response = default_judge_caller(model, system, user, temperature)
                attempts.append({"attempt": attempt, "empty": not bool(response and response.strip())})
                if response and response.strip():
                    return response
            raise RuntimeError("JUDGE_EMPTY_AFTER_3_ATTEMPTS")

        evidence = _build_governed_evidence(
            source_id=f"{task.id}_{rollout_index:02d}",
            domain="airline",
            task=task,
            simulation=simulation,
            domain_policy=contexts["airline"]["original_domain_policy"],
            available_tool_contracts=contexts["airline"]["available_tool_contracts"],
            judge_caller=caller,
        )
        compliance = evidence["compliance_evaluation"]
        write(HERE / "evaluations/compliance" / f"{task.id}_{rollout_index:02d}.json", compliance)
        result = {
            "task_id": task.id,
            "rollout_index": rollout_index,
            "seed": seed,
            "mechanism": spec["mechanism"],
            "polarity": spec.get("polarity"),
            "topology": spec["topology"],
            "context_id": context_id,
            "success": bool(success["success"]),
            "compliance": bool(compliance["compliant"]),
            "judge_attempts": attempts,
            "judge_evaluator_recovery": len(attempts) > 1,
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
        })
        return {"task_id": task.id, "rollout_index": rollout_index, "status": "error", "error_type": type(error).__name__}


def main():
    manifest = build_manifest()
    write(HERE / "runtime/run_manifest.json", manifest)
    config = load(REPO / "benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/calibration/run_config.json")
    config["planned_rollouts"] = 42
    write(HERE / "runtime/run_config.json", config)
    tasks = {row["id"]: Task.model_validate(row) for row in load(PHASE2 / "tasks/candidate_tasks.json")}
    preflight(tasks)
    specs = {row["task_id"]: row for row in manifest["tasks"]}
    contexts = load_authoritative_domain_contexts(REPO / "external/tau2-bench")
    jobs = [(spec, tasks[spec["task_id"]], seed, index) for spec in manifest["tasks"] for index, seed in enumerate(spec["seeds"], 1)]
    rows = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_one, spec, task, seed, index, config, contexts) for spec, task, seed, index in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            write(HERE / "runtime/run_progress.json", rows)
            print(json.dumps({"finished": len(rows), "total": len(jobs), "last": rows[-1]}), flush=True)
    write(HERE / "runtime/run_summary.json", rows)


if __name__ == "__main__":
    main()
