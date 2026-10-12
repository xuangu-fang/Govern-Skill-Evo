#!/usr/bin/env python3
"""Validate the current Governance Core portfolio closeout."""

import json
from pathlib import Path


HERE = (Path(__file__).resolve().parents[4] / 'benchmarks/tau2_governed_evolution/final_candidate')
closeout = json.loads((HERE / "governance_core_portfolio_closeout.json").read_text())
competition = json.loads(
    (HERE / closeout["open_competition"]["result_path"]).read_text()
)

assert closeout["status"] == "GOVERNANCE_CORE_PORTFOLIO_CLOSED__READY_3"
assert closeout["accepted_family_count"] == 3
assert len(set(closeout["accepted_families"])) == 3
assert closeout["decision"] == "ACCEPT_THREE_GOVERNANCE_FAMILIES__DO_NOT_FORCE_A_FOURTH"
assert closeout["formal_task_ids_allocated"] == 0
assert closeout["train_monitor_splits_allocated"] == 0
assert competition["behavioral_rollouts"] == 8
assert competition["winners"] == []
assert all(
    row["decision"] == "REJECT_HYPOTHESIS"
    for row in competition["outcomes"].values()
)
print("PASS_GOVERNANCE_CORE_PORTFOLIO_CLOSEOUT")

