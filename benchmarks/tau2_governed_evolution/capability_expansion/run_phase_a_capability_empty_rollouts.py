"""Run the frozen Step 4T cross-domain suite with v14 and Empty Skill."""

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

from tau2.data_model.simulation import SimulationRun, TextRunConfig  # noqa: E402
from tau2.run import run_single_task  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import (  # noqa: E402
    CAMPAIGN_PATH,
    MANIFEST_PATH,
    PROJECT_ROOT,
    TASKS_PATH,
    load_suite,
    validate_run_contract,
)
from src.adapters.tau2.tau3_gse_runtime import (  # noqa: E402
    _trajectory_model_args,
    write_rollout_artifact,
)
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DEFAULT_ARTIFACT_ROOT = PROJECT_ROOT / "artifacts/phase_a_capability_step4t"
VALID_STATES = {
    "compliant_success",
    "compliant_failure",
    "violating_success",
    "violating_failure",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _config(campaign: dict[str, Any], spec: dict[str, Any], seed: int) -> TextRunConfig:
    agent = campaign["agent"]
    user = campaign["user_simulator"]
    evaluator = campaign["official_evaluator"]
    return TextRunConfig(
        domain=spec["domain"],
        task_split_name="train",
        task_ids=[spec["task_id"]],
        agent="llm_agent",
        user="user_simulator",
        llm_agent=agent["model"],
        llm_args_agent=_trajectory_model_args(agent, seed, include_max_tokens=True),
        llm_user=user["model"],
        llm_args_user=_trajectory_model_args(user, seed, include_max_tokens=True),
        llm_nl_assertions=evaluator["nl_assertions_model"],
        llm_args_nl_assertions={
            "temperature": evaluator["nl_assertions_temperature"]
        },
        max_steps=agent["max_steps"],
        seed=seed,
        max_retries=0,
        auto_review=False,
    )


def _paths(root: Path, task_id: str, index: int) -> tuple[Path, Path, Path]:
    stem = f"{task_id}_rollout_{index:02d}"
    directory = root / "rollouts"
    return (
        directory / f"{stem}.json",
        directory / f"{stem}_tau2_raw.json",
        directory / f"{stem}_error.json",
    )


def _reusable(
    path: Path, *, task_id: str, index: int, seed: int, manifest_hash: str
) -> bool:
    try:
        value = _load_json(path)
        return (
            value["task_id"] == task_id
            and value["skill_version"] == "S0"
            and value["rollout_index"] == index
            and value["rollout_seed"] == seed
            and value["state"] in VALID_STATES
            and value["provenance"]["candidate_manifest_sha256"] == manifest_hash
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _run_one(
    *,
    spec: dict[str, Any],
    task: Any,
    index: int,
    seed: int,
    campaign: dict[str, Any],
    artifact_root: Path,
    manifest_hash: str,
    domain_context: dict[str, Any],
) -> dict[str, Any]:
    task_id = spec["task_id"]
    output, raw_path, error_path = _paths(artifact_root, task_id, index)
    if _reusable(
        output,
        task_id=task_id,
        index=index,
        seed=seed,
        manifest_hash=manifest_hash,
    ):
        return {"path": output.as_posix(), "status": "reused"}
    try:
        if raw_path.is_file():
            simulation = SimulationRun.model_validate_json(raw_path.read_text())
        else:
            simulation = run_single_task(_config(campaign, spec, seed), task, seed=seed)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(
                simulation.model_dump_json(indent=2) + "\n", encoding="utf-8"
            )
        evidence = v14._build_governed_evidence(
            source_id=f"step4t_{task_id}_rollout_{index:02d}",
            domain=spec["domain"],
            task=task,
            simulation=simulation,
            domain_policy=domain_context["original_domain_policy"],
            available_tool_contracts=domain_context["available_tool_contracts"],
            judge_caller=v14.compliance_v13.default_judge_caller,
        )
        write_rollout_artifact(
            output,
            domain=spec["domain"],
            task_id=task_id,
            phase="phase_a_cross_domain_capability_expansion",
            skill_version="S0",
            rollout_index=index,
            rollout_seed=seed,
            governed_evidence=evidence,
            provenance={
                "audit_id": "phase_a_cross_domain_capability_expansion_step4t",
                "source_state": spec["source_state"],
                "raw_tau2_result_path": raw_path.as_posix(),
                "candidate_manifest": MANIFEST_PATH.as_posix(),
                "candidate_manifest_sha256": manifest_hash,
                "task_definitions": TASKS_PATH.as_posix(),
                "skill_kind": "empty_skill",
                "skill_injection": None,
                "agent_config": campaign["agent"],
                "user_simulator_config": campaign["user_simulator"],
                "official_evaluator_config": campaign["official_evaluator"],
                "judge_config": campaign["compliance_judge"],
            },
        )
        error_path.unlink(missing_ok=True)
        return {"path": output.as_posix(), "status": "completed"}
    except Exception as error:
        _write_json(
            error_path,
            {
                "task_id": task_id,
                "rollout_index": index,
                "rollout_seed": seed,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        return {
            "path": output.as_posix(),
            "status": "error",
            "error": f"{type(error).__name__}: {error}",
        }


def run_audit(
    *, artifact_root: Path = DEFAULT_ARTIFACT_ROOT, task_ids: tuple[str, ...] | None = None
) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    manifest, tasks = load_suite()
    campaign = _load_json(CAMPAIGN_PATH)
    validate_run_contract(manifest, campaign)
    manifest_hash = _sha256(MANIFEST_PATH)
    specs = {item["task_id"]: item for item in manifest["tasks"]}
    selected_ids = set(task_ids) if task_ids else set(specs)
    if not selected_ids <= set(specs):
        raise ValueError("Unknown --tasks value")
    contexts = v14.load_authoritative_domain_contexts(
        PROJECT_ROOT / campaign["benchmark"]["path"]
    )
    jobs = [
        {
            "spec": specs[task_id],
            "task": tasks[task_id],
            "index": index,
            "seed": seed,
            "campaign": campaign,
            "artifact_root": artifact_root,
            "manifest_hash": manifest_hash,
            "domain_context": contexts[specs[task_id]["domain"]],
        }
        for task_id in sorted(selected_ids)
        for index, seed in enumerate(manifest["rollout_seeds"], start=1)
    ]
    results = []
    with ThreadPoolExecutor(max_workers=campaign["execution"]["max_concurrency"]) as pool:
        futures = [pool.submit(_run_one, **job) for job in jobs]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["path"])
    summary = {
        "audit_id": manifest["benchmark_id"],
        "artifact_root": artifact_root.as_posix(),
        "candidate_manifest_sha256": manifest_hash,
        "selected_tasks": len(selected_ids),
        "rollouts": len(jobs),
        "completed": sum(item["status"] == "completed" for item in results),
        "reused": sum(item["status"] == "reused" for item in results),
        "errors": sum(item["status"] == "error" for item in results),
        "results": results,
    }
    _write_json(artifact_root / "run_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--tasks", nargs="+")
    args = parser.parse_args()
    result = run_audit(
        artifact_root=args.artifact_root,
        task_ids=tuple(args.tasks) if args.tasks else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
