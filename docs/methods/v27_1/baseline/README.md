# v27.1 设计来源快照

这些文件是 2026-11-04 编写设计稿时的原文字节副本，仅用于来源核对与差异审阅，不是第二套运行资源。准确源路径在 [source_files.json](source_files.json)。

- `v29/`：v29.4 Diagnosis/Preconditioner，以及其沿用的 v29.2 Editor/Replay。
- `v28_3/`：四份直接适配底稿。
- `lmb/`：原 Actor 基础协议、原初始 Skill、最近完成 v27 的 65,536 训练配置、原 SkillAdam 成员 ID。

历史训练配置仍含 Grouping、旧合同和旧 Editor 预算；不能交给未来 v27.1 CLI。v27.1 拟用参数见 [experiment_plan.json](../experiment_plan.json)，该文件本身也不是可执行配置。

这些快照不包含 API 凭据、题目正文、参考答案或模型响应。上游文件今后改变时，快照仍保留本次设计来源，不自动覆盖。
