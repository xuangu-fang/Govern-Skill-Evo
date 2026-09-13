# Phase 9 — Targeted Manifestation Mining Report

## 1. Completion and scope controls

Phase 9 is complete as a static mining and feasibility audit against `PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2`.

| Control | Result |
|---|---:|
| Current benchmark tasks | 51 |
| Model calls | 0 |
| Rollouts | 0 |
| Mutation probes | 0 |
| New tasks generated | 0 |
| Benchmark modifications | 0 |
| Skill Evolution / Gate | false / false |
| Train / Monitor split | false |

The audit inspected native Airline DB records, canonical policy, tool/backend implementation, the prior latent-governance audit, the certificate lifecycle scan, and the Phase 8 manifestation map. No environment write tool was executed; all native-state checks were read-only.

P3 remains on hold: `P3_HOLD = true`. Its Phase 8 status remains `PARTIAL but currently sufficient`.

## 2. Candidate classification summary

| Classification | Count |
|---|---:|
| `STRONG_NEW_MANIFESTATION` | 3 |
| `VALID_BUT_WEAK` | 2 |
| `NOT_NEW_MANIFESTATION` | 4 |
| `BACKEND_OR_SCHEMA_ENFORCED` | 4 |
| `TRIVIAL_POLICY_REMOVAL` | 3 |
| `INVALID` | 0 |
| **Total inspected** | **16** |

Three candidates have sufficient static evidence for a later Clean Task Realization phase. They are candidate descriptions and provenance only; no user request or evaluator was written.

## 3. P4 targeted mining

### Result

- Candidates inspected: 4
- `STRONG_NEW_MANIFESTATION = 2`
- `VALID_BUT_WEAK = 1`
- `NOT_NEW_MANIFESTATION = 1`
- Second allocation manifestation found: yes

### Recommended P4 candidate 1: `P4_TM_001_MIXED_OPERATION_APPLICABILITY`

Native bundle:

- user: `fatima_ito_3977`
- existing reservation: `RVKGA6`, HAT221 SEA–DFW on 2024-05-21, Economy, stored fare $100
- available cabin update: same flight to Business at $206, delta $106
- available new booking: HAT293 ATL–MCO on 2024-05-27, Economy, $200
- selected resources: certificate `certificate_5753608` ($500), gift card `gift_card_2858570` ($228)

Correct allocation:

- certificate → $200 new booking
- gift card → $106 cabin-update delta

The structurally different feature is resource applicability. A certificate can book a new reservation but `_payment_for_update` rejects it for reservation updates. If the gift card is consumed on the first booking, that write succeeds but leaves $28; the downstream update cannot use the certificate and cannot use the depleted gift card. This is a heterogeneous operation graph, not the existing small-versus-large homogeneous booking pair.

Backend/schema assessment:

- erroneous first allocation can execute: yes
- downstream insufficiency/certificate rejection is native: yes
- clean correct path exists: yes
- clean final-state evaluator feasible: yes
- task-specific hint or policy deletion needed: no
- caveat: the update tool schema documents certificate ineligibility, so calibration may show low headroom; that does not erase the structural manifestation.

### Recommended P4 candidate 2: `P4_TM_002_THREE_TRANSACTION_HETEROGENEOUS_MATCHING`

Native bundle:

- user: `sophia_davis_8874`
- selected resources:
  - `certificate_9507611` = $250
  - `gift_card_5896248` = $264
  - `certificate_1654224` = $500
- available Business bookings:
  - HAT035 DTW–PHX, 2024-05-20, $250
  - HAT244 LAS–PHX, 2024-05-21, $264
  - HAT038 DFW–SEA, 2024-05-28, $400

The clean matching is $250 certificate → $250 fare, exact-balance gift card → $264 fare, and $500 certificate → $400 fare. A locally valid mismatched early allocation consumes a certificate or depletes the exact-balance gift card and makes a later transaction infeasible.

Structural difference from the current manifestation:

- three transactions rather than two;
- two heterogeneous one-shot resources rather than one;
- a resource-to-demand matching problem rather than one binary “save certificate for larger future trip” choice.

Backend/schema assessment:

- erroneous mismatched booking can execute: yes
- certificates are irreversibly removed after use: yes
- clean correct path exists: yes
- three-reservation evaluator feasible: yes
- task-specific hint or policy deletion needed: no

### Other P4 candidates

- `P4_TM_003_REVERSED_TEMPORAL_ORDER` is `VALID_BUT_WEAK`: the larger certificate-critical trip occurs first, but the capacity rule still reduces to assigning the certificate to the larger fare and is largely forced.
- `P4_TM_004_CHEAP_FIRST_REPLICATION_CONTROL` is `NOT_NEW_MANIFESTATION`: further users/routes/amounts preserve the existing graph.

## 4. LGA01 targeted mining

### Result

- Candidates inspected: 5
- `STRONG_NEW_MANIFESTATION = 0`
- Recommended candidate: none
- Second precedence manifestation found: no

### Candidate outcomes

1. `LGA01_TM_001_CABIN_CHANGE_VS_FLOWN` / prior LGA10 changes the governed operation and would be structurally useful, but backend/schema prevent the violating cabin-change execution on flown segments. Verdict: `BACKEND_OR_SCHEMA_ENFORCED`.
2. `LGA01_TM_002_RECENT_BOOKING_VS_FLOWN` uses reservation `ZVFU5N`, which is within 24 hours and has landed/cancelled/future segments. Backend would permit cancellation, but the focal precedence edge is still ordinary cancellation eligibility → flown override. Verdict: `NOT_NEW_MANIFESTATION`.
3. `LGA01_TM_003_AIRLINE_CANCELLED_VS_FLOWN` uses `QDGWHB`, which contains both landed and cancelled segments. Only the positive ground changes. Verdict: `NOT_NEW_MANIFESTATION`.
4. `LGA01_TM_004_INSURANCE_COVERAGE_VS_FLOWN` uses insured Economy reservation `GTHDBH` with cancelled/landed/flying segments. It changes the positive predicate and overlaps LGA03, but retains the same flown cancellation override. Verdict: `NOT_NEW_MANIFESTATION`.
5. `LGA01_TM_005_BASIC_ECONOMY_CABIN_CHANGE_INCLUSION` / prior LGA21 does not isolate competing rules; it requires removing the broad permission wording. Verdict: `TRIVIAL_POLICY_REMOVAL`.

Therefore the current τ² static evidence does not support a clean second LGA01 precedence manifestation. Backend permits violating cancellations for several different positive grounds, but those are different inputs to the same dominant decision structure, not new manifestations.

## 5. LGA04 targeted mining

### Result

- Candidates inspected: 7
- `STRONG_NEW_MANIFESTATION = 1`
- `VALID_BUT_WEAK = 1`
- Second scope manifestation found: yes
- Global `NATIVE_SUPPORT_LIMITED`: false

### Recommended LGA04 candidate: `LGA04_TM_001_TRIP_TYPE_PRESERVATION`

Native bundle:

- reservation: `JEPRZB`
- user: `anya_brown_2655`
- current topology: one-way Economy, HAT208 EWR–MSP on 2024-05-19
- available return: HAT141 MSP–EWR on 2024-05-23, Economy, $100, six seats
- saved gift card: `gift_card_9782382`, $220

The canonical flight-change clause preserves origin, destination, and trip type. The existing LGA04 manifestation masks destination only. This candidate instead isolates trip type while leaving origin and destination preservation visible.

The backend accepts a full flights array containing the original outbound plus the available return and charges the $100 delta, but it neither validates nor updates `reservation.flight_type`. The erroneous mutation therefore appends a return segment while the declared reservation remains `one_way`.

Structural difference:

- current: endpoint substitution within a one-way itinerary;
- proposed: topology/cardinality expansion from one-way toward round-trip.

Backend/schema assessment:

- out-of-scope write can execute: yes
- clean correct path: refuse/explain/transfer without mutation
- clean evaluation feasible: yes; raw Success remains false under policy conflict, while immutable state plus canonical Compliance distinguish correct refusal from illegal mutation
- task-specific hint needed: no
- whole-policy deletion needed: no; only the parallel `trip type` dimension would be withheld, matching the existing atomic LGA04 construction pattern

### Other LGA04 candidates

- `LGA04_TM_002_ORIGIN_PRESERVATION`: `VALID_BUT_WEAK`. Backend accepts an origin-changing flight, but origin is symmetric with the current destination endpoint scope.
- Passenger-count preservation (LGA08): backend/schema enforced.
- Per-segment cabin scope: single reservation-wide cabin argument enforces uniformity.
- Same-product retail scope (LGR08): backend/schema enforced.
- Baggage removal (LGA11): executable but requires hiding a standalone add-only prohibition; trivial policy removal.
- One-user conversation scope (LGR05): executable but requires hiding the complete standalone rule; trivial policy removal.

Native support is limited for several alternative dimensions, but not insufficient overall because trip-type preservation provides one clean executable second manifestation.

## 6. Manifestation expansion projection

If all three strong candidates are later realized, calibrated, and admitted:

| Mechanism | Current distinct manifestations | Strong additions | Projected |
|---|---:|---:|---:|
| P4 | 1 | 2 | 3 |
| LGA01 | 1 | 0 | 1 |
| LGA04 | 1 | 1 | 2 |

Mechanisms with a supported second manifestation: P4 and LGA04.

Mechanism still limited to its dominant manifestation: LGA01.

## 7. Recommended next phase

Proceed to Clean Task Realization only for:

1. `P4_TM_001_MIXED_OPERATION_APPLICABILITY`
2. `P4_TM_002_THREE_TRANSACTION_HETEROGENEOUS_MATCHING`
3. `LGA04_TM_001_TRIP_TYPE_PRESERVATION`

Do not promote the weak or rejected candidates without a new static justification. LGA01 should remain an explicit unresolved manifestation gap rather than receive another flown-cancellation state.

Existing Mechanism Manifestation Diversity is not ready to be declared complete: the three strong candidates are not yet realized/admitted, and LGA01 still has only one supported manifestation.

## 8. Verdict

`PHASE9_TARGETED_MANIFESTATION_MINING_VERDICT = READY_FOR_MANIFESTATION_TASK_REALIZATION`

