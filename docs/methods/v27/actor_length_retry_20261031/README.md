# LMB Actor 截断自动重试修订（2026-10-31）

按用户确认，仅修改 v27 与 SkillAdam 共用的 LMB Actor。SkillAdam 原生补丁、Momentum、证据压缩、优化器 Prompt、SDK max_retries=2、patch_attempts=3 均不变；v27 五模块原有六次重试机制与输出契约不变。

## 当前行为

- `finish_reason=length` 归为可重试失败，无论普通 content 是 null、空串、不完整文本，还是已经包含正确答案。
- 原始响应先落盘；下一次请求保持完整消息、模型参数、Skill、题目与选项不变，不拼接截断内容，不加入评分或纠错反馈，不提高输出上限。
- 首次请求、网络/结构错误及截断共用最多六次总尝试。Actor SDK 隐式重试仍为0，等待仍为 `1.0 × 尝试序号` 秒；不额外增加额度。
- 只有正常 `stop` 响应进入评分和执行证据。正常结束的错误答案、空串、格式不合规仍按原 scorer 评分，不因得分补答。
- 六次耗尽停止该任务；没有 `result`、没有零分替代，也没有完成的 Parent/Candidate 配对。恢复不会产生第七次请求。
- 已落盘的截断响应恢复时本地识别并消耗原有槽位，只请求剩余额度；最终已完成响应只读复核。归档损坏时沿用原有零新增请求保护。
- `api_requests` 和 usage 包含已消耗的失败尝试；截断 content 和独立 reasoning_content 不进入五模块或 SkillAdam 优化证据。

## 冻结身份与兼容边界

执行身份改为 `lmb_single_turn_length_retry_v3`；Actor 增加 `retry_policy=technical_and_length_shared_six_v1`。五份 v27 方法 Prompt 升至 v5，仅修订 Actor 运行条件和证据边界，主要职责、user JSON 字段和输出 schema 不变；Actor 的答案格式 Prompt 本身不变。

两份当前配置已更新；[精确配置对照](config_revision.json)以实际上一轮启动时的配置副本为基准，确认除重试策略和相关身份外，模型、容量、并发、数据、预算与优化器参数均不变。历史运行目录、旧报告、历史 Prompt 快照及原始来源清单均保留。

历史运行仍属于“length直接评分”的旧协议，不会被重新标注为新协议。新的身份校验会拒绝用当前源码续跑旧冻结目录；未来采用新策略的实验应使用新运行目录。此次没有启动、续跑或重跑训练，也没有启动真实 Test。

## 契约、Prompt 与离线验收

- [完整当前数据与证据契约](CONTRACTS.md)
- [完整当前验收清单](OFFLINE_ACCEPTANCE.md)：仍为107项映射，修订V07/V08/V10/F05/F13并扩展F12测试覆盖。
- [冻结Actor运行条件](actor_runtime.md)和 [五模块Prompt快照](prompts/grouping.md)：与运行资源逐字校验。
- [v27最终验收](../../../../artifacts/verification/v27_actor_length_retry_final_20261031/validation.json)
- [SkillAdam验收](../../../../artifacts/verification/lmb_skilladam_actor_length_retry_20261031/validation.json)

验证使用独立 `/Users/didi/miniforge3/envs/LiveMathematicianBench/bin/python`，网络被阻断，全部模型输出为合成响应。覆盖截断的三种内容形态及可解析正确标签、混合技术错误、六次耗尽与重复恢复、JSON/HTTP已落盘后中断、等待期间中断、归档损坏、证据拒绝、旧身份拒绝，以及Campaign/合成Test和SkillAdam共用Actor接入。未验证新规则下的真实模型效果；107项映射不等同于全部语义场景实质通过。

最终结果：v27 64/64、SkillAdam 31/31 测试通过；两套均为零网络连接尝试、零真实模型请求。v27运行源码及验收文件哈希已与最终报告再次核对一致，来源核对也通过。原生SkillAdam及LMB接入桥接源码与上一轮实际训练冻结档案逐文件一致。
