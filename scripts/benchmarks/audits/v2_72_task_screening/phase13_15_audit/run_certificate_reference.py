#!/usr/bin/env python3
"""Run the six matched-seed 021/022 certificate Reference Skill trajectories."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scripts.benchmarks.v2.construction.advanced_structure.phase14_cs_reachable_empty_skill_calibration import run_phase14 as base
from src.benchmark_v2.construction.advanced_structure.phase15b_separable_cross_axis_vf_realization import evaluators
from scripts.benchmarks.v2.construction.advanced_structure.phase15c_separable_cross_axis_vf_calibration import run_phase15c as p15c


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit'))
REPO = base.REPO
P15B = p15c.PHASE15B
P15C = P15B.parent / "phase15c_separable_cross_axis_vf_calibration"
SKILL = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/reference_skills/C_CERTIFICATE_ALLOCATION.md')


def protected_files():
    roots = [P15B, P15C, REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/benchmark"]
    return sorted({p for root in roots for p in root.rglob("*") if p.is_file() and "__pycache__" not in str(p)})


def main() -> None:
    e0_manifest = base.load((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/phase_v2_day30/construction/advanced_structure/phase15c_separable_cross_axis_vf_calibration/runtime/run_manifest.json'))
    specs = copy.deepcopy(e0_manifest["tasks"])
    assert len(specs) == 2 and sum(len(s["seeds"]) for s in specs) == 6
    assert not list(((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/trajectories')).glob("*_started.json")), "Immutable experiment already started"
    tasks = {r["id"]: base.Task.model_validate(r) for r in base.load(P15B / "tasks/candidate_tasks.json")}
    pool = base.load(P15B / "separable_vf_candidate_pool_v1.json")
    candidates = {r["task_id"]: r for r in pool["candidates"]}
    config = copy.deepcopy(base.load((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/phase_v2_day30/construction/advanced_structure/phase15c_separable_cross_axis_vf_calibration/runtime/run_config.json')))
    config["skill"] = "MINIMAL_REFERENCE_SKILL"
    config["skill_injection"] = "manual_skill_path"
    config["planned_rollouts"] = 6
    before = {str(p.relative_to(REPO)): base.sha(p) for p in protected_files()}
    aggregate = hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()
    manifest = {
        "schema_version":"phase13_15_certificate_reference_v1",
        "status":"FROZEN_BEFORE_FIRST_ROLLOUT",
        "design":"travel_request_021 support plus travel_request_022 repair, matched to Phase15C task/index/seed/config",
        "rollouts_requested":6,"skill_id":"C_CERTIFICATE_ALLOCATION","skill_sha256":base.sha(SKILL),
        "skill_scope":"No task, user, payment, flight, date, price, or budget identifiers",
        "records":[{"task_id":s["task_id"],"rollout_index":i,"seed":seed} for s in specs for i,seed in enumerate(s["seeds"],1)],
        "protected_before":{"count":len(before),"aggregate_sha256":aggregate},
        "recovery_policy":"Only confirmed pre-behavioral infrastructure failure may retry identical record; behavioral outcomes never rerun.",
    }
    base.write((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/certificate_reference_manifest.json'),manifest)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/runtime/protected_before.json'),before)
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/runtime/run_config.json'),config)
    original_config=base._config
    def reference_config(campaign,spec,seed):
        c=original_config(campaign,spec,seed)
        c.agent="llm_agent_manual_skill"
        c.llm_args_agent=dict(c.llm_args_agent)
        c.llm_args_agent["manual_skill_path"]=str((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/reference_skills/C_CERTIFICATE_ALLOCATION.md'))
        return c
    base._config=reference_config
    base.HERE=HERE
    base.bind_candidate_context=p15c.bind_frozen_context
    base.evaluate_success=evaluators.evaluate_success
    canonical=base.load_authoritative_domain_contexts(REPO/"external/tau2-bench")

    import tau2.utils.llm_utils as llm
    lock=threading.Lock(); counts={"agent_user_completion_attempts":0,"judge_provider_calls":0}
    original_completion=llm.completion; original_judge=base.default_judge_caller
    def counted_completion(*args,**kwargs):
        with lock:
            counts["agent_user_completion_attempts"]+=1; base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/runtime/model_calls.json'),counts)
        return original_completion(*args,**kwargs)
    def counted_judge(*args,**kwargs):
        with lock:
            counts["judge_provider_calls"]+=1; base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/runtime/model_calls.json'),counts)
        return original_judge(*args,**kwargs)
    llm.completion=counted_completion; base.default_judge_caller=counted_judge
    jobs=[]; rows=[]
    with ThreadPoolExecutor(max_workers=6) as executor:
        for spec in specs:
            for index,seed in enumerate(spec["seeds"],1):
                jobs.append(executor.submit(base.run_one,spec,candidates[spec["task_id"]],tasks[spec["task_id"]],seed,index,config,canonical["airline"]))
        for future in as_completed(jobs):
            result=future.result()
            if result["status"]=="completed":
                path=Path(result["path"]); artifact=base.load(path)
                artifact.update({"skill":"MINIMAL_REFERENCE_SKILL","skill_id":"C_CERTIFICATE_ALLOCATION","skill_sha256":base.sha(SKILL),"paired_e0_seed":artifact["seed"]})
                base.write(path,artifact)
            rows.append(result); rows.sort(key=lambda r:(r["task_id"],r["rollout_index"]))
            base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/runtime/run_progress.json'),rows)
            print(json.dumps({"finished":len(rows),"total":6,"last":result}),flush=True)
    after={str(p.relative_to(REPO)):base.sha(p) for p in protected_files()}
    summary={"planned":6,"completed":sum(r["status"]=="completed" for r in rows),"errors":sum(r["status"]=="error" for r in rows),"refused_reruns":sum(r["status"]=="REFUSED_RERUN" for r in rows),"behavioral_trajectory_reruns":0,"protected_files_unchanged":before==after,"model_calls":counts,"results":rows,"completed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/runtime/protected_after.json'),after); base.write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase13_15_audit/runtime/run_summary.json'),summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    if summary["completed"]!=6 or summary["errors"] or summary["refused_reruns"] or not summary["protected_files_unchanged"]: raise SystemExit(2)


if __name__=="__main__": main()
