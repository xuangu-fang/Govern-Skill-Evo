#!/usr/bin/env python3
"""Validate the lightweight P3 closeout against the family registry."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
closeout = json.loads((HERE / "p3_portfolio_closeout.json").read_text(encoding="utf-8"))
registry = json.loads((HERE / "mechanism_family_registry.json").read_text(encoding="utf-8"))

assert closeout["status"] == "P3_LIGHTWEIGHT_CLOSEOUT_COMPLETE"
assert closeout["scope"] == {
    "portfolio_families": 2,
    "rebuild_lineages": 3,
    "ready_for_final_realization": 0,
    "deferred": 0,
    "dropped": 2,
    "new_model_rollouts": 0,
    "new_environment_fixtures": 0,
    "formal_task_ids_allocated": 0,
    "train_monitor_splits_allocated": 0,
}

p3 = {row["family_id"]: row for row in registry["families"] if row["priority"] == "P3"}
rows = {row["family_id"]: row for row in closeout["families"]}
assert set(p3) == set(rows) == {
    "C-RET-GENERIC-EXCHANGE-CONTROL",
    "J-AIR-CERTIFICATE-X-GOVERNANCE-SEEDS",
}
assert sum(len(row["lineages"]) for row in rows.values()) == 3
for family_id, row in rows.items():
    assert p3[family_id]["lineage_count"] == len(row["lineages"])
    assert p3[family_id]["final_realization_status"] == row["decision"]
    assert p3[family_id]["formal_task_ids_allocated"] == 0
    assert p3[family_id]["next_gate"] == row["next_gate"] == "DROPPED__NO_ACTIVE_GATE"

joint = rows["J-AIR-CERTIFICATE-X-GOVERNANCE-SEEDS"]
assert joint["future_dependencies"] == [
    "C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION",
    "G-AIR-LGV16B-001-PASSENGER-CARDINALITY",
    "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE",
]
assert closeout["next_action"] == "CLOSE_FULL_MECHANISM_PORTFOLIO"
print("PASS_P3_LIGHTWEIGHT_CLOSEOUT_VALIDATION")
