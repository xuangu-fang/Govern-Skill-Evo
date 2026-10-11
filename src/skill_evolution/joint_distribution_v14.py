"""Pure matched-monitor measurement for Autonomous GSE v0.14 Phase 3."""

from __future__ import annotations

import copy
from collections import defaultdict
from typing import Any

from src.skill_evolution.two_dimensional_gate import classify_state

STATE_CODES = ("CS", "CF", "VS", "VF")
STATE_NAMES = {
    "CS": "compliant_success",
    "CF": "compliant_failure",
    "VS": "violating_success",
    "VF": "violating_failure",
}
STATE_CODE_BY_NAME = {name: code for code, name in STATE_NAMES.items()}


class JointDistributionContractError(ValueError):
    """Raised when Monitor results cannot support matched measurement."""


def state_code(task_success: bool, compliant: bool) -> str:
    if not isinstance(task_success, bool) or not isinstance(compliant, bool):
        raise JointDistributionContractError("Task Success and Compliance must be boolean.")
    return STATE_CODE_BY_NAME[classify_state(task_success, compliant).value]


def _lineage_key(row: dict[str, Any]) -> tuple[str, str, int, int]:
    return (
        row.get("domain"), str(row.get("task_id")),
        row.get("rollout_index"), row.get("rollout_seed"),
    )


def distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise JointDistributionContractError("Cannot measure an empty Monitor result.")
    counts = {code: 0 for code in STATE_CODES}
    for row in rows:
        code = state_code(row.get("task_success"), row.get("compliant"))
        if row.get("state") != STATE_NAMES[code] or row.get("state_code") != code:
            raise JointDistributionContractError("Monitor row state does not match its binary outcomes.")
        counts[code] += 1
    total = len(rows)
    probabilities = {code: counts[code] / total for code in STATE_CODES}
    if abs(sum(probabilities.values()) - 1.0) > 1e-12:
        raise JointDistributionContractError("Joint-distribution probabilities do not sum to one.")
    return {
        "total_rollouts": total,
        "counts": counts,
        "probabilities": probabilities,
        "success_rate": probabilities["CS"] + probabilities["VS"],
        "compliance_rate": probabilities["CS"] + probabilities["CF"],
        "cup_rate": probabilities["CS"],
    }


def validate_monitor_result(result: dict[str, Any]) -> None:
    if (
        not isinstance(result, dict)
        or result.get("schema_version") != "autonomous_gse_monitor_result_0.14.0"
        or not isinstance(result.get("campaign_id"), str)
        or result.get("monitor_id") != "fixed_monitor_m"
        or result.get("skill_artifact_contract") != "immutable_identity"
        or result.get("rollouts_per_task") != 3
    ):
        raise JointDistributionContractError("Monitor result identity is invalid.")
    skill = result.get("skill")
    if not isinstance(skill, dict) or set(skill) != {"skill_id", "skill_version", "skill_path"} or any(
        not isinstance(skill.get(field), str) or not skill[field]
        for field in skill
    ):
        raise JointDistributionContractError("Monitor Skill identity is invalid.")
    task_ids, rows = result.get("task_ids"), result.get("rows")
    if (
        not isinstance(task_ids, list) or len(task_ids) != 20
        or len(set(task_ids)) != 20
        or any(
            not isinstance(value, str)
            or value.count(":") != 1
            or value.split(":", 1)[0] not in {"airline", "retail"}
            for value in task_ids
        )
        or not isinstance(rows, list) or len(rows) != 60
    ):
        raise JointDistributionContractError(
            "Monitor result must contain 20 Airline/Retail tasks and 60 rows."
        )
    expected_keys = {
        (domain, task_id, rollout_index)
        for domain_task in task_ids
        for domain, task_id in (domain_task.split(":", 1),)
        for rollout_index in (1, 2, 3)
    }
    actual_keys: set[tuple[str, str, int]] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise JointDistributionContractError("Monitor rows must be mappings.")
        required = {
            "source_id", "domain", "task_id", "rollout_index", "rollout_seed",
            "skill_id", "skill_version", "task_success", "compliant", "state",
            "state_code", "trajectory_artifact_path",
        }
        if set(row) != required:
            raise JointDistributionContractError("Monitor row schema drifted.")
        if row["skill_id"] != skill["skill_id"] or row["skill_version"] != skill["skill_version"]:
            raise JointDistributionContractError("Monitor row Skill lineage drifted.")
        if not isinstance(row["rollout_index"], int) or row["rollout_index"] not in {1, 2, 3}:
            raise JointDistributionContractError("Monitor rollout index is invalid.")
        if not isinstance(row["rollout_seed"], int) or isinstance(row["rollout_seed"], bool):
            raise JointDistributionContractError("Monitor rollout seed is invalid.")
        if (
            not isinstance(row["source_id"], str) or not row["source_id"].strip()
            or not isinstance(row["trajectory_artifact_path"], str)
            or not row["trajectory_artifact_path"].strip()
        ):
            raise JointDistributionContractError("Monitor trajectory lineage is missing.")
        actual_keys.add((row["domain"], str(row["task_id"]), row["rollout_index"]))
    if actual_keys != expected_keys or len(actual_keys) != len(rows):
        raise JointDistributionContractError("Monitor rows do not form a complete K=3 task grid.")
    measured = distribution(rows)
    if result.get("summary") != measured:
        raise JointDistributionContractError("Monitor summary does not match row-level outcomes.")


def build_joint_distribution_report(
    parent_result: dict[str, Any], candidate_result: dict[str, Any],
) -> dict[str, Any]:
    validate_monitor_result(parent_result)
    validate_monitor_result(candidate_result)
    if (
        parent_result["campaign_id"] != candidate_result["campaign_id"]
        or parent_result["monitor_id"] != candidate_result["monitor_id"]
        or parent_result["task_ids"] != candidate_result["task_ids"]
        or parent_result["rollouts_per_task"] != candidate_result["rollouts_per_task"]
    ):
        raise JointDistributionContractError("Parent/Candidate Monitor identities are not matched.")

    parent_by_key = {_lineage_key(row): row for row in parent_result["rows"]}
    candidate_by_key = {_lineage_key(row): row for row in candidate_result["rows"]}
    if len(parent_by_key) != 60 or set(parent_by_key) != set(candidate_by_key):
        raise JointDistributionContractError("Parent/Candidate Monitor row lineage is not matched.")

    transition_counts = {
        before: {after: 0 for after in STATE_CODES} for before in STATE_CODES
    }
    matched_pairs: list[dict[str, Any]] = []
    effects: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for parent_row in parent_result["rows"]:
        key = _lineage_key(parent_row)
        candidate_row = candidate_by_key[key]
        before, after = parent_row["state_code"], candidate_row["state_code"]
        delta_success = int(candidate_row["task_success"]) - int(parent_row["task_success"])
        delta_compliance = int(candidate_row["compliant"]) - int(parent_row["compliant"])
        transition_counts[before][after] += 1
        effects[(parent_row["domain"], str(parent_row["task_id"]))].append(
            (delta_success, delta_compliance)
        )
        matched_pairs.append({
            "domain": parent_row["domain"], "task_id": str(parent_row["task_id"]),
            "rollout_index": parent_row["rollout_index"],
            "rollout_seed": parent_row["rollout_seed"],
            "parent_state": before, "candidate_state": after,
            "delta_success": delta_success, "delta_compliance": delta_compliance,
        })

    transition_total = sum(sum(row.values()) for row in transition_counts.values())
    if transition_total != 60:
        raise JointDistributionContractError("Transition matrix does not contain 60 matched pairs.")
    joint_probabilities = {
        before: {after: count / transition_total for after, count in row.items()}
        for before, row in transition_counts.items()
    }

    task_level_effects = []
    for domain_task in parent_result["task_ids"]:
        domain, task_id = domain_task.split(":", 1)
        values = effects[(domain, task_id)]
        if len(values) != 3:
            raise JointDistributionContractError("Each task must have exactly three matched pairs.")
        task_level_effects.append({
            "domain": domain, "task_id": task_id, "matched_rollouts": 3,
            "mean_delta_success": sum(value[0] for value in values) / 3,
            "mean_delta_compliance": sum(value[1] for value in values) / 3,
        })

    parent_distribution = distribution(parent_result["rows"])
    candidate_distribution = distribution(candidate_result["rows"])
    overall_shift = {
        "delta_success": sum(item["delta_success"] for item in matched_pairs) / 60,
        "delta_compliance": sum(item["delta_compliance"] for item in matched_pairs) / 60,
    }
    expected_success = candidate_distribution["success_rate"] - parent_distribution["success_rate"]
    expected_compliance = candidate_distribution["compliance_rate"] - parent_distribution["compliance_rate"]
    if (
        abs(overall_shift["delta_success"] - expected_success) > 1e-12
        or abs(overall_shift["delta_compliance"] - expected_compliance) > 1e-12
    ):
        raise JointDistributionContractError("Paired shift disagrees with distribution marginals.")

    return {
        "schema_version": "autonomous_gse_joint_distribution_report_0.14.0",
        "campaign_id": parent_result["campaign_id"],
        "monitor_id": parent_result["monitor_id"],
        "parent_skill": copy.deepcopy(parent_result["skill"]),
        "candidate_skill": copy.deepcopy(candidate_result["skill"]),
        "matched_pairs": matched_pairs,
        "parent_distribution": parent_distribution,
        "candidate_distribution": candidate_distribution,
        "transition_matrix": {
            "state_order": list(STATE_CODES),
            "counts": transition_counts,
            "joint_probabilities": joint_probabilities,
            "total_pairs": transition_total,
        },
        "task_level_effects": task_level_effects,
        "overall_shift": overall_shift,
    }
