"""Static integrity checks for the completed Phase-3 calibration."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(relative):
    return json.loads((HERE / relative).read_text())


def main():
    manifest = load("runtime/run_manifest.json")
    assert manifest["old_34_tasks_rerun"] is False
    assert manifest["original_102_parent_trajectories_reused_or_untouched"] is True
    assert len(manifest["tasks"]) == 14
    seeds = [seed for task in manifest["tasks"] for seed in task["seeds"]]
    assert seeds == list(range(960103, 960145))
    assert load("runtime/learner_safe_preflight.json")["construction_metadata_leakage_matches"] == 0
    for task in manifest["tasks"]:
        for index in range(1, 4):
            stem = HERE / "trajectories" / f'{task["task_id"]}_{index:02d}'
            assert Path(str(stem) + "_raw.json").is_file()
            assert Path(str(stem) + "_final_db.json").is_file()
            assert Path(str(stem) + ".json").is_file()
            assert (HERE / "evaluations/success" / f'{task["task_id"]}_{index:02d}.json').is_file()
            assert (HERE / "evaluations/compliance" / f'{task["task_id"]}_{index:02d}.json').is_file()
    raw = load("analysis/raw_quadrant_summary.json")
    assert (raw["success"], raw["compliance"]) == (37, 13)
    assert raw["quadrants"] == {"CS": 13, "CF": 0, "VS": 24, "VF": 5}
    topology = load("analysis/topology_aware_summary.json")
    assert topology["CO_SATISFIABLE"]["trajectories"] == 18
    assert topology["POLICY_CONFLICT"]["trajectories"] == 24
    attribution = load("analysis/focal_mechanism_attribution.json")["trajectories"]
    assert len(attribution) == 42
    assert sum(row["FOCAL_HANDLING"] == "CORRECT" for row in attribution) == 13
    assert sum(row["FOCAL_HANDLING"] == "INCORRECT" for row in attribution) == 29
    admission = load("analysis/post_calibration_admission.json")
    assert len(admission["ADMIT"]) == 11 and len(admission["ADMIT_LOW_HEADROOM"]) == 3
    assert not admission["REVIEW_IMPLEMENTATION"] and not admission["REJECT_STRUCTURAL"]
    required = [
        "analysis/per_task_calibration.json", "analysis/focal_headroom_summary.json",
        "analysis/runtime_validity.json", "family_analysis/p4_calibration.json",
        "family_analysis/lga01_calibration.json", "family_analysis/lga03_calibration.json",
        "family_analysis/lga04_calibration.json", "PHASE3_EMPTY_SKILL_CALIBRATION_REPORT.md",
    ]
    assert all((HERE / path).is_file() for path in required)
    print("Phase 3 validation PASS: 14 tasks, 42 immutable trajectories, complete evaluation and analysis artifacts.")


if __name__ == "__main__":
    main()
