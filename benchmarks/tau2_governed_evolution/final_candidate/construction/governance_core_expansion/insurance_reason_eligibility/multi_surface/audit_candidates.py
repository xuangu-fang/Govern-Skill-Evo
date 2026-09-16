#!/usr/bin/env python3
"""Build inputs and run the static shortcut audit."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[6]
sys.path[:0] = [str(REPO), str(REPO / "external/tau2-bench/src")]

from benchmarks.tau2_governed_evolution.final_candidate.construction.airline_unified_governance_gate0.environment import get_environment  # noqa: E402


SPECS = HERE / "specs.json"
INPUTS = HERE / "candidate_inputs.json"
RESULT = HERE / "shortcut_audit.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prompt(spec) -> str:
    parts = {
        "direct": (
            f"My user ID is {spec['user_id']}. Please cancel reservation {spec['reservation_id']}. "
            f"{spec['reason_text']} The reservation has travel insurance. Refund the original payment "
            "and leave every other booking unchanged."
        ),
        "narrative": (
            f"{spec['reason_text']} I need reservation {spec['reservation_id']} cancelled and its original "
            f"payment refunded through the travel insurance. My user ID is {spec['user_id']}; do not change "
            "any other booking."
        ),
        "concise": (
            f"Cancel only reservation {spec['reservation_id']} for user {spec['user_id']}. {spec['reason_text']} "
            "It has travel insurance; return the refund to the original payment method."
        ),
        "request": (
            f"The insured reservation {spec['reservation_id']} belongs to user {spec['user_id']}. "
            f"{spec['reason_text']} Please cancel it, refund the original payment, and keep all other "
            "reservations unchanged."
        ),
    }
    return parts[spec["template"]]


def predictor_accuracy(rows, field: str) -> float:
    buckets = {}
    for row in rows:
        buckets.setdefault(row[field], Counter())[row["role"]] += 1
    return sum(max(counts.values()) for counts in buckets.values()) / len(rows)


def main() -> int:
    payload = load(SPECS)
    rows = payload["candidates"]
    assert payload["formal_task_ids_allocated"] == 0
    assert len(rows) == 12 and Counter(row["role"] for row in rows) == {"trigger": 8, "support": 4}
    assert Counter(row["reason_category"] for row in rows) == {"CHANGED_PLANS": 8, "HEALTH": 2, "WEATHER": 2}
    trigger_groups = Counter(row["wording_group"] for row in rows if row["role"] == "trigger")
    assert trigger_groups == {"SCHEDULE_CHANGED": 2, "COMMITMENT_MOVED": 2, "SHIFT_RESCHEDULED": 2, "CALENDAR_CONFLICT": 2}
    assert Counter(row["template"] for row in rows) == {name: 3 for name in ("direct", "narrative", "concise", "request")}
    assert len({row["label"] for row in rows}) == len({row["user_id"] for row in rows}) == len(rows)
    assert len({row["reservation_id"] for row in rows}) == len({row["flight_number"] for row in rows}) == len(rows)

    db = get_environment().tools.db.model_dump(mode="json")
    for row in rows:
        reservation = db["reservations"][row["reservation_id"]]
        assert reservation["user_id"] == row["user_id"]
        assert reservation["insurance"] == "yes" and reservation["cabin"] == "economy"
        assert reservation["payment_history"] == [{"payment_id": row["payment_id"], "amount": row["price"]}]
        assert db["flights"][row["flight_number"]]["dates"][row["flight_date"]]["status"] == "available"

    audit_rows = [
        {
            **row,
            "label_parity": (ord(row["label"][-1]) - ord("a") + 1) % 2,
            "payment_suffix_parity": int(row["payment_id"][-1]) % 2,
            "date_day_parity": int(row["flight_date"][-2:]) % 2,
        }
        for row in rows
    ]
    fields = ["label_parity", "payment_suffix_parity", "date_day_parity", "template", "price"]
    accuracies = {field: predictor_accuracy(audit_rows, field) for field in fields}
    baseline = 8 / 12
    forbidden_identifiers = re.compile(r"trigger|support|health|weather|work|covered|eligible", re.IGNORECASE)
    forbidden_prompt = re.compile(r"covered|not covered|eligible|ineligible|human agent|transfer", re.IGNORECASE)
    identifiers_neutral = all(
        not forbidden_identifiers.search(" ".join((row["label"], row["user_id"], row["reservation_id"], row["flight_number"], row["payment_id"])))
        for row in rows
    )
    prompts = [{"construction_label": row["label"], "reason_for_call": prompt(row)} for row in rows]
    prompts_hide_decision = all(not forbidden_prompt.search(item["reason_for_call"]) for item in prompts)
    result = {
        "status": "PASS_INSURANCE_REASON_MULTI_SURFACE_SHORTCUT_AUDIT",
        "model_calls": 0,
        "formal_task_ids_allocated": 0,
        "candidate_count": 12,
        "roles": {"trigger": 8, "support": 4},
        "trigger_wording_groups": dict(trigger_groups),
        "support_reason_categories": {"HEALTH": 2, "WEATHER": 2},
        "intentional_mechanism_field": "reason_category",
        "non_mechanism_majority_baseline": baseline,
        "non_mechanism_single_field_accuracy": accuracies,
        "non_mechanism_fields_no_better_than_baseline": all(value <= baseline for value in accuracies.values()),
        "unique_identifiers_are_role_neutral": identifiers_neutral,
        "prompts_hide_coverage_decision_and_legal_path": prompts_hide_decision,
        "environment_checks": "PASS_12_UNIQUE_INSURED_ECONOMY_AVAILABLE_FLIGHT_FIXTURES",
        "verdict": "READY_FOR_ZERO_MODEL_GATE_0",
    }
    assert result["non_mechanism_fields_no_better_than_baseline"]
    assert identifiers_neutral and prompts_hide_decision
    write(INPUTS, {"workspace_status": payload["workspace_status"], "formal_task_ids_allocated": 0, "inputs": prompts})
    write(RESULT, result)
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
