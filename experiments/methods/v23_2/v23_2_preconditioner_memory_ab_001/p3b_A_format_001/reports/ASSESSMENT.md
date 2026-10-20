# 合法A的内容核查与比较边界

## A本身

A完整保留原u1/u2。reason声称：

> the numbered-series/type-switch heuristic makes the coverage requirement implementable with the Actor's two-step history

但最终u1仍要求识别“not yet inspected in this search”、类内编号序列耗尽后再换类。两步近期历史与编号线索不自动提供全局访问/耗尽状态，reason没有证明所有决策点都可恢复该状态。不能因其自称executable就判定能力问题已解决；编号探索本身仍可作为有条件的新策略，而非一概错误。

u2仍保留`do not repeat that action or an equivalent one`和`Instead immediately take a state-changing action`，未明确状态/动作前提改变后的重试与有价值信息获取边界。当前P1:4、P7:11/12、P8:39和P10:25已可支持这一边界审查，不需要历史Memory才能提出。开头允许“reveal new information”，所以也不能夸大为全面禁止信息动作。

Goal保留精确对象、必要处理交付、desklamp等要求；没有新增行为条款，也没有解决原有约束之间的潜在冲突。Checks原样保留，不能视为Actor额外执行的补救指令。

Keep本身合法，并非必须Adjustment；本次具体可执行性论证仍不足。没有Editor或Replay，不判断实际Skill行为好坏。

## 与旧B仅作描述性对照

| 项目 | 新格式A | 原Prompt B |
|---|---|---|
| Prompt | 原Prompt加字段/引用格式说明 | 原冻结Prompt |
| Memory | 空 | M1/M2/M3/M6/M7/M8/M9及sources |
| u1 | 保留类内编号穷尽及之后换类 | 改为跨类型采样/近期去重；附带其他类型采样后才回同类，以及types或locations一次结束 |
| u2 | Keep | Keep |
| Goal/Checks | 保持Original | 保持Original |

B的变换与历史M6/M3的混合响应有显式联系，但only-after和类别/位置一次终止仍有支持不足。新A不调整、旧B调整是实际文本差异；由于Prompt与Memory同时不同，**不能将差异归因于Memory**。原[B历史依据核查](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_MEMORY_ATTRIBUTION.md)保持为独立分析。

## 为什么原B成功、原A连续失败？

已确认原A/B的system、模型、参数相同；原请求未启用服务端结构化Schema约束，依赖自然语言格式要求与事后校验。A的四次完整输出均把basis/reason放进to条目，说明重复的字段映射问题；输入Original Update含basis而replacement不含basis，是可能的混淆来源。B单次成功只能说明相同契约可以被遵守，不能证明Memory保证结构正确。

上下文内容/长度、采样随机性、调用时点可能影响输出；本实验没有隔离这些因素，不能指定唯一内部原因。首次A超时不是格式失败。第四次A首先还遇到斜杠当前引用被历史正则识别的问题，但其字段层级与空外层依据独立不合法。

本次成功走的是空adjustments分支，没有生成to对象。因此它既不证明格式补充导致成功，也不证明原字段错位问题已可靠解决；更不能将格式通过误称为策略构造或Memory机制通过。
