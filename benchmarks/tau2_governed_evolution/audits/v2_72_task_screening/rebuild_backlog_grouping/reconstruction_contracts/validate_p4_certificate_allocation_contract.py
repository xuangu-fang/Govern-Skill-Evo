#!/usr/bin/env python3
"""Validate the minimal narrowed P4 reconstruction contract."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "p4_certificate_allocation_reconstruction_contract.json").read_text(encoding="utf-8"))

assert data["family_id"] == "C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION"
assert data["status"] == "PASS_MINIMAL_DESIGN_CONTRACT_ONLY"
assert data["environment"] == "airline-final-candidate-construction"
assert data["environment_extension"] == "FIXTURE_ONLY"
assert not data["new_domain"] and not data["new_tool"] and not data["new_oracle_sidecar"]
assert data["mechanism"]["operations"] == ["book_reservation", "book_reservation"]
assert data["trigger_inputs"] == 2
assert data["support_policy"] == "OMITTED__GLOBAL_PROTECTED_CONTROLS"
assert data["gate0"]["correct_paths_required_cs"] == data["gate0"]["competing_paths_required_cf"] == 2
assert data["gate0"]["v3_oracle_regression_required"] == 32
assert data["gate1"] == {
    "design": "TRIGGER_ONLY_MATCHED_E0_ER",
    "triggers": 2,
    "seeds": 2,
    "planned_rollouts": 8,
    "e0_focal_allocation_failure_min": 3,
    "er_cs_required": 4,
    "first_user_allocation_leak_allowed": 0,
    "post_hoc_retuning_allowed": False,
}
assert data["formal_task_ids_allocated"] == 0
print("PASS_P4_CERTIFICATE_ALLOCATION_MINIMAL_CONTRACT")
