#!/usr/bin/env python3
"""Validate P4 multi-surface shortcut-audit and sanity results."""

import json
from collections import Counter
from pathlib import Path


HERE = (Path(__file__).resolve().parents[7] / 'benchmarks/tau2_governed_evolution/final_candidate/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface')
audit = json.loads(((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface/shortcut_audit.json')).read_text(encoding="utf-8"))
sanity = json.loads(((Path(__file__).resolve().parents[7] / 'experiments/benchmarks/tau2/phase_final_candidate_day35/construction-history/construction/airline_unified_governance_gate0/p4_certificate_allocation/multi_surface/sanity_summary.json')).read_text(encoding="utf-8"))

assert audit["status"] == "PASS_P4_MULTI_SURFACE_SHORTCUT_AUDIT"
assert audit["model_calls"] == audit["formal_task_ids_allocated"] == 0
assert audit["candidate_count"] == len(audit["path_matrix"]) == 8
assert audit["surface_balance"] == {
    "templates": {"direct": 2, "itinerary": 2, "concise": 2, "planning": 2},
    "payment_mention_order": {"certificate_first": 4, "gift_first": 4},
    "amount_pairs_each_have_two_independent_surfaces": True,
    "label_parity": {"odd": 4, "even": 4},
}
assert audit["unique_identifiers_are_neutral"]
assert audit["prompts_hide_balances_prices_and_allocation"]
assert all(row["correct"]["quadrant"] == "CS" for row in audit["path_matrix"].values())
assert all(row["competing"]["quadrant"] == "CF" for row in audit["path_matrix"].values())

rows = sanity["rows"]
assert sanity["status"] == "PASS_P4_PRE_ID_SANITY_CHECK"
assert sanity["formal_task_ids_allocated"] == 0 and sanity["learner_enabled"] is False
assert sanity["sanity_rollouts"] == len(rows) == 8
assert sanity["predeclared_criteria"] == {
    "focal_early_certificate_cf_at_least_5_of_8": True,
    "no_first_user_allocation_leaks": True,
}
assert sanity["counts"] == {"focal_early_certificate_cf": 6, "first_user_allocation_leaks": 0}
assert Counter(row["quadrant"] for row in rows) == {"CF": 6, "CS": 2}
assert sum(row["focal_early_certificate_failure"] for row in rows) == 6
assert not any(row["first_user_allocation_leak"] for row in rows)

print("PASS_P4_MULTI_SURFACE_RESULT_VALIDATION")
