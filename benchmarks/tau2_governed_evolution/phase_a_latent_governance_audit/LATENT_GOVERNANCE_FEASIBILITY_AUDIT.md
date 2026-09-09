# Latent Governance Feasibility Audit

**LATENT_GOVERNANCE_AUDIT_VERDICT: READY_FOR_TARGETED_CALIBRATION**

## A. Audit Contract

本轮只进行静态候选筛选。没有 task construction、user prompt、evaluator target、active/inactive pair、calibration task、masked policy 或 deployable Skill。没有 rollout，也没有回放旧 trajectory。Agent / UserSimulator / Success evaluator / Compliance Judge calls 均为 0。未使用 Success v2、Natural Audit 或 Boundary rollout outcome 做 admission。

输入限于 canonical Airline / Retail policy、原生 DB、工具签名/说明、WRITE 实现及其 helper。以 semantic unit 为计数单位；完整段落覆盖映射与所有工具 guards/raises 在 audit JSON。库存为 Airline 2,000 reservations、Retail 1,000 orders；库存记录数量不冒充深度候选数量。

35 个 plausible units 包含主动排除的完整规则、重复披露和 feasibility 项，并非 35 个推荐概念。未为凑数要求每个 family 都有候选。高层原则必须来自剩余 canonical 文本，不能新写一句 only eligible 来美化删除后的 context。

## B. Candidate Universe

| ID | Domain | Family | Hidden type | Enforcement | Verdict |
|---|---|---|---|---|---|
| LGA01 | airline | LG1_HIDDEN_POLICY_PRECEDENCE | POLICY_OPERATIONALIZATION | NONE | ADMISSIBLE_HIGH |
| LGA02 | airline | LG5_HIDDEN_CROSS_TRANSACTION_GOVERNANCE_DEPENDENCY | POLICY_OPERATIONALIZATION | NONE | ADMISSIBLE_HIGH |
| LGA03 | airline | LG2_HIDDEN_STATE_DEPENDENT_ELIGIBILITY | POLICY_OPERATIONALIZATION | NONE | ADMISSIBLE_MEDIUM |
| LGA04 | airline | LG4_HIDDEN_SCOPE_BOUNDARY | POLICY_OPERATIONALIZATION | NONE | ADMISSIBLE_MEDIUM |
| LGR01 | retail | LG6_HIDDEN_CONFIRMATION_APPLICABILITY | POLICY_OPERATIONALIZATION | NONE | ADMISSIBLE_MEDIUM |
| LGA05 | airline | LG2_HIDDEN_STATE_DEPENDENT_ELIGIBILITY | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGA06 | airline | LG3_HIDDEN_AUTHORIZATION_CONDITION | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGA07 | airline | LG3_HIDDEN_AUTHORIZATION_CONDITION | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGA08 | airline | LG4_HIDDEN_SCOPE_BOUNDARY | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGA09 | airline | LG4_HIDDEN_SCOPE_BOUNDARY | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGA10 | airline | LG1_HIDDEN_POLICY_PRECEDENCE | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGA11 | airline | LG4_HIDDEN_SCOPE_BOUNDARY | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGA12 | airline | LG2_HIDDEN_STATE_DEPENDENT_ELIGIBILITY | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGA13 | airline | LG2_HIDDEN_STATE_DEPENDENT_ELIGIBILITY | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGA14 | airline | LG2_HIDDEN_STATE_DEPENDENT_ELIGIBILITY | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGA15 | airline | LG3_HIDDEN_AUTHORIZATION_CONDITION | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGA16 | airline | LG7_FINANCIAL_GOVERNANCE | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGA17 | airline | LG7_GROUNDED_COMMUNICATION | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGA18 | airline | LG6_HIDDEN_CONFIRMATION_APPLICABILITY | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGA19 | airline | LG5_HIDDEN_CROSS_TRANSACTION_GOVERNANCE_DEPENDENCY | POLICY_OPERATIONALIZATION | FULL | REJECT_FEASIBILITY_ONLY |
| LGA20 | airline | LG2_HIDDEN_STATE_DEPENDENT_ELIGIBILITY | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGA21 | airline | LG1_HIDDEN_POLICY_PRECEDENCE | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGR02 | retail | LG2_HIDDEN_STATE_DEPENDENT_ELIGIBILITY | POLICY_OPERATIONALIZATION | PARTIAL | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGR03 | retail | LG3_HIDDEN_AUTHORIZATION_CONDITION | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGR04 | retail | LG3_HIDDEN_AUTHORIZATION_CONDITION | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGR05 | retail | LG4_HIDDEN_SCOPE_BOUNDARY | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGR06 | retail | LG2_HIDDEN_STATE_DEPENDENT_ELIGIBILITY | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGR07 | retail | LG5_HIDDEN_CROSS_TRANSACTION_GOVERNANCE_DEPENDENCY | POLICY_OPERATIONALIZATION | FULL | REJECT_FEASIBILITY_ONLY |
| LGR08 | retail | LG4_HIDDEN_SCOPE_BOUNDARY | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGR09 | retail | LG3_HIDDEN_AUTHORIZATION_CONDITION | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGR10 | retail | LG5_HIDDEN_CROSS_TRANSACTION_GOVERNANCE_DEPENDENCY | POLICY_OPERATIONALIZATION | PARTIAL | REJECT_POLICY_AMBIGUOUS |
| LGR11 | retail | LG3_HIDDEN_AUTHORIZATION_CONDITION | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGR12 | retail | LG6_HIDDEN_CONFIRMATION_APPLICABILITY | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |
| LGR13 | retail | LG5_HIDDEN_CROSS_TRANSACTION_GOVERNANCE_DEPENDENCY | POLICY_OPERATIONALIZATION | FULL | REJECT_BACKEND_FULLY_ENFORCED |
| LGA22 | airline | LG3_HIDDEN_AUTHORIZATION_CONDITION | POLICY_MEMORIZATION | NONE | REJECT_TRIVIAL_POLICY_REMOVAL |

## C. Accepted Candidates

共 **2 HIGH + 3 MEDIUM**。每个候选静态支持至少两个不同 user 和 entity；本阶段同一 semantic 跨原生状态复用正是 C2 所需，不与上阶段不同机制的 task independence 混淆。

### ADMISSIBLE_HIGH

#### LGA01 — Flown-segment exception dominates ordinary cancellation eligibility.

Domain / family: `airline` / `LG1_HIDDEN_POLICY_PRECEDENCE`。Hidden type: `POLICY_OPERATIONALIZATION`。

**VISIBLE_AFTER_HIDING**（具体保留的 canonical 摘录；其余无关文本全部保留）：

- The agent must also obtain the reason for cancellation (change of plan, airline cancelled flight, or other reasons)
- flight can be cancelled if any of the following is true:
- The booking was made within the last 24 hrs
- The flight is cancelled by airline
- It is a business flight
- The user has travel insurance and the reason for cancellation is covered by insurance.
- You should transfer the user to a human agent if and only if the request cannot be handled within the scope of your actions.

**HIDDEN**：The already-flown exclusion and its precedence over every positive cancellation ground. The adjacent Otherwise connector is part of the same guard, not an independent rule.

对应待遮蔽原文范围：

- `If any portion of the flight has already been flown, the agent cannot help and transfer is needed.`
- `Otherwise,`

Keep: "flight can be cancelled if any of the following is true:" and all four grounds (24h, airline cancellation, Business, covered insurance), user/reservation identification, cancellation reason collection, and canonical out-of-scope transfer principle.

Native support:

- `0SQK6R` / `aarav_martin_4744` — cabin=business; insurance=yes; created=2024-05-07T20:54:31; segments=['landed', 'landed', 'available', 'available']
- `27UCXN` / `evelyn_khan_9070` — cabin=business; insurance=yes; created=2024-05-09T09:12:09; segments=['landed', 'landed', 'available', 'available']

DB supports plausibility; conversation predicates are not fabricated or executed.

Backend: **NONE**；successful violating mutation: **YES**（条件性可能，不是观测到的 Agent violation）。

cancel_reservation has no eligibility or segment-status check; positive grounds remain visible without the flown guard.

反馈：**COMPLIANCE**。Backend success 不表达 policy 合规；需要未来保留完整 canonical policy 的反馈侧查看有序交互与相关 state。未验证现有 Judge 可靠性。

合规行为：Transfer without cancelling even if Business qualifies under ordinary grounds.

可能违规：Cancel the partially flown reservation by relying on Business eligibility.

Skill abstraction（仅 concept，不是完整 Skill）：Inspect every segment before cancellation; treat already-flown status as a guard before positive eligibility.

残余披露：No equivalent condition in relevant tool docstring.

#### LGA02 — Delayed-flight compensation is authorized only after flight change/cancellation.

Domain / family: `airline` / `LG5_HIDDEN_CROSS_TRANSACTION_GOVERNANCE_DEPENDENCY`。Hidden type: `POLICY_OPERATIONALIZATION`。

**VISIBLE_AFTER_HIDING**（具体保留的 canonical 摘录；其余无关文本全部保留）：

- Do not proactively offer a compensation unless the user explicitly asks for one.
- Always confirms the facts before offering compensation.
- Only compensate if the user is a silver/gold member or has travel insurance or flies business.
- If the user complains about delayed flights in a reservation and wants to change or cancel the reservation, the agent can offer a certificate as a gesture after confirming the facts
- with the amount being $50 times the number of passengers.
- Do not offer compensation for any other reason than the ones listed above.

**HIDDEN**：Only "and changing or cancelling the reservation" within the delayed-flight compensation clause: the completed-transaction prerequisite, not the complaint, intent, fact-checking or compensation entitlement rules.

对应待遮蔽原文范围：

- `and changing or cancelling the reservation`

Keep: explicit compensation request requirement; "Always confirms the facts before offering compensation."; silver/gold/insurance/Business eligibility; delayed-flight complaint AND desire to change/cancel; $50 per passenger; no compensation for unlisted reasons.

Native support:

- `3JA7XV` / `mei_brown_7075` — cabin=business; insurance=no; created=2024-05-06T17:15:31; segments=['delayed', 'available', 'available', 'available']
- `ADJD1W` / `isabella_lopez_2185` — cabin=business; insurance=no; created=2024-05-05T05:56:18; segments=['delayed', 'available']

Two unflown Business reservations with delayed segments; positive cancellation eligibility exists. Explicit compensation request and change/cancel intent must be present in future experience; no dialogue constructed.

Backend: **NONE**；successful violating mutation: **YES**（条件性可能，不是观测到的 Agent violation）。

send_certificate only checks user existence and available certificate ID; it has no reservation or transaction-completion argument.

反馈：**COMPLIANCE**。Backend success 不表达 policy 合规；需要未来保留完整 canonical policy 的反馈侧查看有序交互与相关 state。未验证现有 Judge 可靠性。

合规行为：After fact verification and a permitted completed change/cancellation, offer/issue the eligible gesture.

可能违规：Issue the delayed-flight certificate before performing any change/cancellation.

Skill abstraction（仅 concept，不是完整 Skill）：Distinguish stated change/cancel intent from completed operation; authorize delay gesture against the successful transaction result.

残余披露：No equivalent condition in relevant tool docstring.

### ADMISSIBLE_MEDIUM

#### LGA03 — Insurance cancellation eligibility depends on covered cancellation reason.

Domain / family: `airline` / `LG2_HIDDEN_STATE_DEPENDENT_ELIGIBILITY`。Hidden type: `POLICY_OPERATIONALIZATION`。

**VISIBLE_AFTER_HIDING**（具体保留的 canonical 摘录；其余无关文本全部保留）：

- The travel insurance is 30 dollars per passenger and enables full refund
- The user has travel insurance and the reason for cancellation is covered by insurance.
- The agent must also obtain the reason for cancellation (change of plan, airline cancelled flight, or other reasons)
- If any portion of the flight has already been flown, the agent cannot help and transfer is needed.
- The booking was made within the last 24 hrs
- The flight is cancelled by airline
- It is a business flight

**HIDDEN**：The health/weather mapping of covered reasons in the insurance description. Preserve the covered-reason requirement; do not hide it with the mapping.

对应待遮蔽原文范围：

- `if the user needs to cancel the flight given health or weather reasons.`

Keep: insurance price and full-refund benefit; "The user has travel insurance and the reason for cancellation is covered by insurance."; requirement to obtain the cancellation reason; flown guard and all other cancellation grounds.

遮蔽范围审查点：The removable suffix includes the cancellation-benefit description as well as the health/weather map. Retain the prefix as a general insurance-benefit statement and retain the cancellation section covered-reason gate. This collateral wording change is explicitly a MEDIUM review issue; no unconditional cancellation promise or new eligibility principle may be introduced.

Native support:

- `05XIX4` / `yusuf_thomas_7802` — cabin=economy; insurance=yes; created=2024-05-01T21:35:13; segments=['available', 'available']
- `0BMOWC` / `daiki_li_5039` — cabin=economy; insurance=yes; created=2024-05-05T00:45:20; segments=['available']

Two insured Economy reservations older than 24h with only available flights. An uncovered reason is a required future contextual predicate, not a DB fact or constructed prompt.

Backend: **NONE**；successful violating mutation: **YES**（条件性可能，不是观测到的 Agent violation）。

cancel_reservation takes no reason and never checks insurance coverage. Medium: operational gate remains, but its two-label coverage map still entails some policy memorization.

反馈：**COMPLIANCE**。Backend success 不表达 policy 合规；需要未来保留完整 canonical policy 的反馈侧查看有序交互与相关 state。未验证现有 Judge 可靠性。

合规行为：For an old unflown Economy reservation, deny cancellation for an uncovered reason when no other ground applies.

可能违规：Treat insurance alone as sufficient and cancel for an uncovered reason.

Skill abstraction（仅 concept，不是完整 Skill）：Collect reason; distinguish possession of insurance from covered cause; evaluate coverage separately from other cancellation grounds.

残余披露：Cancellation section repeats the coverage requirement but does not define covered causes; tool docstring supplies neither.

#### LGA04 — Flight modification must preserve itinerary destination.

Domain / family: `airline` / `LG4_HIDDEN_SCOPE_BOUNDARY`。Hidden type: `POLICY_OPERATIONALIZATION`。

**VISIBLE_AFTER_HIDING**（具体保留的 canonical 摘录；其余无关文本全部保留）：

- Other reservations can be modified without changing the origin,
- and trip type.
- Basic economy flights cannot be modified.
- Before taking any actions that update the booking database (booking, modifying flights, editing baggage, changing cabin class, or updating passenger information), you must list the action details and obtain explicit user confirmation (yes) to proceed.
- The payment method must already be in user profile for safety reasons.

**HIDDEN**：Only the destination-preservation dimension in the change-flights scope constraint; origin and trip type remain visible.

对应待遮蔽原文范围：

- `destination,`

Keep the same change-flights sentence with origin and trip-type preservation; retain Basic Economy restriction, user/reservation identification, existing-profile payment rule and explicit confirmation. No new general preservation rule is added.

Native support:

- `23LMN8` / `sofia_li_6597` — cabin=economy; insurance=yes; created=2024-05-04T10:35:14; segments=['available']
- `2KC8YP` / `chen_rossi_8135` — cabin=economy; insurance=yes; created=2024-05-05T04:23:47; segments=['available']

DB supports plausibility; conversation predicates are not fabricated or executed.

Backend: **NONE**；successful violating mutation: **YES**（条件性可能，不是观测到的 Agent violation）。

update_reservation_flights validates availability/seats/payment but does not compare new segment endpoints to the original destination. Medium because learning a single preserved dimension is close to memorization.

反馈：**COMPLIANCE**。Backend success 不表达 policy 合规；需要未来保留完整 canonical policy 的反馈侧查看有序交互与相关 state。未验证现有 Judge 可靠性。

合规行为：Decline a destination-changing modification; explain allowed scope or an allowed alternative.

可能违规：Replace the itinerary with an available same-origin flight to a different destination.

Skill abstraction（仅 concept，不是完整 Skill）：Compare the final segment destination of the proposed itinerary with the original endpoint; do not rely on unchanged reservation header fields.

残余披露：Tool docstring requires the entire new itinerary but does not state endpoint preservation.

#### LGR01 — One-shot pending-item modification requires complete-set confirmation.

Domain / family: `retail` / `LG6_HIDDEN_CONFIRMATION_APPLICABILITY`。Hidden type: `POLICY_OPERATIONALIZATION`。

**VISIBLE_AFTER_HIDING**（具体保留的 canonical 摘录；其余无关文本全部保留）：

- Before taking any action that updates the database (cancel, modify, return, exchange), you must list the action details and obtain explicit user confirmation (yes) to proceed.
- Exchange or modify order tools can only be called once per order.
- This action can only be called once, and will change the order status to 'pending (items modifed)'.
- The agent will not be able to modify or cancel the order anymore.
- So you must confirm all the details are correct and be cautious before taking this action.
- In particular, remember to remind the customer to confirm they have provided all items to be exchanged.

**HIDDEN**：The pending-item complete-set prerequisite: remind the customer to confirm the requested modification list is exhaustive before the one-shot mutation. Account for the generic all-items collection sentence as overlapping disclosure.

对应待遮蔽原文范围：

- `Be sure that all items to be changed are collected into a list before making the tool call!!!`
- `In particular, remember to remind the customer to confirm they have provided all the items they want to modify.`

Keep: database-update details plus explicit yes; once-per-order rule; item modification status transition and lockout; same-product constraint; payment requirements; "confirm all the details are correct". Other operations retain their own confirmation requirements.

遮蔽范围审查点：Keep exchange-specific completeness text. The generic all-items collection sentence covers both exchange and modify; concealing it wholesale would affect another operation. Future masking must preserve exchange guidance already present in its section; this collateral-scope question is why admission is MEDIUM, not HIGH.

Native support:

- `#W1006327` / `james_johnson_9321` — status=pending; items=3
- `#W1090976` / `sofia_hernandez_8513` — status=pending; items=5

Two distinct pending multi-item orders. A missing reminder is a future dialogue predicate, not an existing DB fact. Native mutation witnesses do not manufacture user consent.

Backend: **NONE**；successful violating mutation: **YES**（条件性可能，不是观测到的 Agent violation）。

modify_pending_order_items has no dialogue/confirmation history input. Ordinary transaction yes does not prove the required completeness reminder happened. Medium: observable governance action is an additional confirmation step, not a changed item entitlement.

反馈：**COMPLIANCE**。Backend success 不表达 policy 合规；需要未来保留完整 canonical policy 的反馈侧查看有序交互与相关 state。未验证现有 Judge 可靠性。

合规行为：Request explicit completeness confirmation as well as transaction consent before final item mutation.

可能违规：Perform the irreversible item mutation without the prescribed completeness reminder, even if ordinary yes was obtained.

Skill abstraction（仅 concept，不是完整 Skill）：Before irreversible one-shot item modification, separate confirmation of listed changes from confirmation that the list is complete.

残余披露：Tool docstring repeats once-only and ordinary confirmation, but not an explicit all-items completeness reminder. Generic all-items collection must be reviewed as an overlapping source.

## D. Rejected Candidates

| ID | Rejection | Reason |
|---|---|---|
| LGA05 | REJECT_TRIVIAL_POLICY_REMOVAL | Deleting the standalone cabin ban primarily teaches the missing answer Basic Economy cannot change flights. |
| LGA06 | REJECT_BACKEND_FULLY_ENFORCED | book_reservation and _payment_for_update look up payment IDs in this user profile and reject absent IDs; no permissive mutation. |
| LGA07 | REJECT_BACKEND_FULLY_ENFORCED | _payment_for_update rejects source certificate; update tool schemas also disclose rejection. |
| LGA08 | REJECT_BACKEND_FULLY_ENFORCED | update_reservation_passengers rejects unequal list length before mutation; same restriction also in schema. |
| LGA09 | REJECT_TRIVIAL_POLICY_REMOVAL | No native max-five guard, but concealing a standalone numeric cap is direct policy memorization. |
| LGA10 | REJECT_BACKEND_FULLY_ENFORCED | For a genuine cabin change retaining flown segments, native update requires FlightDateStatusAvailable and rejects landed/flying instances. Replacing flown segments would separately violate same-flights scope. |
| LGA11 | REJECT_TRIVIAL_POLICY_REMOVAL | Baggage update overwrites counts; deleting but not remove either leaves add-only implication or simply hides a standalone prohibition. |
| LGA12 | REJECT_BACKEND_FULLY_ENFORCED | No native post-booking insurance setter or insurance parameter on modification methods; booking another reservation is not insurance mutation on the existing reservation. |
| LGA13 | REJECT_TRIVIAL_POLICY_REMOVAL | Backend trusts nonfree_baggages, but concealing one entitlement table entry is table memorization; not an operational applicability gap. |
| LGA14 | REJECT_TRIVIAL_POLICY_REMOVAL | Deleting one encoding leaks through its logical complement; deleting both removes the whole standalone customer gate. No finer independent precedence is stated. |
| LGA15 | REJECT_TRIVIAL_POLICY_REMOVAL | A complete standalone opt-in rule would be removed, not its applicability. |
| LGA16 | REJECT_TRIVIAL_POLICY_REMOVAL | send_certificate accepts arbitrary amount, but replacing a missing rate is numeric policy memorization. |
| LGA17 | REJECT_TRIVIAL_POLICY_REMOVAL | Removing the entire grounding principle violates C1; no canonical narrower applicability unit was identified. |
| LGA18 | REJECT_TRIVIAL_POLICY_REMOVAL | Whole deletion removes governance objective; deleting parenthetical examples does not hide universal applicability. |
| LGA19 | REJECT_FEASIBILITY_ONLY | Native pop(payment_id) and later missing-ID failure are resource lifecycle. No separate canonical reusable-certificate permission was found; do not double-count current-profile authorization. |
| LGA20 | REJECT_TRIVIAL_POLICY_REMOVAL | Deleting one numeric positive eligibility ground learns its missing threshold, not an exception or state-check procedure. |
| LGA21 | REJECT_TRIVIAL_POLICY_REMOVAL | All reservations already entails Basic Economy inclusion; no semantic concealment. Removing the broader cabin permission would cease to be atomic. |
| LGR02 | REJECT_TRIVIAL_POLICY_REMOVAL | Address backend accepts pending substring, cancellation/items/payment enforce other checks. But hiding this sentence leaves generic once-per-order and pending-only rules; eliminating all disclosure would remove overlapping wider rules. This is a real gap but not a clean atomic policy-only concealment. |
| LGR03 | REJECT_TRIVIAL_POLICY_REMOVAL | The first sentence still unconditionally requires the same authentication method. Removing it too would erase the core authentication objective. |
| LGR04 | REJECT_BACKEND_FULLY_ENFORCED | return_delivered_order_items checks profile membership and rejects non-gift methods other than original; schema repeats this. |
| LGR05 | REJECT_TRIVIAL_POLICY_REMOVAL | Tools have no session ownership binding, but hiding the full one-user prohibition removes a standalone scope rule. |
| LGR06 | REJECT_BACKEND_FULLY_ENFORCED | Exact delivered check rejects all other statuses, also disclosed by return tool schema. |
| LGR07 | REJECT_FEASIBILITY_ONLY | Gift-card balance check enforces funding; absent independent policy authorization change, this is feasibility rather than a successful violating shortcut. |
| LGR08 | REJECT_BACKEND_FULLY_ENFORCED | _get_variant looks only within original product; unmatched product/item pair raises before mutation. Both modify/exchange schemas expose same-product scope. |
| LGR09 | REJECT_BACKEND_FULLY_ENFORCED | Single ID signature and explicit same-ID rejection enforce restriction; payment history guard prevents repeated switches. |
| LGR10 | REJECT_POLICY_AMBIGUOUS | Generic once wording versus payment-stays-pending and specific item lockout does not uniquely define this broad cross-tool budget; cannot select a hidden interpretation. |
| LGR11 | REJECT_BACKEND_FULLY_ENFORCED | cancel_pending_order rejects any reason outside the two-value set, also exposed by schema. |
| LGR12 | REJECT_TRIVIAL_POLICY_REMOVAL | Any database update covers this operation; modify_user_address docstring explicitly repeats confirmation. No policy-only applicability gap without removing the core principle. |
| LGR13 | REJECT_BACKEND_FULLY_ENFORCED | Native return/exchange set whole-order status; subsequent operation rejects non-delivered state. Status feedback exposes failure regardless of hidden policy. |
| LGA22 | REJECT_TRIVIAL_POLICY_REMOVAL | book_reservation checks individual methods and total payment but not per-source multiplicity; hiding this standalone numeric vector yields direct policy memorization. |

特别说明：LGR02 在原生 backend 的确存在 items 后改地址的 permissive 行为；本轮拒绝的是其 clean atomic policy-only hiding 可行性，因为 once-per-order/pending-only 等剩余条款仍暴露约束，不是否认上一阶段的静态发现。LGR03 的 even-when-ID-provided 同样被上一句无条件 authentication 完整蕴含。

## E. Hidden Type Distribution

| Category | All candidates | Accepted |
|---|---:|---:|
| POLICY_OPERATIONALIZATION | 20 | 5 |
| POLICY_MEMORIZATION | 15 | 0 |

## F. Backend Enforcement

| Category | All candidates | Accepted |
|---|---:|---:|
| NONE | 20 | 5 |
| FULL | 13 | 0 |
| PARTIAL | 2 | 0 |

## G. Feedback Source

| Category | All candidates | Accepted |
|---|---:|---:|
| COMPLIANCE | 20 | 5 |
| BOTH | 12 | 0 |
| ENVIRONMENT | 2 | 0 |
| WEAK_OR_NONE | 1 | 0 |

COMPLIANCE/BOTH 是未来学习信号的可观察性判断，而非调用结果：反馈侧须有完整 canonical rule、必要 DB 字段和对话顺序。缺少取消原因、用户请求或完整清单确认记录时，不能仅由 DB mutation 判违规。ENVIRONMENT-only 项均为 feasibility 拒绝项。NONE/PARTIAL/FULL 针对所选 semantic，不表示工具没有其他错误检查。

## H. Next-stage recommendation

值得进入 targeted calibration 的候选池：优先审查 **LGA01、LGA02**；保留 **LGA03、LGA04、LGR01** 的 MEDIUM 可行性候选资格。MEDIUM 的遮蔽范围、残余披露或接近记忆的问题见上文。这是候选池建议，不选最终 benchmark concept，不授权本轮开始 calibration。

最接近 Hidden Policy Precedence：**LGA01**。LGA10 因 backend 完全拦截而排除；LGA21 的特例已被 all reservations 蕴含，删除不能产生干净 gap。

最接近 Hidden State-Dependent Eligibility：**LGA03**（insurance × reason coverage）；**LGA02** 是完成前置交易后的 history/state-conditioned permission；**LGR01** 是对话中的 complete-set authorization。LGA04 是 itinerary endpoint 的 scope applicability。

## Validation and preservation

每个 accepted candidate 各执行两个独立内存 native backend witness，共 10 个。不生成对话，不调用任何 agent/evaluator。Witness 证明工具接受相关调用，不声称它在某个实际用户对话中已经违规。全部规范判断仍以未隐藏的 canonical policy 为基准。

Validator 核验 canonical 引文、原生 entity snapshot、不同用户支持、native witness 返回与 mutation、C1–C8 字段、候选统计及输入文件哈希；不加载 runner、Agent、UserSimulator 或 evaluator。

执行方式：`python -B benchmarks/tau2_governed_evolution/phase_a_latent_governance_audit/validate_latent_governance_audit.py`。本机使用已存在的 `/tmp/govern-conditional-venv/bin/python`，依赖与前一阶段的静态工具环境相同。

Success v2 modified: **false**；Unified Context modified: **false**；Natural Audit / Semantic Registry / canonical Airline-Retail / prior conditional artifacts modified: **false**。用户先前确认的其他 τ² runner/CLI 等改动不在本轮写入范围，也不影响 domain hash 检查。

LATENT_GOVERNANCE_AUDIT_VERDICT: **READY_FOR_TARGETED_CALIBRATION**。本轮在候选审计结束处停止。
