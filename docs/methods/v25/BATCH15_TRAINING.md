# V25 已启动训练配置：8 批 × 15 题

本文记录 history_primary_v2 训练的启动配置。当前源码已更新为
`v25_preconditioner_self_check_scope_v6`，仅做本地验证，未重启或迁移该实验。
链接的配置文件现为后续新实验模板，已同步新引用契约；历史启动条件以各 campaign 的冻结配置为准。

2026-10-26 用户取消每批 10 题训练，要求删除该次训练实验目录，并在新目录从头启动 8 批 × 15 题。此前 10 题离线分析仅作历史测量，不作为当前配置。

当前配置：[v25_spreadsheetbench_full120_batch15.json](../../../experiments/methods/v25/configurations/v25_spreadsheetbench_full120_batch15.json)。

- 原始 80 Train 后接 40 Val，共 120 题，原顺序不打乱，8 批 × 15 题，1 epoch。
- 启动时的项目源码及 `v25_preconditioner_history_primary_v2` Preconditioner，从原始 initial Skill 和空 Memory 开始。
- Actor 并发 4，每次最多 32,768 输出 tokens；最多 30 次实际程序执行，每份程序最多 6 次 API 总请求。
- 无整题累计时限；单次 API 300 秒、单次程序执行 600 秒；无标准答案或评分纠错反馈。
- 仅沿用现有连续时间线，不增加公共内容共享、代码去重或 Verifier 前缀共享。
- API、模型、预览、执行器、评分器、Gate 和优化器预算沿用原 `_004` 配置；仅 Preconditioner 方法版本绑定到启动时设计。
- 新配置准备器默认每批 15 题。只启动训练，不自动启动 Test。

这次启动是从头训练，不恢复已删除的 10 题实验，也不恢复旧 `_004` 的进度。其他旧实验归档、SkillAdam 及基线测试不变。
