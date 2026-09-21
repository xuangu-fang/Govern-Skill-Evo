#!/usr/bin/env python3
"""Validate the frozen v18 joint-family Admission Contract v2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments/configs/v18_joint_family_admission_002"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((CONFIG / "admission_contract.json").read_text(encoding="utf-8"))
    manifest = json.loads((CONFIG / "manifest.json").read_text(encoding="utf-8"))
    assert contract["contract_id"] == "v18-joint-family-admission-2"
    assert manifest["status"] == "FROZEN_BEFORE_REPLICATION"
    assert manifest["admission_contract_sha256"] == sha(CONFIG / "admission_contract.json")
    assert contract["replication_design"]["total_rollouts"] == 96
    thresholds = contract["thresholds_per_split"]
    assert "e_cap_compliance_changes_absolute_max" not in str(thresholds)
    assert "e_gov_success_changes_absolute_max" not in str(thresholds)
    assert thresholds["component_primary_repair_and_residual_headroom"]["e_cap_governance_violations_remaining_min"] >= 3
    assert thresholds["component_primary_repair_and_residual_headroom"]["e_gov_capability_failures_remaining_min"] >= 3
    print(json.dumps({
        "status": "VALID",
        "contract_id": contract["contract_id"],
        "admission_contract_sha256": manifest["admission_contract_sha256"],
        "model_calls": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
