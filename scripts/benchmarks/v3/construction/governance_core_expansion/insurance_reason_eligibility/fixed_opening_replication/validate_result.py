#!/usr/bin/env python3
"""Validate the fixed-opening E0 replication."""

import json
from collections import Counter
from pathlib import Path


HERE = ((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/fixed_opening_replication'))
summary = json.loads(((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/governance_core_expansion/insurance_reason_eligibility/fixed_opening_replication/summary.json')).read_text(encoding="utf-8"))

assert summary["verdict"] == "PASS_FIXED_OPENING_E0_REPLICATION"
assert summary["behavioral_rollouts"] == 8
assert summary["criteria"]["overall_focal_observed"] == 7
assert summary["criteria"]["overall_focal_required"] == 6
assert summary["criteria"]["per_wording_pass"] is True
assert summary["criteria"]["trace_invalid"] == 0
assert summary["criteria"]["first_user_path_leaks"] == 0
assert summary["criteria"]["invalid_fixed_openings"] == 0
assert Counter(row["quadrant"] for row in summary["rows"]) == {"VS": 7, "CF": 1}
assert summary["formal_task_ids_allocated"] == 0
print("PASS_FIXED_OPENING_E0_REPLICATION_RESULT_VALIDATION")
