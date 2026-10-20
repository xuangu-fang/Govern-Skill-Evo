# P3-B Update对照：同Prompt的A与新B

**本版主对照改为：合法A_format_001（无Memory）与新B_format_001（真实R05 Memory）。两组完整system Prompt逐字相同，其他请求字段除Memory外完全一致。原B和失败尝试仅作历史记录，不与新B混用。**


## 1. A独立评价

A ready、adjustments=[]，全部保留。reason认为：

> the numbered-series/type-switch heuristic makes the coverage requirement implementable with the Actor's two-step history

但实际u1仍含`not yet inspected in this search`和`once that series is exhausted`，没有解释两步历史如何恢复全局访问/耗尽状态。编号及局部单向探索可以有合理动机，不能一概判错；本次reason对整条规则可执行的肯定却不充分。当前P6后期长drawer扫描耗尽预算，也不足以证明“必须扫完再换类”。

u2保留无效后不重复相同/等价动作及立即state-changing，未明确前提改变后的重试、有信息价值动作的边界。当前P1:4、P7:11/12、P8:39/P10:25足以检查该问题。原文首句允许reveal new information，不能夸大成完全禁止look/inventory。

Goal/Checks及精确目标、处理交付、desklamp要求保留，无新增条款；但不代表原有范围问题解决。Keep合法，不按没有Adjustment判错，也不以reason“Memory为空”断言模型仅因无历史而Keep。

## 2. 新B独立评价

新B只替换u1，basis引用当前P6/P8/P10、G3及M3/M6。它没有像旧B一样引用M8，也不能沿用旧B原文冒充本次输出。

它保留单向编号探索、到达开闭容器、近期空位置避免重复、精确对象/不替代，新增明确从当前admissible go-to列表选目的地，并把核心优先级改为：

> sample a receptacle type not yet used in this search rather than another instance of the type just swept

跨类型探索有当前问题动机及历史混合反馈支持，可以作为新假设。**具体实现仍有两个关键问题：**

1. `not yet used in this search`需要累计类别访问状态。当前动作候选说明可选动作，不说明哪些类别访问过；两步近期信息也不等于全程类型进度。reason称“executable from recent observations and admissible list”，没有在最终文本补足这一前提。
2. 新终止条件：

> Continue until the exact target is found or every receptacle type available in the room's action list has been sampled once.

这把类别采样一次作为搜索完成边界；M6的同类countertop 3遗漏恰好说明“到过该类”不等于覆盖该类其他实例。历史Diff原文是`all plausible candidate receptacles have been inspected once`，并未授权把位置覆盖替换为类别一次采样。它可能提前放弃仍有未查同类位置，但没有Actor执行，不能说已发生停止/失败。

本次没有固定数字批次、没有明确保证progress；括号内类别是举例，不能机械解释成固定全局顺序。与旧B不同，也没有逐字规定“所有其他类型都采样后才允许回同类”。新B偏好未用类别，例示换类别后再回drawer；这些具体条件和类别终止风险须按本次文本判断，不套用旧报告。

u2、Goal、Checks与A完全相同。精确目标、获取、温度处理、交付、desklamp的原有目标保留；搜索停止条件可能影响找到目标前的覆盖，不能仅凭Goal仍在就宣称全部有效行为都保证保留。

## 3. 原始事实核查

[共有当前证据](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/common_payload_without_memory.json)：P6:18到drawer4后继续，P6:50到drawer20但尚不能称已打开检查20；整条没有到cabinet，但前期也去countertop/sinkbasin。P8反复cabinet/sinkbasin且没到shelf1，但P8:2到bathtubbasin、P8:7/13/20到countertop，所以不能把整条P8说成只访问两种类别。P10:32到diningtable才发现apple，33取、35cool、38交付。它们说明循环/覆盖问题，不隔离证明最优类别安排。

## 4. 实质差异表

| 内容 | A Effective | 新B Effective | 判断 |
|---|---|---|---|
| 搜索安排 | 单向穷尽同类编号后换类 | 优先未用类别而非刚扫类别的下一实例，仍保留类内单向扫描 | 有方向/调度变化；合理探索动机不证明唯一优越性 |
| 候选依据 | 未检查位置及近期观察 | 明确从admissible go-to选下一目的地 | 可由共有当前协议/候选支持，不是历史独有收益 |
| 进度依赖 | 全局位置未查、类内耗尽 | 全局类别未用、所有类别已采样 | 换了状态粒度，没有彻底消除不可见信息前提 |
| 回访/换类 | 耗尽同类才换；之后可重入 | 优先新类型，例示换类后回drawer；刚离开空位置不回访 | 不强行解读为所有类型采样完才可返回；仍可能限制有效覆盖 |
| 搜索终止 | u1未新增类别完成边界 | 每个可用类别采样一次即可结束 | 新增依据不足的粒度变化，与M6同类遗漏警示不匹配 |
| u2 | Original Keep | 完全相同Keep | 无更新增量；状态改变后的重试边界均未修正 |
| Goal/Checks/no-substitute | 保留 | 保留 | 无差异，不能算B额外修复 |

## 5. 全文及实际Adjustment

### Goal（Original=A=B）

> Make search for the exact requested object coverage-oriented and step-efficient so the target is found, conditioned if required, and placed before the step budget is exhausted, without picking up, conditioning, or placing a substitute. Preserve the successful desklamp behavior (hold/co-locate the target and turn the lamp on at its receptacle), the direct acquire-then-place flow, and the correct clean/cool-then-place ordering already demonstrated.

### u1 Original = A

> During any search for the exact requested object (or for the desklamp once the target is in hand), treat the search as coverage of distinct candidate receptacles rather than a loop over a few. When the current observation shows the requested item is absent, move to a receptacle not yet inspected in this search, while retaining the existing rule to open a closed cabinet/drawer/fridge on arrival and inspect its contents. Sweep a numbered series of same-type containers in one direction without returning to earlier ones; once that series is exhausted without the target, switch to a different receptacle type (e.g., from drawers to cabinets, countertops, fridge, shelves, or sinkbasin) before re-entering the series. Use the most recent observations to notice when the next move would revisit a receptacle just left empty or repeat the same small set of locations, and in that case choose a different uninspected candidate. This is coverage for finding the exact target within the step budget; it does not permit picking up, conditioning, or placing a substitute object.

### u1 新B

> During any search for the exact requested object (or, once the target is in hand, for the desklamp), do not restrict the search to one container type or to a small set of locations. When the current observation shows the exact requested item is absent, choose the next destination from the admissible 'go to' list so that you sample a receptacle type not yet used in this search rather than another instance of the type just swept or a location you just saw was empty; for example, if a run of drawers has not yielded the target, go to cabinets, countertops, shelves, fridge, diningtable, or sinkbasin before re-entering the drawer series. While sweeping the numbered instances of one container type, move in one direction and do not return to an instance you just left empty. Keep the existing rule to open a closed cabinet/drawer/fridge on arrival and inspect its contents before leaving. Continue until the exact target is found or every receptacle type available in the room's action list has been sampled once. This is coverage for finding the exact target within the step budget; it does not permit picking up, conditioning, or placing a substitute object.

### u2 Original = A = B

> Do not spend steps on actions that cannot change the world or reveal new information. If an action returns 'Nothing happens,' if a 'look' repeats the description you already have for the current receptacle, or if 'inventory' is issued while carrying nothing, do not repeat that action or an equivalent one. Instead immediately take a state-changing action: move to a new uninspected receptacle, open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination.

### A完整输出

```json
{
  "decision": "ready",
  "reason": "Both proposed Updates are directly grounded in the supplied executions and are executable under the Actor's constraints, so no behavioral adjustment is justified. Update u1 targets the repeated small-set search loops visible in P3:5-P3:11 (drawers 1-4 swept, then re-swept before leaving the series), P6:6-P6:17 (drawer 1/countertop 1/drawer 2 cycled repeatedly), P8:9-P8:49 (cabinets 1-4 and sinkbasin 1 cycled many times), and P10:6-P10:31 (fridge 1/countertop 1/countertop 2/cabinet 1 cycled for ~30 steps before finding apple 1). Update u2 targets the observed no-op actions: the inadmissible 'go to shelf 2' returning 'Nothing happens' at P1:4, the duplicated 'look' with an unchanged observation at P7:11-P7:12, and the empty-handed 'inventory' at P8:39 and P10:25. Both Updates retain the Parent Skill's desklamp and acquire-condition-place behaviors, and the numbered-series/type-switch heuristic makes the coverage requirement implementable with the Actor's two-step history. Memory is empty, so no historical edit-behavior response argues for changing strategy, narrowing scope, or withdrawing either Update.",
  "adjustments": [],
  "checks": null
}
```

### 新B完整输出

```json
{
  "decision": "ready",
  "reason": "Both Updates address behavior that the supplied runs actually exhibit (long one-type searches with revisits, and wasted no-op steps). Only u1 needs refinement: the current evidence and Memory M3/M6 show that the effective ingredient is sampling additional receptacle types plus exact-target/no-substitute guidance, while the anti-cycling/revisit-avoidance wording alone was not reliably followed and is hard to track with the Actor's two-step history. u2 already matches the recorded no-op evidence (unreachable 'go to', duplicate 'look', empty-handed 'inventory'), so it is preserved, and the existing Checks remain appropriate.",
  "adjustments": [
    {
      "from": [
        "u1"
      ],
      "to": [
        {
          "id": "u1",
          "text": "During any search for the exact requested object (or, once the target is in hand, for the desklamp), do not restrict the search to one container type or to a small set of locations. When the current observation shows the exact requested item is absent, choose the next destination from the admissible 'go to' list so that you sample a receptacle type not yet used in this search rather than another instance of the type just swept or a location you just saw was empty; for example, if a run of drawers has not yielded the target, go to cabinets, countertops, shelves, fridge, diningtable, or sinkbasin before re-entering the drawer series. While sweeping the numbered instances of one container type, move in one direction and do not return to an instance you just left empty. Keep the existing rule to open a closed cabinet/drawer/fridge on arrival and inspect its contents before leaving. Continue until the exact target is found or every receptacle type available in the room's action list has been sampled once. This is coverage for finding the exact target within the step budget; it does not permit picking up, conditioning, or placing a substitute object."
        }
      ],
      "basis": [
        "P6:6",
        "P6:50",
        "P8:9",
        "P8:50",
        "P10:6",
        "G3",
        "M3",
        "M6"
      ],
      "reason": "Current runs show the Actor confines long searches to one or two receptacle types and revisits empty ones: P6 sweeps drawers up to drawer 20 and never opens a cabinet (P6:6, P6:50), P8 cycles among cabinets and sinkbasin and never reaches shelf 1 (P8:9, P8:50), and P10 cycles among fridge/countertops/cabinets for many steps before finding the apple (P10:6). Memory M3/M6 record that the anti-cycling/revisit-avoidance wording was not reliably followed and did not by itself break the cycling/step-limit failure, whereas added search breadth combined with exact-target guidance did help. The revised Update therefore makes the breadth requirement executable from the recent observations and the admissible 'go to' list, prioritizes sampling untried receptacle types, and retains the one-direction sweep, the open-closed-container rule, and the no-substitute constraint."
    }
  ],
  "checks": null
}
```

### 保持不变的Checks

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

原始字段见[A Effective](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_format_001/runs/A/effective_plan.json)、[新B Effective](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_B_format_001/runs/B/effective_plan.json)。本次u1实质不同，u2/Goal/Checks相同；没有Editor Patch或行为结果，不能推定任务成功率。
