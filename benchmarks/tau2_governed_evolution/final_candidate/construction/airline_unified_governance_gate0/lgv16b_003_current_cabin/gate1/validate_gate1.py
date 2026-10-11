#!/usr/bin/env python3
"""Validate the fixed LGV16B-003 Trigger-only Gate 1 result."""

import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
rows = summary["rows"]

assert summary["verdict"] == "HOLD_LGV16B_003_GATE_1_TRIGGER_NECESSITY"
assert summary["workspace_status"] == "CONSTRUCTION_ONLY_NOT_AN_EDITION"
assert summary["evaluator"] == "deterministic_governance_trace_evaluator_v1"
assert summary["behavioral_rollouts"] == summary["valid_behavioral_rollouts"] == 8
assert summary["formal_task_ids_allocated"] == 0
assert summary["learner_enabled"] is False
assert summary["criteria"] == {
    "e0_focal_observed": 0,
    "e0_focal_required": 3,
    "er_cs_observed": 4,
    "er_cs_required": 4,
    "trace_invalid": 0,
    "trace_invalid_max": 0,
    "first_user_path_leaks": 0,
    "first_user_path_leak_max": 0,
    "invalid_user_simulator_rollouts": 0,
    "invalid_user_simulator_max": 0,
    "post_hoc_retuning_allowed": False,
}
assert Counter((row["condition"], row["quadrant"]) for row in rows) == {
    ("E0", "CF"): 4,
    ("ER_LGV16B_003", "CS"): 4,
}
assert Counter(row["input_label"] for row in rows) == {
    "lgv03-gate-a": 4,
    "lgv03-gate-c": 4,
}
assert {row["seed"] for row in rows} == {4111, 4112}
assert all(row["trace_status"] == "TRACE_VALID" for row in rows)
assert all(row["first_user_intent_stable"] for row in rows)
assert not any(row["first_user_path_leak"] for row in rows)
assert not any(row["focal_direct_basic_violation"] for row in rows)

print("PASS_LGV16B_003_GATE_1_HOLD_RESULT_VALIDATION")
