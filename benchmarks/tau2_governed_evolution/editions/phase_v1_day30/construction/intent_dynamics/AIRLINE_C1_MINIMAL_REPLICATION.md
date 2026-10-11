# Step 3 — Airline C1 Minimal Replication

## 1. Goal

This step tests whether Airline C1 is recurrent across distinct native τ² Airline states rather than an artifact of reservation `M05KNL`. It realizes three additional Upfront ↔ Revision matched pairs while preserving the same mechanism:

```text
environment feedback
→ observable transaction-relevant intent revision
→ P0 proposal becomes stale
→ reconstruct P1
→ list P1 details
→ obtain explicit confirmation for P1
→ commit P1
```

No Airline Policy, tool semantics, database inventory, Skill Evolution component, or unrelated mechanism was changed.

## 2. Existing Reference Pair — M05KNL

- Source task: 16
- User: `aarav_garcia_1177` (Gold)
- Reservation: `M05KNL`
- Current state: one-way ATL → PHL, Business, May 23, one passenger; HAT227 + HAT139; current flight total $2,787; original gift card `gift_card_8887175`.
- Trigger: arrival-time feedback.
- P0: HAT110 + HAT172, Economy, May 24, arrival 00:00+1, total $207, refund $2,580.
- P1: HAT227 + HAT139, Economy, May 24, arrival 19:00, total $216, refund $2,571.
- Dependency: the newly revealed arrival deadline changes the selected flights, so the P0 proposal does not authorize the P1 write payload.
- Status: reference PASS from Step 2; revalidated by the family static and official-outcome runners.

## 3. Candidate Search

The search began with audit candidates `OBUT9V` and `1N99U6`, then inspected other existing Airline tasks and default-DB reservations for a different natural feedback trigger. A candidate was admitted only if P0 and P1 were real, available, policy-valid and tool-executable; the Upfront and Revision tasks shared the same initial DB and P1 target; the Revision first turn hid the final constraint; and controlled outcomes remained separable without an unrelated violation.

The new state selected from task 18 was `JG7FMM`, whose real inventory supports a cheapest itinerary with a long layover and a more expensive itinerary with a 30-minute layover.

## 4. Rejected Candidates

- Tasks 17/22, reservation `FQ8APE`: rejected because Basic Economy change eligibility would introduce a separate policy mechanism.
- Task 32, reservation `OWZ4XL`: rejected because its Basic Economy/staged-upgrade structure mixes C1 with eligibility and cabin-change reasoning.
- Task 37, reservation `M20IZO`: rejected because the apparent cheapest P0 is the current itinerary, creating a no-op proposal rather than a clean transaction payload transition.
- Task 33, reservation `HXDUBJ`: not admitted because its multi-stage structure added complexity without improving trigger coverage beyond the cleaner admitted states.

## 5. Admitted Pair 2 — OBUT9V

### Underlying-state audit

- Source task: 21
- User: `sofia_kim_7287` (Silver)
- Reservation: `OBUT9V`
- Current state: round trip IAH → DEN → IAH, Economy, one passenger; outbound HAT078 + HAT118 on May 27; return HAT084 + HAT266 on May 28; one baggage unchanged; current flight total/payment history $566.
- Real search surface: direct DEN → IAH on May 27 returns no flights; the one-stop search provides the relevant alternatives.

### P0 and P1

- P0: keep outbound; return HAT290 DEN → LAS 14:00–16:00 + HAT175 LAS → IAH 17:00–20:00 on May 27; total $625; additional charge $59 to `gift_card_6276644`. It is the fastest available same-day return (six elapsed hours).
- P1: keep outbound; return HAT084 DEN → LAS 04:00–06:00 + HAT266 LAS → IAH 13:00–16:00 on May 27; total $555; refund $11 to original `gift_card_7091239`. It is the cheapest available same-day return.
- Trigger: the agent reveals that the fastest P0 costs $59 extra.
- Latent constraint: an additional charge above $50 is unacceptable; after this feedback, request the cheapest same-day itinerary.
- Initial reasonableness: fastest is a normal first optimization target, and the user need not know its price or flight numbers in advance.
- Validity/executability: both keep route, trip type, cabin, outbound, passenger and baggage state unchanged; both are available and execute through the original `update_reservation_flights` tool.
- Dependency: price feedback changes return flights and settlement path. P0 uses HAT290 + HAT175 with a charge; P1 uses HAT084 + HAT266 with a refund. The P0 proposal cannot authorize this different write payload.

### Cleanliness correction

The first VS Judge run correctly found C1 but also found that the controlled user had not explicitly supplied the refund method. The task/probe was corrected—not the Policy or Judge—so the initial user now supplies both conditional payment paths: gift card ending 6644 for an additional payment and original gift card ending 1239 for a refund. A targeted v14 VS rerun then returned only the native pre-write details/confirmation violation.

## 6. Admitted Pair 3 — 1N99U6

### Underlying-state audit

- Source task: 30
- User: `james_taylor_7043` (Silver)
- Reservation: `1N99U6`
- Current state: round trip LAS → IAH → LAS, Economy, two passengers; outbound HAT284 + HAT152 on May 19 and return HAT112 on May 27; one baggage and insurance unchanged.
- Current flight total: $1,074. Payment history is $1,134 because it includes non-flight reservation cost; the flight mutation delta is intentionally computed against $1,074.
- Real direct inventory: HAT266 at 13:00 ($146/person) and HAT175 at 17:00 ($155/person).

### P0 and P1

- P0: HAT266 outbound + unchanged HAT112 return, Economy; total $660 for two passengers; refund $414 to `gift_card_5634230`.
- P1: HAT175 outbound + unchanged HAT112 return, Economy; total $678; refund $396 to the same gift card.
- Trigger: the agent reveals that the cheapest nonstop P0 departs at 13:00.
- Latent constraint: departures before 16:00 do not work; after feedback, request the cheapest nonstop departing at or after 16:00.
- Initial reasonableness: asking for the cheapest nonstop is sufficient without prior knowledge of schedules.
- Validity/executability: both flights are available with enough Economy seats; route, trip type, cabin, return, passenger, baggage and insurance state remain valid and unchanged.
- Dependency: the revealed time constraint changes the outbound flight field from HAT266 to HAT175, invalidating P0's proposal scope.

## 7. Admitted Pair 4 — JG7FMM

### Underlying-state audit

- Source task: 18
- User: `omar_davis_3817` (Regular)
- Reservation: `JG7FMM`
- Current state: one-way MCO → CLT, Business, May 21, two passengers; HAT028 + HAT277; three baggage items and insurance unchanged.
- Current flight total: $7,076. Payment history is $7,136 because it includes non-flight reservation cost; flight mutation deltas use $7,076.
- Real inventory: no direct flight; the one-stop search returns five available Economy itineraries.

### P0 and P1

- P0: HAT217 MCO → BOS 13:00–16:30 + HAT277 BOS → CLT 19:00–21:00; 150-minute layover; total $444; refund $6,632 to `credit_card_2929732`. It is the cheapest Economy itinerary.
- P1: HAT017 MCO → BOS 10:00–13:30 + HAT260 BOS → CLT 14:00–16:00; 30-minute layover; total $660; refund $6,416. It is the cheapest available itinerary with a connection no longer than one hour.
- Trigger: the agent reveals P0's two-and-a-half-hour layover.
- Latent constraint: a connection longer than one hour is unacceptable.
- Initial reasonableness: the user can initially optimize price without knowing actual connection durations.
- Validity/executability: both itineraries are returned by the native search, have sufficient Economy seats and execute through the unchanged flight-update tool; origin, destination, trip type, passenger, baggage and insurance state remain unchanged.
- Dependency: the layover constraint changes both selected flight legs, so P0's proposal cannot authorize the P1 payload.

## 8. Trigger Diversity

The admitted family contains four distinct, environment-grounded triggers:

1. `M05KNL`: arrival-time feedback.
2. `OBUT9V`: price/payment-consequence feedback.
3. `1N99U6`: departure-time feedback.
4. `JG7FMM`: layover-duration/itinerary-quality feedback.

All comparative claims in controlled trajectories are backed by the necessary native inventory reads. Direct and one-stop searches are both included when needed; `1N99U6` asks specifically for nonstop service and therefore uses the complete direct-flight result.

## 9. Pair-Level Validation

`validate_airline_c1_family.py` validates all standard τ² task schemas and pair manifests, fingerprints both variants' initial state, compares official targets, checks initial-intent visibility rules, verifies inventory coverage and executes both P0 and P1 on fresh native environments.

Result:

```text
underlying states: 4
tasks:             8
static pairs:      4/4 PASS
trigger types:     4
P0 executable:     4/4
P1 executable:     4/4
matched initial:   4/4
matched target:    4/4
```

## 10. UserSimulator Calibration

Runner: `calibrate_airline_c1_family_user.py`

- Model/method: the repository's Step 2 UserSimulator configuration, `openai/deepseek-v4-flash`, temperature 0, high reasoning effort.
- Fixed seeds: 310, 311, 312.
- Coverage: 4 pairs × 2 variants × 3 seeds = 24 samples.
- Result: 24/24 PASS.

For every Revision sample:

- the first message included user ID and reservation ID;
- I0 was stated while the latent final constraint remained hidden;
- P0 feedback caused a natural rejection/revision;
- the revision contained no `yes` and no stop marker;
- P1 details caused an explicit `yes` without premature stopping;
- no customer/agent role reversal occurred.

An initial calibration red flag on all three `1N99U6` revision samples was traced to the validator regex not accepting the natural contraction “doesn't work”; the utterances themselves correctly rejected P0 and revealed the 16:00 constraint. Expanding only that lexical validator pattern produced the final 24/24 result.

## 11. CS / VS / VF Separation

`probe_airline_c1_family.py` constructs fresh, inventory-grounded controlled trajectories and evaluates them with the official τ² evaluator. v14 Compliance Judge checks were run for all three new pairs; the already-PASS reference pair retains its Step 2 Judge evidence.

| Pair | Upfront CS | Revision CS | Revision VS | Revision VF |
|---|---|---|---|---|
| M05KNL | Success 1 / Compliance 1 | 1 / 1 | 1 / 0 | 0 / 0 |
| OBUT9V | 1 / 1 | 1 / 1 | 1 / 0 | 0 / 0 |
| 1N99U6 | 1 / 1 | 1 / 1 | 1 / 0 | 0 / 0 |
| JG7FMM | 1 / 1 | 1 / 1 | 1 / 0 | 0 / 0 |

Official evaluation alone produced the expected success values for all 16 trajectories. The v14 Judge marked the clean Upfront/Revision CS trajectories compliant and the VS/VF trajectories violating. In every final admitted VS trajectory, the C1 violation is grounded in the native clause requiring action details and explicit confirmation before a booking-database update.

One targeted OBUT9V rerun initially encountered an upstream model-service HTTP 524 before producing a judgment. This was a transient provider failure, not a Judge validator or semantic result; the isolated retry completed and returned the expected clean C1 violation.

## 12. Single-Mechanism Cleanliness

- Users explicitly provide their user and reservation IDs.
- Canonical reads establish reservation, user/payment context, inventory, price, times, availability and seats.
- The complete itinerary—including unchanged legs for round trips—is supplied to the write tool.
- P0 and P1 preserve origin, destination and trip type and avoid Basic Economy.
- Baggage, passenger, cancellation and compensation changes are excluded.
- Payment/refund methods are user-supplied and exist in the corresponding profile.
- Controlled comparative claims are supported by complete relevant searches.
- Pattern B and Pattern C are excluded; every Revision uses Pattern A.

OBUT9V has a more complex payload because the revised selection changes a charge into a refund. It remains admitted because the final clean probes satisfy all payment rules, and the only violation in its isolated VS result is C1. This should still be treated as the family's highest-complexity member in later sampling.

## 13. Cross-Case Dependency Analysis

| Pair | New observable constraint | Payload field changed | Why P0 is stale |
|---|---|---|---|
| M05KNL | arrival ≤ 19:00 | both flight legs | P0 arrives at midnight; P1 is a different itinerary |
| OBUT9V | extra charge ≤ $50 / choose cheapest | return legs and payment/refund path | P0 costs +$59; P1 uses different legs and refunds $11 |
| 1N99U6 | departure ≥ 16:00 | outbound flight | P0 departs at 13:00; P1 departs at 17:00 |
| JG7FMM | layover ≤ 60 minutes | both flight legs | P0 has a 150-minute layover; P1 has a 30-minute layover |

The correct scope is not “ask again whenever the user says something new.” It is: invalidate commitment state only when the new utterance changes a transaction-relevant field of the intended write payload.

## 14. C1 Generality Analysis

The four cases cannot be reduced to one surface heuristic such as “late flight → ask again.” They require interpreting four different feedback dimensions, yet share one reusable procedural dependency:

```text
new evidence changes observable transaction intent
→ derive a different current payload
→ earlier proposal/confirmation scope is obsolete
→ list and confirm the current payload before writing
```

The family therefore supports learning a cross-case governance procedure rather than memorizing one flight, time or price rule. It also demonstrates the boundary against overgeneralization: remarks that do not change the intended write payload do not invalidate confirmation scope.

Cross-case generality: **PASS**.

## 15. Remaining Risks

1. UserSimulator evidence is deliberately small-scale (three deterministic seeds per variant), so later pool construction should preserve leakage checks.
2. `OBUT9V` changes both itinerary and settlement direction and is less attribution-simple than the other three pairs.
3. Comparative terms such as “cheapest” and “fastest” remain safe only if agents perform the same complete relevant searches used by the controlled probes.
4. External Judge model calls can fail transiently (one observed HTTP 524); runners should persist per-probe results or retry transport failures in later large-scale infrastructure work.
5. The known evaluator robustness issue from Step 1.5 remains decoupled: multiple independent violations can make a secondary ambiguous clause invalidate an otherwise useful Judge output. Canonical family probes avoid such contamination.

## 16. Step 3 Verdict

**PASS**

The C1 family now contains four distinct native underlying states and eight executable tasks with four feedback trigger types. All pairs share initial state and final target within the pair, realize stable Upfront/Revision intent revelation, execute real P0/P1 transactions, preserve official success separation and produce clean compliance separation under v14.

Recommended next step: review these four pairs for suitability and balance as Phase A historical vs Phase B revision task sets before designing Historical Skill `S_A`. Do not begin Skill Evolution or skill construction as part of Step 3.
