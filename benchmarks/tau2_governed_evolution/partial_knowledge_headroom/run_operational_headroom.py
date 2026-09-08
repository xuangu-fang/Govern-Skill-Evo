"""Run matched Full/Partial Empty-Skill rollouts for Step 4W."""

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

from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import _config  # noqa: E402
from benchmarks.tau2_governed_evolution.capability_expansion.validate_phase_a_capability_tasks import CAMPAIGN_PATH, PROJECT_ROOT  # noqa: E402
from benchmarks.tau2_governed_evolution.partial_knowledge_headroom.build_partial_operational_views import (  # noqa: E402
    AIRLINE_O3_POLICY, O2_TOOL_DESCRIPTION, REGISTRY_PATH, RETAIL_O1_POLICY, build, sha256_text,
)
from benchmarks.tau2_governed_evolution.partial_knowledge_headroom.validate_operational_headroom_tasks import load_suite  # noqa: E402
from src.adapters.tau2.tau3_gse_runtime import write_rollout_artifact  # noqa: E402
from src.skill_evolution import autonomous_gse_v14_benchmark_runtime as v14  # noqa: E402


DEFAULT_ROOT = PROJECT_ROOT / "artifacts/partial_knowledge_headroom_step4w"
PROBE_SKILL = PROJECT_ROOT / "artifacts/transition_ablation_step4v/learning/S_A_transition.md"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def _view(orchestrator: Any, spec: dict, condition: str) -> dict:
    if condition in {"partial_empty", "partial_skill"}:
        if spec["knowledge_id"] == "O1":
            orchestrator.agent.domain_policy = RETAIL_O1_POLICY.read_text()
        elif spec["knowledge_id"] == "O3":
            orchestrator.agent.domain_policy = AIRLINE_O3_POLICY.read_text()
        elif spec["knowledge_id"] == "O2":
            found = False
            for tool in orchestrator.agent.tools:
                if tool.name == "update_reservation_flights":
                    tool.short_desc = O2_TOOL_DESCRIPTION
                    tool.long_desc = ""
                    found = True
            if not found:
                raise ValueError("update_reservation_flights tool not found")
    prompt = orchestrator.agent.system_prompt
    descriptions = {tool.name: tool.openai_schema["function"]["description"] for tool in orchestrator.agent.tools}
    if condition == "partial_empty":
        if spec["knowledge_id"] == "O1" and re.search(r"not be able to modify or cancel|pending \(items modifed\)", prompt, re.I):
            raise ValueError("O1 partial view leaks transition")
        if spec["knowledge_id"] == "O2" and re.search(r"ENTIRE new reservation|segment is not changed.*included", descriptions["update_reservation_flights"], re.I):
            raise ValueError("O2 partial tool leaks replacement semantics")
        if spec["knowledge_id"] == "O3" and re.search(r"prices will not be updated based on the current price", prompt, re.I):
            raise ValueError("O3 partial policy leaks preserved pricing")
    return {"policy_sha256": sha256_text(orchestrator.agent.domain_policy), "prompt_sha256": sha256_text(prompt), "tools_sha256": hashlib.sha256(json.dumps(descriptions, sort_keys=True).encode()).hexdigest()}


def _one(condition: str, spec: dict, task: Any, index: int, seed: int, campaign: dict, context: dict, root: Path) -> dict:
    directory = root / condition
    path = directory / f"{task.id}_rollout_{index:02d}.json"
    raw_path = directory / f"{task.id}_rollout_{index:02d}_tau2_raw.json"
    error_path = directory / f"{task.id}_rollout_{index:02d}_error.json"
    try:
        config = _config(campaign, spec, seed)
        if condition == "partial_skill":
            config = config.model_copy(update={"agent": "llm_agent_manual_skill"})
        orchestrator = build_text_orchestrator(config, task, seed=seed)
        view = _view(orchestrator, spec, condition)
        simulation = run_simulation(orchestrator, nl_assertions_model=campaign["official_evaluator"]["nl_assertions_model"], nl_assertions_llm_args={"temperature": campaign["official_evaluator"]["nl_assertions_temperature"]})
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(simulation.model_dump_json(indent=2) + "\n")
        evidence = v14._build_governed_evidence(source_id=f"step4w_{condition}_{task.id}_{index}", domain=spec["domain"], task=task, simulation=simulation, domain_policy=context["original_domain_policy"], available_tool_contracts=context["available_tool_contracts"], judge_caller=v14.compliance_v13.default_judge_caller)
        write_rollout_artifact(path, domain=spec["domain"], task_id=task.id, phase="phase_a_operational_headroom", skill_version="S_A_transition_probe" if condition == "partial_skill" else "S0", rollout_index=index, rollout_seed=seed, governed_evidence=evidence, provenance={"probe_id": "step4w", "knowledge_id": spec["knowledge_id"], "condition": condition, "source_state": spec["source_state"], "raw_tau2_result_path": str(raw_path), "agent_visible_view": view, "canonical_environment_changed": False, "tool_implementation_changed": False, "task_changed_between_conditions": False, "agent_config": campaign["agent"], "user_simulator_config": campaign["user_simulator"], "official_evaluator_config": campaign["official_evaluator"], "judge_config": campaign["compliance_judge"]})
        error_path.unlink(missing_ok=True)
        return {"path": str(path), "status": "completed"}
    except Exception as error:
        _write(error_path, {"task_id": task.id, "condition": condition, "index": index, "seed": seed, "error": str(error), "traceback": traceback.format_exc()})
        return {"path": str(path), "status": "error", "error": str(error)}


def run(condition: str, root: Path, concurrency: int, units: tuple[str, ...] | None, task_ids: tuple[str, ...] | None = None) -> dict:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    build()
    registry, tasks = load_suite()
    campaign = json.loads(CAMPAIGN_PATH.read_text())
    contexts = v14.load_authoritative_domain_contexts(PROJECT_ROOT / campaign["benchmark"]["path"])
    specs = [spec for spec in registry["tasks"] if (units is None or spec["knowledge_id"] in units) and (task_ids is None or spec["task_id"] in task_ids)]
    jobs = [(condition, spec, tasks[spec["task_id"]], index, seed, campaign, contexts[spec["domain"]], root) for spec in specs for index, seed in enumerate(registry["rollout_seeds"], 1)]
    results = []
    old_skill = os.environ.get("TAU2_AGENT_SKILL_PATH")
    if condition == "partial_skill":
        if not PROBE_SKILL.exists():
            raise FileNotFoundError(PROBE_SKILL)
        os.environ["TAU2_AGENT_SKILL_PATH"] = str(PROBE_SKILL)
    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            for future in as_completed([pool.submit(_one, *job) for job in jobs]):
                results.append(future.result())
    finally:
        if old_skill is None:
            os.environ.pop("TAU2_AGENT_SKILL_PATH", None)
        else:
            os.environ["TAU2_AGENT_SKILL_PATH"] = old_skill
    results.sort(key=lambda item: item["path"])
    summary = {"condition": condition, "units": list(units) if units else ["O1", "O2", "O3"], "tasks": len(specs), "rollouts": len(jobs), "completed": sum(item["status"] == "completed" for item in results), "errors": sum(item["status"] == "error" for item in results), "results": results}
    _write(root / condition / "run_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("condition", choices=("full_empty", "partial_empty", "partial_skill"))
    parser.add_argument("--units", nargs="+", choices=("O1", "O2", "O3"))
    parser.add_argument("--tasks", nargs="+")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--max-concurrency", type=int, default=6)
    args = parser.parse_args()
    value = run(args.condition, args.output_root, args.max_concurrency, tuple(args.units) if args.units else None, tuple(args.tasks) if args.tasks else None)
    print(json.dumps(value, indent=2))
    return 0 if value["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
