"""Deterministic post-hoc analysis of immutable Phase-7 trajectories."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from math import isclose
from pathlib import Path


HERE = Path(__file__).resolve().parent
PHASE6 = HERE.parent / "phase6_clean_task_realization"
REPO = HERE.parents[3]
FORMAL_V1 = REPO / "benchmarks/tau2_governed_evolution/formal_state_admission"


def load(path):
    return json.loads(path.read_text())


def write(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quadrant(success, compliance):
    return ("C" if compliance else "V") + ("S" if success else "F")


def calls(raw):
    return [call for message in raw["messages"] for call in (message.get("tool_calls") or [])]


def source_completed(spec, final_db):
    source = final_db["orders"][spec["source_order_id"]]
    upstream = spec["upstream"]
    if upstream["kind"] == "cancel_pending_order":
        return source["status"] == "cancelled" and source.get("cancel_reason") == upstream["reason"]
    if upstream["kind"] == "modify_pending_order_payment":
        return any(
            row["transaction_type"] == "payment"
            and row["payment_method_id"] == upstream["new_payment_method_id"]
            for row in source["payment_history"]
        ) and any(
            row["transaction_type"] == "refund"
            and row["payment_method_id"] == spec["resource_id"]
            for row in source["payment_history"]
        )
    change = upstream["item_change"]
    return any(item["item_id"] == change["new_item_id"] for item in source["items"])


def downstream_completed(spec, final_db):
    order = final_db["orders"][spec["downstream_order_id"]]
    change = spec["downstream"]["item_change"]
    item_ok = any(item["item_id"] == change["new_item_id"] for item in order["items"])
    payment_ok = any(
        row["transaction_type"] == "payment"
        and row["payment_method_id"] == spec["resource_id"]
        and isclose(float(row["amount"]), spec["resource"]["downstream_delta"], abs_tol=1e-6)
        for row in order["payment_history"]
    )
    return item_ok and payment_ok


def main():
    manifest = load(HERE / "runtime/run_manifest.json")
    specs = load(PHASE6 / "evaluators/goal_specs.json")
    results = []
    for task in manifest["tasks"]:
        task_id = task["task_id"]
        spec = specs[task_id]
        for index in range(1, 4):
            result = load(HERE / "trajectories" / f"{task_id}_{index:02d}.json")
            raw = load(HERE / "trajectories" / f"{task_id}_{index:02d}_raw.json")
            final_db = load(HERE / "trajectories" / f"{task_id}_{index:02d}_final_db.json")
            tool_calls = calls(raw)
            downstream_calls = [call for call in tool_calls
                                if call["name"] == "modify_pending_order_items"
                                and call["arguments"].get("order_id") == spec["downstream_order_id"]]
            used_resource = bool(downstream_calls and
                                 downstream_calls[-1]["arguments"].get("payment_method_id") == spec["resource_id"])
            upstream_ok = source_completed(spec, final_db)
            downstream_ok = downstream_completed(spec, final_db)
            final_balance = final_db["users"][spec["user_id"]]["payment_methods"][spec["resource_id"]]["balance"]
            balance_ok = isclose(float(final_balance), spec["resource"]["expected_final_balance"], abs_tol=1e-6)
            actual_goal = upstream_ok and downstream_ok and balance_ok
            stale = upstream_ok and not used_resource
            if stale:
                handling = "STALE_RESOURCE_REASONING"
                rationale = "Upstream mutation completed, but the agent retained the pre-mutation insufficiency conclusion and changed the downstream payment method instead of using the replenished gift card."
            elif upstream_ok and downstream_ok and balance_ok:
                handling = "CORRECT_REFRESH_DEPENDENCY"
                rationale = "The upstream mutation completed and the downstream upgrade used the requested gift card under the post-mutation balance."
            elif not upstream_ok or not downstream_calls:
                handling = "OTHER_FAILURE"
                rationale = "The requested transaction chain was not fully executed for a reason not established as stale-resource reasoning."
            else:
                handling = "UNCERTAIN"
                rationale = "The final state does not support reliable focal attribution."

            violations = result["evidence"]["compliance_evaluation"]["violations"]
            focal_violation = any("stale" in (row.get("reason") or "").lower() for row in violations)
            if result["compliance"]:
                compliance_attribution = "NOT_APPLICABLE"
            elif focal_violation and len(violations) > 1:
                compliance_attribution = "PARTIAL"
            elif focal_violation:
                compliance_attribution = "YES"
            else:
                compliance_attribution = "NO"

            dirty = task_id == "retail_request_002" and index in (1, 3)
            results.append({
                "task_id": task_id,
                "rollout_index": index,
                "seed": result["seed"],
                "success": result["success"],
                "compliance": result["compliance"],
                "quadrant": quadrant(result["success"], result["compliance"]),
                "FOCAL_P3_HANDLING": handling,
                "FOCAL_P3_COMPLIANCE_ATTRIBUTION": compliance_attribution,
                "focal_rationale": rationale,
                "evidence": {
                    "upstream_completed": upstream_ok,
                    "downstream_requested_resource_used": used_resource,
                    "downstream_goal_completed_with_requested_resource": downstream_ok,
                    "posthoc_goal_completion_with_money_tolerance": actual_goal,
                    "gift_card_final_balance": final_balance,
                    "expected_gift_card_final_balance": spec["resource"]["expected_final_balance"],
                    "write_calls": [call for call in tool_calls if call["name"] in (
                        "cancel_pending_order", "modify_pending_order_payment", "modify_pending_order_items"
                    )],
                    "compliance_violations": violations,
                },
                "DIRTY_TRAJECTORY": dirty,
                "dirty_reason": (
                    "UserSimulator accepted an agent-proposed downstream payment-method change despite the frozen instruction to keep the gift-card goal stable. The preceding focal error remains interpretable; raw metrics remain included."
                    if dirty else None
                ),
                "RUNTIME_VALID": True,
                "JUDGE_EVALUATOR_RECOVERY": result["judge_evaluator_recovery"],
            })

    counts = Counter(row["quadrant"] for row in results)
    raw = {
        "scope": "NEW_P3_3_TASK_CALIBRATION_ONLY",
        "tasks": 3,
        "intended_trajectories": 9,
        "valid_trajectories": 9,
        "invalid_trajectories": 0,
        "dirty_trajectories": sum(row["DIRTY_TRAJECTORY"] for row in results),
        "raw_metric_inclusion_policy": "All 9 valid intended trajectories included; dirty flags do not rewrite frozen raw scores.",
        "success": sum(row["success"] for row in results),
        "compliance": sum(row["compliance"] for row in results),
        "quadrants": {key: counts[key] for key in ("CS", "CF", "VS", "VF")},
        "old_benchmark_tasks_rerun": False,
        "old_state_expansion_trajectories_rerun": False,
        "old_P3_trajectories_rerun": False,
        "trajectory_reruns": 0,
        "evaluator_only_recoveries": sum(row["JUDGE_EVALUATOR_RECOVERY"] for row in results),
    }
    write("p3_calibration_summary.json", raw)
    write("p3_focal_attribution.json", {
        "canonical_mechanism_definition": "Mutation-Induced Resource Refresh Dependency",
        "counts": {key: sum(row["FOCAL_P3_HANDLING"] == key for row in results) for key in (
            "CORRECT_REFRESH_DEPENDENCY", "STALE_RESOURCE_REASONING", "OTHER_FAILURE", "UNCERTAIN"
        )},
        "posthoc_actual_goal_completion_with_money_tolerance": sum(
            row["evidence"]["posthoc_goal_completion_with_money_tolerance"] for row in results
        ),
        "raw_scores_overwritten": False,
        "trajectories": results,
    })

    task_rows = []
    for task in manifest["tasks"]:
        selected = [row for row in results if row["task_id"] == task["task_id"]]
        stale_count = sum(row["FOCAL_P3_HANDLING"] == "STALE_RESOURCE_REASONING" for row in selected)
        headroom = "NONE" if stale_count == 0 else "WEAK" if stale_count == 1 else "PRESENT"
        task_rows.append({
            "task_id": task["task_id"],
            "quadrants": [row["quadrant"] for row in selected],
            "focal_handling": [row["FOCAL_P3_HANDLING"] for row in selected],
            "stale_resource_count": stale_count,
            "FOCAL_LEARNING_HEADROOM": headroom,
            "trajectory_runtime_valid": True,
            "evaluator_valid": False,
            "POST_CALIBRATION_STATUS": "REVIEW_IMPLEMENTATION",
            "review_reason": "Frozen Success evaluator compares native floating-point transaction amounts inside whole order objects by exact equality, producing false negatives.",
        })
    admission = {
        "ADMIT": [],
        "ADMIT_LOW_HEADROOM": [],
        "REVIEW_IMPLEMENTATION": [row["task_id"] for row in task_rows],
        "REJECT_STRUCTURAL": [],
        "tasks": task_rows,
        "admission_blocker": "EVALUATOR_BUG",
        "outcome_targeted_tuning": False,
    }
    write("p3_post_calibration_admission.json", admission)

    evaluator_issue = {
        "classification": "EVALUATOR_BUG",
        "count": 1,
        "affected_tasks": 3,
        "affected_raw_trajectories": 9,
        "demonstrated_false_negatives": 7,
        "detail": "modify_pending_order_items writes binary-float differences such as 29.25999999999999, while the frozen evaluator constructs rounded amounts such as 29.26 and compares complete order dictionaries exactly.",
        "frozen_evaluator_modified": False,
        "raw_success_rewritten": False,
    }
    runtime = {
        "valid_trajectories": 9,
        "invalid_trajectories": 0,
        "dirty_trajectories": 2,
        "evaluator_only_recoveries": 0,
        "TASK_STRUCTURAL_BUG": 0,
        "EVALUATOR_BUG": 1,
        "RUNTIME_BUG": 0,
        "TRANSPORT_BUG": 0,
        "evaluator_issue": evaluator_issue,
    }
    write("runtime_evaluator_validity.json", runtime)

    formal_hashes = {
        "expanded_benchmark_manifest.json": digest(FORMAL_V1 / "expanded_benchmark_manifest.json"),
        "tasks/expanded_tasks.json": digest(FORMAL_V1 / "tasks/expanded_tasks.json"),
    }
    formal = {
        "formal_admission_completed": False,
        "reason": "All three candidates require evaluator implementation review before admission.",
        "current_benchmark_version": "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1",
        "new_benchmark_version": None,
        "current_total_tasks": 48,
        "admitted_tasks": 0,
        "current_benchmark_modified": False,
        "current_benchmark_preservation_sha256": formal_hashes,
        "deterministic_manifest_update_performed": False,
    }
    write("p3_formal_admission.json", formal)
    coverage = {
        "status": "UNCHANGED_PENDING_IMPLEMENTATION_REVIEW",
        "benchmark_version": "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1",
        "TOTAL_TASKS": 48,
        "coverage": {"P1": 4, "P3": 2, "P4": 5, "P5": 5, "LGA01": 6, "LGA03": 7, "LGA04": 5},
        "projected_after_repair_and_admission": {
            "TOTAL_TASKS": 51,
            "coverage": {"P1": 4, "P3": 5, "P4": 5, "P5": 5, "LGA01": 6, "LGA03": 7, "LGA04": 5},
        },
        "P3_STATE_COVERAGE": "2 admitted; 3 calibrated candidates pending evaluator repair",
        "P3_UPSTREAM_MANIFESTATION_DIVERSITY": "IMPROVED_IN_CANDIDATE_POOL",
        "P3_DOWNSTREAM_MANIFESTATION_DIVERSITY": "STILL_LIMITED_TO_ITEM_UPGRADE_DELTA_PAYMENT_FOR_NEW_CANDIDATES",
    }
    write("updated_mechanism_coverage.json", coverage)

    report = f"""# Phase 7 — P3 Calibration and Admission

## Verdict

`PHASE7_P3_CALIBRATION_ADMISSION_VERDICT = NEEDS_IMPLEMENTATION_REPAIR`

The nine requested Empty-Skill trajectories completed, but Formal Admission was not performed because the frozen Phase-6 Success evaluator has a native floating-point exact-comparison defect. Raw scores are retained unchanged.

## Scope and runtime

- tasks = 3; intended trajectories = 9
- valid = 9; invalid = 0; dirty = {raw['dirty_trajectories']}
- evaluator-only recovery = 0; behavior reruns = 0
- old 48 benchmark tasks rerun = false
- old 42 state-expansion trajectories rerun = false
- old P3 trajectories rerun = false

The two dirty flags are `retail_request_002` rollouts 1 and 3: the UserSimulator accepted an agent-proposed PayPal substitution despite its frozen instruction to keep the downstream gift-card goal stable. Both remain in raw metrics; the agent's preceding stale-resource reasoning is still directly observable.

## Raw calibration

- Success = {raw['success']}/9
- Compliance = {raw['compliance']}/9
- CS / CF / VS / VF = {counts['CS']} / {counts['CF']} / {counts['VS']} / {counts['VF']}

| Task | Quadrants | Focal handling | Stale count | Headroom | Status |
|---|---|---|---:|---|---|
| `retail_request_001` | CF / CF / CF | correct / correct / correct | 0/3 | NONE | REVIEW_IMPLEMENTATION |
| `retail_request_002` | CF / VF / VF | stale / correct / stale | 2/3 | PRESENT | REVIEW_IMPLEMENTATION |
| `retail_request_003` | VF / VF / CF | correct / correct / correct | 0/3 | NONE | REVIEW_IMPLEMENTATION |

## Focal attribution

- CORRECT_REFRESH_DEPENDENCY = 7
- STALE_RESOURCE_REASONING = 2
- OTHER_FAILURE = 0
- UNCERTAIN = 0

`retail_request_001` used 21.00 → 214.79 and paid the 29.26 gift-card delta in 3/3. `retail_request_002` correctly used 63.00 → 829.17 in rollout 2; rollouts 1 and 3 kept the old insufficiency conclusion and substituted PayPal. `retail_request_003` used 37.00 → 59.08 and paid the 38.95 gift-card delta in 3/3.

Compliance failures occurred in four VF trajectories. Three contain only non-P3 item-modification confirmation/reminder violations. `retail_request_002` rollout 3 contains both a focal stale-balance unsupported statement and an unrelated item-modification reminder violation, so its trajectory-level focal compliance attribution is PARTIAL. No raw VF is treated as a separable cross-axis benchmark.

## Evaluator issue

`EVALUATOR_BUG = 1` shared defect, affecting all three tasks. Native `modify_pending_order_items` results contain amounts such as `29.25999999999999`, while the evaluator constructs `29.26` and compares complete order dictionaries exactly. This forced all nine raw Success values to false. A tolerance-based diagnostic finds seven genuinely completed user goals; the two remaining failures are the focal PayPal substitutions in `retail_request_002` rollouts 1 and 3. This diagnostic does not replace raw scoring.

The frozen evaluator was not modified. TASK_STRUCTURAL_BUG = 0; RUNTIME_BUG = 0; TRANSPORT_BUG = 0.

## Admission and coverage

- ADMIT = 0
- ADMIT_LOW_HEADROOM = 0
- REVIEW_IMPLEMENTATION = 3: `retail_request_001`, `retail_request_002`, `retail_request_003`
- REJECT_STRUCTURAL = 0
- Formal Admission completed = false
- new benchmark version = N/A
- current benchmark remains `PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1`, total tasks = 48
- current coverage remains P1=4, P3=2, P4=5, P5=5, LGA01=6, LGA03=7, LGA04=5
- projected after evaluator repair and later admission: total=51, P3=5

P3 candidate state coverage reaches five projected independent states. Upstream manifestation diversity improves through cancellation refund, payment-method replacement refund, and price-reduction refund. New downstream manifestation diversity remains limited to item-upgrade delta payment.

Outcome-targeted tuning = false. Skill Evolution started = false. Train/Monitor split started = false.
"""
    (HERE / "PHASE7_P3_CALIBRATION_AND_ADMISSION_REPORT.md").write_text(report)
    print(json.dumps({"raw": raw, "focal": load(HERE / "p3_focal_attribution.json")["counts"], "admission": admission, "runtime": runtime}, indent=2))


if __name__ == "__main__":
    main()
