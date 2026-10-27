# V24 RC1 小规模真实验证结果

状态：完成。只运行原第一批 10 个优化任务的一轮自进化，没有启动其余批次或 Test。
执行时间：2026-10-24 23:21:34—23:55:59（Asia/Shanghai），约 34 分 25 秒。

## 主要结果

| 项目 | Parent | Candidate |
|---|---:|---:|
| 成功任务 | 10/10 | 10/10 |
| 总执行步数 | 130 | 79 |
| Actor 请求 | 130 | 79 |

Gate 为 **RETAIN**。原规则只在 Candidate 成功数严格更高时接受；本轮成功数持平，
因此正式 Skill 仍为初始 Parent。Candidate 的步数减少不改变这一选择。

Replay 生成 2 条 Memory 条目、7 项知识内容。Verifier 核验 7 项，未报告冲突，
未触发 Repair，随后成功发布 Memory。这说明 RETAIN 分支仍能完成经验学习。

## 配置与范围

- 使用 `v24_alfworld_verified_feedback_001_rc1/code` 保存的代码副本。
- 使用候选目录的单轮计划配置，任务为 `train:0000` 至 `train:0009`。
- 相对正式配置只缩减 batches 与对应 task_items，模型、prompt、初始 Skill、
  环境条件、并发 8、最多 50 步及请求预算均未改变。
- 各模块/Actor 每步仍最多六次总尝试。Preconditioner、Replay、Verifier、Repair
  的输出额度仍为 32,768，其余沿用 16,384。
- 真实请求参数与保存配置一致。共执行 20 个 episode，Test 为 0。

## 阶段结果与异常

| 阶段 | 实际尝试 | 结果 |
|---|---:|---|
| Grouping | 1 | 通过 |
| Diagnosis | 1 | 提出修改 |
| Preconditioner | 3 | 第一次读取超时；第二次达到输出额度而截断；第三次通过 |
| Editor | 1 | 生成 Candidate |
| Candidate 与 Gate | 10 个任务 | 全部成功，RETAIN |
| Replay | 1 | 生成经验 |
| Verifier | 1 | 7 项核验，无冲突 |
| Repair | 0 | 本轮无需触发 |
| 发布与完成后恢复 | 1 轮 | 正常发布；恢复新增请求和 episode 均为 0 |

Preconditioner 重试复用相同消息和参数；未扩大预算，也未重跑已完成任务。
两次失败均保留在原始记录中。实际观察到了超时及截断重试，没有观察到
Repair 的真实调用或运行中进程中断恢复，不能把这些未发生分支写成真实验证通过。

## 逐任务步数

以下任务的 Parent 和 Candidate 都成功。差值为 Candidate−Parent。

| 任务 | Parent 步数 | Candidate 步数 | 差值 |
|---|---:|---:|---:|
| train:0000 | 4 | 5 | 1 |
| train:0001 | 4 | 4 | 0 |
| train:0002 | 7 | 7 | 0 |
| train:0003 | 4 | 4 | 0 |
| train:0004 | 18 | 11 | -7 |
| train:0005 | 48 | 5 | -43 |
| train:0006 | 12 | 29 | 17 |
| train:0007 | 15 | 6 | -9 |
| train:0008 | 4 | 4 | 0 |
| train:0009 | 14 | 4 | -10 |

`train:0005` 从 48 步变为 5 步；`train:0006` 从 12 步变为 29 步。
完整记录同时保留改善与变慢的任务。本轮只有一次配对执行，不能据此证明
稳定效率提升，也不能证明 v24 相对 v23.5 的整体成功率不下降。

## 调用与用量

- Actor 请求：209 次；方法请求：8 次；合计 217 次。
- 已知输入 token：473,537；已知输出 token：184,552；已知合计：658,089。
- 其中一次读取超时没有用量记录，实际总消耗可能高于上述已知数值。
- 不按 token 数估算金额，未取得本次接口的实际账单。

## 保存材料

- [当前阅读导航与尝试边界](README.md)
- [机器可读汇总](summary.json)
- [逐任务对照表](task_comparison.csv)
- [真实运行目录](../../../../artifacts/methods/v24/alfworld_rc1_smoke_001/)
- [实际运行配置副本](config/campaign.json)
- [最终保留 Skill](results/final_skill.md)
- [候选与实际 Diff](evidence/S1/rounds/R01/editor/attempts/001/actual.diff)
- [Gate 与任务配对](evidence/S1/rounds/R01/gate/result.json)
- [Memory 发布摘录](evidence/memory_publication.json) · [完整 Memory 原归档](../../../../artifacts/methods/v24/alfworld_rc1_smoke_001/S1/rounds/R01/memory/view.json)

2026-10-27 仅补充阅读副本和路径导航，未重跑实验或测试；本报告原有结果与统计保持不变。

候选版本没有被覆盖。此次结论是小规模真实链路验证完成；完整效果对照仍未启动，
需另行明确指令。
