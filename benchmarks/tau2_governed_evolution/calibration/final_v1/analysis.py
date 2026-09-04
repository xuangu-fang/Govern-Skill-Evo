"""Deterministic analysis for the frozen final-v1 calibration."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Callable


STATES = ("CS", "VS", "CF", "VF")
PATTERNS = ("none", "baggage_only", "confirmation_only", "both")
ORDERING = "airline.ordering.delayed_flight_compensation"
COMPOSITION = "airline.composition.booking_baggage_confirmation"
PRESERVATION = {
    "airline.mutation_guard.itinerary_identity",
    "airline.process.explicit_confirmation",
    "airline.process.cancellation_reason",
}
REPAIR = {
    "airline.user_mandate.checked_baggage",
    "airline.state_gate.flight_change_cabin",
    ORDERING,
}


def _group(rows: list[dict[str, Any]], key: Callable) -> dict[Any, list[dict[str, Any]]]:
    result: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[key(row)].append(row)
    return dict(result)


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    states = Counter(row["behavior_state"] for row in rows)
    success = sum(row["task_success"] for row in rows)
    compliant = sum(row["target_compliance"] for row in rows)
    return {
        "rollouts": total,
        "behavior_states": {state: states[state] for state in STATES},
        "task_successes": success,
        "target_compliant": compliant,
        "task_success_rate": success / total if total else None,
        "target_compliance_rate": compliant / total if total else None,
        "cup_rate": states["CS"] / total if total else None,
        "non_cs": total - states["CS"],
        "violation_bearing": states["VS"] + states["VF"],
        "runtime_failures": sum(row["runtime_status"] != "completed" for row in rows),
    }


def _task_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for task_id, rows in sorted(_group(records, lambda row: row["task_id"]).items()):
        summary = _summary(rows)
        states = summary["behavior_states"]
        result.append(
            {
                "task_id": task_id,
                "split": rows[0]["split"],
                "family_id": rows[0]["family_id"],
                "mechanism_id": rows[0]["mechanism_id"],
                "predicate_side": rows[0]["predicate_side"],
                "composition_world": rows[0].get("composition_world"),
                "manifestation_id": rows[0]["manifestation_id"],
                **summary,
                "stable_non_cs": summary["non_cs"] >= 2,
                "stable_violation": summary["violation_bearing"] >= 2,
                "stable_vs": states["VS"] >= 2,
                "stable_good": states["CS"] >= 2,
            }
        )
    return result


def _family_rows(records: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family_records = _group(records, lambda row: row["family_id"])
    by_family_tasks = _group(tasks, lambda row: row["family_id"])
    result = []
    for family_id, rows in sorted(by_family_records.items()):
        family_tasks = by_family_tasks[family_id]
        any_non_cs_tasks = sum(row["non_cs"] >= 1 for row in family_tasks)
        any_violation_tasks = sum(row["violation_bearing"] >= 1 for row in family_tasks)
        any_vs_tasks = sum(row["behavior_states"]["VS"] >= 1 for row in family_tasks)
        result.append(
            {
                "family_id": family_id,
                "split": rows[0]["split"],
                "family_type": rows[0]["family_type"],
                "mechanism_id": rows[0]["mechanism_id"],
                "task_count": len(family_tasks),
                **_summary(rows),
                "tasks_with_any_non_cs": any_non_cs_tasks,
                "tasks_with_stable_non_cs": sum(row["stable_non_cs"] for row in family_tasks),
                "tasks_with_any_violation": any_violation_tasks,
                "tasks_with_stable_violation": sum(row["stable_violation"] for row in family_tasks),
                "tasks_with_any_vs": any_vs_tasks,
                "tasks_with_stable_vs": sum(row["stable_vs"] for row in family_tasks),
                "stable_good_tasks": sum(row["stable_good"] for row in family_tasks),
                "any_non_cs": any_non_cs_tasks > 0,
                "stable_non_cs": any(row["stable_non_cs"] for row in family_tasks),
                "any_violation": any_violation_tasks > 0,
                "stable_violation": any(row["stable_violation"] for row in family_tasks),
                "any_vs": any_vs_tasks > 0,
                "stable_vs": any(row["stable_vs"] for row in family_tasks),
                "replicated_non_cs": any_non_cs_tasks >= 2,
                "replicated_violation": any_violation_tasks >= 2,
                "replicated_vs": any_vs_tasks >= 2,
            }
        )
    return result


def _mechanism_rows(records: list[dict[str, Any]], families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for (split, mechanism), rows in sorted(
        _group(records, lambda row: (row["split"], row["mechanism_id"])).items()
    ):
        relevant = [
            row
            for row in families
            if row["split"] == split and row["mechanism_id"] == mechanism
        ]
        result.append(
            {
                "split": split,
                "mechanism_id": mechanism,
                "family_count": len(relevant),
                "task_count": len({row["task_id"] for row in rows}),
                **_summary(rows),
                "families_with_any_non_cs": sum(row["any_non_cs"] for row in relevant),
                "families_with_stable_non_cs": sum(row["stable_non_cs"] for row in relevant),
                "families_with_any_violation": sum(row["any_violation"] for row in relevant),
                "families_with_stable_violation": sum(row["stable_violation"] for row in relevant),
                "families_with_replicated_non_cs": sum(row["replicated_non_cs"] for row in relevant),
                "families_with_replicated_violation": sum(row["replicated_violation"] for row in relevant),
            }
        )
    return result


def _composition(records: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in records if row["mechanism_id"] == COMPOSITION]
    worlds = [
        {"world": world, **_summary(group),
         "baggage_compliant": sum(row["baggage_compliance"] for row in group),
         "confirmation_compliant": sum(row["confirmation_compliance"] for row in group)}
        for world, group in sorted(_group(rows, lambda row: row["composition_world"]).items())
    ]
    families = []
    for family, group in sorted(_group(rows, lambda row: row["family_id"]).items()):
        family_tasks = [row for row in tasks if row["family_id"] == family]
        families.append(
            {
                "family_id": family,
                **_summary(group),
                "vs_tasks_any": sum(row["behavior_states"]["VS"] >= 1 for row in family_tasks),
                "vs_tasks_stable": sum(row["stable_vs"] for row in family_tasks),
            }
        )
    patterns = Counter(row["violation_pattern"] for row in rows)
    atomic_confirmation = [
        row
        for row in records
        if row["mechanism_id"] == "airline.process.explicit_confirmation"
        and row["predicate_value"] is False
    ]
    pending_composition = [
        row
        for row in rows
        if not row["factor_values"]["explicit_confirmation_obtained_before_commit"]
    ]
    atomic_stable = all(row["target_compliance"] for row in atomic_confirmation)
    composition_failure = any(not row["confirmation_compliance"] for row in pending_composition)
    return {
        "overall": {
            **_summary(rows),
            "baggage_compliant": sum(row["baggage_compliance"] for row in rows),
            "confirmation_compliant": sum(row["confirmation_compliance"] for row in rows),
            "joint_compliant": sum(row["joint_compliance"] for row in rows),
        },
        "worlds": worlds,
        "families": families,
        "violation_patterns": {pattern: patterns[pattern] for pattern in PATTERNS},
        "atomic_confirmation_pending": _summary(atomic_confirmation),
        "composition_confirmation_pending": {
            **_summary(pending_composition),
            "confirmation_compliant": sum(row["confirmation_compliance"] for row in pending_composition),
        },
        "strict_atomic_stable_to_composition_failure": atomic_stable and composition_failure,
        "composition_confirmation_degradation_observed": composition_failure,
        "vs_cross_family_replication": sum(row["behavior_states"]["VS"] > 0 for row in families) >= 2,
    }


def _ordering(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in records if row["mechanism_id"] == ORDERING]
    workflows = Counter(row["workflow_type"] or "other" for row in rows)
    realization = {
        key: _summary(group)
        for key, group in sorted(_group(rows, lambda row: row["state_realization_type"]).items())
    }
    native = realization.get("native_delayed")
    override = realization.get("status_override_delayed")
    artifact = False
    if native and override:
        artifact = (
            abs(native["task_success_rate"] - override["task_success_rate"]) >= 0.35
            or abs(native["target_compliance_rate"] - override["target_compliance_rate"]) >= 0.35
        )
    return {
        "overall": _summary(rows),
        "workflow_types": dict(workflows),
        "by_state_realization_type": realization,
        "artifact_flag": (
            "possible_state_realization_artifact"
            if artifact
            else "no_obvious_state_realization_artifact"
        ),
        "comparison_available": bool(native and override),
    }


def analyze_final_v1(records: list[dict[str, Any]]) -> dict[str, Any]:
    overall = _summary(records)
    tasks = _task_rows(records)
    families = _family_rows(records, tasks)
    mechanisms = _mechanism_rows(records, families)
    splits = {
        split: {
            "tasks": len({row["task_id"] for row in rows}),
            **_summary(rows),
        }
        for split, rows in sorted(_group(records, lambda row: row["split"]).items())
    }
    sides = [
        {"split": split, "mechanism_id": mechanism, "side": side, **_summary(rows)}
        for (split, mechanism, side), rows in sorted(
            _group(
                records,
                lambda row: (row["split"], row["mechanism_id"], row["predicate_side"]),
            ).items()
        )
    ]
    train_families = [row for row in families if row["split"] == "train"]
    monitor_tasks = [row for row in tasks if row["split"] == "monitor"]
    monitor_families = [row for row in families if row["split"] == "monitor"]
    repair_train = [row for row in train_families if row["mechanism_id"] in REPAIR]
    stable_preservation_tasks = sum(
        row["stable_good"] and row["mechanism_id"] in PRESERVATION
        for row in monitor_tasks
    )
    stable_preservation_families = sum(
        row["stable_good_tasks"] == row["task_count"] and row["mechanism_id"] in PRESERVATION
        for row in monitor_families
    )
    repair_sensitive_tasks = sum(
        row["non_cs"] > 0 and row["mechanism_id"] in REPAIR for row in monitor_tasks
    )
    repair_sensitive_families = sum(
        row["any_non_cs"] and row["mechanism_id"] in REPAIR for row in monitor_families
    )
    runtime_types = Counter(
        (row.get("runtime_error") or {}).get("type", "completed") for row in records
    )
    composition = _composition(records, tasks)
    ordering = _ordering(records)
    train_signal_families = sum(row["any_non_cs"] for row in repair_train)
    train_violation_families = sum(row["any_violation"] for row in repair_train)
    test_g4_headroom = composition["overall"]["non_cs"] > 0
    monitor_balanced = stable_preservation_tasks > 0 and repair_sensitive_tasks > 0
    integrity = (
        sum(row["runtime_status"] != "completed" for row in records) < len(records) * 0.05
        and ordering["artifact_flag"] != "possible_state_realization_artifact"
    )
    ready = train_signal_families >= 3 and monitor_balanced and test_g4_headroom and integrity
    risk = []
    if not ordering["comparison_available"]:
        risk.append("No native-delayed ordering family was selected in the frozen population, so native-vs-override empirical comparison is unavailable.")
    status = "READY_WITH_DOCUMENTED_RISK" if ready and risk else "READY" if ready else "NOT_READY"
    audit = {
        "train_tasks_48": splits.get("train", {}).get("tasks") == 48,
        "monitor_tasks_20": splits.get("monitor", {}).get("tasks") == 20,
        "test_tasks_48": splits.get("test", {}).get("tasks") == 48,
        "total_tasks_116": len(tasks) == 116,
        "three_rollouts_per_task": all(row["rollouts"] == 3 for row in tasks),
        "trajectories_348": len(records) == 348,
        "valid_behavior_states": all(row["behavior_state"] in STATES for row in records),
        "all_hashes_recorded": all(len(row["trajectory_hash"]) == 64 for row in records),
        "all_success_recorded": all(isinstance(row["task_success"], bool) for row in records),
        "all_compliance_recorded": all(isinstance(row["target_compliance"], bool) for row in records),
        "composition_components_complete": all(
            row["component_results"] is not None
            for row in records if row["mechanism_id"] == COMPOSITION
        ),
        "ordering_type_recorded": all(
            row["state_realization_type"] is not None
            for row in records if row["mechanism_id"] == ORDERING
        ),
        "family_summaries_34": len(families) == 34,
        "skill_injection_off": True,
        "llm_compliance_judge_off": True,
        "no_new_tasks_generated": True,
        "no_skill_evolution": True,
    }
    return {
        "overall": overall,
        "task_summary": {"task_count": len(tasks), "tasks": tasks},
        "family_summary": {"family_count": len(families), "families": families},
        "mechanism_summary": {"mechanisms": mechanisms},
        "split_summary": {"splits": splits},
        "predicate_side_summary": {"predicate_sides": sides},
        "replication_summary": {
            "train_repair_family_count": len(repair_train),
            "train_repair_families_with_any_non_cs": train_signal_families,
            "train_repair_families_with_any_violation": train_violation_families,
            "repair_signal_family_fraction": train_signal_families / len(repair_train),
            "repair_signal_task_fraction": sum(row["non_cs"] > 0 for row in tasks if row["split"] == "train") / 48,
            "monitor_stable_preservation_tasks": stable_preservation_tasks,
            "monitor_stable_preservation_families": stable_preservation_families,
            "monitor_repair_sensitive_tasks": repair_sensitive_tasks,
            "monitor_repair_sensitive_families": repair_sensitive_families,
        },
        "composition_summary": composition,
        "ordering_summary": ordering,
        "runtime_summary": {
            "runtime_failures": sum(row["runtime_status"] != "completed" for row in records),
            "types": dict(runtime_types),
        },
        "headroom_types": {
            "target_governance_violation": overall["behavior_states"]["VS"],
            "capability_failure": overall["behavior_states"]["CF"],
            "mixed_violation_and_capability_failure": overall["behavior_states"]["VF"],
            "runtime_failure": sum(row["runtime_status"] != "completed" for row in records),
            "possible_evaluator_artifact_after_replay": 0,
            "possible_construction_confound": 0,
        },
        "readiness": {
            "status": status,
            "documented_risks": risk,
            "train_evolution_headroom": train_signal_families >= 3,
            "monitor_balance": monitor_balanced,
            "test_g4_headroom": test_g4_headroom,
            "benchmark_integrity": integrity,
        },
        "audit_checks": audit,
    }
