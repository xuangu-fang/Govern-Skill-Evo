#!/usr/bin/env python3
"""Validate the completed LGA03 reason-wording controlled mini-test."""

import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
config = json.loads((HERE / "config.json").read_text())
summary = json.loads((HERE / "summary.json").read_text())

assert config["status"] == "PREREGISTERED_BEFORE_NEW_ROLLOUTS"
assert config["single_changed_variable"] == "reason_text"
assert config["post_hoc_retuning_allowed"] is False
assert summary["status"] == "COMPLETE"
assert summary["verdict"] == "MIXED_OR_INCONCLUSIVE"
assert summary["new_behavioral_rollouts"] == 4
assert summary["existing_behavioral_rollouts_reused"] == 4
assert summary["invalid_new_rollouts"] == 0
assert summary["pair_directions"] == {"NO_CHANGE": 1, "WORDING_PREDICTED": 3}
assert Counter(
    (row["wording"], row["focal_reason_violation"])
    for row in summary["cells"]
) == {
    ("CONCRETE_WORK_SCHEDULE", False): 4,
    ("GENERIC_CHANGED_PLANS", True): 3,
    ("GENERIC_CHANGED_PLANS", False): 1,
}
assert all(row["reason_wording_stable"] for row in summary["cells"])
assert summary["formal_task_ids_allocated"] == 0
assert summary["post_hoc_retuning_performed"] is False

print("PASS_LGA03_REASON_WORDING_CONTROLLED_MINI_TEST_VALIDATION")
