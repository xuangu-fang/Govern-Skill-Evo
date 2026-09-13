# Phase 5 — P3 Fresh Native State Mining

**PHASE5_P3_STATE_MINING_VERDICT: READY_FOR_P3_TASK_REALIZATION**

Phase 5 已完成。形成 P3_NATIVE_CANDIDATE_POOL_V1，未 materialize task。正式 benchmark 仍为 PHASE_A_UNIFIED_BENCHMARK_STATE_EXPANDED_V1（48 tasks），当前 P3 仍为 2。

## 执行边界

model calls = 0；rollouts = 0；Judge calls = 0；backend mutation/probe calls = 0；benchmark modifications = 0；task prompts = 0；evaluator implementations = 0。无 calibration、Skill Evolution、Gate 或 Train/Monitor split。所有变化值为原生数据加 backend 源码的静态推导，不是执行结果。

P3 canonical definition 保持 cancellation refund resource rebound / mutation-induced resource refresh dependency：upstream mutation → resource state 改变 → downstream 决策依赖最新 resource。候选仅按结构筛选；没有使用 Base outcome。

## 搜索、去重与分类口径

读取完整原生 Retail DB：500 users、1000 orders、50 products。主筛查为 338 个不同的 user/source/gift-card/target 组合，去重后仍 338；得到 5706 个跨门槛算术配置，折叠为 162 个 pair 线索（5544 个配置重复不计 state）。另静态检查 3 个负对照 bundle，总计 341 个 unique bundles 被不同深度检查。

本轮有意限定深度审计：4 个正候选 + 3 个负对照 = 7 个 candidate bundles，去重后 7 个。下表分类只针对这 7 个。其余 158 个算术线索不属于候选池，也没有独立性准入结论；其中包含现有 P3 和共享资源链。不能将 162 或 341 当作新增 P3 coverage。

推荐选择三种不同 upstream mutation，并要求三名用户、三张 gift card、六个订单互不重叠；第四个同型正候选保留为 reserve。按目标与 diversity 选定，不按模型表现筛选。所有商品选择来自可用同产品 native variant；只检查单商品变更，以避开多商品行为的额外复杂性。本轮未穷举多商品组合。

旧 dev inventory 中的两条 P3 仅作为 reference。task ID aliases 记录在 JSON 的 baselines 中；它们不是新 state。原生 tasks 仅检查订单 provenance，单订单引用不误判为完整 chain alias。同 bundle 的其他 variant/操作形式全部合并，不增加计数。

| 分类（7 个深度审计 bundle） | 数量 |
|---|---:|
| STRONG_P3_CANDIDATE | 3 |
| VALID_BUT_LOW_DIVERSITY | 1 |
| NOT_P3 | 2 |
| INVALID | 1 |

## State Mining Table

| Candidate state / User / order chain | Upstream mutation | Resource changed | Downstream dependency | Manifestation type | Independent? | Correct path? | Evaluator feasible? | Diversity vs existing | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| P3_NATIVE_001 / liam_lopez_7019 / #W2000719 → #W7555783 | CANCEL_REFUND_TO_GIFTCARD | gift_card_8483518: 21.00 → 214.79 | cost 29.26; PENDING_ITEM_UPGRADE | CANCEL_REFUND_TO_GIFTCARD -> PENDING_ITEM_UPGRADE | Yes | Yes | Yes, static | 新增类型 | STRONG_P3_CANDIDATE |
| P3_NATIVE_002 / juan_smith_5229 / #W1429524 → #W7546247 | PAYMENT_REPLACEMENT_REFUND_TO_GIFTCARD | gift_card_8506348: 63.00 → 829.17 | cost 71.58; PENDING_ITEM_UPGRADE | PAYMENT_REPLACEMENT_REFUND_TO_GIFTCARD -> PENDING_ITEM_UPGRADE | Yes | Yes | Yes, static | 新增类型 | STRONG_P3_CANDIDATE |
| P3_NATIVE_003 / liam_kovacs_4286 / #W1547606 → #W5762451 | ITEM_DOWNGRADE_REFUND_TO_GIFTCARD | gift_card_4544711: 37.00 → 59.08 | cost 38.95; PENDING_ITEM_UPGRADE | ITEM_DOWNGRADE_REFUND_TO_GIFTCARD -> PENDING_ITEM_UPGRADE | Yes | Yes | Yes, static | 新增类型 | STRONG_P3_CANDIDATE |
| P3_NATIVE_004 / yusuf_garcia_3055 / #W2564042 → #W3260419 | CANCEL_REFUND_TO_GIFTCARD | gift_card_7588375: 15.00 → 3547.75 | cost 1484.51; EXISTING_ORDER_PAYMENT_REPLACEMENT | CANCEL_REFUND_TO_GIFTCARD -> EXISTING_ORDER_PAYMENT_REPLACEMENT | Yes | Yes | Yes, static | 同型 | VALID_BUT_LOW_DIVERSITY |
| P3_NATIVE_005 / raj_sanchez_2970 / #W1067251 → #W4566809 | RETURN_REQUEST_TO_GIFTCARD | gift_card_2259499: 30.00 → 30.00 | cost 826.70; EXISTING_ORDER_PAYMENT_REPLACEMENT (unsupported) | RETURN_REQUEST_TO_GIFTCARD -> EXISTING_ORDER_PAYMENT_REPLACEMENT (unsupported) | Yes | No (P3 chain) | No (P3 chain) | 不计覆盖 | NOT_P3 |
| P3_NATIVE_006 / ivan_khan_7475 / #W1519594 → #W7032009 | CHEAPER_DELIVERED_EXCHANGE_REQUEST | gift_card_1711656: 62.00 → 62.00 | cost 724.34; EXISTING_ORDER_PAYMENT_REPLACEMENT (unsupported) | CHEAPER_DELIVERED_EXCHANGE_REQUEST -> EXISTING_ORDER_PAYMENT_REPLACEMENT (unsupported) | Yes | No (P3 chain) | No (P3 chain) | 不计覆盖 | NOT_P3 |
| P3_NATIVE_007 / ethan_garcia_1261 / #W4967593 → #W9911714 | CANCEL_PROCESSED_ORDER | gift_card_4332117: 86.00 → 86.00 | cost 671.66; EXISTING_ORDER_PAYMENT_REPLACEMENT (unsupported) | CANCEL_PROCESSED_ORDER -> EXISTING_ORDER_PAYMENT_REPLACEMENT (unsupported) | Yes | No (P3 chain) | No (P3 chain) | 不计覆盖 | INVALID |

## 每个候选的静态 structural audit

### P3_NATIVE_001 — retail:liam_lopez_7019:#W2000719->#W7555783:gift_card_8483518

1. **Native independent：** 原生不同用户、gift card、源/目标订单；不与两个现有 P3 或其余本轮候选共享用户/资源/订单。商品 catalog 共用不视为交易 state 重复。
2. **Upstream mutation：** 取消 pending 源订单 #W2000719，将原礼品卡付款 193.79 退回 gift_card_8483518。
3. **Resource：** gift_card_8483518 的 balance。
4. **前后值：** 21.00 → 214.79；即时 credit=193.79；目标费用=29.26；成功链最终余额=185.53。
5. **Downstream：** #W7555783 的一个商品升级至原生可用同产品 variant，用礼品卡支付差价 29.26。 原生门槛 21.00 < 29.26 <= 214.79，可支付集合因 mutation 改变。
6. **Refresh dependency：** before < cost <= after，因此 mutation 改变可支付性。
7. **Stale-state failure：** 继续用 21.00 判断，会错误认为 29.26 不可支付，拒绝/转人工/放弃目标或选错付款方式；真实更新后余额 214.79 足够。此为结构风险，不是已观察 Base 失败。
8. **Clean path：** 按现有 policy 验证用户身份；读取源订单、目标订单及用户礼品卡；商品变更需读取原生产品 variants。；取得源操作的用户确认；取消需合法取消原因，商品变更需确认完整变更集合。；取消 pending 源订单 #W2000719，将原礼品卡付款 193.79 退回 gift_card_8483518。；通过 get_user_details 获取最新余额；也可由已成功 mutation 的真实结果与 backend 规则正确更新资源认知，Success 不强制某个读取调用。；依据最新余额核对目标费用，取得目标操作确认；执行目标操作。
9. **Success evaluator：** {"source_goal": "cancelled 并有对应 gift-card refund", "downstream_goal": "目标指定商品/价格更新、status=pending (item modified)、新增 gift-card 差价 payment", "expected_gift_card_final_balance": 185.53, "preserved_fields": "未选择的商品、地址、其他订单及其他礼品卡余额保持不变；允许 backend 规定的 payment_history 扩展。", "scope": "仅未来 outcome evaluator 的可行性描述；未实现 evaluator。确认、身份验证、强制刷新调用不混入 Success。若要评价刷新行为，需另行定义过程度量；正确状态推理可成功。"}
10. **Task-specific hint：** 未来需明确普通用户意图（取消/保留源订单、所需商品配置、选择现有付款资源）；无需透露刷新步骤、隐藏余额门槛或解法。尚未生成任何 task prompt。
11. **Manifestation vs existing：** HIGH：下游为商品差价支付；upstream 仍为 cancellation。

静态 witness（native IDs / prices，不是 task 或运行后 state）：

```json
{
  "upstream": {
    "kind": "CANCEL_REFUND_TO_GIFTCARD",
    "credit": 193.79
  },
  "downstream": {
    "kind": "PENDING_ITEM_UPGRADE",
    "cost": 29.26,
    "item_change": {
      "old_item": "7617930199",
      "new_item": "1689914594",
      "product_id": "4768869376",
      "old_price": 285.94,
      "new_price": 315.2,
      "delta": 29.26,
      "new_variant": {
        "item_id": "1689914594",
        "options": {
          "color": "red",
          "battery life": "10 hours",
          "water resistance": "no"
        },
        "available": true,
        "price": 315.2
      }
    }
  }
}
```

Backend 依据：external/tau2-bench/src/tau2/domains/retail/tools.py:159-205, external/tau2-bench/src/tau2/domains/retail/tools.py:455-542。

Verdict：**STRONG_P3_CANDIDATE**；推荐下一阶段 realization。

### P3_NATIVE_002 — retail:juan_smith_5229:#W1429524->#W7546247:gift_card_8506348

1. **Native independent：** 原生不同用户、gift card、源/目标订单；不与两个现有 P3 或其余本轮候选共享用户/资源/订单。商品 catalog 共用不视为交易 state 重复。
2. **Upstream mutation：** 将 #W1429524 的整单付款从礼品卡替换为原生已登记的 paypal_9679338，原付款 766.17 即时退回礼品卡；源订单保留 pending。
3. **Resource：** gift_card_8506348 的 balance。
4. **前后值：** 63.00 → 829.17；即时 credit=766.17；目标费用=71.58；成功链最终余额=757.59。
5. **Downstream：** #W7546247 的一个商品升级至原生可用同产品 variant，用礼品卡支付差价 71.58。 原生门槛 63.00 < 71.58 <= 829.17，可支付集合因 mutation 改变。
6. **Refresh dependency：** before < cost <= after，因此 mutation 改变可支付性。
7. **Stale-state failure：** 继续用 63.00 判断，会错误认为 71.58 不可支付，拒绝/转人工/放弃目标或选错付款方式；真实更新后余额 829.17 足够。此为结构风险，不是已观察 Base 失败。
8. **Clean path：** 按现有 policy 验证用户身份；读取源订单、目标订单及用户礼品卡；商品变更需读取原生产品 variants。；取得源操作的用户确认；取消需合法取消原因，商品变更需确认完整变更集合。；将 #W1429524 的整单付款从礼品卡替换为原生已登记的 paypal_9679338，原付款 766.17 即时退回礼品卡；源订单保留 pending。；通过 get_user_details 获取最新余额；也可由已成功 mutation 的真实结果与 backend 规则正确更新资源认知，Success 不强制某个读取调用。；依据最新余额核对目标费用，取得目标操作确认；执行目标操作。
9. **Success evaluator：** {"source_goal": "源订单仍 pending，新增指定替代方式 payment 与原 gift-card refund", "downstream_goal": "目标指定商品/价格更新、status=pending (item modified)、新增 gift-card 差价 payment", "expected_gift_card_final_balance": 757.59, "preserved_fields": "未选择的商品、地址、其他订单及其他礼品卡余额保持不变；允许 backend 规定的 payment_history 扩展。", "scope": "仅未来 outcome evaluator 的可行性描述；未实现 evaluator。确认、身份验证、强制刷新调用不混入 Success。若要评价刷新行为，需另行定义过程度量；正确状态推理可成功。"}
10. **Task-specific hint：** 未来需明确普通用户意图（取消/保留源订单、所需商品配置、选择现有付款资源）；无需透露刷新步骤、隐藏余额门槛或解法。尚未生成任何 task prompt。
11. **Manifestation vs existing：** HIGH：下游为商品差价支付；upstream 为付款替换，源订单保留。

静态 witness（native IDs / prices，不是 task 或运行后 state）：

```json
{
  "upstream": {
    "kind": "PAYMENT_REPLACEMENT_REFUND_TO_GIFTCARD",
    "credit": 766.17,
    "new_payment_method": "paypal_9679338"
  },
  "downstream": {
    "kind": "PENDING_ITEM_UPGRADE",
    "cost": 71.58,
    "item_change": {
      "old_item": "7717598293",
      "new_item": "5946177616",
      "product_id": "6819683148",
      "old_price": 985.66,
      "new_price": 1057.24,
      "delta": 71.58,
      "new_variant": {
        "item_id": "5946177616",
        "options": {
          "type": "gas",
          "size": "portable",
          "features": "none"
        },
        "available": true,
        "price": 1057.24
      }
    }
  }
}
```

Backend 依据：external/tau2-bench/src/tau2/domains/retail/tools.py:545-622, external/tau2-bench/src/tau2/domains/retail/tools.py:455-542。

Verdict：**STRONG_P3_CANDIDATE**；推荐下一阶段 realization。

### P3_NATIVE_003 — retail:liam_kovacs_4286:#W1547606->#W5762451:gift_card_4544711

1. **Native independent：** 原生不同用户、gift card、源/目标订单；不与两个现有 P3 或其余本轮候选共享用户/资源/订单。商品 catalog 共用不视为交易 state 重复。
2. **Upstream mutation：** 将 #W1547606 的一个商品替换为原生可用低价同产品 variant，差额 22.08 退至现有礼品卡；源订单变为 pending (item modified)。
3. **Resource：** gift_card_4544711 的 balance。
4. **前后值：** 37.00 → 59.08；即时 credit=22.08；目标费用=38.95；成功链最终余额=20.13。
5. **Downstream：** #W5762451 的一个商品升级至原生可用同产品 variant，用礼品卡支付差价 38.95。 原生门槛 37.00 < 38.95 <= 59.08，可支付集合因 mutation 改变。
6. **Refresh dependency：** before < cost <= after，因此 mutation 改变可支付性。
7. **Stale-state failure：** 继续用 37.00 判断，会错误认为 38.95 不可支付，拒绝/转人工/放弃目标或选错付款方式；真实更新后余额 59.08 足够。此为结构风险，不是已观察 Base 失败。
8. **Clean path：** 按现有 policy 验证用户身份；读取源订单、目标订单及用户礼品卡；商品变更需读取原生产品 variants。；取得源操作的用户确认；取消需合法取消原因，商品变更需确认完整变更集合。；将 #W1547606 的一个商品替换为原生可用低价同产品 variant，差额 22.08 退至现有礼品卡；源订单变为 pending (item modified)。；通过 get_user_details 获取最新余额；也可由已成功 mutation 的真实结果与 backend 规则正确更新资源认知，Success 不强制某个读取调用。；依据最新余额核对目标费用，取得目标操作确认；执行目标操作。
9. **Success evaluator：** {"source_goal": "源订单单个指定商品/价格更新、status=pending (item modified)、新增 gift-card refund", "downstream_goal": "目标指定商品/价格更新、status=pending (item modified)、新增 gift-card 差价 payment", "expected_gift_card_final_balance": 20.13, "preserved_fields": "未选择的商品、地址、其他订单及其他礼品卡余额保持不变；允许 backend 规定的 payment_history 扩展。", "scope": "仅未来 outcome evaluator 的可行性描述；未实现 evaluator。确认、身份验证、强制刷新调用不混入 Success。若要评价刷新行为，需另行定义过程度量；正确状态推理可成功。"}
10. **Task-specific hint：** 未来需明确普通用户意图（取消/保留源订单、所需商品配置、选择现有付款资源）；无需透露刷新步骤、隐藏余额门槛或解法。尚未生成任何 task prompt。
11. **Manifestation vs existing：** HIGH：下游为商品差价支付；upstream 为商品降价的小额退款，两单商品各变更一次。

静态 witness（native IDs / prices，不是 task 或运行后 state）：

```json
{
  "upstream": {
    "kind": "ITEM_DOWNGRADE_REFUND_TO_GIFTCARD",
    "credit": 22.08,
    "item_change": {
      "old_item": "4859937227",
      "new_item": "6117189161",
      "product_id": "3377618313",
      "old_price": 503.58,
      "new_price": 481.5,
      "delta": -22.08,
      "new_variant": {
        "item_id": "6117189161",
        "options": {
          "resolution": "4K",
          "waterproof": "yes",
          "color": "silver"
        },
        "available": true,
        "price": 481.5
      }
    }
  },
  "downstream": {
    "kind": "PENDING_ITEM_UPGRADE",
    "cost": 38.95,
    "item_change": {
      "old_item": "2244749153",
      "new_item": "2960542086",
      "product_id": "8600330539",
      "old_price": 473.82,
      "new_price": 512.77,
      "delta": 38.95,
      "new_variant": {
        "item_id": "2960542086",
        "options": {
          "material": "wood",
          "color": "black",
          "height": "5 ft"
        },
        "available": true,
        "price": 512.77
      }
    }
  }
}
```

Backend 依据：external/tau2-bench/src/tau2/domains/retail/tools.py:455-542, external/tau2-bench/src/tau2/domains/retail/tools.py:455-542。

Verdict：**STRONG_P3_CANDIDATE**；推荐下一阶段 realization。

### P3_NATIVE_004 — retail:yusuf_garcia_3055:#W2564042->#W3260419:gift_card_7588375

1. **Native independent：** 原生不同用户、gift card、源/目标订单；不与两个现有 P3 或其余本轮候选共享用户/资源/订单。商品 catalog 共用不视为交易 state 重复。
2. **Upstream mutation：** 取消 pending 源订单 #W2564042，将原礼品卡付款 3532.75 退回 gift_card_7588375。
3. **Resource：** gift_card_7588375 的 balance。
4. **前后值：** 15.00 → 3547.75；即时 credit=3532.75；目标费用=1484.51；成功链最终余额=2063.24。
5. **Downstream：** #W3260419 的整单付款替换至礼品卡，需 1484.51。 原生门槛 15.00 < 1484.51 <= 3547.75，可支付集合因 mutation 改变。
6. **Refresh dependency：** before < cost <= after，因此 mutation 改变可支付性。
7. **Stale-state failure：** 继续用 15.00 判断，会错误认为 1484.51 不可支付，拒绝/转人工/放弃目标或选错付款方式；真实更新后余额 3547.75 足够。此为结构风险，不是已观察 Base 失败。
8. **Clean path：** 按现有 policy 验证用户身份；读取源订单、目标订单及用户礼品卡；商品变更需读取原生产品 variants。；取得源操作的用户确认；取消需合法取消原因，商品变更需确认完整变更集合。；取消 pending 源订单 #W2564042，将原礼品卡付款 3532.75 退回 gift_card_7588375。；通过 get_user_details 获取最新余额；也可由已成功 mutation 的真实结果与 backend 规则正确更新资源认知，Success 不强制某个读取调用。；依据最新余额核对目标费用，取得目标操作确认；执行目标操作。
9. **Success evaluator：** {"source_goal": "cancelled 并有对应 gift-card refund", "downstream_goal": "目标新增 gift-card payment 和原付款 refund；status=pending", "expected_gift_card_final_balance": 2063.24, "preserved_fields": "未选择的商品、地址、其他订单及其他礼品卡余额保持不变；允许 backend 规定的 payment_history 扩展。", "scope": "仅未来 outcome evaluator 的可行性描述；未实现 evaluator。确认、身份验证、强制刷新调用不混入 Success。若要评价刷新行为，需另行定义过程度量；正确状态推理可成功。"}
10. **Task-specific hint：** 未来需明确普通用户意图（取消/保留源订单、所需商品配置、选择现有付款资源）；无需透露刷新步骤、隐藏余额门槛或解法。尚未生成任何 task prompt。
11. **Manifestation vs existing：** LOW：相同 cancel → refund → existing-order payment replacement，只增加新交易配置。

静态 witness（native IDs / prices，不是 task 或运行后 state）：

```json
{
  "upstream": {
    "kind": "CANCEL_REFUND_TO_GIFTCARD",
    "credit": 3532.75
  },
  "downstream": {
    "kind": "EXISTING_ORDER_PAYMENT_REPLACEMENT",
    "cost": 1484.51
  }
}
```

Backend 依据：external/tau2-bench/src/tau2/domains/retail/tools.py:159-205, external/tau2-bench/src/tau2/domains/retail/tools.py:545-622。

Verdict：**VALID_BUT_LOW_DIVERSITY**；保留 reserve，不在本轮三个推荐中。

### P3_NATIVE_005 — retail:raj_sanchez_2970:#W1067251->#W4566809:gift_card_2259499

1. **Native independent：** 不同原生用户、源/目标订单、gift card，无本轮候选和已有 P3 重叠。
2. **Upstream mutation：** RETURN_REQUEST_TO_GIFTCARD
3. **Resource：** gift_card_2259499 的 balance。
4. **前后值：** 30.00 → 30.00；即时 credit=0.00；目标费用=826.70；成功链最终余额=None。
5. **Downstream：** 尝试后续将 #W4566809 整单 826.70 改为 gift card 支付；当前 30.00 不足，源操作不能释放可用资金。
6. **Refresh dependency：** return_delivered_order_items 仅设置 return requested / return_items / return_payment_method_id，不记账、不增加余额。
7. **Stale-state failure：** 原生余额未改变；使用旧余额并不会错。若凭退款请求推定入账，属于虚构资源状态，不是 stale pre-mutation resource。
8. **Clean path：** 此 P3 链无 clean path。；return_delivered_order_items 仅设置 return requested / return_items / return_payment_method_id，不记账、不增加余额。；合法 return/exchange 请求本身可完成（processed cancellation 则不可），但不能据此假定余额已到账。
9. **Success evaluator：** {"reason": "该 proposed P3 goal 无真实 backend resource rebound；不能把申请完成等同即时退款。"}
10. **Task-specific hint：** 任何提示均不能修复不存在的 backend 记账/不允许的取消；不得人工补余额或改 status。
11. **Manifestation vs existing：** 不计入 manifestation coverage。

静态 witness（native IDs / prices，不是 task 或运行后 state）：

```json
{
  "return_item_ids": [
    "6452271382",
    "7848293342"
  ],
  "requested_refund_destination": "gift_card_2259499",
  "order_paid_amount": 1201.55,
  "actual_immediate_credit": 0
}
```

Backend 依据：external/tau2-bench/src/tau2/domains/retail/tools.py:664-725。

Verdict：**NOT_P3**；不进入候选池。

### P3_NATIVE_006 — retail:ivan_khan_7475:#W1519594->#W7032009:gift_card_1711656

1. **Native independent：** 不同原生用户、源/目标订单、gift card，无本轮候选和已有 P3 重叠。
2. **Upstream mutation：** CHEAPER_DELIVERED_EXCHANGE_REQUEST
3. **Resource：** gift_card_1711656 的 balance。
4. **前后值：** 62.00 → 62.00；即时 credit=0.00；目标费用=724.34；成功链最终余额=None。
5. **Downstream：** 尝试后续将 #W7032009 整单 724.34 改为 gift card 支付；当前 62.00 不足，源操作不能释放可用资金。
6. **Refresh dependency：** exchange_delivered_order_items 只记录 exchange requested 与差价，不即时退款/改变余额。
7. **Stale-state failure：** 原生余额未改变；使用旧余额并不会错。若凭退款请求推定入账，属于虚构资源状态，不是 stale pre-mutation resource。
8. **Clean path：** 此 P3 链无 clean path。；exchange_delivered_order_items 只记录 exchange requested 与差价，不即时退款/改变余额。；合法 return/exchange 请求本身可完成（processed cancellation 则不可），但不能据此假定余额已到账。
9. **Success evaluator：** {"reason": "该 proposed P3 goal 无真实 backend resource rebound；不能把申请完成等同即时退款。"}
10. **Task-specific hint：** 任何提示均不能修复不存在的 backend 记账/不允许的取消；不得人工补余额或改 status。
11. **Manifestation vs existing：** 不计入 manifestation coverage。

静态 witness（native IDs / prices，不是 task 或运行后 state）：

```json
{
  "old_item": "9472539378",
  "new_item": "1240311797",
  "old_price": 143.72,
  "new_price": 137.17,
  "recorded_exchange_difference": -6.55,
  "actual_immediate_credit": 0,
  "new_variant": {
    "item_id": "1240311797",
    "options": {
      "capacity": "1L",
      "material": "glass",
      "color": "silver"
    },
    "available": true,
    "price": 137.17
  }
}
```

Backend 依据：external/tau2-bench/src/tau2/domains/retail/tools.py:208-284。

Verdict：**NOT_P3**；不进入候选池。

### P3_NATIVE_007 — retail:ethan_garcia_1261:#W4967593->#W9911714:gift_card_4332117

1. **Native independent：** 不同原生用户、源/目标订单、gift card，无本轮候选和已有 P3 重叠。
2. **Upstream mutation：** CANCEL_PROCESSED_ORDER
3. **Resource：** gift_card_4332117 的 balance。
4. **前后值：** 86.00 → 86.00；即时 credit=0.00；目标费用=671.66；成功链最终余额=None。
5. **Downstream：** 尝试后续将 #W9911714 整单 671.66 改为 gift card 支付；当前 86.00 不足，源操作不能释放可用资金。
6. **Refresh dependency：** 源订单原生 status=processed；cancel_pending_order 要求严格 pending，入口即拒绝。
7. **Stale-state failure：** 原生余额未改变；使用旧余额并不会错。若凭退款请求推定入账，属于虚构资源状态，不是 stale pre-mutation resource。
8. **Clean path：** 此 P3 链无 clean path。；源订单原生 status=processed；cancel_pending_order 要求严格 pending，入口即拒绝。；合法 return/exchange 请求本身可完成（processed cancellation 则不可），但不能据此假定余额已到账。
9. **Success evaluator：** {"reason": "该 proposed P3 goal 无真实 backend resource rebound；不能把申请完成等同即时退款。"}
10. **Task-specific hint：** 任何提示均不能修复不存在的 backend 记账/不允许的取消；不得人工补余额或改 status。
11. **Manifestation vs existing：** 不计入 manifestation coverage。

Backend 依据：external/tau2-bench/src/tau2/domains/retail/tools.py:174-181。

Verdict：**INVALID**；不进入候选池。

## Manifestation coverage 与下一阶段建议

已有两个正式 state：W9892465 → W1242543、W5432440 → W9432206，均属于 **CANCEL_REFUND_TO_GIFTCARD → EXISTING_ORDER_PAYMENT_REPLACEMENT**，仅 1 种 manifestation。它们未改动、未重跑。

推荐以下三个 independent states 进入下一阶段 P3 Clean Task Realization：

- **retail:liam_lopez_7019:#W2000719->#W7555783:gift_card_8483518**：CANCEL_REFUND_TO_GIFTCARD -> PENDING_ITEM_UPGRADE。
- **retail:juan_smith_5229:#W1429524->#W7546247:gift_card_8506348**：PAYMENT_REPLACEMENT_REFUND_TO_GIFTCARD -> PENDING_ITEM_UPGRADE。
- **retail:liam_kovacs_4286:#W1547606->#W5762451:gift_card_4544711**：ITEM_DOWNGRADE_REFUND_TO_GIFTCARD -> PENDING_ITEM_UPGRADE。

三条推荐均把 downstream 从整单换付款改成已有订单商品升级差价支付；分别保留取消上游、增加保留订单的付款替换退款上游、增加商品降价退款上游。故增加 3 种细粒度 manifestation；三条下游仍同为 pending item upgrade，不能声称三个不同 downstream families。合计将有 4 种 manifestation、2 种 downstream families（整单替换 / 商品差价）。资源类型仍仅 gift card，未获得 store credit / new purchase 支持。

若**全部三个推荐**后续 admission，projected P3 independent states = 2 + 3 = **5**，条件性达到 soft target ≈ 5，缺口 0；当前实际 coverage 仍为 2。本轮无需下一轮 fresh mining，先进行 realization。若后续有候选不通过，应先评估 reserve；不自动 admission 或改 state。若连 reserve 也后续 admission，则为 6，此数字不是本轮推荐 projection。

## Backend 边界与潜在 composition note

return_delivered_order_items 只记申请，不即时退还余额；exchange_delivered_order_items 只记 exchange 字段/差价、检查余额，不即时扣款或退款。因此 return/exchange 不能被虚构成 upstream rebound。Delivered exchange 的 affordability 可作为后续候选的 downstream，但本轮未深度准入。Retail 未提供新建订单/购买、store credit 或新增付款方式接口。

未证明任何 potential separable VF。可记录通用 confirmation/refresh 与 goal completion 的潜在组合，尤其 P3_NATIVE_003 涉及两单各一次 item modification，与 P1 相邻；其 clean path 不需要二次修改同一订单。未设计 VF→VS→CS、VF→CF→CS，未为 VF 改 native state。

## 可复核证据与限制

精确 native order/items/payment history、gift card、variant availability/options、静态 witness 与 backend 行范围见 p3_state_mining_table.json；来源 SHA-256 和 benchmark 文件保全哈希见 p3_native_candidate_pool_v1.json。

Success evaluator feasible 仅说明将来可依据订单终态、目标商品、payment/refund ledger、礼品卡余额与保留字段写出 outcome 检查，不是 evaluator 实现或 calibration 结论。未要求 Success 必须观察 get_user_details；正确更新状态认知的其他路径也应允许。普通用户目标、合法确认与商品配置仍需下一阶段 realization 明确，候选池没有 task prompt。

本轮为静态检查；未调用 backend mutation、模型或 judge，因此没有动态执行成功/失败的证据，也未声称完成 task admission。

## 文件清单

- p3_native_candidate_pool_v1.json
- p3_state_mining_table.json
- p3_manifestation_coverage.json
- p3_rejected_candidates.json
- PHASE5_P3_FRESH_NATIVE_STATE_MINING_REPORT.md

完成后停止；不写 task、不 rollout、不修改当前 48-task benchmark。

最终静态核验通过：四份 JSON 可解析；七个 bundle 的原生 ownership/profile 归属、用户/订单/资源去重、与已有 P3 的独立性均成立；四个正候选的单商品 availability / 同产品不同配置、付款前置条件及 Decimal 金额门槛核对通过；19 个来源与正式 benchmark 文件 SHA-256 保持不变。仅新增上述五份产物。
