#!/usr/bin/env python3
"""Run the minimal matched-seed Capability Anchor Reference Skill experiment."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tau2.data_model.tasks import Task

from benchmarks.tau2_governed_evolution.editions.phase_v1_day30.benchmark.phase_a_final_unified_benchmark_v1.calibration import run_calibration as base
from src.skill_evolution.autonomous_gse_v13_benchmark_runtime import (
    load_authoritative_domain_contexts,
)


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
V1 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30"
V2 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30"
SUITE = V1 / "benchmark/phase_a_final_unified_benchmark_v1"

DESIGN = {
    "retail_pa_v1b_w8557584_items_address_payment": ("P1", "REPAIR"),
    "retail_request_002": ("P3", "REPAIR"),
    "retail_request_001": ("P3", "SUPPORT"),
    "travel_request_003": ("P4", "REPAIR"),
    "travel_request_015": ("P4", "SUPPORT"),
    "airline_dd_fq8ape_cabin_baggage_budget": ("P5_P6", "REPAIR"),
    "airline_dd_hxdubj_multistage_propagation": ("P5_P6", "SUPPORT"),
}
SKILLS = {
    "P1": HERE / "reference_skills/P1_PENDING_ORDER_SEQUENCE.md",
    "P3": HERE / "reference_skills/P3_RESOURCE_REFRESH.md",
    "P4": HERE / "reference_skills/P4_ONE_SHOT_ALLOCATION.md",
    "P5_P6": HERE / "reference_skills/P5_P6_INCREMENTAL_PLANNING.md",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_files() -> list[Path]:
    roots = [V1, V2 / "benchmark"]
    return sorted(
        {path for root in roots for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts}
    )


def seed_map() -> dict[str, list[int]]:
    seeds = load(SUITE / "metadata/calibration_seeds.json")["seeds"]
    phase3 = load(V1 / "construction/existing_mechanism_state_expansion/phase3_empty_skill_calibration/runtime/run_manifest.json")
    phase7 = load(V1 / "construction/p3_state_expansion/phase7_p3_calibration_and_admission/runtime/run_manifest.json")
    phase11 = load(V1 / "construction/manifestation_diversity/phase11_manifestation_calibration_and_admission/runtime/run_manifest.json")
    for manifest in (phase3, phase7, phase11):
        for row in manifest["tasks"]:
            seeds[row["task_id"]] = row["seeds"]
    return seeds


def main() -> None:
    assert not list((HERE / "trajectories").glob("*_started.json")), "Immutable experiment already started"
    metadata = {
        row["task_id"]: row
        for row in load(V1 / "benchmark/formal_manifestation_admission/metadata/expanded_task_metadata.json")["tasks"]
    }
    tasks = {row["id"]: Task.model_validate(row) for row in load(V2 / "benchmark/tasks.json")}
    seeds = seed_map()
    specs = [copy.deepcopy(metadata[task_id]) for task_id in DESIGN]
    records = [
        {
            "task_id": spec["task_id"],
            "family": DESIGN[spec["task_id"]][0],
            "role": DESIGN[spec["task_id"]][1],
            "rollout_index": index,
            "seed": seed,
        }
        for spec in specs
        for index, seed in enumerate(seeds[spec["task_id"]], 1)
    ]
    assert len(records) == 21
    before = {str(path.relative_to(REPO)): sha(path) for path in protected_files()}
    config = copy.deepcopy(load(SUITE / "calibration/run_config.json"))
    config.update({"skill": "MINIMAL_REFERENCE_SKILL", "skill_injection": "manual_skill_path", "planned_rollouts": 21})
    manifest = {
        "schema_version": "phase_v1_capability_anchor_reference_v1",
        "status": "FROZEN_BEFORE_FIRST_ROLLOUT",
        "design": "P1 repair only; P3/P4/P5_P6 each one repair and one support task; three historical matched seeds per task",
        "rollouts_requested": 21,
        "skills": {family: {"path": str(path.relative_to(REPO)), "sha256": sha(path)} for family, path in SKILLS.items()},
        "skill_scope": "No task, user, order, reservation, product, payment, flight, date, amount, price, budget, or oracle identifiers",
        "records": records,
        "protected_before": {"count": len(before), "aggregate_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()},
        "recovery_policy": "Only a confirmed pre-behavioral infrastructure failure may retry an identical record; behavioral outcomes never rerun.",
    }
    write(HERE / "capability_reference_manifest.json", manifest)
    write(HERE / "runtime/protected_before.json", before)
    write(HERE / "runtime/run_config.json", config)

    original_config = base._config

    def reference_config(campaign, spec, seed):
        result = original_config(campaign, spec, seed)
        family = DESIGN[spec["task_id"]][0]
        result.agent = "llm_agent_manual_skill"
        result.llm_args_agent = dict(result.llm_args_agent)
        result.llm_args_agent["manual_skill_path"] = str(SKILLS[family].resolve())
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
            write(HERE / "runtime/model_calls.json", call_counts)
        return original_completion(*args, **kwargs)

    def counted_judge(*args, **kwargs):
        with lock:
            call_counts["judge_provider_calls"] += 1
            write(HERE / "runtime/model_calls.json", call_counts)
        return original_judge(*args, **kwargs)

    llm.completion = counted_completion
    base.default_judge_caller = counted_judge
    jobs = []
    rows = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for spec in specs:
            for index, seed in enumerate(seeds[spec["task_id"]], 1):
                jobs.append(executor.submit(base.one, spec, tasks[spec["task_id"]], seed, index, config, canonical))
        for future in as_completed(jobs):
            result = future.result()
            if result["status"] == "completed":
                path = Path(result["path"])
                artifact = load(path)
                family, role = DESIGN[artifact["task_id"]]
                artifact.update(
                    {
                        "skill": "MINIMAL_REFERENCE_SKILL",
                        "skill_family": family,
                        "experiment_role": role,
                        "skill_sha256": sha(SKILLS[family]),
                        "paired_e0_seed": artifact["seed"],
                    }
                )
                write(path, artifact)
            rows.append(result)
            rows.sort(key=lambda row: (row["task_id"], row["index"]))
            write(HERE / "runtime/run_progress.json", rows)
            print(json.dumps({"finished": len(rows), "total": 21, "last": result}), flush=True)

    after = {str(path.relative_to(REPO)): sha(path) for path in protected_files()}
    summary = {
        "planned": 21,
        "completed": sum(row["status"] == "completed" for row in rows),
        "errors": sum(row["status"] == "error" for row in rows),
        "refused_reruns": sum(row["status"] == "REFUSED_RERUN" for row in rows),
        "behavioral_trajectory_reruns": 0,
        "protected_files_unchanged": before == after,
        "model_calls": call_counts,
        "results": rows,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    write(HERE / "runtime/protected_after.json", after)
    write(HERE / "runtime/run_summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    if summary["completed"] != 21 or summary["errors"] or summary["refused_reruns"] or not summary["protected_files_unchanged"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
