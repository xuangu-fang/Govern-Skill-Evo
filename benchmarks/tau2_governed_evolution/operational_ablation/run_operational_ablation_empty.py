"""Run Step 4U Partial Operational View + Empty Skill rollouts."""

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


ensure_tau2_importable()

from tau2.data_model.simulation import SimulationRun  # noqa: E402
from tau2.runner.build import build_text_orchestrator  # noqa: E402
from tau2.runner.simulation import run_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import (  # noqa: E402
    _config,
)
from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import (  # noqa: E402
    CAMPAIGN_PATH,
    PROJECT_ROOT,
    load_suite,
)
from benchmarks.tau2_governed_evolution.operational_ablation.build_partial_operational_view import (  # noqa: E402
    CANONICAL_POLICY_PATH,
    PARTIAL_POLICY_PATH,
    PARTIAL_TOOL_DESCRIPTIONS,
    assert_no_operational_leakage,
    build_and_write,
    sha256_text,
)
from src.adapters.tau2.tau3_gse_runtime import write_rollout_artifact  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DIRECTORY = Path(__file__).resolve().parent
MANIFEST_PATH = DIRECTORY / "operational_ablation_manifest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts/operational_ablation_step4u/partial_empty"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _apply_partial_view(orchestrator: Any, partial_policy: str) -> dict[str, str]:
    orchestrator.agent.domain_policy = partial_policy
    applied: dict[str, str] = {}
    for tool in orchestrator.agent.tools:
        if tool.name in PARTIAL_TOOL_DESCRIPTIONS:
            description = PARTIAL_TOOL_DESCRIPTIONS[tool.name]
            tool.short_desc = description
            tool.long_desc = ""
            applied[tool.name] = tool.openai_schema["function"]["description"]
    if set(applied) != set(PARTIAL_TOOL_DESCRIPTIONS):
        raise ValueError(f"partial tool set drifted: {sorted(applied)}")
    assert_no_operational_leakage(partial_policy, applied)
    return applied


def _run_one(
    *, spec: dict[str, Any], task: Any, index: int, seed: int,
    campaign: dict[str, Any], context: dict[str, Any], output_root: Path,
    partial_policy: str, view_hash: str,
) -> dict[str, Any]:
    path = output_root / f"{task.id}_rollout_{index:02d}.json"
    raw_path = output_root / f"{task.id}_rollout_{index:02d}_tau2_raw.json"
    error_path = output_root / f"{task.id}_rollout_{index:02d}_error.json"
    try:
        config = _config(campaign, spec, seed)
        orchestrator = build_text_orchestrator(config, task, seed=seed)
        tool_view = _apply_partial_view(orchestrator, partial_policy)
        simulation = run_simulation(
            orchestrator,
            nl_assertions_model=campaign["official_evaluator"]["nl_assertions_model"],
            nl_assertions_llm_args={
                "temperature": campaign["official_evaluator"]["nl_assertions_temperature"]
            },
        )
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        evidence = v14._build_governed_evidence(
            source_id=f"step4u_partial_empty_{task.id}_{index:02d}",
            domain="retail",
            task=task,
            simulation=simulation,
            domain_policy=context["original_domain_policy"],
            available_tool_contracts=context["available_tool_contracts"],
            judge_caller=v14.compliance_v13.default_judge_caller,
        )
        write_rollout_artifact(
            path,
            domain="retail",
            task_id=task.id,
            phase="phase_a_operational_ablation",
            skill_version="S0",
            rollout_index=index,
            rollout_seed=seed,
            governed_evidence=evidence,
            provenance={
                "probe_id": "step4u_retail_one_shot_operational_ablation",
                "condition": "partial_operational_view_empty_skill",
                "source_state": spec["source_state"],
                "raw_tau2_result_path": raw_path.as_posix(),
                "operational_ablation_manifest": MANIFEST_PATH.as_posix(),
                "agent_visible_policy_path": PARTIAL_POLICY_PATH.as_posix(),
                "agent_visible_policy_sha256": sha256_text(partial_policy),
                "agent_visible_tool_descriptions": tool_view,
                "operational_view_sha256": view_hash,
                "canonical_policy_path": CANONICAL_POLICY_PATH.as_posix(),
                "canonical_policy_sha256": sha256_text(context["original_domain_policy"]),
                "canonical_environment_changed": False,
                "tool_implementation_changed": False,
                "task_changed": False,
                "skill_kind": "empty_skill",
                "agent_config": campaign["agent"],
                "user_simulator_config": campaign["user_simulator"],
                "official_evaluator_config": campaign["official_evaluator"],
                "judge_config": campaign["compliance_judge"],
            },
        )
        error_path.unlink(missing_ok=True)
        return {"path": path.as_posix(), "status": "completed"}
    except Exception as error:
        _write(error_path, {
            "task_id": task.id,
            "rollout_index": index,
            "rollout_seed": seed,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        })
        return {"path": path.as_posix(), "status": "error", "error": str(error)}


def run(output_root: Path, max_concurrency: int | None = None) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    view = build_and_write()
    partial_policy = PARTIAL_POLICY_PATH.read_text(encoding="utf-8")
    manifest = _load(MANIFEST_PATH)
    suite_manifest, tasks = load_suite()
    specs = {item["task_id"]: item for item in suite_manifest["tasks"]}
    campaign = _load(CAMPAIGN_PATH)
    task_ids = manifest["task_ids"]
    seeds = manifest["matched_seeds"]
    if len(task_ids) != 2 or seeds != [820, 821, 822]:
        raise ValueError("Step 4U matched contract drifted")
    if campaign["initial_parent"]["kind"] != "empty_skill":
        raise ValueError("Step 4U requires Empty Skill")
    contexts = v14.load_authoritative_domain_contexts(
        PROJECT_ROOT / campaign["benchmark"]["path"]
    )
    canonical = contexts["retail"]["original_domain_policy"]
    if sha256_text(canonical) != view["canonical_policy_sha256"]:
        raise ValueError("canonical Retail policy source drifted")
    view_hash = hashlib.sha256(
        (partial_policy + json.dumps(PARTIAL_TOOL_DESCRIPTIONS, sort_keys=True)).encode()
    ).hexdigest()
    jobs = [
        dict(
            spec=specs[task_id], task=tasks[task_id], index=index, seed=seed,
            campaign=campaign, context=contexts["retail"], output_root=output_root,
            partial_policy=partial_policy, view_hash=view_hash,
        )
        for task_id in task_ids
        for index, seed in enumerate(seeds, 1)
    ]
    results = []
    workers = max_concurrency or campaign["execution"]["max_concurrency"]
    if workers < 1:
        raise ValueError("max_concurrency must be positive")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_one, **job) for job in jobs]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["path"])
    summary = {
        "probe_id": manifest["probe_id"],
        "condition": "partial_operational_view_empty_skill",
        "tasks": len(task_ids),
        "rollouts": len(jobs),
        "max_concurrency": workers,
        "completed": sum(item["status"] == "completed" for item in results),
        "errors": sum(item["status"] == "error" for item in results),
        "operational_view_sha256": view_hash,
        "results": results,
    }
    _write(output_root / "run_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-concurrency", type=int)
    args = parser.parse_args()
    result = run(args.output_root, args.max_concurrency)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
