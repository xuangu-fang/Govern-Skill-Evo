#!/usr/bin/env python3
"""Materialize benchmark v4 from immutable benchmark v3 plus admitted JRA-01."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
V3 = ROOT / "benchmarks/tau2_governed_evolution/editions/phase_final_candidate_day35"
SOURCE = ROOT / "benchmarks/tau2_governed_evolution/final_candidate/construction/joint_capability_experience_mapping_v1/replication_v1"
V4 = ROOT / "benchmarks/tau2_governed_evolution/editions/phase_v4_day36"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source_tasks = load(SOURCE / "tasks.json")
    source_specs = load(SOURCE / "specs.json")["candidates"]
    source_by_id = {row["id"]: row for row in source_tasks}
    formal_ids = {
        **{f"jcem-repl-train-{i:02d}": f"JRA-01-C{i:02d}" for i in range(1, 5)},
        **{f"jcem-repl-monitor-{i:02d}": f"JRA-01-C{i + 4:02d}" for i in range(1, 5)},
    }
    joint_tasks = []
    joint_specs = []
    for spec in source_specs:
        source_id = spec["input_label"]
        task_id = formal_ids[source_id]
        task = source_by_id[source_id]
        task["id"] = task_id
        task["description"]["purpose"] = "Benchmark v4 Capability × Governance joint family."
        task["description"]["notes"] = "JRA-01 admitted by recorded design decision after frozen replication."
        joint_tasks.append(task)
        joint_specs.append({**spec, "task_id": task_id, "source_input_label": source_id})

    old_core = load(V3 / "benchmark/tasks.json")
    controls = load(V3 / "benchmark/control_tasks.json")
    old_splits = load(V3 / "benchmark/splits.json")
    train_joint = [f"JRA-01-C{i:02d}" for i in range(1, 5)]
    monitor_joint = [f"JRA-01-C{i:02d}" for i in range(5, 9)]
    train = old_splits["splits"]["train"] + train_joint
    monitor_core = old_splits["monitor_roles"]["CORE_GENERALIZATION"] + monitor_joint
    guards = old_splits["monitor_roles"]["REGRESSION_GUARD"]
    monitor = monitor_core + guards

    save(V4 / "benchmark/tasks.json", old_core + joint_tasks)
    save(V4 / "benchmark/control_tasks.json", controls)
    save(V4 / "benchmark/joint_family_specs.json", {"family": "JRA-01", "tasks": joint_specs})
    save(V4 / "benchmark/splits.json", {
        "edition": "phase_v4_day36", "status": "EVOLUTION_AND_MONITOR", "task_count": 81,
        "splits": {"train": train, "monitor": monitor},
        "monitor_roles": {"CORE_GENERALIZATION": monitor_core, "REGRESSION_GUARD": guards},
        "test_split": None,
        "allocation_rule": "Evolution contains 36 Core tasks. Monitor contains 36 held-out Core tasks plus nine regression guards; there is no Test split.",
    })
    old_lineage = load(V3 / "benchmark/lineage.json")["tasks"]
    lineage = old_lineage + [{
        "formal_task_id": formal_ids[row["input_label"]],
        "source_edition": None,
        "source_task_id": None,
        "construction_label": row["input_label"],
        "admission_decision": "docs/methods/v18/JOINT_ADMISSION.md",
    } for row in source_specs]
    save(V4 / "benchmark/lineage.json", {"edition": "phase_v4_day36", "tasks": lineage})
    old_manifest = load(V3 / "benchmark/task_manifest.json")
    save(V4 / "benchmark/task_manifest.json", {
        **old_manifest, "edition": "phase_v4_day36", "task_count": 81,
        "family_counts": {**old_manifest["family_counts"], "JRA-01": 8},
        "sections": {**old_manifest["sections"], "capability_x_governance": ["JSG-01", "JRA-01"]},
        "admitted_task_ids": old_manifest["admitted_task_ids"] + [f"JRA-01-C{i:02d}" for i in range(1, 9)],
        "semantic_spec_files": ["benchmark/new_family_specs.json", "benchmark/joint_family_specs.json"],
    })
    evaluation = load(V3 / "benchmark/evaluation_manifest.json")
    evaluation["edition"] = "phase_v4_day36"
    evaluation["families"]["JRA-01"] = {
        "capability": "deterministic fare-class resource-allocation final state",
        "governance": "deterministic insurance-reason trace rule",
    }
    save(V4 / "benchmark/evaluation_manifest.json", evaluation)
    save(V4 / "benchmark/admission_decision.json", {
        "family": "JRA-01", "decision": "ADMIT_TO_BENCHMARK_V4", "date": "2026-09-20",
        "decision_type": "explicit_design_judgment",
        "contract_v3_result_preserved": "HOLD_REPLICATION",
        "rationale": [
            "Structural Capability and Governance orthogonality was demonstrated.",
            "Both splits retained cross-axis residual headroom under component ablations.",
            "The exact joint Skill reached 4/4 CS independently on Train and Monitor.",
            "Further construction targeting a one-task E0 threshold gap would risk designing Base failure rather than a natural benchmark.",
        ],
        "source_summary": str(((Path(__file__).resolve().parents[3] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/joint_capability_experience_mapping_v1/replication_v1/summary.json')).relative_to(ROOT)),
    })
    print(json.dumps({"status": "BUILT", "core": 72, "controls": 9, "train": 36, "monitor": 45}, indent=2))


if __name__ == "__main__":
    main()
