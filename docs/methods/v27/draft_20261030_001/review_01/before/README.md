# v27 实现前设计与 Prompt 草稿

2026-10-30，待审阅。以 v26 为工程与结构契约底稿，保持 v24.1／v25／v26 的主要模块机制，针对 LiveMathematicianBench 单独设计数据、Actor、证据和提示词。本文档包不创建运行代码、数据视图或实验配置。

阅读入口：

1. [模块迁移清单](MIGRATION.md)：源文件、保留语义、LMB 适配和未来目标位置。
2. [数据与证据契约](CONTRACTS.md)：53／124、六批次、输入权限、模块 schema、状态及评分边界。
3. 五个完整英文 system Prompt 草稿：[Grouping](prompts/grouping.md)、[Diagnosis](prompts/diagnosis.md)、[Preconditioner](prompts/preconditioner.md)、[Editor](prompts/editor.md)、[Replay](prompts/replay.md)。每份均包含完整 LMB 执行说明，无需隐式附加旧 benchmark Prompt。
4. [离线验收清单](OFFLINE_ACCEPTANCE.md)：未来实现的场景、预期结果和验收证据。本清单尚未执行。
5. [来源与文件哈希](source_manifest.json)、[文档检查结果](document_checks.json)。后者只检查文档，不代表运行实现通过验收。

已确定的范围：当前内容 revision `6f53c5ff7227633ea954b2847cd590314d582047`；SkillAdam 35 Train＋18 Selection 合并为 53 题优化，124 Test；顺序批次 10/10/10/10/10/3；SkillOpt 原生 `initial.md`；不运行 Stage0；不将 `reasoning_content` 直接或间接送入优化模块；Verifier／Repair 首版关闭。

所有数学判断、条件、强度及行为比较说明都来自 LMB 的任务特点和证据条件，不作为从 v24.1 移植领域要求的理由。版本一致性指职责、主要实现和输出契约一致，不要求不同 benchmark 的 Prompt 逐字相同。

Prompt 使用方式：未来每次调用以对应文件全文作为 system，以 CONTRACTS.md 定义的模块投影 JSON 作为 user。只允许附加已有输出校验反馈策略规定的临时消息；反馈不得包含原始响应隐藏字段。五份 Prompt 不进行相互拼接，也不附加原 OfficeQA execution_context。Preconditioner／Replay 已内置 Knowledge Only 规则。示例仅说明格式，不是样本证据。

建议评审顺序为契约→Preconditioner→Editor→Grouping／Diagnosis→Replay→验收清单。审阅完成后才进入独立实现阶段；本包不包含启动实验的命令。
