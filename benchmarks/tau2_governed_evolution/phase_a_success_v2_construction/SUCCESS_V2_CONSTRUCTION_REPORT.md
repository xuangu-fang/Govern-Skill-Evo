# Phase-A Success v2 Construction Report

## Experimental boundary

This is a static exposure-completion construction only. No Agent, UserSimulator,
official evaluator, Compliance Judge, replay, Skill, or rollout was run. The
Unified Phase-A contexts and all 24 frozen Success v1 tasks remain unchanged.
The source Success v1 manifest hash remains `990144e5e01bd6bcf6d42a9d4895ce20e7632dc60281ea0ae8c197df48852f7f`.

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

The generated Success v2 manifest SHA-256 is `e72421812c6b6cd6a6143d584d8ef8aea2fba2049947547a20ffaefdb08d2e5c`.

## Verdict

```text
SUCCESS_V2_CONSTRUCTION_VERDICT:
READY_FOR_SUCCESS_V2_ROLLOUT
```
