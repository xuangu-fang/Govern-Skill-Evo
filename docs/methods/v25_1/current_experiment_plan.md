# 实验安排（2026-10-30）

本文记录启动前的安排。v25.1 后续完成 8 轮训练和 280 题首测。[完成记录](../../../experiments/methods/v25_1/v25_v25_1_common_actor_no_review_20261030_001_v25_1/README.md)

用户已取消新 V25 对照，保留旧 V25 已完成结果；本次主要比较为 **V25.1 与 Actor 对齐后的新 SkillAdam**。两者均尚未启动。

| 版本 | 当前用途 | 配置 |
|---|---|---|
| V25.1 | 待运行的新方法 | [冻结配置](../../../experiments/methods/v25_1/v25_v25_1_common_actor_no_review_20261030_001_v25_1/config/config.json) |
| 新 SkillAdam | 待运行的比较方法，优化器保持原配置 | [Actor 共享配置](../../../experiments/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/config/shared_config.json)、[优化器配置](../../../experiments/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/config/skilladam.json) |
| 旧 V25、旧 SkillAdam | 历史参考，完整保留，不重跑 | 原 `v25_skilladam_upstream_actor_prompt_20261030_001/scheduled_run` |

新 SkillAdam 对齐 V25.1 的 Actor Prompt、执行环境和评分兼容口径，保留 SkillAdam 原生优化器配置、Prompt、Gate、Momentum 和更新逻辑。两者使用相同初始 Skill、120 题优化顺序和 280 题测试集。各自从初始状态训练，不能直接用旧 SkillAdam 最终 Skill 替代新配置下的训练。

离线准备说明见 [SkillAdam 冻结说明](../../../experiments/methods/skilladam/spreadsheetbench/aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/reports/README.md)。未启动训练、测试或真实模型请求，仍等待用户后续授权。

该比较衡量 V25.1 与 SkillAdam 在共同 Actor 条件下的方法整体表现。因为已取消同条件 V25 对照，它不能单独证明新预条件设计相对旧 V25 的增益。此前部分测试案例已参与问题分析，不能将这些测试结果描述为完全独立的开发外证据。
