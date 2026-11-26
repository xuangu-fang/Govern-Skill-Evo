# v27 Replay 双重去重合入原版（2026-11-02）

已直接合入主工作区 `src/skill_evolution/v27`，无需独立运行副本。Replay Prompt 为 `v27_lmb_replay_v8`，模型输入视图为 `v27_lmb_pairs_shared_initial_v2`。主配置 `experiments/configs/v27_lmb53_epoch1_deepseek_flash.json` 同步更新。

## 行为

- 相同 system 初始消息共享；完整相同的 user 消息序列只在已经验证的 Parent/Candidate 配对内共享。
- 确认单轮 `request_messages` 与该次执行的初始消息完全一致后，省略重复请求字段。
- 参考 v29 的实现：确认 `outcome.answer.raw_content` 与同一次执行的 `attempts[0].assistant.content` 完全相等后，仅从 Replay 发送视图中移除前者。完整普通响应保留在后者，不截断、不概括。
- 输入事实、Call.input、磁盘归档、评分和证据引用权限保持完整。增加离线还原函数验证省略字段可精确恢复。
- 空内容、长内容、不同内容及缺失字段有回归测试；重复内容不一致直接拒绝，不静默丢弃。
- Actor、其他四个模块、模型参数、输出预算、尝试次数和评分规则未改。容量回归用更大的合成响应继续覆盖溢出拒绝，不放宽运行限制。

## 验证

v27 离线套件 86/86 通过；v28 Replay 测试 9/9 通过。验证屏蔽网络和模型子进程，真实模型请求为 0。v28 源码 40 个文件与本次修改前快照一致。本次没有修改 v28 的冻结策略；其源码哈希检查已由用户另行取消。

历史六轮 53 对、106 条执行记录全部无损还原，且历史文件未改动：原输入 2,385,489 字符，仅初始消息去重后 728,971 字符，加入响应去重后 725,278 字符。响应去重额外减少 3,693 字符，总减少 69.5963%。这是序列化字符计数，不等于供应商 token、费用或质量测量。

证据：`verification/validation.json`、`verification/unittest.log`、`verification/historical_replay_audit.json`、`verification/v28_check.json`；修改清单见 `summary.json`，已有文件的修改前副本见 `before/`。

## 实验状态

旧独立副本实验 `experiments/methods/v27/replay_dedup_v1_20261102/runs/v27_replay_dedup_20261102_134000` 已原地归档：完成 R01，R02 零请求，原始记录保留。自动续跑控制器已停止，定时跟进 v27 已删除。

**没有启动新训练或正式测试。等用户明确通知后，才从初始 Skill 开始新实验。** 不复用旧 R01 的训练成果；旧 run_pipeline.py 为旧独立版本冻结，不作为新版本入口。后续启动需要准备指向原版 v27 的新运行目录及流程，并沿用已授权的 53 题六批训练、124 题标准 49152/最多六次、仅耗尽预算未完成题 81920/最多三次补测方案，与旧版 59/124 对比。
