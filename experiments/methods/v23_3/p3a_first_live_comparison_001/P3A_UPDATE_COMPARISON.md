# P3-A：Original 与 A/B 可比较性

**本轮没有 A 或 B 的实际模型输出及 Effective Plan，无法进行更新语义优劣对照。** 下面明确区分真实 Original、独立评价中的缺失观测，以及不能作出的推断。

## 已获得的真实 Original

完整文本见 [original_plan.json](config/original_plan.json)，未经人工修改。与研究相关的 u2 原文为：

> - When the exact target has not been found after checking several receptacles of one type, expand the search to at least one still-unexamined receptacle of a different type before rechecking any location that was already opened or seen to lack the target.
> - Include visible open surfaces such as tables, countertops, shelves, and sidetables in the search, not only closed drawers or cabinets.
> - If an opened receptacle visibly lacks the target, leave it and choose a different uninspected candidate from the current admissible list; do not cycle back through the same already-inspected containers.

这是真实模型提出的三条行为要求，分别涉及调度、候选范围和回访约束。其粒度可比较，但 `still-unexamined/uninspected/already-inspected` 的全程状态含义仍需处理；Actor 只有当前与最近两组记录，动作候选不是访问过的集合。该问题在 Diagnosis 门记录时已经指出，没有看到 A/B 后才增加评价标准。

当前证据确有搜索循环与扩展机会：P3:8/9 返回已打开的 drawer1/2；P8:14—16 在 countertop 和多个已检查 cabinet 之间来回；P10:32 才到 diningtable 并见到 apple。但这些事实并不证明 u2 的跨类别安排一定优于同类别另一实例。

历史 M6 的实际 S1_R03/diff 将避免近期循环、扩展其他位置和预算偏好与其他指导联合加入；S1_R03/Q4:12/13/17 的 diningtable 发现并完成与 P4:50 失败形成正例；P2:15/16 找到 countertop3 的 bread，而 Q2 循环并未到该实例、Q2:50 失败，限制类别级推论。这些来源已在两组共同 Memory 中，**只说明可用证据是什么，不代表本轮 Preconditioner 已使用它**。

另外两项 Original：

| Update | 实际内容 | 当前证据及未评价边界 |
|---|---|---|
| u1，3 行 | 不操作相近替代对象；容器无匹配目标时继续搜索；非目标处理/交付不算进展 | P7:5 取 knife、7 clean knife、9 放 knife，而任务要 butterknife；足以支持当前纠错。历史 M8 可加强相关认识，但本轮未观察到模型使用它 |
| u3，2 行 | 命令须在当前候选中；导航不可用而直接操作可用时用适当直接操作 | P6:20 非法 go drawer5 后，21 合法 open drawer5；P8:5/6 类似。这是当前证据可支持的规则，不需先归功 Memory |

来源为 [共同输入](config/common_payload.json) 内的 runs、memory.sources 和冻结 Actor 背景。没有加入未来 M10，也没有用历史总体成功率为某种调度背书。

## 先独立评价，再比较

已按预注册分别落盘 [A 独立评价](evaluations/A_independent.json) 和 [B 独立评价](evaluations/B_independent.json)。每份都单独依据该组请求/错误作结论，不使用另一组表现改标准。由同一分析者完成，不声称双盲或第二模型评价。

两份记录的六个语义栏目均为“无可观察输出/不可评价”，而不是零问题或通过：

- 有效更新：不可观察。
- 合理但未验证探索：不可观察。
- 证据足以纠正但未修正的问题：不可评价；不把 Original 的旧问题算作一次未产生输出的方法错误。
- 新增无依据承诺：不可观察，数量为未知，不能记零。
- 必要行为保留：不可观察。
- 实际效果：未执行。

## A/B 对照表

| 维度 | A：自由替换 | B：Patch |
|---|---|---|
| 技术有效性 | 3 次连接故障，无模型响应 | 3 次连接故障，无模型响应 |
| Adjustment / Patch 应用 | 未进入解析或编译 | 未得到 Patch，未进入应用或编译 |
| 实际修改对象与行 | 无实际更新可记录 | 无实际 Patch 行可记录 |
| 历史响应利用 | 已提交相同 Memory；是否使用不可观察 | 已提交相同 Memory；是否使用不可观察 |
| 更新条件与强度 | 不可评价 | 不可评价 |
| 无依据附带承诺 | 未知，不是零 | 未知，不是零 |
| 有效行为保留 | 不可评价 | 不可评价 |
| 具体策略探索 | 不可评价 | 不可评价 |
| Keep / 合法停点 | 没有返回语义决定 | 没有返回语义决定 |
| 实际行为收益 | 未执行 | 未执行 |

不能把两组相同的传输失败解释为方法等效，也不能因为 B 缺少全文重写输出就称其附带承诺更少。P2 的 Patch 兼容结果不能替代本轮缺失的真实模型比较。

## 对核心问题的三个分项回答

**更新粒度：** 真实 Diagnosis 确实形成可独立判断的多行 Original；尚未观察到 B 实际按行修改，因此不能确认本轮实际编辑粒度优于 A。

**历史响应参与：** 两组请求包含同一真实历史编辑—响应材料，但未收到决定文本，无法确认历史是否参与实际变换，更无法估计 Memory 因果增量。

**策略构造质量：** 没有 Actual Effective A/B，无法判断改善、退步、持平或探索能力差异。当前结果属于无有效配对，不属于四种有输出策略对照中的任一种。
