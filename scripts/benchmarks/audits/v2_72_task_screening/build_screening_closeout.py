#!/usr/bin/env python3
"""Freeze a machine-verifiable closeout view of the completed v2 screening."""

import json
from collections import Counter, defaultdict
from pathlib import Path


HERE = (Path(__file__).resolve().parents[4] / 'benchmarks/tau2_governed_evolution/audits/v2_72_task_screening')
AUDIT = (Path(__file__).resolve().parents[4] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/v2_72_task_audit.json')


def main() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    records = audit["records"]
    assert audit["schema_version"] == "v2_72_task_screening_1.8"
    assert len(records) == len({row["task_id"] for row in records}) == 72
    classifications = Counter(row["classification"] for row in records)
    assert classifications == {"KEEP_CONTROL": 21, "REBUILD": 40, "REJECT": 11}
    assert not any(row["classification"].startswith("KEEP_") and row["classification"].endswith("_CORE") for row in records)

    by_classification = defaultdict(list)
    role_matrix = defaultdict(Counter)
    for row in records:
        by_classification[row["classification"]].append(row["task_id"])
        role_matrix[row["original_role"]][row["classification"]] += 1
    output = {
        "schema_version": "v2_72_screening_closeout_v1",
        "status": "CLOSED_72_OF_72",
        "source_audit_schema": audit["schema_version"],
        "task_count": 72,
        "classification_counts": dict(sorted(classifications.items())),
        "direct_core_admissions": 0,
        "interpretation": {
            "KEEP_CONTROL": "Retain lineage as a control candidate; port and surface-balance before final-edition admission.",
            "REBUILD": "Retain mechanism evidence, not the frozen task surface; consolidate into a family-level reconstruction backlog.",
            "REJECT": "Exclude from the final candidate edition while preserving historical lineage and evidence.",
        },
        "task_ids_by_classification": {key: sorted(value) for key, value in sorted(by_classification.items())},
        "role_disposition_matrix": {role: dict(sorted(counts.items())) for role, counts in sorted(role_matrix.items())},
        "next_phase": {
            "name": "SCREENING_CLOSEOUT_AND_REBUILD_BACKLOG_GROUPING",
            "inputs": {"rebuild_lineages": 40, "control_lineages": 21, "excluded_lineages": 11},
            "required_outputs": [
                "lineage-deduplicated mechanism-family registry",
                "family-level rebuild/port/control backlog with priority and dependency",
                "unified Airline/Retail environment extension contract",
                "legal-success/evaluator repair requirements",
                "surface counterfactual balancing matrix",
                "minimal supplemental experiment plan",
                "final-edition admission gates and explicit exclusion ledger",
            ],
            "joint_task_policy": "Construct new Joint families only after their Capability and Governance source families independently pass unified-environment admission and Reference Skill necessity.",
        },
    }
    ((Path(__file__).resolve().parents[4] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/v2_72_screening_closeout.json')).write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# Benchmark v2 72-task screening closeout",
        "",
        "**Status: `CLOSED_72_OF_72`. The frozen v2 edition is unchanged.**",
        "",
        "| Disposition | Count | Meaning |",
        "|---|---:|---|",
        "| `KEEP_CONTROL` | 21 | Retain control lineage; final admission still requires unified-environment port and surface balancing. |",
        "| `REBUILD` | 40 | Retain mechanism evidence, not the frozen surface; group and reconstruct at family level. |",
        "| `REJECT` | 11 | Exclude from the final candidate edition; preserve lineage and evidence. |",
        "",
        "No frozen v2 task is directly admitted as Capability, Governance, or Joint Core. Core construction will use the verified mechanisms and evidence recovered by the audit, not copy legacy tasks wholesale.",
        "",
        "The final Cross-Axis Probe, `airline_unified_uca01_gjlsxx_nyc_date_budget`, is rejected: its three E0 runs show 0/3 P5 Capability failures and 3/3 valid LGA04 violations, so it is not a separable Joint task.",
        "",
        "## Next phase boundary",
        "",
        "The next phase converts 40 rebuild lineages and 21 control lineages into a deduplicated, family-level backlog. It must not begin by rewriting 61 tasks one by one. New Joint families are deferred until their source Capability and Governance families independently pass unified-environment and Reference Skill gates.",
        "",
        "Required outputs are recorded in `v2_72_screening_closeout.json`.",
    ]
    ((Path(__file__).resolve().parents[4] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/V2_72_SCREENING_CLOSEOUT.md')).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS_V2_72_SCREENING_CLOSED")


if __name__ == "__main__":
    main()
