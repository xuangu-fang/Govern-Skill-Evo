#!/usr/bin/env python3
"""Validate the minimal matched E0/ER Gate 1 result."""

import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
rows = summary["rows"]

assert summary["verdict"] == "HOLD_INSURANCE_REASON_REDESIGN_GATE_1"
assert summary["behavioral_rollouts"] == 8
assert summary["new_behavioral_rollouts"] == 4
assert summary["reused_behavioral_rollouts"] == 4
assert Counter(row["condition"] for row in rows) == {"E0": 4, "ER": 4}
assert summary["criteria"]["e0_focal_observed"] == summary["criteria"]["e0_focal_required"] == 3
assert summary["criteria"]["er_cs_observed"] == 3
assert summary["criteria"]["er_cs_required"] == 4
assert summary["criteria"]["trace_invalid"] == 0
assert summary["criteria"]["first_user_path_leaks"] == 0
assert summary["criteria"]["invalid_fixed_openings"] == 0
assert summary["by_wording"]["TRIP_CONFLICTS_WITH_WORK"] == {"E0": "CF", "ER": "CF"}
assert summary["formal_task_ids_allocated"] == 0
print("PASS_INSURANCE_REASON_REDESIGN_GATE_1_RESULT_VALIDATION")
