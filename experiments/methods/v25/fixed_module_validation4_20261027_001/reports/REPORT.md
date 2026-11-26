# 四份固定输入真实模型验证结果

**结果：Editor 正反案例符合预期；Diagnosis 和 Preconditioner 的评分/任务要求边界问题仍未解决。**
四份输出均通过原生结构校验，这不代表四份语义都正确。自检范围修订的效果，本批覆盖不足，不能宣布通过。

## 输入与运行

| 案例 | 输入性质 | 最新 Prompt | 请求数（含截断） | 首请求输入 tokens | 所选输出 tokens |
| --- | --- | --- | ---: | ---: | ---: |
| Diagnosis R05 | `_007` 完整原始首请求 | self_check_scope_v3 | 3 | 107,433 | 12,115 |
| Preconditioner R04 | `_007` 完整原始首请求 | self_check_scope_v6 | 2 | 42,714 | 18,033 |
| Editor R05 | 已冻结的真实反例 | scope_fidelity_v2 | 1 | 5,915 | 6,200 |
| Editor 显式默认策略 | 已冻结的人工正例 | scope_fidelity_v2 | 1 | 5,880 | 5,153 |

API/model 为原实验的 `deepseek-v4.1-flash` 路由，保留 temperature=1、medium reasoning、thinking enabled、300 秒请求超时；Diagnosis/Editor 输出上限 16,384，Preconditioner 为 32,768。输出 tokens 包含推理用量。

共 7 次请求，3 次截断（Diagnosis 2 次、Preconditioner 1 次），其余 4 次完整输出均直接通过结构校验，没有格式纠错重试或语义重采样。已知总用量：输入 **419,522**、输出 **107,037**、合计 **526,559 tokens**。此处总量包含截断请求，仅供审计，不作为新旧质量或成本优劣结论。

## 逐项判断

### Diagnosis：任务要求边界未修复

[新输出](../../../../../artifacts/methods/v25/analysis/fixed_module_validation4_20261027_001/diagnosis_R05/diagnosis/attempts/003/raw_output.txt) 的 u1 一面要求保留真实公式，一面写道：

> keep a real formula in the cell rather than replacing it with a static value; use a computed literal only as a fallback if the cached-value path cannot be made to work

这仍允许因缓存实现失败而删除任务所需公式，未限制为任务允许常量的情况；Goal 和 c1 又要求公式保留。与旧输出相比，核心矛盾仍存在，不能判为改善。

有用内容未整体丢失：公式加缓存、保存值/公式存在性检查、条件匹配、跨表查询及无评分反馈的执行边界仍被保留。新输出未明确宣称回读等于全面正确，但该输入没有针对“错算值回读一致”的完整控制案例，不能用这一点证明自检范围修订有效。

额外观察：reason 把 P12 的 106 个评分差异单元格称为 106 个未解析键；评分差异数不能单独证明未匹配键数量。本批只记录该证据推断风险，没有把它包装为已经定位的另一项机制缺陷。

### Preconditioner：引用格式正常，任务要求边界未修复

[新输出](../../../../../artifacts/methods/v25/analysis/fixed_module_validation4_20261027_001/preconditioner_R04/preconditioner/attempts/002/raw_output.txt) 正确使用 `Evidence:...`、`Memory:...` 显式引用，普通单元格/工作表文字没有触发误判，首份完整输出通过校验。这支持引用修复在本案例可用；不代表所有引用形态均已通过真实模型验证。

但[编译后的计划](../../../../../artifacts/methods/v25/analysis/fixed_module_validation4_20261027_001/preconditioner_R04/preconditioner/attempts/002/effective_plan.json) 保留了：

> This applies even when the task is phrased as 'create a formula'

同时新增“回读不符就改写为普通计算值”的强制步骤。模型没有收窄违规 fallback，而是强化了它。这是可以调整的 u1 正文中的问题，不是仅由不可修改的旧 Goal 导致。

合理建议仍有保留：缓存源值读取、保存后检查、明确列分配优于相反示例行、保护无关内容。旧输出关于“输入改变后重新计算受影响缓存”的提醒未保留；这属于附加差异，本批不要求机械复现旧输出的全部扩展。

### Editor：反例改善，正例也保留明确要求

[反例新输出](../../../../../artifacts/methods/v25/analysis/fixed_module_validation4_20261027_001/editor_R05/editor/attempts/001/candidate.md) 保留“某次观察中返回 0”的例子表达，没有再次改写为数值列的默认规则；任务/列语义允许空白的例外也保留。原输出的目标问题在本样本中消失。

[正例新输出](../../../../../artifacts/methods/v25/analysis/fixed_module_validation4_20261027_001/editor_explicit_default/editor/attempts/001/candidate.md) 则明确写入数值无匹配时填 0，并保留空白例外，未因新增约束而把明确要求弱化成选项。两份补丁均只新增章节，原 Parent 内容保留，其他 Effective Plan 建议也保留。

注意：两份固定 Effective Plan 原本就含公式 fallback 矛盾，Editor 仍复现了它。Editor 的职责是实现 Plan，因此不把这一继承问题归为新的 Editor 强化错误，也不因此宣称生成的整份 Skill 已正确。

## 完整性与解释限制

- `criteria.json` 在模型调用前冻结，人工评价标准不进入请求；没有额外模型评审。
- 三份真实输入的用户消息字节内容与原归档一致，正例只采用此前冻结的人工输入。
- `request_audit.json` 验证每次请求与保存消息、调用配置一致，技术重试不改变基础输入。
- 原始归档哈希、冻结输入/Prompt/生产代码检查通过；完整请求、HTTP 响应、响应对象、原始输出及重试错误均保存。
- 本批只验证四份固定输入，没有运行 Actor、Gate、完整训练或发布 Memory。
- 每份仅一份完整合法输出，旧基线可能经历不同格式重试；不能据此给出训练收益、成功率提升或 Prompt 因果结论。
- 四个局部自检观察没有全部转成模块请求，本次只能检查真实公式回读场景，不能报告自检修订全面通过。

**建议：保留 Editor 的这次正向证据；不要把本版 Diagnosis/Preconditioner 视为已经修复任务要求边界。是否继续局部调整应基于上述明确失败输出决定，本次未修改生产 Prompt。**
