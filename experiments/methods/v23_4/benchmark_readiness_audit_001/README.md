# V23.4 Benchmark 就绪审计

本目录保存 2026-10-22 的历史审计结论和必要失败证据。此处的 `components_implemented_campaign_integration_incomplete` 描述当时状态；后续集成进展见 [Campaign 集成报告](../campaign_integration_001/REPORT.md)，不能将本次历史审计当作当前就绪状态。

## 保留材料

- [RESULTS.json](RESULTS.json)：原始审计结论、配置问题、任务数量和测试统计，保持原文。
- [FAILURE_EVIDENCE.md](FAILURE_EVIDENCE.md)：1 个失败、9 个错误的节点列表及关键日志摘录。

当时全套测试为 **977 passed、1 failed、9 errors**；另一次 V23.4 收集记录为 **301 tests collected**。这些是历史记录，本次整理没有重新运行测试或真实模型。

## 完整本地归档

原始文件位于 [artifacts/methods/v23_4/benchmark_readiness_audit_001](../../../../artifacts/methods/v23_4/benchmark_readiness_audit_001/)：

- [pytest.log](../../../../artifacts/methods/v23_4/benchmark_readiness_audit_001/pytest.log)：完整测试输出、全部错误堆栈及汇总。
- [v23_4_collection.log](../../../../artifacts/methods/v23_4/benchmark_readiness_audit_001/v23_4_collection.log)：301 个 V23.4 测试的收集记录。
- [tmp/](../../../../artifacts/methods/v23_4/benchmark_readiness_audit_001/tmp/)：测试生成的临时归档、合成输入输出和恢复场景。

`tmp/` 的 pytest `*current` 符号链接已改为归档内的相对目标。历史日志与 JSON 中记录的原始路径保持原文；它们是当时测试环境的记录，不是当前运行入口。需要查阅旧路径指向的文件时，使用上述归档中的相同相对路径。

完整归档受仓库 `/artifacts/` 忽略规则覆盖，只克隆 Git 不包含这些原始文件。
