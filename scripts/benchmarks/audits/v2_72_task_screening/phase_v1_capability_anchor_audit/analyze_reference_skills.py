#!/usr/bin/env python3
"""Analyze focal repair and support safety for Capability Anchor skills."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit'))


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def calls(row: dict) -> list[dict]:
    return [action for action in row["evidence"]["actions"] if action.get("event_type") == "tool_call"]


def focal_correct(row: dict) -> bool:
    task_id = row["task_id"]
    tool_calls = calls(row)
    names = [call["tool_name"] for call in tool_calls]
    if task_id == "retail_pa_v1b_w8557584_items_address_payment":
        required = ["modify_pending_order_payment", "modify_pending_order_address", "modify_pending_order_items"]
        return all(name in names for name in required) and names.index("modify_pending_order_items") > max(
            names.index("modify_pending_order_payment"), names.index("modify_pending_order_address")
        )
    if task_id in {"retail_request_001", "retail_request_002"}:
        upstream = "cancel_pending_order" if task_id.endswith("001") else "modify_pending_order_payment"
        return (
            upstream in names
            and "modify_pending_order_items" in names
            and "get_user_details" in names[names.index(upstream) + 1 : names.index("modify_pending_order_items")]
        )
    if task_id == "travel_request_003":
        bookings = [call for call in tool_calls if call["tool_name"] == "book_reservation"]
        if len(bookings) != 2:
            return False
        first_payments = bookings[0]["arguments"]["payment_methods"]
        second_payments = bookings[1]["arguments"]["payment_methods"]
        return (
            first_payments == [{"payment_id": "gift_card_8516878", "amount": 100}]
            and second_payments == [{"payment_id": "certificate_8998287", "amount": 198}]
        )
    if task_id == "travel_request_015":
        booking = [call for call in tool_calls if call["tool_name"] == "book_reservation"]
        update = [call for call in tool_calls if call["tool_name"] == "update_reservation_flights"]
        return (
            len(booking) == len(update) == 1
            and booking[0]["arguments"]["payment_methods"] == [{"payment_id": "certificate_5753608", "amount": 200}]
            and update[0]["arguments"]["payment_id"] == "gift_card_2858570"
            and update[0]["arguments"]["cabin"] == "business"
        )
    if task_id in {
        "airline_dd_fq8ape_cabin_baggage_budget",
        "airline_dd_hxdubj_multistage_propagation",
    }:
        return bool(row["evidence"]["task_success"])
    raise AssertionError(task_id)


def main() -> None:
    paths = sorted(
        path
        for path in ((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/trajectories')).glob("*.json")
        if re.search(r"_\d{2}\.json$", path.name)
    )
    assert len(paths) == 21
    records = []
    for path in paths:
        row = load(path)
        compliant = row["evidence"]["compliance_evaluation"]["compliant"]
        success = row["evidence"]["task_success"]
        focal = focal_correct(row)
        records.append(
            {
                "task_id": row["task_id"],
                "rollout_index": row["index"],
                "seed": row["seed"],
                "family": row["skill_family"],
                "role": row["experiment_role"],
                "success": success,
                "official_compliance": compliant,
                "quadrant": ("C" if compliant else "V") + ("S" if success else "F"),
                "focal_C_correct": focal,
                "nonfocal_official_caveat": focal and not compliant,
                "recovery": row.get("recovery"),
            }
        )
    grouped = defaultdict(list)
    for row in records:
        grouped[row["task_id"]].append(row)
    per_task = {}
    for task_id, rows in sorted(grouped.items()):
        per_task[task_id] = {
            "family": rows[0]["family"],
            "role": rows[0]["role"],
            "rollouts": len(rows),
            "success": sum(row["success"] for row in rows),
            "official_compliance": sum(row["official_compliance"] for row in rows),
            "focal_C_correct": sum(row["focal_C_correct"] for row in rows),
        }
    family_gates = {}
    for family in ("P1", "P3", "P4", "P5_P6"):
        rows = [row for row in records if row["family"] == family]
        repair = [row for row in rows if row["role"] == "REPAIR"]
        support = [row for row in rows if row["role"] == "SUPPORT"]
        family_gates[family] = {
            "repair_focal_correct": sum(row["focal_C_correct"] for row in repair),
            "repair_rollouts": len(repair),
            "repair_gate": "PASS" if repair and all(row["focal_C_correct"] for row in repair) else "FAIL",
            "support_focal_correct": sum(row["focal_C_correct"] for row in support),
            "support_rollouts": len(support),
            "support_gate": (
                "NOT_TESTED_NO_CLEAN_ANCHOR_SUPPORT"
                if not support
                else "PASS"
                if all(row["focal_C_correct"] for row in support)
                else "FAIL"
            ),
        }
    quadrants = Counter(row["quadrant"] for row in records)
    assert all(row["focal_C_correct"] for row in records)
    assert family_gates == {
        "P1": {"repair_focal_correct": 3, "repair_rollouts": 3, "repair_gate": "PASS", "support_focal_correct": 0, "support_rollouts": 0, "support_gate": "NOT_TESTED_NO_CLEAN_ANCHOR_SUPPORT"},
        "P3": {"repair_focal_correct": 3, "repair_rollouts": 3, "repair_gate": "PASS", "support_focal_correct": 3, "support_rollouts": 3, "support_gate": "PASS"},
        "P4": {"repair_focal_correct": 3, "repair_rollouts": 3, "repair_gate": "PASS", "support_focal_correct": 3, "support_rollouts": 3, "support_gate": "PASS"},
        "P5_P6": {"repair_focal_correct": 3, "repair_rollouts": 3, "repair_gate": "PASS", "support_focal_correct": 3, "support_rollouts": 3, "support_gate": "PASS"},
    }
    output = {
        "schema_version": "phase_v1_capability_anchor_reference_analysis_v1",
        "design": "21 matched-seed rollouts across four minimal Capability skills",
        "runtime_integrity": load((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/runtime/recovery_summary.json')),
        "reference": {
            "rollouts": 21,
            "success": sum(row["success"] for row in records),
            "official_compliance": sum(row["official_compliance"] for row in records),
            "quadrants": {label: quadrants[label] for label in ("CS", "CF", "VS", "VF")},
            "focal_C_correct": sum(row["focal_C_correct"] for row in records),
        },
        "family_gates": family_gates,
        "official_caveats": {
            "count": sum(row["nonfocal_official_caveat"] for row in records),
            "interpretation": "All four VS are nonfocal retail confirmation/completeness-reminder findings; the P3 resource-refresh sequence is correct in every repair and support run.",
        },
        "measurement_caveat": "Merged v2 tasks travel_request_003/015 lack native evaluation criteria; focal P4 correctness is therefore verified directly from exact booking/update tool payloads.",
        "final_classification_counts_for_19": {"KEEP_CONTROL": 6, "REBUILD": 12, "REJECT": 1},
        "per_task": per_task,
        "records": records,
    }
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/phase_v1_capability_anchor_reference_results.json')).write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report = """# Phase v1 Capability Anchor audit closeout

**Final result: `REBUILD=12`, `KEEP_CONTROL=6`, `REJECT=1`; no frozen task is promoted directly to Core.**

The audit recovered 57 historical E0 rollouts (`CS=32`, `CF=5`, `VS=4`, `VF=16`) and found 21 focal Capability errors. All 19 tasks fail the final surface/unified-environment admission Gate because mechanism and outcome remain tied to fixed entities, amounts, identifiers, wording, or order.

The minimal Reference Skill experiment ran 21 matched-seed behavioral trajectories. Four post-behavioral errors were recovered from saved evaluated trajectories with Judge-only calls; behavioral reruns remained zero and frozen files were unchanged.

| Family | Repair | Support safety | Interpretation |
|---|---:|---:|---|
| P1 | 3/3 focal correct | Not tested | Strong pending-order sequencing repair; no clean Anchor support surface exists. |
| P3 | 3/3 focal correct | 3/3 focal correct | Resource refresh repairs the failure state and preserves the legal state. |
| P4 | 3/3 focal correct | 3/3 focal correct | One-shot allocation repairs the failure state and preserves mixed-operation applicability. |
| P5/P6 | 3/3 focal correct | 3/3 focal correct | Incremental planning repairs the budget branch and preserves multistage propagation. |

Overall focal correctness is 21/21. Official results are 17 CS and 4 VS; the four VS are nonfocal retail confirmation/completeness-reminder findings. The P3 refresh dependency is correct in all six runs.

The seven stable/recurrent tasks and five weak tasks remain reconstruction seeds. Six stable-CS tasks are controls. `retail_request_003` is rejected because focal P3 is already correct 3/3 and its two VS labels are unrelated Governance findings; stronger P3 support states exist.
"""
    ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/PHASE_V1_CAPABILITY_ANCHOR_CLOSEOUT_REPORT.md')).write_text(report, encoding="utf-8")
    print("PASS_PHASE_V1_CAPABILITY_ANCHOR_REFERENCE_ANALYSIS")


if __name__ == "__main__":
    main()
