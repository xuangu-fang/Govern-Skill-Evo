# Phase 6 — P3 Clean Task Realization

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

The historical registry wording, **Retail Cancellation Refund Resource State**, is cancellation-specific. Internal Phase-6 metadata now uses **Mutation-Induced Resource Refresh Dependency**: an upstream transaction mutation changes payment/resource state, and a downstream decision must use the refreshed post-mutation state. The wording was generalized only in these new Phase-6 artifacts; the historical audit remains untouched. No mechanism semantics, task behavior, policy, Final Context, native state, or existing benchmark task was changed.

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

- pool: `P3_STATE_EXPANSION_CANDIDATE_POOL_V1`
- task count: 3
- status: `PRE_CALIBRATION`
- merged into 48-task benchmark: false
- current P3 coverage: 2
- projected after future admission: 5
- next permitted phase: `3 tasks × 3 rollouts = 9-trajectory Empty-Skill Calibration`
