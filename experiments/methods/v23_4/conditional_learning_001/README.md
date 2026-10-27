# conditional_learning_001

本目录保留 V2 的候选 Prompt、配置、报告、合法提案、失败证据和 Memory 审计。完整输入及运行数据按原相对层级存入 [本地归档](../../../../artifacts/methods/v23_4/conditional_learning_001/)。

## 保留材料

- [候选 Prompt](replay_conditional_learning_v2.md)、[设计](DESIGN.md)、[协议](PROTOCOL.md)、[冻结配置](config/freeze.json)、[输入对照](config/INPUT_COMPARISON.json)。
- [报告](REPORT.md)、[语义审查](SEMANTIC_REVIEW.md)、[采用决定](RESULT.json)、[比较指标](COMPARISON_METRICS.json)、[关键证据](EVIDENCE.json)。
- [调用审计](AUDIT.json)、[历史最终核验](FINAL_VERIFICATION.json)，以及既有 `protected_before.json`。
- 全部 `attempt.json`、`parsed.json`、`result.json` 和 `selected.json`；R05、R06 均选第 2 次结果：[R05 合法提案](runs/R05_replay/attempt_002/parsed.json)、[R06 合法提案](runs/R06_replay/attempt_002/parsed.json)。
- Memory 审计：[R05](cases/R05/results/MEMORY_AUDIT.json)、[R06](cases/R06/results/MEMORY_AUDIT.json)。

四次调用全部计入历史成本。R05 第一次达到输出上限，保留 [失败记录](runs/R05_replay/attempt_001/attempt.json) 和 [响应原文](runs/R05_replay/attempt_001/raw_output.txt)；第二次上限按原规则提高至 65536。R06 第一次引用校验失败，保留 [失败记录](runs/R06_replay/attempt_001/attempt.json) 和 [含错误引用的原始 JSON](runs/R06_replay/attempt_001/parsed.json)。失败内容未修补，采用决定保持不变。

## 原始归档与读取

- [config/](../../../../artifacts/methods/v23_4/conditional_learning_001/config/)：两套完整消息。
- [runs/](../../../../artifacts/methods/v23_4/conditional_learning_001/runs/)：material、messages、完整 HTTP 数据、response、启动记录与其余原始响应文本。
- [cases/](../../../../artifacts/methods/v23_4/conditional_learning_001/cases/)：两套完整 `memory_preview/`，及 `memory_candidate.json`、`memory_view.json`、`future_replay_view.json`、`preconditioner_messages.json`。
- [运行锁](../../../../artifacts/methods/v23_4/conditional_learning_001/live.lock)。

[公共读取工具](../archive_io.py) 支持通过原路径读取归档。运行、审计、Memory 输出及后续 [V3 比较](../replay_v3_validation_001/README.md) 已适配两处存储；既有调用、重试次数和选择结果不变。历史 JSON 中的路径及冻结记录保留原文。本次整理未调用模型、重新提交 Memory 或新增校验清单。完整原始数据被 Git 忽略，仅克隆 Git 不包含这些数据。
