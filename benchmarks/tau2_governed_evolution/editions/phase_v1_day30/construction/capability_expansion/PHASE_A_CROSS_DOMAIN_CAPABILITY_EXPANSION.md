# Step 4T — Cross-Domain Capability Mechanism Diversification

## 1. Scope

Step 4T tested whether the frozen strong Base Agent exposes recurrent Phase-A
capability failures outside the already-supported Airline monetary-baseline
mechanism. All tasks were strictly Upfront-Stable and used native τ² state,
Policy, Tools, official evaluation, and the v14-compatible campaign runtime.

No Historical Skill, Reference Skill, Phase-B task, intent revision, Skill
Evolution component, Policy/Tool change, evaluator change, or Judge change was
introduced.

## 2. Runtime

- Agent: `openai/deepseek-v4-flash`
- Agent temperature: `0.2`
- Reasoning: `high`
- UserSimulator: `openai/deepseek-v4-flash`
- Official NL_ASSERTION evaluator: `openai/deepseek-v4-pro`, temperature `0`
- Compliance Judge: the frozen Judge configured by the v14 campaign,
  `openai/deepseek-v4-pro`, temperature `0`
- Skill: Empty (`S0`)
- Policies and Tools: complete native policy/tool contracts for each domain
- Empty-rollout seeds: `820`, `821`, `822`

## 3. Existing Admitted Family

### A — Airline Transaction Baseline Binding

Status: **SUPPORTED** by the prior Step 4R evidence on independent states
`FQ8APE` and `HXDUBJ`.

Observed chain:

```text
wrong mutable transaction baseline
→ wrong derived consequence
→ wrong branch
→ wrong downstream transaction
→ task failure
```

Step 4T did not add further monetary-baseline tasks.

## 4. Candidate Search and Admission

The first wave admitted six tasks selected by native-state structure before any
Empty-Skill outcome was observed:

| Task | Domain | Family | State | Core dependency |
| --- | --- | --- | --- | --- |
| `retail_pa_r2a_w8557584_item_delta_scope` | Retail | R2 | `#W8557584` | item-local difference card must not replace whole-order payment |
| `retail_pa_r2b_w9318778_order_address_scope` | Retail | R2 | `#W9318778` | order address changes while profile default remains fixed |
| `airline_pa_a1a_dkgiih_business_seat_bottleneck` | Airline | A1 | `DKGIIH` | three-passenger capacity must hold on every outbound segment |
| `airline_pa_a1b_1n99u6_economy_seat_bottleneck` | Airline | A1 | `1N99U6` | two-passenger capacity filters every direct/one-stop segment |
| `airline_pa_a2a_6zqnos_fixed_8accrd_buffer` | Airline | A2 | `6ZQNOS` + `8ACCRD` | fixed reservation derives a six-hour arrival cutoff |
| `airline_pa_a2b_9niyyj_fixed_eoj7hm_buffer` | Airline | A2 | `9NIYYJ` + `EOJ7HM` | cross-date fixed reservation derives a twelve-hour cutoff |

The first wave produced a bounded negative result. Because R3 was
under-instantiated before rollout and mechanism diversity remained narrow, the
single permitted second wave admitted only R4, using two new independent native
states:

| Task | Domain | Family | State | Core dependency |
| --- | --- | --- | --- | --- |
| `retail_pa_r4a_w5918442_one_shot_cameras` | Retail | R4 | `#W5918442` | both Action Cameras must be compiled into one complete item write |
| `retail_pa_r4b_w9132840_one_shot_helmets` | Retail | R4 | `#W9132840` | both Cycling Helmets must be compiled into one complete item write |

The second-wave tasks use duplicate units of one product and a common target
variant. This avoids the native Retail implementation defect that reuses the
last resolved variant while applying a multi-product item-modification payload.

## 5. Rejected Candidates

### R3-A — Address + Payment + Items Ordering

Rejected: **tool and evaluator non-separability**.

Retail Policy says item modification closes later order modification, but the
native address/payment tools accept any status containing `pending`, including
`pending (item modified)`. The official action evaluator checks required action
presence rather than ordering. A wrong order can therefore retain official
success, so this state cannot cleanly measure premature option closing.

### R3-B — Global Feasibility Before Option-Closing Mutation

Rejected: **mechanism degeneration**.

When a requested target variant is unavailable,
`modify_pending_order_items` validates all targets and fails before mutation.
The order remains pending and the cancellation fallback remains executable.
The intended irreversible partial-state failure chain is therefore absent.

R3 verdict: **NOT_SUPPORTED / not cleanly realizable under current native Tool
and evaluator semantics**.

## 6. Real-State Oracles

### R2-A — `#W8557584`

- User: `omar_kim_3528` (Omar Kim, ZIP 32214)
- Request: change only two Tea Kettles to the glass, 2-liter, electric variant
- Oracle write: one `modify_pending_order_items` call using
  `credit_card_3577130` only for the item difference
- Protected: whole-order payment `gift_card_3749819`, shipping address, and
  unrelated items
- Consequence: `$5.27` refund

### R2-B — `#W9318778`

- User: `lucas_martin_4549` (Lucas Martin, ZIP 20517)
- Request: change only this order's shipping address to the Boston address
- Oracle write: `modify_pending_order_address`
- Protected: user profile default address and all other orders

### A1-A — `DKGIIH`

- Passenger count: 3
- Candidate set: all direct and one-stop EWR→LAS Business itineraries on May 16
- Bottleneck: every selected outbound segment needs at least 3 Business seats
- Oracle winner: `HAT056 + HAT131`; both fastest feasible candidates take 15
  elapsed hours and this pair wins the lower-fare tie-break
- Preserved return: `HAT115 + HAT192`

### A1-B — `1N99U6`

- Passenger count: 2
- Candidate set: all direct and one-stop LAS→IAH Economy itineraries on May 19
- Bottleneck: every selected outbound segment needs at least 2 Economy seats;
  enumerated one-stop candidates using `HAT152` fail this requirement
- Oracle winner: `HAT266`, tied on duration with `HAT175` but arriving earlier
- Preserved return: `HAT112`

### A2-A — `6ZQNOS` constrained by `8ACCRD`

- Fixed reservation `8ACCRD` departs DTW at 16:00 on May 20
- Derived arrival cutoff: 10:00 on May 20
- Oracle winner for `6ZQNOS`: Economy `HAT106`, arriving at 08:00
- Only `6ZQNOS` is mutated; `8ACCRD` is protected

### A2-B — `9NIYYJ` constrained by `EOJ7HM`

- Fixed reservation `EOJ7HM` departs EWR at 00:00 on May 20
- Derived cross-date arrival cutoff: 12:00 on May 19
- Oracle winner for `9NIYYJ`: Business `HAT300`, arriving at 09:00
- Only `9NIYYJ` is mutated; `EOJ7HM` is protected

### R4-A — `#W5918442`

- User: `sofia_rossi_8776` (Sofia Rossi, ZIP 78784)
- Oracle: both Action Cameras are changed together to available target
  `6700049080` in one `modify_pending_order_items` call
- Consequence: `$45.39` refund to `credit_card_5051208`
- Protected: Perfume, Skateboard, address, and unrelated order state

### R4-B — `#W9132840`

- User: `lei_ahmed_1705` (Lei Ahmed, ZIP 19128)
- Oracle: both Cycling Helmets are changed together to available target
  `1596993217` in one `modify_pending_order_items` call
- Consequence: `$44.74` refund to `credit_card_3593714`
- Protected: Skateboard, address, and unrelated order state

## 7. Upfront-Stability and Oracle Gates

UserSimulator calibration passed:

- First wave: `6 tasks × 3 seeds = 18/18`
- Second wave: `2 tasks × 3 seeds = 6/6`
- Every first turn exposed all transaction-relevant rules and identity data
- No late goal, constraint, fallback, priority, or scope change occurred
- No oracle flight/item ID leaked in the initial utterance
- Users explicitly confirmed only after the complete proposal

Controlled oracle validation passed for all eight tasks:

- Native Tool execution: success
- Official DB reward: `1`
- Official NL_ASSERTION reward: `1`
- Frozen v14-configured Judge: compliant

## 8. Empty-Skill Results

| Family | Tasks | Rollouts | CS | CF | VS | VF | Success | Compliance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R2 Minimal Mutation Scope | 2 | 6 | 6 | 0 | 0 | 0 | 100% | 100% |
| A1 Bottleneck Feasibility | 2 | 6 | 6 | 0 | 0 | 0 | 100% | 100% |
| A2 Cross-Reservation Constraint | 2 | 6 | 6 | 0 | 0 | 0 | 100% | 100% |
| R4 One-Shot Compilation | 2 | 6 | 6 | 0 | 0 | 0 | 100% | 100% |
| **Overall** | **8** | **24** | **24** | **0** | **0** | **0** | **100%** | **100%** |

Domain totals:

- Airline: `12/12` Success, `12/12` compliant
- Retail: `12/12` Success, `12/12` compliant

## 9. Behavior Audit

All 24 complete trajectories were checked beyond their outcome labels. Every
trajectory satisfied:

1. the write payload exactly matched the frozen oracle;
2. no unrequested write occurred;
3. explicit confirmation preceded the first write;
4. the family-specific prerequisite was resolved before commit.

Family-specific observations:

- R2 preserved the requested local scope in all six runs; no profile/default,
  whole-order-payment, unrelated-item, or other-order mutation occurred.
- A1 searched both direct and one-stop inventory, applied passenger count to
  each candidate segment, selected the oracle itinerary, and preserved the
  return payload in all six runs.
- A2 read both reservations, derived the correct temporal cutoff, mutated only
  the dependent reservation, and preserved the fixed reservation in all six
  runs.
- R4 identified both source units, resolved the target variant, proposed the
  complete pair, and used one complete item-modification write in all six runs.

There were no non-CS trajectories and no suspicious CS trajectories under the
automated write/confirmation/prerequisite audit. Manual spot-checking of each
task family agreed with those checks.

## 10. Capability Family Decisions

### Retail R2 — Minimal Mutation Scope

**NOT_SUPPORTED as Historical headroom.** The mechanism is cleanly executable,
but the Base preserved local versus persistent scope in `6/6` runs across two
independent states. There is no material failure, hence no recurrent cluster.

### Retail R3 — Irreversible / Option-Preserving Planning

**NOT_SUPPORTED under current native semantics.** Both attempted designs were
rejected before Empty rollout because the intended failure could not be made
officially separable without changing Tool/evaluator semantics.

### Retail R4 — One-Shot Transaction Compilation

**NOT_SUPPORTED as Historical headroom.** The bounded second wave was `6/6` CS.
The Base consistently compiled both requested units into the single allowed
write.

### Airline A1 — Conjunctive / Bottleneck Feasibility

**NOT_SUPPORTED as Historical headroom.** The Base correctly performed every-leg
capacity filtering and final selection in `6/6` runs across two independent
states.

### Airline A2 — Cross-Reservation Derived Constraint Propagation

**NOT_SUPPORTED as Historical headroom.** The Base correctly derived and applied
the cross-reservation temporal constraint in `6/6` runs across two independent
state pairs.

## 11. Positive Capabilities Demonstrated

The bounded negative result provides positive evidence that the current Base
already performs the following procedures reliably on this pool:

- distinguishes order-local mutation from profile/global mutation;
- preserves unrelated persistent state;
- evaluates conjunctive per-segment feasibility for multiple passengers;
- derives temporal constraints from a second reservation, including a
  cross-date cutoff;
- binds selected and protected flight state into a complete reservation payload;
- compiles multiple requested same-product item changes into one one-shot write;
- presents current details, obtains explicit confirmation, and avoids extra
  writes.

## 12. Admitted Capability Clusters

No new cluster passed the admission gate. In particular, none of R2, A1, A2, or
R4 exhibited a failure that was simultaneously material, recurrent across two
independent states, feasible, procedural, generalizable, and non-Policy-
paraphrase.

## 13. Phase-A Capability Mechanism Map

### Airline

- A. Transaction Baseline Binding: **SUPPORTED** (prior Step 4R)
- A1. Bottleneck Feasibility: **NOT_SUPPORTED**
- A2. Cross-Reservation Constraint Propagation: **NOT_SUPPORTED**

### Retail

- R2. Minimal Mutation Scope: **NOT_SUPPORTED**
- R3. Irreversible Planning: **NOT_SUPPORTED / not cleanly realizable**
- R4. One-Shot Compilation: **NOT_SUPPORTED**

## 14. Historical Skill Mechanism Diversity

**NARROW**.

The only admitted Phase-A capability weakness remains Airline Transaction
Baseline Binding. Step 4T produced clean negative evidence for three distinct
new mechanisms plus a bounded Retail second wave. The evidence therefore does
not justify broadening a future Historical Skill into general transaction-state
integrity guidance.

## 15. Verdict and Stop Rule

**Step 4T verdict: FAIL for mechanism diversification.**

This is not a task-construction or runtime failure: eight clean tasks, 24 stable
user calibrations, eight oracle CS validations, and 24 Empty rollouts were
successfully completed. It is a negative experimental result: no new recurrent
procedural failure mechanism appeared.

The bounded stop rule now applies. Do not continue by adding more items,
reservations, constraints, or prompt length until the Base eventually fails.

## 16. Recommended Next Step

Human review should decide among the following before any `S_A` construction:

1. accept that current Phase-A evidence supports only a narrow Airline Baseline
   Binding capability and design a correspondingly narrow hypothesis;
2. change the domain/distribution or lifecycle hypothesis rather than further
   escalating Phase-A task complexity;
3. abandon the requirement that a broad Historical Skill must outperform Empty
   under this strong Base and full native Policy.

No Phase-B construction or Skill Evolution should begin automatically from this
result.
