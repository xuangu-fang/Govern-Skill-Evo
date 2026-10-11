# Phase v1 Protected Control audit closeout

**Final result: `KEEP_CONTROL=12`, `REBUILD=3`, `REJECT=1`. Four tasks have directly demonstrated regression sensitivity; eight more are verified/stable negative guards.**

Evidence recovered: 48 historical E0 rollouts plus 117 matched task-pairs from the three-step v2 evolution pilot. The only new behavior was six matched-seed P1 boundary rollouts; all were focal-safe, with no behavioral reruns and no frozen-file changes.

## Directly demonstrated regression detectors

These four tasks combine a 3/3-CS historical baseline with at least one clean `parent CS -> candidate non-CS` transition:

- `airline_pa_a1a_dkgiih_business_seat_bottleneck` (P2+P5+P6): 1 clean regression(s); CS->CS=8, CS->VS=1.
- `airline_pa_a2a_6zqnos_fixed_8accrd_buffer` (P5+P6): 1 clean regression(s); CS->CF=1, CS->CS=8.
- `airline_pa_e2_fatima_distinct_operations` (P5+P6): 1 clean regression(s); CS->CS=8, CS->VF=1.
- `retail_pa_r4a_w5918442_one_shot_cameras` (P1): 1 clean regression(s); CS->CS=8, CS->VS=1.

## Negative and overgeneralization guards

Eight tasks remain useful as safety guards. Six were stable under nine pilot candidate exposures; `retail_pa_r2a_w8557584_item_delta_scope` and `16` additionally passed the scoped P1 supplement 3/3 each. These guards verify non-regression but have not themselves demonstrated a failure-inducing candidate, so they must not be described as empirical detectors.

## Exclusions

- `retail_pa_v2_w9318778_payment_items_address`: rebuild; historical E0 is only 1/3 CS.
- `airline_pa_b2_1n99u6_lexicographic_return` and `75`: rebuild; both show sensitivity but also non-CS parent runs in the pilot, preventing clean causal attribution.
- `53`: reject; historical E0 is 1/3 CS because of unrelated governance errors, and its generic return behavior is redundant.

## Admission boundary

`KEEP_CONTROL` means retain the control lineage and role. None of the frozen v2 surfaces can be copied directly into the final edition: each still requires entity/surface balancing and a domain-wide port into `airline-v3-unified` or `retail-v3-unified`.

| Task | E0 | Pilot pairs | Clean regressions | Control role | Six-class |
|---|---:|---:|---:|---|---|
| `16` | CS/CS/CS | 0 | 0 | `P1_NON_APPLICABILITY_GUARD_VERIFIED` | `KEEP_CONTROL` |
| `17` | CS/CS/CS | 9 | 0 | `STABLE_NEGATIVE_GUARD` | `KEEP_CONTROL` |
| `53` | VS/CS/VS | 9 | 3 | `UNSUITABLE_NOISY_REDUNDANT_CONTROL` | `REJECT` |
| `75` | CS/CS/CS | 9 | 1 | `SENSITIVE_BUT_NOISY_BASELINE` | `REBUILD` |
| `airline_pa_a1a_dkgiih_business_seat_bottleneck` | CS/CS/CS | 9 | 1 | `EMPIRICAL_REGRESSION_DETECTOR` | `KEEP_CONTROL` |
| `airline_pa_a2a_6zqnos_fixed_8accrd_buffer` | CS/CS/CS | 9 | 1 | `EMPIRICAL_REGRESSION_DETECTOR` | `KEEP_CONTROL` |
| `airline_pa_a2b_9niyyj_fixed_eoj7hm_buffer` | CS/CS/CS | 9 | 0 | `STABLE_NEGATIVE_GUARD` | `KEEP_CONTROL` |
| `airline_pa_b2_1n99u6_lexicographic_return` | CS/CS/CS | 9 | 1 | `SENSITIVE_BUT_NOISY_BASELINE` | `REBUILD` |
| `airline_pa_d2_sf5va1_cabin_fallback_bags` | CS/CS/CS | 9 | 0 | `STABLE_NEGATIVE_GUARD` | `KEEP_CONTROL` |
| `airline_pa_e1_raj_mixed_operations` | CS/CS/CS | 9 | 0 | `STABLE_NEGATIVE_GUARD` | `KEEP_CONTROL` |
| `airline_pa_e2_fatima_distinct_operations` | CS/CS/CS | 9 | 1 | `EMPIRICAL_REGRESSION_DETECTOR` | `KEEP_CONTROL` |
| `retail_pa_r2a_w8557584_item_delta_scope` | VS/CS/CS | 0 | 0 | `P1_BOUNDARY_GUARD_VERIFIED` | `KEEP_CONTROL` |
| `retail_pa_r2b_w9318778_order_address_scope` | CS/CS/CS | 9 | 0 | `STABLE_NEGATIVE_GUARD` | `KEEP_CONTROL` |
| `retail_pa_r4a_w5918442_one_shot_cameras` | CS/CS/CS | 9 | 1 | `EMPIRICAL_REGRESSION_DETECTOR` | `KEEP_CONTROL` |
| `retail_pa_r4b_w9132840_one_shot_helmets` | CS/CS/CS | 9 | 0 | `STABLE_NEGATIVE_GUARD` | `KEEP_CONTROL` |
| `retail_pa_v2_w9318778_payment_items_address` | VS/VS/CS | 0 | 0 | `UNSUITABLE_NOISY_BASELINE` | `REBUILD` |
