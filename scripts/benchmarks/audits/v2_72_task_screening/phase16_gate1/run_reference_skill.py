#!/usr/bin/env python3
"""Run matched-seed minimal Reference Skill rollouts for formal Phase 16 tasks."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scripts.benchmarks.v2.construction.advanced_structure.phase14_cs_reachable_empty_skill_calibration import run_phase14 as base
from src.benchmark_v2.construction.advanced_structure.phase16c_latent_governance_variant_family_realization import evaluators
from scripts.benchmarks.v2.construction.advanced_structure.phase16d_frozen_latent_governance_empty_skill_calibration import run_phase16d as p16d


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1'))
REPO = base.REPO
P16C = p16d.P16C
P16D = P16C.parent / "phase16d_frozen_latent_governance_empty_skill_calibration"
SKILLS = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/reference_skills')
FORMAL_TASKS = {
    "travel_request_025", "travel_request_026", "travel_request_028",
    "travel_request_029", "travel_request_030", "travel_request_032",
    "travel_request_034",
}


def protected_files() -> list[Path]:
    roots = [P16C, P16D, REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/benchmark"]
    return sorted({p for root in roots for p in root.rglob("*") if p.is_file() and "__pycache__" not in str(p)})


def aggregate_hash(rows: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def main() -> None:
    frozen = base.load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v2_day30/construction/advanced_structure/phase16d_frozen_latent_governance_empty_skill_calibration/phase16d_calibration_manifest.json'))
    task_rows = base.load(P16C / "tasks/candidate_tasks.json")
    tasks = {row["id"]: base.Task.model_validate(row) for row in task_rows if row["id"] in FORMAL_TASKS}
    pool = base.load(P16C / "latent_governance_variant_family_pool_v1.json")
    family_by_task = {tid: f["family_id"] for f in pool["families"] for tid in f["task_ids"]}
    records = [r for r in frozen["records"] if r["task_id"] in FORMAL_TASKS]
    assert len(tasks) == 7 and len(records) == 21
    assert all((SKILLS / f"{family_by_task[r['task_id']]}.md").is_file() for r in records)
    assert not list(((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/trajectories')).glob("*_started.json")), "Reference experiment already started; immutable rerun refused"

    candidates = {
        tid: {
            "task_id": tid, "source_candidate_id": family_by_task[tid],
            "family_id": family_by_task[tid], "domain": "airline",
            "learner_visible_context_path": str((P16C / "contexts" / f"{family_by_task[tid]}_visible_policy.md").relative_to(REPO)),
        }
        for tid in tasks
    }
    specs = []
    for task_id in sorted(tasks):
        rows = sorted((r for r in records if r["task_id"] == task_id), key=lambda x: x["rollout_index"])
        specs.append({"task_id": task_id, "domain": "airline", "source_candidate_id": family_by_task[task_id], "seeds": [r["seed"] for r in rows]})

    before = {str(path.relative_to(REPO)): base.sha(path) for path in protected_files()}
    config = copy.deepcopy(frozen["base_runtime_configuration"])
    config["skill"] = "MINIMAL_REFERENCE_SKILL"
    config["skill_injection"] = "manual_skill_path"
    config["planned_rollouts"] = 21
    skill_hashes = {p.stem: base.sha(p) for p in sorted(SKILLS.glob("*.md"))}
    manifest = {
        "schema_version": "phase16_minimal_reference_skill_necessity_v1",
        "status": "FROZEN_BEFORE_FIRST_ROLLOUT",
        "comparison": "Matched task, rollout index, seed, model, temperature, visible policy, tools, DB, evaluator, and judge against Phase 16D E0",
        "formal_tasks": sorted(FORMAL_TASKS),
        "rollouts_per_task": 3,
        "rollouts_requested": 21,
        "skill_scope": "One minimal family rule; no task IDs, entity IDs, flight IDs, dates, prices, or oracle outputs",
        "skill_sha256": skill_hashes,
        "records": records,
        "protected_before": {"count": len(before), "aggregate_sha256": aggregate_hash(before)},
        "recovery_policy": "Only confirmed infrastructure failure may retry the identical record; behavioral outcomes are immutable.",
    }
    base.write((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/reference_skill_manifest.json'), manifest)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/runtime/protected_before.json'), before)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/runtime/run_config.json'), config)

    original_config = base._config

    def reference_config(campaign, spec, seed):
        run_config = original_config(campaign, spec, seed)
        family = spec["source_candidate_id"]
        run_config.agent = "llm_agent_manual_skill"
        run_config.llm_args_agent = dict(run_config.llm_args_agent)
        run_config.llm_args_agent["manual_skill_path"] = str((SKILLS / f"{family}.md").resolve())
        return run_config

    def run_one(*args):
        result = base.run_one(*args)
        if result["status"] == "completed":
            path = Path(result["path"])
            artifact = base.load(path)
            family = artifact["source_candidate_id"]
            artifact["skill"] = "MINIMAL_REFERENCE_SKILL"
            artifact["skill_id"] = family
            artifact["skill_sha256"] = skill_hashes[family]
            artifact["paired_e0_seed"] = artifact["seed"]
            base.write(path, artifact)
        return result

    base.HERE = HERE
    base._config = reference_config
    base.bind_candidate_context = p16d.bind_frozen_context
    base.evaluate_success = p16d.evaluate_success_bound
    canonical = base.load_authoritative_domain_contexts(REPO / "external/tau2-bench")

    import tau2.utils.llm_utils as llm
    lock = threading.Lock()
    counts = {"agent_user_completion_attempts": 0, "judge_provider_calls": 0}
    original_completion = llm.completion
    original_judge = base.default_judge_caller

    def counted_completion(*args, **kwargs):
        with lock:
            counts["agent_user_completion_attempts"] += 1
            base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/runtime/model_calls.json'), counts)
        return original_completion(*args, **kwargs)

    def counted_judge(*args, **kwargs):
        with lock:
            counts["judge_provider_calls"] += 1
            base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/runtime/model_calls.json'), counts)
        return original_judge(*args, **kwargs)

    llm.completion = counted_completion
    base.default_judge_caller = counted_judge
    jobs = []
    for record in records:
        task_id = record["task_id"]
        spec = next(x for x in specs if x["task_id"] == task_id)
        jobs.append((spec, candidates[task_id], tasks[task_id], record["seed"], record["rollout_index"], config, canonical["airline"]))

    rows = []
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = [executor.submit(run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            rows.sort(key=lambda x: (x["task_id"], x["rollout_index"]))
            base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/runtime/run_progress.json'), rows)
            print(json.dumps({"finished": len(rows), "total": 21, "last": rows[-1]}), flush=True)

    after = {str(path.relative_to(REPO)): base.sha(path) for path in protected_files()}
    summary = {
        "planned": 21,
        "completed": sum(x["status"] == "completed" for x in rows),
        "errors": sum(x["status"] == "error" for x in rows),
        "refused_reruns": sum(x["status"] == "REFUSED_RERUN" for x in rows),
        "behavioral_trajectory_reruns": 0,
        "protected_files_unchanged": before == after,
        "model_calls": counts,
        "results": rows,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/runtime/protected_after.json'), after)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase16_gate1/runtime/run_summary.json'), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if summary["completed"] != 21 or summary["errors"] or summary["refused_reruns"] or not summary["protected_files_unchanged"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
