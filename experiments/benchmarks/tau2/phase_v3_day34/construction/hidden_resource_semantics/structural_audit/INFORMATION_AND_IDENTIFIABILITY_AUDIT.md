# Hidden Resource Semantics — Structural and Information Audit

## Native backend result

The mechanism is admitted. In native `AirlineTools.book_reservation`, gift-card
payments subtract only the charged amount. Certificate payments instead remove
the entire certificate entry from `user.payment_methods` after validation,
regardless of the amount charged. Direct replay verified that every Core and
Held-out bad allocation completes its smaller booking, consumes the certificate,
and then cannot fund the larger required booking; the paired valid allocation
completes both goals. No backend code was changed.

## Agent-visible information audit

| Source | Contains complete single-use semantics? | v3 Pilot treatment |
|---|---:|---|
| Standard LLMAgent instruction | No | Unchanged |
| Native Airline policy | Yes: one sentence says unused certificate value is not refundable | Remove exactly that sentence in this Pilot's Agent-visible policy only |
| Remaining Airline policy | No complete rule; retains payment types and one-certificate-per-reservation limit | Unchanged and visible |
| `book_reservation` tool schema | No | Unchanged and visible |
| Certificate data-model/schema | No; exposes type, ID, and face amount | Unchanged and visible |
| `get_user_details` before redemption | No; exposes current instance-specific payment resources | Unchanged and visible |
| Successful booking output | No; returns the created reservation and payment record | Unchanged and visible |
| `get_user_details` after redemption | Does not explain the rule, but the used certificate is absent | Unchanged runtime evidence |
| Reusing the consumed certificate | No complete explanation; returns `Payment method <id> not found` | Unchanged runtime evidence |
| User simulator prompt | Explicitly prohibited from explaining reuse/forfeiture semantics | Does not leak K through dialogue |
| Task description/evaluation actions | Construction/evaluator-only and contains valid allocation | Never placed in Agent context |
| Reference Skill | Yes | ER condition only; never available to E0/EI or Learner |
| Existing Skill/memory | Not loaded | No Parent Skill, Diagnosis, Editor, or evolution memory is run |

The semantic context difference is intentionally one-sided: the Pilot omits the
native sentence about unused certificate value but inserts no contradictory
description. All transaction, fare, passenger, flight, payment-method, and
balance facts remain obtainable through the normal request and tools.

## Task audit

| Task | Role | Transactions | Resources | Bad allocation | Valid allocation | Why bad path fails | Semantic invariant |
|---|---|---|---|---|---|---|---|
| HRS-C1 | CAPABILITY_CORE | $50 basic + $100 basic | certificate $100; gift $67 | cert→$50, gift→$100 | gift→$50, cert→$100 | certificate disappears; gift cannot cover $100 | Both exact bookings exist; no extra booking |
| HRS-C2 | CAPABILITY_CORE | $70 basic + $150 economy | certificate $150; gift $85 | cert→$70, gift→$150 | gift→$70, cert→$150 | certificate disappears; gift cannot cover $150 | Same |
| HRS-C3 | CAPABILITY_CORE | $100 basic + $250 business | certificate $250; gift $103 | cert→$100, gift→$250 | gift→$100, cert→$250 | certificate disappears; gift cannot cover $250 | Same |
| HRS-C4 | CAPABILITY_CORE | $150 economy + $250 business | certificate $250; gift $188 | cert→$150, gift→$250 | gift→$150, cert→$250 | certificate disappears; gift cannot cover $250 | Same |
| HRS-P1 | PROTECTED_CONTROL | One $350 business booking | certificate $500 | Not applicable | certificate→$350 | Direct certificate use is correct and sufficient | Exact single booking exists |
| HRS-P2 | PROTECTED_CONTROL | $100 economy + $150 economy | certificate $150; gift $290 | No harmful early use | cert→$100, gift→$150; two alternatives also valid | Gift remains sufficient after early certificate use | Both bookings; any feasible allocation accepted |
| HRS-H1 | HELD_OUT_TRANSFER | $200 economy + $350 business | certificate $500; gift $288 | cert→$200, gift→$350 | gift→$200, cert→$350 | certificate disappears; gift cannot cover $350 | Both exact bookings; no extra booking |
| HRS-H2 | HELD_OUT_TRANSFER | $250 business + $350 business | certificate $500; gift $289 | cert→$250, gift→$350 | gift→$250, cert→$350 | certificate disappears; gift cannot cover $350 | Same |

Before the first payment the Agent can observe every required booking, exact
runtime fare, passenger data, and all saved payment IDs/types/amounts. Only the
post-redemption resource semantics are omitted. Thus each task is information-
sufficient but requires either prior knowledge or globally cautious allocation.

## Deterministic construction validation

- Native certificate deletion was observed without modifying Airline code.
- All six Core/Held-out bad paths produced one completed booking, certificate
  absence, a later insufficient-resource error, and semantic Success 0.
- All eight preferred valid paths produced semantic Success 1.
- Both additional P2 allocations produced semantic Success 1, demonstrating
  that evaluation does not impose a unique payment order.
- P1 verifies that the Reference Skill must still allow immediate certificate use.

## Experience-identifiability assessment

**Pre-rollout assessment: PARTIAL.** K is not directly stated by success or error
messages. A future Learner can infer it from repeated patterns when trajectories
contain a small booking paid by certificate, later absence/reuse failure, an
unfinished second goal, and Success 0, contrasted with successful global
allocations. A trajectory that never re-reads the profile or retries the
certificate exposes weaker evidence: it shows the allocation/outcome pattern but
not the state transition directly. Final calibration trajectories must therefore
be inspected before upgrading this assessment to YES.

Feedback classification is `INFERRED_FROM_OUTCOME_PATTERN`, not
`DIRECTLY_REVEALED_BY_FEEDBACK`: neither native success output nor the later
`payment method not found` error explains single-use remainder forfeiture in a
complete natural-language rule.
