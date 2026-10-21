# P1-R：R04/R05/R06 人工表示与 Patch 走查

以下全部为人工设计材料，不是新模型响应、Candidate Skill 或任务收益。原始材料均为已归档 **P1-B Diagnosis**（R05 使用成功重试），不是正式 V23 当时的 Original；正式各轮 Memory 仅作为只读证据。没有改变归档中的任何 Plan。

每例提供原始 JSON 的逐字节副本和独立多行 JSON。后者只改 text 组织，Goal、Updates 的 id/basis、Checks 及顶层字段不变；原文缺陷也保留。下面 L1/L2 是本报告的临时文本行号，不是新 requirement ID。表示保真是人工对照判断；结构测试只证明其他字段相等。

测试 Patch 是人工先选择要修改的要求和关联，再显式编写相应 Hunk；expected 只用于离线断言，没有运行时“先自由重写全文再反推 Patch”的流程。混合坐标测试故意使用占位要求，不当作策略方案。

## R04

[归档原始来源](../../../../artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R04/attempts/001/diagnosis.json) · [原文精确副本](fixtures/R04.original.json) · [人工多行副本](fixtures/R04.multiline.json) · [人工 Patch 方案](fixtures/R04.scenarios.json)

### 原文到多行的对应

| 人工位置 | 原文来源 | 表示处理 |
|---|---|---|
| u1 L1–2 | 原步骤(1) | 分开精确类别选择与未发现时继续搜索，均保留热处理任务作用域 |
| u1 L3 | 原步骤(2) | 保留 closed 就 open 的原有强前提，不在表示阶段纠正 |
| u1 L4–5 | 原步骤(3) | 处理状态与动作整行保留，避免重复无信息操作另行 |
| u1 L6–7 | 原步骤(4) | 成功处理后交付及避免无关回返分行，显式保留成功后的范围 |
| u1 L8 | 原步骤(5) | 原完成条件保留 |
| u2 L1–4 | 原步骤(1) | 搜索集合/类别覆盖、开容器、表面覆盖、类别限制分别成行 |
| u2 L5/L6/L7/L8 | 原步骤(2)/(3)/(4)/(5) | 保留“移走物体就排除来源”和 unvisited 等原问题，不伪装成已纠正 |

### 决策与未解决问题

- `single` 仅改 u1 L3 开门前提，u1 L6–8 的交付/完成及整个 u2 不变。**L4 仍要求 open microwave，单行演示不是完整语义修复。**
- `linked` 同改 L3/L4：开门视可见前提决定、处理动作须当前提供；这是一组真实必要配套，不能把菜单可用写成任何状态直接 heat 必成功。L5 的反循环和 L6–8 完全保留。
- `cross` 在上述基础上同改 u2 L5/L6，区分当前/近期信息显示空的回访与仍有剩余目标的有效来源；取消“移走一件即空”和“只能未访问处继续”的冲突。u2 L7/L8 的数量与完成保留。
- `add` 是当前候选中动作可用性的独立要求，不由历史搜索正例自动支持；`delete` 仅演示删除 u2 L5，会同时移除该行的部分反循环指导，需另外语义评价，不作为部署建议。
- `broad` 修改 u2 L1/L4/L5/L6，证明大范围变换不受行数限制。Goal 的 `sweeping all receptacle types once` 未改；不能宣称已经解除该目标承诺。

证据仍为 P1 的 R04 当前 heat 候选及多实例回源事实；不能把成功动作链当作必要前置链，也不能要求 Actor 记住已超出两步历史的全部来源。

### 人工多行表示全文

以下仍是原策略的表示副本，不是应用测试 Patch 后的文本。

**u1**（8 行）

```text
- For a heat-then-place task (for example, "hot X" or "heat some X and put it ..."), acquire the exact named target category; do not pick up a visually similar but different category, such as a cup when a mug is requested.
- For a heat-then-place task, if the exact target is not yet visible, continue the systematic search instead of settling for a substitute.
- For a heat-then-place task, carry the target to the microwave; if the microwave is closed, open it once.
- For a heat-then-place task, with the target held at the open microwave, issue exactly one 'heat <target> with microwave 1' action.
- During heat-then-place processing, do not repeatedly move the target into and out of the microwave and do not loop open/close actions; those steps are wasted and can consume the step budget.
- Immediately after the successful heat action, go to the requested destination, open it if closed, and place the target there.
- After successful heating, do not wander to unrelated cabinets or return to the microwave.
- Stop once the heated target has been placed.
```

**u2**（8 行）

```text
- For a task requiring more than one instance of a target category ("two X", "find two X", etc.), treat the initial room listing as the search set and inspect each receptacle type at least once.
- During that multi-instance search, open every closed cabinet, drawer, and fridge encountered.
- During that multi-instance search, also check open furniture surfaces such as countertops, diningtables, coffeetables, shelves, dressers, beds, sofas, sidetables, tvstands, armchairs, and desks.
- During that multi-instance search, do not restrict the sweep to one furniture type (for example, only shelves and drawers) while other listed receptacles remain unchecked.
- During that multi-instance search, when a location is visibly empty or an object there has already been moved, go to a different not-yet-inspected receptacle rather than immediately re-checking the same empty container; do not cycle among a small set of already-inspected locations.
- After delivering one instance to the destination, resume the sweep for the next instance from unvisited receptacles instead of stopping at one or rechecking emptied ones.
- Continue until the requested number of instances of the exact category has been placed; do not substitute another category to reach the count.
- Stop once the required count is placed.
```

### Patch 实际范围

| 方案 | 删除/替换的原行或新增行 | 未改行与边界 |
|---|---|---|
| single | u1: L3 | u1: L1,L2,L4,L5,L6,L7,L8；其余 Update、Goal、Checks 保持 |
| linked | u1: L3/L4 | u1: L1,L2,L5,L6,L7,L8；其余 Update、Goal、Checks 保持 |
| delete | u2: L5 | u2: L1,L2,L3,L4,L6,L7,L8；其余 Update、Goal、Checks 保持 |
| broad | u2: L1/L4/L5/L6 | u2: L2,L3,L7,L8；其余 Update、Goal、Checks 保持 |
| cross | u1: L3/L4；u2: L5/L6 | u1: L1,L2,L5,L6,L7,L8；u2: L1,L2,L3,L4,L7,L8；其余 Update、Goal、Checks 保持 |
| add | u1: 末尾新增 L9 | u1: L1,L2,L3,L4,L5,L6,L7,L8；其余 Update、Goal、Checks 保持 |

每份方案独立从同一人工 Original 应用，不把 single 的结果继续交给 linked。实际应用输出与未改行的原/新坐标证据保存于 [tests.json](results/tests.json)。删除导致后续行号变化，不要求其新行号与旧行号相等。

关联行的实际 Unified Diff：

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -3 +3 @@
-- For a heat-then-place task, carry the target to the microwave; if the microwave is closed, open it once.
+- For a heat-then-place task, carry the target to the microwave and open it only when current access or action conditions require opening.
@@ -4 +4 @@
-- For a heat-then-place task, with the target held at the open microwave, issue exactly one 'heat <target> with microwave 1' action.
+- For a heat-then-place task, while holding the exact target at the microwave, select the required heat action when it is currently offered; do not treat availability as a guarantee of success.
```

有效回源的独立配套 Diff（同一方案还含上述 u1 变化）：

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -5 +5 @@
-- During that multi-instance search, when a location is visibly empty or an object there has already been moved, go to a different not-yet-inspected receptacle rather than immediately re-checking the same empty container; do not cycle among a small set of already-inspected locations.
+- During that multi-instance search, avoid immediate uninformative revisits to a location currently or recently observed empty; removing one object does not establish that the source is empty.
@@ -6 +6 @@
-- After delivering one instance to the destination, resume the sweep for the next instance from unvisited receptacles instead of stopping at one or rechecking emptied ones.
+- After delivering one instance, return to a source if current or recent observations show another exact instance there; otherwise continue searching for the remaining instances.
```

## R05

[归档原始来源](../../../../artifacts/methods/v23_2/v23_2_diagnosis_construction_001_r05_retry_001/R05/attempts/001/diagnosis.json) · [原文精确副本](fixtures/R05.original.json) · [人工多行副本](fixtures/R05.multiline.json) · [人工 Patch 方案](fixtures/R05.scenarios.json)

### 原文到多行的对应

| 人工位置 | 原文来源 | 表示处理 |
|---|---|---|
| u1 L1 | 原第1句 | 具体位置覆盖与原 object/desklamp 作用域 |
| u1 L2–3 | 原第2句 | 未找到时移动与到达闭容器后的检查分行；各自条件和动作完整 |
| u1 L4–5 | 原第3句的两个关联要求 | 编号推进/禁止回返与穷尽后换类分行，保留原方向和前提 |
| u1 L6 | 原第4句 | 近期反循环触发及选择动作同一行 |
| u1 L7–8 | 原第5句 | 预算内找目标的目的与不替代约束分行 |
| u2 L1/L2/L3 | 原三个句子 | 保留信息价值、无效后禁重复、立即 state-changing；L3 展开“Instead”的触发范围 |

**完成边界来源不能混入 Original：** u1 没有“所有位置检查一次即结束”句。该句来自当前 Parent 的一般搜索规则；处理/交付与灯具保留还来自 Goal。它们在下面单列，未添入人工 u1 凑行。

### 决策与未解决问题

- `single` 只改 u1 L5 的类别切换条件；L1–4、L6–8 和整个 u2 不变。原 L4 回返限制以及 L2/L6 的 uninspected 前提仍有问题，不能以单行 Patch 通过宣布策略已完善。
- `linked` 协调 L4/L5：保留编号作为局部选择线索，允许有价值的同类实例和回返；探索更早换类但不宣称更优。L2/L6 仍需独立处理。
- `broad` 同改 L2/L4/L5/L6，利用当前/近期可见信息而非全局 visited 状态。L1 覆盖目的、L3 开容器、L7 预算目的、L8 不替代精确保留。Parent 中的全局完成边界没有因为 Update 未重述就自动消失，仍需独立决策与 Editor 落实，不能宣称本例完整解决。
- `cross` 另外收窄 u2 L2/L3 的禁重复/只许 state-changing，动机来自状态变化后重试及信息价值；不是 u1 调度变化的必需配套。
- `add` 用普通 Diff 新增可用动作要求，旧行全保留；`delete` 删除 L4，保留其他行，可能仍留下 L5 穷尽前提，故仅是表达能力验证。
- 正常方案没有由程序引入 `every receptacle type has been sampled once`。另两个**故意有问题**的测试把这一出口新增成行或塞入被替换行，原应用器、编译器和 Editor 纯接口都接受。这证明结构检查不能替代新承诺的独立语义评价。

M6 正例支持重新考虑探索机会；同类 countertop 实例遗漏、无效移动与晚获取限制推广范围。上述文本只是探索假设，不指定类内穷尽或跨类轮换为唯一正确算法，也不用后来的 M10 指导 R05。

Parent 的真实相关行（仅引用来源，不加入人工 Original）：

```text
1. Identify and search for the exact requested target. If it is not visible, search systematically: open any closed cabinet, drawer, or fridge immediately upon reaching it and inspect its contents before leaving. Do not immediately revisit an already-open receptacle that visibly lacks the target; choose a different uninspected candidate location instead. Do not repeatedly check inventory while carrying nothing. Continue until the exact target is found or all plausible candidate receptacles have been inspected once.
```

Original Goal 的后续任务要求（同样不搬入 u1）：

```text
Make search for the exact requested object coverage-oriented and step-efficient so the target is found, conditioned if required, and placed before the step budget is exhausted, without picking up, conditioning, or placing a substitute. Preserve the successful desklamp behavior (hold/co-locate the target and turn the lamp on at its receptacle), the direct acquire-then-place flow, and the correct clean/cool-then-place ordering already demonstrated.
```

### 人工多行表示全文

以下仍是原策略的表示副本，不是应用测试 Patch 后的文本。

**u1**（8 行）

```text
- During any search for the exact requested object (or for the desklamp once the target is in hand), treat the search as coverage of distinct candidate receptacles rather than a loop over a few.
- During that object or desklamp search, when the current observation shows the requested item is absent, move to a receptacle not yet inspected in this search.
- During that object or desklamp search, retain the existing rule to open a closed cabinet/drawer/fridge on arrival and inspect its contents.
- During that object or desklamp search, sweep a numbered series of same-type containers in one direction without returning to earlier ones.
- During that object or desklamp search, once that series is exhausted without the target, switch to a different receptacle type (e.g., from drawers to cabinets, countertops, fridge, shelves, or sinkbasin) before re-entering the series.
- During that object or desklamp search, use the most recent observations to notice when the next move would revisit a receptacle just left empty or repeat the same small set of locations, and in that case choose a different uninspected candidate.
- This is coverage for finding the exact target within the step budget.
- This search does not permit picking up, conditioning, or placing a substitute object.
```

**u2**（3 行）

```text
- Do not spend steps on actions that cannot change the world or reveal new information.
- If an action returns 'Nothing happens,' if a 'look' repeats the description you already have for the current receptacle, or if 'inventory' is issued while carrying nothing, do not repeat that action or an equivalent one.
- Following such a no-op, repeated-look, or empty-handed-inventory event, instead immediately take a state-changing action: move to a new uninspected receptacle, open a closed container, take the target, perform the required clean/cool/heat, or place the target at the destination.
```

### Patch 实际范围

| 方案 | 删除/替换的原行或新增行 | 未改行与边界 |
|---|---|---|
| single | u1: L5 | u1: L1,L2,L3,L4,L6,L7,L8；其余 Update、Goal、Checks 保持 |
| linked | u1: L4/L5 | u1: L1,L2,L3,L6,L7,L8；其余 Update、Goal、Checks 保持 |
| delete | u1: L4 | u1: L1,L2,L3,L5,L6,L7,L8；其余 Update、Goal、Checks 保持 |
| broad | u1: L2/L4/L5/L6 | u1: L1,L3,L7,L8；其余 Update、Goal、Checks 保持 |
| cross | u1: L4/L5；u2: L2/L3 | u1: L1,L2,L3,L6,L7,L8；u2: L1；其余 Update、Goal、Checks 保持 |
| add | u1: 末尾新增 L9 | u1: L1,L2,L3,L4,L5,L6,L7,L8；其余 Update、Goal、Checks 保持 |

每份方案独立从同一人工 Original 应用，不把 single 的结果继续交给 linked。实际应用输出与未改行的原/新坐标证据保存于 [tests.json](results/tests.json)。删除导致后续行号变化，不要求其新行号与旧行号相等。

关联行的实际 Unified Diff：

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -4 +4 @@
-- During that object or desklamp search, sweep a numbered series of same-type containers in one direction without returning to earlier ones.
+- During that object or desklamp search, use numbered instances as local choices without excluding another useful instance or a known useful return destination.
@@ -5 +5 @@
-- During that object or desklamp search, once that series is exhausted without the target, switch to a different receptacle type (e.g., from drawers to cabinets, countertops, fridge, shelves, or sinkbasin) before re-entering the series.
+- During that object or desklamp search, when recent same-type checks provide no target and another plausible destination is available, try a different receptacle type without requiring exhaustion of the current series.
```

## R06

[归档原始来源](../../../../artifacts/methods/v23_2/v23_2_diagnosis_construction_001/R06/attempts/001/diagnosis.json) · [原文精确副本](fixtures/R06.original.json) · [人工多行副本](fixtures/R06.multiline.json) · [人工 Patch 方案](fixtures/R06.scenarios.json)

### 原文到多行的对应

| 人工位置 | 原文来源 | 表示处理 |
|---|---|---|
| u1 L1/L2 | 原第1/2句 | 搜索策略与 consumed/下一位置限制分开 |
| u1 L3–4 | 原第3句 | 编号线索与需要 unvisited/全新类别的选择偏好分开，原问题保留 |
| u1 L5/L6/L7 | 原第4/5/6句 | 开容器与空时继续、早查表面、搜索结束与预算边界 |
| u2 L1/L2 | 原第1/2句 | 设备前提与 held/open 处理；条件与动作同处各行 |
| u2 L3–4 | 原第3句 | 不提供动作时放入的备用分支与禁止处理循环分开 |
| u2 L5/L6 | 原第4/5句 | 处理后交付及设备也是目的地时的顺序保留 |
| u3 L1/L2/L3–5 | 原第1/2/3句 | 顺序数量任务、继续取得剩余实例、三项独立边界分行 |

### 决策与未解决问题

- `single` 只改 u1 L2 的永久 consumed；`linked` 再改非相邻 L4 的全局 unvisited 选择，两个 Hunk 中间的编号线索 L3 不变。u2 的必要处理与交付完全不动。
- `broad` 修改 u1 L1/L2/L4/L5/L7，消除示例中若干全局进度推断，同时保留 L3 编号线索、L6 表面检查以及整个 u2/u3。它仅证明大范围可表达，仍不是验证过的搜索策略。
- `cross` 协调 u3 L2 的有效来源条件，使回源以当前/近期可得信息为前提；数量、精确类别及普通任务与灯具区别保持。
- `delete` 删除 u2 L3 的无据备用保证，不删同一 Update 的反循环、必要处理或交付；没有推断“放入在所有状态均失败”。`add` 是独立动作可用性要求。
- **Goal 仍含 `numbered receptacle names` 和 `at the open appliance`。** 保留编号线索的局部调整可表达；完全取消这些实现承诺必须由上游处理。纯编译/交接成功不证明 Goal 与所有新规则语义一致。

表示阶段没有把 Actor 的两步历史改成全局记忆，也没有把 M10 summary 当成唯一正确调度。具体效果仍需后续执行。

### 人工多行表示全文

以下仍是原策略的表示副本，不是应用测试 Patch 后的文本。

**u1**（7 行）

```text
- For tasks whose exact target is not initially visible, run a single forward search sweep that does not oscillate.
- During that search, treat each inspected receptacle as consumed; the next move should go to a different receptacle, ideally one not just inspected.
- During that search, use numbered receptacle names as a local progress cue.
- During that search, after checking an instance of a family, prefer the next higher-numbered unvisited instance or a wholly uninspected family or surface instead of jumping back to an earlier location.
- During that search, open each closed container once and read its contents; if it is empty, continue forward to a new receptacle rather than cycling back through earlier ones.
- During that search, include cheap surface checks (countertops, desks, beds, tables, shelves) early in the sweep.
- Continue searching until the exact requested category is found or all plausible receptacles have been inspected once, keeping within the step budget.
```

**u2**（6 行）

```text
- For tasks requiring the exact target to be cooled or heated, after acquiring the target, go to the required appliance (fridge for cool, microwave for heat) and open it if closed.
- For such cooling or heating, perform the cool/heat action directly on the held target while at the open appliance; holding the target is sufficient in the observed environment.
- If the conditioning action is not offered for the held target, place the target inside once and perform the action.
- During conditioning, never replace conditioning with repeated close/open or remove/reinsert cycles.
- Perform one conditioning action, then carry the target to the requested destination (opening it if closed) and place it there.
- If the conditioning appliance is also the destination, condition the target and then place it there.
```

**u3**（5 行）

```text
- For ordinary multi-instance placement requiring two or more instances of the exact category, deliver them sequentially.
- After placing the first exact instance at the destination, continue searching (from remaining uninspected receptacles or a known source) for another instance of the same exact category and repeat until the requested count is placed.
- For ordinary multi-instance placement, do not stop after one.
- For ordinary multi-instance placement, do not substitute a differently named near-match.
- Do not apply the desklamp rule of finishing with one co-located target to ordinary multi-instance put tasks.
```

### Patch 实际范围

| 方案 | 删除/替换的原行或新增行 | 未改行与边界 |
|---|---|---|
| single | u1: L2 | u1: L1,L3,L4,L5,L6,L7；其余 Update、Goal、Checks 保持 |
| linked | u1: L2/L4 | u1: L1,L3,L5,L6,L7；其余 Update、Goal、Checks 保持 |
| delete | u2: L3 | u2: L1,L2,L4,L5,L6；其余 Update、Goal、Checks 保持 |
| broad | u1: L1/L2/L4/L5/L7 | u1: L3,L6；其余 Update、Goal、Checks 保持 |
| cross | u1: L2/L4；u3: L2 | u1: L1,L3,L5,L6,L7；u3: L1,L3,L4,L5；其余 Update、Goal、Checks 保持 |
| add | u1: 末尾新增 L8 | u1: L1,L2,L3,L4,L5,L6,L7；其余 Update、Goal、Checks 保持 |

每份方案独立从同一人工 Original 应用，不把 single 的结果继续交给 linked。实际应用输出与未改行的原/新坐标证据保存于 [tests.json](results/tests.json)。删除导致后续行号变化，不要求其新行号与旧行号相等。

关联行的实际 Unified Diff：

```diff
--- a/SKILL.md
+++ b/SKILL.md
@@ -2 +2 @@
-- During that search, treat each inspected receptacle as consumed; the next move should go to a different receptacle, ideally one not just inspected.
+- During that search, avoid immediate uninformative revisits using current and recent observations; do not treat an inspected source as permanently unavailable.
@@ -4 +4 @@
-- During that search, after checking an instance of a family, prefer the next higher-numbered unvisited instance or a wholly uninspected family or surface instead of jumping back to an earlier location.
+- During that search, after checking one instance, use currently available numbered destinations and recent observations to consider another plausible instance or family without assuming a global visited set.
```

## 共同验收边界

- 18 份人工方案均经原 apply_patch → 显式原 Adjustment → 原 compiler → Editor 纯输入/消息函数验证；另有每例混合增删替换坐标、失败、格式、撤回/Checks 等测试。结果为 [119 项通过](P1R_PATCH_COMPATIBILITY.md)。
- 未改行逐字节保留，不代表它们本来正确；修改行可能夹带多个新承诺，也不因“只改一行”而天然合理。
- Goal、其他 Updates、Checks 的保留与合法替换属于结构验证。这里没有原始模型响应解析、持久化 loader/runner、Editor 生成或真实执行，不能称作 P2 集成完成。
- 三例均为已参与设计的开发案例；本轮仅确认机制可表达和可检查，不构成泛化、因果效果或成功率证据。
