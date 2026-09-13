# Unified Phase-A Success v1 Calibration Report

## A. Experimental Contract

The Unified Phase-A context passed the required static validator before the benchmark was attempted. The frozen context IDs were `AIRLINE_PHASE_A_UNIFIED_V1` and `RETAIL_PHASE_A_UNIFIED_V1`; no task-specific context or fallback was enabled.

| Setting | Frozen value |
| --- | --- |
| Base Agent | `llm_agent` |
| Model | `openai/deepseek-v4-flash` |
| Temperature | `0.2` |
| Reasoning / thinking | `high` / `high` |
| Max tokens | `8192` |
| Skill | `EMPTY` (no injection) |
| UserSimulator | `openai/deepseek-v4-flash`, temperature `0.0`, high reasoning |
| Rollouts per task | `3` |
| Planned task / rollout count | `24 / 72` |

## B. Outcome-Blind Task Pool

The pool was frozen before any Unified v1 rollout. Its manifest SHA-256 is `990144e5e01bd6bcf6d42a9d4895ce20e7632dc60281ea0ae8c197df48852f7f`. It contains 24 tasks: 12 Airline and 12 Retail; 8 `KNOWN_ANCHOR`, 3 `PROTECTED_GOOD_CASE`, and 13 `ORDINARY_CLEAN`.

Selection used Phase-A eligibility, cleanliness, operation/state diversity, and prior provenance. Unified outcomes, desired difficulty, expected latent mechanism, and aggregate Success were excluded.

## C. Execution and Aggregate Results

The run did not produce behavioral data. All 72/72 fixed executions were rejected by the model provider with HTTP 400 `budget_exceeded` before the first UserSimulator message. The error stated that the configured budget and credit package were exhausted.

| Measure | Result |
| --- | ---: |
| Valid trajectories | 0 / 72 |
| Success | NOT MEASURABLE |
| Compliance | NOT MEASURABLE |
| CS / CF / VS / VF | NOT MEASURABLE |

Provider errors are missing observations; they are not counted as Success failures or as 0% Success.

### Domain breakdown

| Domain | Planned | Valid | Provider errors | Success | Compliance |
| --- | ---: | ---: | ---: | ---: | ---: |
| Airline | 36 | 0 | 36 | NOT MEASURABLE | NOT MEASURABLE |
| Retail | 36 | 0 | 36 | NOT MEASURABLE | NOT MEASURABLE |

## D. Task-Level Stability

`Success 0/3` through `3/3`, tasks with any Success failure, tasks with at least 2/3 Success failures, and stable 3/3 Success are all **not measurable** because every task has 0/3 valid trajectories.

## E. Good-Case Mass

The 3 protected and 13 ordinary clean tasks represent 48 planned executions. Their Success, Compliance, and CS are not measurable; all were provider-blocked before behavior began.

## F. Failure Ecology

There are no attributable Success failures and therefore no Success mechanism ecology to cluster.

| Mechanism cluster | Type | Tags | Tasks affected | Failed rollouts | Independent states | Recurring? | Clean? |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| None observed | — | — | 0 | 0 | 0 | No | — |

The only execution-error cluster is `PROVIDER_BUDGET_EXHAUSTED`: `PROVIDER_OR_PARSE_ERROR`, 24 tasks, 72 failed executions, dirty, and not a Success mechanism. It accounts for 100% of execution failures. Largest concentration among attributable Success failures is not measurable because the denominator is zero.

## G. Known Anchor Comparison

| Anchor | Status | Qualification |
| --- | --- | --- |
| S1 | NOT_OBSERVED | NOT EVALUABLE: zero valid trajectories |
| S2 | NOT_OBSERVED | NOT EVALUABLE: zero valid trajectories |
| S3 | NOT_OBSERVED | NOT EVALUABLE: zero valid trajectories |
| S5 | NOT_OBSERVED | NOT EVALUABLE: zero valid trajectories |

This is not evidence that any known mechanism disappeared.

## H. New Mechanisms

`NEW_MECHANISM_CANDIDATE = false`. No agent decision or environment transition was observed, so the provider failure cannot support a mechanism claim.

## I. Dirty Failure Audit

All 72 attempts are `PROVIDER_OR_PARSE_ERROR`. The provider rejected the initial UserSimulator generation call; no agent output, tool call, environment transition, official evaluation, or Compliance judgment occurred. Breakdown: 36 Airline / 36 Retail and 24 anchor / 9 protected-good / 39 ordinary-clean attempts.

## J. Skill-Addressability

No review was performed. There is no clean recurring Success mechanism with representative trajectories, and provider budget exhaustion is not Skill-addressable.

## K. Readiness Verdict

```text
SUCCESS_V1_READINESS:
DIRTY
```

Reason: provider/credit exhaustion dominates 72/72 attempted executions and leaves zero valid behavioral trajectories. The frozen task pool, seed manifest, contexts, and configuration remain unchanged; no seed, task, prompt, context, model, or fallback was substituted after observing the error.
