# Hidden Single-Use Resource Semantics Pilot

## 1. Mechanism definition

This Benchmark v3 Pilot tests whether hiding one task-general runtime rule creates
a Success-addressable knowledge gap:

> A travel certificate is consumed by one successful booking. Any unused face
> value is unavailable to later transactions, so multiple pending payments must
> be allocated globally before the first redemption.

Only this mechanism was tested. Benchmark v2, PB-C02, Primitive A/C, the native
Airline backend, and formal Skill Evolution were not changed.

## 2. Native backend audit

The native backend supports the hypothesized behavior. In
`AirlineTools.book_reservation`, gift-card charges subtract only the charged
amount, while a certificate charge removes the entire payment-method entry with
`user.payment_methods.pop(payment_id)`. This occurs after all payment checks and
before the new reservation is committed. A successful booking returns ordinary
reservation state; a later reuse attempt reports only `Payment method <id> not
found`.

Cancellation does not restore the removed certificate. Deterministic direct-tool
replay therefore established a genuinely irreversible capability dependency;
the backend was not modified.

## 3. Agent-visible context difference

The native Airline policy contains one explicit sentence saying that the
remaining amount of a travel certificate is not refundable. For this Pilot only,
the runner removes exactly that sentence from the policy supplied to both the
Agent and its runtime environment. It inserts no replacement or contrary rule.

Everything instance-specific remains observable: requested bookings, passenger,
routes, dates, cabins, runtime fares, payment-method IDs/types, certificate face
value, gift-card balance, tool schemas, and native tool results. The remaining
policy still names certificates as payment methods and retains the native
one-certificate-per-reservation limit.

## 4. Leakage audit

| Source | Complete K visible before redemption? | Treatment/result |
|---|---:|---|
| Base Agent instruction | No | Unchanged |
| Native Airline policy | Yes, in one sentence | Removed only in this v3 Pilot runtime |
| Tool descriptions and payment schema | No | Unchanged |
| Initial profile serialization | No; instance facts only | Unchanged and visible |
| Successful booking response | No | Unchanged |
| Refreshed profile after use | No prose rule; certificate is absent | Retained as legitimate experience |
| Reuse error | No prose rule; method is `not found` | Retained as legitimate experience |
| User simulator | No | Explicitly does not explain K |
| Task/evaluator construction metadata | Yes | Never inserted into Agent context |
| Relevant Reference Skill | Yes | ER calibration only |
| Existing Skill/evolution memory | Not loaded | No Learner, Diagnosis, Editor, or Parent Skill run |

Result: no task-start leakage and no misleading replacement semantics were
found. The complete rule is not directly revealed by native feedback.

## 5. Task family

| Task | Role | Required transactions | Resources | Bad allocation | Valid allocation | Why the bad path fails | Semantic invariant |
|---|---|---|---|---|---|---|---|
| HRS-C1 | CAPABILITY_CORE | $50 basic; $100 basic | cert $100; gift $67 | cert→$50; gift→$100 | gift→$50; cert→$100 | cert disappears; gift cannot cover $100 | Both exact active bookings, no extra booking |
| HRS-C2 | CAPABILITY_CORE | $70 basic; $150 economy | cert $150; gift $85 | cert→$70; gift→$150 | gift→$70; cert→$150 | cert disappears; gift cannot cover $150 | Same |
| HRS-C3 | CAPABILITY_CORE | $100 basic; $250 business | cert $250; gift $103 | cert→$100; gift→$250 | gift→$100; cert→$250 | cert disappears; gift cannot cover $250 | Same |
| HRS-C4 | CAPABILITY_CORE | $150 economy; $250 business | cert $250; gift $188 | cert→$150; gift→$250 | gift→$150; cert→$250 | cert disappears; gift cannot cover $250 | Same |
| HRS-P1 | PROTECTED_CONTROL | One $350 business booking | cert $500 | None | cert→$350 | Immediate certificate use is correct | Exact single active booking |
| HRS-P2 | PROTECTED_CONTROL | $100 economy; $150 economy | cert $150; gift $290 | No harmful early use | cert→$100; gift→$150; alternatives valid | Gift can still fund the remainder | Both exact active bookings; any feasible allocation |
| HRS-H1 | HELD_OUT_TRANSFER | $200 economy; $350 business | cert $500; gift $288 | cert→$200; gift→$350 | gift→$200; cert→$350 | cert disappears; gift cannot cover $350 | Both exact active bookings, no extra booking |
| HRS-H2 | HELD_OUT_TRANSFER | $250 business; $350 business | cert $500; gift $289 | cert→$250; gift→$350 | gift→$250; cert→$350 | cert disappears; gift cannot cover $350 | Same |

The evaluator matches semantic final state, including exact active requested
bookings and absence of extra bookings. It does not require a tool order or a
specific payment allocation. P2's three feasible allocation patterns were all
validated as Success.

## 6. Construction validation

- All six Core/Held-out bad paths created the smaller booking, removed the
  certificate, then failed to complete the larger target: Success 0.
- All eight preferred valid paths completed their semantic goals: Success 1.
- Two additional P2 allocations also returned Success 1.
- P1 proved that immediate certificate use remains allowed by both Skill and
  evaluator.
- Native backend semantics and instance facts were unchanged.

Construction verdict: `PASS_CONSTRUCTION`.

## 7. Skill conditions

**E0 — Empty Skill:** standard Base Agent with no added certificate guidance.

**ER — Relevant Reference Skill (CALIBRATION ONLY):** treat a certificate as an
irreversible single-use resource; review all pending transactions and resources,
plan globally, and use the certificate where its consumption does not make the
remaining goals infeasible. It also explicitly permits immediate use when no
future conflict exists.

**EI — Irrelevant Skill (CALIBRATION ONLY):** verify that payment methods belong
to the correct customer, bind amounts accurately, and report tool outcomes
truthfully. It contains no irreversibility, global-allocation, remainder-loss,
or certificate-prioritization knowledge.

Neither calibration Skill contains task IDs, users, flights, concrete
amount-to-transaction answers, or held-out solutions.

## 8. Smoke test

The corrected, frozen eight-task suite ran one E0 and one ER trajectory per task:

| Role | Empty | Relevant |
|---|---:|---:|
| CAPABILITY_CORE | 4/4 | 4/4 |
| PROTECTED_CONTROL | 2/2 | 2/2 |
| HELD_OUT_TRANSFER | 2/2 | 2/2 |
| Overall | 8/8 | 8/8 |

Search, payment state, mutation, skill injection, semantic evaluation, and both
controls behaved as designed. One pre-freeze wording bug in H2 used “business
trips,” which the user simulator interpreted as trip purpose rather than cabin;
it was corrected to explicit “business class.” The invalid H2 smoke artifacts
were removed from the Pilot output and were not used for calibration. No task was
made harder in response to model performance.

## 9. Formal calibration

Three matched seeds (300, 301, 302) were used for every task and condition, for
72 trajectories total. Model, temperature, thinking, token budget, tools,
backend, user simulator, initial task state, and Agent-visible policy were held
constant across E0/ER/EI.

| Role | Empty | Relevant | Irrelevant |
|---|---:|---:|---:|
| CAPABILITY_CORE | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) |
| PROTECTED_CONTROL | 6/6 (100.0%) | 6/6 (100.0%) | 6/6 (100.0%) |
| HELD_OUT_TRANSFER | 5/6 (83.3%) | 6/6 (100.0%) | 4/6 (66.7%) |
| Overall | 23/24 (95.8%) | 24/24 (100.0%) | 22/24 (91.7%) |

## 10. Lift and specificity

| Metric | Result |
|---|---:|
| Core Relevant Lift | 0.0 pp |
| Core Irrelevant Lift | 0.0 pp |
| Core Skill Specificity Gap | 0.0 pp |
| Held-out Relevant Lift | +16.7 pp |
| Overall Relevant Lift | +4.2 pp |
| Overall Irrelevant Lift | −4.2 pp |
| Overall Skill Specificity Gap | +8.3 pp |
| Control Regression (Relevant − Empty) | 0.0 pp |

The isolated H2 separation is directionally consistent with the intended Skill,
but it cannot establish a family-level Skill gap when all 12 Core Empty rollouts
already succeed.

## 11. Per-task Success

| Task | Empty | Relevant | Irrelevant |
|---|---:|---:|---:|
| HRS-C1 | 3/3 | 3/3 | 3/3 |
| HRS-C2 | 3/3 | 3/3 | 3/3 |
| HRS-C3 | 3/3 | 3/3 | 3/3 |
| HRS-C4 | 3/3 | 3/3 | 3/3 |
| HRS-P1 | 3/3 | 3/3 | 3/3 |
| HRS-P2 | 3/3 | 3/3 | 3/3 |
| HRS-H1 | 3/3 | 3/3 | 3/3 |
| HRS-H2 | 2/3 | 3/3 | 1/3 |

## 12. Failure attribution and consistency

| Condition | Failures | Early certificate | Local optimization | Feasibility misplanning | Unnecessary avoidance | Binding | Unrelated |
|---|---:|---:|---:|---:|---:|---:|---:|
| Empty | 1/24 | 1 | 0 | 0 | 0 | 0 | 0 |
| Relevant | 0/24 | 0 | 0 | 0 | 0 | 0 | 0 |
| Irrelevant | 2/24 | 2 | 0 | 0 | 0 | 0 | 0 |

All observed failures are focal and internally consistent, but they occur only
on HRS-H2. For the requested Core Empty consistency measure: total failures = 0,
dominant mode = none, dominant fraction = undefined. Thus there is no stable
Core failure pattern for a Skill to summarize.

In E0/HRS-H2/seed-302, the $500 certificate paid the first $250 booking; the
second booking tried to reuse it, received `Payment method <id> not found`, and a
profile refresh showed only the $289 gift card. Cancelling the first booking did
not restore the certificate. EI seeds 301 and 302 followed the same irreversible
early-consumption pattern.

## 13. Protected controls and held-out transfer

Relevant remained 6/6 on controls, including immediate certificate use on P1,
so there is no evidence of “never use a certificate early” overgeneralization.
Control regression is 0.0 pp.

Relevant improved held-out Success from 83.3% to 100%, while Irrelevant reached
66.7%. However, the effect comes entirely from one surface variant (H2), with
only six rollouts per condition, and is not backed by any Core headroom. It is a
useful directional observation, not evidence of transferable Skill sensitivity.

## 14. Experience-identifiability

Representative failures expose: initial certificate amount; a smaller successful
certificate-funded booking; later certificate reuse failure; certificate absence
from a refreshed profile; incomplete final goals; and Success 0. Representative
successes expose the contrasting gift-card-small/certificate-large allocation and
Success 1. The backend never emits a complete natural-language statement that
unused value was forfeited.

Feedback classification: `INFERRED_FROM_OUTCOME_PATTERN`, not
`DIRECTLY_REVEALED_BY_FEEDBACK`.

Final assessment: `PARTIAL`. The causal rule is recoverable from the observed H2
failure pattern without oracle metadata. But all Core E0 trajectories succeeded;
if held-out examples remain withheld as intended, the designated train-side
experience contains no negative contrast from which a Learner could reliably
recover K. Running Learner recovery on this exact split would therefore test
prior knowledge or imitation of already-successful behavior more than recovery
from failure.

## 15. Why the hidden rule was insufficient

The Base Agent naturally performed constraint-first resource arithmetic. In
successful E0 trajectories it observed both prices and balances, noticed that
the gift card could fund only the smaller booking, and assigned the certificate
to the larger booking. This strategy succeeds without committing to the stronger
belief that certificate remainder is forfeited: preserving the only resource
capable of covering the larger transaction is already a common-sense robust plan.

The Relevant Skill therefore mostly restated behavior already induced by the
visible instance geometry. The 100% Core EI result confirms that high-quality
extra payment instructions were neither necessary nor sufficient to distinguish
conditions. The issue is not generic prompting, information insufficiency, or
control damage; it is lack of Core headroom.

## 16. Final verdict and next decision

**`FAIL_TOO_EASY`**

The native dependency is real, construction is valid, information leakage was
not found, and the few failures are focal. Nevertheless, Core Empty Success is
100%, Core Relevant Lift is 0 pp, and Core specificity is 0 pp. Hidden
single-use certificate semantics therefore does **not** produce a validated
Success Skill gap under the current strong Base Agent and task family.

This exact Pilot should not proceed to a real Learner recovery experiment. A
future, separately scoped construction would first need a legitimate train-side
experience signal whose solution cannot be obtained from visible resource
arithmetic alone. This report does not implement replacement semantics,
historical pricing, additional hiding, a weaker model, or any environment change.
