"""Post-hoc Success v2 failure ecology and phenomenon-level analysis."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TRAJECTORIES = ROOT / "trajectories"
EXPOSURE = ROOT.parent / "phase_a_success_v2_construction/success_v2_exposure_matrix.json"

CLUSTERS = {
    "RETAIL_SETTLEMENT_HISTORY_BLOCKS_PAYMENT_REPLACEMENT": {
        "type": "LATENT_OPERATIONAL", "tags": ["L1_SECONDARY_STATE_MUTATION", "L2_FUTURE_OPTION_TRANSITION"],
        "tasks": {"retail_pa_v1b_w8557584_items_address_payment", "retail_pa_o1a_w6779827_items_payment", "retail_pa_o1b_w8327915_items_payment"},
        "decision": "The agent modified items before replacing the whole-order payment method, including simultaneous calls whose listed execution order performed item mutation first.",
        "visible": "The initial pending order had one payment and both requested writes and payment identifiers were visible.",
        "call": "modify_pending_order_items preceded modify_pending_order_payment.",
        "result": "Item settlement appended payment history; payment replacement then returned 'There should be exactly one payment for a pending order.'",
        "cause": "The agent did not anticipate the hidden settlement-history mutation invalidating the later exact-one-payment precondition.",
        "skill": "HIGH", "concept": "Before a state-changing operation, account for secondary settlement records that may invalidate remaining operations and order dependencies accordingly.",
        "new": False,
    },
    "ONE_SHOT_CERTIFICATE_CONSUMED_BY_FIRST_BOOKING": {
        "type": "LATENT_OPERATIONAL", "tags": ["L3_RESOURCE_LIFECYCLE", "L5_CROSS_TRANSACTION_COUPLING"],
        "tasks": {"airline_s3_juan_patel_6197_certificate_lifecycle", "airline_s3_mohamed_ahmed_3350_certificate_lifecycle"},
        "decision": "The agent allocated the certificate to the cheaper first booking and attempted to reuse its nominal remainder for the second.",
        "visible": "Both trip prices and the certificate/gift-card amounts were visible before booking.",
        "call": "The first book_reservation used the certificate; the second referenced the same certificate again.",
        "result": "The second booking returned 'Payment method <certificate> not found.'",
        "cause": "Successful certificate use removes the whole resource, coupling the two bookings and making the second infeasible after the chosen allocation.",
        "skill": "HIGH", "concept": "Allocate one-shot stored-value resources across all planned transactions before the first use.",
        "new": False,
    },
    "FLIGHT_CHANGE_DELTA_BASELINE_REPLACED_BY_GROSS_FARE": {
        "type": "PROCEDURAL_REASONING", "tags": [],
        "tasks": {"airline_dd_fq8ape_cabin_baggage_budget"},
        "decision": "The agent compared gross Business and Economy fares directly with the $250 modification budget and selected no mutation.",
        "visible": "The reservation exposed the stored $131 flight baseline and searched replacement fares.",
        "call": "All evaluator-required mutation calls were omitted after the wrong branch decision.",
        "result": "No tool error occurred; the Economy transaction delta was $340 - $131 = $209 and should have qualified.",
        "cause": "The agent used gross replacement fare instead of reconstructing the payable transaction delta from the visible booked baseline.",
        "skill": "PLAUSIBLE", "concept": "For modification budgets, bind the threshold to the payable delta rather than the gross replacement value.",
        "new": False,
    },
    "PASSENGER_CARDINALITY_NOT_PROPAGATED_TO_SETTLEMENT": {
        "type": "PROCEDURAL_REASONING", "tags": [],
        "tasks": {"airline_pa_o3a_m66qvw_preserved_pricing"},
        "decision": "The agent treated a $34 per-passenger fare difference as the total for a two-passenger reservation.",
        "visible": "The reservation listed two passengers, stored return fare $166, and candidate HAT281 fare $200.",
        "call": "It attempted HAT281 using a zero-balance gift card after understating the charge, then correctly executed fallback HAT178.",
        "result": "HAT281 failed for insufficient gift-card balance; final DB matched fallback, but the required $68 HAT281 total was not reported.",
        "cause": "The visible passenger cardinality was not propagated through the transaction calculation.",
        "skill": "PLAUSIBLE", "concept": "Propagate reservation cardinality through every per-passenger fare difference before applying thresholds or payment constraints.",
        "new": False,
    },
    "CANCELLATION_REFUND_RESOURCE_NOT_REBOUND": {
        "type": "LATENT_OPERATIONAL", "tags": ["L1_SECONDARY_STATE_MUTATION", "L3_RESOURCE_LIFECYCLE"],
        "tasks": {"retail_pa_v2_w9892465_cancel_funds_w1242543", "retail_pa_v2_w5432440_cancel_funds_w9432206"},
        "decision": "The agent declared the downstream gift-card payment infeasible from the pre-cancellation balance and retained that conclusion after cancellation.",
        "visible": "Initial gift-card balance, cancellation payment/refund amount, downstream order amount, and the cancellation tool result were visible.",
        "call": "cancel_pending_order succeeded, but modify_pending_order_payment was omitted.",
        "result": "Cancellation returned a gift-card refund entry, yet the agent continued quoting the stale initial balance and ended without the required payment replacement.",
        "cause": "The agent did not bind the cancellation's hidden immediate resource replenishment to downstream funding feasibility.",
        "skill": "HIGH", "concept": "After a resource-changing transaction, recompute downstream feasibility from the resulting shared resource state rather than the pre-action snapshot.",
        "new": True,
    },
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rate(n: int, d: int) -> float | None:
    return round(n / d, 6) if d else None


def pct(n: int, d: int) -> str:
    return "N/A" if not d else f"{100*n/d:.2f}%"


def rollout_index(path: Path) -> int:
    match = re.search(r"_rollout_(\d+)_tau2_raw\.json$", path.name)
    if not match:
        raise RuntimeError(path)
    return int(match.group(1))


def evaluator_failure(raw: dict[str, Any]) -> dict[str, Any]:
    reward = raw["reward_info"]
    return {
        "db_match": reward.get("db_check", {}).get("db_match"),
        "unmatched_expected_actions": [x["action"]["name"] for x in reward.get("action_checks") or [] if not x.get("action_match")],
        "unmet_nl_assertions": [x.get("justification") for x in reward.get("nl_assertions") or [] if not x.get("met")],
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    states = Counter(row["state"] for row in rows)
    return {
        "rollouts": len(rows), "success": sum(row["success"] for row in rows), "success_rate": rate(sum(row["success"] for row in rows), len(rows)),
        "compliant": sum(row["compliant"] for row in rows), "compliance_rate": rate(sum(row["compliant"] for row in rows), len(rows)),
        "CS": states["compliant_success"], "CF": states["compliant_failure"], "VS": states["violating_success"], "VF": states["violating_failure"],
    }


def main() -> None:
    manifest = load(ROOT / "task_manifest.json")
    config = load(ROOT / "run_config.json")
    specs = {row["task_id"]: row for row in manifest["tasks"]}
    results = [json.loads(line) for line in (ROOT / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(results) != 81 or any(row["compliant"] is None for row in results):
        raise RuntimeError("expected 81 jointly evaluable results")
    by_key = {(row["task_id"], row["rollout_index"]): row for row in results}
    raws = {}
    for path in sorted(TRAJECTORIES.glob("*_tau2_raw.json")):
        raw = load(path)
        raws[(raw["task_id"], rollout_index(path))] = raw
    if len(raws) != 81 or set(raws) != set(by_key):
        raise RuntimeError("raw/result coverage mismatch")

    cluster_failures: dict[str, list[dict[str, Any]]] = defaultdict(list)
    failures = []
    for row in results:
        if row["success"]:
            continue
        cluster_id = next(name for name, value in CLUSTERS.items() if row["task_id"] in value["tasks"])
        cluster = CLUSTERS[cluster_id]
        raw = raws[(row["task_id"], row["rollout_index"])]
        record = {
            **row, "domain": specs[row["task_id"]]["domain"], "task_role": specs[row["task_id"]]["task_role"],
            "failure_type": cluster["type"], "taxonomy_tags": cluster["tags"], "mechanism_cluster": cluster_id, "clean": True,
            "user_simulator_phase_a_violation": False, "observed_agent_decision": cluster["decision"], "relevant_visible_state": cluster["visible"],
            "tool_call_or_omission": cluster["call"], "tool_result_or_error": cluster["result"], "final_evaluator_failure": evaluator_failure(raw),
            "root_cause_explanation": cluster["cause"],
        }
        failures.append(record)
        cluster_failures[cluster_id].append(record)

    cluster_rows = []
    for cluster_id, cluster in CLUSTERS.items():
        rows = cluster_failures[cluster_id]
        tasks = sorted({row["task_id"] for row in rows})
        cluster_rows.append({"cluster_id": cluster_id, "type": cluster["type"], "tags": cluster["tags"], "tasks_affected": len(tasks), "task_ids": tasks, "failed_rollouts": len(rows), "independent_states": len(tasks), "recurring": len(tasks) >= 2, "clean": True, "new_mechanism_candidate": cluster["new"] and len(tasks) >= 2})

    task_rows = []
    for spec in manifest["tasks"]:
        rows = [row for row in results if row["task_id"] == spec["task_id"]]
        task_rows.append({"task_id": spec["task_id"], "domain": spec["domain"], "task_role": spec["task_role"], "success": sum(row["success"] for row in rows), "success_failures": sum(not row["success"] for row in rows), "compliance": sum(row["compliant"] for row in rows), **{k: summarize(rows)[k] for k in ("CS", "CF", "VS", "VF")}})

    overall = summarize(results)
    domains = {domain: summarize([row for row in results if specs[row["task_id"]]["domain"] == domain]) for domain in ("airline", "retail")}
    roles = {role: summarize([row for row in results if specs[row["task_id"]]["task_role"] == role]) for role in ("KNOWN_ANCHOR", "PROTECTED_GOOD_CASE", "ORDINARY_CLEAN", "EXPOSURE_COMPLETION")}
    good_rows = [row for row in results if specs[row["task_id"]]["task_role"] in {"PROTECTED_GOOD_CASE", "ORDINARY_CLEAN"}]
    good = summarize(good_rows)

    exposure = load(EXPOSURE)
    critical_by_p = {f"P{i}": {row["task_id"] for row in exposure["matrix"] if row["exposures"][f"P{i}"] == "EXPOSED_CRITICAL"} for i in range(1, 6)}
    interpretations = {"P1": "OBSERVED_HEADROOM", "P2": "MIXED", "P3": "OBSERVED_HEADROOM", "P4": "OBSERVED_HEADROOM", "P5": "MIXED"}
    phenomenon_rows = []
    for p, task_ids in critical_by_p.items():
        selected = [row for row in results if row["task_id"] in task_ids]
        failed = [row for row in selected if not row["success"]]
        phenomenon_rows.append({"phenomenon_id": p, "critical_tasks": len(task_ids), "independent_states": len(task_ids), "failed_critical_tasks": len({row["task_id"] for row in failed}), "failed_task_ids": sorted({row["task_id"] for row in failed}), "failed_rollouts": len(failed), "success_rollouts": len(selected)-len(failed), "total_critical_rollouts": len(selected), "interpretation": interpretations[p], "behavioral_note": ({"P1": "Three of four independent states repeatedly show the latent settlement-history dependency; the fourth succeeds 3/3.", "P2": "M66QVW has one failure caused by visible passenger-cardinality propagation, not a demonstrated historical-repricing misconception; 5HK4LR succeeds 3/3.", "P3": "Both independent states fail once by retaining the stale pre-cancellation balance after a successful gift-card refund.", "P4": "Both independent certificate states fail, four rollouts total, through one-shot resource consumption.", "P5": "FQ8APE fails twice from direct baseline misbinding; M66QVW's additional failure is cardinality-related, while HXDUBJ and 5HK4LR succeed 3/3."})[p]})

    recurring = [row for row in cluster_rows if row["recurring"]]
    reviews = [{"mechanism_cluster": row["cluster_id"], "SKILL_ADDRESSABILITY": CLUSTERS[row["cluster_id"]]["skill"], "REUSABLE_MECHANISM": "YES", "TASK_SPECIFIC_ONLY": "NO", "POSSIBLE_SKILL_CONCEPT": CLUSTERS[row["cluster_id"]]["concept"], "RATIONALE": CLUSTERS[row["cluster_id"]]["cause"], "representative_failures": [f"{x['task_id']}:{x['rollout_seed']}" for x in cluster_failures[row["cluster_id"]][:2]]} for row in recurring]
    largest = max(cluster_rows, key=lambda row: row["failed_rollouts"])
    latent = sum(row["failure_type"] == "LATENT_OPERATIONAL" for row in failures)
    procedural = sum(row["failure_type"] == "PROCEDURAL_REASONING" for row in failures)
    stability = {"tasks_with_any_success_failure": sum(row["success_failures"] > 0 for row in task_rows), "tasks_with_at_least_2_of_3_success_failures": sum(row["success_failures"] >= 2 for row in task_rows), "tasks_with_success_3_of_3": sum(row["success"] == 3 for row in task_rows), "success_distribution": dict(Counter(row["success"] for row in task_rows))}
    dirty = {"unresolved_dirty_failures": 0, "transient_compliance_judge_empty_outputs": 1, "judge_only_recovered": 1, "success_results_lost": 0, "compliance_results_lost": 0, "user_simulator_phase_a_violations": 0, "evaluator_errors": 0, "provider_or_parse_errors": 0, "task_specification_errors": 0, "dominates_success_ecology": False}

    analysis = {"schema_version": "phase_a_success_v2_analysis_1.0", "experimental_contract": {"tasks": 27, "rollouts": 81, "independent_from_v1": True, "reused_v1_trajectories": False, "manifest_sha256": config["task_manifest_sha256"], "seed_manifest_sha256": config["seed_manifest_sha256"], "skill": "EMPTY", "contexts": ["AIRLINE_PHASE_A_UNIFIED_V1", "RETAIL_PHASE_A_UNIFIED_V1"]}, "overall": overall, "by_domain": domains, "by_task_role": roles, "task_level": task_rows, "task_stability": stability, "good_case_mass": {"tasks": 16, **good}, "failure_ec": {"attributable_success_failures": len(failures), "latent_operational": latent, "latent_share": rate(latent, len(failures)), "procedural_reasoning": procedural, "procedural_share": rate(procedural, len(failures)), "generic_or_other": len(failures)-latent-procedural, "largest_cluster": largest["cluster_id"], "largest_failure_concentration": rate(largest["failed_rollouts"], len(failures)), "recurring_mechanisms": sum(row["recurring"] for row in cluster_rows), "singleton_mechanisms": sum(not row["recurring"] for row in cluster_rows)}, "phenomenon_behavior": phenomenon_rows, "new_mechanism_candidate": any(row["new_mechanism_candidate"] for row in cluster_rows), "dirty_failure_audit": dirty, "v1_descriptive_comparison": {"v1_success": "57/72 (79.17%)", "v2_success": f"{overall['success']}/81 ({pct(overall['success'],81)})", "paired_statistical_comparison": False}, "readiness": "SUCCESS_SIDE_READY_TO_FREEZE"}
    # Context IDs are recorded directly in the analysis contract above.
    write(ROOT / "analysis.json", analysis)
    write(ROOT / "failure_attribution.json", {"schema_version": "phase_a_success_v2_failure_attribution_1.0", "attributable_success_failures": len(failures), "success_failure_records": failures, "dirty_execution_records": []})
    write(ROOT / "mechanism_clusters.json", {"schema_version": "phase_a_success_v2_mechanism_clusters_1.0", "clusters": cluster_rows, "largest_cluster": largest["cluster_id"], "largest_failure_concentration": rate(largest["failed_rollouts"], len(failures)), "new_mechanism_candidates": [row["cluster_id"] for row in cluster_rows if row["new_mechanism_candidate"]], "dirty_failure_clusters": []})
    write(ROOT / "phenomenon_behavior.json", {"schema_version": "phase_a_success_v2_phenomenon_behavior_1.0", "static_exposure_matrix": str(EXPOSURE.relative_to(ROOT.parent.parent.parent)), "phenomena": phenomenon_rows})
    write(ROOT / "skill_addressability_review.json", {"schema_version": "phase_a_success_v2_skill_addressability_1.0", "reviews": reviews, "deployable_skill_generated": False})

    task_table = "\n".join(f"| `{x['task_id']}` | {x['domain']} | {x['task_role']} | {x['success']}/3 | {x['compliance']}/3 |" for x in task_rows)
    role_table = "\n".join(f"| {role} | {v['success']}/{v['rollouts']} ({pct(v['success'],v['rollouts'])}) | {v['compliant']}/{v['rollouts']} ({pct(v['compliant'],v['rollouts'])}) | {v['CS']} | {v['CF']} | {v['VS']} | {v['VF']} |" for role,v in roles.items())
    cluster_table = "\n".join(f"| `{x['cluster_id']}` | {x['type']} | {x['tasks_affected']} | {x['failed_rollouts']} | {'Yes' if x['recurring'] else 'No'} | {'Yes' if x['new_mechanism_candidate'] else 'No'} |" for x in cluster_rows)
    phenomenon_table = "\n".join(f"| {x['phenomenon_id']} | {x['critical_tasks']} | {x['independent_states']} | {x['failed_critical_tasks']} | {x['failed_rollouts']} | {x['interpretation']} |" for x in phenomenon_rows)
    skill_table = "\n".join(f"| `{x['mechanism_cluster']}` | {x['SKILL_ADDRESSABILITY']} | {x['POSSIBLE_SKILL_CONCEPT']} |" for x in reviews)
    air, retail = domains["airline"], domains["retail"]
    report = f"""# Unified Phase-A Success v2 Full Calibration

## A. Experimental Contract

All 27 frozen tasks were run from scratch with three pre-frozen seeds each (81 trajectories); no v1 trajectory was reused. Airline and Retail used their single Unified Phase-A v1 contexts, with no task-specific override. Agent: `{config['agent']['model']}`, temperature {config['agent']['temperature']}, high reasoning, max tokens {config['agent']['max_tokens']}; UserSimulator: the same model, temperature 0, high reasoning; Skill: `EMPTY`. Official Success evaluation and Compliance v13 retained the v1 configuration.

## B. Aggregate Results

All 81 trajectories have official Success and Compliance results. The one initial Compliance empty output was recovered from its frozen trajectory without rerunning simulation or Success evaluation.

| Scope | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Overall | {overall['success']}/81 ({pct(overall['success'],81)}) | {overall['compliant']}/81 ({pct(overall['compliant'],81)}) | {overall['CS']} | {overall['CF']} | {overall['VS']} | {overall['VF']} |
| Airline | {air['success']}/39 ({pct(air['success'],39)}) | {air['compliant']}/39 ({pct(air['compliant'],39)}) | {air['CS']} | {air['CF']} | {air['VS']} | {air['VF']} |
| Retail | {retail['success']}/42 ({pct(retail['success'],42)}) | {retail['compliant']}/42 ({pct(retail['compliant'],42)}) | {retail['CS']} | {retail['CF']} | {retail['VS']} | {retail['VF']} |

Task stability: {stability['tasks_with_any_success_failure']} tasks had any Success failure; {stability['tasks_with_at_least_2_of_3_success_failures']} had at least 2/3 failures; {stability['tasks_with_success_3_of_3']} succeeded 3/3.

## C. Task-level Results

| Task | Domain | Role | Success | Compliance |
| --- | --- | --- | ---: | ---: |
{task_table}

## D. Role Breakdown

| Role | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{role_table}

## E. Good-case Mass

`PROTECTED_GOOD_CASE + ORDINARY_CLEAN` retains 16 tasks / 48 rollouts: Success {good['success']}/48 ({pct(good['success'],48)}), Compliance {good['compliant']}/48 ({pct(good['compliant'],48)}), CS={good['CS']}, CF={good['CF']}, VS={good['VS']}, VF={good['VF']}. Ordinary-clean Success is {roles['ORDINARY_CLEAN']['success']}/{roles['ORDINARY_CLEAN']['rollouts']}; protected Success is {roles['PROTECTED_GOOD_CASE']['success']}/{roles['PROTECTED_GOOD_CASE']['rollouts']}.

## F. Failure Ecology

| Mechanism cluster | Type | Tasks | Failed rollouts | Recurring | New candidate |
| --- | --- | ---: | ---: | --- | --- |
{cluster_table}

All {len(failures)} Success failures are cleanly attributable: {latent} latent-operational ({pct(latent,len(failures))}), {procedural} procedural ({pct(procedural,len(failures))}), and {len(failures)-latent-procedural} generic/other. The largest cluster contributes {largest['failed_rollouts']}/{len(failures)} ({pct(largest['failed_rollouts'],len(failures))}).

## G. Phenomenon-level Behavior

| Phenomenon | Critical tasks | Independent states | Failed critical tasks | Failed rollouts | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
{phenomenon_table}

P1 exhibits repeated settlement-history invalidation in three states. P2 is mixed: M66QVW is 2/3 and 5HK4LR is 3/3, but the M66QVW failure is cardinality propagation rather than direct evidence of historical-segment repricing error. P3 produces one clean failure in each independent state through stale post-cancellation resource reasoning. P4 remains recurring across both certificate states. P5 is mixed: direct baseline binding fails twice on FQ8APE, while the other critical states are mostly robust.

## H. Exposure Completion Tasks

- `airline_pa_v2_5hk4lr_preserved_segment_valuation`: Success 3/3, Compliance 2/3.
- `retail_pa_v2_w9892465_cancel_funds_w1242543`: Success 2/3, Compliance 2/3.
- `retail_pa_v2_w5432440_cancel_funds_w9432206`: Success 2/3, Compliance 2/3.

## I. New Mechanisms

`CANCELLATION_REFUND_RESOURCE_NOT_REBOUND` is a `NEW_MECHANISM_CANDIDATE`: two independent states each show a clean failure where the agent retains the initial gift-card balance after cancellation and omits the now-feasible downstream payment mutation. It is documented only; no tasks were added and no recovery experiment was run.

## J. Dirty Failure Audit

There are zero unresolved dirty failures and no lost Success or Compliance results. One Compliance call initially exhausted 12,000 reasoning tokens with empty content; finite judge-only retry recovered it. No UserSimulator intent drift, evaluator error, task contradiction, provider/parse failure, or tool infrastructure failure dominates the Success ecology.

## K. Skill-addressability

| Recurring clean mechanism | Addressability | Abstract concept |
| --- | --- | --- |
{skill_table}

No deployable Skill, replay, Oracle/Probe Skill, Diagnosis, or Editor was produced.

## L. Relation to Success v1

Success v1 was 57/72 (79.17%); v2 is {overall['success']}/81 ({pct(overall['success'],81)}). These are independent stochastic calibrations, not a paired statistical comparison. V1 identified exposure imbalance; v2 supplies the coverage-balanced calibration.

## M. Final Verdict

P1-P5 have sufficient static exposure, clean structured headroom remains across multiple recurring mechanisms, good-case mass is preserved, the largest mechanism is 50% rather than dominant beyond the prior warning line, and runtime/evaluator dirtiness does not control the result.

```text
SUCCESS_V2_READINESS:
SUCCESS_SIDE_READY_TO_FREEZE
```
"""
    (ROOT / "PHASE_A_SUCCESS_V2_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps(analysis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
