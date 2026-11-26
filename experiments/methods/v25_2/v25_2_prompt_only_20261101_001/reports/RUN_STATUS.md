# V25.2 正式运行

2026-11-01 17:50（Asia/Shanghai）按用户指令启动。

- 启动前 255 项审计通过，Docker 运行环境与 V25.1 基线一致。
- 使用独立冻结源码、配置和初始 Skill，空 Memory，8 轮共 120 题训练。
- 训练完整通过校验后自动运行最终 Skill 的完整 280 题测试。
- 测试完成后自动生成 comparison_results.json 和 comparison.md，与已有 V25.1 和 Actor 对齐 SkillAdam 比较。
- 比较包括准确率、单元格通过率、逐题得失、Skill 词数和测试 token 用量；原始结果保留完整测试成本统计。
- 不增加原配置之外的失败重试或重采样；意外停止时保留现场并通知。
- 每 15 分钟跟进；完成或失败时通知。

实时状态见 pipeline_status.json，日志见 pipeline.log。监控信息见 monitoring.json。
preparation_status.json 和 approved_prompts/README.md 保留启动前的历史快照；当前状态以 pipeline_status.json 为准。

## 2026-11-01 19:46 恢复

用户授权仅豁免第4轮第一次 Grouping 输出 G2.shared_basis 中 G2:P18 的坐标误报。20项离线检查通过，原始输出和六次失败档案保留，Parent缓存复用，新增Grouping请求为0。恢复已进入第4轮Diagnosis。当前有效进程与日志见 recoveries/r04_grouping_coordinate_v1/launch.json 和 recovery.log；pipeline_status.json 使用新的PID。原 pipeline_launch.json 保留历史状态。恢复后自动完成剩余训练、280题测试及三组比较，每15分钟监控。


## 2026-11-01 R06 Docker infrastructure recovery

User authorized restoring Colima and refunding the 29 infrastructure-only failures for R06 Candidate val:54144. Entry: `recoveries/r06_docker_v1/recover.py`, PID 29921; use its launch/start/failure receipts, not earlier PIDs. Original task archives and obsolete downstream Gate/Replay/Memory preserved in recovery/archive with hashes. First real cache error retained; saved response 002_01 reused without a new Actor request and passed 8/8 cells. Recomputed Gate: Parent 12/15, Candidate 12/15, RETAIN. Replay and Memory must be regenerated before R07 resumes. R07 four saved responses remain reusable with the unchanged R05 Parent. Frozen sources, prompts and budgets unchanged. A recovery-process Docker guard stops on infrastructure loss rather than feeding it into model retries. Physical excluded overhead is 28 Actor requests (responses 003-030) and the superseded Replay request, separate from active-campaign cost. Automation v25-2 recreated.
