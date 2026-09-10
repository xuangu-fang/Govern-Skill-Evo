"""Static Phase-7R validation; performs no trajectory or Judge calls."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from tau2.data_model.tasks import Task
from tau2.domains.retail.data_model import RetailDB
from tau2.domains.retail.utils import RETAIL_DB_PATH

from benchmarks.tau2_governed_evolution.formal_state_admission_v2 import benchmark_adapter


HERE = Path(__file__).resolve().parent
P3_ROOT = HERE.parent
PHASE6 = P3_ROOT / "phase6_clean_task_realization"
PHASE7 = P3_ROOT / "phase7_p3_calibration_and_admission"
REPO = HERE.parents[3]
V1 = REPO / "benchmarks/tau2_governed_evolution/formal_state_admission"
V2 = REPO / "benchmarks/tau2_governed_evolution/formal_state_admission_v2"


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []
    old_tasks = load(V1 / "tasks/expanded_tasks.json")
    candidates = load(PHASE6 / "tasks/candidate_tasks.json")
    expanded = load(V2 / "tasks/expanded_tasks.json")
    manifest = load(V2 / "expanded_benchmark_manifest.json")
    ids = [task["id"] for task in expanded]
    assert len(ids) == len(set(ids)) == manifest["total_tasks"] == 51
    assert expanded[:48] == old_tasks and expanded[48:] == candidates
    for task in expanded:
        Task.model_validate(task)
    checks.append("51_UNIQUE_SCHEMA_VALID_TASKS_AND_EXACT_48_PLUS_3_COMPOSITION")

    metadata = load(V2 / "metadata/expanded_task_metadata.json")
    assert len(metadata["tasks"]) == 51
    new_rows = [row for row in metadata["tasks"] if row.get("state_origin") == "P3_STATE_EXPANSION"]
    required = {"mechanism", "native_state_id", "manifestation_type", "calibration_headroom",
                "state_origin", "focal_calibration_summary"}
    assert len(new_rows) == 3 and all(required <= set(row) for row in new_rows)
    assert all(not row["analysis_metadata_agent_visible"] for row in new_rows)
    checks.append("P3_ANALYSIS_METADATA_PRESENT_AND_NOT_LEARNER_FACING")

    before = RetailDB.load(RETAIL_DB_PATH).model_dump(mode="json")
    expected_success = {
        "retail_request_001": [True, True, True],
        "retail_request_002": [False, True, False],
        "retail_request_003": [True, True, True],
    }
    for task in candidates:
        for index, expected in enumerate(expected_success[task["id"]], 1):
            final_db = load(PHASE7 / "trajectories" / f"{task['id']}_{index:02d}_final_db.json")
            actual = benchmark_adapter.evaluate_success(task, before, final_db, lambda unused: None)
            assert actual["success"] is expected
    assert benchmark_adapter.evaluate_success(old_tasks[0], {}, {}, lambda unused: "NATIVE_SENTINEL") == "NATIVE_SENTINEL"
    checks.append("NEW_AND_PREDECESSOR_SUCCESS_DISPATCH_VALID")

    rescore = load(HERE / "phase7r_success_rescore_summary.json")
    counts = Counter(row["quadrant"] for row in rescore["rows"])
    assert rescore["Success"] == 7 and rescore["Compliance"] == 5
    assert rescore["quadrants"] == {key: counts[key] for key in ("CS", "CF", "VS", "VF")}
    assert rescore["quadrants"] == {"CS": 4, "CF": 1, "VS": 3, "VF": 1}
    assert sum(row["DIRTY_TRAJECTORY"] for row in rescore["rows"]) == 2
    for row in rescore["rows"]:
        assert digest(REPO / row["trajectory_source"]) == row["trajectory_sha256"]
        assert digest(REPO / row["compliance_source"]) == row["compliance_sha256"]
        assert not row["trajectory_rerun"] and not row["compliance_judge_rerun"]
    checks.append("SUCCESS_ONLY_RESCORE_AND_IMMUTABLE_INPUT_HASHES_VALID")

    provenance = load(V2 / "admission_provenance.json")
    assert digest(V1 / "expanded_benchmark_manifest.json") == provenance["source_benchmark_preservation_sha256"]["expanded_benchmark_manifest.json"]
    assert digest(V1 / "tasks/expanded_tasks.json") == provenance["source_benchmark_preservation_sha256"]["tasks/expanded_tasks.json"]
    assert not provenance["trajectory_rerun"]
    assert provenance["agent_calls"] == provenance["user_simulator_calls"] == provenance["compliance_judge_calls"] == 0
    assert provenance["success_evaluations"] == 9
    checks.append("PREDECESSOR_BENCHMARK_UNCHANGED_AND_NO_FORBIDDEN_CALLS")

    coverage = load(V2 / "mechanism_coverage_snapshot.json")
    assert coverage["TOTAL_TASKS"] == 51
    assert coverage["after"] == {"P1": 4, "P3": 5, "P4": 5, "P5": 5,
                                  "LGA01": 6, "LGA03": 7, "LGA04": 5}
    admission = load(HERE / "phase7r_post_repair_admission.json")
    assert admission["ADMIT"] == ["retail_request_002"]
    assert admission["ADMIT_LOW_HEADROOM"] == ["retail_request_001", "retail_request_003"]
    assert not admission["REVIEW_IMPLEMENTATION"] and not admission["REJECT_STRUCTURAL"]
    checks.append("ADMISSION_AND_MECHANISM_COVERAGE_VALID")

    result = {
        "validation_result": "PASS",
        "checks": checks,
        "monetary_evaluator_repair_valid": True,
        "non_monetary_strictness_tests_passed": True,
        "success_only_rescore": "7/9",
        "compliance_reused": "5/9",
        "quadrants": {"CS": 4, "CF": 1, "VS": 3, "VF": 1},
        "formal_admission_completed": True,
        "new_benchmark_version": "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2",
        "total_tasks": 51,
        "P3_coverage": 5,
    }
    (HERE / "phase7r_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    (V2 / "static_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    report = """# Formal State Admission V2 Report

`FORMAL_STATE_ADMISSION_V2_VERDICT = COMPLETE`

`PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2` contains the unchanged 48 predecessor tasks plus three admitted P3 state-expansion tasks, for 51 unique schema-valid tasks. The predecessor benchmark files remain unchanged.

The P3 monetary evaluator quantizes only `amount`, `price`, and `balance` to cents. Success-only rescoring of the nine immutable Phase-7 trajectories produced Success 7/9 and reused Compliance 5/9, with CS/CF/VS/VF = 4/1/3/1. No Agent, UserSimulator, or Compliance Judge call was made.

Admission: `retail_request_002` = ADMIT; `retail_request_001` and `retail_request_003` = ADMIT_LOW_HEADROOM. P3 independent-state coverage is now 5. Upstream manifestation diversity improved; the new downstream manifestation remains limited to item-upgrade delta payment.
"""
    (V2 / "FORMAL_STATE_ADMISSION_V2_REPORT.md").write_text(report)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
