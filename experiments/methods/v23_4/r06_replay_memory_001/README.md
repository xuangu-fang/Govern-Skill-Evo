# r06_replay_memory_001：早期 Replay 与 Memory 验证

本目录保留 [协议](PROTOCOL.md)、[结果报告](REPORT.md)、[语义评审](SEMANTIC_REVIEW.md)、[配置与来源](config/)、源码，以及原始研究结论。

## 保留结果与必要证据

- [调用审计](AUDIT.json) 与 [阶段结果](runs/)：保留选中尝试、`attempt.json`、`parsed.json` 和 `result.json`，完整合法提案仍可直接评审。
- [Memory 验证结论](results/MEMORY_AUDIT.json)：保留 Active ID 变化、引用检查及预览边界；结构校验通过不表示语义采用。

## 本地原始归档

- [完整 Replay bundle 与消息](../../../../artifacts/methods/v23_4/r06_replay_memory_001/config/)
- [运行输入、模型响应与 HTTP 原文](../../../../artifacts/methods/v23_4/r06_replay_memory_001/runs/)
- [完整 Memory 预览](../../../../artifacts/methods/v23_4/r06_replay_memory_001/memory_preview/)：Active 索引和历史提交保持同一目录结构，未发布为正式 Memory。
- [完整 Memory 候选](../../../../artifacts/methods/v23_4/r06_replay_memory_001/results/memory_candidate.json) 与 [模型视图](../../../../artifacts/methods/v23_4/r06_replay_memory_001/results/memory_view.json)

[公共读取工具](../archive_io.py) 支持原路径定位；Memory 加载入口使用解析后的完整预览目录。后续 Replay 输入视图实验的读取也已适配。

历史 JSON、冻结依据和原始 Memory 内容保持不变。报告中的文件链接已更新，历史启动与审计校验没有放宽；本次没有重跑模型、重新提交 Memory 或执行完整历史审计。只克隆 Git 不包含这些原始运行材料。
