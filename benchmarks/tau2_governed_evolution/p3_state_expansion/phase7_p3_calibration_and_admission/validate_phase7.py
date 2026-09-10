"""Static integrity checks for Phase-7 artifacts; performs no model calls."""

import hashlib
import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
PHASE6 = HERE.parent / "phase6_clean_task_realization"
REPO = HERE.parents[3]
FORMAL = REPO / "benchmarks/tau2_governed_evolution/formal_state_admission"


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []
    manifest = load(HERE / "runtime/run_manifest.json")
    config = load(HERE / "runtime/run_config.json")
    frozen_config = load(REPO / "benchmarks/tau2_governed_evolution/phase_a_final_unified_benchmark_v1/calibration/run_config.json")
    task_ids = [row["task_id"] for row in manifest["tasks"]]
    assert task_ids == ["retail_request_001", "retail_request_002", "retail_request_003"]
    assert [seed for row in manifest["tasks"] for seed in row["seeds"]] == list(range(960145, 960154))
    assert manifest["planned_trajectories"] == 9
    assert not manifest["old_benchmark_tasks_rerun"]
    checks.append("ONLY_THREE_NEW_P3_TASKS_SCHEDULED")

    comparable = dict(config)
    comparable["planned_rollouts"] = frozen_config["planned_rollouts"]
    assert comparable == frozen_config and config["planned_rollouts"] == 9
    assert config["skill"] == "EMPTY" and config["skill_injection"] is None
    checks.append("FROZEN_RUNTIME_CONFIG_AND_EMPTY_SKILL")

    run_summary = load(HERE / "runtime/run_summary.json")
    assert len(run_summary) == 9 and all(row["status"] == "completed" for row in run_summary)
    expected_stems = {f"{task_id}_{index:02d}" for task_id in task_ids for index in range(1, 4)}
    started = {path.name.removesuffix("_started.json") for path in (HERE / "trajectories").glob("*_started.json")}
    errors = list((HERE / "trajectories").glob("*_error.json"))
    assert started == expected_stems and not errors
    for stem in expected_stems:
        for suffix in (".json", "_raw.json", "_final_db.json"):
            assert (HERE / "trajectories" / f"{stem}{suffix}").is_file()
        for kind in ("success", "compliance"):
            assert (HERE / "evaluations" / kind / f"{stem}.json").is_file()
        result = load(HERE / "trajectories" / f"{stem}.json")
        assert digest(HERE / "trajectories" / f"{stem}_raw.json") == result["raw_sha256"]
    checks.append("NINE_COMPLETE_IMMUTABLE_TRAJECTORY_SETS")

    preflight = load(HERE / "runtime/learner_safe_preflight.json")
    assert preflight["requests"] == 3 and preflight["construction_metadata_leakage_matches"] == 0
    for task_id in task_ids:
        assert load(HERE / "requests" / f"{task_id}.json") == load(PHASE6 / "requests" / f"{task_id}.json")
    checks.append("LEARNER_SAFE_PREFLIGHT_ZERO_LEAKAGE")

    results = [load(HERE / "trajectories" / f"{stem}.json") for stem in sorted(expected_stems)]
    counts = Counter(("C" if row["compliance"] else "V") + ("S" if row["success"] else "F") for row in results)
    summary = load(HERE / "p3_calibration_summary.json")
    assert summary["success"] == sum(row["success"] for row in results) == 0
    assert summary["compliance"] == sum(row["compliance"] for row in results) == 5
    assert summary["quadrants"] == {key: counts[key] for key in ("CS", "CF", "VS", "VF")}
    assert not any(row["judge_evaluator_recovery"] for row in results)
    checks.append("RAW_METRICS_RECOMPUTED_AND_UNCHANGED")

    focal = load(HERE / "p3_focal_attribution.json")
    assert focal["counts"] == {
        "CORRECT_REFRESH_DEPENDENCY": 7,
        "STALE_RESOURCE_REASONING": 2,
        "OTHER_FAILURE": 0,
        "UNCERTAIN": 0,
    }
    assert focal["posthoc_actual_goal_completion_with_money_tolerance"] == 7
    assert not focal["raw_scores_overwritten"]
    checks.append("FOCAL_ATTRIBUTION_AND_EVALUATOR_DEFECT_SEPARATED")

    admission = load(HERE / "p3_post_calibration_admission.json")
    formal = load(HERE / "p3_formal_admission.json")
    assert admission["REVIEW_IMPLEMENTATION"] == task_ids
    assert not admission["ADMIT"] and not admission["ADMIT_LOW_HEADROOM"] and not admission["REJECT_STRUCTURAL"]
    assert not formal["formal_admission_completed"] and formal["new_benchmark_version"] is None
    assert load(FORMAL / "expanded_benchmark_manifest.json")["total_tasks"] == 48
    assert digest(FORMAL / "expanded_benchmark_manifest.json") == formal["current_benchmark_preservation_sha256"]["expanded_benchmark_manifest.json"]
    assert digest(FORMAL / "tasks/expanded_tasks.json") == formal["current_benchmark_preservation_sha256"]["tasks/expanded_tasks.json"]
    checks.append("FORMAL_ADMISSION_WITHHELD_AND_48_TASK_BENCHMARK_PRESERVED")

    validation = {
        "validation_result": "PASS",
        "checks": checks,
        "scheduled_tasks": 3,
        "valid_trajectories": 9,
        "trajectory_reruns": 0,
        "learner_safe_leakage_matches": 0,
        "raw_success": 0,
        "raw_compliance": 5,
        "evaluator_bug_confirmed": True,
        "formal_admission_completed": False,
        "current_benchmark_unchanged": True,
    }
    (HERE / "phase7_validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
