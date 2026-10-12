#!/usr/bin/env python3
"""Run matched-seed minimal Reference Skills for six Phase-v1 latent-G tasks."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scripts.benchmarks.v1.construction.phase_a_latent_governance_v1 import run_final_validation as base


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate'))
REPO = base.REPO
SOURCE = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/construction/phase_a_latent_governance_v1"
SKILLS = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/reference_skills')


def protected_files() -> list[Path]:
    roots = [
        SOURCE,
        REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark",
        REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/benchmark",
        REPO / "benchmarks/tau2_governed_evolution/editions/phase_v3_day34/benchmark",
    ]
    return sorted({path for root in roots if root.exists() for path in root.rglob("*") if path.is_file() and "__pycache__" not in str(path)})


def aggregate_hash(rows: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def main() -> None:
    config = copy.deepcopy(base.load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/construction/phase_a_latent_governance_v1/run_config.json')))
    specs = base.load(SOURCE / "task_manifest.json")["tasks"]
    tasks = {row["id"]: base.Task.model_validate(row) for row in base.load(SOURCE / "final_tasks.json")}
    seeds = base.load(SOURCE / "seed_manifest.json")["seeds"]
    assert len(specs) == len(tasks) == 6
    assert all((SKILLS / f"{spec['candidate_id']}.md").is_file() for spec in specs)
    assert not list(((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/trajectories')).glob("*_started.json")), "Reference experiment already started; immutable rerun refused"

    before = {str(path.relative_to(REPO)): base.sha(path) for path in protected_files()}
    skill_hashes = {path.stem: base.sha(path) for path in sorted(SKILLS.glob("*.md"))}
    records = [
        {
            "task_id": spec["task_id"],
            "family_id": spec["candidate_id"],
            "rollout_index": index,
            "seed": seed,
        }
        for spec in specs
        for index, seed in enumerate(seeds[spec["task_id"]], 1)
    ]
    config["skill"] = "MINIMAL_FAMILY_REFERENCE_SKILL"
    config["skill_injection"] = "manual_skill_path"
    config["planned_rollouts"] = 18
    manifest = {
        "schema_version": "phase_v1_latent_g_reference_manifest_v1",
        "status": "FROZEN_BEFORE_FIRST_ROLLOUT",
        "comparison": "Matched task, rollout index, seed, model, temperature, masked policy, tools, DB, evaluator, and compliance judge against Phase-v1 E0",
        "tasks": sorted(tasks),
        "families": sorted(skill_hashes),
        "rollouts_per_task": 3,
        "rollouts_requested": 18,
        "skill_scope": "One minimal family rule; no task IDs, user IDs, reservation IDs, flight IDs, dates, prices, or oracle outputs",
        "skill_sha256": skill_hashes,
        "records": records,
        "protected_before": {"count": len(before), "aggregate_sha256": aggregate_hash(before)},
        "recovery_policy": "Only confirmed infrastructure failure may retry the identical record; behavioral outcomes are immutable.",
    }
    base.write((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/reference_skill_manifest.json'), manifest)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/runtime/protected_before.json'), before)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/runtime/run_config.json'), config)

    canonical = base.load_authoritative_domain_contexts(REPO / "external/tau2-bench")
    counts = {"agent_user_completion_attempts": 0, "judge_provider_calls": 0}
    lock = threading.Lock()
    import tau2.utils.llm_utils as llm

    original_completion = llm.completion
    original_judge = base.default_judge_caller

    def counted_completion(*args, **kwargs):
        with lock:
            counts["agent_user_completion_attempts"] += 1
            base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/runtime/model_calls.json'), counts)
        return original_completion(*args, **kwargs)

    def counted_judge(*args, **kwargs):
        with lock:
            counts["judge_provider_calls"] += 1
            base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/runtime/model_calls.json'), counts)
        return original_judge(*args, **kwargs)

    llm.completion = counted_completion
    base.default_judge_caller = counted_judge

    def run_one(spec: dict, task, seed: int, index: int) -> dict:
        stem = (Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/trajectories') / f"{task.id}_{index:02d}"
        raw = Path(str(stem) + "_raw.json")
        out = Path(str(stem) + ".json")
        started = Path(str(stem) + "_started.json")
        if started.exists():
            return {"task_id": task.id, "rollout_index": index, "status": "REFUSED_RERUN"}
        base.write(started, {"seed": seed, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        try:
            run_config = base._config(config, spec, seed)
            run_config.agent = "llm_agent_manual_skill"
            run_config.llm_args_agent = dict(run_config.llm_args_agent)
            run_config.llm_args_agent["manual_skill_path"] = str((SKILLS / f"{spec['candidate_id']}.md").resolve())
            orchestrator = base.build_text_orchestrator(run_config, task, seed=seed)
            base.apply_context(orchestrator, spec["domain"])
            orchestrator.agent.domain_policy = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/construction/phase_a_latent_governance_v1/context/airline_phase_a_latent_governance_v1.md')).read_text()
            simulation = orchestrator.run()
            simulation.policy = orchestrator.agent.domain_policy
            base.write(raw, simulation.model_dump(mode="json"))
            reward = base.evaluate_simulation(
                simulation=simulation,
                task=task,
                evaluation_type=base.EvaluationType.ALL,
                solo_mode=False,
                domain=spec["domain"],
                mode=base.CommunicationMode.HALF_DUPLEX,
                nl_assertions_model=config["official_evaluator"]["nl_assertions_model"],
                nl_assertions_llm_args={"temperature": config["official_evaluator"]["nl_assertions_temperature"]},
            )
            simulation.reward_info = reward
            base.write(Path(str(stem) + "_evaluated.json"), simulation.model_dump(mode="json"))
            attempts = []

            def caller(model, system, user, temperature):
                for attempt in range(3):
                    response = counted_judge(model, system, user, temperature)
                    attempts.append({"attempt": attempt + 1, "empty": not bool(response and response.strip())})
                    if response and response.strip():
                        return response
                raise RuntimeError("JUDGE_EMPTY_AFTER_3_ATTEMPTS")

            evidence = base._build_governed_evidence(
                source_id=f"{task.id}_{index}",
                domain=spec["domain"],
                task=task,
                simulation=simulation,
                domain_policy=canonical[spec["domain"]]["original_domain_policy"],
                available_tool_contracts=canonical[spec["domain"]]["available_tool_contracts"],
                judge_caller=caller,
            )
            success = bool(evidence["task_success"])
            compliance = bool(evidence["compliance_evaluation"]["compliant"])
            result = {
                "task_id": task.id,
                "family_id": spec["candidate_id"],
                "native_state": spec["native_state"],
                "rollout_index": index,
                "seed": seed,
                "skill": "MINIMAL_FAMILY_REFERENCE_SKILL",
                "skill_sha256": skill_hashes[spec["candidate_id"]],
                "paired_e0_seed": seed,
                "success": success,
                "compliance": compliance,
                "quadrant": ("C" if compliance else "V") + ("S" if success else "F"),
                "evidence": evidence,
                "judge_attempts": attempts,
                "raw_sha256": base.sha(raw),
            }
            base.write(out, result)
            return {"task_id": task.id, "rollout_index": index, "status": "completed", "path": str(out)}
        except Exception as exc:
            base.write(
                Path(str(stem) + "_error.json"),
                {"task_id": task.id, "rollout_index": index, "error_type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()},
            )
            return {"task_id": task.id, "rollout_index": index, "status": "error", "error_type": type(exc).__name__}

    jobs = [
        (spec, tasks[spec["task_id"]], seed, index)
        for spec in specs
        for index, seed in enumerate(seeds[spec["task_id"]], 1)
    ]
    rows = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            rows.sort(key=lambda item: (item["task_id"], item["rollout_index"]))
            base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/runtime/run_progress.json'), rows)
            print(json.dumps({"finished": len(rows), "total": 18, "last": rows[-1]}), flush=True)

    after = {str(path.relative_to(REPO)): base.sha(path) for path in protected_files()}
    summary = {
        "planned": 18,
        "completed": sum(row["status"] == "completed" for row in rows),
        "errors": sum(row["status"] == "error" for row in rows),
        "refused_reruns": sum(row["status"] == "REFUSED_RERUN" for row in rows),
        "behavioral_trajectory_reruns": 0,
        "protected_files_unchanged": before == after,
        "model_calls": counts,
        "results": rows,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/runtime/protected_after.json'), after)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/runtime/run_summary.json'), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if summary["completed"] != 18 or summary["errors"] or summary["refused_reruns"] or not summary["protected_files_unchanged"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
