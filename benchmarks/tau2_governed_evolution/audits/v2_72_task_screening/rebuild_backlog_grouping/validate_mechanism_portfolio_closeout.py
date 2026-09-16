#!/usr/bin/env python3
"""Validate terminal accounting for all 13 portfolio mechanism families."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
closeout = json.loads((HERE / "mechanism_portfolio_closeout.json").read_text(encoding="utf-8"))
registry = json.loads((HERE / "mechanism_family_registry.json").read_text(encoding="utf-8"))
audit = json.loads((HERE.parent / "v2_72_task_audit.json").read_text(encoding="utf-8"))

assert closeout["status"] == "MECHANISM_PORTFOLIO_CLOSED__READY_3_DEFERRED_7_DROPPED_3"
assert closeout["source_screening"] == {
    "v2_tasks": 72,
    "classifications": {"KEEP_CONTROL": 21, "REBUILD": 40, "REJECT": 11},
}
assert audit["task_count"] == 72
assert audit["classification_counts"] == closeout["source_screening"]["classifications"]
assert closeout["scope"] == {
    "rebuild_lineages": 40,
    "historical_source_family_rows": 14,
    "portfolio_families_after_consolidation": 13,
    "ready_for_final_realization": 3,
    "deferred": 7,
    "dropped": 3,
    "formal_task_ids_allocated": 0,
    "train_monitor_splits_allocated": 0,
    "new_rollouts_for_total_closeout": 0,
}

ready = set(closeout["ready_batch"])
deferred = set(closeout["deferred_batch"])
dropped = set(closeout["dropped_batch"])
assert len(ready) == 3 and len(deferred) == 7 and len(dropped) == 3
assert not (ready & deferred or ready & dropped or deferred & dropped)
assert len(ready | deferred | dropped) == 13

portfolio_ids = {
    row.get("portfolio_family_id", row["family_id"])
    for row in registry["families"]
}
assert portfolio_ids == ready | deferred | dropped

source_statuses: dict[str, set[str]] = {}
for row in registry["families"]:
    portfolio_id = row.get("portfolio_family_id", row["family_id"])
    source_statuses.setdefault(portfolio_id, set()).add(row["final_realization_status"])
for family_id in ready:
    assert source_statuses[family_id] == {"READY_FOR_FINAL_REALIZATION"}
for family_id in deferred:
    assert all(status.startswith("DEFERRED__") for status in source_statuses[family_id])
for family_id in dropped:
    assert all(status.startswith("DROPPED") for status in source_statuses[family_id])

inventory = closeout["ready_pre_id_inventory"]
assert inventory["total_candidates"] == 24
assert sum(
    row["candidates"]
    for family_id, row in inventory.items()
    if family_id != "total_candidates" and family_id != "interpretation"
) == 24
assert closeout["priority_closeouts"] == {
    "P0": "PASS_P0_PORTFOLIO_CLOSEOUT",
    "P1": "P1_GOVERNANCE_PORTFOLIO_CLOSED",
    "P2": "P2_STANDALONE_FAMILY_CLOSED__SUBSUMED_BY_V3_EE01",
    "P3": "P3_LIGHTWEIGHT_CLOSEOUT_COMPLETE",
}
assert [row["order"] for row in closeout["next_program"]] == [1, 2, 3, 4, 5]
print("PASS_MECHANISM_PORTFOLIO_CLOSEOUT_VALIDATION")
