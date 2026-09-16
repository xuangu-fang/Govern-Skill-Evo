# Benchmark v3 Environment Extension Point Audit

## 1. Scope

This audit answers where a v3-only latent operational mechanism can be added
without changing native τ² or Benchmark v2. It inspects Airline and Retail data
models, tool transitions, runner construction, recoverability, and prior v3
failure evidence.

No environment semantics or benchmark task was created. No model, User
Simulator, Judge, Learner, Diagnosis, or Editor was called.

## 2. Audit question

The target is not merely a difficult workflow. A viable extension point must
support all of the following:

```text
visible state x
+ stable latent operational mapping g
→ different correct action
→ wrong action commits successfully
→ delayed semantic failure
→ ordinary retry cannot erase the failure
→ past learner-safe outcomes can identify g
```

The extension must also be isolated under `phase_v3_day34`; it may not alter
`external/tau2-bench`, `phase_v2_day30`, or native task data.

## 3. Native environment findings

### Airline

The native Airline database has 2,000 reservations, including 1,690 with two or
more segments, so it has ample multi-segment state variation.

`ReservationFlight` stores a historical price. During
`update_reservation_flights`, a segment whose flight/date/cabin still matches
keeps that stored price, while a replacement segment receives the current
catalog price. The tool then computes the difference against the old itinerary
and replaces the reservation's complete flight list.

This is a real state-dependent settlement mechanism, but two properties prevent
it from directly supplying the desired delayed-failure primitive:

1. the native tool description explicitly says the caller must provide the
   entire new itinerary; and
2. the same reservation can be modified repeatedly.

An in-memory native replay on reservation `VAAOXJ` changed `HAT287` to `HAT064`
and then successfully changed it back to `HAT287`. Therefore an Agent that
discovers a wrong price branch after mutation can recover; merely choosing the
wrong flight once does not establish Skill necessity.

The native certificate lifecycle does provide irreversibility, but the completed
Hidden Resource Semantics Pilot already showed why irreversibility alone is not
enough: visible amounts made the correct allocation obvious and Core E0 remained
12/12.

### Retail

The native Retail database has 1,000 orders, including 423 pending orders and
798 multi-item orders.

`modify_pending_order_items` provides a strong native commitment transition. A
successful call changes the order status from `pending` to
`pending (item modified)`. A second item modification then fails, while the
first mutation remains committed. In-memory replay on `#W5918442` confirmed this
behavior.

This is a useful delayed-consequence substrate, but it is not hidden operational
knowledge: both the native policy and tool description explicitly say that the
operation can be called only once and that all requested changes must be
collected first. A Pilot built only from this rule is likely to repeat the
PB-C02 problem: the Reference Skill restates behavior already available to a
strong Base Agent.

## 4. Isolation feasibility

The τ² runner resolves a domain name through the process-local registry, and a
run configuration accepts a string domain. A separate v3 factory can therefore
construct an extended DB and an `AirlineTools` or `RetailTools` subclass without
editing the native factories.

A process-local proof registered a temporary v3 Airline domain backed by a tool
subclass. It exposed the same 14 native tools, while constructing the ordinary
`airline` domain still returned the native `AirlineTools` class. Isolation is
therefore feasible.

Recommended boundary:

```text
phase_v3_day34/construction/<primitive>/environment/
├── data_model.py       # v3-only state or sidecar contract
├── tools.py            # subclass/composition with changed semantics
└── environment.py      # separate process-local domain factory
```

The Pilot runner registers this domain only in its own process. Native source,
native data, v2 tasks, and other editions continue to resolve the original
domain.

## 5. Candidate matrix

| ID | Candidate | Real native anchor | Required extension | Wrong action can commit? | Retry blocked? | Shortcut risk | Verdict |
|---|---|---|---|---:|---:|---|---|
| EE-01 | Channel-conditioned settlement + one-change commitment | Stored segment price and historical/current update delta | Stable visible contract/channel, two settlement baselines, explicit one-change budget | Yes | Yes | Medium | `RECOMMEND_GATE_0` |
| EE-02 | Channel-conditioned modification path | Direct update and cancel/rebook produce different state histories | Channel-dependent benefit/identity preservation | Yes | Potentially | Medium–high | `HOLD_SECONDARY` |
| EE-03 | Retail patch/replace contract | Multi-item collections and one-shot item update | New payload representation and two versioned write semantics | Potentially | Yes | High | `REJECT_CURRENT_FORM` |
| EE-04 | Retail one-shot disclosure | Native partial write persists and blocks a second call | User Simulator response branching | Yes | Yes | High | `HOLD_INTERACTION_TRACK` |
| EE-05 | Post-mutation revision rebinding | Native write/read surfaces | Replaceable revision IDs and dependent segment write | Usually error first | No without another constraint | High | `REJECT_AS_FIRST_PRIMITIVE` |
| EE-06 | Single-use resource lifecycle | Native certificate removal | None | Yes | Yes | Confirmed high | `REJECTED_TOO_EASY` |

The machine-readable inventory contains the full rationale for every row.

## 6. Recommended first mechanism

Proceed only to Gate 0 design for:

> **EE-01 — Channel-Conditioned Settlement Commit**

Proposed observable state:

```text
reservation
├── ticketing_channel / settlement_contract
├── complete stored itinerary and historical segment prices
├── current flight candidates and current prices
└── remaining_changes = 1
```

Proposed latent mapping:

```text
channel/contract A
→ unchanged segments use stored historical prices

channel/contract B
→ the complete itinerary uses current prices
```

The one-change budget is visible and documented; it is not part of the hidden
answer. Only the channel-to-settlement mapping is learned from experience.

A user gives a conditional itinerary goal, such as choosing candidate A only
when the resulting complete-reservation charge is within a threshold and using
candidate B otherwise. Carefully balanced prices make the correct branch differ
between the two settlement contracts.

The wrong branch must:

1. pass all native availability, payment, confirmation, and authorization
   checks;
2. return tool success;
3. consume the sole change budget;
4. leave the wrong final itinerary under the user's stated condition; and
5. reject a corrective second mutation.

This creates delayed semantic failure without hiding policy permission or
ending the episode after a recoverable error.

## 7. Why this is not claimed as a new native τ² fact

EE-01 deliberately builds on Benchmark v2's P2/P5 historical-settlement work.
The new contribution would be a clean v3-only selector and commitment contract
that makes the mapping counterfactually necessary and empirically testable.

It must therefore be described as:

> a controlled latent operational-semantics extension derived from native
> settlement structure

and not as a previously undiscovered native Airline rule.

## 8. Gate 0 requirements

This audit does not authorize implementation or rollout automatically. Before
EE-01 proceeds beyond design, two counter-directional tasks must demonstrate:

| Check | Required evidence |
|---|---|
| Mapping necessity | The same visible decision geometry produces different correct branches under the two contracts. |
| Correct paths | Both intended branches commit and receive semantic Success 1. |
| Wrong paths | Both opposite branches commit, consume the change budget, and receive semantic Success 0. |
| Non-recoverability | A second flight mutation is rejected after either first commit. |
| No obvious proxy | Channel name, amount magnitude, candidate order, wording, and entity ID do not reveal the branch. |
| Experience contrast | At least one success/failure intervention pair exists for each contract direction. |
| Information boundary | Base and Learner see the same contract field but neither sees its mapping at task start. |
| Evaluator independence | Success checks final itinerary, settlement, preserved fields, and change budget—not a prescribed call sequence. |

If the two contract directions cannot both be constructed without an obvious
shortcut, EE-01 should be rejected before any model call.

## 9. Final verdict

`ENVIRONMENT_EXTENSION_POINT_AUDIT = COMPLETE`

`RECOMMENDED_NEXT_ACTION = EE_01_GATE_0_DESIGN_ONLY`

The audit found a safe integration boundary and one candidate worth structural
prototyping. It did not find a native, already-hidden mechanism that can simply
be turned into a formal v3 family without extension and calibration.
