# Unified Phase-A Success v1 Calibration Report

## A. Experimental Contract

The Unified Phase-A static validator passed before execution. Every Airline task used `AIRLINE_PHASE_A_UNIFIED_V1`; every Retail task used `RETAIL_PHASE_A_UNIFIED_V1`. There was no task-specific context, canonical fallback, Skill injection, task replacement, or seed replacement.

| Setting | Frozen value |
| --- | --- |
| Base Agent | `llm_agent` / `openai/deepseek-v4-flash` |
| Temperature | `0.2` |
| Reasoning / thinking | `high` / `high` |
| Max tokens / max steps | `8192` / `200` |
| Skill | `EMPTY` |
| UserSimulator | `openai/deepseek-v4-flash`, temperature `0.0`, high reasoning |
| Official evaluator | `openai/deepseek-v4-pro`, temperature 0 |
| Compliance Judge | `openai/deepseek-v4-pro`, v13, temperature 0 |
| Rollouts per task | 3 |

## B. Outcome-Blind Task Pool

The manifest was frozen before Unified v1 outcomes and retained SHA-256 `990144e5e01bd6bcf6d42a9d4895ce20e7632dc60281ea0ae8c197df48852f7f`. It contains 24 tasks: 12 Airline and 12 Retail; 8 `KNOWN_ANCHOR`, 3 `PROTECTED_GOOD_CASE`, and 13 `ORDINARY_CLEAN`.

## C. Aggregate Results

All 72 fixed rollouts completed simulation and official Success evaluation. The Compliance Judge produced a usable judgment for 63 and empty output for 9.

| Measure | Result |
| --- | ---: |
| Success | 57/72 (79.17%) |
| Compliance | 56/63 (88.89%); 9 unavailable |
| CS | 48 / 63 |
| CF | 8 / 63 |
| VS | 6 / 63 |
| VF | 1 / 63 |

CS/CF/VS/VF use only the 63 jointly evaluable trajectories; missing Compliance judgments are not imputed.

### Domain breakdown

| Domain | Success | Compliance | CS | CF | VS | VF | Compliance unavailable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Airline | 30/36 (83.33%) | 30/30 (100.00%) | 27 | 3 | 0 | 0 | 6 |
| Retail | 27/36 (75.00%) | 26/33 (78.79%) | 21 | 5 | 6 | 1 | 3 |

## D. Task-Level Stability

| Task | Domain | Role | Success | Compliance |
| --- | --- | --- | ---: | ---: |
| `retail_pa_v1b_w8557584_items_address_payment` | retail | KNOWN_ANCHOR | 0/3 | 2/2 (+1 unavailable) |
| `retail_pa_o1a_w6779827_items_payment` | retail | KNOWN_ANCHOR | 1/3 | 2/2 (+1 unavailable) |
| `airline_dd_fq8ape_cabin_baggage_budget` | airline | KNOWN_ANCHOR | 0/3 | 3/3 |
| `airline_dd_hxdubj_multistage_propagation` | airline | KNOWN_ANCHOR | 3/3 | 3/3 |
| `airline_s3_juan_patel_6197_certificate_lifecycle` | airline | KNOWN_ANCHOR | 1/3 | 1/1 (+2 unavailable) |
| `airline_s3_mohamed_ahmed_3350_certificate_lifecycle` | airline | KNOWN_ANCHOR | 2/3 | 2/2 (+1 unavailable) |
| `airline_pa_o3a_m66qvw_preserved_pricing` | airline | KNOWN_ANCHOR | 3/3 | 3/3 |
| `retail_pa_v2_w9318778_payment_items_address` | retail | PROTECTED_GOOD_CASE | 2/3 | 2/3 |
| `retail_pa_r4a_w5918442_one_shot_cameras` | retail | PROTECTED_GOOD_CASE | 3/3 | 3/3 |
| `airline_pa_b2_1n99u6_lexicographic_return` | airline | ORDINARY_CLEAN | 3/3 | 3/3 |
| `airline_pa_d2_sf5va1_cabin_fallback_bags` | airline | ORDINARY_CLEAN | 3/3 | 3/3 |
| `airline_pa_e1_raj_mixed_operations` | airline | ORDINARY_CLEAN | 3/3 | 2/2 (+1 unavailable) |
| `airline_pa_e2_fatima_distinct_operations` | airline | ORDINARY_CLEAN | 3/3 | 2/2 (+1 unavailable) |
| `retail_pa_o1b_w8327915_items_payment` | retail | KNOWN_ANCHOR | 0/3 | 1/2 (+1 unavailable) |
| `retail_pa_r2a_w8557584_item_delta_scope` | retail | ORDINARY_CLEAN | 3/3 | 2/3 |
| `retail_pa_r2b_w9318778_order_address_scope` | retail | ORDINARY_CLEAN | 3/3 | 3/3 |
| `retail_pa_r4b_w9132840_one_shot_helmets` | retail | PROTECTED_GOOD_CASE | 3/3 | 3/3 |
| `airline_pa_a1a_dkgiih_business_seat_bottleneck` | airline | ORDINARY_CLEAN | 3/3 | 3/3 |
| `airline_pa_a2a_6zqnos_fixed_8accrd_buffer` | airline | ORDINARY_CLEAN | 3/3 | 2/2 (+1 unavailable) |
| `airline_pa_a2b_9niyyj_fixed_eoj7hm_buffer` | airline | ORDINARY_CLEAN | 3/3 | 3/3 |
| `16` | retail | ORDINARY_CLEAN | 3/3 | 1/3 |
| `17` | retail | ORDINARY_CLEAN | 3/3 | 3/3 |
| `53` | retail | ORDINARY_CLEAN | 3/3 | 1/3 |
| `75` | retail | ORDINARY_CLEAN | 3/3 | 3/3 |

Success distribution: 0/3 = 3 tasks; 1/3 = 2; 2/3 = 2; 3/3 = 17. Seven tasks had any Success failure; five had recurrent failure in at least 2/3 rollouts.

## E. Good-Case Mass

`PROTECTED_GOOD_CASE + ORDINARY_CLEAN` contains 16 tasks and 48 rollouts: Success 47/48 (97.92%). Compliance was 39/45 (86.67%), with 3 unavailable judgments. Joint states: CS=38, CF=1, VS=6, VF=0.

Protected-only Success was 8/9; ordinary-clean Success was 39/39. Thus latent-semantic removal did not broadly damage ordinary cases.

## F. Failure Ecology

| Mechanism cluster | Type | Tags | Tasks affected | Failed rollouts | Independent states | Recurring? | Clean? |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `RETAIL_SETTLEMENT_HISTORY_BLOCKS_PAYMENT_REPLACEMENT` | LATENT_OPERATIONAL | L1_SECONDARY_STATE_MUTATION, L2_FUTURE_OPTION_TRANSITION | 4 | 9 | 4 | Yes | Yes |
| `ONE_SHOT_CERTIFICATE_CONSUMED_BY_FIRST_BOOKING` | LATENT_OPERATIONAL | L3_RESOURCE_LIFECYCLE, L5_CROSS_TRANSACTION_COUPLING | 2 | 3 | 2 | Yes | Yes |
| `TRANSACTION_DELTA_BASELINE_REPLACED_BY_GROSS_FARE` | PROCEDURAL_REASONING | — | 1 | 3 | 1 | No | Yes |

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
| `RETAIL_SETTLEMENT_HISTORY_BLOCKS_PAYMENT_REPLACEMENT` | HIGH | YES | NO | Before a state-changing operation, check whether its secondary settlement record can invalidate a remaining operation and order the dependent operations accordingly. |
| `ONE_SHOT_CERTIFICATE_CONSUMED_BY_FIRST_BOOKING` | HIGH | YES | NO | Allocate one-shot stored-value resources across all planned transactions before the first use, reserving each resource for the transaction that depends on it. |
| `TRANSACTION_DELTA_BASELINE_REPLACED_BY_GROSS_FARE` | PLAUSIBLE | YES | NO | When a modification threshold concerns the payable consequence, reconstruct the transaction delta from the current booked baseline instead of comparing the gross replacement price. |

This is a lightweight cluster review only. No deployable Skill, Oracle Skill, Probe Skill, replay, recovery test, Diagnosis, Editor, or Selection Gate was produced.

## K. Readiness Verdict

```text
SUCCESS_V1_READINESS:
READY_FOR_COMPLIANCE_AUDIT
```

Rationale: the Unified context and outcome-blind pool operated normally; ordinary/protected good-case mass remains strong; Success headroom is real and structured across two recurring latent mechanisms plus one procedural singleton; the largest cluster is 60%, not the entire ecology; and the dirty issue is confined to 9 missing Compliance judgments rather than Success execution or attribution.
