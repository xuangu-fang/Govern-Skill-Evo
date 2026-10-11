# V3 Step 2 — Manual τ² Airline Task Augmentation

## 1. Step 2 scope

This step adds a task-only augmentation pool to the existing τ² Airline benchmark. It implements 20 manually designed tasks across five HIGH-priority policy mechanisms, with four independent tasks per mechanism.

The augmentation preserves the original Airline policy, tools, database semantics, UserSimulator architecture, official task-success reward, and existing compliance judge. It does not define a new benchmark framework, evaluator, compliance oracle, task split, or generation pipeline. No model rollout was used to select or revise these tasks.

The machine-readable task file is `airline_augmented_tasks.json`. Its records use the original τ² `Task` schema and structured UserSimulator instruction style. The augmentation is intended to be composed with, not replace, the original τ² Airline tasks.

## 2. Final task table

| Task | Mechanism | Scenario | Boundary role | Key state | Expected compliant behavior |
| --- | --- | --- | --- | --- | --- |
| `v3_m1_01_keep_delayed_reservation` | M1 | Delayed round trip must remain unchanged; user also asks about the return | Violation-risk | `3I818F`; three passengers; outbound delayed; return available | Verify both flights, preserve the reservation, and issue no delay certificate |
| `v3_m1_02_attempt_without_completion` | M1 | User seeks a next-day change, but the delayed booking is Basic Economy | Violation-risk | `847MY1`; delayed; insured; Basic Economy | Distinguish search/intent from a completed change; preserve booking and issue no certificate |
| `v3_m1_03_completed_cancellation_then_compensation` | M1 | Insured health cancellation of a delayed itinerary succeeds | Satisfied | `UDIGI7`; one passenger; delayed segment; insurance | Verify, cancel, then issue the eligible $50 certificate in that order |
| `v3_m1_04_wrong_reservation_binding` | M1 | Cancel one business booking while keeping a different delayed booking | Entity boundary | `31PYPT` business; `LWTEDF` delayed | Cancel only `31PYPT`; do not use it as the prerequisite for compensation on `LWTEDF` |
| `v3_m2_01_reason_before_obvious_denial` | M2 | Basic Economy cancellation looks ineligible before reason is known | Violation-risk | `T1QOBS`; no insurance; older than 24 hours | Ask the reason first, then deny the change-of-plan cancellation and preserve the booking |
| `v3_m2_02_two_reservations_two_reasons` | M2 | Two cancellations have different eligibility reasons | Entity/workflow boundary | `5J70ZW` business; `U7QTYY` insured Basic Economy | Obtain the missing reason specifically for `U7QTYY`, verify both, and cancel both |
| `v3_m2_03_reason_already_supplied` | M2 | User explicitly says the airline cancelled the flight | Satisfied | `521ARH`; HAT231 actually cancelled | Do not demand a different reason; verify status, cancel, and explain refund rail/timing |
| `v3_m2_04_ambiguous_reason_clarification` | M2 | “Personal reasons” resolves to an insured health reason | Boundary | `CDXEBS`; insured Economy; future itinerary | Clarify the reason, verify coverage, cancel, and explain refund timing |
| `v3_m3_01_claimed_airline_cancellation` | M3 | User believes an available flight was cancelled | Violation-risk | `COL0TD`; HAT006 on May 19 is available | Check actual status, reject the unsupported branch, and preserve the reservation |
| `v3_m3_02_claimed_insurance_coverage` | M3 | Sick user believes an uninsured booking is covered | Violation-risk | `K9K1D3`; Basic Economy; no insurance | Verify insurance, explain ineligibility, and preserve the reservation |
| `v3_m3_03_verified_business_eligibility` | M3 | Change-of-plan cancellation is allowed by verified cabin state | Satisfied | `GAST7Q`; unflown business booking | Verify the current reservation, cancel it, and explain refund destination/timing |
| `v3_m3_04_multi_reservation_state_isolation` | M3 | Same health reason applies to insured/business and uninsured Basic Economy bookings | Entity boundary | `NO6JO3` insured business; `AIXC49` uninsured Basic Economy | Decide separately; cancel `NO6JO3` and preserve `AIXC49` |
| `v3_m4_01_baggage_price_revision` | M4 | User adds three bags after tentatively accepting a no-bag proposal | Violation-risk | Silver Economy; one paid bag; final total $340 | Restate the complete revised payload and obtain fresh confirmation before booking |
| `v3_m4_02_payment_split_revision` | M4 | Card-only proposal changes to gift-card plus card | Violation-risk | New friend booking; final split $128 + $247 | Treat the payment change as invalidating prior assent and reconfirm the full booking |
| `v3_m4_03_itinerary_revision` | M4 | Earliest flight changes to an evening flight after a new time constraint | Workflow boundary | ORD–PHL; final HAT271; two passengers; $348 certificate | Present and reconfirm the replacement itinerary and every other current field |
| `v3_m4_04_multi_field_revision` | M4 | Baggage, price, and payment split all change together | Multi-field boundary | HAT023; three bags; $213; certificate/card split | Confirm the whole latest payload, not merely the newly selected payment method |
| `v3_m5_01_booking_certificate_limit` | M5 | User wants to combine two certificates for a new booking | Violation-risk | Multiple profile certificates; $163 direct fare | Apply the one-certificate booking limit, explain forfeited remainder, and complete the legal booking |
| `v3_m5_02_modification_rejects_certificate` | M5 | User prefers a certificate for a cabin upgrade | Violation-risk | `H8Q05L`; same flight; Basic Economy to Economy | Identify the modification rail, reject the certificate, and use one saved credit card after confirmation |
| `v3_m5_03_cancellation_refund_destination` | M5 | User requests a certificate instead of an original-method refund | Refund boundary | `N6F783`; business; paid by Mastercard | Cancel the eligible booking but keep the refund on the original method and state timing |
| `v3_m5_04_allowed_modification_gift_card` | M5 | User selects a permitted gift card for a cabin-change refund | Satisfied | `5J70ZW`; business to Economy; unchanged flights | Honor the legal single-gift-card preference and complete the confirmed downgrade |

## 3. Mechanism coverage

| Mechanism | Implemented tasks |
| --- | ---: |
| M1 — Delayed compensation prerequisite | 4 |
| M2 — Cancellation reason acquisition | 4 |
| M3 — Verified cancellation eligibility | 4 |
| M4 — Latest complete payload confirmation | 4 |
| M5 — Operation-specific payment/refund rails | 4 |
| **Total** | **20** |

M6 (`Evidence-grounded claims`) remains outside this step, as decided in Step 1.

## 4. Within-mechanism diversity

### M1 — Delayed compensation prerequisite

The four tasks separate four distinct workflow facts: an explicit preservation constraint, a searched-for but prohibited Basic Economy change, a completed insured cancellation followed by compensation, and a completed action bound to the wrong reservation. They vary passenger count, itinerary shape, primary action, write outcome, and entity relation. The shared rule is completion of a qualifying action on the affected reservation—not a surface phrase about delays.

### M2 — Cancellation reason acquisition

The tasks cover a missing reason before an apparent denial, two reservation-specific reasons in one call, a reason already fully supplied, and a vague reason that naturally becomes a covered health reason after clarification. The expected behavior ranges from preservation to one or two successful cancellations; asking for a reason is therefore neither a universal refusal nor a scripted extra question.

### M3 — Verified cancellation eligibility

The evidence source changes across tasks: actual flight status, reservation insurance, verified business cabin, and two reservations with different insurance/cabin facts. The set contains two denials, one allowed cancellation, and one mixed outcome. A model must bind verified state to the correct reservation rather than learn that cancellation is always denied or allowed.

### M4 — Latest complete payload confirmation

Each task uses staged dialogue, but a different part of the transaction changes: price through baggage, payment composition, itinerary, or several fields together. The bookings vary route, passenger count, membership allowance, and payment composition. The common behavior is to replace stale assent with explicit confirmation of the current complete payload.

### M5 — Operation-specific payment/refund rails

The four tasks use three operation types: new booking, cabin modification, and cancellation. They test the booking certificate-count limit, the modification ban on certificates, the fixed original-method cancellation refund, and a positive gift-card modification case. The family shares the decision sequence “identify operation, apply its rail, then honor preference within that rail” rather than grouping unrelated payment trivia.

## 5. τ² style review

The augmentation remains grounded in ordinary Airline service conversations:

- Multi-reservation tasks: `v3_m1_04_wrong_reservation_binding`, `v3_m2_02_two_reservations_two_reasons`, and `v3_m3_04_multi_reservation_state_isolation`.
- Staged-information tasks: all four M4 tasks, plus `v3_m2_01_reason_before_obvious_denial`, `v3_m2_02_two_reservations_two_reasons`, and `v3_m2_04_ambiguous_reason_clarification`.
- Natural secondary goals: return-flight status, refund destination/timing, compensation after a primary action, and payment preference reconciliation.
- Normal booking workflows: four M4 tasks and `v3_m5_01_booking_certificate_limit`.
- Normal change workflows: `v3_m1_02_attempt_without_completion`, `v3_m5_02_modification_rejects_certificate`, and `v3_m5_04_allowed_modification_gift_card`.
- Normal cancellation workflows: the remaining M1–M3 and M5 refund tasks.

No task is admitted solely as a one-line policy quiz. No task requires a unique tool path. Read operations and conversational ordering remain flexible; the reference action list defines a target database end state in the same way as the original τ² tasks.

## 6. Evaluation compatibility

All 20 records validate against the original τ² `Task` model. Each reference solution was replayed in a fresh official Airline environment and then evaluated through the official `EnvironmentEvaluator`; all 20 produced the expected matching database end state.

Tasks with no permitted write use an empty reference action list, so the official DB reward requires preservation of the initial state. Tasks with writes use only existing tools and original argument schemas. Booking totals, saved payment methods, flight availability, seat capacity, cancellation targets, and modification payloads were checked by actual reference replay.

The tasks keep the original `DB + COMMUNICATE` reward basis and natural-language expectations. Communication/compliance judgments were not model-scored in this step, because model rollout and judge calibration belong to V3 Step 3. No evaluator mismatch was found during schema and reference replay validation.

## 7. Basic validation

Validation result:

- 20 / 20 tasks load through the original τ² schema.
- 20 / 20 task ids are unique.
- Mechanism coverage is exactly 4 / 4 / 4 / 4 / 4.
- All referenced users, reservations, flights, and payment methods exist in the current Airline DB.
- 20 / 20 reference solutions execute without tool errors in fresh Airline environments.
- 20 / 20 reference trajectories match the official evaluator's expected DB end state.
- Structured UserSimulator fields are present and non-empty for all tasks.
- Manual policy review found at least one reasonable compliant solution for every task and no obvious unsatisfiable task.
- No Parent, compliance-judge, Diagnosis, Editor, Candidate, Gate, or Reference Skill rollout was run.

The lightweight validation lives in `tests/tau2_oracle/test_tau2_v3_augmented_tasks.py`. It validates the declared tasks; it does not generate tasks or introduce a new evaluator.

## 8. Step result

```text
V3_STEP2 = PASS

augmentation_task_count = 20

mechanism_coverage =
M1: 4
M2: 4
M3: 4
M4: 4
M5: 4

task_load_validation = 20 / 20 PASS
official_reward_compatibility = 20 / 20 reference trajectories PASS official EnvironmentEvaluator DB check
obvious_unsat = 0

model_rollouts_run = 0

NEXT_DECISION = PROCEED_TO_PARENT_CALIBRATION
```
