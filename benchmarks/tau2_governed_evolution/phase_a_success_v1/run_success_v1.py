"""Run frozen Unified Phase-A Success v1 Empty-Agent rollouts."""

from __future__ import annotations

import argparse
import hashlib
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable
from benchmarks.tau2_governed_evolution.phase_a_success_v1.build_task_pool import (
    PROJECT_ROOT,
    RUN_CONFIG,
    SEED_MANIFEST,
    TASK_MANIFEST,
)
from benchmarks.tau2_governed_evolution.phase_a_success_v1.validate_task_pool import load_suite, validate


ensure_tau2_importable()
from tau2.runner.build import build_text_orchestrator  # noqa: E402
from tau2.runner.simulation import run_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from src.adapters.tau2.tau3_gse_runtime import write_rollout_artifact  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DIRECTORY = Path(__file__).resolve().parent
DEFAULT_ROOT = DIRECTORY
CONTEXT_ROOT = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_context/unified"
CONTEXT_MANIFEST = CONTEXT_ROOT / "unified_context_manifest.json"
CAMPAIGN = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
VALID_STATES = {"compliant_success", "compliant_failure", "violating_success", "violating_failure"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _apply_unified_context(orchestrator: Any, domain: str) -> dict[str, Any]:
    context_manifest = _load(CONTEXT_MANIFEST)
    binding = context_manifest["contexts"][domain]
    policy_path = PROJECT_ROOT / binding["policy_path"]
    override_path = PROJECT_ROOT / binding["tool_overrides_path"]
    overrides = _load(override_path)
    if overrides["context_id"] != binding["context_id"]:
        raise ValueError("CONTEXT_BINDING_ERROR: context id drift")

    orchestrator.agent.domain_policy = policy_path.read_text(encoding="utf-8")
    tools_before = {tool.name: deepcopy(tool.openai_schema["function"]) for tool in orchestrator.agent.tools}
    applied = set()
    for tool in orchestrator.agent.tools:
        if tool.name in overrides["overrides"]:
            tool.short_desc = overrides["overrides"][tool.name]["description"]
            tool.long_desc = ""
            applied.add(tool.name)
    if applied != set(overrides["overrides"]):
        raise ValueError("CONTEXT_BINDING_ERROR: tool override target drift")
    tools_after = {tool.name: tool.openai_schema["function"] for tool in orchestrator.agent.tools}
    for name in applied:
        if tools_before[name]["parameters"] != tools_after[name]["parameters"]:
            raise ValueError("CONTEXT_BINDING_ERROR: parameter schema changed")
    if _sha256_json(tools_before) != overrides["canonical_tool_surface_sha256"]:
        raise ValueError("CONTEXT_BINDING_ERROR: canonical tool surface drift")
    if _sha256_json(tools_after) != overrides["unified_tool_surface_sha256"]:
        raise ValueError("CONTEXT_BINDING_ERROR: unified tool surface drift")

    prompt = orchestrator.agent.system_prompt
    forbidden = ("S1_PAYMENT", "S2_TRANSACTION", "S3_CERTIFICATE", "S5_DEEP", "Oracle Skill", "Probe Skill")
    if any(value in prompt for value in forbidden):
        raise ValueError("CONTEXT_BINDING_ERROR: mechanism-specific prompt leakage")
    return {
        "context_id": binding["context_id"],
        "policy_path": binding["policy_path"],
        "policy_sha256": _sha256(policy_path),
        "tool_overrides_path": binding["tool_overrides_path"],
        "tool_surface_sha256": _sha256_json(tools_after),
        "task_specific_override": False,
    }


def _paths(root: Path, task_id: str, index: int) -> tuple[Path, Path, Path]:
    safe_id = task_id.replace("/", "_")
    base = root / "trajectories" / f"{safe_id}_rollout_{index:02d}"
    return base.with_suffix(".json"), base.with_name(base.name + "_tau2_raw.json"), base.with_name(base.name + "_error.json")


def _reusable(path: Path, task_id: str, index: int, seed: int, manifest_hash: str) -> bool:
    try:
        value = _load(path)
        return (
            value["task_id"] == task_id
            and value["rollout_index"] == index
            and value["rollout_seed"] == seed
            and value["state"] in VALID_STATES
            and value["provenance"]["task_manifest_sha256"] == manifest_hash
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def _one(*, spec: dict[str, Any], task: Any, index: int, seed: int, campaign: dict[str, Any], root: Path, manifest_hash: str, domain_context: dict[str, Any]) -> dict[str, Any]:
    output, raw_path, error_path = _paths(root, task.id, index)
    if _reusable(output, task.id, index, seed, manifest_hash):
        return {"path": str(output), "status": "reused"}
    try:
        orchestrator = build_text_orchestrator(_config(campaign, spec, seed), task, seed=seed)
        view = _apply_unified_context(orchestrator, spec["domain"])
        simulation = run_simulation(
            orchestrator,
            nl_assertions_model=campaign["official_evaluator"]["nl_assertions_model"],
            nl_assertions_llm_args={"temperature": campaign["official_evaluator"]["nl_assertions_temperature"]},
        )
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        evidence = v14._build_governed_evidence(
            source_id=f"phase_a_success_v1_{task.id}_{index:02d}",
            domain=spec["domain"],
            task=task,
            simulation=simulation,
            domain_policy=orchestrator.agent.domain_policy,
            available_tool_contracts=domain_context["available_tool_contracts"],
            judge_caller=v14.compliance_v13.default_judge_caller,
        )
        write_rollout_artifact(
            output,
            domain=spec["domain"],
            task_id=task.id,
            phase="unified_phase_a_success_v1_calibration",
            skill_version="S0",
            rollout_index=index,
            rollout_seed=seed,
            governed_evidence=evidence,
            provenance={
                "benchmark_id": "unified_phase_a_success_v1_calibration",
                "task_manifest_sha256": manifest_hash,
                "seed_manifest_sha256": _sha256(SEED_MANIFEST),
                "task_role": spec["task_role"],
                "operation_category": spec["operation_category"],
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
        error_type = "CONTEXT_BINDING_ERROR" if "CONTEXT_BINDING_ERROR" in str(error) else type(error).__name__
        _write(error_path, {
            "task_id": task.id,
            "rollout_index": index,
            "rollout_seed": seed,
            "error_type": error_type,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        })
        return {"path": str(output), "status": "error", "error_type": error_type, "error": str(error)}


def run(root: Path, concurrency: int) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    validation = validate()
    if not validation["passed"]:
        raise RuntimeError("frozen pool validation failed")
    manifest, tasks = load_suite()
    seeds = _load(SEED_MANIFEST)["seeds"]
    run_config = _load(RUN_CONFIG)
    manifest_hash = _sha256(TASK_MANIFEST)
    if manifest_hash != run_config["task_manifest_sha256"]:
        raise RuntimeError("task manifest changed after freeze")
    campaign = _load(CAMPAIGN)
    contexts = v14.load_authoritative_domain_contexts(PROJECT_ROOT / campaign["benchmark"]["path"])
    specs = {row["task_id"]: row for row in manifest["tasks"]}
    jobs = [
        dict(spec=spec, task=tasks[task_id], index=index, seed=seed, campaign=campaign, root=root, manifest_hash=manifest_hash, domain_context=contexts[spec["domain"]])
        for task_id, spec in specs.items()
        for index, seed in enumerate(seeds[task_id], 1)
    ]
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for future in as_completed([pool.submit(_one, **job) for job in jobs]):
            results.append(future.result())
    results.sort(key=lambda row: row["path"])
    summary = {
        "benchmark_id": manifest["benchmark_id"],
        "task_manifest_sha256": manifest_hash,
        "tasks": len(tasks),
        "rollouts": len(jobs),
        "completed": sum(row["status"] == "completed" for row in results),
        "reused": sum(row["status"] == "reused" for row in results),
        "errors": sum(row["status"] == "error" for row in results),
        "results": results,
    }
    _write(root / "run_summary.json", summary)
    result_lines = []
    for row in results:
        if row["status"] in {"completed", "reused"}:
            artifact = _load(Path(row["path"]))
            result_lines.append(json.dumps({
                "task_id": artifact["task_id"],
                "rollout_index": artifact["rollout_index"],
                "rollout_seed": artifact["rollout_seed"],
                "success": artifact["task_evaluation"]["success"],
                "compliant": artifact["compliance_evaluation"]["compliant"],
                "state": artifact["state"],
                "artifact_path": row["path"],
            }, ensure_ascii=False))
    results_text = "\n".join(result_lines)
    if results_text:
        results_text += "\n"
    (root / "results.jsonl").write_text(results_text, encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--max-concurrency", type=int, default=6)
    args = parser.parse_args()
    result = run(args.root, args.max_concurrency)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["errors"] == 0 else 1)
