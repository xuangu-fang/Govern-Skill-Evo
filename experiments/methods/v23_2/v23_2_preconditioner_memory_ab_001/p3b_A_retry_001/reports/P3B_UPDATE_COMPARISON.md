# 补充后的比较可用性

**A重试取得文本，但契约失败，不能将其to.text当作Effective Update。正式A/B对照仍未完成。**

| 对象 | A授权重试 | B原有合法结果 |
|---|---|---|
| reason | 声称当前P6长drawer搜索耗预算、P3扩展到其他位置后成功，拟调整u1 | 引用当前执行及M6/M3历史混合反馈，调整u1 |
| u1有效结果 | 无：非法Adjustment未进入原编译器 | breadth-first跨类型采样、近期去重，并增加only-after及types/locations一次结束要求 |
| u2有效结果 | 无；原文声称保持，不能当已编译Keep | 保持Original |
| Goal/Checks | 无有效编译产物 | 均保持Original |

## A原始文本的诊断性记录（不纳入有效对照）

A原文提出：

> after a short bounded run of that series, switch to a different receptacle type

以及：

> then continue the series only if other types have been covered

它仍使用`not yet inspected this search`等全局进度条件；short bounded run没有规定具体2/3次。原文声称u2保留，未给状态改变后重试的明确修正。这些只用于记录非法响应的内容，不能声称已构造合法策略，也不能把reason中的轨迹概括直接当成核验事实。

本次无Memory原文也提到跨类型探索，因此“提到跨类型探索”本身尤其不能作为Memory使用的充分判据。但这不是有效A/B策略对照，更不能用它估计Memory增量。

## B的独立评价保持不变

B的跨类型探索有问题动机，局部recent-history去重可由当前证据支持；但`Return ... only after other ... sampled`和`all plausible candidate types or locations ... once`仍有依据不足、全局进度与潜在过早停止风险。u2没有明确状态变化后重试边界。没有Actor执行，不能说风险已经导致失败。

完整Original/B文本和既有独立核查见[原始对照报告](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_results/reports/P3B_UPDATE_COMPARISON.md)。A原文完整保留于[本次无效响应](/Users/didi/Desktop/Govern-Skill-Evo/experiments/methods/v23_2/v23_2_preconditioner_memory_ab_001/p3b_A_retry_001/runs/A/raw_output.txt)。既有报告反映首次运行时状态，未被重写。
