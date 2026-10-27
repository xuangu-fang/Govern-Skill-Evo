# V23.4 semantic_generation_007

本目录保留实验脚本、协议与报告、配置冻结和来源记录、人工案例、选中尝试、解析输出、候选及 Diff。完整原始输入和调用数据存于 [本地归档](../../../../artifacts/methods/v23_4/semantic_generation_007/)。

## 研究材料

- [PROTOCOL](PROTOCOL.md)
- [REPORT](REPORT.md)
- [调用审计](AUDIT.json)：原始记录保持不变。
- [配置与来源](config/)：冻结记录和必要配置；生成的完整输入与消息已归档。
- [阶段结果与失败证据](runs/)：保留 `selected.json`、`attempt.json`、`parsed.json`、`result.json`、Candidate 和 Diff。

保存的记录共有 **1 次 HTTP 尝试、1 个选中阶段**，其中 **0 次技术失败**。结构有效不等于语义评审通过；具体判断以报告为准。

## 原始数据与读取

- [完整配置输入与消息](../../../../artifacts/methods/v23_4/semantic_generation_007/config/)
- [完整运行输入、响应与 HTTP 数据](../../../../artifacts/methods/v23_4/semantic_generation_007/runs/)

[公共读取工具](../archive_io.py) 按原路径定位保留文件或归档文件，并合并枚举分开保存的目录。`semantic_generation_001/run.py` 的 `read` / `load` 供后续实验复用，R05/R06 Actor 的独立读取入口也已适配。

历史 JSON、来源元数据和冻结记录保留原文；原始路径通过读取工具解析。已迁移实验的后续运行输出定位到归档目录，既有选中结果和失败次数仍参与复用与重试判断。历史在线启动约束保持原样，本次未调用模型、重跑实验或重新冻结配置。

只克隆 Git 不含完整原始数据；需要读取历史完整输入或响应时，须有相应的本地 artifacts。Python 缓存仍按全局规则忽略。
