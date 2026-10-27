# multi_knowledge_p6_001

本目录保留 P6 的配置、报告、合法提案、首次失败证据和 Memory 审计。完整输入、调用数据与 Memory 预览按原相对层级存入 [本地归档](../../../../artifacts/methods/v23_4/multi_knowledge_p6_001/)。

## 保留材料

- [协议](PROTOCOL.md)、[冻结配置](config/freeze.json)、[结果](RESULTS.json)、[调用审计](AUDIT.json)。
- [实验报告](REPORT.md)、[语义审查](SEMANTIC_REVIEW.md)、[事实检查](FACT_CHECKS.json)、[增长检查](GROWTH.json)、[最终检查](FINAL_CHECKS.json)。
- R05 选择第 2 次提案：[选择记录](runs/R05_replay/selected.json)、[合法提案](runs/R05_replay/attempt_002/parsed.json)、[结果](runs/R05_replay/attempt_002/result.json)。
- R06 选择第 1 次提案：[选择记录](runs/R06_replay/selected.json)、[合法提案](runs/R06_replay/attempt_001/parsed.json)、[结果](runs/R06_replay/attempt_001/result.json)。
- R05 首次失败：[错误记录](runs/R05_replay/attempt_001/attempt.json)、[原始响应文本](runs/R05_replay/attempt_001/raw_output.txt)。该响应未形成合法 JSON，没有生成 `parsed.json`；原文保留，未修复或替换。
- Memory 审计：[R05](cases/R05/results/MEMORY_AUDIT.json)、[R06](cases/R06/results/MEMORY_AUDIT.json)。

所有尝试的 `attempt.json` 保留。既有 `protected_before.json` 与冻结配置中的历史记录保持原文。

## 原始归档

- [runs/](../../../../artifacts/methods/v23_4/multi_knowledge_p6_001/runs/)：完整 material、messages、response、HTTP 请求/响应、发送记录、启动记录及合法提案的原始响应文本。
- [R05 Memory](../../../../artifacts/methods/v23_4/multi_knowledge_p6_001/cases/R05/) 与 [R06 Memory](../../../../artifacts/methods/v23_4/multi_knowledge_p6_001/cases/R06/)：完整 `memory_preview/`，以及 `results/memory_candidate.json`、`results/memory_view.json`。
- [运行锁文件](../../../../artifacts/methods/v23_4/multi_knowledge_p6_001/live.lock)。

[公共读取工具](../archive_io.py) 支持通过原路径读取归档，并合并枚举分开保存的目录。P6 与后续分析、条件学习和 V3 验证的读取路径已适配；历史 JSON 中的路径保持原文。既有启动与审计校验未放宽，本次未调用模型或重新发布 Memory。完整原始数据被 Git 忽略，仅克隆 Git 不包含这些数据。
