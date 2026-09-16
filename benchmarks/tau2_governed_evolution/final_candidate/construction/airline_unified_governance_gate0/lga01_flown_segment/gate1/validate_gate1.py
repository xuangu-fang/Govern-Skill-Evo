#!/usr/bin/env python3
"""Validate LGA01 topology-stratified matched Gate 1 output."""

import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
rows = summary["rows"]
assert summary["status"] == "COMPLETE"
assert summary["verdict"] in {"PASS_LGA01_GATE_1_TRIGGER_NECESSITY", "HOLD_LGA01_GATE_1_TRIGGER_NECESSITY"}
assert summary["rule_id"] == "airline.cancellation.flown_segment_boundary.v1"
assert summary["behavioral_rollouts"] == 8 and summary["formal_task_ids_allocated"] == 0
assert Counter(row["condition"] for row in rows) == {"E0": 4, "ER_LGA01": 4}
assert Counter(row["topology"] for row in rows) == {"TWO_SEGMENT_OUT_AND_BACK": 4, "MULTI_SEGMENT_OUT_AND_BACK": 4}
assert {row["seed"] for row in rows} == {4411, 4412}
criteria = summary["criteria"]
calculated = (
    criteria["e0_focal_observed"] >= criteria["e0_focal_required"]
    and all(value["e0_focal"] >= criteria["e0_focal_required_per_topology"] for value in summary["by_topology"].values())
    and criteria["er_cs_observed"] == criteria["er_cs_required"]
    and all(value["er_cs"] == criteria["er_cs_required_per_topology"] for value in summary["by_topology"].values())
    and criteria["trace_invalid"] == 0 and criteria["first_user_path_leaks"] == 0 and criteria["invalid_user_simulator_rollouts"] == 0
)
assert summary["verdict"].startswith("PASS_") == calculated
print("PASS_LGA01_GATE_1_RESULT_VALIDATION")
