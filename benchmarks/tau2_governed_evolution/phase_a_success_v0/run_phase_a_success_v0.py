"""Run the frozen mixed Phase-A Success-side v0 with Empty Skill."""

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
from benchmarks.tau2_governed_evolution.phase_a_success_v0.build_phase_a_success_v0 import PROJECT_ROOT
from benchmarks.tau2_governed_evolution.phase_a_success_v0.validate_phase_a_success_v0 import load_suite


ensure_tau2_importable()

from tau2.runner.build import build_text_orchestrator  # noqa: E402
from tau2.runner.simulation import run_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import CAMPAIGN_PATH  # noqa: E402
from benchmarks.tau2_governed_evolution.operational_ablation.build_partial_operational_view import PARTIAL_TOOL_DESCRIPTIONS  # noqa: E402
from src.adapters.tau2.tau3_gse_runtime import write_rollout_artifact  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DEFAULT_ROOT = PROJECT_ROOT / "artifacts/phase_a_success_v0"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _apply_view(orchestrator: Any, spec: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    policy_path = manifest["context_views"][spec["view_id"]]
    changed_tools = {}
    if policy_path:
        orchestrator.agent.domain_policy = (PROJECT_ROOT / policy_path).read_text(encoding="utf-8")
    if spec["view_id"] == "ONE_SHOT_PARTIAL":
        for tool in orchestrator.agent.tools:
            if tool.name in PARTIAL_TOOL_DESCRIPTIONS:
                tool.short_desc = PARTIAL_TOOL_DESCRIPTIONS[tool.name]
                tool.long_desc = ""
                changed_tools[tool.name] = tool.openai_schema["function"]["description"]
        if set(changed_tools) != set(PARTIAL_TOOL_DESCRIPTIONS):
            raise ValueError("one-shot partial tool view drifted")
    return {
        "context_mode": spec["context_mode"],
        "view_id": spec["view_id"],
        "policy_sha256": hashlib.sha256(orchestrator.agent.domain_policy.encode()).hexdigest(),
        "changed_tool_descriptions": changed_tools,
    }


def _one(spec: dict[str, Any], task: Any, index: int, seed: int, manifest: dict[str, Any], campaign: dict[str, Any], contexts: dict[str, Any], root: Path) -> dict[str, Any]:
    stem = f"{task.id}_seed_{seed}_rollout_{index:02d}"
    output = root / "rollouts" / f"{stem}.json"
    raw_path = root / "rollouts" / f"{stem}_tau2_raw.json"
    error_path = root / "rollouts" / f"{stem}_error.json"
    try:
        orchestrator = build_text_orchestrator(_config(campaign, spec, seed), task, seed=seed)
        view = _apply_view(orchestrator, spec, manifest)
        simulation = run_simulation(
            orchestrator,
            nl_assertions_model=campaign["official_evaluator"]["nl_assertions_model"],
            nl_assertions_llm_args={"temperature": campaign["official_evaluator"]["nl_assertions_temperature"]},
        )
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        context = contexts[spec["domain"]]
        evidence = v14._build_governed_evidence(
            source_id=f"phase_a_success_v0_{task.id}_{index}",
            domain=spec["domain"],
            task=task,
            simulation=simulation,
            domain_policy=context["original_domain_policy"],
            available_tool_contracts=context["available_tool_contracts"],
            judge_caller=v14.compliance_v13.default_judge_caller,
        )
        write_rollout_artifact(
            output,
            domain=spec["domain"],
            task_id=task.id,
            phase="phase_a_success_v0_calibration",
            skill_version="S0",
            rollout_index=index,
            rollout_seed=seed,
            governed_evidence=evidence,
            provenance={
                "benchmark_id": manifest["benchmark_id"],
                "source_family": spec["source_family"],
                "mechanism_type": spec["mechanism_type"],
                "task_role": spec["task_role"],
                "source_state": spec["source_state"],
                "agent_visible_view": view,
                "raw_tau2_result_path": str(raw_path),
                "agent_config": campaign["agent"],
                "user_simulator_config": campaign["user_simulator"],
                "official_evaluator_config": campaign["official_evaluator"],
                "judge_config": campaign["compliance_judge"],
            },
        )
        error_path.unlink(missing_ok=True)
        return {"path": str(output), "status": "completed"}
    except Exception as error:
        _write(error_path, {"task_id": task.id, "seed": seed, "error": f"{type(error).__name__}: {error}", "traceback": traceback.format_exc()})
        return {"path": str(output), "status": "error", "error": str(error)}


def run(root: Path, concurrency: int, task_ids: set[str] | None = None, seeds: set[int] | None = None) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    campaign = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
    contexts = v14.load_authoritative_domain_contexts(PROJECT_ROOT / campaign["benchmark"]["path"])
    jobs = [
        (spec, tasks[spec["task_id"]], index, seed, manifest, campaign, contexts, root)
        for spec in manifest["tasks"]
        for index, seed in enumerate(manifest["rollout_seeds"], 1)
        if (task_ids is None or spec["task_id"] in task_ids)
        and (seeds is None or seed in seeds)
    ]
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for future in as_completed([pool.submit(_one, *job) for job in jobs]):
            results.append(future.result())
    results.sort(key=lambda row: row["path"])
    summary = {
        "benchmark_id": manifest["benchmark_id"],
        "tasks": len(manifest["tasks"]),
        "rollouts": len(jobs),
        "seeds": manifest["rollout_seeds"],
        "completed": sum(row["status"] == "completed" for row in results),
        "errors": sum(row["status"] == "error" for row in results),
        "results": results,
    }
    _write(root / "run_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--max-concurrency", type=int, default=6)
    parser.add_argument("--task-id", action="append", dest="task_ids")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    args = parser.parse_args()
    result = run(
        args.output_root,
        args.max_concurrency,
        set(args.task_ids) if args.task_ids else None,
        set(args.seeds) if args.seeds else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
