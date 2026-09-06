"""Apply the Step 7 manual review to the completed calibration artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).with_name("parent_calibration")
RESULTS_PATH = ROOT / "rollout_results.jsonl"
SUMMARY_PATH = ROOT / "parent_calibration_summary.json"

# Only non-CS trajectories need explicit overrides. The review checked each
# trajectory against its target Novel Policy and the relevant tool state.
REVIEWS = {
    ("v3_np3_01_cheapest_short_connection", 200): (
        "GENERAL_EXECUTION",
        "Booked the policy-valid itinerary in Basic Economy instead of Economy.",
    ),
    ("v3_np3_01_cheapest_short_connection", 202): (
        "GENERAL_EXECUTION",
        "Booked the policy-valid itinerary in the wrong cabin and made an unsupported fare comparison.",
    ),
    ("v3_np3_02_earliest_arrival_short_connection", 201): (
        "GENERAL_EXECUTION",
        "Booked a policy-valid but later-arriving itinerary instead of the requested earliest valid option.",
    ),
    ("v3_np3_03_modification_short_connection", 200): (
        "OTHER",
        "The P3-compliant update succeeded, but the agent misstated a fare observed in tool results.",
    ),
    ("v3_np3_04_multi_passenger_short_connection", 202): (
        "GENERAL_EXECUTION",
        "Booked the policy-valid itinerary but added three checked bags despite the no-baggage request.",
    ),
    ("v3_np3_05_exact_90_boundary", 201): (
        "OTHER",
        "The exactly-90-minute itinerary was correctly allowed; the Judge flagged a subjective adjective.",
    ),
    ("v3_np4_04_change_future_return_only", 200): (
        "OTHER",
        "The operational segment was preserved, but the stated card suffix did not match the payment method used.",
    ),
    ("v3_np7_04_multi_passenger_payment_mix", 202): (
        "OTHER",
        "The certificate was maximally applied; the Judge flagged the original insurance-question requirement.",
    ),
    ("v3_np7_05_certificate_not_selected", 200): (
        "TAU_REWARD / TASK_REFERENCE",
        "Boundary payment wording names the payment-id suffix as card last-four; the simulator rejected the actual saved card.",
    ),
}

HEADROOM = {policy: "SATURATED" for policy in ("P1", "P3", "P4", "P5", "P7")}


def main() -> None:
    rows = [json.loads(line) for line in RESULTS_PATH.read_text().splitlines() if line]
    if len(rows) != 75 or any(row["runtime_error"] for row in rows):
        raise ValueError("Manual review requires 75 valid, error-free rollout rows.")

    for row in rows:
        key = (row["task_id"], row["seed"])
        if key in REVIEWS:
            attribution, label = REVIEWS[key]
            row["mechanism_related_issue"] = False
            row["mechanism_label"] = label
            row["mechanism_recurrent_after_review"] = False
            row["primary_failure_attribution"] = attribution
        else:
            row["mechanism_related_issue"] = False
            row["mechanism_label"] = None
            row["mechanism_recurrent_after_review"] = False
            row["primary_failure_attribution"] = None

    RESULTS_PATH.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )

    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    vs_rows = [row for row in rows if row["quadrant"] == "VS"]
    summary["manual_review"] = {
        "non_cs_rollouts_reviewed": sum(row["quadrant"] != "CS" for row in rows),
        "target_rollouts_reviewed": sum(row["role"] == "TARGET" for row in rows),
        "target_policy_issue_rollouts": 0,
        "recurrent_target_tasks": [],
        "recurrent_vs_tasks": [],
        "mechanisms_with_cross_task_recurrence": [],
        "headroom": HEADROOM,
        "strong_policy_count": 0,
        "raw_vs_count": len(vs_rows),
        "vs_tasks": sorted({row["task_id"] for row in vs_rows}),
        "per_policy_vs": dict(Counter(row["policy_id"] for row in vs_rows)),
        "primary_failure_attribution": dict(
            Counter(
                row["primary_failure_attribution"]
                for row in rows
                if row["primary_failure_attribution"]
            )
        ),
        "boundary_quadrants": {
            policy: [
                row["quadrant"]
                for row in rows
                if row["policy_id"] == policy and row["role"] == "POSITIVE_BOUNDARY"
            ]
            for policy in HEADROOM
        },
        "overall_headroom": "NOT_SUPPORTED",
        "next_decision": "HOLD",
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
