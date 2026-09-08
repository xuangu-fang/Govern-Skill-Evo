"""Run canonical Airline + Empty Skill rollouts for Step 4W-S5."""

from __future__ import annotations

import argparse
import hashlib
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.cardinality_propagation.build_cardinality_tasks import (
    MANIFEST_PATH,
    PROJECT_ROOT,
)
from benchmarks.tau2_governed_evolution.cardinality_propagation.validate_cardinality_tasks import load_suite
from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable


ensure_tau2_importable()

from tau2.runner.build import build_text_orchestrator  # noqa: E402
from tau2.runner.simulation import run_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import CAMPAIGN_PATH  # noqa: E402
from src.adapters.tau2.tau3_gse_runtime import write_rollout_artifact  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DEFAULT_ROOT = PROJECT_ROOT / "artifacts/cardinality_propagation_step4w_s5"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def _one(spec: dict, task: Any, index: int, seed: int, campaign: dict, context: dict, root: Path) -> dict:
    stem = f"{task.id}_seed_{seed}_rollout_{index:02d}"
    output = root / "rollouts" / f"{stem}.json"
    raw_path = root / "rollouts" / f"{stem}_tau2_raw.json"
    error_path = root / "rollouts" / f"{stem}_error.json"
    try:
        orchestrator = build_text_orchestrator(_config(campaign, spec, seed), task, seed=seed)
        simulation = run_simulation(
            orchestrator,
            nl_assertions_model=campaign["official_evaluator"]["nl_assertions_model"],
            nl_assertions_llm_args={"temperature": campaign["official_evaluator"]["nl_assertions_temperature"]},
        )
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n")
        evidence = v14._build_governed_evidence(
            source_id=f"step4w_s5_{task.id}_{index}",
            domain="airline",
            task=task,
            simulation=simulation,
            domain_policy=context["original_domain_policy"],
            available_tool_contracts=context["available_tool_contracts"],
            judge_caller=v14.compliance_v13.default_judge_caller,
        )
        write_rollout_artifact(
            output,
            domain="airline",
            task_id=task.id,
            phase="phase_a_cardinality_propagation",
            skill_version="S0",
            rollout_index=index,
            rollout_seed=seed,
            governed_evidence=evidence,
            provenance={
                "probe_id": "step4w_s5",
                "mechanism_id": "S5",
                "mechanism_source": "CANONICAL_REASONING_WEAKNESS",
                "condition": "canonical_empty",
                "source_state": spec["source_state"],
                "raw_tau2_result_path": str(raw_path),
                "manifest": str(MANIFEST_PATH),
                "manifest_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest(),
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


def run(root: Path, concurrency: int) -> dict:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    campaign = json.loads(CAMPAIGN_PATH.read_text())
    context = v14.load_authoritative_domain_contexts(PROJECT_ROOT / campaign["benchmark"]["path"])["airline"]
    jobs = [
        (spec, tasks[spec["task_id"]], index, seed, campaign, context, root)
        for spec in manifest["tasks"]
        for index, seed in enumerate(manifest["rollout_seeds"], 1)
    ]
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for future in as_completed([pool.submit(_one, *job) for job in jobs]):
            results.append(future.result())
    results.sort(key=lambda row: row["path"])
    summary = {
        "condition": "canonical_empty",
        "tasks": len(manifest["tasks"]),
        "seeds": manifest["rollout_seeds"],
        "rollouts": len(jobs),
        "completed": sum(row["status"] == "completed" for row in results),
        "errors": sum(row["status"] == "error" for row in results),
        "results": results,
    }
    _write(root / "run_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--max-concurrency", type=int, default=2)
    args = parser.parse_args()
    result = run(args.output_root, args.max_concurrency)
    print(json.dumps(result, indent=2))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
