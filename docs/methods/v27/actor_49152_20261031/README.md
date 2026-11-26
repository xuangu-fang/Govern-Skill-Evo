# 两路 LMB Actor 输出上限 49,152（2026-10-31）

用户授权将 v27 与 SkillAdam 共用 Actor 的 max_tokens 从16,384改为49,152。训练与最终Test使用同一Actor配置。首次请求、截断及技术错误仍共用最多六次总尝试，SDK0、原消息重试、恢复不重置额度；超时300/10秒、等待1.0×尝试序号秒、模型和thinking等全部不变。

SkillAdam原生优化器输出仍为16,384、SDK max_retries=2、patch_attempts=3。接入预检查不再将优化器输出预算绑定到Actor预算，而是独立校验原有16,384；原生源码、Prompt、压缩和优化规则均不变。v27五模块仍为16,384/32,768/32,768/16,384/32,768，方法六次额度及2秒重试系数不变。

五份v27方法Prompt仅将内嵌Actor运行条件中的16,384改为49,152，版本从v5升至v6；Actor实际题目／答案格式Prompt、模块职责和输出契约不变。旧Prompt快照保留。

- [配置精确对照](config_revision.json)
- [Actor运行条件](actor_runtime.md)
- [五模块Prompt快照](prompts/grouping.md)
- [v27离线验收](../../../../artifacts/verification/v27_actor49152_final_20261031/validation.json)
- [SkillAdam离线验收](../../../../artifacts/verification/lmb_skilladam_actor49152_20261031/validation.json)

离线验收通过后，仅清理20261031_114845这次失败的两路训练目录；保留失败原因、启动配置和清理审计，不删除之前其他实验或数据。新运行使用独立目录及初始Skill，各自成功结束并验证最终Skill后自动开启124题Test，失败不启动Test，也不增加重试额度。

来源校验：原始65项来源清单保持不变；原v25变更审查继续沿用。本次增加model_access.json的明确预算变更审查，保存历史／当前快照与精确diff，当前为63项未变＋2项已审查变更。首次来源校验失败报告保留，不标为通过，见[来源核对](reconciliation.json)。

最终验收：v27 69/69、SkillAdam 33/33通过；网络连接尝试、真实模型请求均为0。20261031_114845两路失败训练目录已删除，启动配置、失败摘要和清理审计保留。新两路于北京时间2026-10-31 15:23启动；15:24核对时均正常运行，各有10个请求、1个完成结果、0个错误，实际请求max_tokens均为49152，Test尚未启动。[新运行目录和状态](../../../../artifacts/benchmarks/livemathematicianbench/actor49152_retrain_test_20261031_152036/README.md)。
