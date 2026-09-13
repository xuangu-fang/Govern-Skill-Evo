#!/usr/bin/env python3
"""Run the 33 immutable Phase 16D Empty-Skill trajectories."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from benchmarks.tau2_governed_evolution.advanced_structure.phase14_cs_reachable_empty_skill_calibration import run_phase14 as base
from benchmarks.tau2_governed_evolution.advanced_structure.phase16c_latent_governance_variant_family_realization import evaluators
from src.skill_evolution.information_boundary_v15 import (
    INFORMATION_BOUNDARY_VERSION, LEARNER_SETTING, agent_payload, capture_agent_visible_view)

HERE = Path(__file__).resolve().parent
REPO = base.REPO
P16C = HERE.parent / "phase16c_latent_governance_variant_family_realization"
MANIFEST = HERE / "phase16d_calibration_manifest.json"
MANIFEST_DIGEST = HERE / "phase16d_calibration_manifest.sha256"
GOAL_SPECS = base.load(P16C / "oracle_goal_specs.json")


def protected_files():
    paths = list(base.FORMAL.rglob("*"))
    paths += [REPO / "external/tau2-bench/data/tau2/domains/airline/db.json",
              REPO / "external/tau2-bench/data/tau2/domains/airline/policy.md",
              REPO / "external/tau2-bench/src/tau2/domains/airline/tools.py"]
    paths += list(P16C.rglob("*"))
    paths += [p for p in REPO.rglob("*") if p.is_file() and
              ("v14" in str(p.relative_to(REPO)).lower() or "v15" in str(p.relative_to(REPO)).lower())]
    return sorted({p for p in paths if p.is_file() and "__pycache__" not in str(p)})


def verify_manifest():
    expected = MANIFEST_DIGEST.read_text().split()[0]
    assert base.sha(MANIFEST) == expected
    manifest = base.load(MANIFEST)
    assert manifest["status"] == "FROZEN_BEFORE_FIRST_ROLLOUT"
    assert manifest["candidate_tasks"] == 11 and manifest["rollouts_requested"] == 33
    source_map = {
        "tasks": P16C / "tasks/candidate_tasks.json",
        "pool": P16C / "latent_governance_variant_family_pool_v1.json",
        "visibility_contract": P16C / "latent_visibility_contract_v1.json",
        "historical_evidence_contract": P16C / "historical_evidence_recoverability_contract_v1.json",
        "evaluators": P16C / "evaluators.py",
        "goal_specs": P16C / "oracle_goal_specs.json",
        "base_config": base.CONFIG_SOURCE,
    }
    assert all(base.sha(path) == manifest["freeze_sources"][key] for key, path in source_map.items())
    return manifest


def bind_frozen_context(orchestrator, candidate):
    formal_context = base.bind_agent_context(orchestrator, "airline")
    policy_path = REPO / candidate["learner_visible_context_path"]
    orchestrator.agent.domain_policy = policy_path.read_text()
    envelope = capture_agent_visible_view(orchestrator.agent, "airline")
    view = agent_payload(envelope)
    contract = base.load(P16C / "latent_visibility_contract_v1.json")
    family_contract = next(x for x in contract["families"] if x["family_id"] == candidate["family_id"])
    assert hashlib.sha256(view["visible_policy"].encode()).hexdigest() == family_contract["visible_policy_sha256"]
    assert candidate["family_id"].casefold() not in json.dumps(view).casefold()
    return {"context_id": f'{candidate["task_id"]}_PHASE16C_LATENT_VISIBLE_V1',
            "policy_path": candidate["learner_visible_context_path"],
            "formal_tool_context_id": formal_context,
            "v15_view_digest": hashlib.sha256(envelope.payload.encode()).hexdigest(),
            "v15_payload_keys": sorted(view),
            "visible_policy_sha256": hashlib.sha256(view["visible_policy"].encode()).hexdigest(),
            "public_tool_schema_sha256": hashlib.sha256(json.dumps(view["public_tools"], sort_keys=True).encode()).hexdigest(),
            "shared_hidden_contract_validated": True}, view


def evaluate_success_bound(task_id, initial_db, final_db):
    return evaluators.evaluate_success(task_id, initial_db, final_db, GOAL_SPECS)


def main():
    manifest = verify_manifest()
    assert not list((HERE / "trajectories").glob("*_started.json")), "Phase16D already started"
    config = copy.deepcopy(manifest["base_runtime_configuration"])
    assert config["skill"] == "EMPTY" and config["skill_injection"] is None
    task_rows = base.load(P16C / "tasks/candidate_tasks.json")
    tasks = {row["id"]: base.Task.model_validate(row) for row in task_rows}
    pool = base.load(P16C / "latent_governance_variant_family_pool_v1.json")
    family_by_task = {tid: f["family_id"] for f in pool["families"] for tid in f["task_ids"]}
    candidates = {tid: {"task_id": tid, "source_candidate_id": family_by_task[tid],
                        "family_id": family_by_task[tid], "domain": "airline",
                        "learner_visible_context_path": str((P16C / "contexts" / f'{family_by_task[tid]}_visible_policy.md').relative_to(REPO))}
                  for tid in tasks}
    records = manifest["records"]
    assert {r["task_id"] for r in records} == set(tasks)
    specs = []
    for task_id in sorted(tasks):
        rows = [r for r in records if r["task_id"] == task_id]
        specs.append({"task_id": task_id, "domain": "airline", "source_candidate_id": family_by_task[task_id],
                      "seeds": [r["seed"] for r in sorted(rows, key=lambda x: x["rollout_index"])]})
    before = {str(path.relative_to(REPO)): base.sha(path) for path in protected_files()}
    base.write(HERE / "runtime/protected_before.json", before)
    run_config = copy.deepcopy(config)
    run_config["planned_rollouts"] = 33
    base.write(HERE / "runtime/run_config.json", run_config)
    base.HERE = HERE
    base.TASK_SPECS = tuple(specs)
    base.bind_candidate_context = bind_frozen_context
    base.evaluate_success = evaluate_success_bound
    canonical = base.load_authoritative_domain_contexts(REPO / "external/tau2-bench")

    import tau2.utils.llm_utils as llm
    lock = threading.Lock()
    counts = {"agent_user_completion_attempts": 0, "judge_provider_calls": 0}
    original_completion = llm.completion
    original_judge = base.default_judge_caller

    def counted_completion(*args, **kwargs):
        with lock:
            counts["agent_user_completion_attempts"] += 1
            base.write(HERE / "runtime/model_calls.json", counts)
        return original_completion(*args, **kwargs)

    def counted_judge(*args, **kwargs):
        with lock:
            counts["judge_provider_calls"] += 1
            base.write(HERE / "runtime/model_calls.json", counts)
        return original_judge(*args, **kwargs)

    llm.completion = counted_completion
    base.default_judge_caller = counted_judge
    jobs, rows = [], []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for record in records:
            task_id = record["task_id"]
            jobs.append(executor.submit(base.run_one,
                next(x for x in specs if x["task_id"] == task_id), candidates[task_id], tasks[task_id],
                record["seed"], record["rollout_index"], run_config, canonical["airline"]))
        assert len(jobs) == 33
        for future in as_completed(jobs):
            rows.append(future.result())
            rows.sort(key=lambda x: (x["task_id"], x["rollout_index"]))
            base.write(HERE / "runtime/run_progress.json", rows)
            print(json.dumps({"finished": len(rows), "total": 33, "last": rows[-1]}), flush=True)
    after = {str(path.relative_to(REPO)): base.sha(path) for path in protected_files()}
    summary = {"planned": 33, "completed": sum(x["status"] == "completed" for x in rows),
        "errors": sum(x["status"] == "error" for x in rows),
        "refused_reruns": sum(x["status"] == "REFUSED_RERUN" for x in rows),
        "behavioral_trajectory_reruns": 0, "protected_files_unchanged": before == after,
        "model_calls": counts, "results": rows,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    base.write(HERE / "runtime/protected_after.json", after)
    base.write(HERE / "runtime/run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    assert summary["protected_files_unchanged"] and summary["refused_reruns"] == 0
    if summary["errors"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
