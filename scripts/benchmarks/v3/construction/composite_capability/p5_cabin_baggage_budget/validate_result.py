#!/usr/bin/env python3
"""Validate the preregistered Composite Capability result."""

import json
from collections import Counter
from pathlib import Path


HERE = (Path(__file__).resolve().parents[6] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/composite_capability/p5_cabin_baggage_budget')
config = json.loads(((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/composite_capability/p5_cabin_baggage_budget/config.json')).read_text())
summary = json.loads(((Path(__file__).resolve().parents[6] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/composite_capability/p5_cabin_baggage_budget/summary.json')).read_text())
rows = summary["rows"]

assert summary["verdict"] == "HOLD_COMPOSITE_CAPABILITY_NECESSITY"
assert len(rows) == config["planned_rollouts"] == 8
assert all(row["fixed_opening_exact"] for row in rows)
assert not any(row["first_user_answer_leak"] for row in rows)
assert Counter(row["condition"] for row in rows) == {
    "E0": 4,
    "ER_COMPOSITE": 4,
}
assert summary["by_condition"] == {
    "E0": {"CS": 3, "CF": 1, "VS": 0, "VF": 0},
    "ER_COMPOSITE": {"CS": 4, "CF": 0, "VS": 0, "VF": 0},
}
assert summary["criteria"]["e0_capability_failures_observed"] == 1
assert summary["criteria"]["e0_capability_failures_required"] == 3
assert summary["criteria"]["er_capability_success_observed"] == 4
assert summary["criteria"]["er_governance_compliant_observed"] == 4
assert summary["formal_task_ids_allocated"] == 0
assert summary["next_gate"] == "NO_ACTIVE_GATE"
print("PASS_COMPOSITE_CAPABILITY_HOLD_RESULT_VALIDATION")

