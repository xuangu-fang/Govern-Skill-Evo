"""Run matched Full/Partial Empty-Skill rollouts for Step 4V."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchmarks.tau2_governed_evolution.compiler.resolvers import ensure_tau2_importable


ensure_tau2_importable()

from tau2.runner.build import build_text_orchestrator  # noqa: E402
from tau2.runner.simulation import run_simulation  # noqa: E402

from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import (  # noqa: E402
    _config,
)
from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import (  # noqa: E402
    CAMPAIGN_PATH,
    PROJECT_ROOT,
)
from benchmarks.tau2_governed_evolution.transition_ablation.build_transition_probe import (  # noqa: E402
    CANONICAL_POLICY_PATH,
    FORBIDDEN_PATTERNS,
    MANIFEST_PATH,
    PARTIAL_POLICY_PATH,
    TASKS_PATH,
    build,
    sha256_text,
)
from benchmarks.tau2_governed_evolution.transition_ablation.validate_transition_probe import (  # noqa: E402
    EXPERIMENT_MANIFEST,
    load_suite,
)
from src.adapters.tau2.tau3_gse_runtime import write_rollout_artifact  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DEFAULT_ROOT = PROJECT_ROOT / "artifacts/transition_ablation_step4v"
LEARNED_SKILL_PATH = DEFAULT_ROOT / "learning/S_A_transition.md"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _apply_view(orchestrator: Any, condition: str, partial_policy: str) -> dict[str, Any]:
    if condition in {"partial_empty", "partial_skill"}:
        orchestrator.agent.domain_policy = partial_policy
    visible_prompt = orchestrator.agent.system_prompt
    tool_descriptions = {
        tool.name: tool.openai_schema["function"]["description"]
        for tool in orchestrator.agent.tools
    }
    hits = [pattern for pattern in FORBIDDEN_PATTERNS if re.search(pattern, visible_prompt, re.I)]
    tool_hits = {
        name: [pattern for pattern in FORBIDDEN_PATTERNS if re.search(pattern, desc, re.I)]
        for name, desc in tool_descriptions.items()
    }
    tool_hits = {name: values for name, values in tool_hits.items() if values}
    if condition in {"partial_empty", "partial_skill"} and (hits or tool_hits):
        raise ValueError(f"partial runtime leaks transition semantics: prompt={hits}, tools={tool_hits}")
    return {
        "policy_sha256": sha256_text(orchestrator.agent.domain_policy),
        "system_prompt_sha256": sha256_text(visible_prompt),
        "tool_descriptions_sha256": hashlib.sha256(
            json.dumps(tool_descriptions, sort_keys=True).encode()
        ).hexdigest(),
    }


def _run_one(
    *, condition: str, spec: dict[str, Any], task: Any, index: int, seed: int,
    campaign: dict[str, Any], context: dict[str, Any], output_root: Path,
    partial_policy: str,
) -> dict[str, Any]:
    directory = output_root / condition
    path = directory / f"{task.id}_rollout_{index:02d}.json"
    raw_path = directory / f"{task.id}_rollout_{index:02d}_tau2_raw.json"
    error_path = directory / f"{task.id}_rollout_{index:02d}_error.json"
    try:
        config = _config(campaign, spec, seed)
        if condition == "partial_skill":
            config = config.model_copy(update={"agent": "llm_agent_manual_skill"})
        orchestrator = build_text_orchestrator(config, task, seed=seed)
        visible_view = _apply_view(orchestrator, condition, partial_policy)
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
            source_id=f"step4v_{condition}_{task.id}_{index:02d}",
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
            phase="phase_a_transition_ablation",
            skill_version="S_A_transition" if condition == "partial_skill" else "S0",
            rollout_index=index,
            rollout_seed=seed,
            governed_evidence=evidence,
            provenance={
                "probe_id": "step4v_retail_pending_item_transition",
                "condition": condition,
                "source_state": spec["source_state"],
                "raw_tau2_result_path": raw_path.as_posix(),
                "candidate_manifest": MANIFEST_PATH.as_posix(),
                "task_definitions": TASKS_PATH.as_posix(),
                "agent_visible_policy_path": (
                    PARTIAL_POLICY_PATH.as_posix()
                    if condition in {"partial_empty", "partial_skill"}
                    else CANONICAL_POLICY_PATH.as_posix()
                ),
                "agent_visible_view": visible_view,
                "canonical_policy_sha256": sha256_text(context["original_domain_policy"]),
                "canonical_environment_changed": False,
                "tool_implementation_changed": False,
                "task_changed_between_conditions": False,
                "skill_kind": (
                    "learned_transition_skill" if condition == "partial_skill"
                    else "empty_skill"
                ),
                "agent_config": campaign["agent"],
                "user_simulator_config": campaign["user_simulator"],
                "official_evaluator_config": campaign["official_evaluator"],
                "judge_config": campaign["compliance_judge"],
            },
        )
        error_path.unlink(missing_ok=True)
        return {"path": path.as_posix(), "status": "completed"}
    except Exception as error:
        _write(
            error_path,
            {
                "task_id": task.id,
                "condition": condition,
                "rollout_index": index,
                "rollout_seed": seed,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        return {"path": path.as_posix(), "status": "error", "error": str(error)}


def run(
    condition: str,
    output_root: Path,
    max_concurrency: int,
    task_ids: tuple[str, ...] | None = None,
    rollout_indices: tuple[int, ...] | None = None,
) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    build()
    manifest, tasks = load_suite()
    experiment = _load(EXPERIMENT_MANIFEST)
    campaign = _load(CAMPAIGN_PATH)
    if condition not in {"full_empty", "partial_empty", "partial_skill"}:
        raise ValueError("unknown condition")
    if campaign["initial_parent"]["kind"] != "empty_skill":
        raise ValueError("Step 4V Empty conditions require Empty Skill")
    contexts = v14.load_authoritative_domain_contexts(
        PROJECT_ROOT / campaign["benchmark"]["path"]
    )
    canonical = contexts["retail"]["original_domain_policy"]
    if sha256_text(canonical) != sha256_text(CANONICAL_POLICY_PATH.read_text(encoding="utf-8")):
        raise ValueError("canonical Retail policy source drifted")
    partial_policy = PARTIAL_POLICY_PATH.read_text(encoding="utf-8")
    specs = {item["task_id"]: item for item in manifest["tasks"]}
    selected_ids = list(task_ids) if task_ids else experiment["task_ids"]
    if not set(selected_ids) <= set(specs):
        raise ValueError("unknown --tasks value")
    selected_rollouts = [
        (index, seed)
        for index, seed in enumerate(experiment["rollout_seeds"], 1)
        if rollout_indices is None or index in rollout_indices
    ]
    if rollout_indices is not None and len(selected_rollouts) != len(set(rollout_indices)):
        raise ValueError("unknown --rollout-indices value")
    jobs = [
        dict(
            condition=condition,
            spec=specs[task_id],
            task=tasks[task_id],
            index=index,
            seed=seed,
            campaign=campaign,
            context=contexts["retail"],
            output_root=output_root,
            partial_policy=partial_policy,
        )
        for task_id in selected_ids
        for index, seed in selected_rollouts
    ]
    results = []
    previous_skill = os.environ.get("TAU2_AGENT_SKILL_PATH")
    if condition == "partial_skill":
        if not LEARNED_SKILL_PATH.exists():
            raise FileNotFoundError(LEARNED_SKILL_PATH)
        os.environ["TAU2_AGENT_SKILL_PATH"] = str(LEARNED_SKILL_PATH.resolve())
    try:
        with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
            futures = [pool.submit(_run_one, **job) for job in jobs]
            for future in as_completed(futures):
                results.append(future.result())
    finally:
        if previous_skill is None:
            os.environ.pop("TAU2_AGENT_SKILL_PATH", None)
        else:
            os.environ["TAU2_AGENT_SKILL_PATH"] = previous_skill
    results.sort(key=lambda item: item["path"])
    summary = {
        "probe_id": experiment["probe_id"],
        "condition": condition,
        "tasks": len(selected_ids),
        "rollouts": len(jobs),
        "completed": sum(item["status"] == "completed" for item in results),
        "errors": sum(item["status"] == "error" for item in results),
        "results": results,
    }
    _write(output_root / condition / "run_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("condition", choices=("full_empty", "partial_empty", "partial_skill"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--max-concurrency", type=int, default=6)
    parser.add_argument("--tasks", nargs="+")
    parser.add_argument("--rollout-indices", nargs="+", type=int)
    args = parser.parse_args()
    result = run(
        args.condition,
        args.output_root,
        args.max_concurrency,
        tuple(args.tasks) if args.tasks else None,
        tuple(args.rollout_indices) if args.rollout_indices else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
