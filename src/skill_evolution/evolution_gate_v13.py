"""Behavior-targeted, regression-vetoed, rate-guarded v0.13 gate."""

from __future__ import annotations

import copy
from typing import Any

from src.skill_evolution.evolution_gate_v11 import aggregate_counts

COLLAPSE_RATE = -0.15


def build_evolution_decision(
    *, applied_canonical_edits: list[dict[str, Any]],
    targeted_fix_results: list[dict[str, Any]],
    regression_diagnoses: list[dict[str, Any]],
    parent_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    edit_ids = [item.get("canonical_edit_id") for item in applied_canonical_edits]
    result_ids = [item.get("canonical_edit_id") for item in targeted_fix_results]
    if not edit_ids or len(set(edit_ids)) != len(edit_ids) or sorted(edit_ids) != sorted(result_ids):
        raise ValueError("Every applied canonical edit requires exactly one Target Fix result.")
    statuses = [item.get("status") for item in targeted_fix_results]
    if any(value not in {"FIXED", "NOT_FIXED", "NOT_EXERCISED"} for value in statuses):
        raise ValueError("Invalid Target Fix status.")
    transitions = [
        pair.get("transition")
        for result in targeted_fix_results
        for pair in result.get("pair_transitions", [])
        if isinstance(pair, dict)
    ]
    if any(value not in {"IMPROVED", "UNCHANGED_BAD", "PRESERVED", "WORSENED", "NOT_EXERCISED"} for value in transitions):
        raise ValueError("Invalid Target Fix pair transition.")
    fixed = statuses.count("FIXED")
    not_fixed = statuses.count("NOT_FIXED")
    not_exercised = statuses.count("NOT_EXERCISED")
    worsened = transitions.count("WORSENED")
    change_caused = sum(item.get("attribution") == "CHANGE_CAUSED" for item in regression_diagnoses)
    unrelated = sum(item.get("attribution") == "UNRELATED_VARIATION" for item in regression_diagnoses)
    if change_caused + unrelated != len(regression_diagnoses):
        raise ValueError("Invalid Regression Diagnosis attribution.")
    parent, candidate = aggregate_counts(parent_rows), aggregate_counts(candidate_rows)
    rate_delta = {
        "task_success": candidate["task_success_rate"] - parent["task_success_rate"],
        "compliance": candidate["compliance_rate"] - parent["compliance_rate"],
        "cup": candidate["cup_rate"] - parent["cup_rate"],
    }
    count_delta = {
        "task_success": candidate["task_success_count"] - parent["task_success_count"],
        "compliance": candidate["compliance_count"] - parent["compliance_count"],
        "cup": candidate["cup_count"] - parent["cup_count"],
    }
    targeted_pass = fixed == len(applied_canonical_edits) and worsened == 0
    regression_pass = change_caused == 0
    aggregate_pass = all(value > COLLAPSE_RATE for value in rate_delta.values())
    reasons: list[str] = []
    if worsened:
        reasons.append("TARGET_WORSENED")
    if not_fixed:
        reasons.append("TARGET_NOT_FIXED")
    if not_exercised:
        reasons.append("TARGET_NOT_EXERCISED")
    if not regression_pass:
        reasons.append("CHANGE_CAUSED_REGRESSION")
    if not aggregate_pass:
        reasons.append("AGGREGATE_COLLAPSE")
    return {
        "decision": "ACCEPT" if targeted_pass and regression_pass and aggregate_pass else "REJECT",
        "targeted_fix": {
            "fixed": fixed, "not_fixed": not_fixed, "not_exercised": not_exercised,
            "worsened_pairs": worsened, "applied_edits": len(applied_canonical_edits),
        },
        "regression": {
            "observed_regressions": len(regression_diagnoses),
            "change_caused": change_caused, "unrelated_variation": unrelated,
        },
        "aggregate": {
            "parent": copy.deepcopy(parent), "candidate": copy.deepcopy(candidate),
            "count_delta": count_delta, "rate_delta": rate_delta,
            "collapse_rate_threshold": COLLAPSE_RATE,
        },
        "gate": {
            "targeted_fix_pass": targeted_pass, "regression_pass": regression_pass,
            "aggregate_guardrail_pass": aggregate_pass,
        },
        "primary_reason": reasons[0] if reasons else "ACCEPTED",
        "all_reasons": reasons,
    }


def no_candidate_decision() -> dict[str, Any]:
    return {"decision": "NO_CANDIDATE", "primary_reason": "NO_CANDIDATE", "all_reasons": ["NO_CANDIDATE"]}
