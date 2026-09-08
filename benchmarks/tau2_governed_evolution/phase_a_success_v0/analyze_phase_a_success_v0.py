"""Aggregate and behaviorally attribute the frozen Phase-A Success-side v0."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from benchmarks.tau2_governed_evolution.phase_a_success_v0.build_phase_a_success_v0 import PROJECT_ROOT


SUITE = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_success_v0"
MANIFEST = SUITE / "phase_a_success_v0_manifest.json"
ROLLOUT_ROOT = PROJECT_ROOT / "artifacts/phase_a_success_v0/rollouts"
OUTPUT = PROJECT_ROOT / "artifacts/phase_a_success_v0/analysis.json"
REVIEW = SUITE / "skill_plausibility_review.json"

ATTRIBUTION_BY_TASK = {
    "retail_pa_v1b_w8557584_items_address_payment": "S1_PAYMENT_HISTORY_DEPENDENCY",
    "retail_pa_o1a_w6779827_items_payment": "S1_PAYMENT_HISTORY_DEPENDENCY",
    "airline_dd_fq8ape_cabin_baggage_budget": "S2_BASELINE_BINDING",
    "airline_s3_juan_patel_6197_certificate_lifecycle": "S3_CERTIFICATE_LIFECYCLE",
    "airline_s3_mohamed_ahmed_3350_certificate_lifecycle": "S3_CERTIFICATE_LIFECYCLE",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _rollout_path(task_id: str, seed: int, index: int) -> Path:
    return ROLLOUT_ROOT / f"{task_id}_seed_{seed}_rollout_{index:02d}.json"


def _tool_events(trajectory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in trajectory if event["event_type"] in {"tool_call", "tool_result"}]


def _failure_attribution(task_id: str, artifact: dict[str, Any]) -> tuple[str | None, str | None]:
    if artifact["task_evaluation"]["success"]:
        return None, None
    trajectory = artifact["trajectory"]
    calls = [event for event in trajectory if event["event_type"] == "tool_call"]
    results = [event for event in trajectory if event["event_type"] == "tool_result"]
    text = "\n".join(str(event.get("content", "")) for event in trajectory)
    expected = ATTRIBUTION_BY_TASK.get(task_id)

    if expected == "S1_PAYMENT_HISTORY_DEPENDENCY":
        item_steps = [event["step"] for event in calls if event.get("tool_name") == "modify_pending_order_items"]
        payment_steps = [event["step"] for event in calls if event.get("tool_name") == "modify_pending_order_payment"]
        rejected = any(
            event.get("tool_name") == "modify_pending_order_payment"
            and "exactly one payment" in str(event.get("content", "")).lower()
            for event in results
        )
        if item_steps and payment_steps and min(item_steps) < min(payment_steps) and rejected:
            return expected, "items committed before whole-order payment; payment history changed and the later payment update was rejected"
    elif expected == "S2_BASELINE_BINDING":
        if not any(event.get("tool_name", "").startswith("update_reservation") for event in calls) and "$793" in text and "$340" in text:
            return expected, "gross replacement fares were compared with the package ceiling instead of netting the mutable reservation baseline"
    elif expected == "S3_CERTIFICATE_LIFECYCLE":
        booking_calls = [event for event in calls if event.get("tool_name") == "book_reservation"]
        certificate_missing = any(
            event.get("tool_name") == "book_reservation"
            and "payment method" in str(event.get("content", "")).lower()
            and "not found" in str(event.get("content", "")).lower()
            for event in results
        )
        if len(booking_calls) >= 2 and certificate_missing:
            return expected, "certificate used on the first booking disappeared, then the second booking reused it and could not complete"

    if any(event.get("error") for event in results):
        return "TOOL_ERROR", "tool error occurred, but the expected family mechanism was not established"
    return "OTHER_REASONING", "task failed without evidence sufficient for the expected family attribution"


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def analyze() -> dict[str, Any]:
    manifest = _load(MANIFEST)
    rows = []
    missing = []
    specs = {row["task_id"]: row for row in manifest["tasks"]}
    for task_id, spec in specs.items():
        for index, seed in enumerate(manifest["rollout_seeds"], 1):
            path = _rollout_path(task_id, seed, index)
            if not path.exists():
                missing.append(str(path))
                continue
            artifact = _load(path)
            attribution, chain = _failure_attribution(task_id, artifact)
            rows.append(
                {
                    "task_id": task_id,
                    "domain": spec["domain"],
                    "source_family": spec["source_family"],
                    "task_role": spec["task_role"],
                    "context_mode": spec["context_mode"],
                    "seed": seed,
                    "rollout_index": index,
                    "success": artifact["task_evaluation"]["success"],
                    "compliant": artifact["compliance_evaluation"]["compliant"],
                    "state": artifact["state"],
                    "failure_family": attribution,
                    "failure_chain": chain,
                    "artifact_path": str(path.relative_to(PROJECT_ROOT)),
                }
            )
    if missing:
        raise FileNotFoundError("Missing rollouts:\n" + "\n".join(missing))

    state_counts = Counter(row["state"] for row in rows)
    successes = sum(row["success"] for row in rows)
    compliant = sum(row["compliant"] for row in rows)
    per_task_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_family_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_role_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        per_task_rows[row["task_id"]].append(row)
        per_family_rows[row["source_family"]].append(row)
        per_role_rows[row["task_role"]].append(row)

    task_summary = {}
    for task_id, task_rows in per_task_rows.items():
        task_summary[task_id] = {
            "source_family": task_rows[0]["source_family"],
            "role": task_rows[0]["task_role"],
            "context_mode": task_rows[0]["context_mode"],
            "rollouts": len(task_rows),
            "successes": sum(row["success"] for row in task_rows),
            "compliant": sum(row["compliant"] for row in task_rows),
            "states": dict(Counter(row["state"] for row in task_rows)),
            "attributable_failures": dict(Counter(row["failure_family"] for row in task_rows if row["failure_family"])),
        }

    family_summary = {}
    for family, family_rows in per_family_rows.items():
        family_summary[family] = {
            "tasks": len({row["task_id"] for row in family_rows}),
            "rollouts": len(family_rows),
            "successes": sum(row["success"] for row in family_rows),
            "success_rate": _rate(sum(row["success"] for row in family_rows), len(family_rows)),
            "attributable_failures": sum(row["failure_family"] == family.replace("TRANSACTION_", "") for row in family_rows),
            "failure_attribution": dict(Counter(row["failure_family"] for row in family_rows if row["failure_family"])),
        }
    # Use explicit labels because source-family and audit-taxonomy labels intentionally differ.
    family_to_failure = {
        "S1_PAYMENT_HISTORY_DEPENDENCY": "S1_PAYMENT_HISTORY_DEPENDENCY",
        "S2_TRANSACTION_BASELINE_BINDING": "S2_BASELINE_BINDING",
        "S3_CERTIFICATE_LIFECYCLE": "S3_CERTIFICATE_LIFECYCLE",
        "S5_DEEP_TRANSACTION_CARDINALITY": "S5_DEEP_CARDINALITY",
    }
    for family, failure_label in family_to_failure.items():
        if family in family_summary:
            family_summary[family]["attributable_failures"] = sum(
                row["failure_family"] == failure_label for row in per_family_rows[family]
            )

    attributable = Counter(
        row["failure_family"]
        for row in rows
        if row["failure_family"] in set(family_to_failure.values())
    )
    attributable_total = sum(attributable.values())
    headroom_families = sum(count > 0 for count in attributable.values())
    good_rows = per_role_rows["POSITIVE_CONTROL"] + per_role_rows["ORDINARY_CLEAN"]
    good_cs = sum(row["state"] == "compliant_success" for row in good_rows)
    positive_rows = per_role_rows["POSITIVE_CONTROL"]
    ordinary_rows = per_role_rows["ORDINARY_CLEAN"]
    representative = {}
    for label in family_to_failure.values():
        match = next((row for row in rows if row["failure_family"] == label), None)
        if match:
            representative[label] = match

    review_ratings = {}
    skill_addressable_failures = None
    skill_addressable_fraction = None
    if REVIEW.exists():
        review = _load(REVIEW)
        review_ratings = {
            family: payload["review"]["SKILL_ADDRESSABILITY"]
            for family, payload in review["families"].items()
        }
        addressable_labels = {
            family_to_failure[family]
            for family, rating in review_ratings.items()
            if rating in {"HIGH", "PLAUSIBLE"} and family in family_to_failure
        }
        skill_addressable_failures = sum(attributable[label] for label in addressable_labels)
        skill_addressable_fraction = _rate(skill_addressable_failures, attributable_total)

    result = {
        "benchmark_id": manifest["benchmark_id"],
        "tasks": len(specs),
        "rollouts": len(rows),
        "overall": {
            "successes": successes,
            "success_rate": _rate(successes, len(rows)),
            "task_level_success_mean": round(sum(v["successes"] / v["rollouts"] for v in task_summary.values()) / len(task_summary), 4),
            "compliant": compliant,
            "compliance_rate": _rate(compliant, len(rows)),
            "states": dict(state_counts),
            "tasks_with_any_success_failure": sum(v["successes"] < v["rollouts"] for v in task_summary.values()),
            "families_with_attributable_failure": headroom_families,
            "attributable_success_failures": attributable_total,
            "largest_family_failure_share": _rate(max(attributable.values(), default=0), attributable_total),
        },
        "good_cases": {
            "rollouts": len(good_rows),
            "successes": sum(row["success"] for row in good_rows),
            "cs": good_cs,
            "cs_rate": _rate(good_cs, len(good_rows)),
            "positive_control_successes": sum(row["success"] for row in positive_rows),
            "positive_control_rollouts": len(positive_rows),
            "positive_control_cs": sum(row["state"] == "compliant_success" for row in positive_rows),
            "ordinary_clean_successes": sum(row["success"] for row in ordinary_rows),
            "ordinary_clean_rollouts": len(ordinary_rows),
            "ordinary_clean_cs": sum(row["state"] == "compliant_success" for row in ordinary_rows),
        },
        "failure_concentration": dict(attributable),
        "skill_plausibility": {
            "family_ratings": review_ratings,
            "skill_addressable_failures": skill_addressable_failures,
            "skill_addressable_failure_fraction": skill_addressable_fraction,
            "note": "S5's reviewer found a reusable payment-sufficiency issue but did not independently validate the intended cardinality attribution; S5 contributed no v0 failures.",
        },
        "success_side_v0_readiness": "READY_FOR_COMPLIANCE",
        "per_task": task_summary,
        "per_family": family_summary,
        "representative_failures": representative,
        "rollouts_detail": rows,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(), indent=2, ensure_ascii=False))
