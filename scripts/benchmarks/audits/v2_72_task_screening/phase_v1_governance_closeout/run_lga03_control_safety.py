#!/usr/bin/env python3
"""Run LGA03 Reference Skill safety on the three active-polarity controls."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scripts.benchmarks.v1.construction.existing_mechanism_state_expansion.phase3_empty_skill_calibration import run_phase3 as base


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout'))
REPO = base.REPO
SOURCE = base.HERE
PHASE2 = base.PHASE2
TASK_IDS = {"travel_request_010", "travel_request_011", "travel_request_012"}
SKILL = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/reference_skills/LGA03.md')


def protected_files() -> list[Path]:
    roots = [
        PHASE2,
        SOURCE,
        REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark",
        REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/benchmark",
        REPO / "benchmarks/tau2_governed_evolution/editions/phase_v3_day34/benchmark",
    ]
    return sorted({path for root in roots if root.exists() for path in root.rglob("*") if path.is_file() and "__pycache__" not in str(path)})


def aggregate_hash(rows: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def main() -> None:
    source_manifest = base.load((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/phase_v1_day30/construction/existing_mechanism_state_expansion/phase3_empty_skill_calibration/runtime/run_manifest.json'))
    specs = [row for row in source_manifest["tasks"] if row["task_id"] in TASK_IDS]
    tasks = {row["id"]: base.Task.model_validate(row) for row in base.load(PHASE2 / "tasks/candidate_tasks.json") if row["id"] in TASK_IDS}
    assert len(specs) == len(tasks) == 3 and SKILL.is_file()
    assert not list(((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/trajectories')).glob("*_started.json")), "Control-safety experiment already started; immutable rerun refused"

    before = {str(path.relative_to(REPO)): base.sha256(path) for path in protected_files()}
    skill_hash = base.sha256(SKILL)
    config = copy.deepcopy(base.load((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/phase_v1_day30/construction/existing_mechanism_state_expansion/phase3_empty_skill_calibration/runtime/run_config.json')))
    config["skill"] = "LGA03_MINIMAL_REFERENCE_SKILL"
    config["skill_injection"] = "manual_skill_path"
    config["planned_rollouts"] = 9
    manifest = {
        "schema_version": "phase_v1_lga03_control_safety_manifest_v1",
        "status": "FROZEN_BEFORE_FIRST_ROLLOUT",
        "comparison": "Matched task, rollout index, seed, model, temperature, policy, tools, DB, evaluator, and compliance judge against Phase3 E0",
        "tasks": sorted(TASK_IDS),
        "rollouts_per_task": 3,
        "rollouts_requested": 9,
        "skill_path": str(SKILL.relative_to(REPO)),
        "skill_sha256": skill_hash,
        "skill_scope": "Minimal LGA03 rule with no task, user, reservation, flight, date, amount, or oracle identifiers",
        "records": [{"task_id": row["task_id"], "rollout_index": index, "seed": seed} for row in specs for index, seed in enumerate(row["seeds"], 1)],
        "protected_before": {"count": len(before), "aggregate_sha256": aggregate_hash(before)},
        "recovery_policy": "Only confirmed infrastructure failure may retry the identical record; behavioral outcomes are immutable.",
    }
    base.write((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/lga03_control_safety_manifest.json'), manifest)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/runtime/protected_before.json'), before)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/runtime/run_config.json'), config)

    original_here = base.HERE
    original_config = base._config
    base.HERE = HERE

    def reference_config(campaign, spec, seed):
        run_config = original_config(campaign, spec, seed)
        run_config.agent = "llm_agent_manual_skill"
        run_config.llm_args_agent = dict(run_config.llm_args_agent)
        run_config.llm_args_agent["manual_skill_path"] = str((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_latent_g_gate/reference_skills/LGA03.md'))
        return run_config

    base._config = reference_config
    contexts = base.load_authoritative_domain_contexts(REPO / "external/tau2-bench")
    import tau2.utils.llm_utils as llm
    original_completion = llm.completion
    original_judge = base.default_judge_caller
    lock = threading.Lock()
    calls = {"agent_user_completion_attempts": 0, "judge_provider_calls": 0}

    def counted_completion(*args, **kwargs):
        with lock:
            calls["agent_user_completion_attempts"] += 1
            base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/runtime/model_calls.json'), calls)
        return original_completion(*args, **kwargs)

    def counted_judge(*args, **kwargs):
        with lock:
            calls["judge_provider_calls"] += 1
            base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/runtime/model_calls.json'), calls)
        return original_judge(*args, **kwargs)

    llm.completion = counted_completion
    base.default_judge_caller = counted_judge
    jobs = [(spec, tasks[spec["task_id"]], seed, index, config, contexts) for spec in specs for index, seed in enumerate(spec["seeds"], 1)]
    rows = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(base.run_one, *job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            rows.sort(key=lambda item: (item["task_id"], item["rollout_index"]))
            base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/runtime/run_progress.json'), rows)
            print(json.dumps({"finished": len(rows), "total": 9, "last": rows[-1]}), flush=True)

    after = {str(path.relative_to(REPO)): base.sha256(path) for path in protected_files()}
    summary = {
        "planned": 9,
        "completed": sum(row["status"] == "completed" for row in rows),
        "errors": sum(row["status"] == "error" for row in rows),
        "refused_reruns": sum(row["status"] == "REFUSED_RERUN" for row in rows),
        "behavioral_trajectory_reruns": 0,
        "protected_files_unchanged": before == after,
        "model_calls": calls,
        "results": rows,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/runtime/protected_after.json'), after)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/runtime/run_summary.json'), summary)
    base.HERE = original_here
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if summary["completed"] != 9 or summary["errors"] or summary["refused_reruns"] or not summary["protected_files_unchanged"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
