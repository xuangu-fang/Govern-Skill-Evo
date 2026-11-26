# v27／LMB 旧独立副本归档（源码已删除）

`replay_dedup_v1` 是历史独立源码副本的目录名，不是新方法版本号，也不是当前 v27 的未解决项。

2026-11-02 按用户要求删除 `workspace/`（旧源码、测试及配套数据副本）。当前实现位于主工作区 `src/skill_evolution/v27`，已同时处理请求和响应重复；详见 [当前修复报告](../../../../docs/methods/v27/replay_dedup_v2_20261102/REPORT.md)。

本目录仅保留历史证据：`runs/` 中已归档的 R01 训练记录、`verification/` 离线报告、`snapshot_manifest.json` 和 `changes.patch`。旧自动续跑已取消、定时跟进已删除。旧运行脚本的源码路径已不存在，不再作为启动入口；以下历史复验说明及路径不代表当前运行状态。

## 历史实现与首次离线验收记录（源码删除前）

# v27 Replay 消息去重：隔离实现与离线验收

状态：已实现并完成离线验证。没有启动真实训练、Test 评估或模型调用。

本变体名为 `v27_replay_dedup_v1`，实现位于本目录的 `workspace/`。原项目中的
`src/skill_evolution/v27`、`src/skill_evolution/v28` 及它们的测试未修改。
v28 会校验 v27 源码哈希，因此本次将当前工作区（包含未提交文件）的必要源码、
测试和数据复制到独立目录。副本没有复制 `.env`，没有通过软链接共用可写源码。

本目录的 `changes.patch` 是相对复制前源码的变更，供审阅；未应用到原项目。
原目录继续运行原 v27/v28，本副本仅用于新的 v27 变体。副本中的历史 v28 代码不作为
运行入口，也没有修改其依赖清单来掩盖 v27 变化。

## 实现边界

- 新增 `workspace/src/skill_evolution/v27/benchmarks/lmb/replay_input_view.py`，
  从 v28 本地移植，不运行时导入 v28。
- 在原有完整 bundle 校验、Knowledge-only Memory 投影之后，对 Replay 模型输入去重。
- 验证唯一已完成轮次的 `request_messages` 与本条执行的 `initial.messages`
  精确一致后省略前者；完全相同的 system 消息共享，同题且已验证的 Parent/Candidate
  完整 user 消息序列共享。
- 共享表保留原文、空白、消息元数据和顺序。`initial.task`、独立执行身份、回答、评分、
  Parent、Diff、Plan 和 Knowledge Memory 保持原有信息。
- 完整 bundle 仍写入 `input.json`，发送视图写入 `base_messages.json` 和逐次
  `messages.json`。Replay 输出仍使用原始 payload 校验证据权限。
- Prompt 升级为 `v27_lmb_replay_v7`，输入视图为 `v27_lmb_pairs_shared_initial_v1`。
  提示词明确共享消息解码、请求省略和原始证据 ID 的含义。
- 原有请求预算、Actor 设置、Gate、评分和其他四个方法模块保持不变。

新配置 `workspace/experiments/configs/v27_lmb53_epoch1_replay_dedup_v1.json`
已经离线验证，但没有初始化 campaign。它保留 53 题、10/10/10/10/10/3 顺序、
初始 Skill 内容及原模型预算。旧配置和旧实验不使用新视图恢复运行。

## 验证结果

| 项目 | 结果 |
|---|---|
| 隔离副本 v27 完整离线套件 | 83 项通过，0 失败、0 错误、0 跳过 |
| 原工作区 v28 Replay 套件 | 7 项通过，0 失败、0 错误、0 跳过 |
| 原 v28 实现身份校验 | 43 个继承依赖及 8 个上游来源通过 |
| 原工作区受保护文件 | 121 个哈希保持不变 |
| 六轮真实归档输入 | 53 对、106 条执行，全部去重后完整还原，原对象不变 |
| 真实模型请求 / 网络连接尝试 | 0 / 0 |
| 真实训练 / 基准 Test | 均未启动 |

新增验证覆盖精确还原、同题共享范围、空白与元数据差异、无效引用、非单轮请求、
篡改配对、完整归档与共享发送、输出证据权限、版本冻结、只读恢复、校验反馈重试、
预算变更拒绝和请求篡改拒绝。原有套件继续覆盖合成 Actor、合成训练流程及合成评估，
这些检查只使用临时目录和本地假响应。

首次全量回归有一项旧容量预期失效：原 16,384 字符/执行的压力样例去重后能容纳。
最终保留了该样例的“完整保留且可容纳”回归，另将超限压力样例提高至
24,576 字符/执行，验证超限时仍在发送前拒绝。运行时容量上限没有放宽。
首次结果保留于 `verification/full_suite/`，最终结果见 `verification/full_suite_final/`。

| 轮次 | 原 user JSON 字符 | 去重后字符 | 减少 |
|---|---:|---:|---:|
| R01 | 305,206 | 108,529 | 64.44% |
| R02 | 414,459 | 119,401 | 71.19% |
| R03 | 440,062 | 130,369 | 70.37% |
| R04 | 532,113 | 134,257 | 74.77% |
| R05 | 502,750 | 146,213 | 70.92% |
| R06 | 190,899 | 90,202 | 52.75% |
| 合计 | 2,385,489 | 728,971 | 69.44% |

这些是历史输入的精确字符统计，不是新模型 Token、费用或正确率测量。
历史六轮包含当时批准的恢复记录；本次只读取其已发送的消息，没有恢复旧训练。
无损还原不保证模型生成相同 Knowledge，也不证明新训练成绩改善。

## 报告与复验

- `verification/summary.json`：总结果、变更文件及哈希。
- `verification/full_suite_final/validation.json`：v27 离线套件及来源校验。
- `verification/full_suite_final/unittest.log`：逐项测试结果。
- `verification/historical_replay_audit.json`：六轮归档来源、逐轮字符/字节及还原结果。
- `verification/original_v28_validation.json`：原目录 v28 校验及隔离检查。
- `snapshot_manifest.json`：复制前文件哈希和原目录受保护文件。
- `changes.patch`：实现、提示词、配置及验证代码的审阅补丁。

旧独立副本的复验命令已移除，因为 `workspace/` 已删除。当前源码的复验方式见主工作区修复报告。
