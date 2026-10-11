"""Run exactly the nine immutable Phase-14 Empty-Skill calibration trajectories."""

from __future__ import annotations

import copy
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
PHASE13 = HERE.parent / "phase13_cs_reachable_clean_task_realization"
REPO = HERE.parents[6]
FORMAL = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/formal_manifestation_admission"
CONFIG_SOURCE = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
load_dotenv(REPO / ".env", override=True)
os.environ.pop("TAU2_AGENT_SKILL_PATH", None)

from loguru import logger

logger.remove()

from tau2.data_model.simulation import RewardInfo
from tau2.data_model.tasks import Task
from tau2.runner.build import build_text_orchestrator

from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.construction.capability_expansion.run_phase_a_capability_empty_rollouts import _config
from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.benchmark.phase_a_final_unified_benchmark_v1.benchmark_adapter import bind_agent_context
from benchmarks.tau2_governed_evolution.editions.phase_v2_day30.construction.advanced_structure.phase13_cs_reachable_clean_task_realization.evaluators import evaluate_success
from src.adapters.tau2.tau3_compliance_judge_v13 import default_judge_caller
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import _build_governed_evidence, load_authoritative_domain_contexts
from src.skill_evolution.information_boundary_v15 import agent_payload, capture_agent_visible_view


TASK_SPECS = (
    {"task_id": "retail_request_004", "domain": "retail", "source_candidate_id": "CSG12_001", "seeds": [960163, 960164, 960165]},
    {"task_id": "retail_request_005", "domain": "retail", "source_candidate_id": "CSG12_002", "seeds": [960166, 960167, 960168]},
    {"task_id": "travel_request_018", "domain": "airline", "source_candidate_id": "CSG12_003", "seeds": [960169, 960170, 960171]},
)


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_files():
    paths = list(FORMAL.rglob("*"))
    paths += [
        REPO / "external/tau2-bench/data/tau2/domains/retail/db.json",
        REPO / "external/tau2-bench/data/tau2/domains/airline/db.json",
    ]
    paths += list(PHASE13.rglob("*"))
    paths += [p for p in REPO.rglob("*") if p.is_file() and "v14" in str(p.relative_to(REPO)).lower()]
    return sorted({p for p in paths if p.is_file() and "__pycache__" not in str(p)})


def bind_candidate_context(orchestrator, candidate):
    # Reuse and validate the formal public tool surface, then bind the immutable
    # candidate-version visible policy. Oracle policy is never assigned here.
    formal_context_id = bind_agent_context(orchestrator, candidate["domain"])
    policy_path = REPO / candidate["learner_visible_context_path"]
    orchestrator.agent.domain_policy = policy_path.read_text()
    envelope = capture_agent_visible_view(orchestrator.agent, candidate["domain"])
    view = agent_payload(envelope)
    return {
        "context_id": f'{candidate["task_id"]}_PHASE13_VISIBLE_V1',
        "policy_path": candidate["learner_visible_context_path"],
        "formal_tool_context_id": formal_context_id,
        "v15_view_digest": hashlib.sha256(envelope.payload.encode()).hexdigest(),
        "v15_payload_keys": sorted(view),
        "visible_policy_sha256": hashlib.sha256(view["visible_policy"].encode()).hexdigest(),
        "public_tool_schema_sha256": hashlib.sha256(json.dumps(view["public_tools"], sort_keys=True).encode()).hexdigest(),
    }, view


def preflight(pool, tasks):
    formal_manifest = load(FORMAL / "expanded_benchmark_manifest.json")
    formal_tasks = load(FORMAL / "tasks/expanded_tasks.json")
    assert formal_manifest["benchmark_id"] == "PHASE_A_UNIFIED_BENCHMARK_MANIFESTATION_EXPANDED_V1"
    assert formal_manifest["total_tasks"] == len(formal_tasks) == 54
    assert pool["pool_id"] == "CS_REACHABLE_GOVERNANCE_CANDIDATE_POOL_V1" and pool["task_count"] == 3
    expected = {row["task_id"] for row in TASK_SPECS}
    assert set(tasks) == expected == {row["task_id"] for row in pool["candidates"]}
    assert not expected.intersection(row["id"] for row in formal_tasks)
    assert [seed for row in TASK_SPECS for seed in row["seeds"]] == list(range(960163, 960172))
    for path in (HERE / "trajectories").glob("*_started.json"):
        raise RuntimeError(f"Immutable trajectory already started: {path}")
    config = load(CONFIG_SOURCE)
    assert config["skill"] == "EMPTY" and config["skill_injection"] is None
    assert config["agent"]["model"] == "openai/deepseek-v4-flash"
    assert config["user_simulator"]["model"] == "openai/deepseek-v4-flash"
    assert config["compliance_judge"]["model"] == "openai/deepseek-v4-pro"
    return config, formal_manifest


def judge_evidence(task, simulation, canonical, source_id, domain):
    build_attempts, provider_attempts = [], []
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
                domain=domain,
                task=task,
                simulation=simulation,
                domain_policy=canonical["original_domain_policy"],
                available_tool_contracts=canonical["available_tool_contracts"],
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


def run_one(spec, candidate, task, seed, index, config, canonical):
    stem = HERE / "trajectories" / f'{task.id}_{index:02d}'
    started = Path(str(stem) + "_started.json")
    raw = Path(str(stem) + "_raw.json")
    final_db_path = Path(str(stem) + "_final_db.json")
    result_path = Path(str(stem) + ".json")
    if started.exists():
        return {"task_id": task.id, "rollout_index": index, "status": "REFUSED_RERUN"}
    write(started, {
        "task_id": task.id, "rollout_index": index, "seed": seed,
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "trajectory_rerun": False,
    })
    try:
        orchestrator = build_text_orchestrator(_config(config, spec, seed), task, seed=seed)
        boundary, visible_view = bind_candidate_context(orchestrator, candidate)
        forbidden = [candidate["source_candidate_id"], "oracle_policy", "latent_dimension", "HIDDEN_ANSWER_POINTER"]
        serialized_view = json.dumps(visible_view, ensure_ascii=False)
        if any(term.lower() in serialized_view.lower() for term in forbidden):
            raise RuntimeError("V15_VISIBLE_PAYLOAD_LEAKAGE")
        initial_db = orchestrator.environment.tools.db.model_dump(mode="json")
        simulation = orchestrator.run()
        simulation.policy = orchestrator.agent.domain_policy
        write(raw, simulation.model_dump(mode="json"))
        final_db = orchestrator.environment.tools.db.model_dump(mode="json")
        write(final_db_path, final_db)
        success = evaluate_success(task.id, initial_db, final_db)
        simulation.reward_info = RewardInfo(reward=float(success["success"]), info={"candidate_goal_predicate": success})
        write(HERE / "evaluations/success" / f'{task.id}_{index:02d}.json', success)
        evidence, build_attempts, provider_attempts, original_invalid = judge_evidence(
            task, simulation, canonical, f'phase14_{task.id}_{index:02d}', spec["domain"]
        )
        compliance = evidence["compliance_evaluation"]
        write(HERE / "evaluations/compliance" / f'{task.id}_{index:02d}.json', compliance)
        recovery = original_invalid is not None or any(row["empty"] for row in provider_attempts)
        if recovery:
            write(HERE / "runtime/recoveries" / f'{task.id}_{index:02d}.json', {
                "task_id": task.id, "rollout_index": index,
                "JUDGE_EVALUATOR_RECOVERY": True,
                "ORIGINAL_INVALID_ARTIFACT": original_invalid,
                "RECOVERY_COUNT": sum(x["status"] == "invalid" for x in build_attempts) + sum(x["empty"] for x in provider_attempts),
                "trajectory_rerun": False, "raw_sha256": sha(raw),
            })
        result = {
            "task_id": task.id, "source_candidate_id": spec["source_candidate_id"],
            "domain": spec["domain"], "rollout_index": index, "seed": seed,
            "skill": "EMPTY", "success": bool(success["success"]),
            "compliance": bool(compliance["compliant"]),
            "quadrant": ("C" if compliance["compliant"] else "V") + ("S" if success["success"] else "F"),
            "boundary": boundary,
            "learner_setting": "EXPERIENCE_GROUNDED_LEARNER",
            "information_boundary_version": "v15_learner_safe",
            "privileged_fallback": False,
            "judge_build_attempts": build_attempts,
            "judge_provider_attempts": provider_attempts,
            "judge_evaluator_recovery": recovery,
            "raw_sha256": sha(raw), "final_db_sha256": sha(final_db_path),
            "evidence": evidence,
        }
        write(result_path, result)
        return {"task_id": task.id, "rollout_index": index, "status": "completed", "path": str(result_path)}
    except Exception as error:
        write(Path(str(stem) + "_error.json"), {
            "task_id": task.id, "rollout_index": index, "seed": seed,
            "error_type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc(), "raw_exists": raw.exists(),
            "trajectory_rerun": False,
        })
        return {"task_id": task.id, "rollout_index": index, "status": "error", "error_type": type(error).__name__, "raw_exists": raw.exists()}


def main():
    pool = load(PHASE13 / "cs_reachable_candidate_pool_v1.json")
    tasks = {row["id"]: Task.model_validate(row) for row in load(PHASE13 / "tasks/candidate_tasks.json")}
    candidates = {row["task_id"]: row for row in pool["candidates"]}
    config, formal_manifest = preflight(pool, tasks)
    before = {str(path.relative_to(REPO)): sha(path) for path in protected_files()}
    manifest = {
        "phase": "14", "name": "3-Task / 9-Trajectory CS-Reachable Governance Empty-Skill Calibration",
        "formal_benchmark": formal_manifest["benchmark_id"], "formal_benchmark_task_count": 54,
        "candidate_pool": pool["pool_id"], "skill": "EMPTY", "skill_injection": None,
        "old_tasks_rerun": False, "previous_trajectories_rerun": False,
        "rollouts_per_task": 3, "planned_trajectories": 9,
        "learner_setting": "EXPERIENCE_GROUNDED_LEARNER", "information_boundary_version": "v15_learner_safe",
        "privileged_fallback": False, "formal_admission": False,
        "Skill_Evolution": False, "Diagnosis": False, "Editor_learning": False,
        "Candidate_Skill_generation": False, "Gate": False, "Train_Monitor_split": False,
        "BOUNDED_FEEDBACK_LEARNABILITY_NOT_TESTED": True,
        "seed_scheme": "continue after Phase-11 seed 960162",
        "tasks": list(TASK_SPECS),
        "protected_files_before": {"count": len(before), "aggregate_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()},
    }
    write(HERE / "runtime/run_manifest.json", manifest)
    run_config = copy.deepcopy(config)
    run_config["planned_rollouts"] = 9
    write(HERE / "runtime/run_config.json", run_config)
    canonical = load_authoritative_domain_contexts(REPO / "external/tau2-bench")
    jobs = [
        (spec, candidates[spec["task_id"]], tasks[spec["task_id"]], seed, index, run_config, canonical[spec["domain"]])
        for spec in TASK_SPECS for index, seed in enumerate(spec["seeds"], 1)
    ]
    assert len(jobs) == 9
    rows = []
    with ThreadPoolExecutor(max_workers=8) as pool_executor:
        futures = [pool_executor.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            rows.sort(key=lambda row: (row["task_id"], row["rollout_index"]))
            write(HERE / "runtime/run_progress.json", rows)
            print(json.dumps({"finished": len(rows), "total": len(jobs), "last": rows[-1]}), flush=True)
    after = {str(path.relative_to(REPO)): sha(path) for path in protected_files()}
    summary = {
        "planned": 9, "completed": sum(row["status"] == "completed" for row in rows),
        "errors": sum(row["status"] == "error" for row in rows),
        "refused_reruns": sum(row["status"] == "REFUSED_RERUN" for row in rows),
        "old_tasks_rerun": False, "trajectory_reruns": 0,
        "protected_files_unchanged": before == after,
        "protected_file_count": len(before),
        "results": rows,
    }
    write(HERE / "runtime/run_summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)
    if summary["completed"] != 9 or summary["errors"] or not summary["protected_files_unchanged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
