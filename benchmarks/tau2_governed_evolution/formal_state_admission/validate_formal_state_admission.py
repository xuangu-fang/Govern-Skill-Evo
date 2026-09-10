"""Basic static validation for formal state admission; performs no rollout/evaluation calls."""
import hashlib
import json
from pathlib import Path

from tau2.data_model.tasks import Task

from benchmarks.tau2_governed_evolution.formal_state_admission import benchmark_adapter

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
V1 = HERE.parent / "phase_a_final_unified_benchmark_v1"
PHASE2 = HERE.parent / "existing_mechanism_state_expansion/phase2_clean_task_realization"
PHASE3 = HERE.parent / "existing_mechanism_state_expansion/phase3_empty_skill_calibration"


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    checks = []
    manifest = load(HERE / "expanded_benchmark_manifest.json")
    expanded = load(HERE / "tasks/expanded_tasks.json")
    old = load(V1 / "tasks/final_tasks.json")
    candidates = load(PHASE2 / "tasks/candidate_tasks.json")
    metadata = load(HERE / "metadata/expanded_task_metadata.json")
    coverage = load(HERE / "mechanism_coverage_snapshot.json")
    provenance = load(HERE / "admission_provenance.json")

    ids = [task["id"] for task in expanded]
    assert len(ids) == len(set(ids)) == manifest["total_tasks"] == 48
    assert expanded[:34] == old and expanded[34:] == candidates
    assert {task["id"] for task in candidates} <= set(ids)
    checks += ["48_UNIQUE_TASK_IDS", "ALL_14_ADMITTED", "TASK_SEMANTICS_BYTE_EQUIVALENT_JSON_VALUES"]
    for task in expanded:
        Task.model_validate(task)
    checks.append("ALL_48_TASKS_SCHEMA_VALID")

    new_meta = [row for row in metadata["tasks"] if row["state_origin"] == "STATE_EXPANSION"]
    required = {"mechanism", "native_state_id", "state_origin", "structural_topology", "polarity", "calibration_headroom", "state_diversity"}
    assert len(new_meta) == 14 and all(required <= set(row) for row in new_meta)
    assert all(row["analysis_metadata_agent_visible"] is False for row in metadata["tasks"])
    assert all(set(task) == {"id", "description", "user_scenario", "initial_state", "evaluation_criteria"} for task in candidates)
    checks += ["REQUIRED_ANALYSIS_METADATA_PRESENT", "ANALYSIS_METADATA_NOT_LEARNER_FACING"]

    phase3_preflight = load(PHASE3 / "runtime/learner_safe_preflight.json")
    assert phase3_preflight["requests"] == 14 and phase3_preflight["construction_metadata_leakage_matches"] == 0
    for task in candidates:
        assert load(PHASE2 / f'requests/{task["id"]}.json') == load(PHASE3 / f'requests/{task["id"]}.json')
    checks.append("WHITELIST_REQUEST_ENVELOPES_UNCHANGED_AND_ZERO_LEAKAGE")

    assert benchmark_adapter.evaluate_success(old[0], {}, {}, lambda unused: "NATIVE_SENTINEL") == "NATIVE_SENTINEL"
    initial_db = load(REPO / "external/tau2-bench/data/tau2/domains/airline/db.json")
    for task in candidates:
        value = benchmark_adapter.evaluate_success(task, initial_db, initial_db, lambda unused: None)
        assert set(value) >= {"success", "reward", "compliance_evaluated"}
    checks += ["V1_SUCCESS_DISPATCH_PRESERVED", "ALL_14_CUSTOM_SUCCESS_DISPATCHES_RESOLVE"]

    context_manifest = load(HERE / "contexts/context_manifest.json")
    assert context_manifest == load(V1 / "contexts/context_manifest.json")
    assert all(row["context_id"] in ("AIRLINE_PHASE_A_FINAL_V1", "RETAIL_PHASE_A_FINAL_V1") for row in metadata["tasks"])
    assert all(row["context_id"] == "AIRLINE_PHASE_A_FINAL_V1" for row in new_meta)
    checks.append("FINAL_CONTEXT_ASSIGNMENT_VALID")

    current_v1 = {str(path.relative_to(REPO)): digest(path) for path in sorted(V1.rglob("*"))
                  if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}
    assert current_v1 == provenance["old_benchmark_hashes_before"]
    checks.append("ORIGINAL_V1_UNCHANGED")

    assert coverage["after"] == {"P1": 4, "P3": 2, "P4": 5, "P5": 5, "LGA01": 6, "LGA03": 7, "LGA04": 5}
    assert coverage["LGA03_polarity"]["ACTIVE"] == 3
    assert coverage["LGA03_polarity"]["INACTIVE"] == 4
    checks.append("COVERAGE_AND_LGA03_POLARITY_VALID")

    result = {
        "passed": True,
        "validation_result": "PASS",
        "checks": checks,
        "task_count": 48,
        "admitted_task_count": 14,
        "old_benchmark_unchanged": True,
        "rollout_rerun": False,
        "success_compliance_calibration_rerun": False,
    }
    write(HERE / "static_validation.json", result)
    report = """# Formal State Admission Report

**FORMAL_STATE_ADMISSION_VERDICT = COMPLETE**

## Version

- New benchmark: `PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1`
- Original benchmark retained: `PHASE_A_UNIFIED_BENCHMARK_V1`
- Composition: 34 original + 14 admitted state-expansion tasks = 48 tasks
- Original benchmark unchanged: true
- Rollout rerun: false
- Success/Compliance calibration rerun: false

All `travel_request_001`–`travel_request_014` tasks were admitted. The three `ADMIT_LOW_HEADROOM` tasks (`travel_request_010`–`travel_request_012`) were retained unchanged.

## Independent-state coverage

| Mechanism | Before | Added | After |
|---|---:|---:|---:|
| P1 | 4 | 0 | 4 |
| P3 | 2 | 0 | 2 |
| P4 | 2 | 3 | 5 |
| P5 | 5 | 0 | 5 |
| LGA01 | 2 | 4 | 6 |
| LGA03 | 2 | 5 | 7 |
| LGA04 | 3 | 2 | 5 |

Coverage counts usable independent native states, not raw mechanism-label occurrences.

LGA03 polarity after admission: ACTIVE = 3; INACTIVE = 4. The complete task/state mapping is stored in `mechanism_coverage_snapshot.json`.

## Metadata and runtime contracts

The 14 additions retain mechanism, native state ID, `STATE_EXPANSION` origin, frozen structural topology, LGA03 polarity, calibration headroom, and state diversity in a separate analysis-only metadata manifest. Task objects remain semantically unchanged and contain no construction metadata. The existing whitelist request envelopes remain identical with zero leakage matches.

Success dispatch routes the 14 additions to the frozen Phase-2 deterministic evaluator and preserves the v1 dispatch for the original 34 tasks. Final Context remains domain-wide `AIRLINE_PHASE_A_FINAL_V1` / `RETAIL_PHASE_A_FINAL_V1`; task-specific masking remains false.

## Validation

PASS: 48 unique task IDs; all 14 additions present; all tasks schema-valid; custom evaluator dispatch resolves for all additions; v1 evaluator dispatch is preserved; Final Context assignments are valid; learner-safe filtering remains intact; original v1 hashes are unchanged.

## Scope and next gap

No task prompt, evaluator semantics, native DB, Final Context, canonical policy, or mechanism definition was modified. No Train/Monitor split, P3 mining, Gate, rollout, or Skill Evolution was run.

The next obvious state-count gap remains P3: 2 independent states versus soft target 5 (gap 3). This report records the gap only and does not begin mining.
"""
    (HERE / "FORMAL_STATE_ADMISSION_REPORT.md").write_text(report)
    print("Formal state admission validation PASS: 48 unique tasks; v1 unchanged; no rollout/evaluation rerun.")


if __name__ == "__main__":
    main()
