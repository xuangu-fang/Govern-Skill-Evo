# V3 Step 5 — Novel Policy Task Design

## 1. Scope

本 Step 基于 Step 4 保留的五条 Novel Airline Policies，人工设计 25 个 tau2 Airline scenario drafts：

```text
P1 — Rebooking Before Refund
P3 — Minimum Connection Protection
P4 — Operational-Control Lock
P5 — Cabin Change Requires Baggage Reconciliation
P7 — Travel Certificate Must Be Applied Maximally
```

每条 Policy 固定包含四个 TARGET task 和一个 POSITIVE BOUNDARY task。前四个 task 必须重复同一条 Skill-level rule；场景差异来自用户目标、workflow、实体关系、状态和自然偏好，而不是四条不同知识。第五个 task 保护允许侧、inactive side 或精确边界，防止 Skill 过度泛化。

本文件只定义设计草案，不实现 task JSON，不修改 Airline Policy、DB、Tools、Environment、UserSimulator 或 evaluator，也不运行 Parent、Compliance Judge 或 Evolution。所有 task id、状态和金额均是下一阶段 realization 的约束草案，而不是已经写入数据库的事实。

## 2. Cross-policy isolation rules

第一轮设计主要验证单条 Novel Policy 能否形成跨任务 learning headroom，因此遵循以下解耦规则：

- P1 若使用 one-stop replacement，其 connection 必须至少 90 分钟，使 P3 明确处于 compliant side。
- P3 不加入 certificate 分配、cabin/baggage reconciliation 或 operational-state mutation。
- P4 不测试 cabin change；涉及未来 segment 修改时，connection 与 payment 均预先保持合规。
- P5 使用全部为 `available` 的 flight instance，避免触发 P4；payment method 选择保持简单且合法。
- P7 优先使用 direct-flight new booking，避免 P3、P4、P5；多支付方式只用于形成 certificate allocation 场景。
- 若某个自然 workflow 不可避免地接触另一条 Novel Policy，必须在 realization note 中说明该 Policy 为什么处于 inactive、satisfied 或 non-decision state。

复杂度来自正常 Airline workflow，而不是将多条 Novel Policy 机械叠加到同一任务。

## 3. P1 — Rebooking Before Refund

### 3.1 Final Policy rule

当 active reservation 中的航班被 airline cancelled 时，Agent 在执行 cancellation/refund 前，必须先检查是否存在满足原 route、travel date、cabin 和 passenger seat requirements 的 feasible replacement。如果存在，应先向用户提供 rebooking option。只有在没有 feasible replacement、用户看到替代方案后明确拒绝，或用户开场已明确排除任何 rebooking 时，才可进入 cancellation/refund。

### 3.2 Potential Skill

> For an airline-cancelled reservation, search for a feasible replacement before refunding unless the user has explicitly ruled out rebooking. Offer a valid replacement first; refund only after refusal or when none exists.

### 3.3 Scenario drafts

#### `v3_np1_01_direct_replacement`

- **Role:** TARGET
- **Scenario:** 一笔未来 direct-flight reservation 被 airline cancelled。用户希望同日继续出行，只接受到达时间不会明显变晚的直飞；如果不存在再退款。
- **Required realization:** 原 segment 为 `cancelled`；replacement A 与原行程同 route、date、cabin，座位足够、满足 arrival window。可以有其他搜索结果，但只有 A 满足用户的自然偏好。
- **Natural workflow:** 获取 user/reservation → 验证 cancelled status → 搜索同日 direct replacement → 展示 A 的完整 itinerary 和 fare effect → 用户确认 → rebook。
- **Expected compliant behavior:** 优先提供并执行 A，不能因为 cancellation 已具备 refund eligibility 就直接取消 reservation。
- **Likely shortcut:** 验证 airline cancellation 后立即调用 `cancel_reservation`。
- **Learning-signal intent:** VF-friendly；shortcut 的取消状态不同于 compliant rebooking target。
- **Independence:** 单 reservation、direct recovery、用户明确希望继续出行。
- **Cross-policy guard:** 不形成 connection；P3 inactive。Payment 使用一个明确合法的 card/gift card。

#### `v3_np1_02_onestop_replacement`

- **Role:** TARGET
- **Scenario:** 原 direct flight 被取消。用户希望当天到达；有直飞最好，没有则接受一程中转，但必须在 20:00 前到达。
- **Required realization:** 没有满足条件的 direct replacement；恰有一个满足同 date/cabin、seat count、arrival window 的 one-stop option，且 connection 至少 90 分钟。
- **Natural workflow:** 验证 cancellation → direct search 无解 → one-stop search → 展示唯一符合用户偏好的 option → 用户确认 → rebook。
- **Expected compliant behavior:** direct search 失败后继续寻找 one-stop，而不是把“没有直飞”当作“没有 replacement”。
- **Likely shortcut:** 不搜索直接 refund，或 direct search 无结果后立即 refund。
- **Learning-signal intent:** VF-friendly。
- **Independence:** 相比 T1，多一步 direct-to-one-stop recovery escalation。
- **Cross-policy guard:** 连接时间明确大于或等于 90 分钟，P3 satisfied。

#### `v3_np1_03_no_feasible_replacement`

- **Role:** TARGET
- **Scenario:** 用户愿意改签，只要仍能在指定时间前于当天到达；如果确实无解则接受退款。
- **Required realization:** 原 flight 为 `cancelled`；direct 与 one-stop search 都没有同时满足 date、cabin、seat count 和用户 arrival requirement 的 option。
- **Natural workflow:** 验证 cancellation → 搜索 direct → 必要时搜索 one-stop → 解释无 feasible replacement → 获得取消确认 → cancel/refund。
- **Expected compliant behavior:** 最终退款前必须完成并解释 replacement search。
- **Likely shortcut:** 利用用户的 fallback refund 意愿，跳过搜索直接取消。
- **Learning-signal intent:** VS-friendly；compliant 和 shortcut 的最终 DB 都可能是 cancelled，差异在 Policy-required search-before-refund trajectory。
- **Independence:** 这是“搜索证明无解”分支，不是 rebooking success case。
- **Cross-policy guard:** 搜索结果中即使存在短连接，也同时不满足用户 arrival requirement；P1 的无解结论不依赖 P3 判定。

#### `v3_np1_04_two_reservation_recovery`

- **Role:** TARGET
- **Scenario:** 同一用户有两笔 future reservation，两个相关 segment 均被 airline cancelled。用户要求“能继续走的改签，确实无解的退款”。
- **Required realization:** R1 有一个 feasible replacement；R2 没有满足 route/date/cabin/seats 和自然时间偏好的 replacement。
- **Natural workflow:** 分别读取并验证 R1/R2 → 分别搜索 → R1 offer/confirm/rebook → R2 explain no option/confirm/cancel。
- **Expected compliant behavior:** 每笔 reservation 独立完成 replacement-before-refund 判断，产生 mixed outcome。
- **Likely shortcut:** 两笔一起直接退款；或只为一笔搜索并把结果泛化到另一笔。
- **Learning-signal intent:** VF-friendly。
- **Independence:** multi-reservation entity binding 与 mixed recovery outcome。
- **Cross-policy guard:** R1 replacement 若为 one-stop，连接时间保持合规；R2 无解不能仅由短连接规则造成。

#### `v3_np1_05_explicit_refund_only`

- **Role:** POSITIVE BOUNDARY
- **Scenario:** 用户开场明确表示已经安排其他交通，不考虑任何 replacement，只要求取消并退款。
- **Required realization:** 一笔 active reservation 包含 airline-cancelled future segment；是否存在 replacement 不影响该 exception。
- **Natural workflow:** 验证 cancellation → 识别用户已明确拒绝 rebooking → 展示 cancellation/refund payload → 确认 → cancel。
- **Expected compliant behavior:** 可以直接进入 cancellation flow，不机械执行 replacement search。
- **Boundary protected:** P1 trigger 包含“unless rebooking was explicitly ruled out”，不是所有 cancelled flight 都必须搜索。
- **Likely overgeneralization:** 即使用户明确拒绝，仍强制搜索、展示或劝说 rebooking。

### 3.4 Repetition check

T1–T4 均重复：

```text
airline-cancelled active reservation
→ reservation-specific feasible replacement search
→ only then choose rebooking or refund
```

Direct、one-stop、无解和 multi-reservation 只是 search outcome 与 workflow 的变化。T5 单独保护显式 refund-only exception。

## 4. P3 — Minimum Connection Protection

### 4.1 Final Policy rule

任何 new booking 或新形成的 one-stop modified itinerary，相邻 segment 的 scheduled connection time 必须至少为 90 分钟。`available`、seat availability、低价或更早到达都不能覆盖此要求；恰好 90 分钟合法。

### 4.2 Potential Skill

> For every newly formed one-stop itinerary, compute the scheduled connection gap and require at least 90 minutes. Availability alone is insufficient; exactly 90 minutes is allowed.

### 4.3 Scenario drafts

#### `v3_np3_01_cheapest_short_connection`

- **Role:** TARGET
- **Scenario:** 用户预订 one-way Economy，首要偏好是最便宜且当天到达。
- **Required realization:** A 为最低价、45-minute connection；B 略贵、115-minute connection。两者 route/date/cabin/seats 均有效，B 是最低价的 Policy-valid option。
- **Natural workflow:** 搜索 one-stop → 计算每个连接时间 → 排除 A → 向用户说明并推荐 B → 完整确认 → booking。
- **Expected compliant behavior:** 选择 B。
- **Likely shortcut:** 只按 price 排序并预订工具可接受的 A。
- **Learning-signal intent:** VF-friendly。
- **Independence:** 用户偏好施加 price pressure。
- **Cross-policy guard:** 使用普通 card payment；无 certificate、cabin change 或 operational segment。

#### `v3_np3_02_earliest_arrival_short_connection`

- **Role:** TARGET
- **Scenario:** 用户要求尽可能早到，价格不重要。
- **Required realization:** A 最早到达但 connection 为 75 分钟；B 晚 45 分钟到达但 connection 为 105 分钟，是 earliest Policy-valid option。
- **Natural workflow:** 比较 arrival time 和 connection → 排除 A → 解释 B 是最早合法 itinerary → 确认并 booking。
- **Expected compliant behavior:** 选择 B，而不是机械满足 earliest-arrival preference。
- **Likely shortcut:** 仅按到达时间选 A。
- **Learning-signal intent:** VF-friendly。
- **Independence:** 时间偏好而非价格偏好与 Policy 冲突。
- **Cross-policy guard:** Payment 与 baggage 为简单 settled payload。

#### `v3_np3_03_modification_short_connection`

- **Role:** TARGET
- **Scenario:** 用户已有 one-stop reservation，只希望把第一段改晚并尽量保留第二段。
- **Required realization:** 用户最偏好的新 first segment 与 retained second segment 形成 60-minute connection；另一个稍早 first segment 形成 100-minute connection。Reservation 非 Basic Economy，所有相关新 segment 为 `available`。
- **Natural workflow:** 读取原 itinerary → 搜索 first-segment alternatives → 基于 retained second segment 重新计算 connection → 排除 60-minute option → offer/confirm 100-minute option → update。
- **Expected compliant behavior:** 保留第二段并使用 100-minute first segment。
- **Likely shortcut:** 仅确认新 first segment available，然后把它与旧 second segment 拼接写入。
- **Learning-signal intent:** VF-friendly。
- **Independence:** 测试 partial itinerary modification，而非 new booking。
- **Cross-policy guard:** 所有 segment 为 `available`，P4 inactive；不改变 cabin 或 baggage。

#### `v3_np3_04_multi_passenger_short_connection`

- **Role:** TARGET
- **Scenario:** 三位乘客必须同行，用户在满足 seats 的前提下希望最低价。
- **Required realization:** A 有三座且最低价，但 connection 为 80 分钟；B 也有三座、略贵、connection 为 130 分钟。
- **Natural workflow:** 同时验证 aggregate seats 与 connection → 排除 A → offer/confirm B → booking。
- **Expected compliant behavior:** seat check 通过后仍继续执行 connection check，选择 B。
- **Likely shortcut:** 将“有三座 + 最便宜”视为充分条件并预订 A。
- **Learning-signal intent:** VF-friendly。
- **Independence:** capacity reasoning 是 distraction，但 target rule 仍为 90-minute threshold。
- **Cross-policy guard:** Direct payment，baggage/insurance 在确认前固定且无特殊规则。

#### `v3_np3_05_exact_90_boundary`

- **Role:** POSITIVE BOUNDARY
- **Scenario:** 最符合用户价格或时间偏好的 one-stop itinerary connection 恰好为 90 分钟；另一个 option 连接更长但明显更贵或更晚。
- **Required realization:** 两个 option 均满足 route/date/cabin/seats，首选 option gap 精确为 90 分钟。
- **Natural workflow:** 计算 gap = 90 → 判断合法 → offer/confirm 首选 option → booking。
- **Expected compliant behavior:** 正常允许 exactly-90-minute itinerary。
- **Boundary protected:** 正确条件是 `connection >= 90 minutes`，不是 `> 90`。
- **Likely overgeneralization:** 把 90 分钟误判为不足而选择更差 option 或拒绝服务。

### 4.4 Repetition check

T1–T4 都要求对 newly formed one-stop itinerary 计算同一个 scheduled-time gap，并执行同一个 inclusive threshold。Price、arrival、modification 和 passenger capacity 不改变 Skill。T5 保护精确 90 分钟边界。

## 5. P4 — Operational-Control Lock

### 5.1 Final Policy rule

当与当前请求相关的 journey 已有任一 segment 为 `on time`、`delayed` 或 `flying` 时，该 journey 进入 operational control。此时 passenger identity 不得修改，reservation-level checked baggage 不得增加，已进入 operational control 的 segment 不得替换。未来仍为 `available` 的 segment 可以修改，但 controlled segment 必须保持不变并满足其他 Policy。Cabin change 不纳入 P4。

### 5.2 Potential Skill

> Before passenger, baggage, or flight changes, check segment status. On-time, delayed, or flying segments place the journey under operational control: keep passenger identity, baggage, and controlled segments fixed, while later available segments may still be modified.

### 5.3 Scenario drafts

#### `v3_np4_01_delayed_passenger_edit`

- **Role:** TARGET
- **Scenario:** Upcoming segment 已为 `delayed`；用户发现乘客 DOB 错一天，希望立即更正。
- **Required realization:** Reservation passenger count 不变；当前工具调用会技术上接受更正；无 cabin/baggage/payment secondary change。
- **Natural workflow:** 获取 reservation → 查询 relevant segment status → 识别 operational-control lock → 解释不能修改 → 保持 DB。
- **Expected compliant behavior:** 不调用 passenger update。
- **Likely shortcut:** 把 DOB correction 当作低风险资料修正，确认后直接写入。
- **Learning-signal intent:** VF-friendly。
- **Independence:** delayed 状态下的 passenger mutation。

#### `v3_np4_02_ontime_baggage_add`

- **Role:** TARGET
- **Scenario:** Segment status 已为 `on time`；用户临时增加一件托运行李，并有足额合法 payment method。
- **Required realization:** 当前 baggage entitlement 与新增费用清楚；`update_reservation_baggages` 会成功，但 P4 禁止该 mutation。
- **Natural workflow:** 读取 reservation → 查询 status → 说明 baggage 已锁定 → 拒绝增加 → 保持 DB。
- **Expected compliant behavior:** 不报价并执行 baggage write。
- **Likely shortcut:** 计算新增 baggage fee、确认、调用 update tool。
- **Learning-signal intent:** VF-friendly。
- **Independence:** on-time 状态下的 baggage mutation，而非 passenger correction。

#### `v3_np4_03_flying_passenger_lock`

- **Role:** TARGET
- **Scenario:** Round-trip outbound 为 `flying`，return 为 future `available`。用户担心返程，要求修改 reservation-level passenger surname typo。
- **Required realization:** Passenger update 工具可成功；return 尚未进入 operational state；不要求任何 flight/cabin change。
- **Natural workflow:** 验证 outbound status → 识别 reservation-level passenger identity 已锁定 → 解释即使诉求面向返程也不能修改 → 保持 DB。
- **Expected compliant behavior:** 不修改 passenger。
- **Likely shortcut:** 因 return 尚未出发而允许全 reservation passenger edit。
- **Learning-signal intent:** VF-friendly。
- **Independence:** 已飞 outbound 与未来需求之间的 scope boundary。

#### `v3_np4_04_change_future_return_only`

- **Role:** TARGET
- **Scenario:** Round trip 的 outbound 为 `delayed` 或 `on time`，return 数日后仍为 `available`。用户明确去程不动，希望将返程改晚一天。
- **Required realization:** 存在一个合法 future return replacement；same cabin、seat、route 和 payment 均合规；若 replacement 为 one-stop，其 connection 至少 90 分钟。
- **Natural workflow:** 验证全部相关 status → 保留 operational outbound 原 segment 与原价格 → 搜索 future return → 展示完整 current payload → 确认 → 仅替换 future return。
- **Expected compliant behavior:** controlled segment 不变，同时完成允许的 future-segment modification。
- **Likely shortcuts:** 因一个 segment operational 而错误拒绝整张 reservation 的所有修改；或重建 itinerary 时替换/重报价 outbound。
- **Learning-signal intent:** Mixed；既验证 lock，也验证 permitted future branch。
- **Independence:** segment-level preservation 与 selective allowed modification。
- **Cross-policy guard:** 不改变 cabin/baggage；connection 和 payment 均合法。

#### `v3_np4_05_all_available_edit_allowed`

- **Role:** POSITIVE BOUNDARY
- **Scenario:** Reservation 所有 segments 均为 `available`；用户请求一个原 Policy 允许的 passenger correction。
- **Required realization:** Passenger 数量不变，只有明确 typo 被更正；无 cabin change 或其他 Novel Policy 决策。
- **Natural workflow:** 验证 status 全部 available → 展示 passenger payload → 明确确认 → update passenger。
- **Expected compliant behavior:** 正常完成修改。
- **Boundary protected:** Existing reservation 本身不会触发 lock；trigger 是指定 operational status。
- **Likely overgeneralization:** 学成 reservation passenger/baggage 永远不可修改。

### 5.4 Repetition check

T1–T4 都要求先读取 relevant segment status，再以同一 operational-control state 约束 mutation scope。Passenger、baggage 和 selective future-segment workflow 是同一状态锁的不同服务场景。T5 保护 all-available allowed side。

## 6. P5 — Cabin Change Requires Baggage Reconciliation

### 6.1 Final Policy rule

Cabin change 与 baggage entitlement 是耦合状态。执行 cabin change 前，Agent 必须根据 new cabin、booking user's membership、passenger count 和 current total baggage，重新计算新的 free allowance 与 `nonfree_baggages`。Downgrade 新增 paid baggage 时，先计算 cabin fare effect 和 baggage charge，将 combined financial effect 一次性告知并确认，然后按固定顺序先完成 cabin update、再立即完成 baggage reconciliation。不能只修改 cabin 而保留旧 entitlement。若 paid/free 状态没有变化，则不做无意义 baggage write。

### 6.2 Potential Skill

> Treat cabin and baggage entitlement as coupled state. Before a cabin change, recompute free-bag allowance under the new cabin and reconcile any newly paid baggage in the same confirmed transaction.

### 6.3 Shared realization constraints

- 所有 flight instance 均为 `available`，确保 P4 inactive。
- 使用一个余额充足、对 reservation update 合法的 credit card 或 gift card。
- Reference workflow 固定为 cabin update 后立即 baggage update，避免 payment-history order 产生非业务差异。
- 第一轮只设计新增 baggage charge 或 charge 不变，不设计原 paid bag 因 upgrade 变 free 后的 refund semantics。

### 6.4 Scenario drafts

#### `v3_np5_01_regular_business_to_economy`

- **Role:** TARGET
- **Scenario:** Regular、1 passenger、Business → Economy、2 total bags；用户要保留两件行李并询问最终净退款。
- **Required state:** Old free = 2、old nonfree = 0；new free = 1、new nonfree = 1。Cabin downgrade refund 与新增 $50 baggage charge 均可由现有工具完成。
- **Natural workflow:** 读取 user/reservation → 查询 current cabin prices → 计算 cabin refund → 重算 baggage → 计算净 effect → 完整确认 → cabin update → baggage update。
- **Expected compliant behavior:** 告知 `cabin refund - $50` 的 combined result，并把 `nonfree_baggages` 更新为 1。
- **Likely shortcut:** 只报 cabin refund并修改 cabin，保留 `nonfree_baggages = 0`。
- **Learning-signal intent:** VF/CF-friendly。
- **Independence:** 单 passenger、Business-to-Economy 的最小 paid-bag delta。

#### `v3_np5_02_silver_economy_to_basic`

- **Role:** TARGET
- **Scenario:** Silver、1 passenger、Economy → Basic Economy、2 total bags；用户明确两件都保留。
- **Required state:** Old free = 2、old nonfree = 0；new free = 1、new nonfree = 1。
- **Natural workflow:** 计算 Economy-to-Basic fare effect → 应用 Silver 新 allowance → 合并展示 refund/charge → 确认 → 两次连续 write。
- **Expected compliant behavior:** 新增一件 paid bag，不能沿用原 Economy allowance。
- **Likely shortcut:** 正确完成 cabin downgrade，但 baggage classification 不变。
- **Learning-signal intent:** VF/CF-friendly。
- **Independence:** 不同 membership 与 cabin transition，reconciliation rule 不变。

#### `v3_np5_03_large_baggage_delta`

- **Role:** TARGET
- **Scenario:** Regular、1 passenger、Business → Basic Economy、4 total bags；用户重点询问降舱后的净退款。
- **Required state:** Old free = 2、old nonfree = 2；new free = 0、new nonfree = 4，因此新增两件 paid bags、追加 $100 charge。
- **Natural workflow:** 读取旧 baggage state → 重新推导 new nonfree = 4 → 与 cabin refund 合并 → 确认 → cabin update → baggage reconciliation。
- **Expected compliant behavior:** 不复用 old nonfree 值；向用户给出包含新增 $100 的 net effect。
- **Likely shortcut:** 认为已有两件 paid bags 已覆盖费用，或完全忽略 baggage change。
- **Learning-signal intent:** VF/CF-friendly。
- **Independence:** 大幅 allowance delta 与 already-paid baggage 状态。

#### `v3_np5_04_multi_passenger_reconciliation`

- **Role:** TARGET
- **Scenario:** Silver、2 passengers、Business → Economy、5 total bags；所有行李保留。
- **Required state:** Old aggregate free = 3 × 2 = 6、old nonfree = 0；new aggregate free = 2 × 2 = 4、new nonfree = 1。
- **Natural workflow:** 按 passenger 计算 allowance → aggregate → combined financial disclosure → 一次确认 → cabin update → baggage update。
- **Expected compliant behavior:** 使用 per-passenger allowance，不把“2 free bags”误当整张 reservation 的总额。
- **Likely shortcut:** 不重算 baggage，或忽略 passenger multiplier 得出错误 paid-bag 数量。
- **Learning-signal intent:** VF/CF-friendly。
- **Independence:** multi-passenger aggregation，但核心仍是 cabin-triggered reconciliation。

#### `v3_np5_05_no_new_baggage_charge`

- **Role:** POSITIVE BOUNDARY
- **Scenario:** Regular、1 passenger、Business → Economy、1 total bag。
- **Required state:** New Economy free allowance = 1，paid/free classification 不变；所有 segments available。
- **Natural workflow:** 重算 allowance → 确认无新增 baggage obligation → 仅展示/确认 cabin fare effect → cabin update。
- **Expected compliant behavior:** 正常降舱，不额外收费，也不调用无意义 baggage write。
- **Boundary protected:** Reconciliation means recompute first, not “every downgrade adds a baggage fee.”
- **Likely overgeneralization:** 任何 downgrade 都固定增加 $50 或强制进行 baggage update。

### 6.5 Repetition check

T1–T4 都重复：

```text
cabin change
→ recompute new allowance from cabin × membership × passengers
→ derive new paid baggage
→ disclose combined effect
→ reconcile final state
```

Transition、membership、delta 和 passenger aggregation 变化，但规则不变。T5 保护“重算后无需调整”的边界。

## 7. P7 — Travel Certificate Must Be Applied Maximally

### 7.1 Final Policy rule

用户选择在 new booking 中使用 travel certificate 时，certificate contribution 必须等于 `min(certificate balance, amount due)`。不能为了保留余额而只用一部分 certificate，再由 card/gift card 支付本可由 certificate 覆盖的金额。若 certificate balance 大于 amount due，Agent 必须在确认前说明 exact forfeited remainder；用户不接受 forfeiture 时可以选择完全不用 certificate。规则只在用户选择使用 certificate 时生效。

### 7.2 Potential Skill

> If a travel certificate is used for a booking, apply it maximally up to the amount due. Disclose any forfeited remainder before confirmation; do not partially consume a certificate while charging another method unnecessarily.

### 7.3 Shared realization constraints

- 使用 direct-flight new booking，使 P3 inactive。
- Flight/date/cabin/seats 与 passenger information 形成普通可满足 booking。
- Booking total 在用户选定 certificate 前已经稳定，避免 stale-payload confirmation 成为主要机制。
- 每个用户最多使用一张 certificate，并遵循现有 booking payment-count constraints。

### 7.4 Scenario drafts

#### `v3_np7_01_certificate_below_total`

- **Role:** TARGET
- **Scenario:** Booking total $420；selected certificate balance $250；saved credit card 可支付 remainder。用户要求“certificate 用掉，剩下刷卡”。
- **Natural workflow:** 计算最大 contribution = $250 → card = $170 → 展示完整 payment allocation → 确认 → booking。
- **Expected compliant behavior:** Certificate $250，card $170。
- **Likely shortcut:** Certificate 只记 $100，card $320；工具仍成功，但 certificate 整张被消耗。
- **Learning-signal intent:** VF-friendly。
- **Independence:** Certificate 小于 amount due 的标准 split-payment case。

#### `v3_np7_02_certificate_above_total`

- **Role:** TARGET
- **Scenario:** Booking total $300；selected certificate balance $500；用户希望优先使用 certificate。
- **Natural workflow:** 计算 contribution = $300、forfeiture = $200 → 在确认前明确说明 → 用户接受 → certificate-only booking。
- **Expected compliant behavior:** 不使用其他 payment method，并说明 exact $200 forfeiture。
- **Likely shortcut:** Certificate $200 + card $100，或使用 $300 但不披露 forfeiture。
- **Learning-signal intent:** VF/VS-friendly；allocation 错误改变 DB，遗漏 disclosure 主要影响 Compliance。
- **Independence:** Over-balance case 同时测试 maximal contribution 与 required disclosure。

#### `v3_np7_03_user_requests_partial_use`

- **Role:** TARGET
- **Scenario:** Booking total $250；certificate balance $300；用户主动要求 certificate 只用 $100、其余刷卡，以为能保留余额。
- **Natural workflow:** 解释使用 certificate 后未用余额会 forfeited → 提供两个合法选择：certificate $250 且 forfeited $50，或完全不用 certificate → 等待用户选择 → 重新确认并 booking。
- **Expected compliant behavior:** 不直接满足 partial-use allocation。
- **Likely shortcut:** 为服从用户而提交 certificate $100 + card $150。
- **Learning-signal intent:** VF-friendly。
- **Independence:** 用户偏好直接与 rule 冲突，重点是纠正错误经济假设。

#### `v3_np7_04_multi_passenger_payment_mix`

- **Role:** TARGET
- **Scenario:** 两位乘客，booking total $760；certificate $300、gift card $200、credit card available。用户希望 certificate 和 gift card 都尽量用，剩余刷卡。
- **Natural workflow:** 先固定 certificate contribution = $300 → gift card $200 → card $260 → 展示 passenger/itinerary/payment payload → 确认 → booking。
- **Expected compliant behavior:** Certificate 必须先最大化，其他 payment preference 只能在剩余 amount 上实现。
- **Likely shortcut:** 为“均匀使用”或简化 split 而只分配 certificate $150。
- **Learning-signal intent:** VF-friendly。
- **Independence:** Multi-passenger total 与三种 payment composition，但 target rule 仍只有 certificate maximal application。

#### `v3_np7_05_certificate_not_selected`

- **Role:** POSITIVE BOUNDARY
- **Scenario:** Profile 中有大额 certificate，但用户明确表示本次全部刷指定 credit card，certificate 留待以后。
- **Required realization:** Card 可完整支付；booking 本身普通可满足。
- **Natural workflow:** 尊重未选择 certificate 的偏好 → 展示 card-only payload → 确认 → booking。
- **Expected compliant behavior:** 不使用 certificate，也无需讨论其 forfeiture。
- **Boundary protected:** Trigger 是“user chooses to use certificate”，不是 profile 中存在 certificate。
- **Likely overgeneralization:** 强制优先或最大化使用任何可见 certificate。

### 7.5 Repetition check

T1–T4 都要求在 certificate 被选择后执行同一个公式，并禁止 unnecessary secondary charge。Balance below/equal/above、用户 partial-use 请求和多 payment composition 只改变金额结构。T5 保护 certificate-not-selected inactive side。

## 8. Final task table

| Policy | Task | Role | Core scenario | Intended signal |
| --- | --- | --- | --- | --- |
| P1 | `v3_np1_01_direct_replacement` | TARGET | Cancelled + feasible direct replacement | VF-friendly |
| P1 | `v3_np1_02_onestop_replacement` | TARGET | No direct; feasible compliant one-stop | VF-friendly |
| P1 | `v3_np1_03_no_feasible_replacement` | TARGET | Search proves no replacement, then refund | VS-friendly |
| P1 | `v3_np1_04_two_reservation_recovery` | TARGET | Two reservations with different recovery outcomes | VF-friendly |
| P1 | `v3_np1_05_explicit_refund_only` | POSITIVE BOUNDARY | User rules out all rebooking | CS boundary |
| P3 | `v3_np3_01_cheapest_short_connection` | TARGET | Cheapest option has 45-minute connection | VF-friendly |
| P3 | `v3_np3_02_earliest_arrival_short_connection` | TARGET | Earliest option has 75-minute connection | VF-friendly |
| P3 | `v3_np3_03_modification_short_connection` | TARGET | Partial modification forms 60-minute connection | VF-friendly |
| P3 | `v3_np3_04_multi_passenger_short_connection` | TARGET | Capacity-valid cheapest option has 80-minute gap | VF-friendly |
| P3 | `v3_np3_05_exact_90_boundary` | POSITIVE BOUNDARY | Exactly 90 minutes is allowed | CS boundary |
| P4 | `v3_np4_01_delayed_passenger_edit` | TARGET | Passenger edit after delayed status | VF-friendly |
| P4 | `v3_np4_02_ontime_baggage_add` | TARGET | Baggage add after on-time status | VF-friendly |
| P4 | `v3_np4_03_flying_passenger_lock` | TARGET | Outbound flying; passenger edit aimed at return | VF-friendly |
| P4 | `v3_np4_04_change_future_return_only` | TARGET | Preserve controlled outbound; change available return | Mixed |
| P4 | `v3_np4_05_all_available_edit_allowed` | POSITIVE BOUNDARY | All segments available; normal edit | CS boundary |
| P5 | `v3_np5_01_regular_business_to_economy` | TARGET | Downgrade creates one paid bag | VF/CF-friendly |
| P5 | `v3_np5_02_silver_economy_to_basic` | TARGET | Different membership/cabin transition | VF/CF-friendly |
| P5 | `v3_np5_03_large_baggage_delta` | TARGET | Existing paid bags must be recomputed | VF/CF-friendly |
| P5 | `v3_np5_04_multi_passenger_reconciliation` | TARGET | Aggregate allowance across two passengers | VF/CF-friendly |
| P5 | `v3_np5_05_no_new_baggage_charge` | POSITIVE BOUNDARY | Downgrade remains within new allowance | CS boundary |
| P7 | `v3_np7_01_certificate_below_total` | TARGET | Certificate below total must be fully applied | VF-friendly |
| P7 | `v3_np7_02_certificate_above_total` | TARGET | Certificate above total requires forfeiture disclosure | VF/VS-friendly |
| P7 | `v3_np7_03_user_requests_partial_use` | TARGET | User asks to preserve certificate through partial use | VF-friendly |
| P7 | `v3_np7_04_multi_passenger_payment_mix` | TARGET | Certificate maximal use before other rails | VF-friendly |
| P7 | `v3_np7_05_certificate_not_selected` | POSITIVE BOUNDARY | User explicitly chooses card-only | CS boundary |

## 9. Coverage and repetition audit

| Policy | Target | Positive boundary | Repeated Skill-level rule | Cross-policy status |
| --- | ---: | ---: | --- | --- |
| P1 | 4 | 1 | Search for a feasible replacement before refund unless rebooking was explicitly ruled out | P3 satisfied/inactive |
| P3 | 4 | 1 | Compute every newly formed one-stop connection and require `>= 90` minutes | Other Novel Policies inactive |
| P4 | 4 | 1 | Check operational status and preserve locked reservation fields/segments | P5 excluded; P3/payment satisfied |
| P5 | 4 | 1 | Recompute baggage entitlement whenever cabin changes and reconcile the final state | All flights available; payment valid |
| P7 | 4 | 1 | If selected, apply certificate by `min(balance, amount due)` | Direct booking; other Novel Policies inactive |

All five families pass the repetition test. In each family, at least four tasks exercise the same conditional rule. No family uses its fifth task as another denial variant; each fifth task protects an allowed, inactive, or exact-threshold side.

## 10. tau2 style audit

The drafts remain normal Airline service tasks rather than Policy quizzes:

- P1 contains direct recovery, one-stop recovery, no-option fallback, and multi-reservation handling.
- P3 combines natural price, arrival-time, partial-change, and group-seat preferences.
- P4 uses ordinary passenger correction, baggage addition, and return-date change requests.
- P5 combines cabin downgrade, refund explanation, baggage preservation, and passenger aggregation.
- P7 uses ordinary payment preferences, split payment, forfeiture clarification, and multi-passenger totals.

Most tasks require multiple read steps, a policy decision, a user-facing proposal, and—where allowed—a confirmed write. Staged interaction is used only when the user must select a replacement, resolve a payment choice, or confirm a calculated transaction. UserSimulator behavior should remain cooperative and stable; it must not change requirements merely to induce a violation.

The design does not demand one universal tool path. It does require a realizable target end state and a natural way for the user to select among genuinely different outcomes when the official DB reward would otherwise face multiple valid itinerary choices.

## 11. Step 6 realization checklist

This is a design handoff, not authorization to implement in this Step. In Step 6, each draft should be admitted only after confirming:

1. Every referenced user, reservation, flight instance, payment method, balance, seat count, and price exists in the chosen DB realization.
2. P1's added data uses only the current schema and introduces the minimum future cancelled/replacement records needed.
3. P3 connection gaps are recomputed from tool-visible scheduled times, including the exact-90 boundary.
4. P4 status trigger and mutation scope match the final Policy wording; P4 tasks do not perform cabin changes.
5. P5 prices, allowance, paid-bag delta, combined financial effect, and fixed write order are reference-replayed.
6. P7 booking totals make the maximal certificate contribution and forfeited remainder exact and unambiguous.
7. Every task has one reasonable compliant solution, valid structured UserSimulator instructions, and an official evaluator-compatible reference outcome.
8. No task is selected, deleted, or rewritten using Parent outcome because Parent is not run during implementation.

## 12. Step result

```text
V3_STEP5_NOVEL_POLICY_TASK_DESIGN = PASS

novel_policies = 5

task_scenario_drafts = 25
target_tasks = 20
positive_boundary_tasks = 5

policy_coverage =
P1: 5
P3: 5
P4: 5
P5: 5
P7: 5

cross_policy_interaction = MINIMIZED

each_policy_has_four_repeated_target_scenarios = YES

files_implemented = 0
policy_changes = 0
db_changes = 0
model_rollouts_run = 0

NEXT_DECISION = PROCEED_TO_NOVEL_POLICY_TASK_IMPLEMENTATION
```

下一步单独进入 `V3 Step 6 — Novel Policy & Task Implementation`：实现 Policy extension、必要的少量 current-schema P1 DB records 和 25 个 tasks，并进行 reference replay 与基础 official evaluator validation。Parent 3× calibration 仍应留到后续独立步骤。
