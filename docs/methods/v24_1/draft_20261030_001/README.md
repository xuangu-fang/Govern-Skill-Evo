# v24.1 四模块 Prompt 草案

2026-10-30 草案，经第二次审阅修订。以已准备的“后来那版 Preconditioner、训练并发 10、关闭 Verifier/Repair”v24 配置为基线，改进从执行事实到合理更新、再到历史经验的判断方式。v25 是设计参考，不是已验证更有效的标准答案。

这组文件供审阅，未接入运行代码。旧 v24、v25、实验配置和结果均未修改；没有调用模型、运行环境 episode 或启动训练。当前 v24 的 Diagnosis 校验仍允许 `need_evidence`，不能仅替换 Prompt 就宣称已实现 v24.1 的两种决策。

复审结论及修订原因见 [SECOND_REVIEW.md](SECOND_REVIEW.md)。第一版 Prompt 已单独留档，当前 `prompts/` 为复审后的完整文本。

## 阅读顺序

| 模块 | 完整英文草案 | 中文逐项说明 | 原文与逐行差异 |
| --- | --- | --- | --- |
| Diagnosis | [diagnosis.md](prompts/diagnosis.md) | [D1 至 D9](CHANGES.md#diagnosis) | [基线](baseline/diagnosis.md) · [diff](diffs/diagnosis.diff) |
| Preconditioner | [preconditioner.md](prompts/preconditioner.md) | [P1 至 P4](CHANGES.md#preconditioner) | [基线](baseline/preconditioner.md) · [diff](diffs/preconditioner.diff) |
| Editor | [editor.md](prompts/editor.md) | [E1](CHANGES.md#editor) | [基线](baseline/editor.md) · [diff](diffs/editor.diff) |
| Replay | [replay.md](prompts/replay.md) | [R1 至 R4](CHANGES.md#replay) | [基线](baseline/replay.md) · [diff](diffs/replay.diff) |

[人工审阅案例](REVIEW_CASES.md)同时检查过度激进和过度保守。这些是假设情境和判断边界，不是模型测试结果，也不进入生产 Prompt。

## 基线与范围

基线配置为 [campaign.json](../../../../experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001/config/campaign.json)。四份 `baseline/` 文本取自该配置实际选择的反馈版 Prompt，并与其 [source_contract.json](../../../../experiments/methods/v24/alfworld_history_and_plan_v3_no_review_workers10_20261029_001/config/source_contract.json)逐字核对。

| 项目 | 本草案的处理 |
| --- | --- |
| Diagnosis | 拟采用 `revise`、`no_change`；其余字段与引用结构保留 |
| Preconditioner | 保留历史经验与当前 Plan 审查、D/S/C、KEEP、修改、撤回和原引用契约 |
| Editor | 保留 Parent 加 Effective Plan 输入及无行号 diff 输出 |
| Replay | 保留七字段输入、已验证配对、Knowledge Only、原输出与历史替换规则 |
| Verifier/Repair | 基线已关闭，继续关闭；模块内部自检不新增调用 |
| Grouping、Actor、Gate | 不属于本次改动范围 |
| 数据与运行参数 | 仍以相同数据、初始 Skill、批次、并发、预算和重试作为未来配置约束 |
| 输入表示 | 不迁移 v25 的显式类型引用、消息共享或代码去重 |

未来若比较 v24 与 v24.1，应使用相同的并发 10、无审查基线条件。已完成的旧正式 v24 实验使用了不同并发和审查设置，其成绩不能直接隔离这四模块修改的效果。

## Prompt 组成

`prompts/` 保存完整模块模板，不是节选。它们继承基线中的格式修正说明，未增加语义重采样机制。

- Diagnosis、Preconditioner、Editor 各保留唯一的 `{{execution_context}}` 占位符。
- [execution_context.md](context/execution_context.md)是未修改的 ALFWorld 上下文模板；未来仍应由实际配置渲染最大步数和 Actor 模板。它描述当前观察、候选动作及最近两组观察/动作历史，不授予完整历史、持久笔记或隐藏状态访问能力。
- Preconditioner 在渲染模块模板后，仍追加 [knowledge_only_view.md](context/knowledge_only_view.md)。
- Replay 模块正文没有上下文占位符；仍按原方式追加渲染后的执行上下文，再追加 Knowledge Only 说明。
- 这些附加资源单独保存，供核对原有输入边界，不是新的模块或额外生成步骤。

中文差异说明、案例、版本状态和验收说明都不应拼入模型 Prompt。逐行 diff 是审阅材料，不是给 Preconditioner 或 Editor 的补丁输出示例。

## 修改幅度

下表按空白分词计数，不是 tokenizer token 数量，也不代表延迟或质量结果。附加执行上下文和 Knowledge Only 文本未计入，两边使用相同资源。

| 模块 | 基线词数 | 草案词数 | 净变化 |
| --- | ---: | ---: | ---: |
| Diagnosis | 1751 | 2034 | +283 |
| Preconditioner | 3479 | 3398 | -81 |
| Editor | 1114 | 1162 | +48 |
| Replay | 2390 | 2731 | +341 |

Diagnosis 的增量主要用于修复假设、正文边界和两种决策；Replay 的增量主要用于行动机会形成及 Knowledge 保真。Preconditioner 保留现有主体，合并重复说明后略短于基线；Editor 限于一段澄清。后续审阅依据判断内容是否必要，不以 Prompt 更长、更严格或更谨慎作为改进证明。

## 后续实现边界

审阅通过后，另行实现独立的 v24.1 版本和新配置；本草案不修改旧模块的默认版本或续跑资格。需要同步处理 Diagnosis 枚举校验、`no_change` 调度、按版本读取旧归档和新版本冻结，不能只换系统提示词。`no_change` 表示本轮未形成合理更新；保持 Parent/Memory，按已确认基线的 `continue_no_change=true` 进入下一批。技术或格式错误不能伪装成 `no_change`。

原有结构、引用、补丁和 Memory 提交校验继续保留。Preconditioner 全部 KEEP 仍进入 Editor，全部合法撤回才没有 Effective Plan；Editor 的 null patch 仍表示实现阻塞，不改变其处理方式。当前草案未授权或启动任何上述实现。

文件来源及摘要见 [source_manifest.json](source_manifest.json)，本地一致性核对见 [review_checks.json](review_checks.json)。这些核对只说明文稿和来源的一致性，不证明模型语义效果或任务成绩提升。
