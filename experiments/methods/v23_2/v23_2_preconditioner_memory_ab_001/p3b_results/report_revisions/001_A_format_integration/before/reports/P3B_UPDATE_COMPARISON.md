# P3-B Update独立评价与比较边界

**A无有效输出；先记录其不可评价，再独立分析B。以下Original→B变化不是A→B增量。**

## 1. A组独立评价

A读取超时，没有reason、adjustments、checks或Effective Plan。u1/u2是否Keep、如何改变、是否使用当前证据均**无法判断**。不把Original代填Effective A，不用正式V23/此前任何无Memory输出补位。A的技术失败不是预条件化语义失败。

## 2. B组独立评价

### 实际总体判断

> Keep the no-op avoidance update unchanged because it directly targets observed repeated looks/empty inventory and remains executable. Adjust the search update to breadth-first coverage across receptacle types using only the last two observations, because current runs and historical Memory show that exhaustive same-type sweeps or cycling consume the step budget and that the Actor cannot reliably track an entire inspected set. Preserve exact-target/no-substitute behavior.

唯一Adjustment的实际reason：

> The recorded failures show long same-type sweeps or cycling through a small set consuming the 50-step limit, while P10 eventually finds the exact apple on the diningtable after cycling. Historical M6 and M3 indicate that anti-revisit and broader-search language is often not followed reliably and can still miss a listed location, and the Actor only sees the last two pre-action observations, so the original instruction to sweep a numbered series before switching requires tracking the Actor does not have. Recrafting u1 as breadth-first sampling across receptacle types with recent-history cycling checks better fits Actor capabilities; M8 supports retaining the explicit no-substitute constraint.

其basis为 `['M6', 'M3', 'M8', 'P6:20', 'P6:50', 'P8:50', 'P10:32']`；decision=ready、checks=null。

### u1：从编号穷尽改成跨类型采样，有问题动机，但附带限制仍越界

| 行为要求 | B实际文本 | 独立评价 |
|---|---|---|
| 搜索方向 | `breadth-first coverage ... rather than exhausting one long same-type series` | 当前P6长drawer搜索、P8循环、P10晚到diningtable支持尝试重新安排覆盖；M6/M3也提供混合反馈。跨类型探索可保留为候选假设，不是天然错误；也没有证据证明它一定胜过所有类内穷尽 |
| 近期反循环 | `use the current observation and the last two pre-action pairs`；`not present in that recent history` | 比全局未访问集合更接近Actor实际输入，明确了观察窗口。近期未出现不等于全局未访问，不能据此认为已实现全局广度覆盖；“different listed receptacle or type”留有选择，不是固定全局类别顺序 |
| 类内切换尺度 | `after sampling a few same-type containers ... switch` | few没有给出2次/3次等固定数值，不应机械判为数值阈值。它是有减少单类耗时动机、尚未验证的调度假设；但“few”的跨多步进度未明确，不能声称已完整解决信息能力问题 |
| 全局未访问条件 | `while other receptacle types remain unvisited or the step count is already high` | 步数可见，high未定量不等于已规定阈值；然而“其他类型仍未访问”仍需超出两步窗口的全局进度，文本未给恢复依据。reason所称better fits能力并未贯穿最终规则 |
| 续查同类的前提 | `Return to remaining numbers in a series only after other plausible types or locations have been sampled` | 这是实质性强顺序：先完成其他采样才能续查。既需累计采样/剩余编号状态，也没有独立证据证明这一排他前提必要。M6遗漏同类countertop3反而提示不能无条件推迟同类余项；不据此反向规定必须类内穷尽 |
| 新搜索终止条件 | `until ... all plausible candidate types or locations have been inspected once` | Original u1未规定类别采样终止，Parent边界是合理receptacles而非types。`types or locations`使类别采样与位置耗尽混用，可能在同类仍有未查实例时满足宽泛停止读法；并依赖全局进度。合理的广度动机不足以支持这个附带变化。是文本风险，未执行所以不声称已发生过早停止 |
| 必要行为保留 | 保留exact target/no-substitute、到达闭容器就open；Goal和u2含获取/处理/交付；作用域仍含持目标后lamp搜索 | 精确对象等主要保留。没有新增必然成功/guarantee progress字面保证，也没有数值批次或固定全局类别排序。scope未排除已知有用目的地，新的采样前提与近期回避可能干扰有效返回；G1共址与M9回源需区分，不能据文案直接认定一切回源被禁止 |

B识别了全局已检查集合问题，但最终又引入“其他类型unvisited/已sampled/所有types或locations一次”。**局部近期新颖性条件有所落实，全局策略状态依赖仍未解决。**不把所有编号策略一概判不可执行：某些进度可由当前编号/可见候选恢复；问题是本次跨族累计条件并无这种说明。

B没有为“所有类别采样后才能回同类”和类别级结束条件分别给出证据或可检验预期。不能将广度探索的合理动机自动扩展为所有附带强制条件的依据。

### u2：保持原文，条件范围问题未处理

B明确写 `Keep the no-op avoidance update unchanged`，Effective u2与Original完全一致。当前P1:4不可用移动、P7:11/12相同look、P8:39/P10:25空inventory确实支持避免**相同条件下**无信息重复。

但最终仍为：`do not repeat that action or an equivalent one`，随后 `Instead immediately take a state-changing action`，未明确动作前提/相关状态变化后可重试，亦未细分新信息获取与世界状态改变。开头“change the world or reveal new information”保留信息价值，所以不能夸大成“禁止所有look/inventory”；真正问题是触发后禁止重复的作用时段与例外没有清楚界定。

这是原案继承的范围风险，不是B新增禁令；仅称current evidence支持它并不足以处理这个风险。M6的实际不可用移动反馈没有落实为u2的状态前提修正。**是否A本来也会Keep，完全未知。**

### Goal、Checks与落地

Goal保持冻结原文，未变成新的算法目标。Checks c1–c3原样：c1观测新位置/换类与不回扫，c2观测no-op转state-changing，c3保留处理交付和灯行为。其结构仍引用有效u1/u2，但c1未专门区分类别采样与同类未查位置，c2也未补状态变化后可重试的范围。Checks不能替最终指令补上缺失前提。

编译器准确落实u1替代、u2 Keep；没有编译失真迹象。问题出在实际策略构造/保留判断，而非reason没有进入编译。未调用Editor，不评价实际Patch或行为。

## 3. 各对象对照（A缺失不能补造）

| 对象 | Original | Effective A | Effective B |
|---|---|---|---|
| u1方向/顺序 | 同类编号单向，耗尽后换类 | 不可得 | 跨类型采样，少量同类后切换，其他采样后才回剩余编号 |
| u1信息前提 | 全局未查/系列耗尽，另有近期反循环 | 不可得 | 明确最近两步；但保留其他类型未访问/已采样等累计前提 |
| u1结束 | 当前Update以找到目标/预算为目标；Parent有位置检查一次边界 | 不可得 | 新增types或locations检查一次的结束表达 |
| u2 | 无效后不重复等价动作，立即state-changing | 不可得 | 完全Keep，状态条件未收窄 |
| Goal / Checks | 原文 | 不可得 | 原样 |
| 实际A/B语义差异 | — | **无法比较** | 只能相对Original评价 |

## 4. 全文对照

### Original Goal

> Make search for the exact requested object coverage-oriented and step-efficient so the target is found, conditioned if required, and placed before the step budget is exhausted, without picking up, conditioning, or placing a substitute. Preserve the successful desklamp behavior (hold/co-locate the target and turn the lamp on at its receptacle), the direct acquire-then-place flow, and the correct clean/cool-then-place ordering already demonstrated.

### u1 Original

> During any search for the exact requested object (or for the desklamp once the target is in hand), treat the search as coverage of distinct candidate receptacles rather than a loop over a few. When the current observation shows the requested item is absent, move to a receptacle not yet inspected in this search, while retaining the existing rule to open a closed cabinet/drawer/fridge on arrival and inspect its contents. Sweep a numbered series of same-type containers in one direction without returning to earlier ones; once that series is exhausted without the target, switch to a different receptacle type (e.g., from drawers to cabinets, countertops, fridge, shelves, or sinkbasin) before re-entering the series. Use the most recent observations to notice when the next move would revisit a receptacle just left empty or repeat the same small set of locations, and in that case choose a different uninspected candidate. This is coverage for finding the exact target within the step budget; it does not permit picking up, conditioning, or placing a substitute object.

**Effective A：未获得。**

**Effective B：**

> During any search for the exact requested object (or for the desklamp once the target is in hand), search as breadth-first coverage of distinct listed receptacles rather than exhausting one long same-type series. When the current observation shows the exact object is absent, use the current observation and the last two pre-action pairs to avoid repeating a receptacle just seen empty or the same small set; choose a different listed receptacle or type not present in that recent history. Do not open an entire numbered drawer/cabinet series while other receptacle types remain unvisited or the step count is already high; after sampling a few same-type containers without finding the target, switch to another type (for example drawers, cabinets, countertops, diningtable/sidetable, shelves, fridge, sinkbasin, or other open surfaces), opening each closed container immediately on arrival and inspecting its contents. Return to remaining numbers in a series only after other plausible types or locations have been sampled. Continue until the exact target is found or all plausible candidate types or locations have been inspected once. This is coverage for finding the exact target within the step budget; it never permits picking up, conditioning, or placing a substitute object.

### u2 Original

> Do not spend steps on actions that cannot change the world or reveal new information. If an action returns 'Nothing happens,' if a 'look' repeats the description you already have for the current receptacle, or if 'inventory' is issued while carrying nothing, do not repeat that action or an equivalent one. Instead immediately take a state-changing action: move to a new uninspected receptacle, open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination.

**Effective A：未获得。**

**Effective B：**

> Do not spend steps on actions that cannot change the world or reveal new information. If an action returns 'Nothing happens,' if a 'look' repeats the description you already have for the current receptacle, or if 'inventory' is issued while carrying nothing, do not repeat that action or an equivalent one. Instead immediately take a state-changing action: move to a new uninspected receptacle, open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination.

### Checks（Original与B相同）

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

实际结构化输出见 [B Preconditioner](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/preconditioner.json)、[B Effective](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/runs/B/effective_plan.json)；原始当前执行与菜单见 [固定共同输入](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/config/common_payload_without_memory.json)。
