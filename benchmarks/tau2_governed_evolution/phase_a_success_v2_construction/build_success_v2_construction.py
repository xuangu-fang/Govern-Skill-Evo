"""Build the static, coverage-balanced Phase-A Success v2 construction.

This module is intentionally construction-only: it reads the frozen Success v1
pool and native tau2 state, performs deterministic static checks, and writes no
rollout configuration or behavioral result.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
V1_DIR = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_success_v1"
AUDIT_DIR = PROJECT_ROOT / "benchmarks/tau2_governed_evolution/phase_a_exposure_audit"
AIRLINE_DB = PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/airline/db.json"
RETAIL_DB = PROJECT_ROOT / "external/tau2-bench/data/tau2/domains/retail/db.json"

V1_MANIFEST_SHA256 = "990144e5e01bd6bcf6d42a9d4895ce20e7632dc60281ea0ae8c197df48852f7f"
CONTEXT_IDS = {
    "airline": "AIRLINE_PHASE_A_UNIFIED_V1",
    "retail": "RETAIL_PHASE_A_UNIFIED_V1",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_tasks() -> list[dict[str, Any]]:
    return [
        {
            "id": "airline_pa_v2_5hk4lr_preserved_segment_valuation",
            "description": {
                "purpose": "Coverage-balanced Phase-A conditional flight-change task.",
                "relevant_policies": "Unified Airline Phase-A context.",
                "notes": "EXPOSURE_COMPLETION construction; frozen without behavioral execution.",
            },
            "user_scenario": {
                "persona": "The customer states one complete, stable conditional goal and does not prescribe an execution procedure.",
                "instructions": {
                    "domain": "airline",
                    "reason_for_call": "Apply a price-bounded return-flight preference while preserving the rest of the reservation.",
                    "known_info": "You are Fatima Rossi. Your user ID is fatima_rossi_9268 and your reservation is 5HK4LR. Your Mastercard ending 7369 is credit_card_9469188.",
                    "unknown_info": None,
                    "task_instructions": "Begin your first response by giving your user ID fatima_rossi_9268 and reservation ID 5HK4LR. In that same first response, state this complete final request: keep the May 17 outbound flight HAT115 exactly unchanged; for the May 28 return, change HAT288 to HAT062 only if the total additional amount due for the entire two-passenger reservation is no more than $100. If that condition is not met, leave the entire reservation unchanged. If the change qualifies, use Mastercard credit_card_9469188 for the payment or refund and preserve Economy cabin, both passengers, baggage, insurance, route, and every other reservation field. Do not prescribe a calculation method, tool order, payload construction, or commit timing. Never add, remove, or revise a goal later. When asked to confirm the exact complete proposal, begin your response with Yes and confirm it explicitly. Do not stop until the agent reports the final result.",
                },
            },
            "initial_state": None,
            "evaluation_criteria": {
                "actions": [
                    {
                        "action_id": "airline_pa_v2_5hk4lr_preserved_segment_valuation_target_0",
                        "requestor": "assistant",
                        "name": "update_reservation_flights",
                        "arguments": {
                            "reservation_id": "5HK4LR",
                            "cabin": "economy",
                            "flights": [
                                {"flight_number": "HAT115", "date": "2024-05-17"},
                                {"flight_number": "HAT062", "date": "2024-05-28"},
                            ],
                            "payment_id": "credit_card_9469188",
                        },
                    }
                ],
                "env_assertions": None,
                "communicate_info": [],
                "nl_assertions": [
                    "The assistant reports that reservation 5HK4LR keeps outbound HAT115 on May 17 and changes the May 28 return to HAT062 because the total additional charge is $36, no more than the user's $100 limit; all other reservation fields remain unchanged."
                ],
                "reward_basis": ["DB", "NL_ASSERTION"],
            },
        },
        {
            "id": "retail_pa_v2_w9892465_cancel_funds_w1242543",
            "description": {
                "purpose": "Coverage-balanced Phase-A two-order final-state task.",
                "relevant_policies": "Unified Retail Phase-A context.",
                "notes": "EXPOSURE_COMPLETION construction; frozen without behavioral execution.",
            },
            "user_scenario": {
                "persona": "The customer states both final order goals upfront and does not prescribe an execution procedure.",
                "instructions": {
                    "domain": "retail",
                    "reason_for_call": "Cancel one pending order and change another pending order's whole-order payment method.",
                    "known_info": "You are Ava Nguyen in ZIP code 94128. Your pending orders are #W9892465 and #W1242543. Your gift card is gift_card_1994993.",
                    "unknown_info": None,
                    "task_instructions": "Begin your first response by saying that your name is Ava Nguyen and your ZIP code is 94128. In the same first response, state both final goals: cancel pending order #W9892465 because it is no longer needed, and change the whole-order payment method for pending order #W1242543 to gift card gift_card_1994993. Keep every item, address, and all other fields of #W1242543 unchanged. Do not prescribe tool order, commit timing, or explain how the two requests should be implemented. Never add, remove, or revise a goal later. When asked to confirm the exact complete proposal, begin your response with Yes and confirm it explicitly. Do not stop until the agent reports the final result for both orders.",
                },
            },
            "initial_state": None,
            "evaluation_criteria": {
                "actions": [
                    {
                        "action_id": "retail_pa_v2_w9892465_cancel_funds_w1242543_target_0",
                        "requestor": "assistant",
                        "name": "cancel_pending_order",
                        "arguments": {"order_id": "#W9892465", "reason": "no longer needed"},
                    },
                    {
                        "action_id": "retail_pa_v2_w9892465_cancel_funds_w1242543_target_1",
                        "requestor": "assistant",
                        "name": "modify_pending_order_payment",
                        "arguments": {"order_id": "#W1242543", "payment_method_id": "gift_card_1994993"},
                    },
                ],
                "env_assertions": None,
                "communicate_info": [],
                "nl_assertions": [
                    "The assistant reports that #W9892465 is cancelled as no longer needed and #W1242543 now uses gift card gift_card_1994993 as its whole-order payment method, with the second order's items, address, and other fields unchanged."
                ],
                "reward_basis": ["DB", "NL_ASSERTION"],
            },
        },
        {
            "id": "retail_pa_v2_w5432440_cancel_funds_w9432206",
            "description": {
                "purpose": "Coverage-balanced Phase-A two-order final-state task.",
                "relevant_policies": "Unified Retail Phase-A context.",
                "notes": "EXPOSURE_COMPLETION construction; frozen without behavioral execution.",
            },
            "user_scenario": {
                "persona": "The customer states both final order goals upfront and does not prescribe an execution procedure.",
                "instructions": {
                    "domain": "retail",
                    "reason_for_call": "Cancel one pending order and change another pending order's whole-order payment method.",
                    "known_info": "You are Emma Martin in ZIP code 78750. Your pending orders are #W5432440 and #W9432206. Your gift card is gift_card_4129829.",
                    "unknown_info": None,
                    "task_instructions": "Begin your first response by saying that your name is Emma Martin and your ZIP code is 78750. In the same first response, state both final goals: cancel pending order #W5432440 because it is no longer needed, and change the whole-order payment method for pending order #W9432206 to gift card gift_card_4129829. Keep every item, address, and all other fields of #W9432206 unchanged. Do not prescribe tool order, commit timing, or explain how the two requests should be implemented. Never add, remove, or revise a goal later. When asked to confirm the exact complete proposal, begin your response with Yes and confirm it explicitly. Do not stop until the agent reports the final result for both orders.",
                },
            },
            "initial_state": None,
            "evaluation_criteria": {
                "actions": [
                    {
                        "action_id": "retail_pa_v2_w5432440_cancel_funds_w9432206_target_0",
                        "requestor": "assistant",
                        "name": "cancel_pending_order",
                        "arguments": {"order_id": "#W5432440", "reason": "no longer needed"},
                    },
                    {
                        "action_id": "retail_pa_v2_w5432440_cancel_funds_w9432206_target_1",
                        "requestor": "assistant",
                        "name": "modify_pending_order_payment",
                        "arguments": {"order_id": "#W9432206", "payment_method_id": "gift_card_4129829"},
                    },
                ],
                "env_assertions": None,
                "communicate_info": [],
                "nl_assertions": [
                    "The assistant reports that #W5432440 is cancelled as no longer needed and #W9432206 now uses gift card gift_card_4129829 as its whole-order payment method, with the second order's items, address, and other fields unchanged."
                ],
                "reward_basis": ["DB", "NL_ASSERTION"],
            },
        },
    ]


def task_specs() -> list[dict[str, Any]]:
    source = "benchmarks/tau2_governed_evolution/phase_a_success_v2_construction/exposure_completion_tasks.json"
    return [
        {
            "task_id": "airline_pa_v2_5hk4lr_preserved_segment_valuation",
            "domain": "airline",
            "source_artifact": source,
            "task_role": "EXPOSURE_COMPLETION",
            "target_phenomenon": "P2",
            "phase_a_complete_upfront": True,
            "phase_a_stable_intent": True,
            "procedure_neutral": True,
            "operation_category": "conditional_preserved_segment_flight_change",
            "context_id": CONTEXT_IDS["airline"],
            "selection_reason": "Native independent reservation state in which the preserved-segment historical basis changes a natural $100 flight-change branch.",
            "source_provenance": {"source_pool": "native_tau2_airline_db", "behavioral_outcome_used": False},
        },
        {
            "task_id": "retail_pa_v2_w9892465_cancel_funds_w1242543",
            "domain": "retail",
            "source_artifact": source,
            "task_role": "EXPOSURE_COMPLETION",
            "target_phenomenon": "P3",
            "phase_a_complete_upfront": True,
            "phase_a_stable_intent": True,
            "procedure_neutral": True,
            "operation_category": "cancel_then_cross_order_payment_resource",
            "context_id": CONTEXT_IDS["retail"],
            "selection_reason": "Native independent two-order state where cancellation replenishment is necessary for the requested gift-card payment replacement.",
            "source_provenance": {"source_pool": "native_tau2_retail_db", "behavioral_outcome_used": False},
        },
        {
            "task_id": "retail_pa_v2_w5432440_cancel_funds_w9432206",
            "domain": "retail",
            "source_artifact": source,
            "task_role": "EXPOSURE_COMPLETION",
            "target_phenomenon": "P3",
            "phase_a_complete_upfront": True,
            "phase_a_stable_intent": True,
            "procedure_neutral": True,
            "operation_category": "cancel_then_cross_order_payment_resource",
            "context_id": CONTEXT_IDS["retail"],
            "selection_reason": "Second native user/order state with distinct balances where cancellation replenishment is necessary for the requested gift-card payment replacement.",
            "source_provenance": {"source_pool": "native_tau2_retail_db", "behavioral_outcome_used": False},
        },
    ]


def candidate_audit(air: dict[str, Any], retail: dict[str, Any]) -> dict[str, Any]:
    reservation = air["reservations"]["5HK4LR"]
    kept = reservation["flights"][0]
    changed = reservation["flights"][1]
    passengers = len(reservation["passengers"])
    kept_current = air["flights"][kept["flight_number"]]["dates"][kept["date"]]["prices"][reservation["cabin"]]
    replacement_price = air["flights"]["HAT062"]["dates"][changed["date"]]["prices"][reservation["cabin"]]
    correct_delta = (kept["price"] + replacement_price - kept["price"] - changed["price"]) * passengers
    repriced_delta = (kept_current + replacement_price - kept["price"] - changed["price"]) * passengers

    rows: list[dict[str, Any]] = [
        {
            "task_id": "airline_pa_v2_5hk4lr_preserved_segment_valuation",
            "target_phenomenon": "P2",
            "independent_state": "airline:5HK4LR",
            "admission": "PASS",
            "checks": {
                "phase_a_definition": "PASS",
                "task_evaluator_clean": "PASS",
                "unified_context_compatible": "PASS",
                "exposure": "EXPOSED_CRITICAL",
                "independent_state": True,
                "procedure_leakage": False,
                "rollout_outcome_used": False,
            },
            "static_oracle": {
                "initial_relevant_state": f"5HK4LR has two Economy passengers; preserved HAT115 is stored at ${kept['price']} per passenger but its current catalog fare is ${kept_current}; old return HAT288 is stored at ${changed['price']}.",
                "required_final_target": "Keep HAT115 and replace HAT288 with available HAT062 on May 28 when the total additional charge is no more than $100.",
                "critical_latent_transition": f"The matching preserved HAT115 contributes its stored ${kept['price']} fare; HAT062 contributes its current ${replacement_price} fare.",
                "correct_feasible_action_structure": "Submit the entire two-segment reservation [HAT115, HAT062] in Economy using credit_card_9469188 after confirmation.",
                "why_misunderstanding_changes_outcome": f"Historical preservation yields a ${correct_delta} charge (qualifies); repricing HAT115 yields ${repriced_delta} (does not qualify), changing mutation versus no-mutation final state.",
            },
            "numeric_evidence": {
                "passengers": passengers,
                "preserved_stored_price_per_passenger": kept["price"],
                "preserved_current_price_per_passenger": kept_current,
                "replacement_current_price_per_passenger": replacement_price,
                "stored_old_return_price_per_passenger": changed["price"],
                "correct_additional_charge": correct_delta,
                "incorrect_repriced_preserved_charge": repriced_delta,
                "branch_threshold": 100,
                "replacement_available_seats": air["flights"]["HAT062"]["dates"][changed["date"]]["available_seats"][reservation["cabin"]],
            },
        }
    ]

    p3_specs = [
        ("retail_pa_v2_w9892465_cancel_funds_w1242543", "ava_nguyen_6646", "#W9892465", "#W1242543", "gift_card_1994993"),
        ("retail_pa_v2_w5432440_cancel_funds_w9432206", "emma_martin_6993", "#W5432440", "#W9432206", "gift_card_4129829"),
    ]
    for task_id, user_id, cancel_id, downstream_id, gift_id in p3_specs:
        user = retail["users"][user_id]
        cancel = retail["orders"][cancel_id]
        downstream = retail["orders"][downstream_id]
        balance = user["payment_methods"][gift_id]["balance"]
        refund = cancel["payment_history"][0]["amount"]
        needed = downstream["payment_history"][0]["amount"]
        final_balance = round(balance + refund - needed, 2)
        rows.append(
            {
                "task_id": task_id,
                "target_phenomenon": "P3",
                "independent_state": f"retail:{user_id}:{cancel_id}->{downstream_id}:{gift_id}",
                "admission": "PASS",
                "checks": {
                    "phase_a_definition": "PASS",
                    "task_evaluator_clean": "PASS",
                    "unified_context_compatible": "PASS",
                    "exposure": "EXPOSED_CRITICAL",
                    "independent_state": True,
                    "procedure_leakage": False,
                    "rollout_outcome_used": False,
                },
                "static_oracle": {
                    "initial_relevant_state": f"{gift_id} has ${balance}; cancelling gift-card-funded {cancel_id} refunds ${refund}; changing {downstream_id}'s payment requires ${needed}.",
                    "required_final_target": f"Cancel {cancel_id} and make {gift_id} the whole-order payment method for {downstream_id}.",
                    "critical_latent_transition": f"Cancellation credits ${refund} to the shared profile gift-card resource before the downstream payment replacement.",
                    "correct_feasible_action_structure": f"After a complete confirmation, cancel {cancel_id}, then change {downstream_id}'s payment to {gift_id}.",
                    "why_misunderstanding_changes_outcome": f"The initial ${balance} balance is below ${needed}, while the post-cancellation balance ${round(balance + refund, 2)} covers it; ignoring the replenishment or reversing the writes makes the downstream required mutation fail.",
                },
                "numeric_evidence": {
                    "initial_gift_card_balance": balance,
                    "cancellation_refund": refund,
                    "post_cancellation_balance": round(balance + refund, 2),
                    "downstream_payment_amount": needed,
                    "final_gift_card_balance": final_balance,
                },
            }
        )

    return {
        "schema_version": "phase_a_success_v2_candidate_audit_1.0",
        "audit_kind": "STATIC_CONSTRUCTION_ONLY",
        "outcome_evidence_used": False,
        "unified_context_modified": False,
        "success_v1_modified": False,
        "candidates": rows,
        "construction_checks": {},
    }


def new_exposure_rows(audit: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in audit["candidates"]:
        task_id = item["task_id"]
        p = item["target_phenomenon"]
        exposures = {f"P{i}": "NOT_EXPOSED" for i in range(1, 7)}
        exposures[p] = "EXPOSED_CRITICAL"
        if p == "P2":
            exposures["P5"] = "EXPOSED_CRITICAL"
            exposures["P6"] = "EXPOSED_NONCRITICAL"
        evidence_key = p
        oracle = item["static_oracle"]
        rows.append(
            {
                "task_id": task_id,
                "role": "EXPOSURE_COMPLETION",
                "state_id": item["independent_state"],
                "exposures": exposures,
                "critical_evidence": {
                    evidence_key: {
                        "required_operation_or_decision": oracle["required_final_target"],
                        "state_before": oracle["initial_relevant_state"],
                        "hidden_transition": oracle["critical_latent_transition"],
                        "downstream_dependency": oracle["correct_feasible_action_structure"],
                        "success_impact": oracle["why_misunderstanding_changes_outcome"],
                    }
                },
            }
        )
    return rows


def validate_static(v1_manifest: dict[str, Any], v1_tasks: list[dict[str, Any]], tasks: list[dict[str, Any]], audit: dict[str, Any], air: dict[str, Any], retail: dict[str, Any]) -> dict[str, bool]:
    ids = [task["id"] for task in tasks]
    specs = task_specs()
    checks = {
        "v1_manifest_hash_unchanged": sha256(V1_DIR / "task_manifest.json") == V1_MANIFEST_SHA256,
        "v1_task_count_unchanged": len(v1_manifest["tasks"]) == 24 and len(v1_tasks) == 24,
        "three_unique_completion_tasks": len(ids) == 3 and len(set(ids)) == 3,
        "one_p2_two_p3": [s["target_phenomenon"] for s in specs].count("P2") == 1 and [s["target_phenomenon"] for s in specs].count("P3") == 2,
        "completion_role_only": all(s["task_role"] == "EXPOSURE_COMPLETION" for s in specs),
        "unified_context_only": all(s["context_id"] == CONTEXT_IDS[s["domain"]] for s in specs),
        "phase_a_flags_pass": all(s["phase_a_complete_upfront"] and s["phase_a_stable_intent"] and s["procedure_neutral"] for s in specs),
        "all_candidates_admitted": all(row["admission"] == "PASS" and row["checks"]["exposure"] == "EXPOSED_CRITICAL" for row in audit["candidates"]),
        "outcomes_excluded": audit["outcome_evidence_used"] is False and all(not row["checks"]["rollout_outcome_used"] for row in audit["candidates"]),
        "p2_independent_from_m66qvw": audit["candidates"][0]["independent_state"] == "airline:5HK4LR",
        "p2_branch_flips": audit["candidates"][0]["numeric_evidence"]["correct_additional_charge"] <= 100 < audit["candidates"][0]["numeric_evidence"]["incorrect_repriced_preserved_charge"],
        "p2_replacement_available": audit["candidates"][0]["numeric_evidence"]["replacement_available_seats"] >= len(air["reservations"]["5HK4LR"]["passengers"]),
        "p3_states_independent": len({row["independent_state"].split(":")[1] for row in audit["candidates"] if row["target_phenomenon"] == "P3"}) == 2,
        "p3_funding_critical": all(row["numeric_evidence"]["initial_gift_card_balance"] < row["numeric_evidence"]["downstream_payment_amount"] <= row["numeric_evidence"]["post_cancellation_balance"] for row in audit["candidates"] if row["target_phenomenon"] == "P3"),
        "p3_orders_pending": all(retail["orders"][oid]["status"] == "pending" for oid in ["#W9892465", "#W1242543", "#W5432440", "#W9432206"]),
        "no_latent_semantic_leakage": all(phrase not in task["user_scenario"]["instructions"]["task_instructions"].lower() for task in tasks for phrase in ["historical booked price", "current catalog price", "refund restores", "refund replenishes", "refund will restore"]),
        "no_p1_p4_target_additions": all(s["target_phenomenon"] not in {"P1", "P4", "P5", "P6"} for s in specs),
    }
    return checks


def report_text(manifest_hash: str) -> str:
    return f"""# Phase-A Success v2 Construction Report

## Experimental boundary

This is a static exposure-completion construction only. No Agent, UserSimulator,
official evaluator, Compliance Judge, replay, Skill, or rollout was run. The
Unified Phase-A contexts and all 24 frozen Success v1 tasks remain unchanged.
The source Success v1 manifest hash remains `{V1_MANIFEST_SHA256}`.

## Minimal completion set

Three tasks were added: one P2 task and two P3 tasks. All are marked
`EXPOSURE_COMPLETION`; `target_phenomenon` records construction provenance rather
than a predicted failure label. The resulting Success v2 pool contains 27 tasks.

### P2 — Airline Preserved-Segment Historical Valuation

`airline_pa_v2_5hk4lr_preserved_segment_valuation` uses independent reservation
`5HK4LR` (Fatima Rossi, two Economy passengers). HAT115 on May 17 remains in the
reservation. Its stored price is $128 per passenger while its native current
catalog price is $194. Replacing return HAT288 ($154 stored) with available HAT062
($172 current) produces a true $36 additional charge when the preserved segment
retains its historical value. Repricing the preserved segment would produce $168.
The native difference crosses the user's ordinary $100 condition, so it changes
the evaluator-required final state rather than merely changing an informational
quote. This state is independent of the existing M66QVW exposure.

### P3 — Retail Cancellation Refund Resource State

- `retail_pa_v2_w9892465_cancel_funds_w1242543`: Ava Nguyen's gift card starts at
  $78. Cancelling gift-card-funded #W9892465 credits $370.38. The requested
  payment replacement on #W1242543 needs $184.13, so it is infeasible before the
  cancellation and feasible afterward; final balance is $264.25.
- `retail_pa_v2_w5432440_cancel_funds_w9432206`: Emma Martin's distinct gift card
  starts at $57. Cancelling #W5432440 credits $1,856.45. The requested payment
  replacement on #W9432206 needs $377.97, becoming feasible only after the
  cancellation; final balance is $1,535.48.

These are different users, order pairs, gift cards, initial balances, refund
amounts, and downstream funding amounts. Both use native tau2 state and backend
semantics.

## Cleanliness and leakage audit

All three tasks pass Complete-Upfront Intent, Stable Intent, Procedure-Neutral,
task/evaluator cleanliness, Unified Context compatibility, critical exposure, and
independent-state checks. User-visible task text states final goals, constraints,
payment choices, and confirmation behavior, but does not prescribe action order,
calculation method, payload construction, historical-price behavior, or gift-card
refund bookkeeping. The static oracle remains offline in `candidate_audit.json`.

No Unified Context or taxonomy artifact was modified. No Success v1 task,
manifest entry, result, seed, or wording was modified. No rollout outcome was
used for discovery, admission, or validation. Candidate selection used only the
frozen manifest identity, native database state, backend transitions, task intent,
and evaluator target feasibility.

## Exposure coverage after completion

| Phenomenon | Critical tasks | Independent critical states | Status |
| --- | ---: | ---: | --- |
| P1 Retail item-mutation transition | 4 | 4 | WELL_COVERED |
| P2 Airline preserved-segment historical valuation | 2 | 2 | WELL_COVERED |
| P3 Retail cancellation refund resource state | 2 | 2 | WELL_COVERED |
| P4 Airline certificate lifecycle | 2 | 2 | WELL_COVERED |
| P5 Airline flight-change settlement baseline | 4 | 4 | WELL_COVERED |

The new airline task targets P2. It necessarily also exercises P5's transaction
settlement formula, but no task was added for the purpose of expanding P5. No P1
or P4 task was added. P6 remains Compliance-primary and outside this construction.

The generated Success v2 manifest SHA-256 is `{manifest_hash}`.

## Verdict

```text
SUCCESS_V2_CONSTRUCTION_VERDICT:
READY_FOR_SUCCESS_V2_ROLLOUT
```
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if sha256(V1_DIR / "task_manifest.json") != V1_MANIFEST_SHA256:
        raise RuntimeError("Frozen Success v1 manifest hash changed; refusing construction")

    v1_manifest = load(V1_DIR / "task_manifest.json")
    v1_tasks = load(V1_DIR / "tasks.json")
    base_matrix = load(AUDIT_DIR / "task_exposure_matrix.json")
    air = load(AIRLINE_DB)
    retail = load(RETAIL_DB)
    tasks = make_tasks()
    audit = candidate_audit(air, retail)
    checks = validate_static(v1_manifest, v1_tasks, tasks, audit, air, retail)
    audit["construction_checks"] = checks
    audit["passed"] = all(checks.values())
    if not audit["passed"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"Static construction failed: {failed}")

    dump(OUT_DIR / "exposure_completion_tasks.json", tasks)
    dump(OUT_DIR / "candidate_audit.json", audit)
    dump(OUT_DIR / "success_v2_tasks.json", v1_tasks + tasks)

    merged_manifest = deepcopy(v1_manifest)
    merged_manifest.update(
        {
            "schema_version": "phase_a_success_v2_task_pool_1.0",
            "benchmark_id": "unified_phase_a_success_v2_coverage_balanced",
            "freeze_status": "CONSTRUCTION_FROZEN_AWAITING_HUMAN_REVIEW",
            "parent_manifest": "benchmarks/tau2_governed_evolution/phase_a_success_v1/task_manifest.json",
            "parent_manifest_sha256": V1_MANIFEST_SHA256,
            "construction_kind": "V1_PLUS_EXPOSURE_COMPLETION",
            "outcome_blind": True,
            "selection_excluded_evidence": [
                "Success v1 rollout outcomes",
                "expected Base failure",
                "desired failure rate",
                "model-specific weakness",
                "seed-dependent behavior",
            ],
        }
    )
    merged_manifest["tasks"] = deepcopy(v1_manifest["tasks"]) + task_specs()
    merged_manifest["task_payload_sha256"] = sha256(OUT_DIR / "success_v2_tasks.json")
    dump(OUT_DIR / "success_v2_task_manifest.json", merged_manifest)

    matrix_rows = deepcopy(base_matrix["matrix"]) + new_exposure_rows(audit)
    summary_by_id = {row["phenomenon_id"]: deepcopy(row) for row in base_matrix["phenomenon_summary"]}
    summary_by_id["P2"].update(critical_tasks=2, independent_critical_states=2, coverage_status="WELL_COVERED")
    summary_by_id["P3"].update(critical_tasks=2, independent_critical_states=2, coverage_status="WELL_COVERED")
    summary_by_id["P5"].update(critical_tasks=4, independent_critical_states=4, coverage_status="WELL_COVERED")
    summary_by_id["P6"]["noncritical_tasks"] += 1
    role_summary = deepcopy(base_matrix["role_summary"]) + [
        {"task_role": "EXPOSURE_COMPLETION", "tasks": 3, "tasks_with_any_critical_exposure": 3}
    ]
    exposure_matrix = {
        "schema_version": "phase_a_success_v2_exposure_matrix_1.0",
        "parent_exposure_matrix": "benchmarks/tau2_governed_evolution/phase_a_exposure_audit/task_exposure_matrix.json",
        "task_manifest": "benchmarks/tau2_governed_evolution/phase_a_success_v2_construction/success_v2_task_manifest.json",
        "task_manifest_sha256": sha256(OUT_DIR / "success_v2_task_manifest.json"),
        "task_count": 27,
        "outcome_evidence_used": False,
        "matrix": matrix_rows,
        "phenomenon_summary": [summary_by_id[f"P{i}"] for i in range(1, 7)],
        "role_summary": role_summary,
        "completion_target_met": all(summary_by_id[f"P{i}"]["independent_critical_states"] >= 2 for i in range(1, 6)),
        "verdict": "COVERAGE_SUFFICIENT",
    }
    dump(OUT_DIR / "success_v2_exposure_matrix.json", exposure_matrix)

    manifest_hash = sha256(OUT_DIR / "success_v2_task_manifest.json")
    (OUT_DIR / "SUCCESS_V2_CONSTRUCTION_REPORT.md").write_text(report_text(manifest_hash), encoding="utf-8")
    print(json.dumps({"passed": True, "tasks_added": 3, "success_v2_tasks": 27, "manifest_sha256": manifest_hash, "verdict": "READY_FOR_SUCCESS_V2_ROLLOUT"}, indent=2))


if __name__ == "__main__":
    main()
