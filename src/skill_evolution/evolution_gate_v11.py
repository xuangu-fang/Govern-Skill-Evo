"""Count-based v0.11 evolution gate."""

from __future__ import annotations

import copy
from collections import Counter
from typing import Any

OUTCOME_STATES = (
    "compliant_success",
    "violating_success",
    "compliant_failure",
    "violating_failure",
)


def aggregate_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Cannot aggregate an empty replay batch.")
    states = Counter(row["state"] for row in rows)
    if set(states) - set(OUTCOME_STATES):
        raise ValueError("Invalid four-state value.")
    count = len(rows)
    success = sum(bool(row["task_success"]) for row in rows)
    compliant = sum(bool(row["compliant"]) for row in rows)
    cup = sum(bool(row["task_success"] and row["compliant"]) for row in rows)
    return {
        "trajectory_count": count,
        "task_success_count": success,
        "compliance_count": compliant,
        "cup_count": cup,
        "task_success_rate": success / count,
        "compliance_rate": compliant / count,
        "cup_rate": cup / count,
        "four_state_distribution": {state: states[state] for state in OUTCOME_STATES},
    }


def build_evolution_decision(
    *,
    targeted_fix_results: list[dict[str, Any]],
    regression_diagnoses: list[dict[str, Any]],
    parent_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    fixed = sum(item.get("status") == "FIXED" for item in targeted_fix_results)
    not_fixed = sum(item.get("status") == "NOT_FIXED" for item in targeted_fix_results)
    if fixed + not_fixed != len(targeted_fix_results):
        raise ValueError("Invalid Targeted Fix status.")
    change_caused = sum(
        item.get("attribution") == "CHANGE_CAUSED" for item in regression_diagnoses
    )
    unrelated = sum(
        item.get("attribution") == "UNRELATED_VARIATION" for item in regression_diagnoses
    )
    if change_caused + unrelated != len(regression_diagnoses):
        raise ValueError("Invalid Regression Diagnosis attribution.")
    parent = aggregate_counts(parent_rows)
    candidate = aggregate_counts(candidate_rows)
    delta = {
        "task_success": candidate["task_success_count"] - parent["task_success_count"],
        "compliance": candidate["compliance_count"] - parent["compliance_count"],
        "cup": candidate["cup_count"] - parent["cup_count"],
    }
    targeted_pass = fixed >= 1
    regression_pass = change_caused == 0
    aggregate_pass = all(value > -3 for value in delta.values())
    reasons = []
    if not targeted_pass:
        reasons.append("NO_TARGETED_FIX")
    if not regression_pass:
        reasons.append("CHANGE_CAUSED_REGRESSION")
    if not aggregate_pass:
        reasons.append("AGGREGATE_COLLAPSE")
    primary = reasons[0] if reasons else "ACCEPTED"
    return {
        "decision": "ACCEPT" if not reasons else "REJECT",
        "targeted_fix": {"fixed": fixed, "not_fixed": not_fixed},
        "regression": {
            "observed_regressions": len(regression_diagnoses),
            "change_caused": change_caused,
            "unrelated_variation": unrelated,
        },
        "aggregate": {
            "parent": copy.deepcopy(parent),
            "candidate": copy.deepcopy(candidate),
            "delta": delta,
        },
        "gate": {
            "targeted_fix_pass": targeted_pass,
            "regression_pass": regression_pass,
            "aggregate_guardrail_pass": aggregate_pass,
        },
        "primary_reason": primary,
        "all_reasons": reasons,
    }


def no_candidate_decision() -> dict[str, Any]:
    return {
        "decision": "NO_CANDIDATE",
        "primary_reason": "NO_CANDIDATE",
        "all_reasons": ["NO_CANDIDATE"],
    }
