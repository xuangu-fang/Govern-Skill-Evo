# V26 OfficeQA

V26 沿用 V24/V25 的自进化机制，适配 OfficeQA。

- [步骤 1：继承范围、源版本和恢复规则](INHERITANCE_SCOPE.md)
- [步骤 2：已实现的事实与证据协议、执行桥接及离线验收](FACTS_EVIDENCE.md)
- [步骤 3：七模块 OfficeQA Prompt、逐处修改原因与离线验收](PROMPT_MIGRATION.md)
- [步骤 4：七模块调用、持久化恢复与 Campaign 主循环](CAMPAIGN.md)
- [步骤 5：固定 172 题的独立 Test 执行、恢复与报告](EVALUATION.md)
- [SkillOpt / SkillAdam 正式训练 launcher 与五组统一测试](../../benchmarks/officeqa/NATIVE_LAUNCHERS.md)
- [OfficeQA 专用无损输入视图、长度测量与证据边界](LOSSLESS_INPUT.md)

当前已完成事实/证据适配、七模块 Prompt、模块调用与持久化恢复、Campaign 主循环、最终 Skill 核验、成本统计及独立 Test 执行／恢复／报告。Campaign 命令行支持 `run --resume --archive-only`：无需模型凭据或生成器，只恢复已有归档，遇到需要新请求的步骤停止。仅做离线固定响应验收，没有运行真实模型或启动 V26 实验；正式运行参数与对应规模的输入容量验收仍待完成。

正式训练已确定的部分：原 Train 50 题与 Validation 24 题合并为 74 题优化池；初始 Skill 使用 SkillOpt OfficeQA `initial.md`，不引入 Stage0；Gate 按 EM=1 计成功，仅在 Candidate 成功数严格增加时 ACCEPT。见 [配置选择记录](../../../experiments/configs/v26_officeqa_training_selection.json)。模型、输出额度、批次、epoch 等参数仍留待明确；172 道独立 Test 题不变。
