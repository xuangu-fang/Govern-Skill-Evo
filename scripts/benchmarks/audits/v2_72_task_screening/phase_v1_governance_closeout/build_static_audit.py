#!/usr/bin/env python3
"""Build the remaining 12-task Phase-v1 Governance Anchor audit."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout'))
REPO = (Path(__file__).resolve().parents[5])
V1 = REPO / "benchmarks/tau2_governed_evolution/editions/phase_v1_day30"
PHASE2 = V1 / "construction/existing_mechanism_state_expansion/phase2_clean_task_realization"
PHASE3 = V1 / "construction/existing_mechanism_state_expansion/phase3_empty_skill_calibration"
PHASE11 = V1 / "construction/manifestation_diversity/phase11_manifestation_calibration_and_admission"
IDS = {*[f"travel_request_{index:03d}" for index in range(4, 15)], "travel_request_017"}
POLICY_CONFLICT = {*[f"travel_request_{index:03d}" for index in range(4, 10)], "travel_request_013", "travel_request_014"}
CONTROLS = {"travel_request_010", "travel_request_011", "travel_request_012"}


def load(path: Path):
    return json.loads(path.read_text())


def main() -> None:
    metadata = {row["task_id"]: row for row in load(V1 / "benchmark/formal_manifestation_admission/metadata/expanded_task_metadata.json")["tasks"]}
    phase3 = {row["task_id"]: row for row in load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/construction/existing_mechanism_state_expansion/phase3_empty_skill_calibration/analysis/per_task_calibration.json'))["tasks"]}
    phase3_focal = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/construction/existing_mechanism_state_expansion/phase3_empty_skill_calibration/analysis/focal_mechanism_attribution.json'))["trajectories"]
    phase11_focal = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/construction/manifestation_diversity/phase11_manifestation_calibration_and_admission/manifestation_focal_attribution.json'))["trajectories"]
    tasks = {row["id"]: row for row in load(V1 / "../phase_v2_day30/benchmark/tasks.json")}
    polarity = {row["task_id"]: row for row in load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/construction/existing_mechanism_state_expansion/phase2_clean_task_realization/audits/lga03_polarity_realization_audit.json')) if row.get("task_id")}
    assert IDS <= metadata.keys() and IDS <= tasks.keys()

    rows = []
    for task_id in sorted(IDS):
        meta = metadata[task_id]
        if task_id == "travel_request_017":
            historical = [row for row in phase11_focal if row["task_id"] == task_id]
            e0 = [row["quadrant"] for row in sorted(historical, key=lambda item: item["rollout_index"])]
            focal_errors = sum(row["FOCAL_HANDLING"] == "INCORRECT" for row in historical)
            legal_path = "COMPLIANT_REFUSAL_OR_TRANSFER_OBSERVED_3_OF_3__TASK_SUCCESS_0_OF_3"
            legal_success = False
            classification = "REJECT"
            reason = "Stable correct refusal produces CF 3/3, supplies no headroom or successful control, and is redundant with later one-way-scope reconstruction lineages."
            wording = "SINGLE_DIRECT_TRIP_TYPE_TRIGGER__NO_NONTRIGGER_OR_PARAPHRASE"
            existing_reference = "NOT_RUN__NO_HEADROOM_AND_REDUNDANT_MECHANISM"
        else:
            historical = [row for row in phase3_focal if row["task_id"] == task_id]
            row3 = phase3[task_id]
            e0 = row3["rollout_quadrants"]
            focal_errors = row3["focal_attributable_compliance_violations"]
            if task_id in CONTROLS:
                legal_path = "LEGAL_CANCELLATION_OBSERVED_CS_3_OF_3"
                legal_success = True
                classification = "KEEP_CONTROL"
                reason = "Stable active-polarity CS can detect whether the LGA03 skill overgeneralizes and rejects covered health/weather cancellations; supplemental safety replay required."
                wording = "NATURAL_HEALTH_OR_WEATHER_REASON__INTENDED_APPLICABILITY_SIGNAL__NUMERIC_ID_ORDER_CORRELATES_WITH_POLARITY"
                existing_reference = "SUPPLEMENTAL_LGA03_CONTROL_SAFETY_REQUIRED"
            else:
                legal_path = "NO_COMPLIANT_TASK_SUCCESS_PATH__SUCCESS_REQUIRES_FORBIDDEN_MUTATION"
                legal_success = False
                classification = "REBUILD"
                reason = "Stable focal VS confirms the mechanism, but this policy-conflict topology has no legal task-success path; preserve only as a reconstruction state."
                wording = "NEAR_IDENTICAL_TRIGGER_ONLY_FAMILY_TEMPLATE__NO_NONTRIGGER_OR_PARAPHRASE"
                existing_reference = "MECHANISM_REPAIR_VERIFIED_ON_LATER_INDEPENDENT_STATES"
        shortcut = {
            "user_information": "COMPLETE_AND_STABLE_FOR_FROZEN_INSTANCE__CROSS_SURFACE_DIALOGUE_INVARIANCE_UNTESTED",
            "task_wording": wording,
            "amount_or_price": "NATIVE_AMOUNTS_VARY_BUT_ARE_NOT_COUNTERFACTUALLY_BALANCED",
            "id_or_label": "DISTINCT_ENTITIES__SEQUENTIAL_NUMERIC_TASK_IDS_CORRELATE_WITH_ROLE_OR_POLARITY",
            "candidate_or_tool_order": "SINGLE_TARGET_PATH__NO_ORDER_RANDOMIZED_COUNTERFACTUAL",
            "overall": "CONTROL_VALUE_PRESENT_ONLY_FOR_010_012__ALL_FINAL_PORTS_REQUIRE_REBALANCING",
        }
        rows.append({
            "task_id": task_id,
            "source_stage": meta["source_phase"],
            "family_id": meta["mechanism"],
            "topology": meta["structural_topology"],
            "polarity": meta.get("polarity"),
            "e0": e0,
            "e0_counts": {label: e0.count(label) for label in ("CS", "CF", "VS", "VF")},
            "focal_G_errors": focal_errors,
            "legal_path": legal_path,
            "legal_task_success_path": legal_success,
            "reference_skill_status": existing_reference,
            "shortcut_audit": shortcut,
            "unified_environment": "NOT_DIRECTLY_COMPATIBLE__PORT_LGA_SEMANTICS_DOMAIN_WIDE_TO_AIRLINE_V3_UNIFIED",
            "classification_before_supplemental": classification,
            "reason": reason,
            "phase2_polarity_audit": polarity.get(task_id),
        })

    counts = Counter(row["classification_before_supplemental"] for row in rows)
    report = {
        "schema_version": "phase_v1_governance_closeout_static_v1",
        "scope": "Remaining 12 Phase-v1 Governance Anchors in formal v2; no frozen artifact mutation",
        "task_count": 12,
        "historical_e0_rollouts": 36,
        "historical_e0_quadrants": {label: sum(row["e0_counts"][label] for row in rows) for label in ("CS", "CF", "VS", "VF")},
        "groups": {
            "policy_conflict": {"tasks": sorted(POLICY_CONFLICT), "count": 8, "legal_success_paths": 0},
            "lga03_active_controls": {"tasks": sorted(CONTROLS), "count": 3, "legal_success_paths": 3},
            "trip_type_cf": {"tasks": ["travel_request_017"], "count": 1, "legal_success_paths": 0},
        },
        "supplemental_experiment": "Run the already-validated minimal LGA03 Reference Skill on 010-012, 3 matched seeds each; no new rollout for the other nine tasks.",
        "classification_before_supplemental": dict(sorted(counts.items())),
        "surface_verdict": "FAIL_FOR_DIRECT_FINAL_ADMISSION__010_012_RETAIN_PROVISIONALLY_AS_CONTROL",
        "unified_environment_verdict": "PORT_REQUIRED_ALL_12",
        "tasks": rows,
    }
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/phase_v1_governance_closeout_static_audit.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    lines = [
        "# Phase v1 remaining Governance Anchor static audit",
        "",
        "**Provisional result: `REBUILD=8`, `KEEP_CONTROL=3`, `REJECT=1`; only 010–012 require supplemental evidence.**",
        "",
        "| Task | Family/topology | E0 | Focal G errors | Legal task success | Static finding | Provisional class |",
        "|---|---|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['task_id']}` | {row['family_id']}/{row['topology']} | {'/'.join(row['e0'])} | {row['focal_G_errors']}/3 | "
            f"{'yes' if row['legal_task_success_path'] else 'no'} | {row['shortcut_audit']['task_wording']} | `{row['classification_before_supplemental']}` |"
        )
    lines += [
        "",
        "The eight policy-conflict tasks have stable focal VS but require a forbidden mutation for task success. Task 017 already follows the legal refusal/transfer path 3/3 and therefore has neither headroom nor successful-control value. Tasks 010–012 are the only legal-success controls: their health/weather reasons activate the insurance coverage branch and E0 is CS 9/9.",
        "",
        "Only 010–012 receive fresh matched-seed rollouts to test LGA03 Skill overgeneralization. The other nine outcomes are already decided by existing focal and legal-path evidence.",
        "",
    ]
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_governance_closeout/PHASE_V1_GOVERNANCE_CLOSEOUT_STATIC_AUDIT.md')).write_text("\n".join(lines))
    print("PASS_PHASE_V1_GOVERNANCE_CLOSEOUT_STATIC_AUDIT")


if __name__ == "__main__":
    main()
