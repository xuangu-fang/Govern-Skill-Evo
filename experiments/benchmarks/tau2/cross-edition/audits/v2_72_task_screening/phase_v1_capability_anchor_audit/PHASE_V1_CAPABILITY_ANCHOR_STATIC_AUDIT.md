# Phase v1 Capability Anchor static audit

**Static result: `REBUILD=12`, `KEEP_CONTROL=6`, `REJECT=1`; no task is directly Core-admissible.**

Historical E0: 57 rollouts, `CS=32`, `CF=5`, `VS=4`, `VF=16`; focal Capability errors: 21.

| Task | Family | E0 | Focal C | Bucket | Legal path | Surface | Provisional |
|---|---|---|---:|---|---|---|---|
| `retail_pa_v1b_w8557584_items_address_payment` | P1 | 0/0/0/3 | 3/3 | STABLE | STRUCTURALLY_FEASIBLE__REFERENCE_WITNESS_REQUIRED | FAIL | `REBUILD` |
| `retail_pa_o1a_w6779827_items_payment` | P1 | 1/0/1/1 | 1/3 | WEAK | YES_OBSERVED_IN_E0 | FAIL | `REBUILD` |
| `airline_dd_fq8ape_cabin_baggage_budget` | P5+P6 | 1/2/0/0 | 2/3 | RECURRENT | YES_OBSERVED_IN_E0 | FAIL | `REBUILD` |
| `airline_dd_hxdubj_multistage_propagation` | P5+P6 | 3/0/0/0 | 0/3 | NONE_OBSERVED | YES_OBSERVED_IN_E0 | FAIL | `KEEP_CONTROL` |
| `airline_s3_juan_patel_6197_certificate_lifecycle` | P4 | 1/1/0/1 | 2/3 | RECURRENT | YES_OBSERVED_IN_E0 | FAIL | `REBUILD` |
| `airline_s3_mohamed_ahmed_3350_certificate_lifecycle` | P4 | 1/1/0/1 | 2/3 | RECURRENT | YES_OBSERVED_IN_E0 | FAIL | `REBUILD` |
| `airline_pa_o3a_m66qvw_preserved_pricing` | P2+P5+P6 | 2/0/0/1 | 1/3 | WEAK | YES_OBSERVED_IN_E0 | FAIL | `REBUILD` |
| `retail_pa_o1b_w8327915_items_payment` | P1 | 1/0/0/2 | 2/3 | RECURRENT | YES_OBSERVED_IN_E0 | FAIL | `REBUILD` |
| `airline_pa_v2_5hk4lr_preserved_segment_valuation` | P2+P5+P6 | 3/0/0/0 | 0/3 | NONE_OBSERVED | YES_OBSERVED_IN_E0 | FAIL | `KEEP_CONTROL` |
| `retail_pa_v2_w9892465_cancel_funds_w1242543` | P3 | 2/0/0/1 | 1/3 | WEAK | YES_OBSERVED_IN_E0 | FAIL | `REBUILD` |
| `retail_pa_v2_w5432440_cancel_funds_w9432206` | P3 | 3/0/0/0 | 0/3 | NONE_OBSERVED | YES_OBSERVED_IN_E0 | FAIL | `KEEP_CONTROL` |
| `travel_request_001` | P4 | 2/0/0/1 | 1/3 | WEAK | YES_OBSERVED_IN_E0 | FAIL | `REBUILD` |
| `travel_request_002` | P4 | 2/0/0/1 | 1/3 | WEAK | YES_OBSERVED_IN_E0 | FAIL | `REBUILD` |
| `travel_request_003` | P4 | 0/0/0/3 | 3/3 | STABLE | STRUCTURALLY_FEASIBLE__REFERENCE_WITNESS_REQUIRED | FAIL | `REBUILD` |
| `retail_request_001` | P3 | 3/0/0/0 | 0/3 | NONE_OBSERVED | YES_OBSERVED_IN_E0 | FAIL | `KEEP_CONTROL` |
| `retail_request_002` | P3 | 0/1/1/1 | 2/3 | RECURRENT | STRUCTURALLY_FEASIBLE__REFERENCE_WITNESS_REQUIRED | FAIL | `REBUILD` |
| `retail_request_003` | P3 | 1/0/2/0 | 0/3 | NONE_OBSERVED | YES_OBSERVED_IN_E0 | FAIL | `REJECT` |
| `travel_request_015` | P4 | 3/0/0/0 | 0/3 | NONE_OBSERVED | YES_OBSERVED_IN_E0 | FAIL | `KEEP_CONTROL` |
| `travel_request_016` | P4 | 3/0/0/0 | 0/3 | NONE_OBSERVED | YES_OBSERVED_IN_E0 | FAIL | `KEEP_CONTROL` |

All 19 tasks use fixed entities, identifiers, amounts or thresholds, and presentation order without counterfactual balance. Several prompts also state the intended dependency or calculation sequence directly. The mechanisms may be useful, but every final port requires new surfaces and domain-wide integration into the v3 unified environment.
