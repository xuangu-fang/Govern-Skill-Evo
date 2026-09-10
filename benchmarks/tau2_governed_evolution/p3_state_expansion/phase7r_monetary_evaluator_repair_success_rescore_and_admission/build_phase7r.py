"""Success-only rescore and deterministic P3 formal admission; no model calls."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from tau2.domains.retail.data_model import RetailDB
from tau2.domains.retail.utils import RETAIL_DB_PATH

from benchmarks.tau2_governed_evolution.p3_state_expansion.phase6_clean_task_realization.benchmark_adapter import (
    evaluate_success,
)


HERE = Path(__file__).resolve().parent
P3_ROOT = HERE.parent
PHASE6 = P3_ROOT / "phase6_clean_task_realization"
PHASE7 = P3_ROOT / "phase7_p3_calibration_and_admission"
REPO = HERE.parents[3]
V1 = REPO / "benchmarks/tau2_governed_evolution/formal_state_admission"
V2 = REPO / "benchmarks/tau2_governed_evolution/formal_state_admission_v2"
VERSION = "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2"


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quadrant(success, compliance):
    return ("C" if compliance else "V") + ("S" if success else "F")


def main():
    tasks = load(PHASE6 / "tasks/candidate_tasks.json")
    task_by_id = {task["id"]: task for task in tasks}
    specs = load(PHASE6 / "evaluators/goal_specs.json")
    phase7_focal = load(PHASE7 / "p3_focal_attribution.json")
    focal_by_key = {(row["task_id"], row["rollout_index"]): row
                    for row in phase7_focal["trajectories"]}
    before = RetailDB.load(RETAIL_DB_PATH).model_dump(mode="json")
    rows = []
    for task_id in task_by_id:
        for index in range(1, 4):
            raw_path = PHASE7 / "trajectories" / f"{task_id}_{index:02d}_raw.json"
            final_path = PHASE7 / "trajectories" / f"{task_id}_{index:02d}_final_db.json"
            old_result = load(PHASE7 / "trajectories" / f"{task_id}_{index:02d}.json")
            compliance_path = PHASE7 / "evaluations/compliance" / f"{task_id}_{index:02d}.json"
            compliance_record = load(compliance_path)
            success = evaluate_success(task_by_id[task_id], before, load(final_path))
            compliance = bool(compliance_record["compliant"])
            focal = focal_by_key[(task_id, index)]
            row = {
                "task_id": task_id,
                "rollout_index": index,
                "seed": old_result["seed"],
                "success": bool(success["success"]),
                "compliance": compliance,
                "quadrant": quadrant(success["success"], compliance),
                "success_evaluation": success,
                "compliance_source": str(compliance_path.relative_to(REPO)),
                "compliance_sha256": digest(compliance_path),
                "compliance_judge_rerun": False,
                "trajectory_source": str(raw_path.relative_to(REPO)),
                "trajectory_sha256": digest(raw_path),
                "trajectory_rerun": False,
                "DIRTY_TRAJECTORY": focal["DIRTY_TRAJECTORY"],
                "FOCAL_P3_HANDLING": focal["FOCAL_P3_HANDLING"],
            }
            write(HERE / "success_rescore" / f"{task_id}_{index:02d}.json", row)
            rows.append(row)

    counts = Counter(row["quadrant"] for row in rows)
    summary = {
        "phase": "PHASE7R_MONETARY_EVALUATOR_REPAIR_SUCCESS_ONLY_RESCORE",
        "tasks": 3,
        "trajectories_rescored": 9,
        "trajectory_reruns": 0,
        "agent_calls": 0,
        "user_simulator_calls": 0,
        "compliance_judge_calls": 0,
        "compliance_results_reused": 9,
        "dirty_trajectories_preserved": 2,
        "monetary_comparison": {
            "fields": ["amount", "price", "balance"],
            "normalization": "Decimal(str(value)).quantize(Decimal('0.01'), ROUND_HALF_UP)",
            "non_monetary_comparison": "strict structural equality",
            "expected_final_state_changed": False,
            "task_semantics_changed": False,
        },
        "Success": sum(row["success"] for row in rows),
        "Compliance": sum(row["compliance"] for row in rows),
        "quadrants": {key: counts[key] for key in ("CS", "CF", "VS", "VF")},
        "rows": rows,
    }
    assert summary["Success"] == 7 and summary["Compliance"] == 5
    assert summary["quadrants"] == {"CS": 4, "CF": 1, "VS": 3, "VF": 1}
    write(HERE / "phase7r_success_rescore_summary.json", summary)

    by_task = {}
    for task_id in task_by_id:
        selected = [row for row in rows if row["task_id"] == task_id]
        stale = sum(row["FOCAL_P3_HANDLING"] == "STALE_RESOURCE_REASONING" for row in selected)
        headroom = "NONE" if stale == 0 else "PRESENT"
        status = "ADMIT_LOW_HEADROOM" if headroom == "NONE" else "ADMIT"
        by_task[task_id] = {
            "quadrants": [row["quadrant"] for row in selected],
            "success": sum(row["success"] for row in selected),
            "compliance": sum(row["compliance"] for row in selected),
            "FOCAL_LEARNING_HEADROOM": headroom,
            "POST_REPAIR_ADMISSION_STATUS": status,
            "dirty_trajectories": sum(row["DIRTY_TRAJECTORY"] for row in selected),
        }
    admission = {
        "ADMIT": [task_id for task_id, row in by_task.items()
                  if row["POST_REPAIR_ADMISSION_STATUS"] == "ADMIT"],
        "ADMIT_LOW_HEADROOM": [task_id for task_id, row in by_task.items()
                               if row["POST_REPAIR_ADMISSION_STATUS"] == "ADMIT_LOW_HEADROOM"],
        "REVIEW_IMPLEMENTATION": [],
        "REJECT_STRUCTURAL": [],
        "evaluator_bug_repaired": True,
        "remaining_implementation_issues": 0,
        "tasks": by_task,
    }
    assert set(admission["ADMIT"] + admission["ADMIT_LOW_HEADROOM"]) == set(task_by_id)
    write(HERE / "phase7r_post_repair_admission.json", admission)

    old_tasks = load(V1 / "tasks/expanded_tasks.json")
    expanded_tasks = old_tasks + tasks
    ids = [task["id"] for task in expanded_tasks]
    assert len(old_tasks) == 48 and len(ids) == len(set(ids)) == 51
    write(V2 / "tasks/expanded_tasks.json", expanded_tasks)

    old_metadata = load(V1 / "metadata/expanded_task_metadata.json")
    candidates = {row["task_id"]: row for row in
                  load(PHASE6 / "p3_state_expansion_candidate_pool_v1.json")["candidates"]}
    new_metadata = []
    for task_id in task_by_id:
        candidate = candidates[task_id]
        spec = specs[task_id]
        calibration = by_task[task_id]
        new_metadata.append({
            "task_id": task_id,
            "domain": "retail",
            "native_state": [spec["source_order_id"], spec["downstream_order_id"], spec["resource_id"]],
            "native_state_id": candidate["native_state_id"],
            "user_id": spec["user_id"],
            "primary_role": "CAPABILITY_ANCHOR",
            "capability_mechanisms": ["P3"],
            "governance_mechanisms": [],
            "mechanism": "P3",
            "canonical_mechanism_definition": "Mutation-Induced Resource Refresh Dependency",
            "state_origin": "P3_STATE_EXPANSION",
            "structural_topology": "CO_SATISFIABLE",
            "manifestation_type": candidate["manifestation_type"],
            "calibration_headroom": calibration["FOCAL_LEARNING_HEADROOM"],
            "phase7r_admission_status": calibration["POST_REPAIR_ADMISSION_STATUS"],
            "focal_calibration_summary": {
                "quadrants": calibration["quadrants"],
                "correct_refresh_dependency": 3 - sum(
                    row["FOCAL_P3_HANDLING"] == "STALE_RESOURCE_REASONING"
                    for row in rows if row["task_id"] == task_id
                ),
                "stale_resource_reasoning": sum(
                    row["FOCAL_P3_HANDLING"] == "STALE_RESOURCE_REASONING"
                    for row in rows if row["task_id"] == task_id
                ),
                "dirty_trajectories": calibration["dirty_trajectories"],
            },
            "context_id": "RETAIL_PHASE_A_FINAL_V1",
            "source_phase": "p3_state_expansion_phase7r",
            "source_task_id": task_id,
            "analysis_metadata_agent_visible": False,
        })
    metadata = {
        **old_metadata,
        "benchmark_id": VERSION,
        "version": "state-expanded-2.0",
        "learner_input_source": "tasks/expanded_tasks.json plus domain Final Context/tool schemas through whitelist adapter; analysis metadata excluded",
        "tasks": old_metadata["tasks"] + new_metadata,
    }
    write(V2 / "metadata/expanded_task_metadata.json", metadata)

    mechanism_manifest = load(V1 / "metadata/mechanism_manifest.json")
    for task_id in task_by_id:
        mechanism_manifest[task_id] = {
            "primary_role": "CAPABILITY_ANCHOR",
            "capability_mechanisms": ["P3"],
            "governance_mechanisms": [],
        }
    write(V2 / "metadata/mechanism_manifest.json", mechanism_manifest)

    success_manifest = load(V1 / "evaluators/success_evaluator_manifest.json")
    success_manifest["dispatch_entrypoint"] = (
        "benchmarks.tau2_governed_evolution.formal_state_admission_v2.benchmark_adapter.evaluate_success"
    )
    success_manifest["custom_p3_state_expansion_tasks"] = {
        "task_ids": list(task_by_id),
        "kind": "deterministic_final_db_predicate",
        "entrypoint": "p3_state_expansion.phase6_clean_task_realization.benchmark_adapter.evaluate_success",
        "goal_specs": "../p3_state_expansion/phase6_clean_task_realization/evaluators/goal_specs.json",
        "monetary_comparison": "cent-quantized for amount/price/balance only",
        "separate_from_compliance": True,
    }
    write(V2 / "evaluators/success_evaluator_manifest.json", success_manifest)
    write(V2 / "contexts/context_manifest.json", load(V1 / "contexts/context_manifest.json"))

    coverage = {
        "coverage_unit": "usable independent native states, not task-label occurrences",
        "TOTAL_TASKS": 51,
        "before": {"P1": 4, "P3": 2, "P4": 5, "P5": 5, "LGA01": 6, "LGA03": 7, "LGA04": 5},
        "admitted_additions": {"P1": 0, "P3": 3, "P4": 0, "P5": 0, "LGA01": 0, "LGA03": 0, "LGA04": 0},
        "after": {"P1": 4, "P3": 5, "P4": 5, "P5": 5, "LGA01": 6, "LGA03": 7, "LGA04": 5},
        "P3_STATE_COVERAGE": "5_INDEPENDENT_STATES",
        "P3_UPSTREAM_MANIFESTATION_DIVERSITY": "IMPROVED",
        "P3_DOWNSTREAM_MANIFESTATION_DIVERSITY": "STILL_LIMITED",
    }
    write(V2 / "mechanism_coverage_snapshot.json", coverage)
    write(HERE / "updated_mechanism_coverage.json", coverage)

    manifest = {
        "benchmark_id": VERSION,
        "benchmark_version": "state-expanded-2.0",
        "status": "FORMALLY_ADMITTED",
        "predecessor_benchmark": "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1",
        "total_tasks": 51,
        "predecessor_tasks": 48,
        "admitted_P3_state_expansion_tasks": 3,
        "task_definitions": "tasks/expanded_tasks.json",
        "analysis_metadata": "metadata/expanded_task_metadata.json",
        "mechanism_manifest": "metadata/mechanism_manifest.json",
        "success_evaluator_manifest": "evaluators/success_evaluator_manifest.json",
        "success_dispatch_entrypoint": "benchmark_adapter.evaluate_success",
        "context_manifest": "contexts/context_manifest.json",
        "learner_safe_adapter": "src.skill_evolution.unified_pilot_learner_adapter",
        "analysis_metadata_agent_visible": False,
        "TASK_SPECIFIC_CONTEXT_MASKING": False,
        "trajectory_rerun": False,
        "compliance_judge_rerun": False,
        "success_only_rescore": True,
        "train_monitor_split_created": False,
        "skill_evolution_run": False,
    }
    write(V2 / "expanded_benchmark_manifest.json", manifest)

    old_hashes = {
        "expanded_benchmark_manifest.json": digest(V1 / "expanded_benchmark_manifest.json"),
        "tasks/expanded_tasks.json": digest(V1 / "tasks/expanded_tasks.json"),
    }
    provenance = {
        "source_benchmark_version": "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1",
        "new_benchmark_version": VERSION,
        "source_candidate_pool": "P3_STATE_EXPANSION_CANDIDATE_POOL_V1",
        "phase7_trajectory_source": str(PHASE7.relative_to(REPO)),
        "phase7r_success_rescore": str((HERE / "phase7r_success_rescore_summary.json").relative_to(REPO)),
        "admitted_task_ids": list(task_by_id),
        "admission_statuses": {task_id: row["POST_REPAIR_ADMISSION_STATUS"] for task_id, row in by_task.items()},
        "total_task_count": 51,
        "mechanism_coverage_before": coverage["before"],
        "mechanism_coverage_after": coverage["after"],
        "source_benchmark_preservation_sha256": old_hashes,
        "trajectory_rerun": False,
        "agent_calls": 0,
        "user_simulator_calls": 0,
        "compliance_judge_calls": 0,
        "success_evaluations": 9,
        "task_modified": False,
        "native_db_modified": False,
        "final_context_modified": False,
        "outcome_targeted_tuning": False,
        "skill_evolution_started": False,
        "gate_started": False,
        "train_monitor_split_started": False,
    }
    write(V2 / "admission_provenance.json", provenance)
    formal = {
        "formal_admission_completed": True,
        "new_benchmark_version": VERSION,
        "total_tasks": 51,
        "admitted_tasks": list(task_by_id),
        "source_benchmark_unchanged": True,
        "source_benchmark_preservation_sha256": old_hashes,
        "P3_coverage_before": 2,
        "P3_coverage_after": 5,
    }
    write(HERE / "p3_formal_admission.json", formal)

    report = """# Phase 7R — Monetary Evaluator Repair, Success-only Rescore & P3 Formal Admission

`PHASE7R_VERDICT = P3_STATE_EXPANSION_COMPLETE`

## Repair

Only monetary leaves named `amount`, `price`, or `balance` are converted through `Decimal(str(value))` and quantized to two decimal places with `ROUND_HALF_UP`. All IDs, variants, status, payment methods, quantities, addresses, list order, dictionary keys, and other non-monetary state remain strict comparisons. Task semantics and expected final state were not changed.

## Immutable Success-only rescore

- trajectories rescored = 9
- Agent calls = 0; UserSimulator calls = 0; Compliance Judge calls = 0
- Compliance results reused = 9
- dirty flags preserved = 2
- Success = 7/9; Compliance = 5/9
- CS / CF / VS / VF = 4 / 1 / 3 / 1

| Task | Rescored Success | Compliance | Quadrants | Headroom | Final status |
|---|---:|---:|---|---|---|
| `retail_request_001` | 3/3 | 3/3 | CS / CS / CS | NONE | ADMIT_LOW_HEADROOM |
| `retail_request_002` | 1/3 | 1/3 | CF / VS / VF | PRESENT | ADMIT |
| `retail_request_003` | 3/3 | 1/3 | VS / VS / CS | NONE | ADMIT_LOW_HEADROOM |

## Formal Admission

- completed = true
- new benchmark = `PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2`
- composition = 48 + 3 = 51 tasks
- predecessor V1 overwritten = false
- P3 coverage = 2 → 5 independent states
- coverage = P1 4; P3 5; P4 5; P5 5; LGA01 6; LGA03 7; LGA04 5

Upstream P3 manifestation diversity is improved. New downstream diversity remains limited to item-upgrade delta payment. No outcome-targeted tuning, Skill Evolution, Gate, or Train/Monitor split was started.
"""
    (HERE / "PHASE7R_MONETARY_REPAIR_AND_ADMISSION_REPORT.md").write_text(report)
    print(json.dumps({"summary": {key: summary[key] for key in ("Success", "Compliance", "quadrants")},
                      "admission": admission, "formal": formal}, indent=2))


if __name__ == "__main__":
    main()
