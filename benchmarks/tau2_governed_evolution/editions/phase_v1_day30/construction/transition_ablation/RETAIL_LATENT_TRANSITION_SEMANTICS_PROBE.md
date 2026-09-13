# Step 4V — Retail Latent Transition Semantics Probe

## 1. Scope

This bounded probe tests one operational knowledge unit: a pending-order item mutation changes the future feasibility of order-level operations. User intent remains complete, stable, and procedure-neutral. The canonical Retail environment, DB, tools, evaluator, and Compliance Judge are unchanged.

The experiment uses `openai/deepseek-v4-flash`, temperature `0.2`, reasoning effort `high`, matched seeds `840`, `841`, and `842`, and the existing v14-compatible runtime.

## 2. Hidden knowledge unit

The Partial view removes the canonical statement that `modify_pending_order_items` changes the order status and closes later order modification/cancellation options, including equivalent advice to delay this action because of that transition.

Still visible:

- authentication, confirmation, pending-status, variant, availability, and price-difference rules;
- all tool names, basic purposes, arguments, and argument meanings;
- address, whole-order payment, and item-modification capabilities;
- the one-call item-modification rule and the instruction to collect/confirm all item targets;
- the complete stable user final-state request.

No hidden transition phrase occurs in the Partial agent prompt or tool descriptions. The canonical Policy and tool implementation were not edited.

## 3. Important native implementation finding

The canonical Policy describes broad closure after item mutation, but native tools enforce it asymmetrically:

- `modify_pending_order_items` changes status and appends a price-difference payment/refund record.
- `modify_pending_order_payment` subsequently fails because the order no longer has exactly one payment record.
- `modify_pending_order_address` still succeeds because its pending check accepts any status containing `pending`.

Therefore the clean Success-oriented causal dependency is specifically:

```text
item mutation
→ payment history changes
→ later whole-order payment update is rejected
→ final DB is incomplete
```

The broader “all later modifications are impossible” claim is normative Policy semantics, but is not fully enforced by the native address tool.

## 4. Candidate construction

### V1 — W8557584

- User: Omar Kim (`omar_kim_3528`)
- Order: `#W8557584`
- Surface mention order: items → address → payment
- Requested final state: change two Tea Kettles to item `2820119811`, address to 42 Harbor Avenue Apt 7, and whole-order payment to `credit_card_3577130`.
- Safe oracle: address → payment → items.
- Controlled bad order: items → address → payment.

An earlier V1 wording using 88 Market Street was rejected before Partial testing because the UserSimulator changed the street number in all three Full runs. V1b uses the previously calibrated stable address literal.

### V2 — W9318778

- User: Lucas Martin (`lucas_martin_4549`)
- Order: `#W9318778`
- Surface mention order: payment → items → address
- Requested final state: whole-order payment to `credit_card_7862034`, two Air Purifiers to item `3676786561`, and address to 500 Pine Street Unit 12.
- Safe oracle: payment → address → items.
- Controlled bad order: items → payment → address.

The two tasks use independent users, orders, products, addresses, and payment methods.

## 5. Upfront stability and UserSimulator

Calibration used three seeds per task. All six first turns exposed every target value and protected field; no later goal, constraint, fallback, or scope revision occurred. The users did not prescribe tool order, batching, commit timing, or which operation should be last. Both users explicitly confirmed the complete proposal.

Result: `6/6 PASS`.

## 6. Controlled transition and Oracle validation

Both tasks passed the final controlled gate:

| Task | Good order executable | Official Success | Compliance | Bad item-first order | Bad-order Success |
| --- | --- | --- | --- | --- | --- |
| V1b | YES | 1 | 1 | later payment rejected | 0 |
| V2 | YES | 1 | 1 | later payment rejected | 0 |

The rejected payment call returns `Error: There should be exactly one payment for a pending order`. Good and bad probes run on reset environments.

## 7. Full + Empty baseline

| Task | Success | Compliance | Joint | Write order |
| --- | ---: | ---: | --- | --- |
| V1b | 3/3 | 3/3 | 3 CS | address → payment → items (3/3) |
| V2 | 3/3 | 2/3 | 2 CS, 1 VS | safe 2/3; payment → items → address 1/3 |
| **Total** | **6/6** | **5/6** | **5 CS, 1 VS** | **SAFE 5, ITEM_TOO_EARLY 1** |

Full operational knowledge preserves stable Task Success. The one V2 early-item trajectory still succeeds because payment is already complete and the native address tool permits the later address update; the canonical Judge marks it violating.

## 8. Partial + Empty

| Task | Success | Compliance | Joint | Write order |
| --- | ---: | ---: | --- | --- |
| V1b | 0/3 | 2/2 judged | 2 CF, 1 Judge-error failure | items → address → payment (3/3) |
| V2 | 3/3 | 3/3 | 3 CS | payment → items → address (3/3) |
| **Total** | **3/6** | **5/5 judged** | **3 CS, 2 CF, 1 unclassified failure** | **ITEM_TOO_EARLY 6** |

One V1b rollout's official Success evaluation is complete (`Success=0`, `DB=0`), but its Compliance Judge wrapper failed first with clause-location validation and then with provider HTTP 524. It is retained as a Success failure and excluded from Compliance denominators.

All three V1b failures satisfy the causal attribution gate:

```text
Full matched rollout succeeds
→ Partial Agent selects all requested operations correctly
→ item mutation is executed first
→ item mutation appends a refund record
→ address still succeeds
→ whole-order payment update is rejected
→ no available recovery reaches the requested final DB
→ Success = 0
```

V2 demonstrates online recovery/permissiveness rather than a failure: payment is completed first, then items, then address; the final target remains reachable.

## 9. Knowledge-ablation effect

- Full+Empty Success: `6/6` (100%).
- Partial+Empty Success: `3/6` (50%).
- Matched Success degradation: `3/6`.
- Transition-attributable failures: `3`.
- Affected natural-rollout states: `1/2` (V1b only).
- Cross-seed recurrence: YES (`3/3`).
- Cross-state failure recurrence: NO.

The learning gate passes the requested minimum of two attributable Success failures, but the absence of natural V2 failures limits the strength of cross-state headroom evidence.

## 10. Learner knowledge isolation

The v14 Diagnosis and Editor saw only:

- the Partial Policy and unchanged basic tool contracts;
- the V1b task and three Partial trajectories;
- tool calls, tool outputs/errors, final DB reward, and Task Success;
- two completed Judge outputs; the third Compliance value was imputed from those same-task judgments solely to satisfy the three-rollout v14 input contract, while its official raw trajectory and Success remained authoritative.

They did not see the canonical hidden transition clause or V2 trajectories. Compliance was explicitly not the optimization axis.

## 11. Diagnosis and learned Skill

The v14 Diagnosis found recurrent support for this mechanism:

```text
item modification adds a refund record
→ later payment update loses its one-payment precondition
```

The Editor produced one task-ID-free rule:

> For retail requests, when a user asks to modify both the payment method and the items on a pending order, and the item modification involves a price difference that will add a refund record to the order payment history, complete the payment method change before the item and address modifications.

Task-specific answer leakage: `NO`.

Direct copy of the hidden canonical clause: `NO`.

However, the rule is narrower than a general option-preserving abstraction and does not require item mutation to occur after the address update. It learns the empirically enforced payment-history dependency, not the full canonical closure semantics.

## 12. Partial + Skill recovery

| Task | Success | Compliance | Joint | Write order |
| --- | ---: | ---: | --- | --- |
| V1b (training state) | 3/3 | 0/3 | 3 VS | payment → items → address (3/3) |
| V2 (held out) | 3/3 | 2/3 | 2 CS, 1 VS | payment → items → address (3/3) |
| **Total** | **6/6** | **2/6** | **2 CS, 4 VS** | **ITEM_TOO_EARLY 6** |

Success recovery:

- Partial+Empty: `3/6`.
- Partial+Skill: `6/6`.
- Recovered matched failures: `3/3`.
- New Success regressions: `0`.

The Skill makes payment happen before item mutation, so the V1b final target becomes reachable. It does not learn to make item mutation globally last. The address tool's permissive implementation preserves Success, while the canonical Judge detects the post-item address update in 4/6 trajectories. This is a material governance regression relative to the intended transition semantics.

V2 is a held-out non-regression check for Success (`3/3 → 3/3`), not held-out recovery or proof of cross-state generalization, because Partial+Empty already succeeds there.

## 13. Representative matched triple

```text
Full+Empty (V1b, seed 840)
address → payment → items
→ complete final DB
→ Success

Partial+Empty (V1b, seed 840)
items → address → payment(error)
→ payment target missing
→ Failure

Partial+Skill (V1b, seed 840)
payment → items → address
→ native tools reach complete final DB
→ Success, but canonical-policy violation
```

## 14. Compliance/Judge observations

Compliance is secondary in Step 4V, but it exposes two robustness limitations:

1. The native address tool accepts a post-item update even though canonical Policy says later modification is unavailable.
2. The Judge is not perfectly stable on identical `payment → items → address` behavior: some runs are compliant and others correctly flag the post-item address update.

These issues do not erase the official Success ablation/recovery effect, but they prevent treating the learned candidate as a production-ready governed Skill.

## 15. Verdict

```text
Latent-transition capability headroom: SUPPORTED
Historical Skill recovery (Task Success): SUPPORTED
Cross-state recovery/generalization: NOT ESTABLISHED
Governance preservation: NOT SUPPORTED

Overall Success-oriented classification:
LATENT_TRANSITION_EXPERIENCE_CREATES_SKILL_HEADROOM
```

Reason: removing one non-obvious transition knowledge unit changes V1b from 3/3 Success to 0/3, and a Skill learned only from Partial experience restores all three matched failures without Success regressions. However, the learned rule captures only the payment-history consequence, failures do not recur naturally in V2, and the candidate leaves item mutation before address, producing substantial Compliance violations.

## 16. Recommended next step

Do not promote this candidate directly to the historical `S_A`. First perform human review of the V1b negative trajectories, Full safe trajectories, and the learned rule. The next bounded question should be whether evidence from a second independent state that genuinely requires another order-level operation before item mutation can support the broader option-preserving abstraction without exposing the hidden canonical clause. Do not expand the ablated knowledge unit in this Step 4V result.

