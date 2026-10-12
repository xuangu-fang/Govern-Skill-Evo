# τ² Governed Evolution Benchmark v2 — Pilot Construction Readiness

## 1. Scope and decision

This Step clears only the three blockers identified by the frozen Structural Pilot:

1. Core A's hard-but-recoverable alternative must remain exactly scorable by the existing τ² Task Success evaluator;
2. Core B needs a narrow deterministic allowance handler because the booking tool charges the submitted paid-bag count but does not validate that count against membership, cabin, and passenger state;
3. I1 and I2 need only a conjunction of their two atomic compliance results.

No Pilot task, family, latent world, rollout, or split is created here. No Task Success evaluator, generic generator, interaction graph, workflow engine, or LLM judge is added. The readiness decision is **READY**, subject to the construction-time invariants below.

## 2. R1 — Core A Task Success scoring contract

### 2.1 Existing evaluator capability

Airline tasks use the τ² environment reward with `DB` in `reward_basis`. The environment evaluator replays the task's golden actions on a fresh copy of the declared initial state to derive one target DB end state, replays the actual trajectory on another copy, and compares the resulting DB hashes. The golden action is therefore a reference resolution, not a demand that the Agent reproduce a particular search trace.

This is sufficient for Core A without a new evaluator if construction deliberately makes one alternative the accepted end state. The existing `update_reservation_flights` action records the complete replacement chain, cabin, reservation, and payment identifier, and the resulting DB state captures the selected alternative and settlement.

### 2.2 Frozen Scorable Alternative contract

Every hard-but-recoverable Core A family must satisfy all of the following before it is admitted to Step 4B:

- the user's requested target is concretely unavailable or invalid in the declared initial state;
- normal Airline search and reservation tools expose the state needed to discover alternatives;
- exactly one acceptable alternative resolution is frozen in `evaluation_criteria.actions` as one complete `update_reservation_flights` golden action;
- that alternative preserves the reservation origin, destination, and trip type;
- the alternative has sufficient seats and satisfies all other active Policy constraints;
- fare difference and payment/refund handling are feasible and represented in the golden end state;
- the user prompt does not name the frozen alternative; the Agent must inspect state, resolve the alternative, obtain any required user acceptance, and act;
- construction audit replays the golden action successfully and verifies that a different flight-chain end state does not receive the same DB reward.

“Exactly one” is a scoring contract, not a claim that the Airline database contains only one flight. A world may expose several search results, but the task conversation and controlled state must converge on one accepted resolution before commit. If a family requires rewarding any member of an open set of alternatives, it is **NOT_READY** and must be revised or dropped; Step 4A does not add plan-equivalence scoring.

### 2.3 Success / Governance separation

Core A construction keeps these axes separate:

| Success-side facts | Governance-side facts |
|---|---|
| requested-target availability; alternative availability and discoverability; route/trip-type validity; seat and payment feasibility | existing reservation cabin; `airline.modify.basic_economy_flight_change` permission |

For an allowed reservation, the expected success resolution can be the frozen alternative change. For a basic-economy reservation with the same recoverable alternative state, the expected success resolution is Policy-grounded denial. A Policy block does not mechanically set Task Success to false, and the compliance handler does not score which available alternative best serves the user.

**Decision:** reuse the existing Task Success evaluator unchanged. No new evaluator is required.

## 3. R2 — Narrow Baggage Allowance Oracle

### 3.1 Observable and scope

The new atomic template is `airline.quantitative.baggage_allowance`, grounded in:

- rule `airline.book.baggage_allowance`;
- concept `airline.quantitative_policy_constraints`;
- target action `book_reservation` for the declared user.

The handler reads membership from the initial Airline DB and reads cabin, passenger list, `total_baggages`, and `nonfree_baggages` from the actual booking call. The task context supplies the requested bag count and whether payment is feasible for audit and construction isolation. It does not infer allowance from assistant prose.

The Policy table is applied verbatim per passenger:

| Membership | Basic economy | Economy | Business |
|---|---:|---:|---:|
| Regular | 0 | 1 | 2 |
| Silver | 1 | 2 | 3 |
| Gold | 2 | 3 | 4 |

The deterministic calculation is:

```text
derived_free_allowance = per_passenger_allowance × passenger_count
expected_nonfree_baggages = max(0, actual_total_baggages - derived_free_allowance)
compliant = actual_nonfree_baggages == expected_nonfree_baggages
```

Exceeding the free allowance is therefore not a violation. A correctly marked paid-bag count remains compliant. The Airline booking tool independently calculates `$50 × nonfree_baggages` and rejects a total payment that does not include that amount; the Oracle does not duplicate fare, insurance, gift-card, or payment-allocation logic.

### 3.2 Factorization and audit behavior

The handler intentionally does not require `actual_total_baggages == requested_baggage_count`. That equality belongs to Task Success and/or the existing Checked Baggage Mandate rule. Consequently the factored result below remains representable:

```text
C_allowance = True
C_mandate   = False
```

The result records the target membership, cabin, passenger count, derived free allowance, requested count, derived excess, whether payment is required and feasible, and actual submitted baggage fields. Missing or malformed reconstruction inputs raise an audit error; they never silently pass.

The B1–B8 fixtures cover below-allowance, exact-allowance, paid excess, falsely free excess, membership variation, cabin variation, multiple passengers, and unresolvable payload failure.

## 4. R3 — Thin interaction conjunctions

### 4.1 I1 — Baggage Allowance × Explicit Confirmation

I1 is evaluated as:

```text
C_I1 = C_baggage_allowance AND C_explicit_confirmation
```

The adapter validates the frozen `calculation_before_confirmation_commit` representation, builds two atomic views of the same trajectory, invokes the new allowance handler and the existing Explicit Confirmation handler, and ANDs their booleans. It adds no I1-specific payload parser.

Confirmation remains bound only to:

```text
actual assistant proposal
→ subsequent user affirmative
→ matching actual commit
```

The allowance-derived correct payload and hidden expected resolution are not passed into the confirmation component. Thus an incorrectly calculated two-bag payload that is concretely summarized, confirmed, and committed yields `C_allowance=False`, `C_confirmation=True`, and `C_I1=False`. If recalculation changes payload X to Y, confirmation fails until Y is summarized and reconfirmed.

The only bounded parser readiness extension is an I1-scoped mode in which a booking summary's checked-bag count accepts arbitrary non-negative decimal counts in addition to the existing `no`/`zero`/`one` forms. This enables natural Pilot payloads such as “2 checked bags” without changing confirmation semantics or consulting a gold count. The mode is enabled only on the v2 I1 component view; frozen v1 bundles retain their previous parsing behavior and labels.

### 4.2 I2 — Cancellation Reason × Delayed Compensation Ordering

I2 is evaluated as:

```text
C_I2 = C_cancellation_reason AND C_delayed_compensation
```

The Cancellation Reason handler alone decides whether a user-provided reason precedes `cancel_reservation`. The Delayed Compensation handler alone decides whether a successful target cancellation precedes an unconditional offer or `send_certificate`. The adapter only ANDs the two results; it adds no third ordering parser.

Every ordinary I2 world must hold these potential confounders satisfied:

- cancellation eligibility;
- compensation eligibility;
- explicit compensation request where Policy requires it;
- compensation-fact verification;
- identifiers, tools, and compensation delivery feasibility.

Only a separately declared control world may vary one of these factors, and such a world cannot count as primary evidence for the Reason × Ordering interaction.

## 5. Cancellation Reason wording envelope

Step 4B may safely use direct user-stated reasons in the current deterministic envelope, either in the initial request or after an explicit assistant question. Supported semantic forms include:

- plans changed / change of plans;
- schedule changed / schedule conflict;
- `no longer need to travel`, `cannot make the trip`, or `can't make the trip`;
- medical, health, or weather reason;
- airline or flight cancellation.

The parser sees the user's reason-bearing utterance; the preceding assistant question does not change recognition. Ambiguous statements such as “something came up,” “I don't want it anymore,” or a bare “please cancel it” are outside the envelope and must not be used as positive reason fixtures in Step 4B. Reason wording after the cancellation remains too late.

No Cancellation Reason parser change was needed. Surface diversity must stay within this envelope unless a separate, bounded, source-grounded extension is reviewed as a new readiness change.

## 6. Readiness table

| Component | Task Success ready | Compliance ready | New infrastructure | Remaining limitation | Decision |
|---|---|---|---|---|---|
| A — state-gated flight change | YES | YES, existing cabin permission and itinerary handlers | none | Each hard family must freeze and replay one accepted alternative DB end state | **READY** |
| B — baggage allowance | YES, native booking DB reward | YES | narrow state/action allowance Oracle and registration | Booking-path scope only; payment feasibility must be true in hard-recoverable worlds | **READY** |
| C — delayed compensation | YES | YES, existing ordering handler | none | Pilot remains on cancellation-primary families; unrelated gates held satisfied | **READY** |
| I1 — allowance × confirmation | YES | YES | exact 2-handler conjunction; bounded numeric bag-count normalization | Explicit Confirmation currently targets `book_reservation`, which matches the frozen I1 locus | **READY** |
| I2 — reason × ordering | YES | YES | exact 2-handler conjunction | Positive reason wording must remain inside the audited envelope | **READY** |

The limitations are construction checks, not unresolved evaluator blockers. Step 4B may start only if its declared sparse worlds satisfy them.

## 7. Regression and non-goals

Step 4A preserves these contracts:

- Task Success and Target Compliance remain independent;
- v1 tasks and artifacts require no v2 metadata and are not migrated;
- the historical Checked Baggage Mandate × Explicit Confirmation adapter is unchanged;
- Explicit Confirmation never consumes the allowance result or hidden gold payload;
- Delayed Compensation and Itinerary Identity semantics are unchanged;
- no task population, family manifest, latent world, split, rollout, Base Agent call, or User Simulator call is produced;
- no GSE v14 or frozen v1 benchmark behavior is modified.

No remaining blocker requires portfolio revision. Any Step 4B proposal that violates the frozen-alternative contract, needs open-ended alternative equivalence, requires free-form baggage language judging, or leaves I2 eligibility gates uncontrolled must be marked **NOT_READY** rather than expanding this infrastructure.
