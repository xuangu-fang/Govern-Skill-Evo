"""Run the frozen Step 4R Deep-Dependency suite with v14 and Empty Skill."""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

from tau2.data_model.simulation import SimulationRun
from tau2.run import run_single_task

from benchmarks.tau2_governed_evolution.intent_dynamics import (
    run_airline_complex_upfront_empty_rollouts as shared,
)
from benchmarks.tau2_governed_evolution.intent_dynamics.validate_airline_deep_dependency import (
    MANIFEST_PATH,
    TASKS_PATH,
    load_suite,
)
from src.adapters.tau2.tau3_gse_runtime import write_rollout_artifact
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACT_ROOT = PROJECT_ROOT / "artifacts/airline_deep_dependency_step4r"


def validate_run_contract(manifest: dict[str, Any], campaign: dict[str, Any]) -> None:
    v14.validate_campaign_contract(campaign)
    if (
        manifest.get("selection_status") != "frozen_before_empty_skill_rollouts"
        or manifest.get("selection_basis") != "real_state_branch_audit_only"
        or manifest.get("empty_rollout_outcomes_used_for_selection") is not False
        or manifest.get("rollout_seeds") != [620, 621, 622]
        or len(manifest.get("tasks", [])) != 6
    ):
        raise ValueError("Step 4R frozen run contract drifted")
    if campaign["initial_parent"]["kind"] != "empty_skill":
        raise ValueError("Step 4R must run the Empty Skill baseline")


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
    output, raw_path, error_path = shared._paths(artifact_root, task_id, index)
    if shared._reusable(
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
            simulation = run_single_task(
                shared._config(campaign, task_id, seed), task, seed=seed
            )
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(
                simulation.model_dump_json(indent=2) + "\n", encoding="utf-8"
            )
        evidence = v14._build_governed_evidence(
            source_id=f"deep_dependency_{task_id}_rollout_{index:02d}",
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
            task_id=task_id,
            phase="phase_a_deep_dependency_upfront",
            skill_version="S0",
            rollout_index=index,
            rollout_seed=seed,
            governed_evidence=evidence,
            provenance={
                "audit_id": "airline_deep_dependency_step4r",
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
        shared._write_json(
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


def main() -> int:
    # Reuse only the established orchestration; Step 4R owns its frozen contract,
    # loader, artifact namespace, and per-rollout provenance above.
    shared.MANIFEST_PATH = MANIFEST_PATH
    shared.TASKS_PATH = TASKS_PATH
    shared.DEFAULT_ARTIFACT_ROOT = DEFAULT_ARTIFACT_ROOT
    shared.load_suite = load_suite
    shared.validate_run_contract = validate_run_contract
    shared._run_one = _run_one
    result = shared.run_audit(artifact_root=DEFAULT_ARTIFACT_ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
