# Experiment Results

本目录保存可以进入版本控制的实验汇总、Candidate Skill 和决策证据。体积较大的原始轨迹、学习输入和数据库快照保存在 `artifacts/` 中，不提交到 Git。

## ST-WebAgentBench SuiteCRM 演化链路

```text
v01：S0 Train 与 Day 8 基线实验
  └─ 生成 Governed Candidate S1
          ↓
v02：在 18 个 Selection Task 上比较 S0 与 S1
  └─ Evolution Gate 接受 S1
          ↓
v03：使用 S1 重新生成 Train 经验并增量生成 S2
  └─ 在 18 个 Selection Task 上比较 S1 与 S2
  └─ Evolution Gate 拒绝 S2，继续保留 S1
```

| 目录 | 主要内容 | 结论 |
|---|---|---|
| `stweb_suitecrm_poc_v01/` | Day 8 基线结果、二维状态分析、Governed Candidate S1 及其生成证据 | 从 S0 Train 经验生成 S1 |
| `stweb_suitecrm_poc_v02/` | S0 与 S1 的 Selection 汇总和 Evolution Gate 决策 | S1 被接受并晋升为 Parent |
| `stweb_suitecrm_poc_v03/` | S1 Train、Candidate S2、S1/S2 Selection 汇总和 Gate 决策 | S2 被拒绝，继续保留 S1 |

## 推荐阅读顺序

1. 阅读 `docs/04_EXPERIMENT_LOG.md` 中的 Day 9-10 记录，了解实验设计和主要结论。
2. 阅读各版本的 `selection/evolution_summary.md`，查看人类可读的 Selection 结果。
3. 阅读 `selection/evolution_decision.json`，查看正式 Gate 决策。
4. 阅读 `skills/*_skill.md`，查看实际注入 Agent 的 Skill。
5. 需要审计或复现实验时，再查看 `provenance`、`metadata`、`freeze` 和 Learner 原始回答。

## 结果文件与原始数据

本目录只保存适合审阅和追踪的小型结果文件，包括：

- Candidate Skill 及其 Patch；
- 规则来源和生成元数据；
- Candidate 冻结记录；
- Selection 汇总；
- Evolution Gate 决策；
- 实现冻结和预注册信息。

以下大型或本地环境相关数据保存在被 Git 忽略的 `artifacts/` 目录：

- 原始 Train 和 Selection trajectories；
- Governed Experience 学习输入；
- SuiteCRM 数据库快照；
- 运行过程中的 failure 和中间文件。
