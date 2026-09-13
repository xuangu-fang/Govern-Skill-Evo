# Phase 8 — Existing Mechanism Manifestation Gap Audit

## 1. Scope and execution controls

Phase 8 is complete as a static artifact audit of `PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V2` (51 tasks).

| Control | Result |
|---|---:|
| Model calls | 0 |
| Rollouts | 0 |
| Calibration calls | 0 |
| New tasks generated | 0 |
| Fresh native-state mining | false |
| Benchmark modifications | 0 |
| Skill Evolution / Gate | false / false |
| Train / Monitor split | false |

The audited mechanisms are P4, LGA01, P3, and LGA04. LGA03 is intentionally outside the detailed expansion ranking.

Manifestation means a meaningfully different operational process or decision structure. User, object, amount, route, date, and wording changes alone are parametric variation.

## 2. Summary

| Mechanism | Independent states | Distinct manifestations | Main manifestations | Parametric diversity | Structural diversity | Main gap | Priority |
|---|---:|---:|---|---|---|---|---|
| P4 | 5 | 1 | two ordered bookings; gift card for smaller first trip; one-shot certificate for larger second trip | HIGH | LOW | no alternative allocation graph, ordering, applicability, or fallback structure | HIGH |
| LGA01 | 6 | 1 | Business cancellation permission vs already-flown override | HIGH | LOW | no second clean precedence relation | HIGH |
| P3 | 5 | 3 upstream / 2 downstream / 4 observed pairings | three refund/rebound mutations; whole-order replacement and item-upgrade consumers | HIGH | MODERATE_TO_HIGH | downstream consumers and cross-combinations remain limited | MEDIUM |
| LGA04 | 5 | 1 focal scope type | destination substitution vs destination preservation | HIGH | LOW | no second scope dimension; composition does not change the focal boundary | HIGH |

P3 is the only audited family whose admitted tasks already contain substantial structural variation. P4, LGA01, and LGA04 have enough independent state count but remain essentially the same task shape.

## 3. P4 manifestation map

### P4_M1 — Sequential two-booking opportunity-cost allocation

States:

- `airline_s3_juan_patel_6197_certificate_lifecycle`
- `airline_s3_mohamed_ahmed_3350_certificate_lifecycle`
- `travel_request_001`
- `travel_request_002`
- `travel_request_003`

All five require two ordered one-way Economy bookings, one one-shot certificate, and one reusable gift card. The gift card can pay for the cheaper first booking but not the more expensive second booking; therefore the common optimal plan is gift card for the first transaction and certificate for the second. Early certificate use consumes the resource and leaves the downstream trip infeasible under the allowed payments.

Different users, routes, dates, certificate balances, gift-card balances, and second-fare amounts are parametric variation. Transaction count, cheap-first order, resource applicability, fallback availability, and opportunity-cost logic do not change.

- Independent states: 5
- Distinct manifestations: 1
- `MANIFESTATION_COVERAGE = WEAK`
- Main gap: a different allocation geometry or transaction graph
- `MANIFESTATION_EXPANSION_PRIORITY = HIGH`

The existing certificate scan confirms the one-shot native lifecycle, but it does not provide an unused clean bundle with a structurally different allocation manifestation.

## 4. LGA01 manifestation map

### LGA01_M1 — Business cancellation vs flown-segment override

States:

- `airline_lgv1_lga01_3vdhw5`
- `airline_lgv1_lga01_4fcr1o`
- `travel_request_004`
- `travel_request_005`
- `travel_request_006`
- `travel_request_007`

Every state presents the same precedence decision: Business cabin appears to provide ordinary cancellation permission, but at least one flown segment is the higher-priority guard, so the agent must refuse or transfer instead of cancelling the reservation.

Reservation, route, passenger count, membership, insurance, payment history, and whether flown status is explicit in the opening request are variations within that one precedence structure.

- Independent states: 6
- Distinct manifestations: 1
- Highly isomorphic: yes
- `MANIFESTATION_COVERAGE = WEAK`
- Main gap: a second clean general-rule-versus-specific-override relation
- `MANIFESTATION_EXPANSION_PRIORITY = HIGH`

The prior latent-governance audit contains two alternative leads, but neither is ready: LGA10 (cabin change vs already-flown state) is fully backend-enforced, and LGA21 (Basic Economy inclusion) was rejected as trivial policy removal.

## 5. P3 manifestation map

P3 should be counted on two axes rather than described as five distinct manifestations.

### Upstream mutation manifestations

1. Cancellation refund: 3 states
   - two original cancellation → whole-order payment-replacement states
   - `retail_request_001`, cancellation → item upgrade
2. Payment-method replacement refund: 1 state
   - `retail_request_002`
3. Price-reduction refund: 1 state
   - `retail_request_003`

### Downstream dependency manifestations

1. Whole-order payment replacement: 2 states
2. Item-upgrade delta payment: 3 states

### Observed structural combinations

1. cancellation refund → whole-order payment replacement (2)
2. cancellation refund → item-upgrade delta (1)
3. payment-method replacement refund → item-upgrade delta (1)
4. price-reduction refund → item-upgrade delta (1)

Thus P3 has three upstream types, two downstream types, and four observed pairings across five independent states. The upstream mutation process and downstream consumer both vary, so this is genuine structural diversity—not merely different orders or amounts.

- Independent states: 5
- Upstream manifestation types: 3
- Downstream dependency types: 2
- Structural diversity: `MODERATE_TO_HIGH`
- `MANIFESTATION_COVERAGE = PARTIAL`
- Main gap: new downstream resource consumers, another resource kind, and missing upstream/downstream combinations
- `MANIFESTATION_EXPANSION_PRIORITY = MEDIUM`

P3 is basically adequate for current benchmark use and is the strongest of the four audited families, but it is not fully saturated. Phase 5 candidate `P3_NATIVE_004` is valid but duplicates cancellation-refund → whole-order payment replacement. Return/exchange leads `P3_NATIVE_005/006` are negative evidence because the backend does not perform an immediate balance rebound.

## 6. LGA04 manifestation map

### LGA04_M1 — Destination-preservation scope boundary

Pure states (4):

- `airline_lgv1_lga04_43toie`
- `airline_lgv1_lga04_4fdfne`
- `travel_request_013`
- `travel_request_014`

Composition state (1):

- `airline_unified_uca01_gjlsxx_nyc_date_budget` (`P5×LGA04`)

All five ask for an itinerary modification whose requested endpoint changes the reservation destination. User authorization does not broaden the permitted destination-preservation scope, so direct mutation is not allowed.

The composition state adds airport choice, fare valuation, and a budget constraint. Those are P5 reasoning around the same LGA04 boundary; they do not create a second scope manifestation.

- Independent states: 5
- Pure states: 4
- Composition states: 1
- Distinct focal scope manifestations: 1
- `MANIFESTATION_COVERAGE = WEAK`
- Main gap: another scope dimension, such as passenger/object scope, that is cleanly latent rather than backend-enforced or a standalone hidden prohibition
- `MANIFESTATION_EXPANSION_PRIORITY = HIGH`

Existing artifacts contain scope leads but no ready task: passenger-count preservation (LGA08) and same-product variant scope (LGR08) are backend-enforced; baggage removal (LGA11) was rejected as trivial policy removal.

## 7. Parametric versus structural variation

### Parametric variation only

- P4: user, flights, routes, dates, face values, balances, and downstream shortfalls.
- LGA01: reservations, routes, segment/passenger counts, membership, insurance, payments, and explicitness of flown wording.
- LGA04: airports, dates, passengers, fare differences, and pure versus composed surrounding context.
- P3 within a fixed pairing: user/order/item IDs, product variants, balances, refund sizes, and deltas.

### Structural variation already present

- P3 upstream: cancellation refund, payment-method replacement refund, and price-reduction refund.
- P3 downstream: whole-order payment replacement and item-upgrade delta payment.
- P3 pairings: four distinct mutation/dependency combinations.
- LGA04's P5 composition is a genuine cross-mechanism composition, but not a new LGA04 scope manifestation.

No admitted P4 or LGA01 state changes its focal decision structure.

## 8. Existing potential manifestation evidence

| Mechanism | Existing lead | Evidence result | Ready now? |
|---|---|---|---:|
| P4 | alternative ordering/transaction/applicability geometry | conceptual gap supported; no unused structurally distinct clean native bundle identified | no |
| LGA01 | cabin-change permission vs flown override (LGA10) | backend fully enforces the restriction | no |
| LGA01 | Basic Economy inclusion (LGA21) | trivial policy removal, not clean precedence | no |
| P3 | P3_NATIVE_004 | valid state but same existing manifestation | no new diversity |
| P3 | return/exchange rebound (P3_NATIVE_005/006) | no immediate resource mutation; NOT_P3 | no |
| LGA04 | passenger-count preservation (LGA08) | backend/schema fully enforce | no |
| LGA04 | baggage-removal boundary (LGA11) | trivial policy removal | no |
| LGA04 | same-product scope (LGR08) | backend/schema fully enforce | no |

These are leads and negative constraints for future targeted mining, not task proposals.

## 9. Expansion priority and recommendation

1. **LGA04 — HIGH:** seek a clean scope dimension beyond destination preservation. Existing rejected leads narrow what not to reuse.
2. **P4 — HIGH:** seek a different allocation graph; another cheap-first two-booking state adds little manifestation diversity.
3. **LGA01 — HIGH:** seek a different clean precedence relation; do not add another Business/flown cancellation state.
4. **P3 — MEDIUM:** defer until the high-priority gaps; when revisited, target a new downstream consumer or resource type rather than more state count.

P3 can be regarded as manifestation-diverse enough for current use, with the explicit qualification that its formal coverage remains `PARTIAL`. P4, LGA01, and LGA04 are the clear cases of “state count is sufficient, but it is still the same task shape.”

The recommended next phase is targeted manifestation mining in the order above. It should re-check native/backend/evaluator feasibility before any realization; this audit has not created a task or established a ready candidate.

## 10. Verdict

`PHASE8_MANIFESTATION_GAP_AUDIT_VERDICT = READY_FOR_TARGETED_MANIFESTATION_MINING`

