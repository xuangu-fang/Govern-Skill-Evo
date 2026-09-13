# Phase-A Context Transformation Review

`HUMAN_REVIEW_STATUS: COMPLETE`

本报告只复核 `canonical_visible = YES AND primary_role = L` 候选及两个已确认边界，不重新审计全部 832 个 source-occurrence units。分类和 transformation 均未使用 task labels、failure families、rollout outcomes 或 benchmark difficulty。

## 1. Final transformation rules

1. Complete-Upfront + Stable User Intent 保持 Phase-A 定义。
2. Canonical-visible N / D / I / E → `KEEP`。
3. Canonical-visible L → `HIDE`。
4. Canonical-hidden any role → `NO_CHANGE`；不补 implementation-only knowledge。
5. R → `NO_CHANGE`；保留已有证据，不添加答案、checklist 或 evaluator scaffold。
6. 同一 domain 对所有任务使用同一 transformation。
7. N/D/I/E 与 L 之间仍有真实歧义时，保守 `KEEP`。

## 2. Human-reviewed Airline HIDE list

| Knowledge ID | Domain | Canonical source | Role | Tags | Action | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| `AIR_POLICY_FLIGHT_HISTORY_001` | Airline | Policy · Modify flight / Change flights | L | L4 | HIDE | 保留 segment 是否可 kept；只隐藏 kept segment 使用历史价格而不按 current price 更新的 stateful valuation law。 |
| `AIR_POLICY_FLIGHT_ENFORCEMENT_001` | Airline | Policy · Modify flight / Change flights | L | L6 | HIDE | 隐藏 API 不执行 flight-change eligibility 的 backend enforcement disclosure；资格规则本身保持可见。 |
| `AIR_POLICY_CANCEL_ENFORCEMENT_001` | Airline | Policy · Cancel flight | L | L6 | HIDE | 隐藏 cancellation API 不执行 eligibility 的 backend enforcement disclosure；完整 cancellation eligibility 保持可见。 |

## 3. Human-reviewed Retail HIDE list

| Knowledge ID | Domain | Canonical source | Role | Tags | Action | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| `RET_POLICY_MODIFY_ITEMS_STATUS_001` | Retail | Policy · Modify pending order / Modify items | L | L1 | HIDE | Item substitution 之外的 secondary status mutation。 |
| `RET_POLICY_MODIFY_ITEMS_FUTURE_MODIFY_001` | Retail | Policy · Modify pending order / Modify items | L | L2 | HIDE | 当前 action 导致未来 modify option 关闭。 |
| `RET_POLICY_MODIFY_ITEMS_FUTURE_CANCEL_001` | Retail | Policy · Modify pending order / Modify items | L | L2 | HIDE | 当前 action 导致未来 cancel option 关闭。 |
| `RET_TOOL_CANCEL_DETAILS_004` | Retail | Tool schema · `cancel_pending_order` description | L | L1, L3 | HIDE | 只隐藏 refund 如何写入用户 gift-card profile balance；退款承诺、原支付方式和时效继续可见。 |

## 4. KEEP corrections

| Knowledge ID | Domain | Canonical source | Role | Tags | Action | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| `RET_POLICY_CANCEL_REFUND_001` | Retail | Policy · Cancel pending order | E | — | KEEP | Cancellation 有多个 explicit user-facing primary effects；退款是公开 action meaning。 |
| `RET_TOOL_CANCEL_DETAILS_003` | Retail | Tool schema · `cancel_pending_order` description | E | — | KEEP | Tool 明示 cancellation refunds payment；不能与 ledger mechanics 混为 L。 |
| `RET_TOOL_CANCEL_DETAILS_007` | Retail | Tool schema · `cancel_pending_order` description | N | — | KEEP | Gift-card refund 的 promised timing 属于用户 entitlement；由混合句拆出登记。 |
| `RET_TOOL_EXCHANGE_DELIVERED_ORDER_ITEMS_PRICE_DIFFERENCE_001` | Retail | Tool schema · `exchange_delivered_order_items.parameters.payment_method_id` | I | — | KEEP | 直接解释 `payment_method_id` 用于支付或接收 item price difference。 |
| `RET_TOOL_MODIFY_PENDING_ORDER_ITEMS_PRICE_DIFFERENCE_001` | Retail | Tool schema · `modify_pending_order_items.parameters.payment_method_id` | I | — | KEEP | 直接解释 `payment_method_id` 用于支付或接收 item price difference。 |

Correction A 将“取消会退款”的公开 primary effect 与 `payment_history`、gift-card balance、historical amount、mutation order 等 backend mechanics 分开。Correction B 将 price-difference parameter purpose 与 historical basis、ledger append、balance mutation、future feasibility 分开；L4 仅保留给 hidden historical/stateful valuation law。

## 5. Canonical-hidden semantics: explicitly NO_CHANGE

所有 `agent_visible_in_canonical_runtime = NO` 条目均为 `NO_CHANGE`。这包括 implementation-only I/D/E、hidden Raises、private helpers 和 implementation-only L；Unified Context 不补入这些信息，也不改变真实 tool result/error 的可观察性。

## 6. Ambiguous items kept conservatively

Retail cancellation tool 的混合句按 atomic semantics 拆分：user-facing refund promise 和 timing `KEEP`，gift-card profile balance update mechanism `HIDE`。Price-difference parameter purpose 按 I `KEEP`，不把 backend 是否立即结算、采用何种 old-price basis 或如何记账写入 context。Human review 后没有未解决、需要进一步扩大审计范围的 HIGH ambiguity。
