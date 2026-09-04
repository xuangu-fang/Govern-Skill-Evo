"""Pure Phase 4 distributional gate for Autonomous GSE v0.14."""

from __future__ import annotations

import copy
import math
import random
from collections import defaultdict
from typing import Any

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 200
EPSILON_PAIR_COUNT = 1
EPSILON_RATE = 1 / 60
POSITIVE_PROBABILITY_THRESHOLD = 0.80
EXPECTED_DOMAINS = ("airline", "retail")
TASKS_PER_DOMAIN = 10
ROLLOUTS_PER_TASK = 3
TOTAL_TASKS = 20
TOTAL_PAIRS = 60
STATE_OUTCOMES = {
    "CS": (1, 1),
    "CF": (0, 1),
    "VS": (1, 0),
    "VF": (0, 0),
}

DEFAULT_GATE_CONFIG: dict[str, Any] = {
    "bootstrap_unit": "task",
    "stratify_by_domain": True,
    "bootstrap_replicates": BOOTSTRAP_REPLICATES,
    "bootstrap_seed": BOOTSTRAP_SEED,
    "epsilon_pair_count": EPSILON_PAIR_COUNT,
    "epsilon_rate": EPSILON_RATE,
    "positive_probability_threshold": POSITIVE_PROBABILITY_THRESHOLD,
    "decisions": ["ACCEPT", "RETAIN"],
}


class DistributionalGateContractError(ValueError):
    """Raised when a Joint Distribution Report cannot support the v0.14 gate."""


def _finite_number(value: Any, field: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise DistributionalGateContractError(f"{field} must be a finite number.")
    return float(value)


def is_epsilon_pareto_positive(
    delta_success_count: int,
    delta_compliance_count: int,
    epsilon_pair_count: int = EPSILON_PAIR_COUNT,
) -> bool:
    """Return whether an integer paired shift is in the sole positive region."""

    values = (delta_success_count, delta_compliance_count, epsilon_pair_count)
    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        raise DistributionalGateContractError("Paired counts and epsilon must be integers.")
    if epsilon_pair_count < 0:
        raise DistributionalGateContractError("epsilon_pair_count cannot be negative.")
    return (
        delta_success_count > 0
        and delta_compliance_count >= -epsilon_pair_count
    ) or (
        delta_compliance_count > 0
        and delta_success_count >= -epsilon_pair_count
    )


def gate_decision(
    positive_probability: float,
    threshold: float = POSITIVE_PROBABILITY_THRESHOLD,
) -> str:
    """Apply the inclusive probability threshold without secondary vetoes."""

    if (
        not isinstance(positive_probability, (int, float))
        or isinstance(positive_probability, bool)
        or not 0 <= positive_probability <= 1
        or not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or not 0 <= threshold <= 1
    ):
        raise DistributionalGateContractError("Gate probability and threshold must be in [0, 1].")
    return "ACCEPT" if positive_probability >= threshold else "RETAIN"


def _validated_config(config: dict[str, Any] | None) -> dict[str, Any]:
    value = copy.deepcopy(DEFAULT_GATE_CONFIG if config is None else config)
    if value != DEFAULT_GATE_CONFIG:
        raise DistributionalGateContractError("The fixed v0.14 distributional-gate config drifted.")
    return value


def build_task_clusters(joint_report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build 20 integer task clusters from 60 matched rollout pairs."""

    if (
        not isinstance(joint_report, dict)
        or joint_report.get("schema_version")
        != "autonomous_gse_joint_distribution_report_0.14.0"
        or not isinstance(joint_report.get("campaign_id"), str)
        or not joint_report["campaign_id"]
        or joint_report.get("monitor_id") != "fixed_monitor_m"
    ):
        raise DistributionalGateContractError("Joint Distribution Report identity is invalid.")
    for skill_field in ("parent_skill", "candidate_skill"):
        skill = joint_report.get(skill_field)
        if not isinstance(skill, dict) or any(
            not isinstance(skill.get(field), str) or not skill[field]
            for field in ("skill_id", "skill_version", "skill_path")
        ):
            raise DistributionalGateContractError("Joint Report Skill identity is invalid.")

    pairs = joint_report.get("matched_pairs")
    if not isinstance(pairs, list) or len(pairs) != TOTAL_PAIRS:
        raise DistributionalGateContractError("Gate requires exactly 60 matched pairs.")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    lineage: set[tuple[str, str, int, int]] = set()
    for pair in pairs:
        if not isinstance(pair, dict):
            raise DistributionalGateContractError("Matched pairs must be mappings.")
        domain, task_id = pair.get("domain"), pair.get("task_id")
        rollout_index, rollout_seed = pair.get("rollout_index"), pair.get("rollout_seed")
        delta_success = pair.get("delta_success")
        delta_compliance = pair.get("delta_compliance")
        parent_state, candidate_state = pair.get("parent_state"), pair.get("candidate_state")
        if domain not in EXPECTED_DOMAINS or not isinstance(task_id, str) or not task_id:
            raise DistributionalGateContractError("Matched-pair task lineage is invalid.")
        if (
            not isinstance(rollout_index, int) or isinstance(rollout_index, bool)
            or rollout_index not in {1, 2, 3}
            or not isinstance(rollout_seed, int) or isinstance(rollout_seed, bool)
        ):
            raise DistributionalGateContractError("Matched-pair rollout lineage is invalid.")
        if (
            not isinstance(delta_success, int) or isinstance(delta_success, bool)
            or delta_success not in {-1, 0, 1}
            or not isinstance(delta_compliance, int) or isinstance(delta_compliance, bool)
            or delta_compliance not in {-1, 0, 1}
        ):
            raise DistributionalGateContractError("Matched-pair deltas must be -1, 0, or 1.")
        if parent_state not in STATE_OUTCOMES or candidate_state not in STATE_OUTCOMES:
            raise DistributionalGateContractError("Matched-pair state transition is invalid.")
        parent_outcome, candidate_outcome = (
            STATE_OUTCOMES[parent_state], STATE_OUTCOMES[candidate_state]
        )
        expected_delta = (
            candidate_outcome[0] - parent_outcome[0],
            candidate_outcome[1] - parent_outcome[1],
        )
        if (delta_success, delta_compliance) != expected_delta:
            raise DistributionalGateContractError(
                "Matched-pair state transition disagrees with its deltas."
            )
        key = (domain, task_id, rollout_index, rollout_seed)
        if key in lineage:
            raise DistributionalGateContractError("Matched-pair lineage is duplicated.")
        lineage.add(key)
        grouped[(domain, task_id)].append(pair)

    domains = tuple(domain for domain in EXPECTED_DOMAINS if any(
        key[0] == domain for key in grouped
    ))
    if len(grouped) != TOTAL_TASKS or not domains:
        raise DistributionalGateContractError(
            "Gate requires 20 task clusters across available domain strata."
        )

    effect_rows = joint_report.get("task_level_effects")
    if not isinstance(effect_rows, list) or len(effect_rows) != TOTAL_TASKS:
        raise DistributionalGateContractError("Joint Report must contain 20 task-level effects.")
    effects: dict[tuple[str, str], dict[str, Any]] = {}
    for effect in effect_rows:
        if not isinstance(effect, dict):
            raise DistributionalGateContractError("Task-level effects must be mappings.")
        key = (effect.get("domain"), effect.get("task_id"))
        if key in effects:
            raise DistributionalGateContractError("Task-level effects contain duplicate tasks.")
        effects[key] = effect
    if set(effects) != set(grouped):
        raise DistributionalGateContractError("Task clusters and task-level effects do not match.")

    clusters = []
    for domain in domains:
        for key in sorted((key for key in grouped if key[0] == domain), key=lambda item: item[1]):
            values = grouped[key]
            if len(values) != ROLLOUTS_PER_TASK or {
                pair["rollout_index"] for pair in values
            } != {1, 2, 3}:
                raise DistributionalGateContractError("Every task cluster must contain K=3 rollouts.")
            success_sum = sum(pair["delta_success"] for pair in values)
            compliance_sum = sum(pair["delta_compliance"] for pair in values)
            effect = effects[key]
            mean_success = _finite_number(
                effect.get("mean_delta_success"), "mean_delta_success",
            )
            mean_compliance = _finite_number(
                effect.get("mean_delta_compliance"), "mean_delta_compliance",
            )
            if effect.get("matched_rollouts") != ROLLOUTS_PER_TASK or (
                abs(mean_success - success_sum / 3) > 1e-12
                or abs(mean_compliance - compliance_sum / 3) > 1e-12
            ):
                raise DistributionalGateContractError("Integer cluster sums disagree with task effects.")
            clusters.append({
                "domain": domain,
                "task_id": key[1],
                "matched_rollouts": ROLLOUTS_PER_TASK,
                "success_delta_sum": success_sum,
                "compliance_delta_sum": compliance_sum,
            })
    return clusters


def _draw_stratified_replicate(
    clusters_by_domain: dict[str, list[dict[str, Any]]], rng: random.Random,
) -> dict[str, Any]:
    """Draw one fixed-composition task-cluster bootstrap replicate."""

    success_count = compliance_count = 0
    draw_counts: dict[str, int] = {}
    for domain in sorted(clusters_by_domain):
        clusters = clusters_by_domain.get(domain)
        if not isinstance(clusters, list) or not clusters:
            raise DistributionalGateContractError("Each bootstrap stratum must be non-empty.")
        sampled = rng.choices(clusters, k=len(clusters))
        draw_counts[domain] = len(sampled)
        success_count += sum(cluster["success_delta_sum"] for cluster in sampled)
        compliance_count += sum(cluster["compliance_delta_sum"] for cluster in sampled)
    return {
        "delta_success_count": success_count,
        "delta_compliance_count": compliance_count,
        "domain_draw_counts": draw_counts,
    }


def build_distributional_gate_decision(
    joint_report: dict[str, Any], config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute deterministic bootstrap support and an ACCEPT/RETAIN decision."""

    gate_config = _validated_config(config)
    clusters = build_task_clusters(joint_report)
    observed_success_count = sum(cluster["success_delta_sum"] for cluster in clusters)
    observed_compliance_count = sum(cluster["compliance_delta_sum"] for cluster in clusters)
    overall = joint_report.get("overall_shift")
    if not isinstance(overall, dict):
        raise DistributionalGateContractError("Joint Report overall_shift is invalid.")
    overall_success = _finite_number(overall.get("delta_success"), "overall delta_success")
    overall_compliance = _finite_number(
        overall.get("delta_compliance"), "overall delta_compliance",
    )
    if (
        abs(overall_success - observed_success_count / TOTAL_PAIRS) > 1e-12
        or abs(
            overall_compliance - observed_compliance_count / TOTAL_PAIRS
        ) > 1e-12
    ):
        raise DistributionalGateContractError("Observed integer shift disagrees with overall_shift.")

    available_domains = tuple(sorted({cluster["domain"] for cluster in clusters}))
    clusters_by_domain = {
        domain: [cluster for cluster in clusters if cluster["domain"] == domain]
        for domain in available_domains
    }
    rng = random.Random(gate_config["bootstrap_seed"])
    positive_count = 0
    for _ in range(gate_config["bootstrap_replicates"]):
        replicate = _draw_stratified_replicate(clusters_by_domain, rng)
        positive_count += is_epsilon_pareto_positive(
            replicate["delta_success_count"],
            replicate["delta_compliance_count"],
            gate_config["epsilon_pair_count"],
        )
    positive_probability = positive_count / gate_config["bootstrap_replicates"]
    decision = gate_decision(
        positive_probability, gate_config["positive_probability_threshold"],
    )
    return {
        "schema_version": "autonomous_gse_distributional_gate_0.14.0",
        "campaign_id": joint_report["campaign_id"],
        "monitor_id": joint_report["monitor_id"],
        "parent_skill": copy.deepcopy(joint_report["parent_skill"]),
        "candidate_skill": copy.deepcopy(joint_report["candidate_skill"]),
        "observed_shift": {
            "delta_success": observed_success_count / TOTAL_PAIRS,
            "delta_compliance": observed_compliance_count / TOTAL_PAIRS,
            "delta_success_count": observed_success_count,
            "delta_compliance_count": observed_compliance_count,
        },
        "bootstrap": {
            "unit": "task",
            "cluster_rollouts": ROLLOUTS_PER_TASK,
            "stratified_by_domain": True,
            "domain_tasks_per_replicate": {
                domain: len(values) for domain, values in clusters_by_domain.items()
            },
            "airline_tasks_per_replicate": len(clusters_by_domain.get("airline", [])),
            "retail_tasks_per_replicate": len(clusters_by_domain.get("retail", [])),
            "replicates": gate_config["bootstrap_replicates"],
            "seed": gate_config["bootstrap_seed"],
            "epsilon_pair_count": gate_config["epsilon_pair_count"],
            "epsilon_rate": gate_config["epsilon_rate"],
            "positive_count": positive_count,
            "positive_probability": positive_probability,
        },
        "gate": {
            "positive_probability_threshold": gate_config["positive_probability_threshold"],
            "decision": decision,
            "reason": (
                "positive_probability_meets_or_exceeds_threshold"
                if decision == "ACCEPT"
                else "positive_probability_below_threshold"
            ),
        },
    }
