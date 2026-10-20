# P3-B Update对照（A* Keep与原B Adjust）

**修订说明：本报告以合法的新格式A（记作A*）与原B作描述性对照。A*修改过输出格式Prompt，故不满足原P3-A的同Prompt控制条件；不是严格的Memory单变量验证。旧报告及执行记录已保留。**


## 1. A*独立评价

A*的reason称：

> the numbered-series/type-switch heuristic makes the coverage requirement implementable with the Actor's two-step history

u1未改变。仍要求`not yet inspected in this search`、单向扫完同类编号再换类；两步历史与编号线索不能自动恢复整个搜索的访问集合或穷尽状态。它没有说明这些必要前提如何持续获得。编号/局部有序探索可以是合理假设，不能一概判错；但本次对整条要求可执行的肯定超过了已说明的依据。P6的长drawer搜索耗尽预算也需要区分重复与覆盖安排，不由“方向正确”消除。

u2未改变。P1:4 no-op、P7:11/12重复look、P8:39/P10:25空inventory支持避免状态未变时的无信息重复；原文未明确状态改变后重试或有效信息获取的例外，仍要求立即state-changing。开头允许reveal new information，因此不夸大为禁止全部look/inventory。

A*没有新增强制要求，保留精确目标、必要处理交付、desklamp Goal及检查项；但原有边界问题仍在。合法Keep不等于必然合理，也不因没有Adjustment而自动判错。reason中“Memory为空”是其显式陈述，不证明其只因空Memory而Keep。

## 2. B独立评价

B确实把u1换成breadth-first跨类型探索、最近两组历史去重，保留精确目标/不替代和到达开容器；u2保持。改变探索安排有当前循环/覆盖问题与历史混合响应的动机，允许作为待验证假设，不要求它已被证明最优。

但B同时引入：

> Return to remaining numbers in a series only after other plausible types or locations have been sampled.

> Continue until the exact target is found or all plausible candidate types or locations have been inspected once.

前者新增排他续行条件；后者把types与locations放在同一完成边界，可能使类别采样代替实例覆盖。它们不能只凭扩大覆盖动机获充分支持；`remain unvisited`/`have been sampled`/`all ... once`仍依赖累计状态。文本风险未经过Actor验证，不能说已经发生过早停止或成功率退化。`a few`不是固定2/3次，括号类别列表不是已确定的强制全局顺序。

B对u2保留与A*相同的状态范围歧义。Goal仍含有效任务行为，但不能仅凭Goal保留就保证搜索续行限制不会与有效回源发生冲突。

## 3. 行为要求逐项差异

| 项目 | A*实际Effective | B实际Effective | 核查判断 |
|---|---|---|---|
| 同类编号搜索 | 必须单向扫完序列再换类 | 不穷尽长同类序列；采样few后换类 | 实质策略差异；两者优劣未隔离验证 |
| 近期去重 | 原有recent observations，加全局uninspected | 明确last two pre-action pairs、近期未出现候选 | B局部范围更明确，但共有Actor说明已支持，不是独有历史知识 |
| 全局状态 | not yet inspected、series exhausted | unvisited、sampled、all inspected once | 两者均残留未充分落实的信息前提 |
| 回到同类余项 | 穷尽后换类别再重入 | 其他合理类型/位置采样后才回余项 | B增加排他条件，M6同类遗漏不证明该条件必要 |
| 搜索结束 | u1没有新增类别一次结束条件 | exact target或all plausible types/locations once | B新增粒度混淆风险；不能等同于完整位置覆盖 |
| 无效动作u2 | 原文Keep | 完全相同Keep | 无更新增量，状态相关重复边界未改善 |
| 目标/交付/灯/Goal | 原样 | 原样；u1保留no-substitute | 无新增差异，不直接归功于M8 |
| Checks | 原c1/c2/c3 | 完全相同 | 无观测标准差异；Checks不是执行补救指令 |

## 4. Original、Effective全文及调整

以下全文直接读取原始JSON；未重写模型输出。A* u1/u2、Goal/Checks均与Original严格相同，故合列全文，避免把同一文本重复三次。

### Goal（Original=A*=B）

> Make search for the exact requested object coverage-oriented and step-efficient so the target is found, conditioned if required, and placed before the step budget is exhausted, without picking up, conditioning, or placing a substitute. Preserve the successful desklamp behavior (hold/co-locate the target and turn the lamp on at its receptacle), the direct acquire-then-place flow, and the correct clean/cool-then-place ordering already demonstrated.

### u1 Original = Effective A*

> During any search for the exact requested object (or for the desklamp once the target is in hand), treat the search as coverage of distinct candidate receptacles rather than a loop over a few. When the current observation shows the requested item is absent, move to a receptacle not yet inspected in this search, while retaining the existing rule to open a closed cabinet/drawer/fridge on arrival and inspect its contents. Sweep a numbered series of same-type containers in one direction without returning to earlier ones; once that series is exhausted without the target, switch to a different receptacle type (e.g., from drawers to cabinets, countertops, fridge, shelves, or sinkbasin) before re-entering the series. Use the most recent observations to notice when the next move would revisit a receptacle just left empty or repeat the same small set of locations, and in that case choose a different uninspected candidate. This is coverage for finding the exact target within the step budget; it does not permit picking up, conditioning, or placing a substitute object.

### u1 Effective B

> During any search for the exact requested object (or for the desklamp once the target is in hand), search as breadth-first coverage of distinct listed receptacles rather than exhausting one long same-type series. When the current observation shows the exact object is absent, use the current observation and the last two pre-action pairs to avoid repeating a receptacle just seen empty or the same small set; choose a different listed receptacle or type not present in that recent history. Do not open an entire numbered drawer/cabinet series while other receptacle types remain unvisited or the step count is already high; after sampling a few same-type containers without finding the target, switch to another type (for example drawers, cabinets, countertops, diningtable/sidetable, shelves, fridge, sinkbasin, or other open surfaces), opening each closed container immediately on arrival and inspecting its contents. Return to remaining numbers in a series only after other plausible types or locations have been sampled. Continue until the exact target is found or all plausible candidate types or locations have been inspected once. This is coverage for finding the exact target within the step budget; it never permits picking up, conditioning, or placing a substitute object.

### u2 Original = Effective A* = Effective B

> Do not spend steps on actions that cannot change the world or reveal new information. If an action returns 'Nothing happens,' if a 'look' repeats the description you already have for the current receptacle, or if 'inventory' is issued while carrying nothing, do not repeat that action or an equivalent one. Instead immediately take a state-changing action: move to a new uninspected receptacle, open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination.

### A*完整决策

```json
{
  "decision": "ready",
  "reason": "Both proposed Updates are directly grounded in the supplied executions and are executable under the Actor's constraints, so no behavioral adjustment is justified. Update u1 targets the repeated small-set search loops visible in P3:5-P3:11 (drawers 1-4 swept, then re-swept before leaving the series), P6:6-P6:17 (drawer 1/countertop 1/drawer 2 cycled repeatedly), P8:9-P8:49 (cabinets 1-4 and sinkbasin 1 cycled many times), and P10:6-P10:31 (fridge 1/countertop 1/countertop 2/cabinet 1 cycled for ~30 steps before finding apple 1). Update u2 targets the observed no-op actions: the inadmissible 'go to shelf 2' returning 'Nothing happens' at P1:4, the duplicated 'look' with an unchanged observation at P7:11-P7:12, and the empty-handed 'inventory' at P8:39 and P10:25. Both Updates retain the Parent Skill's desklamp and acquire-condition-place behaviors, and the numbered-series/type-switch heuristic makes the coverage requirement implementable with the Actor's two-step history. Memory is empty, so no historical edit-behavior response argues for changing strategy, narrowing scope, or withdrawing either Update.",
  "adjustments": [],
  "checks": null
}
```

### B完整决策与Adjustment

```json
{
  "decision": "ready",
  "reason": "Keep the no-op avoidance update unchanged because it directly targets observed repeated looks/empty inventory and remains executable. Adjust the search update to breadth-first coverage across receptacle types using only the last two observations, because current runs and historical Memory show that exhaustive same-type sweeps or cycling consume the step budget and that the Actor cannot reliably track an entire inspected set. Preserve exact-target/no-substitute behavior.",
  "adjustments": [
    {
      "from": [
        "u1"
      ],
      "to": [
        {
          "id": "u1",
          "text": "During any search for the exact requested object (or for the desklamp once the target is in hand), search as breadth-first coverage of distinct listed receptacles rather than exhausting one long same-type series. When the current observation shows the exact object is absent, use the current observation and the last two pre-action pairs to avoid repeating a receptacle just seen empty or the same small set; choose a different listed receptacle or type not present in that recent history. Do not open an entire numbered drawer/cabinet series while other receptacle types remain unvisited or the step count is already high; after sampling a few same-type containers without finding the target, switch to another type (for example drawers, cabinets, countertops, diningtable/sidetable, shelves, fridge, sinkbasin, or other open surfaces), opening each closed container immediately on arrival and inspecting its contents. Return to remaining numbers in a series only after other plausible types or locations have been sampled. Continue until the exact target is found or all plausible candidate types or locations have been inspected once. This is coverage for finding the exact target within the step budget; it never permits picking up, conditioning, or placing a substitute object."
        }
      ],
      "basis": [
        "M6",
        "M3",
        "M8",
        "P6:20",
        "P6:50",
        "P8:50",
        "P10:32"
      ],
      "reason": "The recorded failures show long same-type sweeps or cycling through a small set consuming the 50-step limit, while P10 eventually finds the exact apple on the diningtable after cycling. Historical M6 and M3 indicate that anti-revisit and broader-search language is often not followed reliably and can still miss a listed location, and the Actor only sees the last two pre-action observations, so the original instruction to sweep a numbered series before switching requires tracking the Actor does not have. Recrafting u1 as breadth-first sampling across receptacle types with recent-history cycling checks better fits Actor capabilities; M8 supports retaining the explicit no-substitute constraint."
    }
  ],
  "checks": null
}
```

### 三者相同Checks

```json
[
  {
    "id": "c1",
    "update_ids": [
      "u1"
    ],
    "question": "After a receptacle is inspected and the target is absent, does the Actor move to a new uninspected receptacle or switch receptacle type rather than returning to one already seen empty or re-sweeping the same series?"
  },
  {
    "id": "c2",
    "update_ids": [
      "u2"
    ],
    "question": "Does the Actor avoid repeating no-op actions ('Nothing happens,' duplicate 'look,' empty-handed 'inventory') and instead choose a state-changing action?"
  },
  {
    "id": "c3",
    "update_ids": [
      "u1",
      "u2"
    ],
    "question": "When the exact target is found, does the Actor still complete the required conditioning and final placement with that target, and preserve the desklamp on-while-co-located success pattern?"
  }
]
```

原文定位：[A*全部字段](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/effective_plan.json)；[B全部字段](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/effective_plan.json)；[共有当前证据](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/common_payload_without_memory.json)。u1有实质差异，u2无差异；这项描述可确认，但Prompt不一致阻断纯Memory归因。
