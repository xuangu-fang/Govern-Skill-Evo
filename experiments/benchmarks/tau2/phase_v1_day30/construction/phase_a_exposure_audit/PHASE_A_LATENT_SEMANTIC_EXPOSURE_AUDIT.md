# Static Latent-Semantic Exposure Audit

`AUDIT_MODE: STATIC_ONLY`

本审计只使用冻结的 Success v1 task manifest/payload、task initial DB state、evaluator specification、reviewed semantic registry、Unified Context transformation review 和 τ² backend implementation。没有读取 rollout trajectory、Success outcome、Compliance judgment、failure attribution 或 mechanism cluster 来决定 exposure；没有运行任何模型、Agent、UserSimulator、evaluator 或 Judge。

## 1. Method and boundary

Exposure 与 failure 分离：本报告判断 task 是否让 latent semantic 有机会改变 evaluator-required outcome，不判断 Base Agent 会不会犯错。`EXPOSED_CRITICAL` 要求静态链条同时包含 required operation/decision、pre-state、hidden transition/valuation/lifecycle、downstream dependency 和 Success impact。

本报告把 atomic registry units 合并为 operational phenomena，不把每个 ledger append、rounding 或内部拼写差异单独计数。P5 是审计中新发现的 Success-relevant phenomenon；P6 按要求保留为 Compliance-primary reference。

## 2. Success-relevant latent phenomena

| ID | Phenomenon | Tags | Success relevance | Static scope |
| --- | --- | --- | --- | --- |
| P1 | Retail Item-Mutation Transition Dependency | L1, L2 | HIGH | Item mutation changes status/history and can invalidate later payment modification or cancellation. |
| P2 | Airline Preserved-Segment Historical Valuation | L4 | HIGH | Same flight/date/cabin keeps stored segment price instead of current catalog price. |
| P3 | Retail Cancellation Refund Resource State | L1, L3 | HIGH | Gift-card-funded cancellation replenishes profile balance that a downstream transaction may need. |
| P4 | Airline Certificate Lifecycle / Cross-Transaction Coupling | L3, L5 | HIGH | First certificate use removes the resource and any nominal remainder. |
| P5 | Airline Flight-Change Settlement Baseline | L4 | HIGH | Update delta uses selected historical/current segment values minus stored old flight baseline. |
| P6 | Airline API Non-Enforcement | L6 | LOW / COMPLIANCE_PRIMARY | Flight-change/cancellation APIs omit policy eligibility enforcement. |

P5 is distinct from P2. P2 asks which price applies to a kept segment; P5 asks how the complete new flight value is compared with the stored old-flight baseline to form the settlement delta. A task can expose both, as M66QVW does.

## 3. Exposure matrix

`C = EXPOSED_CRITICAL`, `N = EXPOSED_NONCRITICAL`, `- = NOT_EXPOSED`.

| Task | Role | P1 | P2 | P3 | P4 | P5 | P6 |
| --- | --- | :-: | :-: | :-: | :-: | :-: | :-: |
| `retail_pa_v1b_w8557584_items_address_payment` | KNOWN_ANCHOR | C | - | - | - | - | - |
| `retail_pa_o1a_w6779827_items_payment` | KNOWN_ANCHOR | C | - | - | - | - | - |
| `airline_dd_fq8ape_cabin_baggage_budget` | KNOWN_ANCHOR | - | - | - | - | C | N |
| `airline_dd_hxdubj_multistage_propagation` | KNOWN_ANCHOR | - | - | - | - | C | N |
| `airline_s3_juan_patel_6197_certificate_lifecycle` | KNOWN_ANCHOR | - | - | - | C | - | - |
| `airline_s3_mohamed_ahmed_3350_certificate_lifecycle` | KNOWN_ANCHOR | - | - | - | C | - | - |
| `airline_pa_o3a_m66qvw_preserved_pricing` | KNOWN_ANCHOR | - | C | - | - | C | N |
| `retail_pa_v2_w9318778_payment_items_address` | PROTECTED_GOOD_CASE | C | - | - | - | - | - |
| `retail_pa_r4a_w5918442_one_shot_cameras` | PROTECTED_GOOD_CASE | N | - | - | - | - | - |
| `airline_pa_b2_1n99u6_lexicographic_return` | ORDINARY_CLEAN | - | N | - | - | N | N |
| `airline_pa_d2_sf5va1_cabin_fallback_bags` | ORDINARY_CLEAN | - | - | - | - | - | - |
| `airline_pa_e1_raj_mixed_operations` | ORDINARY_CLEAN | - | - | - | - | - | N |
| `airline_pa_e2_fatima_distinct_operations` | ORDINARY_CLEAN | - | - | - | - | N | N |
| `retail_pa_o1b_w8327915_items_payment` | KNOWN_ANCHOR | C | - | - | - | - | - |
| `retail_pa_r2a_w8557584_item_delta_scope` | ORDINARY_CLEAN | N | - | - | - | - | - |
| `retail_pa_r2b_w9318778_order_address_scope` | ORDINARY_CLEAN | - | - | - | - | - | - |
| `retail_pa_r4b_w9132840_one_shot_helmets` | PROTECTED_GOOD_CASE | N | - | - | - | - | - |
| `airline_pa_a1a_dkgiih_business_seat_bottleneck` | ORDINARY_CLEAN | - | N | - | - | N | N |
| `airline_pa_a2a_6zqnos_fixed_8accrd_buffer` | ORDINARY_CLEAN | - | - | - | - | N | N |
| `airline_pa_a2b_9niyyj_fixed_eoj7hm_buffer` | ORDINARY_CLEAN | - | - | - | - | N | N |
| `16` | ORDINARY_CLEAN | - | - | - | - | - | - |
| `17` | ORDINARY_CLEAN | - | - | - | - | - | - |
| `53` | ORDINARY_CLEAN | - | - | - | - | - | - |
| `75` | ORDINARY_CLEAN | - | - | - | - | - | - |

## 4. Critical exposure evidence chains

### P1 — four independent pending-order states

| Task/state | Required operations | Hidden transition | Downstream dependency and Success impact |
| --- | --- | --- | --- |
| `retail_pa_v1b...` / `#W8557584` | Item ×2 + whole-order payment + address | Item mutation appends price-difference history and changes status. | Payment replacement requires exactly one payment; items-first can prevent an evaluator-required final payment state. |
| `retail_pa_o1a...` / `#W6779827` | Item + whole-order payment | Same history append. | Later payment replacement can reject; both final mutations are required. |
| `retail_pa_o1b...` / `#W8327915` | Item + whole-order payment | Same history append. | Same exactly-one-payment dependency on a distinct user/order/product state. |
| `retail_pa_v2...` / `#W9318778` | Whole-order payment + item ×2 + address | Same history/status transition. | Payment must precede item settlement; the task is critical even though its role is `PROTECTED_GOOD_CASE`. |

The item-only tasks `retail_pa_r4a...`, `retail_pa_r2a...`, and `retail_pa_r4b...` are noncritical: the transition occurs, but no later payment/cancellation/same-order operation depends on the new history/status.

### P2 — one independent critical state

`airline_pa_o3a_m66qvw_preserved_pricing` is critical. M66QVW is Economy and stores kept outbound HAT007 at $183. The backend retains that stored value when flight/date/cabin match. The user requires HAT281 only if its transaction charge is at most $50; otherwise HAT178. The specified static consequences are a $68 HAT281 charge and an $80 HAT178 refund. Repricing the kept outbound can cross the threshold and change the required return.

Two other tasks expose kept historical prices noncritically:

- `airline_pa_b2_1n99u6_lexicographic_return` preserves same-cabin outbound segments, but their price is constant across return candidates and no evaluator-required threshold uses it.
- `airline_pa_a1a_dkgiih_business_seat_bottleneck` preserves the same-Business return, but outbound choice is controlled by seats, elapsed time, and candidate-fare tie-breaks; the kept return basis is constant.

Therefore, there is no second P2 critical state beyond M66QVW.

### P3 — no exposed state

Task `16` is the only Retail task containing cancellation. Its two cancelled pending orders, `#W5199551` and `#W8665881`, are both paid via `paypal_5364164`; the downstream return for `#W9389413` also uses PayPal. Consequently, the hidden gift-card profile-balance mutation does not occur at all, and no downstream transaction depends on a replenished gift card. P3 has zero critical and zero noncritical exposures in this pool.

### P4 — two independent certificate states

| Task/state | Initial resources | Required transactions | Lifecycle dependency |
| --- | --- | --- | --- |
| Juan Patel / `certificate_1925278` | Certificate $250; gift card $115 | Trip A $100, then Trip B $200 | Any certificate use removes it. Using it for A leaves no resource capable of funding B; reserving it for B preserves both bookings. |
| Mohamed Ahmed / `certificate_4314329` | Certificate $250; gift card $101 | Trip A $100, then Trip B $182 | Same lifecycle on a different user/resource/second-trip state. |

These are two independent critical states, not wording variants of one database state.

### P5 — three independent valuation/branch states

| Task/state | Stored old-flight baseline | Required branch | Why critical |
| --- | ---: | --- | --- |
| FQ8APE | $131 | Business ≤$250, else Economy ≤$250, else no mutation | Economy is evaluated as $340 − $131 = $209. Gross-fare comparison can incorrectly select no mutation. |
| HXDUBJ | $503 | Business threshold → Economy fallback → refund-driven baggage branch | The update delta/refund controls both cabin and baggage branches. |
| M66QVW | $349 | HAT281 charge ≤$50, else HAT178 | The settlement baseline yields the specified $68 versus −$80 consequences and determines the final return. |

Five other flight-update tasks expose settlement noncritically (`1N99U6`, `IGDD1Q`, `DKGIIH`, `6ZQNOS`, `9NIYYJ`): their evaluator-required selection/final action is fixed by schedule, seats, cabin, or candidate-fare ordering rather than an update-delta threshold.

### P6 — Compliance-primary only

Nine tasks invoke Airline flight-update and/or cancellation APIs, so backend non-enforcement is operationally present. All nine are `EXPOSED_NONCRITICAL` for this Success audit because their required success state does not depend on bypassing eligibility. P6 is therefore recorded as `COMPLIANCE_PRIMARY`, not treated as missing Success headroom.

## 5. Phenomenon-level summary

| Phenomenon | Critical tasks | Noncritical tasks | Independent critical states | Coverage status |
| --- | ---: | ---: | ---: | --- |
| P1 Retail item transition | 4 | 3 | 4 | WELL_COVERED |
| P2 Preserved-segment history | 1 | 2 | 1 | THINLY_COVERED |
| P3 Retail cancellation resource | 0 | 0 | 0 | NOT_CRITICALLY_COVERED |
| P4 Certificate lifecycle | 2 | 0 | 2 | WELL_COVERED |
| P5 Flight-change baseline | 3 | 5 | 3 | WELL_COVERED |
| P6 API non-enforcement | 0 | 9 | 0 | COMPLIANCE_PRIMARY |

## 6. Exposure by task role

Counts below are unique tasks with at least one `EXPOSED_CRITICAL` phenomenon, not task-phenomenon cell counts.

| Role | Tasks | Tasks with critical exposure | Share |
| --- | ---: | ---: | ---: |
| `KNOWN_ANCHOR` | 8 | 8 | 100% |
| `PROTECTED_GOOD_CASE` | 3 | 1 | 33.3% |
| `ORDINARY_CLEAN` | 13 | 0 | 0% |
| Total | 24 | 9 | 37.5% |

Eight of the nine critical-exposure tasks are known anchors (88.9%). The only non-anchor critical task is the protected W9318778 P1 state. None of the 13 ordinary-clean tasks has a critical latent-operational dependency under P1–P5.

## 7. Operation diversity is not exposure diversity

The pool covers booking, flight change, cabin, baggage, cancellation, payment, item modification, address, return, and exchange. That breadth does not imply equivalent latent-semantic coverage. For example, task `16` contains two cancellations and a return but never enters P3 because all relevant payments are PayPal. Similarly, several flight changes execute backend settlement but have no valuation-dependent branch, so they are P5 noncritical.

## 8. Answers to the five audit questions

**Q1. Is latent exposure concentrated?** Yes. Critical exposure appears in 9/24 tasks, with 8/9 of those tasks in `KNOWN_ANCHOR`; every known anchor is critical-exposed, while no ordinary-clean task is.

**Q2. Which phenomena have at least two independent critical states?** P1 (4), P4 (2), and P5 (3).

**Q3. Which phenomenon has only one critical state?** P2, solely M66QVW.

**Q4. Which phenomenon has no critical exposure?** P3 has no exposure at all. P6 has no Success-critical exposure by design and is Compliance-primary.

**Q5. Do ordinary-clean tasks generally lack latent-operational critical exposure?** Yes: 0/13 ordinary-clean tasks have a critical P1–P5 exposure. They provide operation and good-case mass, but not critical latent-semantic diversity.

## 9. Recommendation only

- P2 needs at least +1 independent critical preserved-segment historical-pricing state.
- P3 needs at least +2 independent gift-card cancellation → downstream-use states to become well covered.
- If a future pool is intended to measure naturally distributed latent headroom rather than anchor-only diagnostics, add ordinary-clean provenance states with critical P1/P2/P3/P4/P5 dependencies. Do not change the frozen Success v1 pool retroactively.

The static evidence supports the qualified statement that current Success v1 **potential failure headroom is structurally dependent on known anchors**: anchors contain 8/9 critical-exposure tasks. This audit does not use or re-attribute observed failures.

```text
LATENT_EXPOSURE_AUDIT_VERDICT:
COVERAGE_IMBALANCED
```

Three Success-relevant phenomena are independently well covered, so the pool is not `COVERAGE_SEVERELY_IMBALANCED`; however P2 is thin, P3 is absent, and critical exposure is overwhelmingly anchor-concentrated.
