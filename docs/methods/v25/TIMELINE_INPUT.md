# V25 优化器连续时间线视图

2026-10-27 新增 [execution_only_v1](EXECUTION_HISTORY.md)：先审计原始请求，再过滤生成失败，最后做时间线去重。此时还原的是正式执行历史，不是包含临时格式反馈的全部 API 请求。下文的逐轮真实请求还原结论适用于原有证据协议；新旧策略分别验证，不回写旧归档。

当前源码的新优化器请求使用 `current_execution_timeline_v1`，只去除完整执行记录中每次尝试重复携带的累计 `request_messages`。Actor 的实际请求、原始执行归档、各模块的 `input.json`、证据 ID、评分、Gate 和 Memory 发布规则不变。

每题保留一次 `initial.messages`。第 n 次 Actor 请求可以由初始消息加上前 n−1 次的原始 `response`（assistant 消息）和非空 `feedback_to_actor` 按顺序完整还原。投影前逐轮检查相等，不一致时明确报错，不删除无法还原的信息。

完整响应与 `executed_code` 两份保留；每题公共系统 Prompt、Skill 和预览仍完整保留。不实施跨任务共享或代码去重。`execution`、`feedback_to_actor`、`outcome.score` 继续分别表示执行事实、Actor 真正收到的信息和事后评分。

Grouping、Diagnosis、Preconditioner、Replay 通过共同请求边界采用该视图。Verifier／Repair 中已有的完整执行引用同样去重；孤立的尝试引用保留自己的 `request_messages`，因为其初始上下文和之前尝试不一定属于该次允许查看的证据。不额外加载其他执行记录。Editor 没有执行轨迹的输入不变。

视图版本保存在 `request_context.json` 的 `execution_view` 中。没有该字段的旧归档继续使用原输入表示；重试与中断恢复保留原视图版本，已有输出校验反馈不变。新 `messages.json` 记录实际发送的时间线视图，原始证据归档不经过投影。

## 验证

简单离线回归覆盖多轮还原、空响应、运行日志与可见反馈边界、不一致历史拒绝、精确引用范围、重试、归档加载，以及完整的预设响应流程；不请求真实模型。

相关 21 项测试通过。先前启动的 V25＋V24 共 190 项回归也已完成验证：183 项首次通过，7 项因 `/private/tmp` Docker 挂载失败，改用用户缓存测试路径后全部通过。

已完成的第一批真实轨迹离线检查见 [报告](../../../experiments/methods/v25/timeline_first15_001/reports/REPORT.md)。15 题共 32 次 Actor 请求逐轮还原一致；Grouping／Diagnosis／Preconditioner 的完整输入字符数分别减少约 51.6%／50.4%／49.1%。统计包含时间线说明；修改后模型 Token 数未测量，不以字符数估算替代 API 用量。

## 后续训练

从项目根目录使用当前 `src.skill_evolution.v25.cli` 启动新的 campaign 即采用本次修改。已有 `v25_spreadsheetbench_verified400_rc1/code/` 是保留的独立旧快照，不会自动同步当前源码。本次没有修改该快照、旧 pilot 的冻结源码／配置，也没有启动训练。

旧 campaign 的源码冻结检查继续生效，不能在修改源码后直接 resume 旧 campaign。需要本次视图的完整训练应使用新的 campaign 目录；批次大小、Actor 预算和模型参数仍由所选配置决定。
