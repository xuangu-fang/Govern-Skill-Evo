"""Build the state-expanded benchmark version from immutable admitted inputs."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
V1 = HERE.parent / "phase_a_final_unified_benchmark_v1"
PHASE2 = HERE.parent / "existing_mechanism_state_expansion/phase2_clean_task_realization"
PHASE3 = HERE.parent / "existing_mechanism_state_expansion/phase3_empty_skill_calibration"
VERSION = "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1"


def load(path):
    return json.loads(path.read_text())


def write(relative, value):
    path = HERE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def v1_hashes():
    return {str(path.relative_to(REPO)): digest(path) for path in sorted(V1.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}


def main():
    before_hashes = v1_hashes()
    old_tasks = load(V1 / "tasks/final_tasks.json")
    new_tasks = load(PHASE2 / "tasks/candidate_tasks.json")
    old_role = load(V1 / "metadata/task_role_manifest.json")
    old_mechanisms = load(V1 / "metadata/mechanism_manifest.json")
    provenance = {row["task_id"]: row for row in load(PHASE2 / "provenance/realization_provenance.json")}
    calibration = {row["task_id"]: row for row in load(PHASE3 / "analysis/per_task_calibration.json")["tasks"]}
    admission = load(PHASE3 / "analysis/post_calibration_admission.json")
    admitted_ids = [task["id"] for task in new_tasks]
    assert set(admitted_ids) == set(admission["ADMIT"] + admission["ADMIT_LOW_HEADROOM"])
    assert len(old_tasks) == 34 and len(new_tasks) == 14

    expanded_tasks = old_tasks + new_tasks
    ids = [task["id"] for task in expanded_tasks]
    assert len(ids) == len(set(ids)) == 48
    write("tasks/expanded_tasks.json", expanded_tasks)

    old_rows = []
    for row in old_role["tasks"]:
        old_rows.append({
            **row,
            "state_origin": "ORIGINAL_UNIFIED_V1",
            "structural_topology": None,
            "calibration_headroom": None,
            "state_diversity": None,
            "analysis_metadata_agent_visible": False,
        })
    new_rows = []
    for task in new_tasks:
        task_id = task["id"]
        source = provenance[task_id]
        result = calibration[task_id]
        mechanism = source["mechanism"]
        new_rows.append({
            "task_id": task_id,
            "domain": "airline",
            "native_state": source["native_objects"],
            "native_state_id": source["source_native_state"],
            "user_id": load(PHASE2 / f"evaluators/goal_specs.json")[task_id]["user_id"],
            "primary_role": "CAPABILITY_ANCHOR" if mechanism == "P4" else "GOVERNANCE_ANCHOR",
            "capability_mechanisms": [mechanism] if mechanism == "P4" else [],
            "governance_mechanisms": [] if mechanism == "P4" else [mechanism],
            "mechanism": mechanism,
            "state_origin": "STATE_EXPANSION",
            "structural_topology": result["topology"],
            "polarity": result["polarity"] if mechanism == "LGA03" else None,
            "calibration_headroom": result["FOCAL_LEARNING_HEADROOM"],
            "phase3_admission_status": result["POST_CALIBRATION_STATUS"],
            "state_diversity": {
                "level": source["state_diversity"],
                "variation_dimensions": source["state_variation_dimensions"],
            },
            "context_id": "AIRLINE_PHASE_A_FINAL_V1",
            "source_phase": "existing_mechanism_state_expansion",
            "source_task_id": task_id,
            "analysis_metadata_agent_visible": False,
        })
    metadata = {
        "benchmark_id": VERSION,
        "version": "state-expanded-1.0",
        "status": "FORMALLY_ADMITTED",
        "analysis_metadata_agent_visible": False,
        "learner_input_source": "tasks/expanded_tasks.json plus domain Final Context/tool schemas through whitelist adapter; this metadata file is excluded",
        "tasks": old_rows + new_rows,
    }
    write("metadata/expanded_task_metadata.json", metadata)

    mechanism_manifest = dict(old_mechanisms)
    for row in new_rows:
        mechanism_manifest[row["task_id"]] = {
            "primary_role": row["primary_role"],
            "capability_mechanisms": row["capability_mechanisms"],
            "governance_mechanisms": row["governance_mechanisms"],
        }
    write("metadata/mechanism_manifest.json", mechanism_manifest)

    before_coverage = {row["mechanism"]: row["total_usable_coverage"] for row in
                       load(HERE.parent / "existing_mechanism_state_coverage_audit/mechanism_coverage_matrix.json")["rows"]}
    before_selected = {key: before_coverage[key] for key in ("P1", "P3", "P4", "P5", "LGA01", "LGA03", "LGA04")}
    additions = {"P1": 0, "P3": 0, "P4": 3, "P5": 0, "LGA01": 4, "LGA03": 5, "LGA04": 2}
    after_coverage = {key: before_selected[key] + additions[key] for key in before_selected}
    lga03_mapping = [
        {"task_id": "airline_lgv1_lga03_0huih5", "native_state_id": "0HUIH5", "polarity": "INACTIVE", "state_origin": "ORIGINAL_UNIFIED_V1"},
        {"task_id": "airline_lgv1_lga03_0igx7a", "native_state_id": "0IGX7A", "polarity": "INACTIVE", "state_origin": "ORIGINAL_UNIFIED_V1"},
    ] + [{"task_id": row["task_id"], "native_state_id": row["native_state_id"], "polarity": row["polarity"], "state_origin": "STATE_EXPANSION"}
         for row in new_rows if row["mechanism"] == "LGA03"]
    coverage = {
        "coverage_unit": "usable independent native states, not task-label occurrences",
        "TOTAL_TASKS": 48,
        "before": before_selected,
        "admitted_additions": additions,
        "after": after_coverage,
        "LGA03_polarity": {
            "ACTIVE": sum(row["polarity"] == "ACTIVE" for row in lga03_mapping),
            "INACTIVE": sum(row["polarity"] == "INACTIVE" for row in lga03_mapping),
            "mapping": lga03_mapping,
        },
        "next_obvious_state_count_gap": {"mechanism": "P3", "states": 2, "soft_target": 5, "gap": 3},
    }
    assert after_coverage == {"P1": 4, "P3": 2, "P4": 5, "P5": 5, "LGA01": 6, "LGA03": 7, "LGA04": 5}
    assert coverage["LGA03_polarity"]["ACTIVE"] == 3 and coverage["LGA03_polarity"]["INACTIVE"] == 4
    write("mechanism_coverage_snapshot.json", coverage)

    manifest = {
        "benchmark_id": VERSION,
        "benchmark_version": "state-expanded-1.0",
        "status": "FORMALLY_ADMITTED",
        "original_benchmark": "PHASE_A_UNIFIED_BENCHMARK_V1",
        "total_tasks": 48,
        "original_tasks": 34,
        "admitted_state_expansion_tasks": 14,
        "task_definitions": "tasks/expanded_tasks.json",
        "analysis_metadata": "metadata/expanded_task_metadata.json",
        "mechanism_manifest": "metadata/mechanism_manifest.json",
        "success_evaluator_manifest": "evaluators/success_evaluator_manifest.json",
        "success_dispatch_entrypoint": "benchmark_adapter.evaluate_success",
        "context_manifest": "contexts/context_manifest.json",
        "learner_safe_adapter": "src.skill_evolution.unified_pilot_learner_adapter",
        "analysis_metadata_agent_visible": False,
        "TASK_SPECIFIC_CONTEXT_MASKING": False,
        "rollout_rerun": False,
        "success_compliance_calibration_rerun": False,
        "train_monitor_split_created": False,
        "skill_evolution_run": False,
    }
    write("expanded_benchmark_manifest.json", manifest)

    success_manifest = load(V1 / "evaluators/success_evaluator_manifest.json")
    success_manifest["custom_state_expansion_tasks"] = {
        "task_ids": admitted_ids,
        "kind": "deterministic_final_db_predicate",
        "entrypoint": "existing_mechanism_state_expansion.phase2_clean_task_realization.benchmark_adapter.evaluate_success",
        "goal_specs": "../existing_mechanism_state_expansion/phase2_clean_task_realization/evaluators/goal_specs.json",
        "separate_from_compliance": True,
    }
    success_manifest["dispatch_entrypoint"] = "benchmarks.tau2_governed_evolution.formal_state_admission.benchmark_adapter.evaluate_success"
    write("evaluators/success_evaluator_manifest.json", success_manifest)
    write("contexts/context_manifest.json", load(V1 / "contexts/context_manifest.json"))

    provenance_record = {
        "source_candidate_pool": "benchmarks/tau2_governed_evolution/existing_mechanism_state_expansion/phase2_clean_task_realization/candidate_pool/state_expansion_candidate_pool_v1.json",
        "phase3_admission_source": "benchmarks/tau2_governed_evolution/existing_mechanism_state_expansion/phase3_empty_skill_calibration/analysis/post_calibration_admission.json",
        "phase3_verdict": "READY_FOR_STATE_ADMISSION",
        "phase3_status_counts": {"ADMIT": 11, "ADMIT_LOW_HEADROOM": 3, "REVIEW_IMPLEMENTATION": 0, "REJECT_STRUCTURAL": 0},
        "original_benchmark_version": "PHASE_A_UNIFIED_BENCHMARK_V1",
        "new_benchmark_version": VERSION,
        "admitted_task_ids": admitted_ids,
        "total_task_count": 48,
        "mechanism_coverage_before": before_selected,
        "mechanism_coverage_after": after_coverage,
        "old_benchmark_hashes_before": before_hashes,
        "rollout_rerun": False,
        "success_compliance_calibration_rerun": False,
        "task_semantics_modified": False,
        "evaluator_semantics_modified": False,
        "native_db_modified": False,
        "final_context_modified": False,
        "canonical_policy_modified": False,
        "mechanism_definition_modified": False,
    }
    write("admission_provenance.json", provenance_record)
    assert v1_hashes() == before_hashes
    print(f"Built {VERSION}: 34 + 14 = 48 tasks; v1 unchanged; no rollout/evaluation calls.")


if __name__ == "__main__":
    main()
