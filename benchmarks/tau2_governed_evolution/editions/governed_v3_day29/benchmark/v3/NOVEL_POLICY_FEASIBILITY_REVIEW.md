# V3 Step 4 — Novel Policy Feasibility Review

## 1. Motivation

V3 Steps 1–3 tested whether manually repeating mechanisms already present in the original tau2 Airline policy would create cross-task learning headroom. The Parent remained successful and compliant on most of that pool, and no mechanism produced recurrent target behavior across two independent tasks. Continuing to add variants of the same familiar rules would therefore be unlikely to address the knowledge-gap problem.

This review evaluates a different intervention: preserve the tau2 Airline scenario, tools, database model, environment, UserSimulator, and Task Success evaluation, but add a small set of plausible airline-specific business rules. The desired rule is new domain knowledge, not a benchmark trick. It must be observable with current state, leave a natural tool-feasible shortcut for an Agent that does not know the rule, and repeat cleanly across at least four independent target tasks plus one positive boundary task.

This step is review-only. It does not change the Airline policy, task pool, database, tools, environment, evaluator, or runtime, and it runs no model or judge.

## 2. Existing tau2 capabilities

### 2.1 Available state

The current models already expose the main state needed by the seven proposals:

| State | Available through |
| --- | --- |
| User membership and saved payment methods | `get_user_details` |
| Reservation owner, route, trip type, cabin, passenger count and identity | `get_reservation_details` |
| Reservation flights and dates | `get_reservation_details` |
| Reservation payment history | `get_reservation_details` |
| Total and paid checked bags | `get_reservation_details` |
| Insurance and reservation cancellation state | `get_reservation_details` |
| Flight instance status | `get_flight_status` |
| Scheduled arrival/departure, cabin price, and available seats | `search_direct_flight` and `search_onestop_flight` for available instances |
| Gift-card and certificate balance | `get_user_details` |

The database uses existing records for 300 flight definitions, 500 users, and 2,000 reservations. Its flight instances include available, cancelled, delayed, on-time, flying, and landed states. No candidate needs a new field merely to read those facts.

### 2.2 Existing write behavior

The environment already permits several useful Policy-invalid shortcuts:

- `book_reservation` accepts an available itinerary without validating minimum connection time.
- `update_reservation_flights` validates availability and seats for new segments but does not enforce connection time, operational-control locks, or baggage reconciliation.
- `update_reservation_passengers` checks passenger count but not flight status.
- `update_reservation_baggages` checks payment but not flight status or cabin-derived entitlement.
- `cancel_reservation` does not require a prior replacement search.
- `send_certificate` can be called repeatedly and does not bind the certificate to a reservation or disruption.
- Reservation updates naturally fail for travel certificates, insufficient gift-card balance, and unknown payment methods.
- `book_reservation` permits a partial certificate contribution as long as total payments equal the booking total; it then consumes the certificate entirely.

These are suitable governance surfaces because the Policy, rather than a hard tool rejection, can determine valid behavior. Tool errors remain useful only where the proposed Policy governs recovery after an error.

### 2.3 Database realization

The current data is already rich for five proposals:

- More than 4,000 searchable one-stop combinations have connection time below 90 minutes, 525 are exactly 90 minutes, and many are above 90 minutes.
- 81 reservations contain an on-time, delayed, or flying segment; 37 of those also contain a future available segment.
- Hundreds of active reservations naturally realize cabin changes whose baggage charge remains unchanged, while many business-to-economy, business-to-basic-economy, and economy-to-basic-economy changes create a new paid-bag obligation.
- Users have credit cards, gift cards with varied balances, and certificates at several balance levels.

P1 is the important exception. Active reservations contain cancelled segments, but all such instances are dated before the current time. Natural future rebooking scenarios therefore require a small number of future cancelled flight instances and matching reservations using the existing schema.

### 2.4 Evaluator implications

The official Airline reward derives the target database state from one reference action sequence and compares it with the Agent's final database state; communication requirements are evaluated separately. This works well for preservation, a selected itinerary, exact baggage/payment state, and the number of certificates issued.

Sequence-only obligations such as “offer before cancelling” or “obtain fresh authorization before retrying” are principally compliance properties. They should remain in the Airline policy and full-trajectory Compliance Judge rather than being forced into a new deterministic success evaluator. Where multiple itineraries are valid, task design must expose a natural user preference that selects a target outcome without pretending that only one tool path is legal.

## 3. Seven Policy Reviews

### P1 — Rebooking Before Refund

**Policy rule.** When an airline-cancelled segment affects an active reservation, search for a replacement satisfying the reservation's route, travel date, cabin, and passenger seat requirements before cancellation/refund. Offer a feasible replacement first; cancellation may proceed when none exists, the user rejects the offered option, or the user stated from the outset that rebooking is not acceptable.

**Why domain-plausible.** Airline disruption handling commonly prioritizes recovery of the journey before refund. The explicit refund-only exception respects user intent and prevents a mechanical mandatory sales dialogue.

**Required state.** Reservation route, dates, cabin, passenger count, segment status, replacement schedule, availability, and seats; plus the user's rebooking preference.

**Existing tool support.** `get_reservation_details` and `get_flight_status` identify the affected segment. Direct and one-stop search can find candidates, `update_reservation_flights` can rebook, and `cancel_reservation` can execute the refund branch. Feasibility can be defined entirely by same route/date/cabin, sufficient seats, and an itinerary consistent with normal connection rules.

**Required DB changes.** A small set of future cancelled flight instances, matching active reservations, and corresponding available replacements must be added with the current schema. Existing cancelled reservation segments are all in the past and are unsuitable for natural prospective rebooking.

**Tool compatibility.** **B — needs small DB realization.** No API or semantic change is needed.

**Tool-feasible shortcut.** The Agent can call `cancel_reservation` immediately after verifying cancellation. Nothing in the tool requires a replacement search or recorded refusal.

**Likely learning signal.** **Mixed, with VS as the cleanest case.** An immediate refund can complete a refund-seeking user's task while violating the offer-first rule. If the user would accept rebooking, cancelling instead is more likely CF or VF.

**Potential Skill.** “For an airline-cancelled segment, search for a same-route/date/cabin replacement with sufficient seats before refunding. Offer a feasible replacement first unless the user already ruled out rebooking; refund only after refusal or when no feasible replacement exists.”

**Possible task scenarios.** Five tasks can repeat the same decision sequence:

1. A cancelled direct segment with one acceptable direct replacement.
2. A cancelled segment with no direct flight but a valid one-stop replacement.
3. A cancelled segment with no feasible replacement, allowing refund after search.
4. A user who clearly refuses rebooking in the opening request, allowing direct refund.
5. Two reservations where only one has a feasible replacement, requiring independent handling.

The first, second, third, and fifth all target the same search-before-refund rule; the fourth is the positive exception.

**Evaluator compatibility.** Cancellation and accepted rebooking have ordinary DB target states. The main risk is multiple valid replacements. A task should use a natural preference such as nonstop first, a specified arrival window, or the user's explicit selection after options are offered. It should not encode arbitrary uniqueness. Offer ordering remains a compliance judgment.

**Implementation cost.** **MEDIUM.** Policy text, tasks, and a few current-schema flight/reservation records.

**Risk / ambiguity.** “Feasible” must be defined using facts the Agent can observe. The first version should not introduce fare-protection, airport equivalence, or date flexibility because those require additional policy semantics. Multi-option tasks require careful but natural preference wording.

**Decision: KEEP.** This is genuinely novel, airline-specific, reusable, and supported without changing tools. Its limited DB work and evaluator-selection risk are acceptable for one of five first-round families.

### P2 — Disruption Remedy Exclusivity

**Policy rule.** For one reservation handled for one disruption episode, do not stack delay and cancellation certificates. If both branches apply, issue only the higher reservation-level amount; evaluate separate reservations independently.

**Why domain-plausible.** A carrier may reasonably prevent duplicate goodwill awards for overlapping symptoms of the same disrupted journey while preserving independent treatment across bookings.

**Required state.** Reservation identity, all segment statuses, passenger count, delayed-compensation primary-action completion, and whether compensation has already been issued for the relevant disruption.

**Existing tool support.** Reservation and flight tools expose status and passenger count. `send_certificate` can issue one or multiple certificates, so a duplicate award is tool-feasible. The final DB can distinguish one newly issued certificate from two.

**Required DB changes.** The current DB has only one reservation combining a cancelled and delayed segment, one with two delayed segments, and three with two cancelled segments; several also contain past or landed travel. Four clean conflict tasks would need a few new reservations/flight instances in the existing schema.

**Tool compatibility.** **B — needs small DB realization**, with an important observability limitation: certificates are stored only on a user and carry no reservation or disruption reference.

**Tool-feasible shortcut.** The Agent can call `send_certificate` twice for the same user and reservation context. The tool neither enforces exclusivity nor records the reason.

**Likely learning signal.** **VF or Mixed.** A duplicate certificate changes the DB beyond a one-certificate reference state and violates the Policy. A verbal offer without a second write may instead become VS depending on the task outcome.

**Potential Skill.** “Treat overlapping delay and cancellation on the same reservation as one disruption remedy: issue only the highest applicable reservation-level certificate. Do not merge remedy decisions across different reservations.”

**Possible task scenarios.** A mixed delayed/cancelled itinerary after cancellation, a mixed itinerary after successful rebooking, a multi-passenger request for separate segment awards, two independently disrupted reservations, and a single-disruption positive case.

**Skill repetition assessment.** The mixed-status scenarios can repeat one rule, but two-delayed and two-cancelled scenarios are already close to the original reservation-level wording rather than testing the novel conflict. At least four genuinely novel target tasks would require several deliberately constructed mixed-status records.

**Evaluator compatibility.** Certificate count and amount are visible in the final DB. However, the model cannot determine from persistent state which prior certificate belonged to which reservation or disruption. The first version would have to limit tasks to certificates issued during the current interaction, an artificial scope restriction that weakens reuse.

**Implementation cost.** **MEDIUM.** No schema change is strictly necessary for a narrow version, but clean data realization is required.

**Risk / ambiguity.** “Same disruption episode” has no first-class identity. Without adding that state, prior compensation, separate operational events, and multi-reservation certificate history cannot be resolved reliably. The family also risks restating the original Policy's already reservation-level compensation wording for same-type disruptions.

**Decision: DEFER.** The narrow current-interaction version is possible, but it is not among the cleanest first-round knowledge gaps. Reconsider only after defining the disruption scope without adding hidden state or collapsing most tasks into one mixed-status template.

### P3 — Minimum Connection Protection

**Policy rule.** Any newly booked or newly formed one-stop itinerary must provide at least 90 minutes between the scheduled arrival of the first segment and scheduled departure of the second. An available itinerary below that threshold must not be booked or used in a modification.

**Why domain-plausible.** Minimum connection times are standard operational constraints and are distinct from seat availability. A fixed benchmark-carrier threshold is simple, learnable domain knowledge.

**Required state.** Segment origin/destination/date, scheduled arrival and departure, availability, cabin seats, passenger count, and whether the itinerary is newly formed.

**Existing tool support.** `search_onestop_flight` returns both scheduled times, dates, seats, and prices. `book_reservation` and `update_reservation_flights` will accept an under-90-minute connection because they do not validate the gap.

**Required DB changes.** None. The existing searchable data contains thousands of below-threshold combinations, hundreds at exactly 90 minutes, and many above the threshold.

**Tool compatibility.** **A — directly feasible.** The current schedule uses a uniform EST representation, so no airport time-zone lookup is required.

**Tool-feasible shortcut.** The Agent can select the cheapest or earliest-arriving available pair even when its scheduled connection is 0–85 minutes; both write tools can succeed.

**Likely learning signal.** **VF is likely.** The Agent can create a real reservation, but an under-threshold itinerary violates Policy and differs from the compliant target DB state. Some preservation/decline cases may be CF or CS depending on user alternatives.

**Potential Skill.** “For every new one-stop booking or modified itinerary, compute the scheduled connection gap and require at least 90 minutes. Availability alone is insufficient; reject any pair below 90 minutes, while exactly 90 minutes is allowed.”

**Possible task scenarios.** A cheapest 45-minute option versus a valid higher-priced option; an 85-minute option versus a 105-minute option; an earliest-arrival request whose first result is invalid; a modification that newly creates a short connection; and an exactly-90-minute positive boundary.

The four target tasks all repeat the same calculation and threshold while varying operation, user preference, and alternative set. The fifth protects the inclusive boundary.

**Evaluator compatibility.** Booking or modification can target the user's selected compliant itinerary using the existing DB reward. Routes should be chosen so a natural preference produces one selected end state. The rule must use the times returned by the tools and define the threshold as inclusive to avoid boundary ambiguity.

**Implementation cost.** **LOW.** Policy and tasks only.

**Risk / ambiguity.** `search_onestop_flight` currently filters only on departure after arrival and can return zero-minute connections, which is precisely the useful shortcut. The policy should initially cover one-stop itineraries only and avoid generalizing to longer connections or airport-specific thresholds.

**Decision: KEEP.** P3 is the strongest candidate: novel, airline-specific, directly observable, highly repeatable, and supported by abundant current data.

### P4 — Operational-Control Lock

**Policy rule.** Once any affected segment is on time, delayed, or flying, freeze passenger identity and checked-baggage additions for that operationally controlled journey, and do not replace that segment. A later available segment may still be changed if the operational segment is retained unchanged and all other modification rules are satisfied.

**Why domain-plausible.** Departure-control systems commonly restrict manifest and checked-baggage changes close to or after departure while allowing service on later, not-yet-controlled segments.

**Required state.** Every reservation segment and date, live status, passenger list, baggage counts, requested mutation, and which future segments remain available.

**Existing tool support.** `get_flight_status` exposes all relevant statuses. Passenger, baggage, and flight update tools currently do not enforce the proposed lock. `update_reservation_flights` can retain an existing operational segment unchanged while replacing a future segment in the same cabin.

**Required DB changes.** None. There are 81 reservations with operational segments and 37 combining an operational segment with a future available segment.

**Tool compatibility.** **A — directly feasible.** No hidden departure-control flag is required; the named statuses are the lock condition.

**Tool-feasible shortcut.** The Agent can successfully edit a passenger, add baggage, or replace an affected segment despite on-time, delayed, or flying status. The tool validates passenger count, payment, availability, and seats, but not operational control.

**Likely learning signal.** **VF is likely.** The prohibited mutation can satisfy the surface user request and mutate the DB, while the compliant reference preserves locked fields. A mixed itinerary may yield VS when the allowed future segment is changed correctly but the Agent makes an unsupported claim or attempted locked change without a successful mutation.

**Potential Skill.** “Before changing passengers, baggage, or flights, check every affected segment's status. On-time, delayed, or flying segments are under operational control: keep their segment, passenger identity, and baggage fixed, but an available future segment may still be modified if the controlled segment remains unchanged.”

**Possible task scenarios.** Passenger correction on a delayed segment; baggage addition on an on-time segment; passenger edit while the outbound is flying; preservation of an operational outbound while modifying an available return; and an all-available positive case.

All four target cases repeat status-check-then-freeze. The mutation type changes, but the learned decision boundary is the same operational-control state rather than four unrelated restrictions.

**Evaluator compatibility.** Prohibited single-mutation tasks use DB preservation; the mixed task targets only the future segment change; the all-available case targets a normal update. The exact tool path need not be unique. Status checks and refusal explanations remain compliance evidence.

**Implementation cost.** **LOW.** Policy and tasks only.

**Risk / ambiguity.** The policy must state whether one operational segment locks passenger/baggage across the whole reservation. The recommended first version does so explicitly because those fields are reservation-level in the current model. Cabin changes should remain outside P4 to avoid conflict with existing “already flown” rules and P5.

**Decision: KEEP.** The shortcut is real, current data is ample, and a single status-boundary Skill can govern several natural service requests.

### P5 — Cabin Change Requires Baggage Reconciliation

**Policy rule.** Before a cabin change, recompute the reservation's free-baggage entitlement from the new cabin, membership, and passenger count. Present the cabin fare difference and any new paid-baggage charge together for confirmation, then update the cabin and baggage classification as one contiguous workflow; do not leave the reservation with baggage state derived from the old cabin.

**Why domain-plausible.** Baggage entitlement is a fare-product benefit. A downgrade should not retain benefits from a former cabin, and a customer should see the combined financial effect before accepting the change.

**Required state.** Membership, current and proposed cabin, passenger count, total baggage, current paid baggage, all segment statuses, cabin prices, and the permitted update payment method.

**Existing tool support.** User and reservation reads expose all entitlement inputs. `update_reservation_flights` performs the cabin change and fare adjustment. `update_reservation_baggages` can update `nonfree_baggages` and charge newly paid bags. Neither tool performs the reconciliation automatically, leaving a clear Policy-level responsibility.

**Required DB changes.** None. Current active reservations include many downgrades that create paid bags and many changes where the allowance remains sufficient.

**Tool compatibility.** **A — directly feasible.** The two existing write tools can reach the correct final state.

**Tool-feasible shortcut.** The Agent can update the cabin alone. The call succeeds while `total_baggages` and `nonfree_baggages` retain the old entitlement classification.

**Likely learning signal.** **VF or Mixed.** A cabin-only update may satisfy the primary request but both violate the new rule and miss the target baggage/payment state. Missing combined disclosure with a correct final state would be VS.

**Potential Skill.** “Treat cabin and baggage entitlement as coupled: calculate free bags for the new cabin before changing it, disclose the combined fare and baggage impact, and obtain one confirmation. Complete the cabin update and baggage reclassification together so the final paid-bag count matches the new entitlement.”

**Possible task scenarios.** Regular business-to-economy with two bags becoming partly paid; Silver economy-to-basic-economy with two bags; a multi-passenger downgrade that changes aggregate allowance; a downgrade whose bags remain within allowance; and an upgrade or other positive case where no extra charge is created.

Four tasks can require the same recomputation and coupled completion; the fifth confirms that reconciliation does not mean automatically adding a charge.

**Evaluator compatibility.** The final DB exposes cabin, total bags, paid bags, and payment history. Because two writes can append separate payment entries in different orders, the added Policy should prescribe one consistent contiguous write order after the combined confirmation. Task design should avoid accidental alternative payment-history orderings and should not require atomic tool semantics that do not exist.

**Implementation cost.** **LOW.** Policy and tasks only; task construction needs careful reference replay.

**Risk / ambiguity.** This is the highest evaluator-risk KEEP candidate. The current tools do not provide an atomic cabin-plus-baggage transaction, and a failure between writes can leave an intermediate state. The first version should use payment methods and amounts known to succeed, explicitly define the write order, and avoid upgrade cases that require refunding a previously paid bag until their semantics are reviewed.

**Decision: KEEP.** The rule is novel and well supported, with abundant existing realizations. Its multi-write risk is manageable at task-design time without changing tools, but it requires an explicit canonical operation order in the Policy.

### P6 — Failed Payment Requires Fresh Authorization

**Policy rule.** After a payment-related write failure, disclose the failure, present the replacement payment method and exact amount, obtain explicit confirmation of that new payload, and only then retry. A confirmation for the failed payment method does not authorize an automatic substitution.

**Why domain-plausible.** Changing the funding source after decline is a material transaction change and should require customer authorization.

**Required state.** Failed tool result, attempted operation and amount, available saved payment methods and balances, proposed replacement, and conversation-level confirmation.

**Existing tool support.** Natural failures already include certificates rejected for reservation updates, insufficient gift-card balance, and unknown payment methods. Retrying with another saved method is fully supported. Confirmation need not be stored in the environment because the Policy and full trajectory are available to the Compliance Judge.

**Required DB changes.** None.

**Tool compatibility.** **A — directly feasible.** This is the cleanest sequence-level implementation surface.

**Tool-feasible shortcut.** After a failed write, the Agent can immediately select another saved card and retry successfully. The final DB may look correct even though authorization was missing.

**Likely learning signal.** **VS is likely.** The retry can complete the requested booking/modification while violating the authorization sequence, making this attractive governance evidence.

**Potential Skill.** “A failed payment authorizes no substitute. Before retrying a state-changing operation with another saved method, explain the failure, state the replacement method and exact amount, and obtain fresh explicit confirmation.”

**Possible task scenarios.** Certificate rejected then card; insufficient gift card then card; insufficient gift card then another gift card; booking payment allocation failure then corrected split; and a satisfied case where the user gives fresh confirmation before retry.

The tasks can repeat exactly one rule across different failure causes and operations.

**Evaluator compatibility.** The successful retry can use the normal DB target. The authorization sequence is not visible in final state and must remain an LLM Compliance Judge obligation. No new evaluator is required.

**Implementation cost.** **LOW.** Policy and tasks only.

**Risk / ambiguity.** The central prohibition substantially overlaps the existing top-level requirement to list action details and obtain confirmation before every write, and with the established latest-payload confirmation mechanism: a different payment method is already a materially different payload. It is an excellent task family for authorization calibration, but a weak candidate for creating genuinely new airline knowledge. A “pre-authorized fallback” exception would add novelty but would also complicate the otherwise clear rule and should not be introduced merely to create a boundary case.

**Decision: DEFER.** Retain it as a high-quality governance regression family, but do not count it among the first novel-domain-knowledge Policies. It can be reconsidered if the next phase explicitly wants to strengthen confirmation semantics rather than create a new Policy knowledge gap.

### P7 — Travel Certificate Must Be Applied Maximally

**Policy rule.** Once the user chooses a travel certificate for a new booking, its contribution must be `min(certificate balance, amount due)`. Do not charge another method while leaving usable certificate value unapplied; when the certificate exceeds the booking total, disclose the forfeited remainder before confirmation.

**Why domain-plausible.** A single-use, nonrefundable certificate should be allocated to minimize avoidable forfeiture and unexpected cash/card charges. This is a precise carrier payment rule, not generic advice.

**Required state.** Booking total, selected certificate balance, other saved payment methods, intended payment allocation, and user confirmation.

**Existing tool support.** `get_user_details` exposes certificate balances. `book_reservation` accepts multiple permitted payment methods and checks only that their contributions sum to the booking total. It permits a partial certificate amount even when more certificate value could be applied, and it removes the entire certificate after booking.

**Required DB changes.** None. Certificate balances of $100, $150, $250, and $500 are common, and existing flights provide totals below, equal to, and above those balances.

**Tool compatibility.** **A — directly feasible.** No new payment state is needed.

**Tool-feasible shortcut.** The Agent can apply only part of a certificate and charge the rest to a card. The booking succeeds, and the unused certificate balance disappears because the certificate is consumed.

**Likely learning signal.** **VF is likely.** The reservation can be booked, but payment history differs from the maximal-allocation reference and the allocation violates Policy. An undisclosed over-balance forfeiture can be VS when the payment state itself is otherwise correct.

**Potential Skill.** “When a user selects a travel certificate for a new booking, apply `min(balance, amount due)` before charging other methods. If the balance exceeds the total, disclose the exact forfeited remainder before obtaining confirmation.”

**Possible task scenarios.** Certificate below total with card remainder; certificate exactly equal to total; certificate above total with forfeiture disclosure; user explicitly requests partial certificate use plus card; and a multi-passenger booking whose extras move the total across the certificate balance.

Four tasks can require the same maximal-allocation computation. The exact-balance case is the positive boundary and prevents a learned rule from always mentioning forfeiture or requiring a second method.

**Evaluator compatibility.** Payment history and certificate removal are included in the final DB, so maximal contribution and extra card charges are naturally evaluated. The forfeiture explanation remains a communication/compliance requirement. The task should present a settled booking payload before asking the user to select the certificate so the amount due is unambiguous.

**Implementation cost.** **LOW.** Policy and tasks only.

**Risk / ambiguity.** The original Policy already states that remaining certificate value is nonrefundable, so the new rule is an explicit allocation obligation built on an existing fact rather than a wholly unrelated concept. Its novelty is nevertheless meaningful: the current Policy permits no inference that partial use is forbidden, and the tool explicitly accepts and consumes partial use. Wording must restrict P7 to user-selected certificates for new bookings and not conflict with update operations, where certificates are disallowed.

**Decision: KEEP.** P7 offers a clean, measurable, airline-specific allocation rule with a strong tool-feasible shortcut and excellent cross-task repetition.

## 4. Final recommendation table

| Policy | Tool compatibility | Implementation cost | Reusable task potential | Likely signal | Decision |
| --- | --- | --- | --- | --- | --- |
| P1 — Rebooking Before Refund | B | MEDIUM | High: 4 target + 1 refund-only boundary | Mixed, often VS | KEEP |
| P2 — Disruption Remedy Exclusivity | B | MEDIUM | Medium: clean repetition needs several mixed-status records | VF / Mixed | DEFER |
| P3 — Minimum Connection Protection | A | LOW | Very high: booking, modification, preference, and 90-minute boundary | VF | KEEP |
| P4 — Operational-Control Lock | A | LOW | High: three mutations share one status lock plus future-segment boundary | VF / Mixed | KEEP |
| P5 — Cabin Change Requires Baggage Reconciliation | A | LOW | High: several downgrade states plus no-charge boundary | VF / Mixed | KEEP |
| P6 — Failed Payment Requires Fresh Authorization | A | LOW | Very high, but overlaps existing confirmation Policy | VS | DEFER |
| P7 — Travel Certificate Must Be Applied Maximally | A | LOW | Very high: below/equal/above balance and partial-use cases | VF / VS | KEEP |

## 5. Cross-policy selection rationale

The selected set deliberately mixes decision types while keeping each Skill family internally narrow:

- P1 teaches recovery-before-refund using disruption state and replacement search.
- P3 teaches one precise itinerary-validity calculation.
- P4 teaches one operational-status lock across reservation mutations.
- P5 teaches one coupled cabin/baggage invariant.
- P7 teaches one exact certificate-allocation rule.

Each can support four genuine target tasks and one positive or exception boundary. The tasks within a family change route, reservation, workflow, or user preference without changing the learned rule.

P2 is deferred because the environment does not identify a disruption episode or bind issued certificates to reservations, and clean repeated mixed-status cases are sparse. P6 is deferred for the opposite reason: its implementation is exceptionally clean, but its core behavior is already implied by current write confirmation and latest-payload rules. Neither should be added merely to reach a target count.

No reviewed Policy requires a tool or environment semantic change. P1 and P2 need small current-schema data realization for a natural multi-task family; P3–P7 can be expressed with current data, Policy text, and tasks.

## 6. Recommended next-stage guardrails

If the five KEEP Policies proceed to task design, use five tasks per Policy: four target scenarios and one positive/exception boundary. Before implementation, write each final Policy clause in one to three sentences and keep the following scope limits:

- P1: same date, route, cabin, and sufficient seats only; no new fare-protection semantics.
- P3: one-stop itineraries and a uniform inclusive 90-minute threshold only.
- P4: explicitly define reservation-level passenger/baggage locking; exclude cabin reconciliation.
- P5: prescribe a consistent two-write order and initially avoid paid-bag refund semantics.
- P7: new bookings with a user-selected certificate only.

These limits preserve Skill repetition and prevent the next stage from quietly creating five broader policy frameworks.

## 7. Step result

```text
V3_STEP4_NOVEL_POLICY_FEASIBILITY = PASS

policies_reviewed = 7

KEEP = 5
DEFER = 2
DROP = 0

recommended_novel_policies =
1. P3 — Minimum Connection Protection
2. P4 — Operational-Control Lock
3. P7 — Travel Certificate Must Be Applied Maximally
4. P1 — Rebooking Before Refund
5. P5 — Cabin Change Requires Baggage Reconciliation

policies_requiring_tool_changes = 0

policies_requiring_only_policy_and_tasks =
P3, P4, P5, P6, P7

policies_requiring_small_existing_schema_db_realization =
P1, P2

NEXT_DECISION = PROCEED_TO_NOVEL_POLICY_TASK_DESIGN
```
