#!/usr/bin/env python3
"""Validate the P1 closeout and its source-row/portfolio accounting."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
closeout = json.loads(
    (HERE / "p1_governance_portfolio_closeout.json").read_text(encoding="utf-8")
)
registry = json.loads(
    (HERE / "mechanism_family_registry.json").read_text(encoding="utf-8")
)

assert closeout["status"] == "P1_GOVERNANCE_PORTFOLIO_CLOSED"
assert closeout["scope"] == {
    "historical_source_family_rows": 5,
    "portfolio_families_after_consolidation": 4,
    "rebuild_lineages": 16,
    "ready_for_final_realization": 0,
    "deferred": 4,
    "formal_task_ids_allocated": 0,
    "train_monitor_splits_allocated": 0,
    "new_rollouts_run_for_closeout": 0,
}

p1_rows = {row["family_id"]: row for row in registry["families"] if row["priority"] == "P1"}
assert len(p1_rows) == 5
assert sum(row["lineage_count"] for row in p1_rows.values()) == 16
assert closeout["ready_batch"] == []
assert len(closeout["deferred_batch"]) == 4
assert sum(row["lineage_count"] for row in closeout["families"]) == 16

for family in closeout["families"]:
    source_rows = [p1_rows[source_id] for source_id in family["source_family_ids"]]
    assert sum(row["lineage_count"] for row in source_rows) == family["lineage_count"]
    assert {row["final_realization_status"] for row in source_rows} == {family["decision"]}
    assert {row["next_gate"] for row in source_rows} == {"DEFERRED__NO_ACTIVE_GATE"}
    assert all(row["formal_task_ids_allocated"] == 0 for row in source_rows)

endpoint = next(
    row for row in closeout["families"]
    if row["portfolio_family_id"] == "G-AIR-ENDPOINT-PRESERVATION"
)
assert len(endpoint["source_family_ids"]) == 2
assert endpoint["lineage_count"] == 5
assert closeout["default_evaluator_effect"] == (
    "NO_DEFERRED_P1_RULE_IS_ACTIVE_IN_THE_DEFAULT_V1_REGISTRY"
)
assert closeout["next_portfolio_queue"] == "C-AIR-P2-PRESERVED-SEGMENT-VALUATION"
print("PASS_P1_GOVERNANCE_PORTFOLIO_CLOSEOUT_VALIDATION")
