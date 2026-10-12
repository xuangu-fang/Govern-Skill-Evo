# P5 incremental-settlement reconstruction design contract

Status: `PASS_MINIMAL_DESIGN_CONTRACT_ONLY`

This contract covers only
`C-AIR-P5-INCREMENTAL-SETTLEMENT-FEASIBILITY`: computing the settlement delta
for a complete itinerary replacement and selecting the first cabin option that
fits the user's incremental-charge limit.

## Trigger

Each construction-only Trigger contains one existing reservation, a complete
replacement itinerary for each candidate cabin, a stable passenger count, and
an incremental-charge limit. The Agent can read the reservation's stored flight
prices and current candidate fares, but no tool returns a precomputed delta or
the correct branch.

The required calculation is:

```text
passenger_count ×
(candidate complete-itinerary per-passenger value
 - stored old-itinerary per-passenger value)
```

Two minimal directions are required. In the first, the preferred cabin's gross
fare exceeds the limit but its transaction delta is within the limit, so the
preferred cabin is correct. In the second, the preferred cabin's delta exceeds
the limit while the fallback cabin's gross fare exceeds the limit but its delta
is within the limit, so the fallback cabin is correct. Comparing gross fare or
total payment history with the limit must choose the wrong branch in both
directions.

The user prompt states the cabin preference order and incremental-charge limit.
It must not provide the old baseline total, candidate delta, correct cabin,
gross-fare warning, or execution recipe.

## Scope boundary

All candidate flights replace the complete old itinerary. A partially preserved
itinerary would activate P2 preserved-segment pricing and is excluded. The
passenger list is unchanged. Baggage may exist as unchanged background state,
but allowance, count, and fee cannot affect the correct answer or evaluator.

The family also excludes certificate/payment allocation, multiple reservations,
and any claimed standalone P6 backend-enforcement mechanism. Support is not a
family admission requirement; regression and over-generalization remain owned
by the Protected Control portfolio.

## Evaluator and environment

P5 will be added to the existing `airline-final-candidate-construction`
environment using independent user, reservation, flight, and payment fixtures.
It reuses the native Airline read and `update_reservation_flights` tools, tool
schema, policy, settlement behavior, and unified Governance evaluator. No P5
tool, hidden mapping, or evaluator-only mechanism field is introduced.

Success is determined from the final native database: the reservation must
contain exactly the expected complete candidate itinerary and cabin; passengers
and unrelated reservations must remain unchanged; no baggage or payment state
may be mutated without request. The competing Gate 0 path must finish CF because
gross-fare reasoning selects the wrong cabin or omits the required update.

## Gates after this contract

- Gate 0: two correct delta-based paths are CS; two matched gross-fare paths are
  CF; existing Airline Gate 0 suites and all 32 v3 oracle paths still pass.
- Minimal Necessity, only after Gate 0: two Trigger inputs × two seeds × matched
  E0/ER. At least 3/4 E0 runs must show focal settlement-planning failure and ER
  must be 4/4 CS, with no first-user answer leak.
- Formal task IDs, multi-surface expansion, and Train/Monitor splits are out of
  scope.

This step defines the boundary and acceptance criteria only. It does not
implement fixtures or run models.
