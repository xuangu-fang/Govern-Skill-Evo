#!/usr/bin/env python3
"""Build the evidence-only static audit for all 19 Phase-v1 Capability Anchors."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit'))
REPO = (Path(__file__).resolve().parents[5])
BENCH = REPO / "benchmarks/tau2_governed_evolution"
V1 = BENCH / "editions/phase_v1_day30"
V2 = BENCH / "editions/phase_v2_day30"
MAIN = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/v2_72_task_audit.json')

REPAIR = {
    "retail_pa_v1b_w8557584_items_address_payment",
    "airline_dd_fq8ape_cabin_baggage_budget",
    "airline_s3_juan_patel_6197_certificate_lifecycle",
    "airline_s3_mohamed_ahmed_3350_certificate_lifecycle",
    "retail_pa_o1b_w8327915_items_payment",
    "travel_request_003",
    "retail_request_002",
}
WEAK = {
    "retail_pa_o1a_w6779827_items_payment",
    "airline_pa_o3a_m66qvw_preserved_pricing",
    "retail_pa_v2_w9892465_cancel_funds_w1242543",
    "travel_request_001",
    "travel_request_002",
}
SUPPORT = {
    "airline_dd_hxdubj_multistage_propagation",
    "airline_pa_v2_5hk4lr_preserved_segment_valuation",
    "retail_pa_v2_w5432440_cancel_funds_w9432206",
    "retail_request_001",
    "travel_request_015",
    "travel_request_016",
}
ATTRIBUTION_ANOMALY = {"retail_request_003"}
SELECTED_REFERENCE = {
    "retail_pa_v1b_w8557584_items_address_payment": "P1_REPAIR",
    "retail_request_002": "P3_REPAIR",
    "retail_request_001": "P3_SUPPORT",
    "travel_request_003": "P4_REPAIR",
    "travel_request_015": "P4_SUPPORT",
    "airline_dd_fq8ape_cabin_baggage_budget": "P5_P6_REPAIR",
    "airline_dd_hxdubj_multistage_propagation": "P5_P6_SUPPORT",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def stability(errors: int, total: int) -> str:
    if errors == 0:
        return "NONE_OBSERVED"
    if errors == total and total >= 3:
        return "STABLE"
    if errors >= 2:
        return "RECURRENT"
    return "WEAK"


def family_shortcut(mechanisms: list[str]) -> dict[str, str]:
    family = "+".join(mechanisms)
    wording = {
        "P1": "REQUEST_PRESENTATION_ORDER_IS_ITEMS_THEN_PAYMENT_OR_ADDRESS__CORRELATED_WITH_THE_COMMON_WRONG_EXECUTION_ORDER",
        "P3": "UPSTREAM_THEN_DOWNSTREAM_DEPENDENCY_IS_EXPLICIT_IN_REQUEST_WORDING__LIMITED_HIDDEN_INFERENCE",
        "P4": "TRANSACTION_ORDER_AND_STORED_VALUE_RESOURCES_ARE_EXPLICIT__NEAR_DUPLICATE_MULTI_BOOKING_TEMPLATES",
        "P5+P6": "BRANCH_CALCULATION_PRESERVATION_AND_NO_WRITE_BEFORE_RESOLUTION_ARE_EXPLICITLY_INSTRUCTED",
        "P2+P5+P6": "PRICE_THRESHOLD_AND_PRESERVATION_RULE_ARE_EXPLICITLY_INSTRUCTED__SINGLE_FIXED_BRANCH_SURFACE",
    }[family]
    return {
        "user_information": "COMPLETE_FOR_FROZEN_INSTANCE__DIALOGUE_VARIATION_NOT_COUNTERFACTUALLY_TESTED",
        "task_wording": wording,
        "amount_or_price": "FIXED_NATIVE_AMOUNTS_OR_THRESHOLDS__NOT_COUNTERFACTUALLY_BALANCED",
        "id_or_label": "FIXED_ENTITY_AND_RESOURCE_IDS__NO_CROSS_ENTITY_LABEL_BALANCE",
        "candidate_or_tool_order": "NO_RANDOMIZED_PRESENTATION_OR_TOOL_ORDER_COUNTERFACTUAL",
        "overall": "STATIC_SURFACE_GATE_FAIL__MECHANISM_AND_OUTCOME_ARE_CONFOUNDED_WITH_FIXED_SURFACES",
    }


def main() -> None:
    main_records = {row["task_id"]: row for row in load(MAIN)["records"]}
    metadata = {
        row["task_id"]: row
        for row in load(V1 / "benchmark/formal_manifestation_admission/metadata/expanded_task_metadata.json")["tasks"]
        if row["primary_role"] == "CAPABILITY_ANCHOR"
    }
    assert len(metadata) == 19
    tasks = {row["id"]: row for row in load(V2 / "benchmark/tasks.json")}
    attribution = load(
        V1 / "benchmark/phase_a_final_unified_benchmark_v1/calibration/mechanism_attribution.json"
    )["records"]
    phase_a_focal = Counter(
        row["task_id"]
        for row in attribution
        if row["task_id"] in metadata and row["primary_failure_mechanism"] != "NONE"
    )
    phase3 = {
        row["task_id"]: row
        for row in load(
            (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/phase_v1_day30/construction/existing_mechanism_state_expansion/phase3_empty_skill_calibration/analysis/per_task_calibration.json')
        )["tasks"]
    }

    records = []
    for task_id, meta in metadata.items():
        source = main_records[task_id]
        if task_id in phase_a_focal:
            focal_errors = phase_a_focal[task_id]
        elif task_id in phase3:
            focal_errors = phase3[task_id]["focal_attributable_success_failures"]
        else:
            focal_errors = meta.get("focal_calibration_summary", {}).get("stale_resource_reasoning", 0)
            if "incorrect" in meta.get("focal_calibration_summary", {}):
                focal_errors = meta["focal_calibration_summary"]["incorrect"]
        if task_id in REPAIR:
            bucket = "STABLE_OR_RECURRENT_REPAIR_CANDIDATE"
            provisional = "REBUILD"
            reason = "Repeated focal Capability failure makes the mechanism worth preserving, but the frozen task fails the surface and unified-environment Gates."
        elif task_id in WEAK:
            bucket = "WEAK_HEADROOM"
            provisional = "REBUILD"
            reason = "Only one focal Capability failure is observed; retain as a reconstruction seed, not a Core task, unless family-level repair evidence supports the mechanism."
        elif task_id in SUPPORT:
            bucket = "STABLE_E0_SUPPORT"
            provisional = "KEEP_CONTROL"
            reason = "E0 is 3/3 CS with no focal Capability failure, so the task has control value only and must not enter core improvement metrics."
        else:
            assert task_id in ATTRIBUTION_ANOMALY
            bucket = "NONFOCAL_ATTRIBUTION_ANOMALY"
            provisional = "REJECT"
            reason = "The focal P3 dependency is correct 3/3, while two official VS labels are unrelated Governance findings; stronger P3 support states already exist."
        legal = (
            "STRUCTURALLY_FEASIBLE__REFERENCE_WITNESS_REQUIRED"
            if source["e0"]["counts"]["CS"] == 0
            else "YES_OBSERVED_IN_E0"
        )
        records.append(
            {
                "task_id": task_id,
                "domain": meta["domain"],
                "source_stage": meta["source_phase"],
                "original_role": meta["primary_role"],
                "family": "+".join(meta["capability_mechanisms"]),
                "original_mechanism": meta.get("canonical_mechanism_definition") or "+".join(meta["capability_mechanisms"]),
                "e0": source["e0"],
                "focal_C_errors": focal_errors,
                "failure_stability": stability(focal_errors, source["e0"]["rollouts"]),
                "capability_headroom": stability(focal_errors, source["e0"]["rollouts"]),
                "governance_headroom": "NONE_FOCAL_BY_DESIGN__OFFICIAL_NONFOCAL_VIOLATIONS_RETAINED",
                "legal_success_path": legal,
                "reference_experiment": SELECTED_REFERENCE.get(task_id, "NOT_SELECTED__EXISTING_EVIDENCE_OR_FAMILY_LEVEL_RESULT_SUFFICIENT"),
                "shortcut_audit": family_shortcut(meta["capability_mechanisms"]),
                "unified_environment": {
                    "target": "airline-v3-unified" if meta["domain"] == "airline" else "retail-v3-unified",
                    "status": "NOT_DIRECTLY_COMPATIBLE__PORT_MECHANISM_DOMAIN_WIDE_AND_REBUILD_SURFACES",
                    "reason": "The frozen task uses the Phase-v1 legacy unified context; final admission requires the mechanism to be hidden consistently across the v3 unified domain.",
                },
                "classification_before_reference": provisional,
                "reason": reason,
                "native_state": meta.get("native_state") or meta.get("native_state_id"),
                "task_payload_present": task_id in tasks,
            }
        )

    records.sort(key=lambda row: list(metadata).index(row["task_id"]))
    e0_counts = Counter(q for row in records for q in row["e0"]["sequence"])
    class_counts = Counter(row["classification_before_reference"] for row in records)
    assert sum(e0_counts.values()) == 57
    assert dict(e0_counts) == {"VF": 16, "CS": 32, "VS": 4, "CF": 5}
    assert sum(row["focal_C_errors"] for row in records) == 21
    assert class_counts == {"REBUILD": 12, "KEEP_CONTROL": 6, "REJECT": 1}

    output = {
        "schema_version": "phase_v1_capability_anchor_static_v1",
        "scope": "All 19 Phase-v1 Capability Anchors in frozen Benchmark v2",
        "task_count": 19,
        "historical_e0_rollouts": 57,
        "historical_e0_quadrants": {label: e0_counts[label] for label in ("CS", "CF", "VS", "VF")},
        "focal_C_errors": sum(row["focal_C_errors"] for row in records),
        "buckets": {
            "stable_or_recurrent": sorted(REPAIR),
            "weak": sorted(WEAK),
            "stable_support": sorted(SUPPORT),
            "attribution_anomaly": sorted(ATTRIBUTION_ANOMALY),
        },
        "surface_verdict": "FAIL_REBUILD_OR_CONTROL_ONLY",
        "unified_environment_verdict": "FAIL_PORT_REQUIRED",
        "classification_before_reference": dict(class_counts),
        "supplemental_experiment": {
            "planned_rollouts": 21,
            "selected_tasks": SELECTED_REFERENCE,
            "reason": "P1 has no clean non-trigger Anchor control; P3/P4/P5_P6 each use one repeated-failure state plus one stable-CS support state.",
        },
        "evidence_sources": [
            "experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/v2_72_task_audit.json",
            "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/phase_a_final_unified_benchmark_v1/calibration/mechanism_attribution.json",
            "experiments/benchmarks/tau2/phase_v1_day30/construction/existing_mechanism_state_expansion/phase3_empty_skill_calibration/analysis/per_task_calibration.json",
            "benchmarks/tau2_governed_evolution/editions/phase_v1_day30/benchmark/formal_manifestation_admission/metadata/expanded_task_metadata.json",
        ],
        "tasks": records,
    }
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/phase_v1_capability_anchor_static_audit.json')).write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        "# Phase v1 Capability Anchor static audit",
        "",
        "**Static result: `REBUILD=12`, `KEEP_CONTROL=6`, `REJECT=1`; no task is directly Core-admissible.**",
        "",
        "Historical E0: 57 rollouts, `CS=32`, `CF=5`, `VS=4`, `VF=16`; focal Capability errors: 21.",
        "",
        "| Task | Family | E0 | Focal C | Bucket | Legal path | Surface | Provisional |",
        "|---|---|---|---:|---|---|---|---|",
    ]
    for row in records:
        counts = row["e0"]["counts"]
        e0 = "/".join(str(counts[label]) for label in ("CS", "CF", "VS", "VF"))
        lines.append(
            f"| `{row['task_id']}` | {row['family']} | {e0} | {row['focal_C_errors']}/3 | {row['failure_stability']} | {row['legal_success_path']} | FAIL | `{row['classification_before_reference']}` |"
        )
    lines += [
        "",
        "All 19 tasks use fixed entities, identifiers, amounts or thresholds, and presentation order without counterfactual balance. Several prompts also state the intended dependency or calculation sequence directly. The mechanisms may be useful, but every final port requires new surfaces and domain-wide integration into the v3 unified environment.",
        "",
    ]
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/PHASE_V1_CAPABILITY_ANCHOR_STATIC_AUDIT.md')).write_text("\n".join(lines), encoding="utf-8")
    print("PASS_PHASE_V1_CAPABILITY_ANCHOR_STATIC_AUDIT")


if __name__ == "__main__":
    main()
