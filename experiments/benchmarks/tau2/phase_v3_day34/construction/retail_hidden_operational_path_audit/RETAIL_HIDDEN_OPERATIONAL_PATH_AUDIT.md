# Retail Hidden Operational Path Audit

## Outcome

The audit is complete. It used no model calls and made no changes to native τ²,
Benchmark v2, or the formal v3 task set.

Native Retail supplies useful irreversible anchors, but it does not by itself
contain a hidden operational-path Skill gap. The public Policy already states
the relevant order eligibility, one-call boundaries, refund destinations, and
need to collect all requested item changes. The intended exchange-versus-return
primitive therefore requires a small isolated v3 environment extension.

The audit recommends only `RHP-01 — Fulfillment-Conditioned Exchange or Return`
for a two-task Gate 0 design. It does not authorize task expansion or rollout.

## Stable-Intent boundary

Every candidate was evaluated under the following user contract:

```text
first user turn
→ a natural, sufficiently specified, solvable request

later user turns
→ authentication, confirmation, or clarification of the same intent
→ no added, revised, or selectively revealed required goal information
→ no hint about hidden environment semantics
```

The user need not enumerate every condition, priority, fallback, or identifier.
The hidden variable must be an environment mechanism: task failure cannot be
manufactured by omitting information the Agent needed from the user.

## Native evidence

The source audit covered `RetailTools`, the Retail data model, the native
Policy, and the 1,000-order database. Relevant native state includes pending and
delivered orders, item variants, fulfillment item groups, payment history, and
gift-card balances.

In-memory replay established three consequential transitions:

1. Exchange on a delivered order succeeds, changes status to
   `exchange requested`, and makes a later return fail without rollback.
2. Return on the same initial delivered order succeeds, changes status to
   `return requested`, and makes a later exchange fail without rollback.
3. A pending item modification succeeds, changes status to
   `pending (item modified)`, and blocks a second item modification and
   cancellation without rolling back the first write.

These are genuine backend consequences, not evaluator inventions. They are not
yet hidden knowledge: the Policy explicitly describes the one-shot constraints
and the ordinary exchange/return rules.

Native Retail also lacks several states or actions assumed by common task ideas:

- no fulfillment mode with benefit-preservation semantics;
- no promotion or purchase-protection state;
- no mixed-payment provenance;
- no reusable replacement-history state machine; and
- no create-order or reorder tool.

Claims about those mechanisms must therefore be labelled v3-only extensions,
not native τ² discoveries.

## Candidate screen

| ID | Candidate | Native anchor | Required extension | Verdict |
|---|---|---|---|---|
| RHP-01 | Fulfillment-conditioned exchange or return | Both writes commit and are mutually exclusive | Visible fulfillment mode plus stable benefit-preservation contract | `RECOMMEND_GATE_0` |
| RHP-02 | Payment-provenance refund routing | Return stores one destination | Mixed-payment provenance and routing | `HOLD_SECONDARY` |
| RHP-03 | Replacement-history resolution | Terminal delivered resolution | History state and another executable continuation path | `HOLD_NEEDS_TOOL_DESIGN` |
| RHP-04 | Pending mutation order | Native one-shot item modification | None | `REJECT_POLICY_VISIBLE` |
| RHP-05 | Promotion-preserving refund/reorder | Native refund state | Promotion system and reorder action | `REJECT_CURRENT_SCOPE` |
| RHP-06 | Split-fulfillment partial resolution | Fulfillment groups exist | Fulfillment-scoped transitions | `REJECT_NO_COUNTER_DIRECTION` |

## Recommended Gate 0 primitive

`RHP-01` keeps the user's complete conditional choice visible from the first
turn:

> Exchange the named delivered item for the named variant if the original
> purchase protection remains after exchange; otherwise return that item to the
> stated allowed payment method. Do not perform another resolution.

The proposed observable state is the delivered order, selected item and
replacement variant, allowed payment method, purchase-protection requirement,
and a fulfillment mode. The stable v3-only mechanism determines whether the
exchange path preserves that protection.

Two Gate 0 tasks must point in opposite directions:

```text
fulfillment mode A
→ exchange preserves protection
→ exchange is correct
→ return commits but violates the preferred conditional goal

fulfillment mode B
→ exchange loses protection
→ return is correct
→ exchange commits but violates the protected condition
```

In both cases the wrong first call must pass native eligibility, return success,
enter a terminal request state, and reject the opposite corrective path. The
evaluator checks the semantic final state and benefit outcome, not a prescribed
call sequence.

## Why other candidates do not proceed

The native pending-order sequence is unsuitable because the public Policy gives
the procedure directly and Stable-Intent excludes delayed user disclosure as a
source of difficulty. Refund/reorder is also unavailable because Retail has no
order-creation action. Mixed-payment and replacement-history candidates require
larger state and tool changes than needed for a second primitive. Split
fulfillment has no reverse-direction case: a complete single call dominates.

## Next authorized action

Only a two-task, process-local `RHP-01` Gate 0 prototype is eligible next. Before
any model call it must prove two correct and two opposite committed backend
paths, non-recoverability, policy neutrality, native/v2 isolation, and no fixed
exchange/return shortcut. If that proof fails, the candidate is rejected rather
than expanded.
