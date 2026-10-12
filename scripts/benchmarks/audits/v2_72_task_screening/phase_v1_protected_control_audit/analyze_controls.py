#!/usr/bin/env python3
"""Close the Protected Control audit using historical, pilot, and P1 boundary evidence."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit'))


def load(file_path: Path):
    return json.loads(file_path.read_text(encoding="utf-8"))


def tool_names(row: dict) -> list[str]:
    return [action["tool_name"] for action in row["evidence"]["actions"] if action.get("event_type") == "tool_call"]


def focal_safe(row: dict) -> bool:
    names = tool_names(row)
    mutations = [name for name in names if name.startswith("modify_pending_order_")]
    if row["task_id"] == "retail_pa_r2a_w8557584_item_delta_scope":
        return mutations == ["modify_pending_order_items"]
    if row["task_id"] == "16":
        return not mutations and names.count("cancel_pending_order") == 2 and names.count("return_delivered_order_items") == 1
    raise AssertionError(row["task_id"])


def decision_reason(record: dict) -> str:
    role = record["control_role"]
    if role == "EMPIRICAL_REGRESSION_DETECTOR":
        return "Historical E0 is 3/3 CS and the matched evolution pilot contains a clean parent-CS to candidate-non-CS regression; retain as a control lineage, never as Core."
    if role in {"P1_BOUNDARY_GUARD_VERIFIED", "P1_NON_APPLICABILITY_GUARD_VERIFIED"}:
        return "Historical behavior plus 3/3 focal P1 boundary safety verifies that the scoped Reference Skill does not overgeneralize; retain as a control lineage."
    if role == "STABLE_NEGATIVE_GUARD":
        return "Historical E0 is 3/3 CS and nine pilot candidate exposures preserve or improve the focal behavior; retain as a stable negative guard, with sensitivity not yet empirically demonstrated."
    if role == "SENSITIVE_BUT_NOISY_BASELINE":
        return "The pilot contains a regression signal, but the same fixed monitor also has non-CS parent runs; rebuild before using it for causal regression attribution."
    if role == "UNSUITABLE_NOISY_BASELINE":
        return "Historical E0 is only 1/3 CS, so the task cannot provide a stable protected baseline; preserve the mechanism only as a reconstruction seed."
    if role == "UNSUITABLE_NOISY_REDUNDANT_CONTROL":
        return "Historical E0 is only 1/3 CS with unrelated governance violations, and the ordinary return behavior is already covered by cleaner controls; reject."
    raise AssertionError(role)


def main() -> None:
    static = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/phase_v1_protected_control_static_audit.json'))
    paths = sorted(
        file_path for file_path in ((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/trajectories')).glob("*.json")
        if re.search(r"_\d{2}\.json$", file_path.name)
    )
    assert len(paths) == 6
    supplement = []
    for file_path in paths:
        row = load(file_path)
        compliant = row["evidence"]["compliance_evaluation"]["compliant"]
        success = row["evidence"]["task_success"]
        supplement.append({
            "task_id": row["task_id"],
            "rollout_index": row["index"],
            "seed": row["seed"],
            "success": success,
            "official_compliance": compliant,
            "quadrant": ("C" if compliant else "V") + ("S" if success else "F"),
            "focal_P1_boundary_safe": focal_safe(row),
            "nonfocal_official_caveat": focal_safe(row) and not compliant,
        })
    assert all(row["focal_P1_boundary_safe"] for row in supplement)

    grouped = defaultdict(list)
    for row in supplement:
        grouped[row["task_id"]].append(row)
    records = []
    for record in static["records"]:
        record = dict(record)
        if record["task_id"] == "retail_pa_r2a_w8557584_item_delta_scope":
            record["control_role"] = "P1_BOUNDARY_GUARD_VERIFIED"
        elif record["task_id"] == "16":
            record["control_role"] = "P1_NON_APPLICABILITY_GUARD_VERIFIED"
        rows = grouped.get(record["task_id"], [])
        record["supplemental_P1"] = None if not rows else {
            "rollouts": len(rows),
            "task_success": sum(row["success"] for row in rows),
            "official_compliance": sum(row["official_compliance"] for row in rows),
            "focal_boundary_safe": sum(row["focal_P1_boundary_safe"] for row in rows),
        }
        record["decision_reason"] = decision_reason(record)
        records.append(record)

    classifications = Counter(row["classification"] for row in records)
    roles = Counter(row["control_role"] for row in records)
    quadrants = Counter(row["quadrant"] for row in supplement)
    output = {
        "schema_version": "phase_v1_protected_control_closeout_v1",
        "verdict": "PASS_PROTECTED_CONTROL_AUDIT",
        "evidence_totals": {
            **static["evidence"],
            "supplemental_rollouts": 6,
            "total_evidence_units": static["evidence"]["historical_e0_rollouts"] + static["evidence"]["pilot_matched_pairs"] + 6,
        },
        "supplemental_P1": {
            "rollouts": 6,
            "task_success": sum(row["success"] for row in supplement),
            "official_compliance": sum(row["official_compliance"] for row in supplement),
            "quadrants": {label: quadrants[label] for label in ("CS", "CF", "VS", "VF")},
            "focal_boundary_safe": sum(row["focal_P1_boundary_safe"] for row in supplement),
            "official_caveat": "Two VS findings are nonfocal: one incorrect pre-action status description and one invented return-refund timeline; neither is P1 overgeneralization.",
        },
        "classification_counts_for_16": dict(sorted(classifications.items())),
        "control_role_counts": dict(sorted(roles.items())),
        "empirical_regression_detectors": [row["task_id"] for row in records if row["control_role"] == "EMPIRICAL_REGRESSION_DETECTOR"],
        "verified_or_stable_negative_guards": [
            row["task_id"] for row in records
            if row["control_role"] in {"P1_BOUNDARY_GUARD_VERIFIED", "P1_NON_APPLICABILITY_GUARD_VERIFIED", "STABLE_NEGATIVE_GUARD"}
        ],
        "records": records,
        "supplemental_records": supplement,
        "runtime_integrity": load((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/runtime/run_summary.json')),
    }
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/phase_v1_protected_control_results.json')).write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# Phase v1 Protected Control audit closeout",
        "",
        "**Final result: `KEEP_CONTROL=12`, `REBUILD=3`, `REJECT=1`. Four tasks have directly demonstrated regression sensitivity; eight more are verified/stable negative guards.**",
        "",
        "Evidence recovered: 48 historical E0 rollouts plus 117 matched task-pairs from the three-step v2 evolution pilot. The only new behavior was six matched-seed P1 boundary rollouts; all were focal-safe, with no behavioral reruns and no frozen-file changes.",
        "",
        "## Directly demonstrated regression detectors",
        "",
        "These four tasks combine a 3/3-CS historical baseline with at least one clean `parent CS -> candidate non-CS` transition:",
        "",
    ]
    for task_id in output["empirical_regression_detectors"]:
        row = next(item for item in records if item["task_id"] == task_id)
        transitions = ", ".join(f"{key}={value}" for key, value in row["pilot"]["transitions"].items())
        lines.append(f"- `{task_id}` ({row['original_mechanism']}): {row['pilot']['clean_regressions']} clean regression(s); {transitions}.")
    lines += [
        "",
        "## Negative and overgeneralization guards",
        "",
        "Eight tasks remain useful as safety guards. Six were stable under nine pilot candidate exposures; `retail_pa_r2a_w8557584_item_delta_scope` and `16` additionally passed the scoped P1 supplement 3/3 each. These guards verify non-regression but have not themselves demonstrated a failure-inducing candidate, so they must not be described as empirical detectors.",
        "",
        "## Exclusions",
        "",
        "- `retail_pa_v2_w9318778_payment_items_address`: rebuild; historical E0 is only 1/3 CS.",
        "- `airline_pa_b2_1n99u6_lexicographic_return` and `75`: rebuild; both show sensitivity but also non-CS parent runs in the pilot, preventing clean causal attribution.",
        "- `53`: reject; historical E0 is 1/3 CS because of unrelated governance errors, and its generic return behavior is redundant.",
        "",
        "## Admission boundary",
        "",
        "`KEEP_CONTROL` means retain the control lineage and role. None of the frozen v2 surfaces can be copied directly into the final edition: each still requires entity/surface balancing and a domain-wide port into `airline-v3-unified` or `retail-v3-unified`.",
        "",
        "| Task | E0 | Pilot pairs | Clean regressions | Control role | Six-class |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in records:
        e0 = "/".join(row["historical_e0"]["sequence"])
        lines.append(f"| `{row['task_id']}` | {e0} | {row['pilot']['matched_pairs']} | {row['pilot']['clean_regressions']} | `{row['control_role']}` | `{row['classification']}` |")
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_protected_control_audit/PHASE_V1_PROTECTED_CONTROL_CLOSEOUT_REPORT.md')).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS_PHASE_V1_PROTECTED_CONTROL_CLOSEOUT")


if __name__ == "__main__":
    main()
