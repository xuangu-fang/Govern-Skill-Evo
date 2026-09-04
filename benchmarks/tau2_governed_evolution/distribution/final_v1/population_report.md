# Governed Evolution Benchmark v1 — Step 16 Population Report

## 1. Blueprint concentration repair

The frozen Test allocation is 18 unseen Atomic/Preservation tasks, 14 unseen
Ordering tasks, and 16 held-out Composition tasks. This replaces the earlier
14/10/24 plan. Composition therefore falls from 50% to 33.3% of Test, while two
complete independent 2×2 grids preserve G4 coverage.

Train remains 32 Repair/Boundary + 12 Ordering + 4 Preservation-only. Fixed
Monitor remains 8 Repair/Boundary + 8 Preservation/Process + 4 Ordering.

## 2. Fresh entity inventory

The native Airline DB contains 500 users, 2,000 reservations, and 300 flights.
After excluding calibration primaries, the static feasibility scan found:

- 329 booking users with a saved passenger and credit card;
- 4,497 available non-blacklisted flight instances;
- 1,270 active, unflown reservations;
- 154 direct-route flight-change candidates with both identity-preserving and
  identity-breaking targets;
- 446 independently cancellable business reservations;
- 429 available business-reservation bases suitable for ordering construction;
- 2 fresh native delayed-business reservations.

Only Ordering lacked enough fully native delayed cases for seven families. Each
ordering family therefore uses a different fresh native business reservation
and materializes exactly one target flight-instance fact from `available` to
`delayed`. Source reservation and flight lineage remain recorded. No copied ID
or synthetic entity family is used.

## 3. Calibration entity exclusion

The blacklist is generated from all five structured task/metadata asset sets,
not from a manually copied list. It contains 3 primary users, 3 primary
reservations, 4 primary flight instances, and 1 primary booking context. The
three primary-family categories contain 7 entries. All 48 Pilot tasks remain
`calibration_only`; final-vs-calibration overlap is zero.

## 4. Family assignment before materialization

`distribution/final_v1/split_manifest.yaml` records the 34 family assignments,
entity contexts, family shapes, manifestation counts, roles, and generalization
levels before any world or Task is built. Assignment is Policy/provenance based
and does not read individual Base-Agent outcomes.

## 5. Train population

Train contains 48 tasks from 13 latent families:

| Mechanism | Families | Tasks |
|---|---:|---:|
| Checked Baggage | 4 | 16 |
| Flight Change Cabin | 4 | 16 |
| Delayed Compensation Ordering | 3 | 12 |
| Itinerary Identity | 1 | 2 |
| Explicit Confirmation | 1 | 2 |

There are no Cancellation Reason or Composition Train tasks.

## 6. Monitor population

Fixed Monitor contains 20 tasks from 7 latent families:

| Mechanism | Families | Tasks |
|---|---:|---:|
| Checked Baggage | 1 | 4 |
| Flight Change Cabin | 1 | 4 |
| Itinerary Identity | 1 | 2 |
| Explicit Confirmation | 2 | 4 |
| Cancellation Reason | 1 | 2 |
| Delayed Compensation Ordering | 1 | 4 |

## 7. Test population

Held-out Test contains 48 tasks:

| Mechanism | Families | Tasks |
|---|---:|---:|
| Checked Baggage | 3 | 6 |
| Flight Change Cabin | 3 | 6 |
| Itinerary Identity | 1 | 2 |
| Explicit Confirmation | 1 | 2 |
| Cancellation Reason | 1 | 2 |
| Delayed Compensation Ordering | 3 | 14 |
| Baggage × Confirmation | 2 composition families | 16 |

Ordering Test families have 4, 4, and 6 tasks. Each composition family is a
complete four-world grid with two manifestations per world.

## 8. Composition holdout population

`aircomp_0001` and `aircomp_0002` use different users and different native
flight contexts. Neither context is reused by Atomic Test, Monitor, Train, or
calibration. Their rule pair is known atomically, but joint activation and entity
families are unseen: G3 + G4.

## 9. Entity and family independence

Each of the 34 families has a unique primary user. Reservation mechanisms also
use distinct primary reservations; booking mechanisms use distinct user/flight
contexts. Source and target flight-instance contexts are included in the global
overlap audit. Train∩Monitor, Train∩Test, Monitor∩Test, and Final∩Calibration are
all empty for families, users, reservations, and relevant flight instances.

## 10. Generalization coverage

- Train: G1 and controlled G2.
- Monitor: family-unseen G1/G2.
- Test Atomic and Ordering: G2/G3.
- Test Composition: G3/G4.

Test families change entity/state context, controlled predicate realization,
information presentation, and surface style without changing source Policy.

## 11. Compiler and environment validation

All 116 tasks deserialize through the vendored τ² `Task` schema and load into
the Airline environment. Every family has a canonical governed path with τ²
environment reward 1.0 (and communication reward 1.0 where applicable). The
extra-blocker audit checks booking availability/payment/options, flight-change
route and seat feasibility, cancellation status/refund/eligibility, and the full
ordering isolation set.

## 12. Compliance Oracle coverage

All atomic tasks resolve to an existing target-rule handler. Composition tasks
reuse the Checked Baggage and Explicit Confirmation handlers and compute joint
compliance as their conjunction. The confirmation handler was minimally made
payload-driven so it can bind a summary to each fresh booking payload. Offline
replay keeps all 144 stored calibration labels unchanged and does not alter any
trajectory hash.

Task Success remains outcome-based. Confirmation, cancellation reason, and
ordering are not inserted into ACTION rewards; denial sides continue to use the
existing deterministic semantic denial evaluation contract.

## 13. Leakage audit

All audited overlap counts are zero:

- family overlap across formal splits;
- primary user/reservation/flight-context overlap across splits;
- composition-grid or composition-family overlap;
- composition-vs-atomic Test entity overlap;
- final-vs-calibration primary entity overlap.

Policy Concept, Boundary Template, and Policy Rule may intentionally cross
splits because mechanism generalization is the evaluation target.

## 14. Final benchmark statistics

- 32 fresh atomic/ordering latent families;
- 2 fresh composition families;
- 116 formal tasks: 48 Train, 20 Monitor, 48 Test;
- Test role allocation: 18 Atomic/Preservation, 14 Ordering, 16 Composition;
- 48 calibration tasks remain excluded.

## 15. Remaining risks

Ordering families require a minimal delayed-status override because only two
fresh native delayed-business reservations exist. This is explicit and narrow,
but Step 17 should report outcomes separately by family so any state-realization
artifact is visible. The current population is statically validated, not yet
empirically calibrated.

## 16. Step 17 final calibration contract

Step 17 may run the frozen Train/Monitor/Test tasks for the first time using the
unchanged Base Agent configuration. It must not change split membership after
observing results. It should measure CS/VS/CF/VF, repair density, Monitor
preservation, unseen Atomic/Ordering behavior, held-out Composition headroom,
and independent-family replication.

