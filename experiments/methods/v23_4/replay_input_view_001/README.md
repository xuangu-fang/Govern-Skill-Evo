# replay_input_view_001

本目录保存实验定义、研究结论及必要证据。

## 保留材料

- [REPORT](REPORT.md)

调用配置、来源关系、既有冻结和完整性记录、源码快照、Prompt 与 Diff 保留原文。完整输入、Memory、HTTP 数据或测试原始日志按原相对层级存入 [本地归档](../../../../artifacts/methods/v23_4/replay_input_view_001/)。

## 原始归档

- [cases/](../../../../artifacts/methods/v23_4/replay_input_view_001/cases/)

[公共读取工具](../archive_io.py) 支持通过原路径读取归档，并合并枚举分开保存的目录。实验入口、测试读取和后续消费者已适配；历史 JSON 中的路径保持原文。历史启动与审计校验没有放宽，本次未调用模型或重新发布 Memory。只克隆 Git 不包含完整原始数据。
