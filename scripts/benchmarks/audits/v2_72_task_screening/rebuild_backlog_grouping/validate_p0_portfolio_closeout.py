#!/usr/bin/env python3
"""Validate the P0 portfolio decision against the mechanism registry."""

import json
from collections import Counter
from pathlib import Path


HERE = (Path(__file__).resolve().parents[5] / 'benchmarks/tau2_governed_evolution/audits/v2_72_task_screening/rebuild_backlog_grouping')
closeout = json.loads(((Path(__file__).resolve().parents[5] / 'experiments/benchmarks/tau2/cross-edition/audits/v2_72_task_screening/rebuild_backlog_grouping/p0_portfolio_closeout.json')).read_text(encoding="utf-8"))
registry = json.loads((HERE / "mechanism_family_registry.json").read_text(encoding="utf-8"))

assert closeout["status"] == "PASS_P0_PORTFOLIO_CLOSEOUT"
assert closeout["scope"] == {
    "families": 6,
    "governance_families": 2,
    "capability_families": 4,
    "ready_for_final_realization": 3,
    "deferred": 3,
    "formal_task_ids_allocated": 0,
    "train_monitor_splits_allocated": 0,
    "new_rollouts_run_for_closeout": 0,
}

p0 = {row["family_id"]: row for row in registry["families"] if row["priority"] == "P0"}
rows = {row["family_id"]: row for row in closeout["families"]}
assert len(p0) == len(rows) == 6
assert set(p0) == set(rows)
assert Counter(row["axis"] for row in rows.values()) == {"CAPABILITY": 4, "GOVERNANCE": 2}
assert set(closeout["ready_batch"]) == {
    "G-AIR-LGV16B-002-MEMBERSHIP-BAGGAGE",
    "G-AIR-LGV16B-001-PASSENGER-CARDINALITY",
    "C-AIR-P4-CERTIFICATE-LIFECYCLE-ALLOCATION",
}
assert set(closeout["deferred_batch"]) == {
    "C-RET-P1-PENDING-MUTATION-SEQUENCE",
    "C-RET-P3-RESOURCE-REFRESH",
    "C-AIR-P5-INCREMENTAL-SETTLEMENT-FEASIBILITY",
}
for family_id, row in rows.items():
    registry_row = p0[family_id]
    assert row["axis"] == registry_row["axis"]
    assert row["decision"] == registry_row["final_realization_status"]
    assert registry_row["formal_task_ids_allocated"] == 0
    for key in ("gate0_path", "gate1_path"):
        assert (HERE / registry_row[key]).resolve().is_file()
    for key in ("shortcut_audit_path", "sanity_check_path"):
        if key in registry_row:
            assert (HERE / registry_row[key]).resolve().is_file()

assert closeout["next_portfolio_queue"] == "G-AIR-LGV16B-003-BASIC-CURRENT-CABIN"
print("PASS_P0_PORTFOLIO_CLOSEOUT_VALIDATION")
