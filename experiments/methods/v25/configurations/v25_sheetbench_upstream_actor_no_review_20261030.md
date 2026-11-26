# V25 SheetBench：关闭 Knowledge Verify/Repair

新实验配置：`v25_sheetbench_upstream_actor_no_review_20261030.json`。

源配置：`experiments/comparisons/v25_skilladam_upstream_actor_prompt_20261030_001/scheduled_run/v25/campaign/config.json`。

仅调整：
- `method.knowledge_review = disabled_v1`。
- `method.memory_publication = replay_validated_before_commit`。
- 删除 `module_max_tokens` 中不再执行的 `verifier`、`repair` 预算。

其余参数与源配置一致，包括 Actor、优化器、Gate、数据顺序和初始 Skill。
此前讨论的 Actor/Preconditioner Prompt 修改草案未实施。

V25 新配置构造默认关闭审核；已有明确启用审核的配置仍保留原语义。
Replay 的结构、引用校验及 Memory 发布一致性校验继续执行。
禁用状态写入每轮 `knowledge_review/result.json`，不会发起 Verify/Repair 模型请求。

本配置供后续新实验使用，须使用新的输出目录；不能用于改变旧实验的续跑语义。
旧实验的冻结源码、配置、失败记录和结果未修改。尚未启动训练或测试。
