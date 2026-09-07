"""Run the frozen Step 4 Phase-A audit pool with the v14 Base Agent and S0."""

from __future__ import annotations

import argparse
import hashlib
import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.compiler.resolvers import (
    ensure_tau2_importable,
)


ensure_tau2_importable()

from tau2.data_model.simulation import SimulationRun, TextRunConfig  # noqa: E402
from tau2.data_model.tasks import Task  # noqa: E402
from tau2.evaluator import evaluator_nl_assertions  # noqa: E402
from tau2.run import get_tasks, run_single_task  # noqa: E402

from src.adapters.tau2.tau3_gse_runtime import (  # noqa: E402
    _trajectory_model_args,
    write_rollout_artifact,
)
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (  # noqa: E402
    _build_governed_evidence,
    load_authoritative_domain_contexts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = Path(__file__).resolve().parent
MANIFEST_PATH = DIRECTORY / "airline_phase_a_headroom_candidates.json"
CAMPAIGN_PATH = PROJECT_ROOT / "experiments/campaigns/autonomous_gse_v14/campaign_manifest.json"
DEFAULT_ARTIFACT_ROOT = PROJECT_ROOT / "artifacts/airline_phase_a_headroom_step4"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_audit_contract(manifest: dict[str, Any], campaign: dict[str, Any]) -> None:
    v14.validate_campaign_contract(campaign)
    if (
        manifest.get("selection_status") != "frozen_before_base_rollout"
        or manifest.get("selection_basis") != "task_structure_only"
        or manifest.get("outcome_used_for_selection") is not False
        or manifest.get("rollouts_per_task") != 3
        or manifest.get("rollout_seeds") != [400, 401, 402]
    ):
        raise ValueError("Step 4 audit manifest contract drifted")
    tasks = manifest.get("tasks") or []
    if len(tasks) != 12 or len({item["audit_task_id"] for item in tasks}) != 12:
        raise ValueError("Step 4 requires twelve recorded tasks after structural amendments")
    eligible = [
        item
        for item in tasks
        if not item.get("phase_a_conformance", "").startswith("excluded_posthoc")
    ]
    if len(eligible) != 10:
        raise ValueError("Step 4 requires ten Phase-A-conformant tasks")
    if sum(item["layer"] == "c1_upfront_seed" for item in tasks) != 4:
        raise ValueError("Step 4 requires exactly four C1 Upfront seed tasks")
    if sum(item["layer"] == "broader_native" for item in eligible) != 6:
        raise ValueError("Step 4 requires exactly six eligible broader native tasks")
    if campaign["initial_parent"]["kind"] != "empty_skill":
        raise ValueError("Step 4 must use the frozen Empty Skill baseline")


def _load_task(spec: dict[str, Any]) -> Task:
    if spec["source_kind"] == "realized_task_file":
        values = _load_json(DIRECTORY / spec["task_file"])
        matches = [value for value in values if value["id"] == spec["audit_task_id"]]
        if len(matches) != 1:
            raise ValueError(f"Cannot resolve {spec['audit_task_id']}")
        return Task.model_validate(matches[0])
    if spec["source_kind"] == "official_native_task":
        tasks = get_tasks(
            "airline",
            task_split_name=spec["official_source_split"],
            task_ids=[spec["source_task_id"]],
        )
        if len(tasks) != 1:
            raise ValueError(f"Cannot resolve native task {spec['source_task_id']}")
        return tasks[0]
    raise ValueError(f"Unknown task source: {spec['source_kind']}")


def _config(campaign: dict[str, Any], spec: dict[str, Any], seed: int) -> TextRunConfig:
    agent = campaign["agent"]
    user = campaign["user_simulator"]
    return TextRunConfig(
        domain="airline",
        task_split_name=spec["official_source_split"],
        task_ids=[spec["source_task_id"]],
        agent="llm_agent",
        user="user_simulator",
        llm_agent=agent["model"],
        llm_args_agent=_trajectory_model_args(agent, seed, include_max_tokens=True),
        llm_user=user["model"],
        llm_args_user=_trajectory_model_args(user, seed, include_max_tokens=True),
        max_steps=agent["max_steps"],
        seed=seed,
        max_retries=0,
        auto_review=False,
    )


def _artifact_paths(
    artifact_root: Path, audit_task_id: str, rollout_index: int
) -> tuple[Path, Path, Path]:
    root = artifact_root / "rollouts"
    stem = f"{audit_task_id}_rollout_{rollout_index:02d}"
    return root / f"{stem}.json", root / f"{stem}_tau2_raw.json", root / f"{stem}_error.json"


def _reusable(
    path: Path,
    *,
    audit_task_id: str,
    rollout_index: int,
    seed: int,
    manifest_sha256: str,
) -> bool:
    try:
        value = _load_json(path)
        return (
            value["task_id"] == audit_task_id
            and value["skill_version"] == "S0"
            and value["rollout_index"] == rollout_index
            and value["rollout_seed"] == seed
            and value["state"] in {"compliant_success", "compliant_failure", "violating_success", "violating_failure"}
            and value["provenance"]["candidate_manifest_sha256"] == manifest_sha256
        )
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _run_one(
    *,
    spec: dict[str, Any],
    rollout_index: int,
    seed: int,
    campaign: dict[str, Any],
    artifact_root: Path,
    manifest_sha256: str,
    domain_context: dict[str, Any],
) -> dict[str, Any]:
    output, raw_path, error_path = _artifact_paths(
        artifact_root, spec["audit_task_id"], rollout_index
    )
    if _reusable(
        output,
        audit_task_id=spec["audit_task_id"],
        rollout_index=rollout_index,
        seed=seed,
        manifest_sha256=manifest_sha256,
    ):
        return {"path": output.as_posix(), "status": "reused"}
    try:
        task = _load_task(spec)
        if raw_path.is_file():
            simulation = SimulationRun.model_validate_json(raw_path.read_text())
        else:
            simulation = run_single_task(
                _config(campaign, spec, seed), task, seed=seed
            )
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        source_id = (
            f"phase_a_headroom_{spec['audit_task_id']}_rollout_{rollout_index:02d}"
        )
        evidence = _build_governed_evidence(
            source_id=source_id,
            domain="airline",
            task=task,
            simulation=simulation,
            domain_policy=domain_context["original_domain_policy"],
            available_tool_contracts=domain_context["available_tool_contracts"],
            judge_caller=v14.compliance_v13.default_judge_caller,
        )
        write_rollout_artifact(
            output,
            domain="airline",
            task_id=spec["audit_task_id"],
            phase="phase_a_headroom",
            skill_version="S0",
            rollout_index=rollout_index,
            rollout_seed=seed,
            governed_evidence=evidence,
            provenance={
                "audit_id": "airline_phase_a_headroom_step4",
                "source_kind": spec["source_kind"],
                "source_task_id": spec["source_task_id"],
                "official_source_split": spec["official_source_split"],
                "raw_tau2_result_path": raw_path.as_posix(),
                "candidate_manifest": MANIFEST_PATH.as_posix(),
                "candidate_manifest_sha256": manifest_sha256,
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
                "audit_task_id": spec["audit_task_id"],
                "rollout_index": rollout_index,
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
    manifest, campaign = _load_json(MANIFEST_PATH), _load_json(CAMPAIGN_PATH)
    validate_audit_contract(manifest, campaign)
    manifest_hash = _sha256(MANIFEST_PATH)
    selected = [
        spec
        for spec in manifest["tasks"]
        if (
            spec["audit_task_id"] in task_ids
            if task_ids is not None
            else not spec.get("phase_a_conformance", "").startswith(
                "excluded_posthoc"
            )
        )
    ]
    if task_ids is not None and {item["audit_task_id"] for item in selected} != set(task_ids):
        raise ValueError("Unknown --tasks value")

    evaluator = campaign["official_evaluator"]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS = evaluator[
        "nl_assertions_model"
    ]
    evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS_ARGS = {
        "temperature": evaluator["nl_assertions_temperature"]
    }
    context = load_authoritative_domain_contexts(
        PROJECT_ROOT / campaign["benchmark"]["path"]
    )["airline"]
    jobs = [
        {
            "spec": spec,
            "rollout_index": index,
            "seed": seed,
            "campaign": campaign,
            "artifact_root": artifact_root,
            "manifest_sha256": manifest_hash,
            "domain_context": context,
        }
        for spec in selected
        for index, seed in enumerate(manifest["rollout_seeds"], start=1)
    ]
    results = []
    with ThreadPoolExecutor(max_workers=campaign["execution"]["max_concurrency"]) as executor:
        futures = [executor.submit(_run_one, **job) for job in jobs]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["path"])
    summary = {
        "audit_id": manifest["audit_id"],
        "artifact_root": artifact_root.as_posix(),
        "candidate_manifest_sha256": manifest_hash,
        "selected_tasks": len(selected),
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
