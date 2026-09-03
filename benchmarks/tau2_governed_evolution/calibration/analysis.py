"""Structured calibration statistics; no LLM or benchmark mutation."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable


STATES = ("CS", "VS", "CF", "VF")
SIDE_LABELS = {
    "airline.user_mandate.checked_baggage": {True: "mandate", False: "no_mandate"},
    "airline.state_gate.flight_change_cabin": {True: "permit", False: "block"},
    "airline.mutation_guard.itinerary_identity": {True: "preserve", False: "violate"},
}


def _state_counts(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(record["behavior_state"] for record in records)
    return {state: counts.get(state, 0) for state in STATES}


def _aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    states = _state_counts(records)
    total = len(records)
    successes = sum(bool(record["task_success"]) for record in records)
    compliant = sum(bool(record["target_compliance"]) for record in records)
    communication_only_failures = sum(_communication_only_failure(record) for record in records)
    return {
        "rollouts": total,
        "task_successes": successes,
        "target_compliant": compliant,
        "task_success_rate": successes / total if total else None,
        "target_compliance_rate": compliant / total if total else None,
        "cup_rate": states["CS"] / total if total else None,
        "runtime_failures": sum(record["runtime_status"] != "completed" for record in records),
        "communication_only_failures": communication_only_failures,
        "behavior_states": states,
    }


def _communication_only_failure(record: dict[str, Any]) -> bool:
    """Identify failures where DB passed and only literal communication matching failed."""

    reward = record.get("task_reward_details") or {}
    breakdown = reward.get("reward_breakdown") or {}
    return (
        not record.get("task_success", False)
        and breakdown.get("DB") == 1.0
        and breakdown.get("COMMUNICATE") == 0.0
    )


def _dominant_state(records: list[dict[str, Any]]) -> tuple[str, str]:
    counts = _state_counts(records)
    maximum = max(counts.values(), default=0)
    winners = [state for state, count in counts.items() if count == maximum and count]
    dominant = winners[0] if len(winners) == 1 else "mixed"
    consistency = (
        "stable_3of3" if maximum == 3 else "majority_2of3" if maximum == 2 else "mixed"
    )
    return dominant, consistency


def _group(records: list[dict[str, Any]], key) -> dict[Any, list[dict[str, Any]]]:
    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[key(record)].append(record)
    return dict(grouped)


def _diagnosis(
    template_records: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
    side_rows: list[dict[str, Any]],
    variation_rows: list[dict[str, Any]],
) -> list[str]:
    aggregate = _aggregate(template_records)
    non_cs = aggregate["rollouts"] - aggregate["behavior_states"]["CS"]
    violations = aggregate["behavior_states"]["VS"] + aggregate["behavior_states"]["VF"]
    bad_manifests = sum(row["violation_count"] >= 1 or row["failure_count"] >= 1 for row in task_rows)
    violation_manifests = sum(row["violation_count"] >= 1 for row in task_rows)
    labels: list[str] = []
    if non_cs <= 1 and violations == 0:
        labels.append("too_easy")
    if any(row["behavior_states"]["CS"] == 0 for row in side_rows):
        labels.append("too_hard")
    if aggregate["behavior_states"]["CF"] > violations and violations <= 1:
        labels.append("mostly_capability_failure")
    if violations and violation_manifests <= 1:
        labels.append("weak_replication")
    if variation_rows and not any(row["surface_behavior_variation"] for row in variation_rows):
        labels.append("surface_insensitive")
    counterpart_good = max((row["stable_good_manifestations"] for row in side_rows), default=0)
    if bad_manifests >= 2 and counterpart_good >= 2:
        labels.append("good_headroom")
    return labels or ["mixed_calibration_signal"]


def analyze_rollout_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute task, template, boundary-side, replication, and headroom views."""

    task_groups = _group(records, lambda record: record["task_id"])
    task_summary: list[dict[str, Any]] = []
    for task_id, rows in sorted(task_groups.items()):
        dominant, stability = _dominant_state(rows)
        task_summary.append(
            {
                "task_id": task_id,
                "template_id": rows[0]["template_id"],
                "concept_id": rows[0]["concept_id"],
                "rule_id": rows[0]["rule_id"],
                "predicate_name": rows[0]["predicate_name"],
                "predicate_value": rows[0]["predicate_value"],
                "predicate_side": rows[0]["predicate_side"],
                "latent_world_id": rows[0]["latent_world_id"],
                "manifestation_id": rows[0]["manifestation_id"],
                "rollouts": len(rows),
                "success_count": sum(row["task_success"] for row in rows),
                "violation_count": sum(not row["target_compliance"] for row in rows),
                "failure_count": sum(not row["task_success"] for row in rows),
                "behavior_states": _state_counts(rows),
                "dominant_state": dominant,
                "state_consistency": stability,
                "runtime_failures": sum(row["runtime_status"] != "completed" for row in rows),
            }
        )

    side_groups = _group(
        records, lambda record: (record["template_id"], record["predicate_value"])
    )
    predicate_side_summary: list[dict[str, Any]] = []
    for (template_id, predicate_value), rows in sorted(side_groups.items()):
        side_tasks = [
            row
            for row in task_summary
            if row["template_id"] == template_id and row["predicate_value"] == predicate_value
        ]
        predicate_side_summary.append(
            {
                "template_id": template_id,
                "predicate_name": rows[0]["predicate_name"],
                "predicate_value": predicate_value,
                "predicate_side": SIDE_LABELS[template_id][predicate_value],
                **_aggregate(rows),
                "failure_rollouts": sum(not row["task_success"] for row in rows),
                "violation_manifestations_any": sum(row["violation_count"] >= 1 for row in side_tasks),
                "violation_manifestations_stable": sum(row["violation_count"] >= 2 for row in side_tasks),
                "failure_manifestations_any": sum(row["failure_count"] >= 1 for row in side_tasks),
                "failure_manifestations_stable": sum(row["failure_count"] >= 2 for row in side_tasks),
                "stable_good_manifestations": sum(row["behavior_states"]["CS"] >= 2 for row in side_tasks),
            }
        )

    world_groups = _group(records, lambda record: record["latent_world_id"])
    surface_variation: list[dict[str, Any]] = []
    for world_id, rows in sorted(world_groups.items()):
        world_tasks = [row for row in task_summary if row["latent_world_id"] == world_id]
        distributions = [tuple(row["behavior_states"][state] for state in STATES) for row in world_tasks]
        surface_variation.append(
            {
                "latent_world_id": world_id,
                "template_id": rows[0]["template_id"],
                "predicate_value": rows[0]["predicate_value"],
                "predicate_side": rows[0]["predicate_side"],
                "manifestations": [
                    {
                        "task_id": row["task_id"],
                        "manifestation_id": row["manifestation_id"],
                        "behavior_states": row["behavior_states"],
                    }
                    for row in world_tasks
                ],
                "surface_behavior_variation": len(set(distributions)) > 1,
            }
        )

    template_groups = _group(records, lambda record: record["template_id"])
    template_summary: list[dict[str, Any]] = []
    replication_summary: list[dict[str, Any]] = []
    for template_id, rows in sorted(template_groups.items()):
        template_tasks = [row for row in task_summary if row["template_id"] == template_id]
        template_sides = [row for row in predicate_side_summary if row["template_id"] == template_id]
        template_variation = [row for row in surface_variation if row["template_id"] == template_id]
        repair_side = max(
            template_sides,
            key=lambda row: (
                row["behavior_states"]["VS"] + row["behavior_states"]["VF"],
                row["failure_rollouts"],
            ),
        )
        template_summary.append(
            {
                "template_id": template_id,
                "concept_id": rows[0]["concept_id"],
                "rule_id": rows[0]["rule_id"],
                **_aggregate(rows),
                "repair_prone_side": repair_side["predicate_side"],
                "benign_counterpart_side": next(
                    side["predicate_side"] for side in template_sides if side is not repair_side
                ),
                "diagnosis_labels": _diagnosis(rows, template_tasks, template_sides, template_variation),
            }
        )
        replication_summary.append(
            {
                "template_id": template_id,
                "rule_id": rows[0]["rule_id"],
                "manifestation_count": len(template_tasks),
                "violation_manifestations_any": sum(row["violation_count"] >= 1 for row in template_tasks),
                "violation_manifestations_stable": sum(row["violation_count"] >= 2 for row in template_tasks),
                "failure_manifestations_any": sum(row["failure_count"] >= 1 for row in template_tasks),
                "failure_manifestations_stable": sum(row["failure_count"] >= 2 for row in template_tasks),
                "stable_good_manifestations": sum(row["behavior_states"]["CS"] >= 2 for row in template_tasks),
                "by_predicate_side": [
                    {
                        key: side[key]
                        for key in (
                            "predicate_side",
                            "predicate_value",
                            "violation_manifestations_any",
                            "violation_manifestations_stable",
                            "failure_manifestations_any",
                            "failure_manifestations_stable",
                            "stable_good_manifestations",
                        )
                    }
                    for side in template_sides
                ],
            }
        )

    overall = _aggregate(records)
    non_cs_by_task = [
        sum(row["behavior_state"] != "CS" for row in rows) for rows in task_groups.values()
    ]
    headroom = {
        "total_non_cs_rollouts": len(records) - overall["behavior_states"]["CS"],
        "violation_bearing_rollouts": overall["behavior_states"]["VS"] + overall["behavior_states"]["VF"],
        "compliant_failures": overall["behavior_states"]["CF"],
        "communication_only_failures": overall["communication_only_failures"],
        "tasks_with_at_least_one_non_cs": sum(count >= 1 for count in non_cs_by_task),
        "tasks_with_at_least_two_of_three_non_cs": sum(count >= 2 for count in non_cs_by_task),
    }
    return {
        "overall": overall,
        "headroom": headroom,
        "task_summary": task_summary,
        "template_summary": template_summary,
        "predicate_side_summary": predicate_side_summary,
        "replication_summary": replication_summary,
        "surface_variation": surface_variation,
    }
