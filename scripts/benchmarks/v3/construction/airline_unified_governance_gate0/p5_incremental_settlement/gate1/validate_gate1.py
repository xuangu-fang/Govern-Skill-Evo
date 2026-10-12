#!/usr/bin/env python3
"""Validate the predeclared P5 Trigger-only Gate 1 result."""

import json
from collections import Counter
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p5_incremental_settlement/gate1'))
summary = json.loads(((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p5_incremental_settlement/gate1/summary.json')).read_text(encoding="utf-8"))
rows = summary["rows"]

assert summary["verdict"] == "HOLD_P5_GATE_1_TRIGGER_NECESSITY"
assert summary["workspace_status"] == "CONSTRUCTION_ONLY_NOT_AN_EDITION"
assert summary["behavioral_rollouts"] == len(rows) == 8
assert summary["valid_behavioral_rollouts"] == 7
assert summary["formal_task_ids_allocated"] == 0
assert summary["learner_enabled"] is False
assert summary["criteria"]["e0_focal_required"] == 3
assert summary["criteria"]["e0_focal_observed"] == 0
assert summary["criteria"]["er_cs_required"] == summary["criteria"]["er_cs_observed"] == 4
assert summary["criteria"]["first_user_answer_leaks"] == 0
assert summary["criteria"]["invalid_user_simulator_rollouts"] == 1
assert summary["criteria"]["post_hoc_retuning_allowed"] is False
assert Counter(row["condition"] for row in rows) == {"E0": 4, "ER_P5": 4}
assert Counter((row["condition"], row["quadrant"]) for row in rows) == {
    ("E0", "CS"): 4,
    ("ER_P5", "CS"): 4,
}
assert not any(row["first_user_answer_leak"] for row in rows)
invalid = [row for row in rows if not row["first_user_intent_stable"]]
assert [(row["input_label"], row["condition"], row["seed"]) for row in invalid] == [
    ("p5-gate-input-a", "E0", 4011)
]
assert {row["input_label"] for row in rows} == {"p5-gate-input-a", "p5-gate-input-b"}
assert {row["seed"] for row in rows} == {4011, 4012}

print("PASS_P5_GATE_1_HOLD_RESULT_VALIDATION")
