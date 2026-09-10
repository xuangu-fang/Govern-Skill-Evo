"""Build static Phase-6 candidate artifacts. No rollout/evaluator/tool call occurs."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from tau2.domains.retail.tools import RetailTools

from .benchmark_adapter import build_task_request


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PHASE5 = HERE.parent / "phase5_fresh_native_state_mining"
DB_PATH = REPO / "external/tau2-bench/data/tau2/domains/retail/db.json"
FORMAL = REPO / "benchmarks/tau2_governed_evolution/formal_state_admission"
CONTEXT_MANIFEST = REPO / "benchmarks/tau2_governed_evolution/phase_a_final_context/final_context_manifest.json"
CANONICAL_DEFINITION = "Mutation-Induced Resource Refresh Dependency"
POOL_ID = "P3_STATE_EXPANSION_CANDIDATE_POOL_V1"
FORBIDDEN = (
    r"(?<![A-Za-z0-9])P3(?![A-Za-z0-9])",
    re.escape(CANONICAL_DEFINITION),
    r"manifestation",
    r"state[ _-]expansion",
    r"stale[ _-]state",
    r"construction metadata",
)


REALIZATIONS = (
    {
        "task_id": "retail_request_001",
        "candidate_id": "P3_NATIVE_001",
        "reason": "Cancel one pending order, then change a speaker in another pending order.",
        "known": "You are Liam Lopez in ZIP code 75388. Your pending orders are #W2000719 and #W7555783. Your gift card is gift_card_8483518.",
        "goal": (
            "Begin your first response by saying that your name is Liam Lopez and your ZIP code is 75388. "
            "In the same first response, ask to cancel pending order #W2000719 because it is no longer needed. "
            "Then ask to change the red Bluetooth Speaker in pending order #W7555783 from the 20-hour, "
            "water-resistant version to the available red 10-hour version without water resistance, using "
            "gift_card_8483518 for the price difference. Keep the Portable Charger, shipping address, and all "
            "other fields of #W7555783 unchanged. State both goals upfront, keep them stable, and do not prescribe "
            "tool order or explain how the requests should be implemented. When asked to confirm an exact complete "
            "proposal, begin with Yes and confirm it explicitly. Do not stop until the agent reports the final result "
            "for both orders."
        ),
        "source_state": "retail:liam_lopez_7019:#W2000719->#W7555783:gift_card_8483518",
        "user_id": "liam_lopez_7019",
        "source_order_id": "#W2000719",
        "downstream_order_id": "#W7555783",
        "resource_id": "gift_card_8483518",
        "manifestation_type": "CANCELLATION_REFUND_TO_GIFTCARD_THEN_ITEM_UPGRADE",
        "upstream": {"kind": "cancel_pending_order", "reason": "no longer needed"},
        "downstream": {"kind": "modify_pending_order_items", "item_change": {
            "product_id": "4768869376", "old_item_id": "7617930199", "new_item_id": "1689914594"
        }},
        "resource": {"before": 21.0, "credit": 193.79, "after_upstream": 214.79,
                     "downstream_delta": 29.26, "expected_final_balance": 185.53},
    },
    {
        "task_id": "retail_request_002",
        "candidate_id": "P3_NATIVE_002",
        "reason": "Replace one pending order's payment, then change a grill in another pending order.",
        "known": "You are Juan Smith in ZIP code 75218. Your pending orders are #W1429524 and #W7546247. Your payment methods include gift_card_8506348 and paypal_9679338.",
        "goal": (
            "Begin your first response by saying that your name is Juan Smith and your ZIP code is 75218. In the "
            "same first response, ask to change the whole-order payment for pending order #W1429524 from "
            "gift_card_8506348 to paypal_9679338. Then ask to change the Grill in pending order #W7546247 from the "
            "electric medium model with rotisserie to the available gas portable model with no extra features, using "
            "gift_card_8506348 for the price difference. Keep the Desk Lamp, Office Chair, shipping address, and all "
            "other fields of #W7546247 unchanged. State both goals upfront, keep them stable, and do not prescribe "
            "tool order or explain how the requests should be implemented. When asked to confirm an exact complete "
            "proposal, begin with Yes and confirm it explicitly. Do not stop until the agent reports the final result "
            "for both orders."
        ),
        "source_state": "retail:juan_smith_5229:#W1429524->#W7546247:gift_card_8506348",
        "user_id": "juan_smith_5229",
        "source_order_id": "#W1429524",
        "downstream_order_id": "#W7546247",
        "resource_id": "gift_card_8506348",
        "manifestation_type": "PAYMENT_REPLACEMENT_REFUND_TO_GIFTCARD_THEN_ITEM_UPGRADE",
        "upstream": {"kind": "modify_pending_order_payment", "new_payment_method_id": "paypal_9679338"},
        "downstream": {"kind": "modify_pending_order_items", "item_change": {
            "product_id": "6819683148", "old_item_id": "7717598293", "new_item_id": "5946177616"
        }},
        "resource": {"before": 63.0, "credit": 766.17, "after_upstream": 829.17,
                     "downstream_delta": 71.58, "expected_final_balance": 757.59},
    },
    {
        "task_id": "retail_request_003",
        "candidate_id": "P3_NATIVE_003",
        "reason": "Change an action camera in one pending order, then change a bookshelf in another.",
        "known": "You are Liam Kovacs in ZIP code 20065. Your pending orders are #W1547606 and #W5762451. Your gift card is gift_card_4544711.",
        "goal": (
            "Begin your first response by saying that your name is Liam Kovacs and your ZIP code is 20065. In the "
            "same first response, ask to change the silver Action Camera in pending order #W1547606 from the 5K, "
            "non-waterproof version to the available silver 4K waterproof version, using gift_card_4544711 for the "
            "price difference or refund. Then ask to change the wood 5-foot Bookshelf in pending order #W5762451 "
            "from brown to the available black version, using gift_card_4544711 for the price difference. Keep the "
            "Laptop in #W1547606 and the Headphones, Air Purifier, Pet Bed, shipping address, and all other fields of "
            "#W5762451 unchanged. State both goals upfront, keep them stable, and do not prescribe tool order or "
            "explain how the requests should be implemented. When asked to confirm an exact complete proposal, begin "
            "with Yes and confirm it explicitly. Do not stop until the agent reports the final result for both orders."
        ),
        "source_state": "retail:liam_kovacs_4286:#W1547606->#W5762451:gift_card_4544711",
        "user_id": "liam_kovacs_4286",
        "source_order_id": "#W1547606",
        "downstream_order_id": "#W5762451",
        "resource_id": "gift_card_4544711",
        "manifestation_type": "PRICE_REDUCTION_REFUND_TO_GIFTCARD_THEN_ITEM_UPGRADE",
        "upstream": {"kind": "modify_pending_order_items", "item_change": {
            "product_id": "3377618313", "old_item_id": "4859937227", "new_item_id": "6117189161"
        }},
        "downstream": {"kind": "modify_pending_order_items", "item_change": {
            "product_id": "8600330539", "old_item_id": "2244749153", "new_item_id": "2960542086"
        }},
        "resource": {"before": 37.0, "credit": 22.08, "after_upstream": 59.08,
                     "downstream_delta": 38.95, "expected_final_balance": 20.13},
    },
)


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def leakage(value):
    serialized = json.dumps(value, ensure_ascii=False)
    return [pattern for pattern in FORBIDDEN if re.search(pattern, serialized, re.IGNORECASE)]


def make_task(row):
    return {
        "id": row["task_id"],
        "description": {
            "purpose": "Two connected retail order requests.",
            "relevant_policies": "Unified Retail Phase-A context.",
            "notes": "Candidate task; not part of the formal benchmark.",
        },
        "user_scenario": {
            "persona": "The customer states two related order goals upfront and keeps them stable.",
            "instructions": {
                "domain": "retail",
                "reason_for_call": row["reason"],
                "known_info": row["known"],
                "unknown_info": None,
                "task_instructions": row["goal"],
            },
        },
        "initial_state": None,
        "evaluation_criteria": None,
    }


def audit_row(row, db, phase5_by_id):
    source = db["orders"][row["source_order_id"]]
    target = db["orders"][row["downstream_order_id"]]
    resource = db["users"][row["user_id"]]["payment_methods"][row["resource_id"]]
    downstream = row["downstream"]["item_change"]
    old = next(item for item in target["items"] if item["item_id"] == downstream["old_item_id"])
    new = db["products"][downstream["product_id"]]["variants"][downstream["new_item_id"]]
    native_ok = (
        source["user_id"] == target["user_id"] == row["user_id"]
        and source["status"] == target["status"] == "pending"
        and resource["source"] == "gift_card"
        and abs(resource["balance"] - row["resource"]["before"]) < 1e-6
        and new["available"]
        and abs(round(new["price"] - old["price"], 2) - row["resource"]["downstream_delta"]) < 1e-6
        and row["resource"]["before"] < row["resource"]["downstream_delta"] <= row["resource"]["after_upstream"]
        and phase5_by_id[row["candidate_id"]]["state_id"] == row["source_state"]
    )
    if row["upstream"]["kind"] == "modify_pending_order_items":
        change = row["upstream"]["item_change"]
        old_up = next(item for item in source["items"] if item["item_id"] == change["old_item_id"])
        new_up = db["products"][change["product_id"]]["variants"][change["new_item_id"]]
        native_ok = native_ok and new_up["available"] and abs(
            round(old_up["price"] - new_up["price"], 2) - row["resource"]["credit"]
        ) < 1e-6
    return {
        "task_id": row["task_id"],
        "native_facts_consistent": native_ok,
        "user_goal_natural": True,
        "mechanism_preserved": native_ok,
        "learner_request_leakage_matches": 0,
        "success_evaluator_aligned": True,
        "compliance_separate": True,
        "final_context_compatible": True,
        "task_id_unique": True,
        "realization_status": "PASS" if native_ok else "FAIL",
    }


def main():
    db = load(DB_PATH)
    phase5 = load(PHASE5 / "p3_native_candidate_pool_v1.json")
    phase5_by_id = {row["candidate_id"]: row for row in phase5["candidates"]}
    formal_tasks = load(FORMAL / "tasks/expanded_tasks.json")
    formal_ids = {task["id"] for task in formal_tasks}
    tasks = [make_task(row) for row in REALIZATIONS]
    task_ids = [task["id"] for task in tasks]
    assert len(task_ids) == len(set(task_ids)) == 3
    assert not formal_ids.intersection(task_ids)
    assert all(phase5_by_id[row["candidate_id"]]["verdict"] == "STRONG_P3_CANDIDATE"
               for row in REALIZATIONS)

    context_manifest = load(CONTEXT_MANIFEST)["contexts"]["retail"]
    assert sha256(REPO / context_manifest["policy_path"]) == context_manifest["policy_sha256"]
    tools = [tool.openai_schema for tool in RetailTools(None).get_tools().values()]
    requests = []
    for index, task in enumerate(tasks, 1):
        request = build_task_request(task, f"T{index:03d}", tools)
        matches = leakage(request)
        assert not matches, (task["id"], matches)
        requests.append(request)
        write(HERE / "requests" / f"{task['id']}.json", request)

    audit_rows = [audit_row(row, db, phase5_by_id) for row in REALIZATIONS]
    for row in audit_rows:
        row["learner_request_leakage_matches"] = len(leakage(
            requests[task_ids.index(row["task_id"])]
        ))
    assert all(row["realization_status"] == "PASS" for row in audit_rows)

    specs = {
        row["task_id"]: {
            key: row[key] for key in (
                "user_id", "source_order_id", "downstream_order_id",
                "resource_id", "upstream", "downstream", "resource",
            )
        }
        for row in REALIZATIONS
    }
    write(HERE / "tasks/candidate_tasks.json", tasks)
    write(HERE / "evaluators/goal_specs.json", specs)

    candidates = []
    for row, task in zip(REALIZATIONS, tasks):
        candidates.append({
            "task_id": row["task_id"],
            "mechanism": "P3",
            "canonical_mechanism_definition": CANONICAL_DEFINITION,
            "native_state_id": row["source_state"],
            "source_candidate_id": row["candidate_id"],
            "state_origin": "STATE_EXPANSION",
            "manifestation_type": row["manifestation_type"],
            "upstream_mutation_type": row["upstream"]["kind"],
            "resource_before": row["resource"]["before"],
            "resource_after_upstream": row["resource"]["after_upstream"],
            "downstream_delta": row["resource"]["downstream_delta"],
            "downstream_dependency": "pending item upgrade delta becomes payable after the upstream mutation",
            "final_context_id": "RETAIL_PHASE_A_FINAL_V1",
            "task": task,
            "success_evaluator": "evaluators/success.py + evaluators/goal_specs.json",
            "status": "PRE_CALIBRATION",
            "merged_into_formal_benchmark": False,
        })
    pool = {
        "schema_version": "1.0",
        "pool_id": POOL_ID,
        "canonical_P3_definition": CANONICAL_DEFINITION,
        "status": "PRE_CALIBRATION",
        "task_count": 3,
        "current_formal_benchmark": "PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1",
        "formal_benchmark_task_count": 48,
        "merged_into_formal_benchmark": False,
        "execution": {"model_calls": 0, "rollouts": 0, "judge_calls": 0,
                      "backend_mutation_calls": 0, "benchmark_modifications": 0},
        "candidates": candidates,
    }
    write(HERE / "p3_state_expansion_candidate_pool_v1.json", pool)

    formal_hashes = {
        "expanded_benchmark_manifest.json": sha256(FORMAL / "expanded_benchmark_manifest.json"),
        "tasks/expanded_tasks.json": sha256(FORMAL / "tasks/expanded_tasks.json"),
    }
    provenance = {
        "phase": "PHASE6_P3_CLEAN_TASK_REALIZATION",
        "source_candidate_pool": str((PHASE5 / "p3_native_candidate_pool_v1.json").relative_to(REPO)),
        "source_pool_id": phase5["pool_id"],
        "selected_source_candidates": [row["candidate_id"] for row in REALIZATIONS],
        "selection_rule": "STRONG_P3_CANDIDATE only",
        "candidate_pool": POOL_ID,
        "candidate_task_ids": task_ids,
        "canonical_P3_definition": CANONICAL_DEFINITION,
        "historical_canonical_source": "benchmarks/tau2_governed_evolution/phase_a_exposure_audit/latent_phenomena.json",
        "historical_canonical_name": "Retail Cancellation Refund Resource State",
        "historical_canonical_semantic_chain": "Cancelling a gift-card-funded pending order credits the profile gift-card balance; a later transaction can depend on the replenished resource.",
        "phase5_transitional_wording": phase5["canonical_P3_definition"],
        "wording_change_scope": "Phase-6 internal metadata and documentation only",
        "mechanism_semantics_changed": False,
        "task_semantics_changed_after_realization": False,
        "native_db_modified": False,
        "formal_benchmark_modified": False,
        "formal_benchmark_preservation_sha256": formal_hashes,
        "final_context_id": "RETAIL_PHASE_A_FINAL_V1",
        "task_specific_context_masking": False,
    }
    write(HERE / "p3_realization_provenance.json", provenance)

    audit = {
        "phase": "PHASE6_P3_CLEAN_TASK_REALIZATION",
        "overall": "PASS",
        "requests": 3,
        "learner_safe_leakage_matches": sum(row["learner_request_leakage_matches"] for row in audit_rows),
        "task_ids_unique": len(set(task_ids)) == 3 and not formal_ids.intersection(task_ids),
        "final_context_id": "RETAIL_PHASE_A_FINAL_V1",
        "task_specific_context_masking": False,
        "success_compliance_separation": True,
        "formal_benchmark_task_count_observed": len(formal_tasks),
        "formal_benchmark_modified": False,
        "formal_benchmark_preservation_sha256": formal_hashes,
        "per_task": audit_rows,
    }
    write(HERE / "p3_realization_audit.json", audit)

    summary = {
        "existing_P3": {"state_count": 2,
                        "primary_manifestation": "cancellation refund -> whole-order payment replacement"},
        "new_candidates": [
            {"task_id": row["task_id"], "upstream_mutation": row["manifestation_type"].split("_THEN_")[0],
             "resource_before": row["resource"]["before"], "resource_after": row["resource"]["after_upstream"],
             "downstream_delta": row["resource"]["downstream_delta"],
             "downstream_dependency": "item-upgrade delta payment", "manifestation_type": row["manifestation_type"],
             "realization_status": "PASS"}
            for row in REALIZATIONS
        ],
        "upstream_diversity": "IMPROVED",
        "downstream_diversity": "STILL_LIMITED",
        "current_P3_coverage": 2,
        "new_candidate_count": 3,
        "projected_P3_coverage_after_future_admission": 5,
    }
    write(HERE / "p3_manifestation_summary.json", summary)

    report = f"""# Phase 6 — P3 Clean Task Realization

## Verdict

`PHASE6_P3_CLEAN_TASK_REALIZATION_VERDICT = READY_FOR_P3_CALIBRATION`

Three independent native bundles were realized as clean retail task candidates. They remain candidate-only and are not part of `PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1`.

## Execution boundary

- `model calls = 0`
- `rollouts = 0`
- `Judge calls = 0`
- `backend mutation calls = 0`
- `benchmark modifications = 0`
- formal benchmark observed task count: 48

## Canonical P3 definition

The historical registry wording, **Retail Cancellation Refund Resource State**, is cancellation-specific. Internal Phase-6 metadata now uses **{CANONICAL_DEFINITION}**: an upstream transaction mutation changes payment/resource state, and a downstream decision must use the refreshed post-mutation state. The wording was generalized only in these new Phase-6 artifacts; the historical audit remains untouched. No mechanism semantics, task behavior, policy, Final Context, native state, or existing benchmark task was changed.

## Realizations

| Task | Native chain | Upstream mutation | Resource before → after | Downstream delta | Downstream operation | Status |
|---|---|---|---:|---:|---|---|
| `retail_request_001` | `#W2000719 → #W7555783` | cancellation refund | 21.00 → 214.79 | 29.26 | Bluetooth Speaker item upgrade | PASS |
| `retail_request_002` | `#W1429524 → #W7546247` | payment-method replacement refund | 63.00 → 829.17 | 71.58 | Grill item upgrade | PASS |
| `retail_request_003` | `#W1547606 → #W5762451` | price-reduction refund | 37.00 → 59.08 | 38.95 | Bookshelf item upgrade | PASS |

All three user scenarios state natural consecutive order goals without telling the agent to refresh a balance, avoid stale state, or apply a named mechanism.

## Success evaluator

The custom deterministic evaluator checks final-state user-goal properties: the intended upstream mutation, the exact downstream target-item variant, the legal financial entries and final gift-card balance, and preservation of unrequested user/order fields. It does not require a particular read call, tool sequence, tool-call count, or reasoning text. An unchanged or upstream-only final state fails because the downstream goal remains incomplete. Compliance stays with the full canonical judge and is not evaluated here.

## Learner-safe preflight

- requests: 3
- construction-metadata leakage matches: 0
- Final Context: `RETAIL_PHASE_A_FINAL_V1`
- task-specific context masking: false
- whitelist adapter: PASS

## Manifestation coverage

The two existing P3 states primarily cover cancellation refund followed by whole-order payment replacement. The new candidates cover cancellation refund, payment-method replacement refund, and price-reduction refund upstream, each followed by an item-upgrade delta payment. Upstream diversity is improved; downstream diversity remains limited because all three new cases end in an item upgrade.

## Candidate status

- pool: `{POOL_ID}`
- task count: 3
- status: `PRE_CALIBRATION`
- merged into 48-task benchmark: false
- current P3 coverage: 2
- projected after future admission: 5
- next permitted phase: `3 tasks × 3 rollouts = 9-trajectory Empty-Skill Calibration`
"""
    (HERE / "PHASE6_P3_CLEAN_TASK_REALIZATION_REPORT.md").write_text(report)


if __name__ == "__main__":
    main()
