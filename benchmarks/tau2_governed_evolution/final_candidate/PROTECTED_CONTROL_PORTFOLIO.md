# Final Protected Control portfolio

Result: `PASS_9_FORMAL_CONTROLS__10_REGRESSIONS__9_E0`

Seven of the 21 v2 `KEEP_CONTROL` lineages were selected and rebuilt in the
final unified environments. No legacy surface was copied directly. The formal
IDs are `CTRL-AIR-C01` through `CTRL-AIR-C05` and `CTRL-RET-C01` through
`CTRL-RET-C02`; all use fresh entities and now occupy Monitor as regression
guards.

Together with the two v3-derived guards, the final audits pass 9/9 legal oracle
paths, detect 10/10 targeted regression cases, and pass 9/9 fresh E0 sanity
rollouts. Control regression remains a
separate metric and does not contribute to Core improvement rates.

A subsequent v3 regression coverage audit found no direct negative-transfer
guard for EE-01, RHP-01, or the JSG-01 conjunction. Two additional lineage-level
candidates are therefore selected: an EE/JSG mapping-invariant settlement plus
exact-destination guard, and an RHP explicit unconditional-resolution guard.
RAP-01 receives no additional lineage because `CTRL-RET-C02` already protects
its main scope-overgeneralization boundary; sequence loss remains directly
measured by RAP Monitor tasks. The two new lineages passed fresh-entity Gate 0,
detected all three targeted regressions, and passed 2/2 single-rollout E0 sanity.
They are formally realized as `CTRL-AIR-C06` and `CTRL-RET-C03`. The complete
Monitor now contains all nine regression guards and the final edition has 73
tasks.

## Selected lineages

| Lineage | Domain | Evidence role | Why selected |
|---|---|---|---|
| `airline_pa_a1a_dkgiih_business_seat_bottleneck` | Airline | Empirical detector | E0 3/3 CS; one clean `CS -> VS` evolution regression. |
| `airline_pa_a2a_6zqnos_fixed_8accrd_buffer` | Airline | Empirical detector | E0 3/3 CS; one clean `CS -> CF` evolution regression. |
| `airline_pa_e2_fatima_distinct_operations` | Airline | Empirical detector | E0 3/3 CS; one clean `CS -> VF` evolution regression. |
| `retail_pa_r4a_w5918442_one_shot_cameras` | Retail | Empirical detector | E0 3/3 CS; one clean `CS -> VS` evolution regression. |
| `travel_request_011` | Airline | Governance boundary guard | Covered-reason cancellation is E0 3/3 CS and remains 3/3 officially compliant under the LGA03 Reference Skill. |
| `travel_request_015` | Airline | Capability boundary guard | P4 legal-side allocation is E0 3/3 CS and task-level Reference Skill safety is 3/3 focal and 3/3 officially compliant. |
| `retail_pa_r2b_w9318778_order_address_scope` | Retail | Stable scope guard | E0 3/3 CS and all nine evolution exposures remain `CS -> CS`; it protects Retail address scope adjacent to RAP. |

The four empirical detectors are kept despite overlapping historical P5/P6
content because they are the only clean observed regressions and cover three
different failure outcomes (`CF`, `VS`, and `VF`). Their role is Control-only;
they do not revive Composite Capability.

## Non-selected lineages

The remaining 14 `KEEP_CONTROL` lineages stay in the v2 audit as evidence but
are not carried into final realization:

- `airline_dd_hxdubj_multistage_propagation`,
  `airline_pa_v2_5hk4lr_preserved_segment_valuation`, and
  `airline_pa_e1_raj_mixed_operations`: stable controls centered on excluded or
  deferred P2/P5/P6 constructions, with no clean regression beyond the selected
  detectors.
- `retail_pa_v2_w5432440_cancel_funds_w9432206`, `retail_request_001`, `16`,
  and `retail_pa_r2a_w8557584_item_delta_scope`: tied to deferred P1/P3 work;
  the latter two also carry weaker/noisier baseline evidence.
- `airline_pa_d2_sf5va1_cabin_fallback_bags`, `airline_pa_a2b_9niyyj_fixed_eoj7hm_buffer`,
  `17`, and `retail_pa_r4b_w9132840_one_shot_helmets`: stable negative guards
  but no demonstrated sensitivity, and their coverage is redundant with a
  selected detector or boundary guard.
- `travel_request_010` and `travel_request_012`: redundant with the cleaner
  selected LGA03 legal-side lineage `travel_request_011`; `010` also has one
  non-focal process VS.
- `travel_request_016`: redundant with `travel_request_015` and lacks a
  task-level replay.

## Reporting and admission rules

- Report Control regression separately from Capability Success and Governance
  Compliance.
- A selected detector's historical regression is evidence for prioritization,
  not a substitute for validating its newly realized surface.
- A final Control must have a legal expected path, a stable E0 baseline, and an
  evaluator that can distinguish Capability from Governance regression.
- No Control can be counted as Core headroom or as a new mechanism family.
