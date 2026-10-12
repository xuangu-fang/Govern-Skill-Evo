#!/usr/bin/env python3
"""Validate LGA03 matched Gate 1 output."""

import json
from collections import Counter
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/lga03_insurance_reason/gate1'))
summary = json.loads(((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/lga03_insurance_reason/gate1/summary.json')).read_text(encoding="utf-8"))
rows = summary["rows"]

assert summary["status"] == "COMPLETE"
assert summary["verdict"] in {
    "PASS_LGA03_GATE_1_TRIGGER_NECESSITY",
    "HOLD_LGA03_GATE_1_TRIGGER_NECESSITY",
}
assert summary["workspace_status"] == "CONSTRUCTION_ONLY_NOT_AN_EDITION"
assert summary["rule_id"] == "airline.cancellation.insurance_reason_eligibility.v1"
assert summary["behavioral_rollouts"] == 8
assert summary["formal_task_ids_allocated"] == 0
assert summary["learner_enabled"] is False
assert len(rows) == 8
assert Counter(row["condition"] for row in rows) == {"E0": 4, "ER_LGA03": 4}
assert Counter(row["input_label"] for row in rows) == {
    "lga03-gate-a": 4,
    "lga03-gate-b": 4,
}
assert {row["seed"] for row in rows} == {4311, 4312}
criteria = summary["criteria"]
calculated = (
    criteria["e0_focal_observed"] >= criteria["e0_focal_required"]
    and criteria["er_cs_observed"] == criteria["er_cs_required"]
    and criteria["trace_invalid"] <= criteria["trace_invalid_max"]
    and criteria["first_user_path_leaks"] <= criteria["first_user_path_leak_max"]
    and criteria["invalid_user_simulator_rollouts"] <= criteria["invalid_user_simulator_max"]
)
assert summary["verdict"].startswith("PASS_") == calculated
print("PASS_LGA03_GATE_1_RESULT_VALIDATION")
