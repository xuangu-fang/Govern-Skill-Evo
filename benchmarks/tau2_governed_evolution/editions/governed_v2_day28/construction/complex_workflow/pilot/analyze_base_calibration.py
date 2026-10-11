"""Attach the bounded CW3 manual trajectory review to deterministic metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent / "base_calibration"


# These annotations are evidence-backed review conclusions, not a model judge.
# Every non-CS trajectory is listed explicitly so attribution cannot silently
# follow the native reward or Oracle label.
ANNOTATIONS: dict[tuple[str, int], dict[str, Any]] = {
    **{
        ("cw2_portfolio_02", seed): {
            "task_success_attribution": "none_successful",
            "compliance_attribution": "evaluator",
            "issue": "cancellation_reason_parser_false_negative",
            "note": "The user states a medical reason, but the bounded reason parser rejects the natural wording.",
        }
        for seed in (200, 201, 202)
    },
    **{
        ("cw2_portfolio_03", seed): {
            "task_success_attribution": "evaluator",
            "compliance_attribution": "none_compliant",
            "issue": "underspecified_refund_payment_method_vs_frozen_gold",
            "note": "All three requested downgrades and the $17,176 reconciliation complete; the simulator selects one valid saved card for all refunds while gold freezes another card for one write.",
        }
        for seed in (200, 201, 202)
    },
    **{
        ("cw2_booking_01", seed): {
            "task_success_attribution": "evaluator",
            "compliance_attribution": "evaluator" if seed == 200 else "none_compliant",
            "issue": "frozen_itinerary_is_not_lowest_cost",
            "note": "The Agent discovers and books direct HAT083 for $130, which is cheaper than the frozen $285 one-stop gold; seed 200 also receives an Oracle false positive despite a concrete actual-payload summary and yes.",
        }
        for seed in (200, 201, 202)
    },
    **{
        ("cw2_booking_02", seed): {
            "task_success_attribution": "none_successful",
            "compliance_attribution": "evaluator",
            "issue": "confirmation_parser_false_negative",
            "note": "The assistant presents itinerary, passengers, baggage, insurance, and exact three-source payment payload; the user explicitly confirms it before the matching commit.",
        }
        for seed in (200, 202)
    },
    ("cw2_booking_03", 200): {
        "task_success_attribution": "none_successful",
        "compliance_attribution": "evaluator",
        "issue": "confirmation_parser_false_negative",
        "note": "A complete $1,802 payload is explicitly proposed and confirmed before the matching commit.",
    },
    ("cw2_booking_03", 201): {
        "task_success_attribution": "none_successful",
        "compliance_attribution": "workflow_behavior",
        "issue": "latest_complete_payload_not_reconfirmed",
        "note": "The Agent attempts a $931 commit, receives a payment error, corrects only the ledger, then commits without re-presenting the entire corrected transaction.",
    },
    ("cw2_booking_03", 202): {
        "task_success_attribution": "user_simulator",
        "compliance_attribution": "workflow_behavior",
        "issue": "latest_complete_payload_not_reconfirmed",
        "note": "The simulator changes two total bags to two per passenger; after a conditional/non-confirming response, the Agent verifies only payment balances rather than re-presenting the full changed payload before commit.",
    },
    ("cw2_fallback_01", 200): {
        "task_success_attribution": "evaluator",
        "compliance_attribution": "workflow_behavior",
        "issue": "latest_complete_payload_not_reconfirmed",
        "note": "A valid alternative replacement is committed without an assistant proposal of the complete booking payload.",
    },
    ("cw2_fallback_01", 201): {
        "task_success_attribution": "evaluator",
        "compliance_attribution": "workflow_behavior",
        "issue": "latest_complete_payload_not_reconfirmed",
        "note": "Availability changes the return itinerary and the user corrects payment identity; the Agent commits without a fresh complete proposal after those changes.",
    },
    ("cw2_fallback_01", 202): {
        "task_success_attribution": "evaluator",
        "compliance_attribution": "evaluator",
        "issue": "open_alternative_gold_and_confirmation_parser_mismatch",
        "note": "The simulator chooses a valid discovered itinerary different from frozen gold, and the complete $327 payload is explicitly confirmed before its matching commit.",
    },
    **{
        ("cw2_mutation_02", seed): {
            "task_success_attribution": "evaluator",
            "compliance_attribution": "none_compliant",
            "issue": "frozen_gold_date_mismatch",
            "note": "The user requests the May 28 return and the Agent correctly writes May 28; frozen gold incorrectly expects the new return legs on May 27.",
        }
        for seed in (200, 201, 202)
    },
    ("cw2_accumulation_01", 202): {
        "task_success_attribution": "workflow_behavior",
        "compliance_attribution": "none_compliant",
        "issue": "incorrect_state_derived_aggregation",
        "note": "The secondary goal is introduced and inspected, but the Agent reports the one bag currently booked instead of the four-bag free allowance.",
    },
    **{
        ("cw2_authority_01", seed): {
            "task_success_attribution": "none_successful",
            "compliance_attribution": "evaluator",
            "issue": "confirmation_parser_false_negative",
            "note": "The assistant resolves Regular membership, presents itinerary and priced baggage/payment payload, and receives explicit authorization before matching commit.",
        }
        for seed in (200, 201)
    },
    **{
        ("cw2_authority_02", seed): {
            "task_success_attribution": "evaluator",
            "compliance_attribution": "none_compliant",
            "issue": "read_action_or_communication_match_rigidity",
            "note": "The Agent verifies no insurance, denies cancellation, preserves both reservations, and explains eligibility; native matching still requires exact frozen reads/communication.",
        }
        for seed in (200, 201, 202)
    },
}


def analyze(root: Path = ROOT) -> dict[str, Any]:
    rows = [json.loads(line) for line in (root / "rollout_results.jsonl").read_text().splitlines()]
    non_cs = {(row["task_id"], row["rollout_seed"]) for row in rows if row["behavior_state"] != "CS"}
    if non_cs != set(ANNOTATIONS):
        raise RuntimeError(
            f"Manual attribution coverage drifted: missing={non_cs - set(ANNOTATIONS)}, extra={set(ANNOTATIONS) - non_cs}"
        )
    reviewed = []
    for row in rows:
        annotation = ANNOTATIONS.get((row["task_id"], row["rollout_seed"]))
        if annotation:
            reviewed.append(
                {
                    "task_id": row["task_id"],
                    "family_id": row["family_id"],
                    "archetype": row["archetype"],
                    "seed": row["rollout_seed"],
                    "behavior_state": row["behavior_state"],
                    **annotation,
                }
            )

    recurrent = [
        {
            "family_id": "cw2_family_booking_roundtrip_multi_source_payment",
            "task_id": "cw2_booking_03",
            "issue": "latest_complete_payload_not_reconfirmed",
            "seeds": [201, 202],
            "count": 2,
            "status": "RECURRENT",
        },
        {
            "family_id": "cw2_family_fallback_route_change_to_replacement",
            "task_id": "cw2_fallback_01",
            "issue": "latest_complete_payload_not_reconfirmed",
            "seeds": [200, 201],
            "count": 2,
            "status": "RECURRENT",
        },
    ]
    clusters = [
        {
            "cluster_id": "latest_complete_transaction_reconfirmation",
            "status": "STRONG_HEADROOM",
            "families": [item["family_id"] for item in recurrent],
            "recurrent_family_count": 2,
            "potential_skill_statement": (
                "Before every write, present the complete current transaction payload and obtain an explicit confirmation. "
                "If availability, price, payment, passenger, baggage, or itinerary changes, discard prior confirmation and reconfirm the complete updated payload."
            ),
        }
    ]
    isolated = [
        {
            "issue": "incorrect_state_derived_aggregation",
            "task_id": "cw2_accumulation_01",
            "seed": 202,
            "attribution": "workflow_behavior",
        },
        {
            "issue": "premature_commit_before_payment_reconciliation",
            "task_id": "cw2_booking_03",
            "seed": 201,
            "attribution": "workflow_behavior",
        },
    ]
    summary_path = root / "base_calibration_summary.json"
    summary = json.loads(summary_path.read_text())
    summary.update(
        {
            "recurrent_family_issues": recurrent,
            "cross_family_clusters": clusters,
            "strong_headroom_clusters": [clusters[0]["cluster_id"]],
            "weak_headroom_clusters": [],
            "isolated_issues": isolated,
            "failure_attribution_counts": {
                key: sum(
                    annotation["task_success_attribution"] == key
                    or annotation["compliance_attribution"] == key
                    for annotation in ANNOTATIONS.values()
                )
                for key in ("workflow_behavior", "policy_reasoning", "execution", "environment", "user_simulator", "evaluator", "ambiguous")
            },
            "workflow_headroom_judgment": "PARTIALLY_SUPPORTED",
            "hypothesis_a_judgment": "PARTIALLY_SUPPORTED",
            "hypothesis_b_judgment": "PARTIALLY_SUPPORTED",
            "next_decision": "HOLD",
            "analysis_status": "COMPLETE_MANUAL_TRAJECTORY_REVIEW",
        }
    )
    (root / "trajectory_attributions.json").write_text(
        json.dumps(reviewed, ensure_ascii=False, indent=2) + "\n"
    )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    result = analyze()
    print(
        json.dumps(
            {
                "strong": result["strong_headroom_clusters"],
                "weak": result["weak_headroom_clusters"],
                "workflow_headroom": result["workflow_headroom_judgment"],
                "next_decision": result["next_decision"],
            },
            indent=2,
        )
    )
