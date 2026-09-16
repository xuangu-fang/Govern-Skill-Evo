#!/usr/bin/env python3
"""Validate the P2 standalone-family closeout."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
closeout = json.loads((HERE / "p2_portfolio_closeout.json").read_text(encoding="utf-8"))
registry = json.loads((HERE / "mechanism_family_registry.json").read_text(encoding="utf-8"))
recovery = json.loads((HERE / "p2_preserved_pricing_recovery.json").read_text(encoding="utf-8"))

assert closeout["status"] == "P2_STANDALONE_FAMILY_CLOSED__SUBSUMED_BY_V3_EE01"
assert closeout["decision"] == "DROPPED_AS_STANDALONE__SUBSUMED_BY_V3_EE01"
assert closeout["lineage_count"] == 2
assert closeout["construction_decision"] == {
    "minimal_pair_structurally_feasible": True,
    "minimal_contract_written": False,
    "gate0_run": False,
    "gate1_run": False,
    "cancellation_reason": "LOW_MARGINAL_INFORMATION__DUPLICATES_AN_ADMITTED_V3_CAPABILITY_FAMILY",
}
assert closeout["scope"] == {
    "new_model_rollouts": 0,
    "new_environment_fixtures": 0,
    "formal_task_ids_allocated": 0,
    "train_monitor_splits_allocated": 0,
}
assert closeout["retained_assets"]["separate_core_metric"] is False
assert set(closeout["retained_assets"]["lineages"]) == {
    "airline_pa_o3a_m66qvw_preserved_pricing",
    "airline_pa_b2_1n99u6_lexicographic_return",
}

p2 = next(row for row in registry["families"] if row["priority"] == "P2")
assert p2["family_id"] == closeout["family_id"] == recovery["family_id"]
assert p2["final_realization_status"] == closeout["decision"]
assert recovery["decision"]["family_status"] == closeout["decision"]
assert p2["next_gate"] == closeout["next_gate"] == "DROPPED__NO_ACTIVE_GATE"
assert p2["formal_task_ids_allocated"] == 0
print("PASS_P2_PORTFOLIO_CLOSEOUT_VALIDATION")
