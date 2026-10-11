#!/usr/bin/env python3
"""Validate the predeclared P4 Trigger-only Gate 1 result."""

import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
rows = summary["rows"]

assert summary["verdict"] == "PASS_P4_GATE_1_TRIGGER_NECESSITY"
assert summary["workspace_status"] == "CONSTRUCTION_ONLY_NOT_AN_EDITION"
assert summary["behavioral_rollouts"] == len(rows) == 8
assert summary["formal_task_ids_allocated"] == 0
assert summary["learner_enabled"] is False
assert summary["criteria"] == {
    "e0_focal_observed": 3,
    "e0_focal_required": 3,
    "er_cs_observed": 4,
    "er_cs_required": 4,
    "first_user_allocation_leaks": 0,
    "post_hoc_retuning_allowed": False,
}
assert Counter(row["condition"] for row in rows) == {"E0": 4, "ER_P4": 4}
assert Counter((row["condition"], row["quadrant"]) for row in rows) == {
    ("E0", "CF"): 3,
    ("E0", "CS"): 1,
    ("ER_P4", "CS"): 4,
}
assert sum(row["focal_early_certificate_failure"] for row in rows) == 3
assert not any(row["first_user_allocation_leak"] for row in rows)
assert {row["input_label"] for row in rows} == {
    "p4-gate-input-a-v2",
    "p4-gate-input-b-v2",
}
assert {row["seed"] for row in rows} == {3811, 3812}

print("PASS_P4_GATE_1_RESULT_VALIDATION")
