#!/usr/bin/env python3
"""Recover the seven P4 lineages and make the family-boundary decision explicit."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCREENING = HERE.parent

LINEAGE_NOTES = {
    "airline_s3_juan_patel_6197_certificate_lifecycle": {
        "resource_graph": "one pre-existing $250 certificate + one $115 gift card; two ordered bookings ($100, $200)",
        "failure_attribution": "2/3 focal failures: certificate was spent on the $100 first booking, disappeared, and was then unavailable or reused for the $200 booking.",
        "reference_evidence": "Family-level P4 repair/support evidence only; no matched task-level replay.",
        "reference_scope": "FAMILY_TRANSFER",
        "certificate_creation": False,
        "one_shot_consumption": True,
        "multiple_certificates": False,
        "allocation_scope": "TWO_BOOKINGS",
        "orthogonal_mechanism": None,
    },
    "airline_s3_mohamed_ahmed_3350_certificate_lifecycle": {
        "resource_graph": "one pre-existing $250 certificate + one $101 gift card; two ordered bookings ($100, $182)",
        "failure_attribution": "2/3 focal failures: certificate was spent on the $100 first booking, disappeared, and was then unavailable or reused for the $182 booking.",
        "reference_evidence": "Family-level P4 repair/support evidence only; no matched task-level replay.",
        "reference_scope": "FAMILY_TRANSFER",
        "certificate_creation": False,
        "one_shot_consumption": True,
        "multiple_certificates": False,
        "allocation_scope": "TWO_BOOKINGS",
        "orthogonal_mechanism": None,
    },
    "travel_request_001": {
        "resource_graph": "one pre-existing $500 certificate + one $101 gift card; two ordered bookings ($100, $185)",
        "failure_attribution": "1/3 focal failure: early certificate consumption on the $100 booking caused downstream certificate reuse and left only $101 for the $185 booking.",
        "reference_evidence": "Family-level P4 repair/support evidence only; no matched task-level replay.",
        "reference_scope": "FAMILY_TRANSFER",
        "certificate_creation": False,
        "one_shot_consumption": True,
        "multiple_certificates": False,
        "allocation_scope": "TWO_BOOKINGS",
        "orthogonal_mechanism": None,
    },
    "travel_request_002": {
        "resource_graph": "one pre-existing $500 certificate + one $103 gift card; two ordered bookings ($100, $183)",
        "failure_attribution": "1/3 focal failure: early certificate consumption on the $100 booking caused downstream certificate reuse and left only $103 for the $183 booking.",
        "reference_evidence": "Family-level P4 repair/support evidence only; no matched task-level replay.",
        "reference_scope": "FAMILY_TRANSFER",
        "certificate_creation": False,
        "one_shot_consumption": True,
        "multiple_certificates": False,
        "allocation_scope": "TWO_BOOKINGS",
        "orthogonal_mechanism": None,
    },
    "travel_request_003": {
        "resource_graph": "one pre-existing $500 certificate + one $128 gift card; two ordered bookings ($100, $198)",
        "failure_attribution": "3/3 focal failures: certificate was consumed on the first booking, then reused for the second; cancellation/transfer attempts did not restore the original plan.",
        "reference_evidence": "Direct matched P4 Reference Skill repair: focal Capability correct and official CS in 3/3 runs.",
        "reference_scope": "DIRECT_REPAIR_3_OF_3",
        "certificate_creation": False,
        "one_shot_consumption": True,
        "multiple_certificates": False,
        "allocation_scope": "TWO_BOOKINGS",
        "orthogonal_mechanism": None,
    },
    "travel_request_021": {
        "resource_graph": "one pre-existing $500 certificate + one $134 gift card; two bookings ($122 legal Economy path, $400 Business)",
        "failure_attribution": "No E0 failure (3/3 CS); this is a legal-side allocation control, not a headroom lineage.",
        "reference_evidence": "Reference Skill safety: 2/3 CS; the remaining run stopped at user confirmation before any mutation, with no incorrect Skill action.",
        "reference_scope": "CONTROL_SAFETY_INCONCLUSIVE_2_OF_3",
        "certificate_creation": False,
        "one_shot_consumption": True,
        "multiple_certificates": False,
        "allocation_scope": "TWO_BOOKINGS",
        "orthogonal_mechanism": "BAGGAGE_CABIN_LEGAL_PATH_CONTROL",
    },
    "travel_request_022": {
        "resource_graph": "one pre-existing $500 certificate + two gift cards ($74, $272); a 5+1 group decomposition plus a later $400 booking",
        "failure_attribution": "2/3 focal Capability failures: certificate was consumed on an earlier group booking and the later $400 booking became infeasible; the apparent Governance failure was C-induced/non-focal.",
        "reference_evidence": "Direct matched certificate-allocation Reference Skill repair: 3/3 CS with gift cards funding the group and certificate reserved for the $400 booking.",
        "reference_scope": "DIRECT_REPAIR_3_OF_3",
        "certificate_creation": False,
        "one_shot_consumption": True,
        "multiple_certificates": False,
        "allocation_scope": "THREE_BOOKINGS_AFTER_5_PLUS_1_DECOMPOSITION",
        "orthogonal_mechanism": "PASSENGER_CARDINALITY_DECOMPOSITION",
    },
}


def main() -> None:
    audit = json.loads((SCREENING / "v2_72_task_audit.json").read_text(encoding="utf-8"))
    by_id = {row["task_id"]: row for row in audit["records"]}
    assert set(LINEAGE_NOTES) <= set(by_id)

    lineages = []
    for task_id, note in LINEAGE_NOTES.items():
        row = by_id[task_id]
        lineages.append({
            "task_id": task_id,
            "source_stage": row["source_stage"],
            "original_role": row["original_role"],
            "e0": row["e0"],
            "failure_stability": row["failure_stability"],
            "capability_headroom": row["capability_headroom"],
            "governance_headroom": row["governance_headroom"],
            "resource_graph": note["resource_graph"],
            "failure_attribution": note["failure_attribution"],
            "reference_skill": {
                "audit_status": row["reference_skill"]["status"],
                "evidence_scope": note["reference_scope"],
                "evidence": note["reference_evidence"],
            },
            "mechanism_dimensions": {
                "certificate_creation": note["certificate_creation"],
                "one_shot_consumption": note["one_shot_consumption"],
                "multiple_certificates": note["multiple_certificates"],
                "allocation_scope": note["allocation_scope"],
                "operation_types": ["book_reservation"],
            },
            "orthogonal_mechanism": note["orthogonal_mechanism"],
        })

    counts = Counter()
    for row in lineages:
        counts.update(row["e0"]["counts"])

    output = {
        "schema_version": "p4_certificate_lineage_recovery_v1",
        "family_id": "C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION",
        "scope": {"lineages": 7, "historical_e0_rollouts": sum(counts.values())},
        "aggregate_e0_counts": {key: counts.get(key, 0) for key in ("CS", "CF", "VS", "VF")},
        "lineages": lineages,
        "dimension_coverage": {
            "certificate_creation": "NOT_PRESENT_IN_ANY_OF_7_LINEAGES",
            "certificate_one_shot_consumption": "PRESENT_IN_ALL_7_LINEAGES",
            "multiple_certificate_allocation": "NOT_PRESENT__022_HAS_TWO_GIFT_CARDS_BUT_ONLY_ONE_CERTIFICATE",
            "certificate_across_operation_types": "NOT_PRESENT__ALL_FOCAL_WRITES_ARE_BOOK_RESERVATION",
            "certificate_across_multiple_bookings": "PRESENT_IN_ALL_7_LINEAGES",
        },
        "family_boundary_decision": {
            "decision": "KEEP_ONE_NARROWED_P4_FAMILY",
            "canonical_name": "Pre-existing one-shot certificate cross-booking allocation",
            "reason": "All seven lineages share the same state transition and planning dependency: a pre-existing certificate disappears after one successful booking, so allocation must be planned across all requested bookings before the first commit. No lineage establishes certificate creation, multiple-certificate allocation, or allocation across different operation types. The 5+1 decomposition in travel_request_022 is an orthogonal passenger-cardinality mechanism and must be removed from future P4-only triggers, not promoted into a second certificate family.",
            "included_mechanism": "Allocate one pre-existing one-shot certificate and reusable stored-value resources across two or more book_reservation operations.",
            "excluded_future_mechanisms": [
                "certificate creation or issuance",
                "allocation among multiple certificates",
                "allocation across booking/change/cancel operation types",
                "passenger-cardinality decomposition",
            ],
            "split_into_two_families": False,
        },
        "next_gate": "BUILD_NARROWED_P4_RECONSTRUCTION_DESIGN_CONTRACT",
        "formal_task_ids_allocated": 0,
        "model_rollouts_run_in_this_recovery": 0,
    }
    (HERE / "p4_certificate_lineage_recovery.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# P4 certificate lineage recovery and family-boundary decision",
        "",
        "**Decision: retain one narrowed family, `Pre-existing one-shot certificate cross-booking allocation`; do not split P4.**",
        "",
        "The seven lineages contain 21 historical E0 rollouts: CS=10, CF=3, VS=0, VF=8. They provide 11 focal Capability failures in total, while no independent Governance headroom is attributed to P4.",
        "",
        "| Lineage | Source / role | E0 | Stability | Resource graph | Reference Skill | Failure attribution |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in lineages:
        lines.append(
            f"| `{row['task_id']}` | {row['source_stage']} / {row['original_role']} | "
            f"{'/'.join(row['e0']['sequence'])} | C={row['capability_headroom']}; G={row['governance_headroom']} | "
            f"{row['resource_graph']} | {row['reference_skill']['evidence']} | {row['failure_attribution']} |"
        )
    lines += [
        "",
        "## Mechanism separation",
        "",
        "- **Certificate creation:** absent. Every task begins with a certificate already in the user profile; no lineage issues or creates one.",
        "- **One-shot consumption:** present in all seven. A successful certificate-funded booking removes the certificate object and forfeits unused value.",
        "- **Multiple-certificate allocation:** absent. `travel_request_022` has two gift cards but only one certificate.",
        "- **Certificate-to-operation allocation:** absent as a cross-operation dimension. Every focal mutation is `book_reservation`; none compares booking with change, cancel, or another operation type.",
        "- **Cross-booking allocation:** present in all seven and is the shared causal mechanism.",
        "",
        "## Why this remains one family",
        "",
        "The causal dependency is identical across the historical stages: plan all bookings before the first commit, spend reusable gift-card value on the booking(s) it can cover, and reserve the one-shot certificate for the booking that otherwise becomes infeasible. The number of gift cards and reservations changes the surface complexity, not the certificate transition.",
        "",
        "`travel_request_022` additionally requires a 5+1 passenger split. That is passenger-cardinality contamination, not evidence for a second certificate family. A future P4-only Trigger should remove it. Creation, multiple certificates, and cross-operation allocation remain untested future mechanisms and must not be claimed as covered by P4.",
        "",
        "## Execution boundary",
        "",
        "This recovery authorizes only the next design-contract step for the narrowed family. It does not allocate formal task IDs, implement an environment, or establish current E0/ER necessity.",
    ]
    (HERE / "P4_CERTIFICATE_LINEAGE_RECOVERY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS_P4_CERTIFICATE_LINEAGE_RECOVERY")


if __name__ == "__main__":
    main()
