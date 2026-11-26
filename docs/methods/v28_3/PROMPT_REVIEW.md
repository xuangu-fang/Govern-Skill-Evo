# v28.3 提示词来源与审阅说明

状态：四份已审阅 Prompt 原文保持不变，已由独立 v28.3 运行时绑定。Editor 调用预算按用户最新要求由 16,384 改为 32,768，不修改 Prompt 内的 Actor 协议。

## 方法来源

| Prompt | 方法来源 | 本次处理 |
|---|---|---|
| [Diagnosis](prompts/diagnosis.md) | v29.4 Diagnosis | 保留直接跨执行比较、原 Update 构造指导和输出；替换为 SearchQA 证据、Actor、评分及任务语义 |
| [Preconditioner](prompts/preconditioner.md) | v29.4 Preconditioner | 保留 D/S/C、历史调整、整条 KEEP、全文 REPLACE/WITHDRAW；适配当前 context 可见而历史原始 context 不可用 |
| [Editor](prompts/editor.md) | v29.4 继续采用的 v29.2 Editor | 使用已有 v28.2 SearchQA 适配文本，逐字保留；调用预算设置 32,768，Actor 预算仍为 32,768 |
| [Replay](prompts/replay.md) | v29.4 继续采用的 v29.2 Replay | 使用已有 v28.2 SearchQA 适配文本，逐字保留；EM-only 事件规则不变 |

Diagnosis/Preconditioner 的方法主体来自本目录 baseline 中的 v29.4 副本。SearchQA 的通用证据边界和 Actor 协议可复用 v28.2 中未改变 benchmark 事实的段落，但不导入其 v2 方法主体。来源路径、绑定身份与差异见 [source_map.json](source_map.json)。

## 逐项审阅结论

1. **没有隐含 Grouping**：Diagnosis 直接分析完整批次，不生成中间分类报告；JSON 示例没有 G 引用。合同仍要求校验器识别并拒绝旧 Group 来源。
2. **保留 v29.4 的提案自由度**：保留 independently justified/actionable、必要依赖、合理单案例试验、no_change 和无固定 Update 数量；不引入按预期成败/去留划分的要求，也不整体带入 v28.2 v2 替代段落。
3. **可见证据正确**：可核对当前 question/context；不能把 passage 的存在当成 Actor 使用证据；不把 DocVQA 图片不可见的限制迁入文本任务。历史 raw context 不因当前 context 可见而获得访问权。
4. **评分解释正确**：EM/F1 使用 SearchQA 归一化，F1 不投票；冠词和标点变化不直接等于 EM 翻转；参考形式差异不自动证明实体错误或通用名称偏好。
5. **职责和传递完整**：Diagnosis reason 不传下游；Plan 中的直接引用选择完整执行，basis 承载关键支持；Editor 只读 goal/id/text；实施条件不能依赖 reason。
6. **历史和归因不变**：事件、Update 关联与 Gate 决策分开；Replay 只见当前 EM 翻转；无法明确关联时用 null；历史不改写。未增加成功保持类别或其他新字段。
7. **预算不混淆**：Prompt 引用的 32,768 是 Actor 预算；方法调用额度由设计配置决定，Editor 是 32,768，另三模块是 65,536。

## 静态检查与后续工作

本次检查 Prompt 数量、基线差异、Actor 原文、JSON 示例、输入/输出字段、预算与引用说明、文档链接、旧源文件原文保持和暂停状态。记录在 [design_validation.json](design_validation.json)，不调用模型、不导入 campaign 执行器、不做训练或 Test。

独立事实入口、引用拒绝、四阶段接线、版本隔离和恢复已实现，并以合成记录验收，结果见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。结构通过不能证明模型合理组织 Update、正确归因或提高测试成功率。本轮不把 v28.2 两轮实验中的具体答案编入 Prompt，也不根据它们额外增加通用名称规则。
