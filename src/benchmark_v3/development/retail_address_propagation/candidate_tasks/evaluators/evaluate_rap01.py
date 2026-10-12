"""Semantic final-state evaluator for RAP-01 candidates."""

from typing import Any


ADDRESS_FIELDS = ("address1", "address2", "city", "state", "country", "zip")


def _matches(observed: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(observed[field] == expected[field] for field in ADDRESS_FIELDS)


def evaluate_success(spec: dict[str, Any], final_db: dict[str, Any]) -> dict[str, Any]:
    order = final_db["orders"][spec["order_id"]]
    user = final_db["users"][spec["user_id"]]
    contract = final_db["address_propagation_contracts"][spec["order_id"]]
    checks = {
        "order_address_matches_temporary_goal": _matches(
            order["address"], spec["order_address"]
        ),
        "profile_address_matches_long_term_goal": _matches(
            user["address"], spec["profile_address"]
        ),
        "both_targets_written_once": sorted(contract["written_targets"])
        == ["order", "profile"],
        "session_closed_after_both_writes": contract["session_closed"] is True,
    }
    return {
        "success": all(checks.values()),
        "semantic_invariant": checks,
        "observed_written_targets": contract["written_targets"],
        "observed_session_closed": contract["session_closed"],
    }
