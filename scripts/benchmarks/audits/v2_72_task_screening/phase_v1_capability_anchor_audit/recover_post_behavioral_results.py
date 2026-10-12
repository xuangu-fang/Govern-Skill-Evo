#!/usr/bin/env python3
"""Recover packaging/Judge-only failures without rerunning behavioral trajectories."""

from __future__ import annotations

import json
from pathlib import Path

from tau2.data_model.simulation import SimulationRun
from tau2.data_model.tasks import Task

from src.adapters.tau2.tau3_compliance_judge_v13 import default_judge_caller
from src.skill_evolution.v13.autonomous_gse_v13_benchmark_runtime import _build_governed_evidence, load_authoritative_domain_contexts


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit'))
REPO = (Path(__file__).resolve().parents[5])
V1 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30"
V2 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30"
SKILL = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/reference_skills/P4_ONE_SHOT_ALLOCATION.md')


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def reconstruct_with_judge(task: Task, index: int, metadata: dict, contexts: dict) -> dict:
    stem = (Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/trajectories') / f"{task.id}_{index:02d}"
    simulation = SimulationRun.model_validate_json(Path(str(stem) + "_evaluated.json").read_text())
    attempts = []

    def caller(model, system, user, temperature):
        for attempt in range(1, 4):
            try:
                response = default_judge_caller(model, system, user, temperature)
                attempts.append({"attempt": attempt, "empty": not bool(response and response.strip()), "error": None})
                if response and response.strip():
                    return response
            except RuntimeError as error:
                attempts.append({"attempt": attempt, "empty": True, "error": str(error)})
        raise RuntimeError("JUDGE_ONLY_RECOVERY_EXHAUSTED")

    evidence = _build_governed_evidence(
        source_id=f"{task.id}_{index}",
        domain="airline",
        task=task,
        simulation=simulation,
        domain_policy=contexts["airline"]["original_domain_policy"],
        available_tool_contracts=contexts["airline"]["available_tool_contracts"],
        judge_caller=caller,
    )
    write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/evaluations/compliance') / f"{task.id}_{index:02d}.json", evidence["compliance_evaluation"])
    return {
        "task_id": task.id,
        "primary_role": metadata["primary_role"],
        "native_state": metadata["native_state_id"],
        "index": index,
        "seed": load(Path(str(stem) + "_started.json"))["seed"],
        "context_id": metadata["context_id"],
        "evidence": evidence,
        "judge_attempts": attempts,
        "skill": "MINIMAL_REFERENCE_SKILL",
        "skill_family": "P4",
        "experiment_role": "SUPPORT",
        "skill_sha256": __import__("hashlib").sha256(SKILL.read_bytes()).hexdigest(),
        "paired_e0_seed": load(Path(str(stem) + "_started.json"))["seed"],
        "recovery": "JUDGE_ONLY_FROM_SAVED_EVALUATED_TRAJECTORY__NO_BEHAVIORAL_RERUN",
        "success_measurement_caveat": "Merged v2 task has no native evaluation criteria; focal P4 safety is assessed from recorded tool actions.",
    }


def recover_judge(task: Task, metadata: dict, contexts: dict) -> dict:
    index = 3
    stem = (Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/trajectories') / f"{task.id}_{index:02d}"
    simulation = SimulationRun.model_validate_json(Path(str(stem) + "_evaluated.json").read_text())
    attempts = []

    def caller(model, system, user, temperature):
        for attempt in range(1, 4):
            try:
                response = default_judge_caller(model, system, user, temperature)
                attempts.append({"attempt": attempt, "empty": not bool(response and response.strip()), "error": None})
                if response and response.strip():
                    return response
            except RuntimeError as error:
                attempts.append({"attempt": attempt, "empty": True, "error": str(error)})
        raise RuntimeError("JUDGE_ONLY_RECOVERY_EXHAUSTED")

    evidence = _build_governed_evidence(
        source_id=f"{task.id}_{index}",
        domain="airline",
        task=task,
        simulation=simulation,
        domain_policy=contexts["airline"]["original_domain_policy"],
        available_tool_contracts=contexts["airline"]["available_tool_contracts"],
        judge_caller=caller,
    )
    write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/evaluations/compliance') / f"{task.id}_{index:02d}.json", evidence["compliance_evaluation"])
    skill_path = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/reference_skills/P5_P6_INCREMENTAL_PLANNING.md')
    return {
        "task_id": task.id,
        "primary_role": metadata["primary_role"],
        "native_state": metadata["native_state"],
        "index": index,
        "seed": load(Path(str(stem) + "_started.json"))["seed"],
        "context_id": metadata["context_id"],
        "evidence": evidence,
        "judge_attempts": attempts,
        "skill": "MINIMAL_REFERENCE_SKILL",
        "skill_family": "P5_P6",
        "experiment_role": "SUPPORT",
        "skill_sha256": __import__("hashlib").sha256(skill_path.read_bytes()).hexdigest(),
        "paired_e0_seed": load(Path(str(stem) + "_started.json"))["seed"],
        "recovery": "JUDGE_ONLY_FROM_SAVED_EVALUATED_TRAJECTORY__NO_BEHAVIORAL_RERUN",
    }


def main() -> None:
    metadata = {
        row["task_id"]: row
        for row in load(V1 / "benchmark/formal_manifestation_admission/metadata/expanded_task_metadata.json")["tasks"]
    }
    tasks = {row["id"]: Task.model_validate(row) for row in load(V2 / "benchmark/tasks.json")}
    recovered = []
    contexts = load_authoritative_domain_contexts(REPO / "external/tau2-bench")
    for index in (1, 2, 3):
        output = (Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/trajectories') / f"travel_request_015_{index:02d}.json"
        assert not output.exists()
        write(output, reconstruct_with_judge(tasks["travel_request_015"], index, metadata["travel_request_015"], contexts))
        recovered.append({"task_id": "travel_request_015", "index": index, "type": "JUDGE_ONLY"})
    output = (Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/trajectories/airline_dd_hxdubj_multistage_propagation_03.json')
    assert not output.exists()
    write(output, recover_judge(tasks["airline_dd_hxdubj_multistage_propagation"], metadata["airline_dd_hxdubj_multistage_propagation"], contexts))
    recovered.append({"task_id": "airline_dd_hxdubj_multistage_propagation", "index": 3, "type": "JUDGE_ONLY"})

    original = load((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/runtime/run_summary.json'))
    recovery = {
        "schema_version": "phase_v1_capability_anchor_recovery_v1",
        "original_summary": original,
        "recovered_records": recovered,
        "behavioral_trajectory_reruns": 0,
        "judge_only_recoveries": 4,
        "packaging_only_recoveries": 0,
        "final_completed": 21,
        "final_errors": 0,
        "protected_files_unchanged": original["protected_files_unchanged"],
    }
    write((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/runtime/recovery_summary.json'), recovery)
    print("PASS_POST_BEHAVIORAL_RECOVERY_4_OF_4")


if __name__ == "__main__":
    main()
