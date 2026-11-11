# R05 Preconditioner 对照结果

同一份实际用户消息、调用配置和历史 Memory。系统提示词只替换一段。首次模型回复通过现有验证。

| Original | 原正式训练 | 新版快检 |
|---|---|---|
| u1，避免回访 | WITHDRAW | WITHDRAW。Parent 已覆盖，当前失败也没有触发 inventory 兜底。 |
| u2，首遍优先未采样类别 | REPLACE | KEEP。交给 Editor 的有效文字逐字等于 Original。 |

新版引用 M2/M6 的收益和 M3/M4 的退步，并将退步解释为 Actor 未遵守继续搜索及防回访条件。但它没有给出在同类新位置与异类新位置均可选时应保护同类推进的条件，也没有给出 Actor 在历史退步中能够进入并执行后续兜底的依据。新版保留了 Original 的示例列表及 cabinet/drawer 合写，原正式版则把两类分列并扩展了示例，所以两版有效文本不同。在目标决策上两版都优先去未采样类别。

本次条件是先出现有实质差异的 REPLACE，再做十题实跑。本次没有满足条件，未构建 Candidate 或进入 Gate，不能给新版填入原版的 8/10。结果只说明第一次同输入快检未产生预期的行为区分。保留修订供审阅，正式训练默认仍指向 historical_attempt。

[新模型输出](../../../../../artifacts/methods/v24_4/v24_4_alfworld_r05_gain_regression_20261107_1637/preconditioner/result.json) · [原正式训练输出](../../../../../artifacts/methods/v24_4/v24_4_alfworld_retained_20261107_135247/rounds/R05/preconditioner/result.json)
