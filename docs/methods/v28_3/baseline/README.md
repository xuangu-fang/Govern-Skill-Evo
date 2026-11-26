# v28.3 设计来源快照

这些是 2026-11-04 本次设计时读取的原文副本，不是 v28.3 的运行输入，也不应由旧 runner 直接启动。

- diagnosis_v29_4.md、preconditioner_v29_4.md：方法主体基线。
- editor_v29_2.md、replay_v29_2.md：v29.4 继续采用的上游提示词。
- searchqa_v28_1_config.json：600 题顺序、20×30 批次、Actor 与 SearchQA 原有预算基准；其中旧方法身份仅用于溯源。
- actor_base_protocol.md、actor_system.md、actor_user.md：SearchQA Actor 模板。
- initial_skill.md：未来 v28.3 重新初始化使用的原始 Skill。

未来运行须使用独立实现和新的版本身份，不能恢复旧 campaign 或继承 v28.2 Memory。来源差异及预定参数见上级 source_map.json。
