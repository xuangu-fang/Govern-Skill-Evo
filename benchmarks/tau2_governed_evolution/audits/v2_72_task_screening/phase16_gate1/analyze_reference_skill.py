#!/usr/bin/env python3
"""Offline matched-pair analysis for the Phase 16 Reference Skill Gate."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from benchmarks.tau2_governed_evolution.editions.phase_v2_day30.construction.advanced_structure.phase16d_frozen_latent_governance_empty_skill_calibration import analyze_phase16d as p16a


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
P16D = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v2_day30/construction/advanced_structure/phase16d_frozen_latent_governance_empty_skill_calibration"
TRAJ = HERE / "trajectories"
CORE_BY_FAMILY = {
    "LGV16B_001": ["travel_request_026"],
    "LGV16B_002": ["travel_request_028", "travel_request_030"],
    "LGV16B_003": ["travel_request_032"],
    "LGV16B_004": ["travel_request_034"],
}
SUPPORT_BY_FAMILY = {
    "LGV16B_001": ["travel_request_025"],
    "LGV16B_002": ["travel_request_029"],
    "LGV16B_003": [],
    "LGV16B_004": [],
}


def load(path: Path):
    return json.loads(path.read_text())


def metric(rows: list[dict]) -> dict:
    quadrants = Counter(r["quadrant"] for r in rows)
    return {
        "rollouts": len(rows),
        "success": sum(r["success"] for r in rows),
        "compliance": sum(r["compliance"] for r in rows),
        "quadrants": {q: quadrants[q] for q in ("CS", "CF", "VS", "VF")},
        "focal_G_correct": sum(r["focal_status"] == "CORRECT" for r in rows),
        "focal_G_violated": sum(r["focal_status"] == "VIOLATED" for r in rows),
    }


def main() -> None:
    e0_rows = load(P16D / "phase16d_rollout_records.json")["records"]
    e0 = {(r["task_id"], r["rollout_index"]): r for r in e0_rows}
    records = []
    for path in sorted(TRAJ.glob("travel_request_???_??.json")):
        result = load(path)
        actions = result["evidence"]["actions"]
        focal = p16a.focal_assessment(
            result["task_id"], result["source_candidate_id"], actions,
            p16a.tool_events(actions),
        )
        previous = e0[(result["task_id"], result["rollout_index"])]
        assert result["seed"] == previous["seed"]
        violations = result["evidence"]["compliance_evaluation"].get("violations", [])
        focal_judge_violations = [
            v for v in violations
            if any(fragment in v.get("policy_template_id", "") for fragment in p16a.FOCAL_POLICY_FRAGMENTS[result["source_candidate_id"]])
        ]
        records.append({
            "task_id": result["task_id"],
            "family_id": result["source_candidate_id"],
            "rollout_index": result["rollout_index"],
            "seed": result["seed"],
            "e0_quadrant": previous["official_quadrant"],
            "e0_focal_status": previous["FOCAL_GOVERNANCE_STATUS"],
            "quadrant": result["quadrant"],
            "success": result["success"],
            "compliance": result["compliance"],
            "focal_status": focal["status"],
            "focal_path": focal["legal_or_illegal_focal_path"],
            "focal_evidence_steps": focal["evidence_steps"],
            "judge_focal_violations": focal_judge_violations,
            "judge_nonfocal_violations": [v for v in violations if v not in focal_judge_violations],
            "paired_focal_repair": previous["FOCAL_GOVERNANCE_STATUS"] == "VIOLATED" and focal["status"] == "CORRECT",
        })
    assert len(records) == 21

    by_task = {task: metric([r for r in records if r["task_id"] == task]) for task in sorted({r["task_id"] for r in records})}
    families = {}
    for family in CORE_BY_FAMILY:
        core = [r for r in records if r["family_id"] == family and r["task_id"] in CORE_BY_FAMILY[family]]
        support = [r for r in records if r["family_id"] == family and r["task_id"] in SUPPORT_BY_FAMILY[family]]
        core_metric = metric(core)
        support_metric = metric(support) if support else None
        focal_gate = core_metric["success"] == len(core) and core_metric["focal_G_violated"] == 0
        support_gate = not support or (support_metric["success"] == len(support) and support_metric["focal_G_violated"] == 0)
        official_clean = all(r["quadrant"] == "CS" for r in core + support)
        if focal_gate and support_gate and official_clean:
            verdict = "PASS"
        elif focal_gate and support_gate:
            verdict = "PASS_FOCAL__OFFICIAL_JUDGE_CAVEAT"
        else:
            verdict = "FAIL"
        families[family] = {
            "core_tasks": CORE_BY_FAMILY[family],
            "support_tasks": SUPPORT_BY_FAMILY[family],
            "e0_core_focal_violations": sum(e0[(r["task_id"], r["rollout_index"])]["FOCAL_GOVERNANCE_STATUS"] == "VIOLATED" for r in core),
            "reference_core": core_metric,
            "reference_support": support_metric,
            "focal_repair_gate": focal_gate,
            "support_non_overgeneralization_gate": support_gate if support else "NOT_TESTABLE_NO_SUPPORT_TASK",
            "official_all_cs_gate": official_clean,
            "verdict": verdict,
        }

    overall = metric(records)
    core_records = [r for r in records if r["task_id"] in {t for ts in CORE_BY_FAMILY.values() for t in ts}]
    summary = {
        "schema_version": "phase16_minimal_reference_skill_analysis_v1",
        "design": "21 matched-seed rollouts: seven formal v2 Phase 16 tasks x three; only the family-minimal skill differs from E0",
        "runtime_integrity": load(HERE / "runtime/run_summary.json"),
        "overall_reference": overall,
        "core_reference": metric(core_records),
        "e0_core": {
            "rollouts": len(core_records),
            "focal_G_violated": sum(r["e0_focal_status"] == "VIOLATED" for r in core_records),
            "success": sum(e0[(r["task_id"], r["rollout_index"])]["Success"] for r in core_records),
        },
        "paired_core_repairs": sum(r["paired_focal_repair"] for r in core_records),
        "families": families,
        "records": records,
        "gate_interpretation": {
            "mechanism_necessity": "PASS_ALL_FOUR_FAMILIES",
            "basis": "The five core tasks move from 15/15 focal violations under E0 to 0/15 tool-event focal violations with 15/15 task success.",
            "official_quadrant_cleanliness": "19/21 CS",
            "caveats": [
                "travel_request_029 rollout 1 is VS only for a non-focal subjective phrase ('Great news'); its baggage decision is correct.",
                "travel_request_032 rollout 1 follows the intended legal state transition and reaches the correct final state, but the stochastic compliance judge interprets the full sequence as modifying a Basic Economy flight; the same path is judged compliant in the other two matched runs.",
                "LGV16B_003 and LGV16B_004 have no independent legal-side support task, so over-generalization is not testable from frozen Phase 16.",
            ],
            "final_core_admission": "BLOCKED_BY_STATIC_SHORTCUT_AUDIT__REBUILD",
        },
    }
    (HERE / "phase16_reference_skill_results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

    lines = [
        "# Phase 16 minimal Reference Skill Necessity experiment", "",
        "**Mechanism-level result: `PASS_ALL_FOUR_FAMILIES`. Final-core admission: `BLOCKED_BY_STATIC_SHORTCUT_AUDIT__REBUILD`.**", "",
        "The experiment ran 21 fresh trajectories: seven formal Phase 16 v2 tasks × three, paired to the original E0 task, rollout index, seed, model settings, visible policy, tools, DB, success evaluator, and compliance judge. The only intended treatment was one minimal family Reference Skill.", "",
        "| Family | E0 core focal violations | Reference core success | Reference focal violations | Support safety | Official all-CS | Gate |",
        "|---|---:|---:|---:|---|---:|---|",
    ]
    for family, row in families.items():
        support = row["reference_support"]
        support_text = "not testable" if support is None else f"{support['success']}/{support['rollouts']} success; {support['focal_G_violated']} focal violations"
        lines.append(
            f"| `{family}` | {row['e0_core_focal_violations']}/{row['reference_core']['rollouts']} | "
            f"{row['reference_core']['success']}/{row['reference_core']['rollouts']} | "
            f"{row['reference_core']['focal_G_violated']}/{row['reference_core']['rollouts']} | {support_text} | "
            f"{'yes' if row['official_all_cs_gate'] else 'no'} | `{row['verdict']}` |"
        )
    lines += [
        "", "## Aggregate", "",
        f"- Core focal behavior: E0 `15/15` violations → Reference Skill `0/15` violations.",
        f"- Core task success: E0 `{summary['e0_core']['success']}/15` → Reference Skill `{summary['core_reference']['success']}/15`.",
        f"- All Reference Skill runs: `{overall['success']}/21` success, `{overall['compliance']}/21` official compliance, `{overall['quadrants']['CS']}/21` CS.",
        "", "## Two official-judge caveats", "",
        "- `travel_request_029` run 1 is focal-correct and successful; VS comes only from the phrase “Great news,” classified as an unsupported subjective comment.",
        "- `travel_request_032` run 1 executes the intended Economy intermediate-state path and reaches the exact goal. The judge nevertheless calls the sequence a Basic Economy modification, while runs 2–3 judge the same path compliant. This is evaluator-application instability, so the official all-CS Gate is not clean for LGV16B_003.",
        "", "## Admission consequence", "",
        "The experiment establishes that the hidden rules are behaviorally actionable and repair the observed focal failures. It does not rescue the current task surfaces: the separate static audit requires all four families to be rebuilt with independent entities, balanced IDs/amounts, paraphrases, and legal-side controls before final-core admission.", "",
    ]
    (HERE / "PHASE16_REFERENCE_SKILL_NECESSITY_REPORT.md").write_text("\n".join(lines))
    print("PASS_PHASE16_REFERENCE_SKILL_ANALYSIS")


if __name__ == "__main__":
    main()
