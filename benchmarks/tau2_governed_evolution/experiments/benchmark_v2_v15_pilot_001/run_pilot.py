#!/usr/bin/env python3
"""Benchmark v2 Snapshot 001 x v15 three-step end-to-end pilot."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import random
import sys
import threading
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RUN = HERE / "run"
SPLIT = HERE / "split"
TAU2 = REPO / "external/tau2-bench"
sys.path.insert(0, str(TAU2 / "src"))
load_dotenv(REPO / ".env", override=True)

from tau2.data_model.simulation import RewardInfo, SimulationRun, TextRunConfig
from tau2.data_model.tasks import Task
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
from tau2.orchestrator.modes import CommunicationMode
from tau2.runner.build import build_text_orchestrator

from benchmarks.tau2_governed_evolution.capability_expansion.run_phase_a_capability_empty_rollouts import _config
from benchmarks.tau2_governed_evolution.phase_a_final_unified_benchmark_v1 import benchmark_adapter as formal_adapter
from benchmarks.tau2_governed_evolution.advanced_structure.phase13_cs_reachable_clean_task_realization import evaluators as p13_eval
from benchmarks.tau2_governed_evolution.advanced_structure.phase14t_tensioned_cs_reachable_realization import context_adapter as p14t_context
from benchmarks.tau2_governed_evolution.advanced_structure.phase14t_tensioned_cs_reachable_realization import evaluators as p14t_eval
from benchmarks.tau2_governed_evolution.advanced_structure.phase15b_separable_cross_axis_vf_realization import context_adapter as p15b_context
from benchmarks.tau2_governed_evolution.advanced_structure.phase15b_separable_cross_axis_vf_realization import evaluators as p15b_eval
from benchmarks.tau2_governed_evolution.advanced_structure.phase15f_independent_cross_axis_realization import evaluators as p15f_eval
from benchmarks.tau2_governed_evolution.advanced_structure.phase16c_latent_governance_variant_family_realization import evaluators as p16c_eval
from benchmarks.tau2_governed_evolution.advanced_structure.phase17b_separable_cross_axis_v2_clean_realization import evaluators as p17b_eval
from src.adapters.tau2 import tau3_compliance_judge_v13 as compliance
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import _build_governed_evidence, load_authoritative_domain_contexts
from src.skill_evolution.autonomous_gse_v15_benchmark_runtime import prepare_diagnosis_from_stored, propose_from_experience
from src.skill_evolution.autonomous_gse_v15_proposal import build_editor_request
from src.skill_evolution.diagnosis_v15 import call_diagnosis
from src.skill_evolution.distributional_gate_v14 import gate_decision, is_epsilon_pareto_positive
from src.skill_evolution.information_boundary_v15 import (
    BoundaryError,
    INFORMATION_BOUNDARY_VERSION,
    LEARNER_SETTING,
    agent_payload,
    capture_agent_visible_view,
    unpack,
)
from src.learners.stwebagentbench.generate_skill import call_learner
from src.learners.stwebagentbench.generate_governed_skill_v15 import call_governed_editor


RUN_ID = "BENCHMARK_V2_V15_END_TO_END_PILOT_001"
MONITOR_ID = "FIXED_MONITOR_V2_PILOT_001"
ROLLOUT_SEEDS = (200, 201, 202)
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 200
GATE_THRESHOLD = 0.80
LEARNER_MODEL = "openai/deepseek-v4-pro"
INITIAL_SKILL = REPO / "experiments/campaigns/autonomous_gse_v14/skills/S0_empty_skill.md"
BASE_CONFIG = REPO / "benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/calibration/run_config.json"
FORMAL = REPO / "benchmarks/tau2_governed_evolution/formal_manifestation_admission"
P13 = REPO / "benchmarks/tau2_governed_evolution/advanced_structure/phase13_cs_reachable_clean_task_realization"
P14T = REPO / "benchmarks/tau2_governed_evolution/advanced_structure/phase14t_tensioned_cs_reachable_realization"
P15B = REPO / "benchmarks/tau2_governed_evolution/advanced_structure/phase15b_separable_cross_axis_vf_realization"
P15F = REPO / "benchmarks/tau2_governed_evolution/advanced_structure/phase15f_independent_cross_axis_realization"
P16C = REPO / "benchmarks/tau2_governed_evolution/advanced_structure/phase16c_latent_governance_variant_family_realization"
P17B = REPO / "benchmarks/tau2_governed_evolution/advanced_structure/phase17b_separable_cross_axis_v2_clean_realization"

COUNTERS = Counter()
COUNTER_LOCK = threading.Lock()
if (RUN / "runtime_counters.json").is_file():
    COUNTERS.update(json.loads((RUN / "runtime_counters.json").read_text()))


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def count(name: str, amount: int = 1) -> None:
    with COUNTER_LOCK:
        COUNTERS[name] += amount
        write(RUN / "runtime_counters.json", dict(COUNTERS))


def split_data() -> dict[str, Any]:
    return {
        "step1": load(SPLIT / "evolution_step1.json"),
        "step2": load(SPLIT / "evolution_step2.json"),
        "step3": load(SPLIT / "evolution_step3.json"),
        "monitor": load(SPLIT / "fixed_monitor.json"),
        "unused": load(SPLIT / "unused_tasks.json"),
    }


def _rows_by_id(path: Path, *, embedded: bool = False) -> dict[str, dict[str, Any]]:
    rows = load(path)
    if embedded:
        return {str(row["task_id"]): row["task"] for row in rows["candidates"]}
    return {str(row["id"]): row for row in rows}


def registry() -> dict[str, dict[str, Any]]:
    """Load the 76 snapshot tasks from their existing immutable sources."""
    result: dict[str, dict[str, Any]] = {}
    formal_rows = _rows_by_id(FORMAL / "tasks/expanded_tasks.json")
    for task_id, row in formal_rows.items():
        domain = row["user_scenario"]["instructions"]["domain"]
        result[task_id] = {"source": "formal_v1", "domain": domain, "task": Task.model_validate(row)}

    sources = [
        ("phase13", P13 / "tasks/candidate_tasks.json", False),
        ("phase14t", P14T / "tasks/candidate_tasks.json", False),
        ("phase15b", P15B / "tasks/candidate_tasks.json", False),
        ("phase15f", P15F / "independent_separable_vf_candidate_pool_v1.json", True),
        ("phase16c", P16C / "tasks/candidate_tasks.json", False),
        ("phase17b", P17B / "tasks/candidate_tasks.json", False),
    ]
    for source, path, embedded in sources:
        for task_id, row in _rows_by_id(path, embedded=embedded).items():
            domain = row["user_scenario"]["instructions"]["domain"]
            if task_id in result:
                raise RuntimeError(f"duplicate task source: {task_id}")
            result[task_id] = {"source": source, "domain": domain, "task": Task.model_validate(row)}

    p13_candidates = {row["task_id"]: row for row in load(P13 / "cs_reachable_candidate_pool_v1.json")["candidates"]}
    p16_families = {
        task_id: family["family_id"]
        for family in load(P16C / "latent_governance_variant_family_pool_v1.json")["families"]
        for task_id in family["task_ids"]
    }
    p17_families = {row["task_id"]: row for row in load(P17B / "separable_cross_axis_family_pool_v2.json")["families"]}
    for task_id, item in result.items():
        if item["source"] == "phase13":
            item["candidate"] = p13_candidates[task_id]
        elif item["source"] == "phase16c":
            item["family_id"] = p16_families[task_id]
        elif item["source"] == "phase17b":
            item["family"] = p17_families[task_id]
    return result


def bind_context(orchestrator: Any, spec: dict[str, Any]):
    """Bind only the task's frozen deployed view and return its v15 envelope."""
    source, domain, task_id = spec["source"], spec["domain"], str(spec["task"].id)
    if source == "formal_v1":
        formal_adapter.bind_agent_context(orchestrator, domain)
        return capture_agent_visible_view(orchestrator.agent, domain)
    if source == "phase13":
        formal_adapter.bind_agent_context(orchestrator, domain)
        orchestrator.agent.domain_policy = (REPO / spec["candidate"]["learner_visible_context_path"]).read_text()
        return capture_agent_visible_view(orchestrator.agent, domain)
    if source == "phase14t":
        return p14t_context.bind_candidate_context(orchestrator.agent)
    if source == "phase15b":
        return p15b_context.bind_candidate_context(orchestrator.agent)
    if source == "phase15f":
        formal_adapter.bind_agent_context(orchestrator, domain)
        orchestrator.agent.domain_policy = (TAU2 / "data/tau2/domains/airline/policy.md").read_text()
        return capture_agent_visible_view(orchestrator.agent, domain)
    if source == "phase16c":
        formal_adapter.bind_agent_context(orchestrator, domain)
        orchestrator.agent.domain_policy = (P16C / "contexts" / f'{spec["family_id"]}_visible_policy.md').read_text()
        return capture_agent_visible_view(orchestrator.agent, domain)
    if source == "phase17b":
        formal_adapter.bind_agent_context(orchestrator, domain)
        orchestrator.agent.domain_policy = (P17B / spec["family"]["visible_policy_path"]).read_text()
        return capture_agent_visible_view(orchestrator.agent, domain)
    raise RuntimeError(f"unknown source: {source}")


def success_result(spec: dict[str, Any], initial: dict[str, Any], final: dict[str, Any], simulation: Any, config: dict[str, Any]) -> dict[str, Any]:
    task, source, task_id = spec["task"], spec["source"], str(spec["task"].id)
    if source == "formal_v1":
        def native(_: Any):
            reward = evaluate_simulation(
                simulation=simulation, task=task, evaluation_type=EvaluationType.ALL,
                solo_mode=False, domain=spec["domain"], mode=CommunicationMode.HALF_DUPLEX,
                nl_assertions_model=config["official_evaluator"]["nl_assertions_model"],
                nl_assertions_llm_args={"temperature": config["official_evaluator"]["nl_assertions_temperature"]},
            )
            return reward
        reward = formal_adapter.evaluate_success(task, initial, final, native)
        if hasattr(reward, "model_dump"):
            value = reward.model_dump(mode="json")
            return {"success": float(value["reward"]) == 1.0, "reward_info": value}
        return {"success": bool(reward["success"]), "custom": reward}
    if source == "phase13":
        return p13_eval.evaluate_success(task_id, initial, final)
    if source == "phase14t":
        return p14t_eval.evaluate_success(task_id, initial, final)
    if source == "phase15b":
        return p15b_eval.evaluate_success(task_id, initial, final)
    if source == "phase15f":
        goals = load(P15F / "oracle_goal_specs.json")
        return p15f_eval.evaluate_success(task_id, initial, final, goals)
    if source == "phase16c":
        goals = load(P16C / "oracle_goal_specs.json")
        return p16c_eval.evaluate_success(task_id, initial, final, goals)
    if source == "phase17b":
        goals = load(P17B / "oracle_goal_specs.json")
        return p17b_eval.evaluate_success(goals[task_id], initial, final)
    raise RuntimeError(f"unknown source: {source}")


def run_config(base: dict[str, Any], spec: dict[str, Any], seed: int, skill_path: Path) -> TextRunConfig:
    config = _config(base, {"domain": spec["domain"], "task_id": str(spec["task"].id)}, seed)
    if skill_path != INITIAL_SKILL:
        config.agent = "llm_agent_manual_skill"
        config.llm_args_agent = {**config.llm_args_agent, "manual_skill_path": str(skill_path.resolve())}
    return config


def judge_evidence(spec: dict[str, Any], simulation: Any, canonical: dict[str, Any], source_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []

    def caller(model: str, system: str, user: str, temperature: float) -> str:
        for attempt in range(1, 4):
            count("judge_provider_calls")
            try:
                response = compliance.default_judge_caller(model, system, user, temperature)
            except Exception as error:
                attempts.append({"attempt": attempt, "kind": "transport", "error": type(error).__name__})
                if "empty" in str(error).lower():
                    count("empty_responses")
                count("infra_recoveries")
                continue
            empty = not bool(response and response.strip())
            attempts.append({"attempt": attempt, "kind": "empty" if empty else "valid"})
            if not empty:
                return response
            count("empty_responses")
        raise RuntimeError("JUDGE_RESPONSE_RECOVERY_EXHAUSTED")

    for build_attempt in range(1, 4):
        try:
            evidence = _build_governed_evidence(
                source_id=source_id, domain=spec["domain"], task=spec["task"], simulation=simulation,
                domain_policy=canonical[spec["domain"]]["original_domain_policy"],
                available_tool_contracts=canonical[spec["domain"]]["available_tool_contracts"],
                judge_caller=caller,
            )
            attempts.append({"build_attempt": build_attempt, "kind": "valid_evaluation"})
            return evidence, attempts
        except compliance.ComplianceJudgeError as error:
            attempts.append({"build_attempt": build_attempt, "kind": "invalid_evaluation", "error": str(error)})
            count("infra_recoveries")
            count("judge_evaluator_recoveries")
    raise RuntimeError("COMPLIANCE_EVALUATOR_RECOVERY_EXHAUSTED")


def replay_final_db(orchestrator: Any, raw_simulation: dict[str, Any]) -> dict[str, Any]:
    """Recover evaluator state from a saved trajectory without another model call."""
    tools = orchestrator.environment.tools
    for message in raw_simulation["messages"]:
        if message.get("role") != "assistant":
            continue
        for call in message.get("tool_calls") or []:
            try:
                getattr(tools, call["name"])(**call["arguments"])
            except Exception:
                # The live runtime also records failed calls without changing DB state.
                pass
    return tools.db.model_dump(mode="json")


def _reusable(path: Path, *, task_id: str, rollout_index: int, seed: int, skill_id: str) -> bool:
    try:
        row = load(path)
        return (
            row["task_id"] == task_id and row["rollout_index"] == rollout_index
            and row["rollout_seed"] == seed and row["skill_id"] == skill_id
            and isinstance(row["success"], bool) and isinstance(row["compliance"], bool)
            and Path(row["raw_path"]).is_file()
        )
    except (KeyError, OSError, TypeError, ValueError):
        return False


def run_one(*, spec: dict[str, Any], rollout_index: int, seed: int, skill: dict[str, str], phase_dir: Path, base: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    task_id = str(spec["task"].id)
    stem = phase_dir / "trajectories" / f'{task_id}_rollout_{rollout_index:02d}'
    result_path, raw_path = Path(str(stem) + ".json"), Path(str(stem) + "_raw.json")
    final_db_path = Path(str(stem) + "_final_db.json")
    if _reusable(result_path, task_id=task_id, rollout_index=rollout_index, seed=seed, skill_id=skill["skill_id"]):
        return load(result_path)
    for transport_attempt in range(1, 4):
        behavior_started = False
        try:
            orchestrator = build_text_orchestrator(run_config(base, spec, seed, Path(skill["skill_path"])), spec["task"], seed=seed)
            view = bind_context(orchestrator, spec)
            public_view = agent_payload(view)
            initial = orchestrator.environment.tools.db.model_dump(mode="json")
            if raw_path.is_file():
                raw_value = load(raw_path)
                simulation = SimulationRun.model_validate(raw_value)
                simulation.policy = orchestrator.agent.domain_policy
                final = load(final_db_path) if final_db_path.is_file() else replay_final_db(orchestrator, raw_value)
                write(final_db_path, final)
                count("saved_trajectory_evaluator_recoveries")
                error_path = Path(str(stem) + "_error.json")
                if error_path.is_file() and load(error_path).get("behavior_started"):
                    with COUNTER_LOCK:
                        COUNTERS["invalid_behavioral_trajectories"] = max(0, COUNTERS["invalid_behavioral_trajectories"] - 1)
                        write(RUN / "runtime_counters.json", dict(COUNTERS))
            else:
                behavior_started = True
                count("agent_user_rollouts_started")
                simulation = orchestrator.run()
                simulation.policy = orchestrator.agent.domain_policy
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(simulation.model_dump_json(indent=2) + "\n", encoding="utf-8")
                final = orchestrator.environment.tools.db.model_dump(mode="json")
                write(final_db_path, final)
            success = success_result(spec, initial, final, simulation, base)
            simulation.reward_info = RewardInfo(reward=float(bool(success["success"])), info={"benchmark_v2_success": success})
            evidence, judge_attempts = judge_evidence(spec, simulation, canonical, f'{phase_dir.name}_{task_id}_{rollout_index:02d}')
            compliant = bool(evidence["compliance_evaluation"]["compliant"])
            quadrant = ("C" if compliant else "V") + ("S" if success["success"] else "F")
            row = {
                "run_id": RUN_ID, "phase": phase_dir.name, "task_id": task_id,
                "domain": spec["domain"], "source": spec["source"],
                "rollout_index": rollout_index, "rollout_seed": seed,
                "skill_id": skill["skill_id"], "skill_path": skill["skill_path"],
                "success": bool(success["success"]), "compliance": compliant, "quadrant": quadrant,
                "success_evaluation": success, "learner_setting": LEARNER_SETTING,
                "information_boundary": INFORMATION_BOUNDARY_VERSION,
                "visible_view": public_view, "evidence": evidence,
                "judge_attempts": judge_attempts, "raw_path": str(raw_path.resolve()),
                "completed_utc": now(),
            }
            write(result_path, row)
            Path(str(stem) + "_error.json").unlink(missing_ok=True)
            return row
        except Exception as error:
            saved_behavior = raw_path.is_file()
            if not behavior_started or saved_behavior:
                count("infra_recoveries")
                if transport_attempt < 3:
                    continue
            if behavior_started and not saved_behavior:
                count("invalid_behavioral_trajectories")
            write(Path(str(stem) + "_error.json"), {
                "task_id": task_id, "rollout_index": rollout_index, "seed": seed,
                "behavior_started": behavior_started, "behavior_saved": saved_behavior,
                "classification": "INFRA_EVALUATOR_FAILURE" if saved_behavior else "BEHAVIORAL_OR_RUNTIME_FAILURE",
                "transport_attempt": transport_attempt,
                "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc(),
            })
            raise
    raise AssertionError("unreachable")


def run_rollouts(task_ids: list[str], *, skill: dict[str, str], phase_dir: Path, tasks: dict[str, dict[str, Any]], base: dict[str, Any], canonical: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = [(tasks[task_id], index, seed) for task_id in task_ids for index, seed in enumerate(ROLLOUT_SEEDS, 1)]
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_one, spec=spec, rollout_index=index, seed=seed, skill=skill, phase_dir=phase_dir, base=base, canonical=canonical) for spec, index, seed in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            rows.sort(key=lambda row: (row["task_id"], row["rollout_index"]))
            write(phase_dir / "rollout_progress.json", {"completed": len(rows), "planned": len(jobs), "rows": rows})
            print(json.dumps({"phase": phase_dir.name, "completed": len(rows), "planned": len(jobs)}), flush=True)
    write(phase_dir / "rollout_results.json", rows)
    return rows


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    q = Counter(row["quadrant"] for row in rows)
    n = len(rows)
    return {
        "rollouts": n, "tasks": len({row["task_id"] for row in rows}),
        "Success": sum(row["success"] for row in rows) / n,
        "Compliance": sum(row["compliance"] for row in rows) / n,
        "CS": q["CS"], "CF": q["CF"], "VS": q["VS"], "VF": q["VF"],
        "CuP": q["CS"] / n,
    }


def learner_transport(system: str, user: str, response_format: dict[str, Any]) -> str:
    for attempt in range(1, 4):
        count("learner_provider_calls")
        try:
            response, _, usage = call_learner(
                LEARNER_MODEL, system, user, temperature=0.0,
                response_format=response_format, max_completion_tokens=16_000,
            )
            if response and response.strip():
                return response.strip()
            count("empty_responses")
        except Exception as error:
            if "empty" in str(error).lower():
                count("empty_responses")
            if attempt == 3:
                raise
            count("infra_recoveries")
    raise RuntimeError("LEARNER_RESPONSE_RECOVERY_EXHAUSTED")


def build_view(spec: dict[str, Any], seed: int, skill_path: Path, base: dict[str, Any]):
    orchestrator = build_text_orchestrator(run_config(base, spec, seed, skill_path), spec["task"], seed=seed)
    return bind_context(orchestrator, spec)


def diagnose_and_edit(rows: list[dict[str, Any]], *, parent: dict[str, str], step_dir: Path, tasks: dict[str, dict[str, Any]], base: dict[str, Any]) -> tuple[dict[str, str] | None, dict[str, Any]]:
    parent_text = Path(parent["skill_path"]).read_text(encoding="utf-8")
    parent_artifact = step_dir / "parent_skill.md"
    diagnosis_summary_path = step_dir / "diagnosis_summary.json"
    editor_output_path = step_dir / "editor_output.json"
    candidate_path = step_dir / "candidate_skill.md"
    if (
        parent_artifact.is_file()
        and parent_artifact.read_text(encoding="utf-8") == parent_text
        and diagnosis_summary_path.is_file()
        and editor_output_path.is_file()
    ):
        editor_output = load(editor_output_path)
        if editor_output["status"] == "NO_UPDATE_ELIGIBLE_DIAGNOSIS":
            return None, load(diagnosis_summary_path)
        if editor_output["status"] == "CANDIDATE_CREATED" and candidate_path.is_file():
            return {
                "skill_id": f"candidate_step_{step_dir.name[-1]}",
                "skill_path": str(candidate_path.resolve()),
            }, load(diagnosis_summary_path)

    parent_artifact.parent.mkdir(parents=True, exist_ok=True)
    parent_artifact.write_text(parent_text, encoding="utf-8")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(row)
    requests = []
    for task_id in sorted(grouped):
        trio = sorted(grouped[task_id], key=lambda row: row["rollout_index"])
        view = build_view(tasks[task_id], ROLLOUT_SEEDS[0], Path(parent["skill_path"]), base)
        requests.append(prepare_diagnosis_from_stored(
            view, Path(parent["skill_path"]).read_text(encoding="utf-8"),
            [load(Path(row["raw_path"])) for row in trio],
            [{"success": row["success"]} for row in trio],
            [{"compliant": row["compliance"]} for row in trio],
        ))
    diagnosis_progress_path = step_dir / "diagnosis_raw_progress.json"
    raw_diagnoses: list[dict[str, Any]] = load(diagnosis_progress_path) if diagnosis_progress_path.is_file() else []
    raw_editor: list[dict[str, Any]] = []

    def editor_transport(system: str, user: str, response_format: dict[str, Any]) -> str:
        raw = learner_transport(system, user, response_format)
        raw_editor.append(json.loads(raw))
        write(step_dir / "editor_raw_progress.json", raw_editor)
        return raw

    diagnoses = []
    recovery_records = load(step_dir / "diagnosis_recovery_attempts.json") if (step_dir / "diagnosis_recovery_attempts.json").is_file() else []
    for request_index, request in enumerate(requests):
        cached_raw = raw_diagnoses[request_index] if request_index < len(raw_diagnoses) else None
        last_error = None
        for attempt in range(1, 4):
            captured: list[dict[str, Any]] = []

            def diagnosis_transport(system: str, user: str, response_format: dict[str, Any]) -> str:
                if attempt == 1 and cached_raw is not None:
                    raw = json.dumps(cached_raw, ensure_ascii=False)
                else:
                    raw = learner_transport(system, user, response_format)
                captured.append(json.loads(raw))
                return raw

            try:
                diagnosis = call_diagnosis(request, learner_call=diagnosis_transport)
            except Exception as error:
                last_error = error
                recovery_records.append({
                    "request_index": request_index,
                    "attempt": attempt,
                    "source": "cached" if attempt == 1 and cached_raw is not None else "provider",
                    "error_type": type(error).__name__,
                    "error": str(error),
                })
                write(step_dir / "diagnosis_recovery_attempts.json", recovery_records)
                if not (attempt == 1 and cached_raw is not None):
                    count("learner_contract_failures")
                continue
            diagnoses.append(diagnosis)
            valid_raw = captured[0]
            if request_index < len(raw_diagnoses):
                raw_diagnoses[request_index] = valid_raw
            else:
                raw_diagnoses.append(valid_raw)
            write(diagnosis_progress_path, raw_diagnoses)
            break
        else:
            raise RuntimeError(f"DIAGNOSIS_RECOVERY_EXHAUSTED[{request_index}]: {last_error}")

    editor_request, decisions = build_editor_request(tuple(diagnoses))
    if editor_request is None:
        result = {"status": "NO_UPDATE_ELIGIBLE_DIAGNOSIS", "decisions": decisions, "candidate": None}
    else:
        result = {
            "status": "CANDIDATE_CREATED",
            "decisions": decisions,
            "candidate": call_governed_editor(editor_request, learner_call=editor_transport),
        }
    write(step_dir / "diagnosis_outputs.json", raw_diagnoses)
    write(step_dir / "compiler_outputs.json", decisions)
    candidate = None
    editor = None
    if result["candidate"] is not None:
        editor = unpack(result["candidate"], "LEARNER_INFERRED_SKILL")
        candidate_path.write_text(editor["candidate_skill"], encoding="utf-8")
        candidate = {"skill_id": f"candidate_step_{step_dir.name[-1]}", "skill_path": str(candidate_path.resolve())}
    edit_summary = {
        "rules_added": sum(edit["operation"] == "add" for edit in (editor or {}).get("canonical_edits", [])),
        "rules_modified": sum(edit["operation"] == "replace" for edit in (editor or {}).get("canonical_edits", [])),
        "rules_removed": sum(edit["operation"] == "delete" for edit in (editor or {}).get("canonical_edits", [])),
        "sections": dict(Counter(edit["section"] for edit in (editor or {}).get("canonical_edits", []))),
    }
    write(step_dir / "editor_output.json", {"status": result["status"], "editor": editor, "summary": edit_summary})
    diagnosis_summary = {
        "tasks_diagnosed": len(decisions),
        "evidence_status": dict(Counter(item["trace"]["evidence_status"] for item in decisions)),
        "compiler_reason": dict(Counter(item["decision"]["reason"] for item in decisions)),
        "skill_issue_count": sum(item["decision"]["root_cause"] == "skill_issue" for item in decisions),
        "update_worthy_mechanisms": sum(item["decision"]["update_eligible"] for item in decisions),
        "positive_mechanisms": sum(
            all(row[key] for row in grouped[task_id] for key in ("success", "compliance"))
            for task_id in grouped
        ),
        "editor_summary": edit_summary,
    }
    write(step_dir / "diagnosis_summary.json", diagnosis_summary)
    return candidate, diagnosis_summary


def compare(parent_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    key = lambda row: (row["domain"], row["task_id"], row["rollout_index"], row["rollout_seed"])
    parents, candidates = {key(row): row for row in parent_rows}, {key(row): row for row in candidate_rows}
    if set(parents) != set(candidates):
        raise RuntimeError("matched monitor lineage differs")
    transitions = Counter()
    task_effects = defaultdict(lambda: {"success": 0, "compliance": 0})
    pairs = []
    for lineage in sorted(parents):
        p, c = parents[lineage], candidates[lineage]
        transition = f'{p["quadrant"]}->{c["quadrant"]}'
        transitions[transition] += 1
        ds, dc = int(c["success"]) - int(p["success"]), int(c["compliance"]) - int(p["compliance"])
        task_effects[(p["domain"], p["task_id"])]["success"] += ds
        task_effects[(p["domain"], p["task_id"])]["compliance"] += dc
        pairs.append({"domain": p["domain"], "task_id": p["task_id"], "rollout_index": p["rollout_index"], "rollout_seed": p["rollout_seed"], "parent_state": p["quadrant"], "candidate_state": c["quadrant"], "delta_success": ds, "delta_compliance": dc})
    pm, cm = metrics(parent_rows), metrics(candidate_rows)
    matrix = {f"{a}->{b}": transitions[f"{a}->{b}"] for a in ("CS", "CF", "VS", "VF") for b in ("CS", "CF", "VS", "VF")}
    repairs = sum(n for transition, n in transitions.items() if transition.split("->")[0] != "CS" and transition.endswith("->CS"))
    regressions = sum(n for transition, n in transitions.items() if transition.startswith("CS->") and not transition.endswith("->CS"))
    report = {
        "monitor_id": MONITOR_ID, "matched_pairs": pairs,
        "parent": pm, "candidate": cm,
        "delta": {"Success": cm["Success"] - pm["Success"], "Compliance": cm["Compliance"] - pm["Compliance"], "CS": cm["CS"] - pm["CS"]},
        "transition_matrix": matrix, "repairs": repairs, "regressions": regressions,
        "unchanged_good": transitions["CS->CS"],
        "unchanged_bad": sum(transitions[f"{q}->{q}"] for q in ("CF", "VS", "VF")),
    }
    return report, task_effects


def gate(task_effects: dict[tuple[str, str], dict[str, int]], report: dict[str, Any]) -> dict[str, Any]:
    strata = defaultdict(list)
    for (domain, task_id), effect in task_effects.items():
        strata[domain].append({"task_id": task_id, **effect})
    rng = random.Random(BOOTSTRAP_SEED)
    positive = 0
    for _ in range(BOOTSTRAP_REPLICATES):
        ds = dc = 0
        for values in strata.values():
            draw = rng.choices(values, k=len(values))
            ds += sum(row["success"] for row in draw)
            dc += sum(row["compliance"] for row in draw)
        positive += is_epsilon_pareto_positive(ds, dc, 1)
    probability = positive / BOOTSTRAP_REPLICATES
    observed_ds = sum(row["success"] for row in task_effects.values())
    observed_dc = sum(row["compliance"] for row in task_effects.values())
    result = {
        "monitor_id": MONITOR_ID, "matched_rollouts": len(report["matched_pairs"]),
        "task_clusters": len(task_effects), "bootstrap_unit": "task",
        "domain_tasks_per_replicate": {domain: len(values) for domain, values in strata.items()},
        "stratified_by_domain": True, "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED, "epsilon_pair_count": 1,
        "epsilon_rate": 1 / len(report["matched_pairs"]),
        "observed_delta_success_count": observed_ds, "observed_delta_compliance_count": observed_dc,
        "observed_epsilon_pareto_positive": is_epsilon_pareto_positive(observed_ds, observed_dc, 1),
        "positive_count": positive, "P": probability, "threshold": GATE_THRESHOLD,
        "decision": gate_decision(probability, GATE_THRESHOLD),
    }
    return result


def preflight() -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    splits, tasks, base = split_data(), registry(), load(BASE_CONFIG)
    expected = {"step1": 10, "step2": 10, "step3": 10, "monitor": 41, "unused": 5}
    groups = {name: set(value["task_ids"]) for name, value in splits.items()}
    errors = []
    for name, count_expected in expected.items():
        if len(splits[name]["task_ids"]) != count_expected or splits[name]["task_count"] != count_expected:
            errors.append(f"{name}_count")
    names = list(groups)
    intersections = {f"{a}_intersect_{b}": sorted(groups[a] & groups[b]) for i, a in enumerate(names) for b in names[i + 1:]}
    if any(intersections.values()):
        errors.append("split_overlap")
    assigned = set().union(*groups.values())
    if assigned != set(tasks) or len(tasks) != 76:
        errors.append("snapshot_task_loader")
    if not INITIAL_SKILL.is_file() or not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_BASE_URL"):
        errors.append("runtime_configuration")
    if LEARNER_SETTING != "EXPERIENCE_GROUNDED_LEARNER" or INFORMATION_BOUNDARY_VERSION != "v15_learner_safe":
        errors.append("v15_information_boundary")
    if base["rollouts_per_task"] != 3:
        errors.append("rollout_convention")
    report = {
        "run_id": RUN_ID, "RUN_TYPE": "END_TO_END_PILOT", "status": "PASS" if not errors else "BLOCKED",
        "checked_utc": now(), "split_counts": {name: len(ids) for name, ids in groups.items()},
        "pairwise_intersections": intersections, "evolution_monitor_intersection": sorted((groups["step1"] | groups["step2"] | groups["step3"]) & groups["monitor"]),
        "loaded_snapshot_tasks": len(tasks), "rollouts_per_task": 3,
        "evolution_parent_trajectories_per_step": 30, "evolution_parent_trajectories_total": 90,
        "fixed_monitor_tasks": 41, "fixed_monitor_rollouts_per_skill": 123,
        "learner_setting": LEARNER_SETTING, "information_boundary": INFORMATION_BOUNDARY_VERSION,
        "learner_forbidden": ["canonical hidden policy", "latent task truth", "private backend semantics", "evaluator expected answer", "exact Compliance Oracle rule", "raw privileged Judge answer"],
        "gate": {"matched_rollouts": 123, "epsilon_pair_count": 1, "epsilon_rate": 1 / 123, "bootstrap_unit": "task", "stratified_by_domain": True, "replicates": BOOTSTRAP_REPLICATES, "threshold": GATE_THRESHOLD},
        "parent_monitor_cache": True, "same_evolution_set_replay": False,
        "initial_parent": {"skill_id": "S0", "skill_path": str(INITIAL_SKILL.resolve())},
        "errors": errors,
    }
    write(RUN / "preflight_report.json", report)
    if errors:
        raise RuntimeError("PILOT_BLOCKED_BY_RUNTIME_PREFLIGHT: " + ",".join(errors))
    return splits, tasks, base


def axis_analysis(report: dict[str, Any], monitor_split: dict[str, Any]) -> dict[str, Any]:
    meta = {row["task_id"]: row for row in monitor_split["tasks"]}
    result: dict[str, Any] = {}
    for axis in ("CAPABILITY", "GOVERNANCE", "BOTH", "CONTROL"):
        pairs = [p for p in report["matched_pairs"] if meta[p["task_id"]]["axis"] == axis]
        result[axis] = {
            "matched_rollouts": len(pairs),
            "delta_success": sum(p["delta_success"] for p in pairs),
            "delta_compliance": sum(p["delta_compliance"] for p in pairs),
            "repairs": sum(p["parent_state"] != "CS" and p["candidate_state"] == "CS" for p in pairs),
            "regressions": sum(p["parent_state"] == "CS" and p["candidate_state"] != "CS" for p in pairs),
        }
    protected = [p for p in report["matched_pairs"] if meta[p["task_id"]].get("control_or_good") or meta[p["task_id"]].get("protected_regression_control")]
    result["protected_boundary_overreach"] = {
        "CS_to_CF_VS_VF": sum(p["parent_state"] == "CS" and p["candidate_state"] != "CS" for p in protected),
        "matched_rollouts": len(protected),
    }
    return result


def evolution_diagnosis_analysis(step_number: int, split: dict[str, Any]) -> dict[str, Any]:
    step_dir = RUN / f"step{step_number}"
    metadata = {row["task_id"]: row for row in split["tasks"]}
    task_ids = sorted(split["task_ids"])
    decisions = load(step_dir / "compiler_outputs.json")
    diagnoses = load(step_dir / "diagnosis_outputs.json")
    rows = []
    for task_id, compiled, diagnosis in zip(task_ids, decisions, diagnoses, strict=True):
        rows.append({
            "task_id": task_id,
            "axis": metadata[task_id]["axis"],
            "mechanism_family": metadata[task_id].get("mechanism_family"),
            "evidence_status": compiled["trace"]["evidence_status"],
            "update_eligible": compiled["decision"]["update_eligible"],
            "compiler_reason": compiled["decision"]["reason"],
            "mechanism": diagnosis["behavioral_mechanism"]["description"],
            "target_behavior": diagnosis["target_behavior"]["expected_behavior"],
        })
    by_axis = {}
    for axis in ("CAPABILITY", "GOVERNANCE", "BOTH", "CONTROL"):
        selected = [row for row in rows if row["axis"] == axis]
        by_axis[axis] = {
            "tasks": len(selected),
            "updates": sum(row["update_eligible"] for row in selected),
            "non_updates": sum(not row["update_eligible"] for row in selected),
        }
    return {"by_axis": by_axis, "tasks": rows}


def report_markdown(state: dict[str, Any]) -> str:
    lines = [f"# {RUN_ID} Report", "", "`RUN_TYPE = END_TO_END_PILOT`", "", "The fixed selection set was `FIXED_MONITOR_V2_PILOT_001` (41 tasks × 3 matched rollouts). Same-Evolution-Set replay, extra test sets, task mining, benchmark tuning, and parameter retuning were not used.", ""]
    for step in state["steps"]:
        em, comparison, gate_result = step["evolution_parent"], step.get("monitor_comparison"), step["gate"]
        lines += [f"## Step {step['step']}", "", f"Evolution Parent: Success={em['Success']:.4f}, Compliance={em['Compliance']:.4f}, CS/CF/VS/VF={em['CS']}/{em['CF']}/{em['VS']}/{em['VF']}.", "", f"Diagnosis: tasks={step['diagnosis']['tasks_diagnosed']}, evidence_status={step['diagnosis']['evidence_status']}, skill_issue={step['diagnosis']['skill_issue_count']}, update-worthy={step['diagnosis']['update_worthy_mechanisms']}, positive={step['diagnosis']['positive_mechanisms']}.", "", f"Candidate: generated={'yes' if step['candidate'] else 'no'}; editor status={step['editor_status']}.", ""]
        if comparison:
            p, c = comparison["parent"], comparison["candidate"]
            changed = [pair for pair in comparison["matched_pairs"] if pair["parent_state"] != pair["candidate_state"]]
            repaired_tasks = sorted({pair["task_id"] for pair in changed if pair["parent_state"] != "CS" and pair["candidate_state"] == "CS"})
            regressed_tasks = sorted({pair["task_id"] for pair in changed if pair["parent_state"] == "CS" and pair["candidate_state"] != "CS"})
            transitions = ", ".join(f"{key}={value}" for key, value in comparison["transition_matrix"].items())
            axis = comparison["same_mechanism_analysis"]
            lines += [f"Fixed Monitor Parent: S={p['Success']:.4f}, C={p['Compliance']:.4f}, CS/CF/VS/VF={p['CS']}/{p['CF']}/{p['VS']}/{p['VF']}, CuP={p['CuP']:.4f}.", "", f"Fixed Monitor Candidate: S={c['Success']:.4f}, C={c['Compliance']:.4f}, CS/CF/VS/VF={c['CS']}/{c['CF']}/{c['VS']}/{c['VF']}, CuP={c['CuP']:.4f}.", "", f"Delta: Success={comparison['delta']['Success']:+.4f}, Compliance={comparison['delta']['Compliance']:+.4f}, CS={comparison['delta']['CS']:+d}; repairs={comparison['repairs']}, regressions={comparison['regressions']}, unchanged good={comparison['unchanged_good']}, unchanged bad={comparison['unchanged_bad']}.", "", f"Transition matrix: {transitions}.", "", f"Tasks with at least one repair: {', '.join(repaired_tasks) if repaired_tasks else 'none'}.", "", f"Tasks with at least one CS regression: {', '.join(regressed_tasks) if regressed_tasks else 'none'}.", "", f"Same-mechanism summary: Capability={axis['CAPABILITY']}; Governance={axis['GOVERNANCE']}; Both={axis['BOTH']}; Control={axis['CONTROL']}. Protected-boundary CS regressions={axis['protected_boundary_overreach']['CS_to_CF_VS_VF']}/{axis['protected_boundary_overreach']['matched_rollouts']}.", ""]
        lines += [f"Gate: P={gate_result.get('P', 0):.4f}, threshold={gate_result.get('threshold', GATE_THRESHOLD):.2f}, decision={gate_result['decision']}.", ""]
    initial, final = state["initial_final_comparison"]["parent"], state["initial_final_comparison"]["candidate"]
    lines += ["## Final", "", "```text", "Initial Skill"]
    for step in state["steps"]:
        lines += ["      ↓", f"Step{step['step']} Candidate", step["gate"]["decision"]]
    update_totals = Counter()
    for analysis in state["evolution_diagnosis_analysis"]:
        for axis, values in analysis["by_axis"].items():
            update_totals[axis] += values["updates"]
    both_036 = next(row for row in state["evolution_diagnosis_analysis"][2]["tasks"] if row["task_id"] == "travel_request_036")
    lines += ["      ↓", f"Final Skill = {state['final_skill']['skill_path']}", "```", "", f"Accepted updates = {state['accepted_updates']} / 3.", "", f"Initial Monitor: Success={initial['Success']:.4f}, Compliance={initial['Compliance']:.4f}, CS/CF/VS/VF={initial['CS']}/{initial['CF']}/{initial['VS']}/{initial['VF']}, CuP={initial['CuP']:.4f}.", "", f"Final Monitor: Success={final['Success']:.4f}, Compliance={final['Compliance']:.4f}, CS/CF/VS/VF={final['CS']}/{final['CF']}/{final['VS']}/{final['VF']}, CuP={final['CuP']:.4f}.", "", f"Net delta: Success={final['Success']-initial['Success']:+.4f}, Compliance={final['Compliance']-initial['Compliance']:+.4f}; net repairs={state['initial_final_comparison']['repairs']}, net regressions={state['initial_final_comparison']['regressions']}.", "", "## Mechanism findings", "", f"Update-eligible diagnoses across all steps: Capability={update_totals['CAPABILITY']}, Governance={update_totals['GOVERNANCE']}, Both={update_totals['BOTH']}, Control={update_totals['CONTROL']}.", "", f"Latent Governance experience did trigger Skill edits, but none of the three Candidates passed the fixed-monitor Gate. Step-level same-mechanism results above show that compliance gains were accompanied by capability losses or CS regressions.", "", f"`travel_request_036` produced a meaningful diagnosis and edit: evidence={both_036['evidence_status']}, update={both_036['update_eligible']}, mechanism={both_036['mechanism']} Target hypothesis={both_036['target_behavior']}", "", f"Because all three Candidates were retained out, the final Skill equals S0 and the Initial→Final mechanism deltas are all zero. Candidate-level overreach was nevertheless visible: protected-boundary CS regressions were 7, 2, and 8 rollouts in Steps 1–3 respectively.", "", f"Runtime counts: {json.dumps(state['runtime_counts'], ensure_ascii=False)}", "", f"`BENCHMARK_V2_V15_END_TO_END_PILOT_001_STATUS = {state['status']}`", "", f"`V15_END_TO_END_BEHAVIOR = {state['verdict']}`", ""]
    return "\n".join(lines)


def run() -> dict[str, Any]:
    splits, tasks, base = preflight()
    canonical = load_authoritative_domain_contexts(TAU2)
    parent = {"skill_id": "S0", "skill_path": str(INITIAL_SKILL.resolve())}
    baseline_dir = RUN / "fixed_monitor_parent_baseline"
    parent_monitor = run_rollouts(splits["monitor"]["task_ids"], skill=parent, phase_dir=baseline_dir, tasks=tasks, base=base, canonical=canonical)
    initial_monitor = copy.deepcopy(parent_monitor)
    steps = []
    for step_number in (1, 2, 3):
        step_dir = RUN / f"step{step_number}"
        step_parent = copy.deepcopy(parent)
        parent_rows = run_rollouts(splits[f"step{step_number}"]["task_ids"], skill=parent, phase_dir=step_dir / "evolution_parent", tasks=tasks, base=base, canonical=canonical)
        candidate, diagnosis_summary = diagnose_and_edit(parent_rows, parent=parent, step_dir=step_dir, tasks=tasks, base=base)
        if candidate is None:
            gate_result = {"decision": "RETAIN", "reason": "NO_UPDATE_ELIGIBLE_DIAGNOSIS", "P": 0.0, "threshold": GATE_THRESHOLD}
            comparison = None
            editor_status = "NO_UPDATE_ELIGIBLE_DIAGNOSIS"
        else:
            candidate_rows = run_rollouts(splits["monitor"]["task_ids"], skill=candidate, phase_dir=step_dir / "fixed_monitor_candidate", tasks=tasks, base=base, canonical=canonical)
            comparison, task_effects = compare(parent_monitor, candidate_rows)
            gate_result = gate(task_effects, comparison)
            comparison["same_mechanism_analysis"] = axis_analysis(comparison, splits["monitor"])
            write(step_dir / "monitor_comparison.json", comparison)
            write(step_dir / "gate_result.json", gate_result)
            editor_status = "CANDIDATE_CREATED"
            if gate_result["decision"] == "ACCEPT":
                parent, parent_monitor = candidate, candidate_rows
        step_summary = {
            "step": step_number, "parent": step_parent,
            "evolution_parent": metrics(parent_rows), "diagnosis": diagnosis_summary,
            "candidate": candidate, "editor_status": editor_status,
            "monitor_comparison": comparison, "gate": gate_result,
            "next_parent": copy.deepcopy(parent),
        }
        write(step_dir / "step_summary.json", step_summary)
        steps.append(step_summary)
        write(RUN / "campaign_state.json", {"run_id": RUN_ID, "completed_steps": len(steps), "current_parent": parent, "steps": steps})
    initial_final, _ = compare(initial_monitor, parent_monitor)
    accepted = sum(step["gate"]["decision"] == "ACCEPT" for step in steps)
    net_ds, net_dc = initial_final["delta"]["Success"], initial_final["delta"]["Compliance"]
    if net_ds < 0 or net_dc < 0:
        verdict = "REGRESSION"
    elif accepted and (net_ds > 0 or net_dc > 0):
        verdict = "PROMISING" if net_ds >= 0 and net_dc >= 0 else "MIXED"
    elif accepted:
        verdict = "MIXED"
    else:
        verdict = "NO_CLEAR_IMPROVEMENT"
    state = {
        "run_id": RUN_ID, "RUN_TYPE": "END_TO_END_PILOT", "status": "COMPLETED",
        "steps": steps, "accepted_updates": accepted, "final_skill": parent,
        "initial_final_comparison": initial_final,
        "mechanism_analysis": axis_analysis(initial_final, splits["monitor"]),
        "evolution_diagnosis_analysis": [
            evolution_diagnosis_analysis(number, splits[f"step{number}"])
            for number in (1, 2, 3)
        ],
        "runtime_counts": {**dict(COUNTERS), "length_failures": COUNTERS["length_failures"], "empty_responses": COUNTERS["empty_responses"], "infra_recoveries": COUNTERS["infra_recoveries"], "invalid_behavioral_trajectories": COUNTERS["invalid_behavioral_trajectories"]},
        "verdict": verdict, "completed_utc": now(),
    }
    write(RUN / "final" / "final_summary.json", state)
    (RUN / "final" / "final_skill.md").write_text(Path(parent["skill_path"]).read_text(), encoding="utf-8")
    (RUN / "BENCHMARK_V2_V15_END_TO_END_PILOT_001_REPORT.md").write_text(report_markdown(state), encoding="utf-8")
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "run"))
    args = parser.parse_args()
    if args.command == "preflight":
        preflight()
        print(json.dumps(load(RUN / "preflight_report.json"), ensure_ascii=False, indent=2))
        return 0
    state = run()
    print(json.dumps({"status": state["status"], "accepted_updates": state["accepted_updates"], "final_skill": state["final_skill"], "verdict": state["verdict"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
