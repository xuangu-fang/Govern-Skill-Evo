#!/usr/bin/env python3
"""Validate endpoint-preservation topology-stratified Gate 1 output."""

import json
from collections import Counter
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/endpoint_preservation/gate1'))
summary = json.loads(((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/endpoint_preservation/gate1/summary.json')).read_text(encoding="utf-8"))
rows = summary["rows"]

assert summary["status"] == "COMPLETE"
assert summary["verdict"] in {
    "PASS_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY",
    "HOLD_ENDPOINT_PRESERVATION_GATE_1_TRIGGER_NECESSITY",
}
assert summary["workspace_status"] == "CONSTRUCTION_ONLY_NOT_AN_EDITION"
assert summary["evaluator"] == "deterministic_governance_trace_evaluator_v1"
assert summary["shared_rule_id"] == "airline.flight_change.endpoint_preservation.v1"
assert summary["behavioral_rollouts"] == 8
assert summary["formal_task_ids_allocated"] == 0
assert summary["learner_enabled"] is False
assert len(rows) == 8
assert Counter(row["condition"] for row in rows) == {"E0": 4, "ER_ENDPOINT": 4}
assert Counter(row["topology"] for row in rows) == {
    "DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT": 4,
    "APPENDED_REVERSE_RETURN": 4,
}
assert {row["seed"] for row in rows} == {4211, 4212}

criteria = summary["criteria"]
calculated_pass = (
    criteria["e0_focal_observed"] >= criteria["e0_focal_required"]
    and criteria["e0_each_topology_pass"]
    and criteria["er_cs_observed"] == criteria["er_cs_required"]
    and criteria["trace_invalid"] <= criteria["trace_invalid_max"]
    and criteria["first_user_path_leaks"] <= criteria["first_user_path_leak_max"]
    and criteria["invalid_user_simulator_rollouts"] <= criteria["invalid_user_simulator_max"]
)
assert (summary["verdict"].startswith("PASS_")) == calculated_pass

for topology, values in summary["by_topology"].items():
    topology_rows = [row for row in rows if row["topology"] == topology]
    assert len(topology_rows) == values["rollouts"] == 4
    assert values["e0_focal_violations"] == sum(
        row["focal_endpoint_violation"]
        for row in topology_rows
        if row["condition"] == "E0"
    )
    assert values["er_cs"] == sum(
        row["quadrant"] == "CS"
        for row in topology_rows
        if row["condition"] == "ER_ENDPOINT"
    )

print("PASS_ENDPOINT_PRESERVATION_GATE_1_RESULT_VALIDATION")
