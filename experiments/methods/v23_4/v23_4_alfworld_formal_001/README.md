# v23_4_alfworld_formal_001

本目录保留正式配置与固定任务清单；完整执行数据位于 [正式归档](../../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/)。

## 配置与任务

- [优化配置](config/campaign.json)、[Test 配置](config/evaluation.json)、[配置来源与差异](config/provenance.json)。这些文件内嵌环境材料及配置副本，保留完整结构和原文。
- [方法](config/method.json)、[预算](config/budget.json)。
- [六批顺序](data/batches.json)、[57 条优化任务](data/optimization_pool.json)、[134 条 Test 任务](data/test.json)。

Benchmark 和 Test 入口直接读取本目录；V23.5，也读取这里的 campaign.json，因此此次整理没有移动或改写任何正式配置。

## 归档状态与结果

2026-10-27 直接读取已有 JSON：

- [优化状态](../../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1/state.json) 为 `next_round=7`，最终 Parent 指向 `rounds/R04/editor/attempts/001/candidate.md`，Active Memory 指向 `rounds/R06/memory`。
- [最终保留 Skill](../../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1/rounds/R04/editor/attempts/001/candidate.md)、[轮次归档](../../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1/rounds/)、[最终 Memory](../../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/S1/rounds/R06/memory/)。
- [Test 完成记录](../../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/evaluation/result.json) 为 `complete`；[S1 汇总](../../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/evaluation/S1/summary.json) 记录完成 134 条、成功 106 条、失败 28 条，成功率约 79.10%。
- [执行日志](../../../../artifacts/methods/v23_4/v23_4_alfworld_formal_001/execution/)、[输出预算修订](../output_budget_recovery_001/README.md)。

这些数字来自已有结果，未重新运行实验或核验模型输出。2026-10-22 的 [集成报告](../campaign_integration_001/REPORT.md) 和 2026-10-23 的 [预算恢复报告](../output_budget_recovery_001/REPORT.md) 保留各自时间点的状态；后续运行不能描述为全程采用原始固定 16K 输出预算。

[运行说明](../../../../docs/methods/v23_4/BENCHMARK_RUNBOOK.md) · [版本实验索引](../README.md)。归档已被 Git 忽略，配置中的路径和历史来源记录保持原文。
