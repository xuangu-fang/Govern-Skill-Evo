"""Run the frozen nine-trajectory Compliance Boundary calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable
from benchmarks.tau2_governed_evolution.phase_a_context.validate_unified_phase_a_context import validate as validate_context


ensure_tau2_importable()
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402
from tau2.runner.simulation import run_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from benchmarks.tau2_governed_evolution.phase_a_success_v2.run_success_v2 import apply_context  # noqa: E402
from src.adapters.tau2.tau3_gse_runtime import write_rollout_artifact  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TASK_MANIFEST = ROOT / "task_manifest.json"
TASKS = ROOT / "tasks.json"
SEED_MANIFEST = ROOT / "seed_manifest.json"
RUN_CONFIG = ROOT / "run_config.json"
CAMPAIGN = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
VALID_STATES = {
    "compliant_success",
    "compliant_failure",
    "violating_success",
    "violating_failure",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_suite() -> tuple[dict[str, Any], dict[str, Task]]:
    manifest = load(TASK_MANIFEST)
    values = load(TASKS)
    tasks = {row["id"]: Task.model_validate(row) for row in values}
    expected = {row["task_id"] for row in manifest["tasks"]}
    if len(tasks) != 3 or set(tasks) != expected:
        raise RuntimeError("frozen boundary suite mismatch")
    return manifest, tasks


def validate() -> None:
    config = load(RUN_CONFIG)
    seeds = load(SEED_MANIFEST)
    manifest, tasks = load_suite()
    context = validate_context()
    checks = {
        "context": context["UNIFIED_PHASE_A_CONTEXT_VERDICT"] == "READY_FOR_SUCCESS_V1",
        "manifest_hash": config["task_manifest_sha256"] == sha256(TASK_MANIFEST),
        "tasks_hash": config["tasks_sha256"] == sha256(TASKS),
        "seeds_hash": config["seed_manifest_sha256"] == sha256(SEED_MANIFEST),
        "task_count": len(tasks) == 3,
        "seed_keys": set(seeds["seeds"]) == set(tasks),
        "three_each": all(len(values) == 3 for values in seeds["seeds"].values()),
        "unique_seeds": len({seed for values in seeds["seeds"].values() for seed in values}) == 9,
        "empty_skill": config["skill"] == "EMPTY" and config["skill_injection"] is None,
        "contexts": all(row["context_id"] == "AIRLINE_PHASE_A_UNIFIED_V1" for row in manifest["tasks"]),
        "target": all(row["target_governance_phenomenon"] == "G1_P6_ELIGIBILITY_BACKEND_PERMISSIVENESS" for row in manifest["tasks"]),
    }
    if not all(checks.values()):
        raise RuntimeError(f"boundary static validation failed: {checks}")


def paths(task_id: str, index: int) -> tuple[Path, Path, Path]:
    base = ROOT / "trajectories" / f"{task_id}_rollout_{index:02d}"
    return (
        base.with_suffix(".json"),
        base.with_name(base.name + "_tau2_raw.json"),
        base.with_name(base.name + "_error.json"),
    )


def reusable(path: Path, task_id: str, index: int, seed: int, manifest_hash: str) -> bool:
    try:
        value = load(path)
        return (
            value["task_id"] == task_id
            and value["rollout_index"] == index
            and value["rollout_seed"] == seed
            and value["state"] in VALID_STATES
            and value["provenance"]["task_manifest_sha256"] == manifest_hash
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def one(
    spec: dict[str, Any],
    task: Task,
    index: int,
    seed: int,
    campaign: dict[str, Any],
    manifest_hash: str,
    domain_context: dict[str, Any],
) -> dict[str, Any]:
    output, raw_path, error_path = paths(task.id, index)
    if reusable(output, task.id, index, seed, manifest_hash):
        return {"path": str(output), "status": "reused"}
    try:
        orchestrator = build_text_orchestrator(_config(campaign, spec, seed), task, seed=seed)
        view = apply_context(orchestrator, "airline")
        simulation = run_simulation(
            orchestrator,
            nl_assertions_model=campaign["official_evaluator"]["nl_assertions_model"],
            nl_assertions_llm_args={"temperature": campaign["official_evaluator"]["nl_assertions_temperature"]},
        )
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        evidence = v14._build_governed_evidence(
            source_id=f"phase_a_compliance_boundary_{task.id}_{index:02d}",
            domain="airline",
            task=task,
            simulation=simulation,
            domain_policy=orchestrator.agent.domain_policy,
            available_tool_contracts=domain_context["available_tool_contracts"],
            judge_caller=v14.compliance_v13.default_judge_caller,
        )
        write_rollout_artifact(
            output,
            domain="airline",
            task_id=task.id,
            phase="phase_a_compliance_boundary_rollout",
            skill_version="S0",
            rollout_index=index,
            rollout_seed=seed,
            governed_evidence=evidence,
            provenance={
                "benchmark_id": "phase_a_compliance_boundary_rollout_v1",
                "task_manifest_sha256": manifest_hash,
                "seed_manifest_sha256": sha256(SEED_MANIFEST),
                "task_role": spec["task_role"],
                "target_governance_phenomenon": spec["target_governance_phenomenon"],
                "boundary_subtype": spec["boundary_subtype"],
                "agent_visible_context": view,
                "raw_tau2_result_path": str(raw_path),
                "skill_kind": "empty_skill",
                "skill_injection": None,
                "agent_config": campaign["agent"],
                "user_simulator_config": campaign["user_simulator"],
                "official_evaluator_config": campaign["official_evaluator"],
                "judge_config": campaign["compliance_judge"],
            },
        )
        error_path.unlink(missing_ok=True)
        return {"path": str(output), "status": "completed"}
    except Exception as error:
        write(
            error_path,
            {
                "task_id": task.id,
                "rollout_index": index,
                "rollout_seed": seed,
                "error_type": "CONTEXT_BINDING_ERROR" if "CONTEXT_BINDING_ERROR" in str(error) else type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        return {"path": str(output), "status": "error", "error": str(error)}


def run(concurrency: int) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    validate()
    manifest, tasks = load_suite()
    seeds = load(SEED_MANIFEST)["seeds"]
    campaign = load(CAMPAIGN)
    contexts = v14.load_authoritative_domain_contexts(PROJECT_ROOT / "external/tau2-bench")
    manifest_hash = sha256(TASK_MANIFEST)
    jobs = [
        (spec, tasks[spec["task_id"]], index, seed, campaign, manifest_hash, contexts["airline"])
        for spec in manifest["tasks"]
        for index, seed in enumerate(seeds[spec["task_id"]], 1)
    ]
    rows = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(one, *job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(json.dumps({"finished": len(rows), "total": len(jobs), "status": row["status"], "path": row["path"]}), flush=True)
    rows.sort(key=lambda row: row["path"])
    summary = {
        "benchmark_id": "phase_a_compliance_boundary_rollout_v1",
        "task_manifest_sha256": manifest_hash,
        "tasks": 3,
        "rollouts": 9,
        "completed": sum(row["status"] == "completed" for row in rows),
        "reused": sum(row["status"] == "reused" for row in rows),
        "errors": sum(row["status"] == "error" for row in rows),
        "results": rows,
    }
    write(ROOT / "run_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-concurrency", type=int, default=3)
    args = parser.parse_args()
    result = run(args.max_concurrency)
    raise SystemExit(0 if result["errors"] == 0 else 1)
