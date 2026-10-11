#!/usr/bin/env python3
"""Validate the minimal P3 reconstruction contract."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "p3_resource_refresh_reconstruction_contract.json").read_text(encoding="utf-8"))
assert data["family_id"] == "C-RET-P3-RESOURCE-REFRESH"
assert data["formal_task_ids_allocated"] == 0
assert not any((data["new_domain"], data["new_tool"], data["new_oracle_sidecar"]))
assert data["refresh_is_backend_precondition"] is False
assert len(data["triggers"]) == 2
for row in data["triggers"]:
    assert row["initial_balance"] < row["downstream_need"]
    assert row["refreshed_balance"] >= row["downstream_need"]
    assert row["refreshed_balance"] - row["downstream_need"] == row["expected_final_balance"]
assert data["gate1"] == {"triggers": 2, "seeds": 2, "e0_focal_min": 3, "er_cs_required": 4}
print("PASS_P3_RESOURCE_REFRESH_RECONSTRUCTION_CONTRACT")
