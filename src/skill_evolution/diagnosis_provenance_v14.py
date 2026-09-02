"""Deterministic provenance aliases for v0.14 Semantic Diagnosis."""

from __future__ import annotations

import copy
from typing import Any


def _trajectory_steps(rollout: dict[str, Any]) -> list[dict[str, Any]]:
    actions = rollout.get("actions")
    if isinstance(actions, list):
        return actions
    trajectory = rollout.get("trajectory")
    if isinstance(trajectory, dict):
        actions = trajectory.get("actions")
        return actions if isinstance(actions, list) else []
    return trajectory if isinstance(trajectory, list) else []


def _violations(rollout: dict[str, Any]) -> list[dict[str, Any]]:
    feedback = rollout.get("process_feedback")
    if not isinstance(feedback, dict):
        return []
    violations = feedback.get("violated_policies")
    return violations if isinstance(violations, list) else []


def _canonical_policy_ids(violation: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key in ("policy_id", "policy_template_id"):
        value = violation.get(key)
        if isinstance(value, str) and value and value not in result:
            result.append(value)
    return result


def build_provenance_alias_context(
    rollouts: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    """Build a stable alias index and an annotated prompt-only rollout copy."""

    presented = copy.deepcopy(tuple(sorted(
        rollouts, key=lambda item: item.get("rollout_index", 0),
    )))
    evidence_aliases: dict[str, dict[str, Any]] = {}
    policy_aliases: dict[str, dict[str, str]] = {}
    policy_alias_by_id: dict[str, str] = {}

    for rollout in presented:
        source_id = rollout.get("source_id")
        steps = sorted(
            _trajectory_steps(rollout),
            key=lambda item: item.get("step", 0) if isinstance(item, dict) else 0,
        )
        for step in steps:
            step_id = step.get("step") if isinstance(step, dict) else None
            if (
                not isinstance(source_id, str) or not source_id
                or not isinstance(step_id, int) or isinstance(step_id, bool) or step_id <= 0
            ):
                continue
            alias = f"E{len(evidence_aliases) + 1:03d}"
            evidence_aliases[alias] = {"source_id": source_id, "step_id": step_id}
            step["evidence_ref"] = alias

        for violation in _violations(rollout):
            if not isinstance(violation, dict):
                continue
            policy_ids = _canonical_policy_ids(violation)
            if not policy_ids:
                continue
            aliases = []
            for policy_id in policy_ids:
                alias = policy_alias_by_id.get(policy_id)
                if alias is None:
                    alias = f"P{len(policy_aliases) + 1:03d}"
                    policy_alias_by_id[policy_id] = alias
                    policy_aliases[alias] = {"policy_id": policy_id}
                aliases.append(alias)
            violation["policy_ref"] = aliases[0]
            if len(aliases) > 1:
                violation["policy_refs"] = aliases

        compliance = rollout.get("compliance_evaluation")
        duplicate_violations = compliance.get("violations") if isinstance(compliance, dict) else None
        if isinstance(duplicate_violations, list):
            for violation in duplicate_violations:
                if not isinstance(violation, dict):
                    continue
                aliases = [
                    policy_alias_by_id[policy_id]
                    for policy_id in _canonical_policy_ids(violation)
                    if policy_id in policy_alias_by_id
                ]
                if aliases:
                    violation["policy_ref"] = aliases[0]
                    if len(aliases) > 1:
                        violation["policy_refs"] = aliases

    return {
        "rollouts": presented,
        "evidence_aliases": evidence_aliases,
        "policy_aliases": policy_aliases,
    }


def resolve_semantic_provenance(
    semantic: dict[str, Any], alias_context: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Resolve validated E/P selections to canonical provenance identifiers."""

    mechanism = semantic["behavioral_mechanism"]
    evidence_aliases = alias_context["evidence_aliases"]
    policy_aliases = alias_context["policy_aliases"]

    def evidence_refs(field: str) -> list[dict[str, Any]]:
        return [
            {
                "alias": alias,
                "source_id": evidence_aliases[alias]["source_id"],
                "step_ids": [evidence_aliases[alias]["step_id"]],
            }
            for alias in dict.fromkeys(mechanism[field])
        ]

    return {
        "support_evidence_refs": evidence_refs("support_evidence_refs"),
        "counterevidence_refs": evidence_refs("counterevidence_refs"),
        "repair_policy_refs": [
            {"alias": alias, "policy_id": policy_aliases[alias]["policy_id"]}
            for alias in dict.fromkeys(semantic["repair_policy_refs"])
        ],
    }
