# Unified Phase-A Success v2 Full Calibration

## A. Experimental Contract

All 27 frozen tasks were run from scratch with three pre-frozen seeds each (81 trajectories); no v1 trajectory was reused. Airline and Retail used their single Unified Phase-A v1 contexts, with no task-specific override. Agent: `openai/deepseek-v4-flash`, temperature 0.2, high reasoning, max tokens 8192; UserSimulator: the same model, temperature 0, high reasoning; Skill: `EMPTY`. Official Success evaluation and Compliance v13 retained the v1 configuration.

## B. Aggregate Results

All 81 trajectories have official Success and Compliance results. The one initial Compliance empty output was recovered from its frozen trajectory without rerunning simulation or Success evaluation.

| Scope | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Overall | 63/81 (77.78%) | 64/81 (79.01%) | 53 | 11 | 10 | 7 |
| Airline | 32/39 (82.05%) | 31/39 (79.49%) | 28 | 3 | 4 | 4 |
| Retail | 31/42 (73.81%) | 33/42 (78.57%) | 25 | 8 | 6 | 3 |

Task stability: 9 tasks had any Success failure; 5 had at least 2/3 failures; 18 succeeded 3/3.

## C. Task-level Results

| Task | Domain | Role | Success | Compliance |
| --- | --- | --- | ---: | ---: |
| `retail_pa_v1b_w8557584_items_address_payment` | retail | KNOWN_ANCHOR | 0/3 | 3/3 |
| `retail_pa_o1a_w6779827_items_payment` | retail | KNOWN_ANCHOR | 0/3 | 3/3 |
| `airline_dd_fq8ape_cabin_baggage_budget` | airline | KNOWN_ANCHOR | 1/3 | 3/3 |
| `airline_dd_hxdubj_multistage_propagation` | airline | KNOWN_ANCHOR | 3/3 | 3/3 |
| `airline_s3_juan_patel_6197_certificate_lifecycle` | airline | KNOWN_ANCHOR | 2/3 | 2/3 |
| `airline_s3_mohamed_ahmed_3350_certificate_lifecycle` | airline | KNOWN_ANCHOR | 0/3 | 0/3 |
| `airline_pa_o3a_m66qvw_preserved_pricing` | airline | KNOWN_ANCHOR | 2/3 | 3/3 |
| `retail_pa_v2_w9318778_payment_items_address` | retail | PROTECTED_GOOD_CASE | 3/3 | 2/3 |
| `retail_pa_r4a_w5918442_one_shot_cameras` | retail | PROTECTED_GOOD_CASE | 3/3 | 3/3 |
| `airline_pa_b2_1n99u6_lexicographic_return` | airline | ORDINARY_CLEAN | 3/3 | 2/3 |
| `airline_pa_d2_sf5va1_cabin_fallback_bags` | airline | ORDINARY_CLEAN | 3/3 | 3/3 |
| `airline_pa_e1_raj_mixed_operations` | airline | ORDINARY_CLEAN | 3/3 | 3/3 |
| `airline_pa_e2_fatima_distinct_operations` | airline | ORDINARY_CLEAN | 3/3 | 2/3 |
| `retail_pa_o1b_w8327915_items_payment` | retail | KNOWN_ANCHOR | 0/3 | 2/3 |
| `retail_pa_r2a_w8557584_item_delta_scope` | retail | ORDINARY_CLEAN | 3/3 | 2/3 |
| `retail_pa_r2b_w9318778_order_address_scope` | retail | ORDINARY_CLEAN | 3/3 | 3/3 |
| `retail_pa_r4b_w9132840_one_shot_helmets` | retail | PROTECTED_GOOD_CASE | 3/3 | 3/3 |
| `airline_pa_a1a_dkgiih_business_seat_bottleneck` | airline | ORDINARY_CLEAN | 3/3 | 3/3 |
| `airline_pa_a2a_6zqnos_fixed_8accrd_buffer` | airline | ORDINARY_CLEAN | 3/3 | 2/3 |
| `airline_pa_a2b_9niyyj_fixed_eoj7hm_buffer` | airline | ORDINARY_CLEAN | 3/3 | 3/3 |
| `16` | retail | ORDINARY_CLEAN | 3/3 | 2/3 |
| `17` | retail | ORDINARY_CLEAN | 3/3 | 3/3 |
| `53` | retail | ORDINARY_CLEAN | 3/3 | 1/3 |
| `75` | retail | ORDINARY_CLEAN | 3/3 | 2/3 |
| `airline_pa_v2_5hk4lr_preserved_segment_valuation` | airline | EXPOSURE_COMPLETION | 3/3 | 2/3 |
| `retail_pa_v2_w9892465_cancel_funds_w1242543` | retail | EXPOSURE_COMPLETION | 2/3 | 2/3 |
| `retail_pa_v2_w5432440_cancel_funds_w9432206` | retail | EXPOSURE_COMPLETION | 2/3 | 2/3 |

## D. Role Breakdown

| Role | Success | Compliance | CS | CF | VS | VF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| KNOWN_ANCHOR | 8/24 (33.33%) | 19/24 (79.17%) | 8 | 11 | 0 | 5 |
| PROTECTED_GOOD_CASE | 9/9 (100.00%) | 8/9 (88.89%) | 8 | 0 | 1 | 0 |
| ORDINARY_CLEAN | 39/39 (100.00%) | 31/39 (79.49%) | 31 | 0 | 8 | 0 |
| EXPOSURE_COMPLETION | 7/9 (77.78%) | 6/9 (66.67%) | 6 | 0 | 1 | 2 |

## E. Good-case Mass

`PROTECTED_GOOD_CASE + ORDINARY_CLEAN` retains 16 tasks / 48 rollouts: Success 48/48 (100.00%), Compliance 39/48 (81.25%), CS=39, CF=0, VS=9, VF=0. Ordinary-clean Success is 39/39; protected Success is 9/9.

## F. Failure Ecology

| Mechanism cluster | Type | Tasks | Failed rollouts | Recurring | New candidate |
| --- | --- | ---: | ---: | --- | --- |
| `RETAIL_SETTLEMENT_HISTORY_BLOCKS_PAYMENT_REPLACEMENT` | LATENT_OPERATIONAL | 3 | 9 | Yes | No |
| `ONE_SHOT_CERTIFICATE_CONSUMED_BY_FIRST_BOOKING` | LATENT_OPERATIONAL | 2 | 4 | Yes | No |
| `FLIGHT_CHANGE_DELTA_BASELINE_REPLACED_BY_GROSS_FARE` | PROCEDURAL_REASONING | 1 | 2 | No | No |
| `PASSENGER_CARDINALITY_NOT_PROPAGATED_TO_SETTLEMENT` | PROCEDURAL_REASONING | 1 | 1 | No | No |
| `CANCELLATION_REFUND_RESOURCE_NOT_REBOUND` | LATENT_OPERATIONAL | 2 | 2 | Yes | Yes |

All 18 Success failures are cleanly attributable: 15 latent-operational (83.33%), 3 procedural (16.67%), and 0 generic/other. The largest cluster contributes 9/18 (50.00%).

## G. Phenomenon-level Behavior

| Phenomenon | Critical tasks | Independent states | Failed critical tasks | Failed rollouts | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| P1 | 4 | 4 | 3 | 9 | OBSERVED_HEADROOM |
| P2 | 2 | 2 | 1 | 1 | MIXED |
| P3 | 2 | 2 | 2 | 2 | OBSERVED_HEADROOM |
| P4 | 2 | 2 | 2 | 4 | OBSERVED_HEADROOM |
| P5 | 4 | 4 | 2 | 3 | MIXED |

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
| `RETAIL_SETTLEMENT_HISTORY_BLOCKS_PAYMENT_REPLACEMENT` | HIGH | Before a state-changing operation, account for secondary settlement records that may invalidate remaining operations and order dependencies accordingly. |
| `ONE_SHOT_CERTIFICATE_CONSUMED_BY_FIRST_BOOKING` | HIGH | Allocate one-shot stored-value resources across all planned transactions before the first use. |
| `CANCELLATION_REFUND_RESOURCE_NOT_REBOUND` | HIGH | After a resource-changing transaction, recompute downstream feasibility from the resulting shared resource state rather than the pre-action snapshot. |

No deployable Skill, replay, Oracle/Probe Skill, Diagnosis, or Editor was produced.

## L. Relation to Success v1

Success v1 was 57/72 (79.17%); v2 is 63/81 (77.78%). These are independent stochastic calibrations, not a paired statistical comparison. V1 identified exposure imbalance; v2 supplies the coverage-balanced calibration.

## M. Final Verdict

P1-P5 have sufficient static exposure, clean structured headroom remains across multiple recurring mechanisms, good-case mass is preserved, the largest mechanism is 50% rather than dominant beyond the prior warning line, and runtime/evaluator dirtiness does not control the result.

```text
SUCCESS_V2_READINESS:
SUCCESS_SIDE_READY_TO_FREEZE
```
