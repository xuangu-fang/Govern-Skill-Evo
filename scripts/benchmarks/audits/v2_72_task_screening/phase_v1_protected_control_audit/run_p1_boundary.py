#!/usr/bin/env python3
"""Run six matched-seed P1 boundary/non-applicability safety rollouts."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tau2.data_model.tasks import Task

from scripts.benchmarks.v1.benchmark.phase_a_final_unified_benchmark_v1.calibration import run_calibration as base
from src.skill_evolution.v13.autonomous_gse_v13_benchmark_runtime import load_authoritative_domain_contexts


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit'))
REPO = (Path(__file__).resolve().parents[5])
V1 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30"
V2 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30"
SUITE = V1 / "benchmark/phase_a_final_unified_benchmark_v1"
SKILL = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/reference_skills/P1_PENDING_ORDER_SEQUENCE.md')
DESIGN = {
    "retail_pa_r2a_w8557584_item_delta_scope": "NEAR_BOUNDARY_ITEM_ONLY",
    "16": "NON_APPLICABILITY_CANCEL_AND_RETURN",
}


def load(file_path: Path):
    return json.loads(file_path.read_text(encoding="utf-8"))


def write(file_path: Path, value) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def protected_files() -> list[Path]:
    roots = [V1, V2 / "benchmark"]
    return sorted({file_path for root in roots for file_path in root.rglob("*") if file_path.is_file() and "__pycache__" not in file_path.parts})


def main() -> None:
    assert not list(((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/trajectories')).glob("*_started.json")), "Immutable experiment already started"
    metadata = {row["task_id"]: row for row in load(V1 / "benchmark/formal_manifestation_admission/metadata/expanded_task_metadata.json")["tasks"]}
    tasks = {row["id"]: Task.model_validate(row) for row in load(V2 / "benchmark/tasks.json")}
    seeds = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/metadata/calibration_seeds.json'))["seeds"]
    specs = [copy.deepcopy(metadata[task_id]) for task_id in DESIGN]
    records = [
        {"task_id": spec["task_id"], "boundary_role": DESIGN[spec["task_id"]], "rollout_index": index, "seed": seed}
        for spec in specs for index, seed in enumerate(seeds[spec["task_id"]], 1)
    ]
    assert len(records) == 6
    before = {str(file_path.relative_to(REPO)): sha(file_path) for file_path in protected_files()}
    config = copy.deepcopy(load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/run_config.json')))
    config.update({"skill": "P1_MINIMAL_REFERENCE_SKILL", "skill_injection": "manual_skill_path", "planned_rollouts": 6})
    manifest = {
        "schema_version": "phase_v1_protected_control_p1_boundary_v1",
        "status": "FROZEN_BEFORE_FIRST_ROLLOUT",
        "design": "P1 near-boundary and non-applicability safety; three historical matched seeds per task",
        "rollouts_requested": 6,
        "skill": {"path": str(SKILL.relative_to(REPO)), "sha256": sha(SKILL)},
        "skill_scope": "No task, user, order, product, payment, amount, price, or oracle identifiers",
        "records": records,
        "protected_before": {"count": len(before), "aggregate_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()},
        "recovery_policy": "Behavioral outcomes never rerun.",
    }
    write((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/p1_boundary_manifest.json'), manifest)
    write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/runtime/protected_before.json'), before)
    write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/runtime/run_config.json'), config)

    original_config = base._config

    def reference_config(campaign, spec, seed):
        result = original_config(campaign, spec, seed)
        result.agent = "llm_agent_manual_skill"
        result.llm_args_agent = dict(result.llm_args_agent)
        result.llm_args_agent["manual_skill_path"] = str((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/reference_skills/P1_PENDING_ORDER_SEQUENCE.md'))
        return result

    base._config = reference_config
    base.ROOT = HERE
    canonical = load_authoritative_domain_contexts(REPO / "external/tau2-bench")

    import tau2.utils.llm_utils as llm

    lock = threading.Lock()
    call_counts = {"agent_user_completion_attempts": 0, "judge_provider_calls": 0}
    original_completion = llm.completion
    original_judge = base.default_judge_caller

    def counted_completion(*args, **kwargs):
        with lock:
            call_counts["agent_user_completion_attempts"] += 1
            write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/runtime/model_calls.json'), call_counts)
        return original_completion(*args, **kwargs)

    def counted_judge(*args, **kwargs):
        with lock:
            call_counts["judge_provider_calls"] += 1
            write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/runtime/model_calls.json'), call_counts)
        return original_judge(*args, **kwargs)

    llm.completion = counted_completion
    base.default_judge_caller = counted_judge
    jobs, rows = [], []
    with ThreadPoolExecutor(max_workers=6) as executor:
        for spec in specs:
            for index, seed in enumerate(seeds[spec["task_id"]], 1):
                jobs.append(executor.submit(base.one, spec, tasks[spec["task_id"]], seed, index, config, canonical))
        for future in as_completed(jobs):
            result = future.result()
            if result["status"] == "completed":
                file_path = Path(result["path"])
                artifact = load(file_path)
                artifact.update({
                    "skill": "P1_MINIMAL_REFERENCE_SKILL",
                    "boundary_role": DESIGN[artifact["task_id"]],
                    "skill_sha256": sha(SKILL),
                    "paired_e0_seed": artifact["seed"],
                })
                write(file_path, artifact)
            rows.append(result)
            rows.sort(key=lambda row: (row["task_id"], row["index"]))
            write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/runtime/run_progress.json'), rows)
            print(json.dumps({"finished": len(rows), "total": 6, "last": result}), flush=True)

    after = {str(file_path.relative_to(REPO)): sha(file_path) for file_path in protected_files()}
    summary = {
        "planned": 6,
        "completed": sum(row["status"] == "completed" for row in rows),
        "errors": sum(row["status"] == "error" for row in rows),
        "refused_reruns": sum(row["status"] == "REFUSED_RERUN" for row in rows),
        "behavioral_trajectory_reruns": 0,
        "protected_files_unchanged": before == after,
        "model_calls": call_counts,
        "results": rows,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/runtime/protected_after.json'), after)
    write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/runtime/run_summary.json'), summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    if summary["completed"] != 6 or summary["errors"] or summary["refused_reruns"] or not summary["protected_files_unchanged"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
