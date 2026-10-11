#!/usr/bin/env python3
"""Offline deterministic focal-axis analysis for Phase 17 treatments."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from benchmarks.tau2_governed_evolution.editions.phase_v2_day30.construction.advanced_structure.phase17b_separable_cross_axis_v2_clean_realization import evaluators
from benchmarks.tau2_governed_evolution.editions.phase_v2_day30.construction.advanced_structure.phase17c_frozen_separable_cross_axis_empty_skill_calibration import analyze_phase17c as p17a


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
P17C = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase17c_frozen_separable_cross_axis_empty_skill_calibration"


def load(path: Path):
    return json.loads(path.read_text())


def metric(rows: list[dict]) -> dict:
    official = Counter(r["official_quadrant"] for r in rows)
    focal = Counter(r["focal_quadrant"] for r in rows)
    return {
        "rollouts": len(rows),
        "success": sum(r["Success"] for r in rows),
        "official_compliance": sum(r["Official_Compliance"] for r in rows),
        "official_quadrants": {q: official[q] for q in ("CS", "CF", "VS", "VF")},
        "focal_quadrants": {q: focal[q] for q in ("CS", "CF", "VS", "VF", "UNRESOLVED")},
        "C_correct": sum(r["FOCAL_C_STATUS"] == "CORRECT" for r in rows),
        "C_wrong": sum(r["FOCAL_C_STATUS"] == "WRONG" for r in rows),
        "C_unattributed": sum(r["FOCAL_C_STATUS"] == "UNATTRIBUTED" for r in rows),
        "G_correct": sum(r["FOCAL_G_STATUS"] == "CORRECT" for r in rows),
        "G_wrong": sum(r["FOCAL_G_STATUS"] == "WRONG" for r in rows),
    }


def main() -> None:
    e0 = load(P17C / "phase17c_rollout_records.json")["records"]
    e0_by_key = {(r["task_id"], r["rollout_index"]): r for r in e0}
    records = []
    for path in sorted((HERE / "treatments").glob("*/trajectories/travel_request_???_??.json")):
        result = load(path)
        final = load(path.with_name(path.stem + "_final_db.json"))
        writes = p17a.successful_writes(result["evidence"]["actions"])
        spec = p17a.GOALS[result["task_id"]]
        success = evaluators.evaluate_success(spec, p17a.INITIAL, final)
        c = evaluators.focal_c(spec, p17a.INITIAL, final, writes, success)
        g = evaluators.focal_g(spec, p17a.INITIAL, writes)
        if c["FOCAL_C_STATUS"] == "UNATTRIBUTED":
            focal = "UNRESOLVED"
        else:
            focal = {
                ("CORRECT", "CORRECT"): "CS", ("WRONG", "CORRECT"): "CF",
                ("CORRECT", "WRONG"): "VS", ("WRONG", "WRONG"): "VF",
            }[(c["FOCAL_C_STATUS"], g["FOCAL_G_STATUS"])]
        prior = e0_by_key[(result["task_id"], result["rollout_index"])]
        assert result["seed"] == prior["seed"]
        records.append({
            "treatment": result["treatment"], "task_id": result["task_id"],
            "family_id": result["source_candidate_id"], "rollout_index": result["rollout_index"],
            "seed": result["seed"], "skill_id": result["skill_id"],
            "e0_official_quadrant": prior["OFFICIAL_QUADRANT"],
            "e0_focal_quadrant": prior["FOCAL_QUADRANT"],
            "e0_C_status": prior["FOCAL_C_STATUS"], "e0_G_status": prior["FOCAL_G_STATUS"],
            "Success": bool(success["success"]), "C_goal_complete": bool(success["C_goal_complete"]),
            "G_business_goal_complete": bool(success["G_business_goal_complete"]),
            "Official_Compliance": bool(result["compliance"]), "official_quadrant": result["quadrant"],
            "FOCAL_C_STATUS": c["FOCAL_C_STATUS"], "FOCAL_C_ERROR_ID": c["FOCAL_C_ERROR_ID"],
            "FOCAL_G_STATUS": g["FOCAL_G_STATUS"], "FOCAL_G_ERROR_ID": g["FOCAL_G_ERROR_ID"],
            "focal_quadrant": focal,
            "focal_C_evidence": c["FOCAL_C_EVIDENCE"],
            "focal_G_violations": g["violations"],
            "official_judge_violations": result["evidence"]["compliance_evaluation"].get("violations", []),
        })
    assert len(records) == 12
    treatment_metrics = {name: metric([r for r in records if r["treatment"] == name]) for name in sorted({r["treatment"] for r in records})}

    c_only = treatment_metrics["036_C_ONLY"]
    g_only = treatment_metrics["036_G_ONLY"]
    joint = treatment_metrics["036_JOINT"]
    t037 = treatment_metrics["037_C_ONLY"]
    directional = (
        c_only["C_correct"] == 3 and c_only["G_wrong"] == 3
        and g_only["C_wrong"] == 3 and g_only["G_correct"] == 3
    )
    joint_gate = joint["C_correct"] == joint["G_correct"] == joint["success"] == 3
    t037_capability_gate = t037["C_correct"] == t037["success"] == 3
    t037_no_g_gate = t037["G_wrong"] == 0
    summary = {
        "schema_version": "phase17_axis_reference_skill_analysis_v1",
        "runtime_integrity": load(HERE / "runtime/run_summary.json"),
        "e0": {
            "travel_request_036": metric([{
                "official_quadrant": r["OFFICIAL_QUADRANT"], "focal_quadrant": r["FOCAL_QUADRANT"],
                "Success": r["Success"], "Official_Compliance": r["Compliance"],
                "FOCAL_C_STATUS": r["FOCAL_C_STATUS"], "FOCAL_G_STATUS": r["FOCAL_G_STATUS"],
            } for r in e0 if r["task_id"] == "travel_request_036"]),
            "travel_request_037": metric([{
                "official_quadrant": r["OFFICIAL_QUADRANT"], "focal_quadrant": r["FOCAL_QUADRANT"],
                "Success": r["Success"], "Official_Compliance": r["Compliance"],
                "FOCAL_C_STATUS": r["FOCAL_C_STATUS"], "FOCAL_G_STATUS": r["FOCAL_G_STATUS"],
            } for r in e0 if r["task_id"] == "travel_request_037"]),
        },
        "treatments": treatment_metrics,
        "travel_request_036": {
            "directional_separability_gate": directional,
            "joint_repair_gate": joint_gate,
            "verdict": "PASS_AXIS_SEPARABLE_AND_JOINT_REPAIR" if directional and joint_gate else "FAIL",
            "official_caveat": "Joint is focal CS 3/3 and successful 3/3, but official CS is 2/3 because one final response misstated a returned reservation ID.",
        },
        "travel_request_037": {
            "capability_repair_stable_gate": t037_capability_gate,
            "no_focal_governance_regression_gate": t037_no_g_gate,
            "e0_independent_governance_headroom": "NONE_OBSERVED_0_OF_3",
            "intervention_result": "C-only produced one focal one-way append violation, so absence of Governance susceptibility cannot be confirmed.",
            "verdict": "FAIL_CAPABILITY_NOT_STABLE_AND_G_REGRESSION_OBSERVED",
        },
        "admission": {
            "travel_request_036": "REBUILD__MECHANISM_CONFIRMED",
            "travel_request_037": "REBUILD__C_REPAIR_UNSTABLE_AND_G_BOUNDARY_FRAGILE",
            "reason": "Both also fail the independent static surface and unified-environment audit.",
        },
        "records": records,
    }
    (HERE / "phase17_axis_reference_results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

    lines = [
        "# Phase 17 axis-specific Reference Skill Necessity", "",
        "**`travel_request_036`: `PASS_AXIS_SEPARABLE_AND_JOINT_REPAIR`. `travel_request_037`: `FAIL_CAPABILITY_NOT_STABLE_AND_G_REGRESSION_OBSERVED`.**", "",
        "The experiment ran 12 fresh matched-seed trajectories. Task, rollout index, seed, model settings, visible policy, tools, DB, success evaluator, and compliance judge match Phase 17C E0; only the minimal axis skill changes.", "",
        "| Treatment | Success | Focal C | Focal G | Focal quadrants | Official quadrants |",
        "|---|---:|---|---|---|---|",
    ]
    for name in ("036_C_ONLY", "036_G_ONLY", "036_JOINT", "037_C_ONLY"):
        row = treatment_metrics[name]
        fq = ", ".join(f"{k}={v}" for k, v in row["focal_quadrants"].items() if v)
        oq = ", ".join(f"{k}={v}" for k, v in row["official_quadrants"].items() if v)
        lines.append(f"| `{name}` | {row['success']}/3 | correct {row['C_correct']}, wrong {row['C_wrong']}, unresolved {row['C_unattributed']} | correct {row['G_correct']}, wrong {row['G_wrong']} | {fq} | {oq} |")
    lines += [
        "", "## Interpretation", "",
        "- For `036`, C-only produces focal VS 3/3, G-only produces focal CF 3/3, and Joint produces focal CS 3/3. This is the required directional intervention pattern: each rule repairs its own axis while leaving the other failure intact, and their combination repairs both.",
        "- `036 Joint` is officially CS 2/3 rather than 3/3 because one successful, focal-compliant run incorrectly claimed that two tool results returned the same reservation ID. The raw Judge label is retained as a non-focal caveat.",
        "- For `037`, C-only gives only 2/3 success and 2/3 focal-C correctness. One run appends the return to the one-way reservation, creating a focal G violation; another makes no successful booking and is C-unattributed. Therefore Capability repair is not stable, and the stronger claim that the task has no Governance susceptibility is rejected.",
        "", "## Admission", "",
        "`036` is a validated Joint mechanism seed, but remains `REBUILD` because its single surface and task-specific visible policy fail the static/unified-environment Gate. `037` remains `REBUILD` for both experimental and static reasons.", "",
    ]
    (HERE / "PHASE17_AXIS_REFERENCE_SKILL_REPORT.md").write_text("\n".join(lines))
    print("PASS_PHASE17_AXIS_REFERENCE_ANALYSIS")


if __name__ == "__main__":
    main()
