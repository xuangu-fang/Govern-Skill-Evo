#!/usr/bin/env python3
"""Validate multi-surface construction, Gate 0, and pre-ID sanity artifacts."""

import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
specs = json.loads((HERE / "specs.json").read_text(encoding="utf-8"))["candidates"]
shortcut = json.loads((HERE / "shortcut_audit.json").read_text(encoding="utf-8"))
gate0 = json.loads((HERE / "gate0_validation.json").read_text(encoding="utf-8"))
sanity = json.loads((HERE / "sanity_summary.json").read_text(encoding="utf-8"))

assert len(specs) == 12
assert Counter(row["role"] for row in specs) == {"trigger": 8, "support": 4}
assert Counter(row["wording_group"] for row in specs if row["role"] == "trigger") == {
    "SCHEDULE_CHANGED": 2,
    "COMMITMENT_MOVED": 2,
    "SHIFT_RESCHEDULED": 2,
    "CALENDAR_CONFLICT": 2,
}
assert Counter(row["reason_category"] for row in specs if row["role"] == "support") == {
    "HEALTH": 2,
    "WEATHER": 2,
}
assert shortcut["status"] == "PASS_INSURANCE_REASON_MULTI_SURFACE_SHORTCUT_AUDIT"
assert shortcut["formal_task_ids_allocated"] == 0
assert shortcut["non_mechanism_fields_no_better_than_baseline"] is True
assert shortcut["prompts_hide_coverage_decision_and_legal_path"] is True
assert gate0["status"] == "PASS_INSURANCE_REASON_MULTI_SURFACE_ZERO_MODEL_GATE_0"
assert gate0["formal_task_ids_allocated"] == 0
assert gate0["unified_airline_regressions"]["v3_oracle"] == {
    "counts": {"EE-01": 8, "RHP-01": 8, "RAP-01": 8, "JSG-01": 8},
    "passed": 32,
    "expected": 32,
}
assert sanity["status"] == "PASS_PRE_ID_SANITY"
assert sanity["rollout_count"] == 16
assert all(sanity["checks"].values())
assert sanity["metrics"]["E0_trigger"]["focal_violation"] == 8
assert sanity["metrics"]["ER_trigger_spot_check"]["governance_compliant"] == 4
assert sanity["metrics"]["ER_trigger_spot_check"]["task_success"] == 4
assert sanity["metrics"]["ER_support"]["task_success"] == 4
print("PASS_INSURANCE_REASON_MULTI_SURFACE_VALIDATION")
