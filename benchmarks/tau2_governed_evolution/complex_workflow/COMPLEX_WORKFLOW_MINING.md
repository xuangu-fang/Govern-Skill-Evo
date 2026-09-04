# Step CW1 — Original τ² Complex Workflow Mining

Status: **STRUCTURAL MINING COMPLETE**

Scope: original τ² Airline task/workflow analysis only

Decision: **PROCEED TO CW2; no task construction or rollout in CW1**

## 1. Motivation

The Step 5R result left the atomic v2 Pilot semantically clean but structurally
weak for evolution:

```text
H1_BASE = MIXED
H2      = NOT_SUPPORTED
H3      = MIXED
```

CW1 tests a narrower diagnosis: whether the original τ² Airline population
contains natural workflow structure that the v2 Pilot removed while isolating
individual mechanisms. It does not test whether the current Base Agent fails
those workflows, and it does not revise the existing Pilot.

The important distinction is:

```text
long task / many calls
    is not sufficient

goal dependency, state dependency, policy dependency,
entity binding, preservation, conditional branching,
goal accumulation, or reconciliation
    is structural workflow complexity
```

## 2. CW1 question

Two explanations remain possible:

- **Hypothesis A:** Airline is now easy for the Base even when its full
  workflows are retained.
- **Hypothesis B:** Airline still contains useful workflow-level difficulty,
  but v2 removed it through over-atomic construction.

CW1 cannot decide which model-behavior hypothesis is true without new
rollouts. It asks the prerequisite question:

> What reusable, naturally occurring complex-workflow patterns are actually
> present in original τ² Airline tasks?

## 3. Data reviewed

The review covered all 50 tasks in:

- `external/tau2-bench/data/tau2/domains/airline/tasks.json`;
- the Airline source policy in `policy.md`;
- concrete users, reservations, flights, payment methods, membership,
  insurance, passenger, cabin, trip, date, and flight-status state in
  `db.json` for the candidate tasks;
- Airline tool semantics for search, booking, reservation reads, modification,
  cancellation, calculation, and compensation;
- each candidate's user goal, staged simulator instructions, golden actions,
  communication assertions, and natural-language assertions;
- the frozen v2 Pilot declarations and materialized evaluation actions for the
  structural comparison.

No historical model score or trajectory outcome was used. In particular,
Task 5 and Task 7 were inspected because the request names them as structural
case studies, not because of any prior DeepSeek result.

Descriptive inventory—not a complexity definition:

| Population | Tasks | Expected-action distribution | Tasks with ≥3 expected actions | Tasks with ≥2 write mutations |
| --- | ---: | --- | ---: | ---: |
| Original Airline | 50 | 0–19 actions | 19 | 13 |
| Revised v2 Pilot | 28 | 0–2 actions; 20 have exactly 1 | 0 | 0 reservation-mutation chains |

The original counts only flag candidates. Admission below depends on the
semantic relationship among goals, entities, policy checks, and actions.

## 4. Task-level workflow representation

The following is the finite candidate inventory produced by reviewing the
original task definitions. `Goals` counts unresolved user outcomes, not tool
calls. Entity abbreviations are `R` reservation, `P` passenger, `F` flight,
and `Pay` payment method.

| Task | Goals | Entities | Policy decision points | Dependencies / state | Preservation, accumulation, conflict, reconciliation, branches | Workflow summary |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | start booking; investigate delay; handle compensation (3) | several R, claimed/actual P count, delayed F | fact verification; user-request condition; delayed-remedy prerequisite | locate “last” R, verify delay and P count before compensation | mid-dialogue topic switch; claim/DB conflict; original booking is explicitly abandoned; preserve delayed R | Begin booking, retain/close its state correctly, resolve an underspecified prior reservation, reject a false passenger count, and avoid compensation without modification/cancellation. |
| 3 | compute total free bags; resolve membership dispute (2) | user, R, multiple P | membership authority; allowance by member/cabin/passengers | DB membership and R passenger count jointly determine numeric total | Gold claim conflicts with Silver DB; numeric aggregation; possible escalation | Verify authoritative membership and aggregate allowance instead of accepting the user's entitlement claim. |
| 5 | verify delayed flight; obtain maximum remedy without changing trip (2) | user, four R, delayed F, four P, Pay | proactive-offer rule; fact verification; compensation eligibility; delayed-remedy prerequisite | identify HAT045 inside the correct R, verify delay, membership, cabin and P count | Gold claim conflicts with Regular DB; explicit “flight must stay as is” preservation; remedy request conflicts with required primary action | Resolve eligibility and authority while preserving the reservation, rather than treating this as a single compensation lookup. |
| 7 | cancel R1; cancel R2; enumerate other upcoming travel; sum its cost (4) | six R, multiple F/P, one credit card | basic-economy modification; cabin change; two distinct cancellation eligibility paths; reason; confirmation | R1 requires cabin upgrade before cancellation; R2 uses insured sickness; remaining-R query follows mutations | goal added after third agent message; cross-R aggregation; keep all goals live | Execute two different cancellation plans while adding a portfolio query and recomputing remaining upcoming cost. |
| 8 | reproduce prior itinerary; conditionally book one/two P; use certificate only (3) | prior R, target F, two P, certificate | passenger data; seat/cabin consistency; one-certificate rule; baggage/insurance | inspect prior R, find exact later F, compare total to budget, then choose passenger set | conditional branch at $500; payment-source preservation; exact-flight constraint | Reconstruct a previous booking and bind itinerary, passenger branch, budget, and payment policy into one commit. |
| 9 | cancel R1; cancel R2; change R3 if possible (3) | three R, multiple F, one Pay | per-R cancellation eligibility; flown segment; route-preserving modification | each R requires a separate state/policy decision | cross-R state isolation; mixed deny/deny/search-no-change outcomes | Triage three reservations without transferring eligibility or actions between them. |
| 11 | remove one P; if denied downgrade all; report refund (3) | round-trip R, multiple P/F, original Pay | passenger-count preservation; all-segment cabin consistency; refund handling | denial of first request activates cabin fallback and refund calculation | delayed disclosure of R id; conditional goal replacement; preserve passenger count | Recognize an impossible mutation, retain the user's fallback, apply it to the whole itinerary, and reconcile the refund. |
| 12 | attempt cabin upgrade; add bags regardless; possibly try one-P upgrade (3) | multi-P, multi-segment R, flights, Pay | same cabin for all P/F; budget; baggage allowance | price calculation determines denial; baggage goal survives upgrade denial | preservation of independent baggage subgoal; invalid partial-passenger fallback | Reject the partial cabin workaround without dropping the still-valid baggage mutation. |
| 14 | total balances; replace basic-economy R; minimize card charge; report amount (4) | R, three P, round-trip F, gift cards, certificates, card | basic-economy change prohibition; cancellation; booking; payment-count limits; confirmation | balance aggregation → cheapest itinerary search → cancellation/rebook → payment allocation → budget test | multi-goal; payment reconciliation; threshold branch; trip/date/no-bag/no-insurance preservation | Complete a state-dependent replacement transaction whose admissibility depends on both policy and reconciled payment totals. |
| 17 | cabin change; passenger substitution; baggage change (3) | one R, P, multi-leg F, gift card | same-cabin constraint; passenger-count preservation; allowance; confirmation per mutation | later payloads depend on the updated R and authoritative user DOB | maintain three unresolved goals and bind each to the same R | Coordinate three distinct mutations without dropping a subgoal or changing passenger count. |
| 18 | downgrade every business R; preserve F/P; aggregate savings (2+) | five target R among portfolio, many F/P/Pay | cabin rules; refund destination; confirmation | inspect portfolio, select only business R, compute each refund and final sum | cross-R isolation; preservation of flights/passengers; aggregation after mutations | Apply a common rule independently to several reservations and reconcile all refunds into one answer. |
| 19 | locate trip; seek later return; if change blocked cancel using insurance (2) | unknown R, round-trip F, insurance | basic-economy restriction; cancellation eligibility and reason | identify R → search target → policy denial → insured cancellation fallback | conditional fallback; airport/date constraints; no rebooking | Convert a failed modification path into a policy-valid cancellation while preserving the user's no-new-booking intent. |
| 20 | choose cheapest time-valid itinerary; book with bags; split payment (3) | direct/one-stop F, P, two certificates, card | flight availability; one-certificate maximum; allowance; insurance; payment total | filter time/cabin, compare direct and connecting options, price bags, then allocate payment | preference fallback; arithmetic reconciliation; payment binding | Search and commit a complete booking whose chosen itinerary and payment payload depend on several coupled constraints. |
| 21 | select fastest same-day return; add bag; use smallest gift card (3) | round-trip R, candidate F, Pay | itinerary/trip preservation; cabin; baggage; update payment | compute elapsed time including layover and temporal order; update F then baggage | ranking/reconciliation; keep economy and outbound leg fixed | Resolve a temporal graph problem and carry its result into two coordinated reservation mutations. |
| 23 | total balances; replace R; create three bookings; minimize card total (5+) | old R, three new R/P, multi-leg F, certificates/gifts/card | cancellation; booking; max one certificate per R; payment safety; confirmation | discover one-certificate limit → user introduces three-booking plan → allocate distinct methods → sum card exposure | mid-dialogue plan change; cross-booking binding; aggregation; repeated commits | Re-plan the transaction topology itself to satisfy payment policy while preserving itinerary equivalence. |
| 24 | remove P; conditionally cancel; independently book West Coast trip (3) | old R/P plus new R/F/Pay | passenger-count preservation; cancellation eligibility; booking; free allowance; payment limits | denial of remove activates cancellation attempt; failure must not block separate search/book goal | multiple independent goals; preserve other passengers; fallback chain | Close a denied mutation branch correctly and continue a separate constrained booking workflow. |
| 29 | change endpoints; if forbidden cancel/rebook; add bag (3) | old and new R, round-trip F, Pay | itinerary identity; cancellation; booking; baggage; insurance misconception | route-change denial activates cancellation/rebooking; chosen flights feed booking payload | preservation of dates/time/cabin and one bag across transaction replacement | Transform a forbidden modification into a valid two-transaction recovery without losing constraints. |
| 32 | cabin upgrade; confirm; then separate flight change; confirm (2) | one R, multi-leg F, Pay | basic-economy flight restriction; cabin change; explicit confirmation; itinerary preservation | first committed state makes second operation permissible | ordered two-stage mutation; no new ticket; budget | Perform two individually confirmed state transitions rather than collapsing them into one opaque change. |
| 33 | change outbound/return; later request cabin and bags; resolve budget/partial cabin restriction (4) | one round-trip R, candidate F, Pay, bags | modification; same cabin across legs; insurance misconception; allowance | finish flight change before later goals appear; price drives cabin fallback but baggage remains | mid-dialogue accumulation; subgoal preservation; conditional fallback | Preserve completed and pending state while a later bundle partly fails policy/budget constraints. |
| 34 | price a four-part package; mutate nothing if over budget (4) | one round-trip R, F, Pay, bags | modification, cabin consistency, insurance claim, baggage, confirmation | complete-package feasibility must be known before any write | atomicity/preservation: no partial changes; conditional all-or-none branch | Treat feasibility analysis as a transaction guard and protect the original R if the full bundle is not admissible. |
| 35 | attempt cancellation under false status claim; then book second-cheapest trip (2) | old R, new one-stop F, P, Pay | cancellation eligibility; membership authority; booking/payment | close repeated denied cancellation without transfer, then rank and book a separate itinerary | goal persistence across denial; authority conflict; “second cheapest” aggregation | Resist pressure on one goal while still completing the independent downstream booking goal. |
| 39 | cancel every eligible upcoming R, preserve all others (portfolio goal) | seven R with different cabin/insurance/time states | cancellation eligibility independently per R | inspect every R, partition eligible/ineligible, mutate only eligible set | cross-entity isolation and preservation of four R | Apply the same policy predicate per entity rather than using one global user-level decision. |
| 42 | find schedule conflicts; cancel only impossible self-trips; protect other-P bookings (portfolio goal) | seven R, many P/F/cities/times | cancellation eligibility plus ownership/passenger relevance | reconstruct temporal/location continuity across R and identify two conflicting trips | cross-entity reasoning; protected reservations for other passengers | Infer which bookings conflict from time, location and passenger identity, then mutate only those entities. |
| 44 | partition R by duration; deny ineligible cancellations; price and upgrade short trips (3+) | five R, many legs/layovers, Pay | cancellation reason/eligibility; cabin update; payment; confirmation | compute durations including layovers → partition actions → total upgrade price → confirm → mutate selected R | cross-R aggregation; “do not upgrade then cancel” preservation; mixed action classes | Run a portfolio query whose classification creates different governed workflows for each reservation. |

This inventory deliberately excludes tasks whose apparent difficulty is only
persistent wording or a single isolated policy denial. It also shows that the
same task can evidence more than one archetype; the archetypes below are
workflow lenses, not a new formal ontology.

## 5. Reusable complex-workflow archetypes

### Archetype 1 — Per-entity portfolio triage and reconciliation

**Core structure**

```text
enumerate reservations
→ resolve state and policy independently per reservation
→ partition into action / deny / preserve sets
→ execute selected actions
→ reconcile portfolio-level result
```

**Complexity sources:** multi-goal, multi-reservation, multi-state,
multi-policy, entity binding, preservation, aggregation.

**Original exemplars:** Tasks 7, 18, 39, 42, and 44. Task 39 applies
cancellation eligibility to seven reservations; Task 42 combines passenger,
location, and time consistency; Task 44 assigns different action classes after
duration and policy checks.

**Potential recurrent failures:** cross-reservation state leakage, acting on a
protected entity, skipping an entity, applying one reservation's eligibility
globally, and incorrect aggregate cost/refund.

**Potential Skill form:** “Maintain a per-reservation ledger of goals, state,
eligibility, intended action, and protected fields; reconcile only after every
entity is resolved.”

### Archetype 2 — Constraint-coupled booking and payment reconciliation

**Core structure**

```text
discover candidate itinerary
→ filter/rank by time, route, cabin and seats
→ bind passengers, bags and insurance
→ enforce payment-method cardinality/balance rules
→ reconcile exact total
→ confirm and commit one complete payload
```

**Complexity sources:** multi-state, multi-policy, cross-entity binding,
conditional choice, arithmetic/aggregation, complete-payload confirmation.

**Original exemplars:** Tasks 8, 14, 20, 23, and 25. Task 20 couples
direct/one-stop ranking with bag fees and a certificate/card split. Task 14
adds balance totals and replacement of an unmodifiable reservation. Task 23
changes from one group reservation to three separate bookings to respect the
one-certificate-per-reservation rule.

**Potential recurrent failures:** wrong itinerary ranking, passenger/payment
misbinding, certificate overuse, incorrect remainder, stale confirmation after
price changes, and committing only part of the intended booking.

**Potential Skill form:** “Construct and verify one final transaction ledger—
itinerary, passengers, ancillaries and exact payment split—before requesting
confirmation.”

### Archetype 3 — Policy-triggered fallback and transactional branching

**Core structure**

```text
attempt preferred goal
→ inspect state and policy
→ if blocked, activate only the user-authorized fallback
→ re-evaluate fallback policy/feasibility
→ either commit fallback or preserve state
```

**Complexity sources:** conditional branching, dependency, multi-policy,
goal persistence, preservation, task-specific authority.

**Original exemplars:** Tasks 11, 19, 24, 29, 34, 35, and 45. Task 11 turns
an impermissible passenger removal into an all-passenger cabin downgrade. Task
29 turns a forbidden endpoint change into cancellation plus rebooking. Task 34
requires no mutation if the complete requested package exceeds budget.

**Potential recurrent failures:** taking an unoffered workaround, abandoning a
valid secondary goal after a denial, evaluating fallback with the first path's
state, partial writes before feasibility is known, and failure to preserve the
original reservation.

**Potential Skill form:** “Represent fallbacks as guarded branches; close the
current branch before opening the next, and perform no write until that branch's
full preconditions are satisfied.”

### Archetype 4 — Multi-attribute mutation with protected invariants

**Core structure**

```text
load one reservation
→ maintain several requested mutations
→ evaluate each against shared invariants
→ sequence dependent updates
→ preserve rejected and untouched dimensions
```

**Complexity sources:** multi-goal, shared state, multi-policy, ordered writes,
preservation, partial feasibility.

**Original exemplars:** Tasks 12, 17, 21, 22, 30, 32, and 33. Task 17
coordinates cabin, passenger, and baggage changes. Task 21 couples temporal
itinerary selection with payment and baggage. Task 33 adds cabin and baggage
goals after flight modification, while a rejected partial-cabin fallback must
not erase the baggage goal.

**Potential recurrent failures:** lost subgoal, stale reservation state between
writes, illegal partial cabin/passenger change, removing protected baggage,
and incorrectly rolling back or overwriting a successful prior update.

**Potential Skill form:** “Track requested and protected fields separately;
after every write, refresh the reservation and revalidate remaining mutations.”

### Archetype 5 — Mid-dialogue goal accumulation and plan continuity

**Core structure**

```text
begin Goal A
→ user introduces Goal B or changes the plan
→ explicitly retain, defer or close A
→ integrate B with already learned state
→ finish every non-withdrawn goal
```

**Complexity sources:** multi-goal, dialogue state, goal accumulation/change,
dependency, premature-termination risk.

**Original exemplars:** Tasks 2, 7, 23, and 33. Task 2 abruptly switches from
booking to a delayed-flight complaint and later withdraws the booking. Task 7
adds an upcoming-reservation cost query while two cancellations remain active.
Task 33 adds cabin and baggage goals only after the flight changes.

**Potential recurrent failures:** new goal replaces old goals, withdrawn goal
is accidentally resumed, premature stop after the newest goal, repeated reads
because earlier state is forgotten, and missing re-confirmation after a plan
change.

**Potential Skill form:** “Keep an explicit unresolved-goal checklist; on every
goal change, mark each prior goal active, deferred, completed, blocked, or
withdrawn.”

### Archetype 6 — Authority conflict under a protected-state remedy request

**Core structure**

```text
receive user claim and requested remedy
→ resolve authoritative user/reservation/flight state
→ verify all policy prerequisites
→ preserve explicitly protected reservation state
→ communicate or deny the remedy without inventing eligibility
```

**Complexity sources:** state conflict, authority resolution, multi-policy,
preservation, compensation/refund prerequisites.

**Original exemplars:** Tasks 3, 5, 27, 38, 48, and 49. Tasks 3 and 5
contain membership claims contradicted by DB state. Tasks 2/38 contain an
incorrect passenger count. Tasks 48/49 contradict booking-time or insurance
state. Task 5 and Task 27 require the reservation to remain unchanged while
the user requests compensation.

**Potential recurrent failures:** trusting unsupported claims, checking the
wrong reservation/flight instance, deriving entitlement from membership alone,
premature compensation, or modifying/cancelling protected state to unlock a
remedy.

**Potential Skill form:** “Treat user claims as hypotheses; verify the exact
entity and all remedy prerequisites from tools, and never perform a primary
action the user explicitly prohibited.”

## 6. Task 5 case study — authority, remedy prerequisites, and preservation

Task 5 is not merely a delayed-compensation policy task.

Concrete state establishes:

- user `mei_brown_7075` claims Gold but the DB says `regular`;
- HAT045 on 2024-05-15 is delayed and belongs to reservation `3JA7XV`;
- that reservation is business, round-trip, and has four passengers;
- the user asks for maximum compensation and prefers the original payment
  method, but explicitly forbids cancellation or modification.

The governed workflow is:

```text
identify user and relevant reservation/flight instance
→ resolve Gold-vs-Regular authority conflict
→ verify delay, cabin, passenger count and remedy eligibility
→ distinguish certificate remedy from original-payment refund
→ enforce delayed-remedy prerequisite
→ preserve the reservation because the user forbids the primary action
→ deny compensation without mutating the trip
```

Several decision points interact. Regular status alone is not a sufficient
denial reason because the reservation is business; verified delay and general
eligibility still do not authorize the delayed certificate when no change or
cancellation occurs. The preservation mandate makes “perform the primary
action, then compensate” invalid for this user goal.

Potential failures are workflow-management failures: selecting a reservation
by flight number incorrectly, trusting Gold status, using one satisfied
eligibility predicate as if all prerequisites were satisfied, offering a
certificate too early, or changing protected state to make compensation
available.

## 7. Task 7 case study — heterogeneous reservation plans plus accumulated goal

Task 7 maintains four outcomes across six reservations in the user's profile:

1. cancel `XEHM4B`;
2. cancel `59XX6W`;
3. after the third agent message, find other upcoming reservations;
4. calculate their total cost, expected as `$1,628`.

`XEHM4B` is a basic-economy, uninsured round trip. Flight modification is
blocked, but cabin change is allowed; the user's authorized path is therefore
upgrade the whole reservation to business with card `credit_card_2408938`,
then cancel it. `59XX6W` is economy with insurance, and the stated sickness is
a covered cancellation reason, so it has a different cancellation path.

The dependency structure is:

```text
R1: inspect → basic economy → whole-R cabin upgrade → updated state → cancel
R2: inspect → insurance + sickness reason → cancel

after dialogue trigger:
enumerate remaining upcoming R
→ exclude cancelled/past/irrelevant state correctly
→ aggregate total cost = 1,628

all four goals remain live until explicitly resolved
```

This is materially more complex than v2 A/B/C. It combines two heterogeneous
state machines, multiple policy decisions, ordered writes, per-reservation
binding, post-mutation aggregation, and mid-dialogue goal accumulation.
A failure can occur even when every individual rule is known: abandoning the
second cancellation, applying insurance from one reservation to the other,
cancelling basic economy before upgrading it, forgetting the newly added
query, or summing the pre-cancellation portfolio.

## 8. Original τ² complex workflow vs v2 Structural Pilot

| Dimension | Original complex task | v2 Pilot |
| --- | --- | --- |
| Goals per task | Frequently 2–5 unresolved outcomes; some portfolio-level goals expand per entity | Normally one user goal and one target mechanism; interactions remain one shared transaction |
| Entities | Multiple reservations, passengers, flight legs and payment sources are often jointly relevant | Family worlds intentionally freeze one reservation or one booking context |
| Policy decisions | Several independent checks can govern different branches/entities | One atomic target, or exactly two conjunctive atomic handlers |
| State dependencies | Earlier reads/writes determine later eligibility, payload, totals, or entity set | State factor is deliberately exposed and unrelated blockers are fixed |
| Workflow depth | Read/partition/branch/mutate/re-read/reconcile; original gold paths reach 19 actions | Gold paths have 0–2 actions; 20/28 tasks have one |
| Preservation | Protected reservations, passengers, flights, transaction atomicity, or “do not change/cancel” clauses | Mostly opposite-boundary denial or fixed factor preservation |
| Mid-dialogue changes | Explicit in Tasks 2, 7, 23, 33 and conditional simulator branches elsewhere | No accumulated independent goal; scripted interaction only creates the selected two-way relation |
| Aggregation/reconciliation | Portfolio totals, refunds, balances, rankings, durations, payment remainder | Narrow allowance/price or fixed alternative calculation |
| Main difficulty type | Maintaining a coherent plan over dependent goals, entities, policies and protected state | Isolated rule/state reasoning and short transaction ordering |

**Finding: `SUPPORTED` as a structural diagnosis.** Review of the actual task
definitions shows that clean attribution in v2 systematically removed most
multi-goal, cross-entity, branching, preservation, and reconciliation
structure. The evidence is not merely longer prompts or more calls: Tasks 5,
7, 14, 23, 33, 42, and 44 each contain dependencies whose correct downstream
behavior changes with upstream state or policy resolution.

This does **not** establish that Hypothesis B is behaviorally true. A future
Base calibration may show that DeepSeek handles these workflows reliably, in
which case Hypothesis A remains viable. CW1 supports testing B, not assuming it.

## 9. Proposed Complex Workflow Pilot

Recommended size: **15 tasks**, using six archetypes and no formal split.

| Archetype | Independent future families | Intended evidence |
| --- | ---: | --- |
| Per-entity portfolio triage | 3 | heterogeneous per-R decisions plus preservation and reconciliation |
| Booking/payment reconciliation | 3 | complete payload construction across itinerary, P, baggage and Pay |
| Policy-triggered fallback | 2 | guarded branch transitions and no premature/partial writes |
| Multi-attribute mutation | 2 | retained subgoals and invariants across sequential writes |
| Mid-dialogue goal accumulation | 3 | goal continuity across additions, withdrawals and plan change |
| Authority conflict + protected remedy | 2 | tool-grounded authority and preservation across remedy decisions |

The count is a design target for CW2, not a frozen population. Every family
must use a different concrete latent realization—not a renamed user or
paraphrased prompt—and should naturally contain at least three related
complexity dimensions. Candidate families should differ in reservations,
state constellation, branch outcome, entity topology, and concrete arithmetic
or temporal realization while retaining the same archetypal workflow.

CW2 should reuse:

- original Airline Policy;
- original tools and environment;
- original User Simulator architecture;
- native Task Success / golden-action mechanism;
- existing deterministic Compliance handlers where a governed target is
  already supported.

Only task workflow should be newly declared. No easy/hard pairing, Cartesian
world enumeration, generic workflow generator, or requirement for symmetric
archetype counts is proposed. A matched control is justified only when it
isolates a specific attribution question without dismantling the workflow.

## 10. Future Base Calibration protocol

After a separate CW2 construction and deterministic golden-path audit:

```text
12–18 tasks × K=3 Base rollouts
```

Reuse the current GSE v14 settings unchanged: DeepSeek Base, temperature 0.2,
the same reasoning/User Simulator configuration, Parent Skill, retry policy,
and seed protocol. Keep runtime failures separate from behavior failures.

Primary analysis should be task/family/trajectory based:

1. Does a bad behavior recur within a workflow family?
2. Does an equivalent behavior recur across independent tasks/families?
3. Are there multiple non-redundant failure mechanisms?
4. Do the workflows naturally produce distinct CS/CF/VS/VF states?
5. Can each recurrent behavior be expressed as a short, source-grounded Skill?
6. Can Skill, execution, environment/state, and evaluator uncertainty be
   distinguished from saved evidence?

Aggregate Success or Compliance is descriptive, not an admission criterion.
No task may be retained, deleted, or rewritten because its observed failure
rate is attractive.

Initial clustering seeds for post-rollout analysis are:

- subgoal abandonment;
- cross-entity state leakage;
- prerequisite omission;
- premature downstream action;
- preservation violation;
- authority-resolution error;
- payment/passenger binding error;
- premature escalation or termination;
- incorrect aggregation or ranking.

These are review prompts, not a formal taxonomy or labels baked into future
tasks. Actual clusters must come from trajectory evidence, and uncertain cases
must remain ambiguous.

## 11. No-outcome-selection audit

- All 50 original task definitions were reviewed before archetype selection.
- No historical DeepSeek Success, Compliance, CS/CF/VS/VF, Gate, or Candidate
  result was loaded or ranked.
- Task 5 and Task 7 are case studies because their workflows were explicitly
  named for review; they are not selected future tasks in CW1.
- Archetype admission is based on semantic dependency among goals, state,
  policies, entities, branches, preservation, and reconciliation.
- High action count was used only to find candidates and never as sufficient
  complexity evidence.
- Future family selection is constrained to workflow structure and independent
  latent realization, not model outcome.
- CW1 made no model, Agent, User Simulator, rollout, Judge, Diagnosis, Editor,
  Gate, or Reference-Skill call.
- CW1 did not alter the v2 Pilot, Policy, tools, environment, simulator,
  evaluator, Oracle, or GSE v14.

## 12. Final judgment

```text
WORKFLOW_COMPLEXITY_HYPOTHESIS = SUPPORTED

Recommended archetypes:
1. Per-entity portfolio triage and reconciliation
2. Constraint-coupled booking and payment reconciliation
3. Policy-triggered fallback and transactional branching
4. Multi-attribute mutation with protected invariants
5. Mid-dialogue goal accumulation and plan continuity
6. Authority conflict under a protected-state remedy request

Recommended Complex Workflow Pilot size = 15 tasks

CW2_DECISION = PROCEED
```

“Supported” means the original Airline source contains enough genuinely
distinct natural workflow structure to justify a bounded Complex Workflow
Pilot. It does not claim those tasks will fail, that they should be copied
verbatim, or that Hypothesis B has already beaten Hypothesis A. That behavioral
question belongs to a future calibration after CW2, not to CW1.
