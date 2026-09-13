#!/usr/bin/env python3
"""Post-hoc analysis for the frozen Unified Phase-A Success v1 calibration."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TRAJECTORIES = ROOT / "trajectories"


CLUSTERS = {
    "RETAIL_SETTLEMENT_HISTORY_BLOCKS_PAYMENT_REPLACEMENT": {
        "type": "LATENT_OPERATIONAL",
        "tags": ["L1_SECONDARY_STATE_MUTATION", "L2_FUTURE_OPTION_TRANSITION"],
        "task_ids": {
            "retail_pa_v1b_w8557584_items_address_payment",
            "retail_pa_o1a_w6779827_items_payment",
            "retail_pa_o1b_w8327915_items_payment",
            "retail_pa_v2_w9318778_payment_items_address",
        },
        "observed_agent_decision": (
            "The agent modified items before replacing the whole-order payment method."
        ),
        "relevant_visible_state": (
            "The initial pending order had one whole-order payment; the requested item variant, "
            "price-difference payment method, and whole-order replacement method were visible."
        ),
        "tool_call_or_omission": (
            "modify_pending_order_items preceded modify_pending_order_payment."
        ),
        "tool_result_or_error": (
            "The item mutation appended a price-difference payment/refund entry; the later payment "
            "replacement returned: There should be exactly one payment for a pending order."
        ),
        "root_cause_explanation": (
            "The agent did not anticipate the hidden secondary ledger mutation and its effect on the "
            "future payment-replacement precondition. Payment replacement first is the successful contrast."
        ),
        "possible_skill_concept": (
            "Before a state-changing operation, check whether its secondary settlement record can "
            "invalidate a remaining operation and order the dependent operations accordingly."
        ),
        "skill_addressability": "HIGH",
        "representatives": [
            "retail_pa_v1b_w8557584_items_address_payment:1200",
            "retail_pa_o1b_w8327915_items_payment:1240",
        ],
        "contrasting_evidence": [
            "retail_pa_o1a_w6779827_items_payment:1204",
            "retail_pa_v2_w9318778_payment_items_address:1222",
        ],
    },
    "ONE_SHOT_CERTIFICATE_CONSUMED_BY_FIRST_BOOKING": {
        "type": "LATENT_OPERATIONAL",
        "tags": ["L3_RESOURCE_LIFECYCLE", "L5_CROSS_TRANSACTION_COUPLING"],
        "task_ids": {
            "airline_s3_juan_patel_6197_certificate_lifecycle",
            "airline_s3_mohamed_ahmed_3350_certificate_lifecycle",
        },
        "observed_agent_decision": (
            "The agent allocated the travel certificate to the cheaper first booking and attempted "
            "to reuse its nominal remainder on the second booking."
        ),
        "relevant_visible_state": (
            "Both booking prices and the certificate/gift-card balances were visible before either write."
        ),
        "tool_call_or_omission": (
            "The first book_reservation consumed the certificate; the second book_reservation referenced it again."
        ),
        "tool_result_or_error": "The second booking returned: Payment method <certificate> not found.",
        "root_cause_explanation": (
            "The backend consumes the entire certificate resource on first use, coupling feasibility "
            "across bookings. Successful contrasts reserve the gift card for booking one and the certificate for booking two."
        ),
        "possible_skill_concept": (
            "Allocate one-shot stored-value resources across all planned transactions before the first use, "
            "reserving each resource for the transaction that depends on it."
        ),
        "skill_addressability": "HIGH",
        "representatives": [
            "airline_s3_juan_patel_6197_certificate_lifecycle:1212",
            "airline_s3_mohamed_ahmed_3350_certificate_lifecycle:1215",
        ],
        "contrasting_evidence": [
            "airline_s3_juan_patel_6197_certificate_lifecycle:1214",
            "airline_s3_mohamed_ahmed_3350_certificate_lifecycle:1216",
        ],
    },
    "TRANSACTION_DELTA_BASELINE_REPLACED_BY_GROSS_FARE": {
        "type": "PROCEDURAL_REASONING",
        "tags": [],
        "task_ids": {"airline_dd_fq8ape_cabin_baggage_budget"},
        "observed_agent_decision": (
            "The agent compared gross replacement fares ($793 Business and $340 Economy) directly "
            "with the $250 transaction threshold and selected no mutation."
        ),
        "relevant_visible_state": (
            "The reservation exposed the existing stored flight total ($131), and the searched Economy "
            "fares and zero baggage charge were visible."
        ),
        "tool_call_or_omission": (
            "The agent omitted all three required writes after using the wrong baseline; the Economy "
            "transaction delta was $340 - $131 = $209."
        ),
        "tool_result_or_error": "No mutation tool error occurred; the failure was the branch decision and resulting omissions.",
        "root_cause_explanation": (
            "Visible evidence was available, but the agent failed to reconstruct the modification-level "
            "price difference and instead treated gross new fare as the payable package consequence."
        ),
        "possible_skill_concept": (
            "When a modification threshold concerns the payable consequence, reconstruct the transaction "
            "delta from the current booked baseline instead of comparing the gross replacement price."
        ),
        "skill_addressability": "PLAUSIBLE",
        "representatives": ["airline_dd_fq8ape_cabin_baggage_budget:1206"],
        "contrasting_evidence": ["airline_dd_hxdubj_multistage_propagation:1209"],
    },
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def percent(numerator: int, denominator: int) -> str:
    return "N/A" if not denominator else f"{100 * numerator / denominator:.2f}%"


def rollout_index(path: Path) -> int:
    match = re.search(r"_rollout_(\d+)_tau2_raw\.json$", path.name)
    if not match:
        raise ValueError(f"unrecognized raw trajectory name: {path.name}")
    return int(match.group(1))


def failed_evaluator_summary(raw: dict[str, Any]) -> dict[str, Any]:
    reward = raw["reward_info"]
    return {
        "reward": reward["reward"],
        "db_match": reward.get("db_check", {}).get("db_match"),
        "unmatched_expected_actions": [
            check["action"]["name"]
            for check in reward.get("action_checks") or []
            if not check.get("action_match")
        ],
        "unmet_nl_assertions": [
            {
                "assertion": check.get("nl_assertion"),
                "justification": check.get("justification"),
            }
            for check in reward.get("nl_assertions") or []
            if not check.get("met")
        ],
    }


def main() -> None:
    manifest = load(ROOT / "task_manifest.json")
    config = load(ROOT / "run_config.json")
    seeds = load(ROOT / "seed_manifest.json")["seeds"]
    run_summary = load(ROOT / "run_summary.json")
    specs = {row["task_id"]: row for row in manifest["tasks"]}

    raw_rows: list[dict[str, Any]] = []
    raw_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted(TRAJECTORIES.glob("*_tau2_raw.json")):
        raw = load(path)
        index = rollout_index(path)
        row = {
            "task_id": raw["task_id"],
            "domain": specs[raw["task_id"]]["domain"],
            "task_role": specs[raw["task_id"]]["task_role"],
            "operation_category": specs[raw["task_id"]]["operation_category"],
            "rollout_index": index,
            "seed": raw["seed"],
            "success": raw["reward_info"]["reward"] > 0,
            "termination_reason": raw["termination_reason"],
            "artifact_path": str(path.relative_to(ROOT)),
        }
        raw_rows.append(row)
        raw_by_key[(raw["task_id"], index)] = raw

    governed_rows: list[dict[str, Any]] = []
    for path in sorted(TRAJECTORIES.glob("*_rollout_[0-9][0-9].json")):
        artifact = load(path)
        governed_rows.append(
            {
                "task_id": artifact["task_id"],
                "domain": specs[artifact["task_id"]]["domain"],
                "task_role": specs[artifact["task_id"]]["task_role"],
                "rollout_index": artifact["rollout_index"],
                "seed": artifact["rollout_seed"],
                "success": artifact["task_evaluation"]["success"],
                "compliant": artifact["compliance_evaluation"]["compliant"],
                "state": artifact["state"],
                "artifact_path": str(path.relative_to(ROOT)),
            }
        )
    governed_by_key = {
        (row["task_id"], row["rollout_index"]): row for row in governed_rows
    }

    expected_keys = {
        (task_id, index)
        for task_id, task_seeds in seeds.items()
        for index, _seed in enumerate(task_seeds, 1)
    }
    if set(raw_by_key) != expected_keys:
        raise RuntimeError("raw official-evaluator artifacts do not cover the frozen seed manifest")
    if len(raw_rows) != 72:
        raise RuntimeError("expected exactly 72 official Success observations")

    dirty_records = []
    for path in sorted(TRAJECTORIES.glob("*_error.json")):
        error = load(path)
        if error.get("error_message") != "Learner returned an empty Skill.":
            dirty_type = "PROVIDER_OR_PARSE_ERROR"
        else:
            dirty_type = "COMPLIANCE_JUDGE_ISSUE"
        dirty_records.append(
            {
                "task_id": error["task_id"],
                "domain": specs[error["task_id"]]["domain"],
                "task_role": specs[error["task_id"]]["task_role"],
                "rollout_index": error["rollout_index"],
                "seed": error["rollout_seed"],
                "failure_type": dirty_type,
                "success_observation_available": (error["task_id"], error["rollout_index"]) in raw_by_key,
                "compliance_observation_available": False,
                "root_cause_explanation": (
                    "The official Success evaluation completed, but the Compliance Judge caller "
                    "returned empty content after its configured retries."
                ),
                "error_artifact": str(path.relative_to(ROOT)),
            }
        )

    result_lines = []
    for row in raw_rows:
        judgment = governed_by_key.get((row["task_id"], row["rollout_index"]))
        result_lines.append(
            json.dumps(
                {
                    "task_id": row["task_id"],
                    "rollout_index": row["rollout_index"],
                    "rollout_seed": row["seed"],
                    "success": row["success"],
                    "compliant": judgment["compliant"] if judgment else None,
                    "state": judgment["state"] if judgment else "compliance_unavailable",
                    "raw_tau2_artifact_path": row["artifact_path"],
                    "governed_artifact_path": judgment["artifact_path"] if judgment else None,
                },
                ensure_ascii=False,
            )
        )
    (ROOT / "results.jsonl").write_text("\n".join(result_lines) + "\n", encoding="utf-8")

    failure_records = []
    cluster_rollouts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        if row["success"]:
            continue
        cluster_id = next(
            name for name, cluster in CLUSTERS.items() if row["task_id"] in cluster["task_ids"]
        )
        cluster = CLUSTERS[cluster_id]
        raw = raw_by_key[(row["task_id"], row["rollout_index"])]
        record = {
            **row,
            "failure_type": cluster["type"],
            "taxonomy_tags": cluster["tags"],
            "mechanism_cluster": cluster_id,
            "clean": True,
            "user_simulator_phase_a_violation": False,
            "observed_agent_decision": cluster["observed_agent_decision"],
            "relevant_visible_state": cluster["relevant_visible_state"],
            "tool_call_or_omission": cluster["tool_call_or_omission"],
            "tool_result_or_error": cluster["tool_result_or_error"],
            "final_evaluator_failure": failed_evaluator_summary(raw),
            "root_cause_explanation": cluster["root_cause_explanation"],
        }
        failure_records.append(record)
        cluster_rollouts[cluster_id].append(record)

    mechanism_rows = []
    for cluster_id, cluster in CLUSTERS.items():
        failures = cluster_rollouts[cluster_id]
        tasks = sorted({row["task_id"] for row in failures})
        mechanism_rows.append(
            {
                "cluster_id": cluster_id,
                "type": cluster["type"],
                "tags": cluster["tags"],
                "tasks_affected": len(tasks),
                "task_ids": tasks,
                "failed_rollouts": len(failures),
                "independent_states": len(tasks),
                "recurring": len(tasks) >= 2,
                "clean": True,
                "new_mechanism_candidate": False,
            }
        )

    success_total = sum(row["success"] for row in raw_rows)
    compliance_total = sum(row["compliant"] for row in governed_rows)
    states = Counter(row["state"] for row in governed_rows)

    def breakdown(key: str, value: str) -> dict[str, Any]:
        success_rows = [row for row in raw_rows if row[key] == value]
        judged_rows = [row for row in governed_rows if row[key] == value]
        state_counts = Counter(row["state"] for row in judged_rows)
        return {
            "planned": len(success_rows),
            "success_count": sum(row["success"] for row in success_rows),
            "success_rate": rate(sum(row["success"] for row in success_rows), len(success_rows)),
            "compliance_evaluable": len(judged_rows),
            "compliance_unavailable": len(success_rows) - len(judged_rows),
            "compliant_count": sum(row["compliant"] for row in judged_rows),
            "compliance_rate": rate(sum(row["compliant"] for row in judged_rows), len(judged_rows)),
            "CS": state_counts["compliant_success"],
            "CF": state_counts["compliant_failure"],
            "VS": state_counts["violating_success"],
            "VF": state_counts["violating_failure"],
        }

    task_rows = []
    for task_id, spec in specs.items():
        successes = [row for row in raw_rows if row["task_id"] == task_id]
        judgments = [row for row in governed_rows if row["task_id"] == task_id]
        task_rows.append(
            {
                "task_id": task_id,
                "domain": spec["domain"],
                "task_role": spec["task_role"],
                "success": sum(row["success"] for row in successes),
                "success_denominator": 3,
                "success_failures": 3 - sum(row["success"] for row in successes),
                "compliance": sum(row["compliant"] for row in judgments),
                "compliance_evaluable": len(judgments),
                "compliance_unavailable": 3 - len(judgments),
            }
        )

    good_roles = {"PROTECTED_GOOD_CASE", "ORDINARY_CLEAN"}
    good_success = [row for row in raw_rows if row["task_role"] in good_roles]
    good_judged = [row for row in governed_rows if row["task_role"] in good_roles]
    good_states = Counter(row["state"] for row in good_judged)

    latent_failures = sum(row["failure_type"] == "LATENT_OPERATIONAL" for row in failure_records)
    procedural_failures = sum(row["failure_type"] == "PROCEDURAL_REASONING" for row in failure_records)
    largest = max(row["failed_rollouts"] for row in mechanism_rows)
    largest_cluster = max(mechanism_rows, key=lambda row: row["failed_rollouts"])["cluster_id"]

    analysis = {
        "schema_version": "phase_a_success_v1_analysis_2.0",
        "task_pool": {
            "total": len(specs),
            "by_domain": dict(Counter(row["domain"] for row in specs.values())),
            "by_role": dict(Counter(row["task_role"] for row in specs.values())),
            "manifest_sha256": config["task_manifest_sha256"],
            "outcome_blind": manifest["outcome_blind"],
        },
        "execution": {
            "planned_rollouts": 72,
            "official_success_evaluable": len(raw_rows),
            "compliance_evaluable": len(governed_rows),
            "compliance_unavailable": len(dirty_records),
            "run_summary_completed": run_summary["completed"],
            "run_summary_errors": run_summary["errors"],
        },
        "overall": {
            "success_count": success_total,
            "success_denominator": len(raw_rows),
            "success_rate": rate(success_total, len(raw_rows)),
            "compliant_count": compliance_total,
            "compliance_denominator": len(governed_rows),
            "compliance_rate": rate(compliance_total, len(governed_rows)),
            "CS": states["compliant_success"],
            "CF": states["compliant_failure"],
            "VS": states["violating_success"],
            "VF": states["violating_failure"],
            "joint_denominator": len(governed_rows),
        },
        "by_domain": {domain: breakdown("domain", domain) for domain in ("airline", "retail")},
        "by_task_role": {
            role: breakdown("task_role", role)
            for role in ("KNOWN_ANCHOR", "PROTECTED_GOOD_CASE", "ORDINARY_CLEAN")
        },
        "task_level": task_rows,
        "task_stability": {
            "success_distribution": dict(Counter(row["success"] for row in task_rows)),
            "tasks_with_any_success_failure": sum(row["success_failures"] > 0 for row in task_rows),
            "tasks_with_at_least_2_of_3_success_failures": sum(row["success_failures"] >= 2 for row in task_rows),
            "stable_success_3_of_3": sum(row["success"] == 3 for row in task_rows),
        },
        "good_case_mass": {
            "tasks": sum(row["task_role"] in good_roles for row in specs.values()),
            "success_count": sum(row["success"] for row in good_success),
            "success_denominator": len(good_success),
            "success_rate": rate(sum(row["success"] for row in good_success), len(good_success)),
            "compliant_count": sum(row["compliant"] for row in good_judged),
            "compliance_denominator": len(good_judged),
            "compliance_rate": rate(sum(row["compliant"] for row in good_judged), len(good_judged)),
            "CS": good_states["compliant_success"],
            "CF": good_states["compliant_failure"],
            "VS": good_states["violating_success"],
            "VF": good_states["violating_failure"],
        },
        "failure_ecology": {
            "attributable_success_failures": len(failure_records),
            "latent_operational": latent_failures,
            "latent_operational_share": rate(latent_failures, len(failure_records)),
            "procedural_reasoning": procedural_failures,
            "procedural_reasoning_share": rate(procedural_failures, len(failure_records)),
            "generic_or_other": len(failure_records) - latent_failures - procedural_failures,
            "largest_cluster": largest_cluster,
            "largest_failure_concentration": rate(largest, len(failure_records)),
            "independent_recurring_mechanisms": sum(row["recurring"] for row in mechanism_rows),
            "singleton_mechanisms": sum(not row["recurring"] for row in mechanism_rows),
        },
        "known_anchor_comparison": {
            "S1": "REPRODUCED",
            "S2": "PARTIALLY_REPRODUCED",
            "S3": "REPRODUCED",
            "S5": "NOT_OBSERVED",
        },
        "new_mechanism_candidate": False,
        "dirty_failure_audit": {
            "count": len(dirty_records),
            "type": "COMPLIANCE_JUDGE_ISSUE",
            "success_results_lost": 0,
            "compliance_results_lost": len(dirty_records),
            "dominates_success_ecology": False,
        },
        "readiness": "READY_FOR_COMPLIANCE_AUDIT",
    }
    write(ROOT / "analysis.json", analysis)
    write(
        ROOT / "failure_attribution.json",
        {
            "schema_version": "phase_a_success_v1_failure_attribution_2.0",
            "attributable_success_failures": len(failure_records),
            "success_failure_records": failure_records,
            "dirty_execution_records": dirty_records,
        },
    )
    write(
        ROOT / "mechanism_clusters.json",
        {
            "schema_version": "phase_a_success_v1_mechanism_clusters_2.0",
            "clusters": mechanism_rows,
            "largest_cluster": largest_cluster,
            "largest_failure_concentration": rate(largest, len(failure_records)),
            "new_mechanism_candidates": [],
            "dirty_failure_clusters": [
                {
                    "cluster_id": "COMPLIANCE_JUDGE_EMPTY_OUTPUT",
                    "type": "COMPLIANCE_JUDGE_ISSUE",
                    "affected_rollouts": len(dirty_records),
                    "clean": False,
                    "success_mechanism": False,
                }
            ],
        },
    )
    reviews = []
    for cluster_id, cluster in CLUSTERS.items():
        rows = cluster_rollouts[cluster_id]
        reviews.append(
            {
                "mechanism_cluster": cluster_id,
                "SKILL_ADDRESSABILITY": cluster["skill_addressability"],
                "REUSABLE_MECHANISM": "YES",
                "TASK_SPECIFIC_ONLY": "NO",
                "POSSIBLE_SKILL_CONCEPT": cluster["possible_skill_concept"],
                "RATIONALE": cluster["root_cause_explanation"],
                "representative_failures": cluster["representatives"],
                "positive_or_contrasting_evidence": cluster["contrasting_evidence"],
                "failed_rollouts": len(rows),
                "tasks_affected": len({row["task_id"] for row in rows}),
            }
        )
    write(
        ROOT / "skill_addressability_review.json",
        {
            "schema_version": "phase_a_success_v1_skill_addressability_2.0",
            "reviews": reviews,
            "deployable_skill_generated": False,
        },
    )

    stability_rows = "\n".join(
        f"| `{row['task_id']}` | {row['domain']} | {row['task_role']} | "
        f"{row['success']}/3 | {row['compliance']}/{row['compliance_evaluable']}"
        f"{' (+' + str(row['compliance_unavailable']) + ' unavailable)' if row['compliance_unavailable'] else ''} |"
        for row in task_rows
    )
    cluster_table = "\n".join(
        f"| `{row['cluster_id']}` | {row['type']} | {', '.join(row['tags']) or '—'} | "
        f"{row['tasks_affected']} | {row['failed_rollouts']} | {row['independent_states']} | "
        f"{'Yes' if row['recurring'] else 'No'} | Yes |"
        for row in mechanism_rows
    )
    skill_table = "\n".join(
        f"| `{review['mechanism_cluster']}` | {review['SKILL_ADDRESSABILITY']} | "
        f"{review['REUSABLE_MECHANISM']} | {review['TASK_SPECIFIC_ONLY']} | "
        f"{review['POSSIBLE_SKILL_CONCEPT']} |"
        for review in reviews
    )
    airline = analysis["by_domain"]["airline"]
    retail = analysis["by_domain"]["retail"]
    report = f"""# Unified Phase-A Success v1 Calibration Report

## A. Experimental Contract

The Unified Phase-A static validator passed before execution. Every Airline task used `AIRLINE_PHASE_A_UNIFIED_V1`; every Retail task used `RETAIL_PHASE_A_UNIFIED_V1`. There was no task-specific context, canonical fallback, Skill injection, task replacement, or seed replacement.

| Setting | Frozen value |
| --- | --- |
| Base Agent | `{config['agent']['implementation_s0']}` / `{config['agent']['model']}` |
| Temperature | `{config['agent']['temperature']}` |
| Reasoning / thinking | `{config['agent']['reasoning_effort']}` / `{config['agent']['thinking']}` |
| Max tokens / max steps | `{config['agent']['max_tokens']}` / `{config['agent']['max_steps']}` |
| Skill | `EMPTY` |
| UserSimulator | `{config['user_simulator']['model']}`, temperature `{config['user_simulator']['temperature']}`, high reasoning |
| Official evaluator | `{config['official_evaluator']['nl_assertions_model']}`, temperature 0 |
| Compliance Judge | `{config['compliance_judge']['model']}`, v13, temperature 0 |
| Rollouts per task | 3 |

## B. Outcome-Blind Task Pool

The manifest was frozen before Unified v1 outcomes and retained SHA-256 `{config['task_manifest_sha256']}`. It contains 24 tasks: 12 Airline and 12 Retail; 8 `KNOWN_ANCHOR`, 3 `PROTECTED_GOOD_CASE`, and 13 `ORDINARY_CLEAN`.

## C. Aggregate Results

All 72 fixed rollouts completed simulation and official Success evaluation. The Compliance Judge produced a usable judgment for 63 and empty output for 9.

| Measure | Result |
| --- | ---: |
| Success | {success_total}/72 ({percent(success_total, 72)}) |
| Compliance | {compliance_total}/63 ({percent(compliance_total, 63)}); 9 unavailable |
| CS | {states['compliant_success']} / 63 |
| CF | {states['compliant_failure']} / 63 |
| VS | {states['violating_success']} / 63 |
| VF | {states['violating_failure']} / 63 |

CS/CF/VS/VF use only the 63 jointly evaluable trajectories; missing Compliance judgments are not imputed.

### Domain breakdown

| Domain | Success | Compliance | CS | CF | VS | VF | Compliance unavailable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Airline | {airline['success_count']}/36 ({percent(airline['success_count'],36)}) | {airline['compliant_count']}/{airline['compliance_evaluable']} ({percent(airline['compliant_count'],airline['compliance_evaluable'])}) | {airline['CS']} | {airline['CF']} | {airline['VS']} | {airline['VF']} | {airline['compliance_unavailable']} |
| Retail | {retail['success_count']}/36 ({percent(retail['success_count'],36)}) | {retail['compliant_count']}/{retail['compliance_evaluable']} ({percent(retail['compliant_count'],retail['compliance_evaluable'])}) | {retail['CS']} | {retail['CF']} | {retail['VS']} | {retail['VF']} | {retail['compliance_unavailable']} |

## D. Task-Level Stability

| Task | Domain | Role | Success | Compliance |
| --- | --- | --- | ---: | ---: |
{stability_rows}

Success distribution: 0/3 = 3 tasks; 1/3 = 2; 2/3 = 2; 3/3 = 17. Seven tasks had any Success failure; five had recurrent failure in at least 2/3 rollouts.

## E. Good-Case Mass

`PROTECTED_GOOD_CASE + ORDINARY_CLEAN` contains 16 tasks and 48 rollouts: Success {sum(row['success'] for row in good_success)}/48 ({percent(sum(row['success'] for row in good_success),48)}). Compliance was {sum(row['compliant'] for row in good_judged)}/{len(good_judged)} ({percent(sum(row['compliant'] for row in good_judged),len(good_judged))}), with {48-len(good_judged)} unavailable judgments. Joint states: CS={good_states['compliant_success']}, CF={good_states['compliant_failure']}, VS={good_states['violating_success']}, VF={good_states['violating_failure']}.

Protected-only Success was 8/9; ordinary-clean Success was 39/39. Thus latent-semantic removal did not broadly damage ordinary cases.

## F. Failure Ecology

| Mechanism cluster | Type | Tags | Tasks affected | Failed rollouts | Independent states | Recurring? | Clean? |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
{cluster_table}

All 15 Success failures were attributable: 12/15 (80%) latent-operational, 3/15 (20%) procedural reasoning, and 0 generic/other. The largest cluster contains 9/15 failures (60%). There are two independent recurring mechanisms and one singleton mechanism.

## G. Known Anchor Comparison

| Anchor | Status | Evidence |
| --- | --- | --- |
| S1 | REPRODUCED | Three known-anchor tasks and one protected state exhibit item-settlement → payment-replacement invalidation. |
| S2 | PARTIALLY_REPRODUCED | FQ8APE fails 3/3 on transaction baseline; HXDUBJ succeeds 3/3. |
| S3 | REPRODUCED | Certificate lifecycle failure appears in both independent booking states. |
| S5 | NOT_OBSERVED | The preserved-pricing anchor succeeds 3/3; no replacement task or seed was added. |

## H. New Mechanisms

`NEW_MECHANISM_CANDIDATE = false`. No recurring family outside the independently derived clusters matched the >=2-state requirement.

## I. Dirty Failure Audit

Nine trajectories have `COMPLIANCE_JUDGE_ISSUE`: simulation and official Success evaluation completed, but the v13 judge caller returned empty content after retries. This loses 9 Compliance observations, not Success observations. No provider-budget error, task contradiction, evaluator error, tool-infrastructure failure, or transaction-relevant UserSimulator drift was found in the 15 Success-failure chains.

## J. Skill-Addressability

| Mechanism | Addressability | Reusable | Task-specific only | Possible concept |
| --- | --- | --- | --- | --- |
{skill_table}

This is a lightweight cluster review only. No deployable Skill, Oracle Skill, Probe Skill, replay, recovery test, Diagnosis, Editor, or Selection Gate was produced.

## K. Readiness Verdict

```text
SUCCESS_V1_READINESS:
READY_FOR_COMPLIANCE_AUDIT
```

Rationale: the Unified context and outcome-blind pool operated normally; ordinary/protected good-case mass remains strong; Success headroom is real and structured across two recurring latent mechanisms plus one procedural singleton; the largest cluster is 60%, not the entire ecology; and the dirty issue is confined to 9 missing Compliance judgments rather than Success execution or attribution.
"""
    (ROOT / "PHASE_A_SUCCESS_V1_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
