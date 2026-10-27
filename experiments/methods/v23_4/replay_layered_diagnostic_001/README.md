# replay_layered_diagnostic_001

本目录保留分层诊断的协议、问题、评分依据、全部回答和研究结论。四个条件各完成两次调用，共八次、三十二个回答；两次结果均保留，不按语义好坏择优。

## 保留材料

- [协议](PROTOCOL.md)、[冻结配置](freeze.json)、[重复计划](repeat_plan.json)、[设计脚本](design.py)。
- [R05 问题](config/R05/questions.json)、[R06 问题](config/R06/questions.json)、[输入统计](config/input_checks.json)。
- [独立标准事实](private/standard_facts.json)：调用前准备的评分依据，未发送给模型。
- [报告](REPORT.md)、[逐题评分](SCORES.md)、[调用统计](CALLS.md)。
- [初始评分](initial_evaluation.json)、[全部评分](evaluation.json)、[跨层比较](cross_layer.json)、[P6 对照回答](P6_COMPARISON_SOURCE.json)。
- [全部回答与调用结果](runs/)：八份 `parsed.json` 与八份 `attempt.json`，包括所有语义和引用错误证据。
- [输入核验](INPUT_VERIFICATION.json)、[引用审计](REFERENCE_AUDIT.json)、[调用审计](AUDIT.json)、[最终核验](FINAL_VERIFICATION.json)，以及原有 `protected_before.json`。

八次调用都正常结束且格式合法。R06_B 第一次的 `Q2:40`、`Q2:11` 引用错误等问题保留在原回答和评分中，没有修补。四次补充是预先登记的稳定性重复，历史记录为零技术重试。

## 原始归档

完整数据按原相对层级存于 [本地归档](../../../../artifacts/methods/v23_4/replay_layered_diagnostic_001/)：

- [config/](../../../../artifacts/methods/v23_4/replay_layered_diagnostic_001/config/)：四组完整 `evidence.json` 和含完整消息的 `request.json`。
- [runs/](../../../../artifacts/methods/v23_4/replay_layered_diagnostic_001/runs/)：八次调用的 `http/`、`response.json`、`raw_output.txt` 和 `started.json`。
- [live.lock](../../../../artifacts/methods/v23_4/replay_layered_diagnostic_001/live.lock)：运行锁文件。

[公共读取工具](../archive_io.py) 支持通过原路径访问归档，并合并枚举两处文件。运行入口和审计均从两处枚举启动记录，仍识别已完成的八次调用；既有尝试不重复发送，八次总预算保持不变。输入保存也识别已归档文件，避免在原位置重新生成完整输入。

历史 JSON 中的路径及冻结记录保持原文。后续条件学习、V3 验证的公共读取和文件枚举兼容此布局。本次整理没有调用模型、重新评分或重新执行历史冻结校验。完整原始数据被 Git 忽略，仅克隆 Git 不包含这些数据。
