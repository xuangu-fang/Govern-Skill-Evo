#!/usr/bin/env python3
"""Validate the complete Phase-v1 Capability Anchor audit."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit'))
MAIN = (Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/v2_72_task_audit.json')


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    static = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/phase_v1_capability_anchor_static_audit.json'))
    reference = load((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/phase_v1_capability_anchor_reference_results.json'))
    recovery = load((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/runtime/recovery_summary.json'))
    audit = load(MAIN)
    assert static["task_count"] == 19
    assert static["historical_e0_rollouts"] == 57
    assert static["historical_e0_quadrants"] == {"CS": 32, "CF": 5, "VS": 4, "VF": 16}
    assert static["focal_C_errors"] == 21
    assert static["classification_before_reference"] == {"REBUILD": 12, "KEEP_CONTROL": 6, "REJECT": 1}
    assert reference["reference"] == {
        "rollouts": 21,
        "success": 21,
        "official_compliance": 17,
        "quadrants": {"CS": 17, "CF": 0, "VS": 4, "VF": 0},
        "focal_C_correct": 21,
    }
    assert all(row["repair_gate"] == "PASS" for row in reference["family_gates"].values())
    assert reference["family_gates"]["P1"]["support_gate"] == "NOT_TESTED_NO_CLEAN_ANCHOR_SUPPORT"
    assert all(reference["family_gates"][family]["support_gate"] == "PASS" for family in ("P3", "P4", "P5_P6"))
    assert recovery["final_completed"] == 21 and recovery["final_errors"] == 0
    assert recovery["behavioral_trajectory_reruns"] == 0 and recovery["protected_files_unchanged"]
    paths = [path for path in ((Path(__file__).resolve().parents[5] / 'artifacts/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/phase_v1_capability_anchor_audit/trajectories')).glob("*.json") if re.search(r"_\d{2}\.json$", path.name)]
    assert len(paths) == 21
    assert audit["schema_version"] == "v2_72_task_screening_1.6"
    assert audit["classification_counts"] == {"KEEP_CONTROL": 23, "REBUILD": 40, "REJECT": 9}
    capability = [row for row in audit["records"] if row["original_role"] == "CAPABILITY_ANCHOR"]
    assert len(capability) == 19
    assert Counter(row["classification"] for row in capability) == {"REBUILD": 12, "KEEP_CONTROL": 6, "REJECT": 1}
    assert next(row for row in capability if row["task_id"] == "retail_request_003")["classification"] == "REJECT"
    print("PASS_PHASE_V1_CAPABILITY_ANCHOR_AUDIT_VALIDATION")


if __name__ == "__main__":
    main()
