# multi_knowledge_p4_001

本目录保存实验定义、研究结论及必要证据。

## 保留材料

- [FAILURE_EVIDENCE](FAILURE_EVIDENCE.md)
- [REPORT](REPORT.md)
- [candidate_prompt](candidate_prompt.md)
- [original_prompt](original_prompt.md)

调用配置、来源关系、既有冻结和完整性记录、源码快照、Prompt 与 Diff 保留原文。完整输入、Memory、HTTP 数据或测试原始日志按原相对层级存入 [本地归档](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/)。

## 原始归档

- [cases/](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/cases/)
- [p4_tests.xml](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/p4_tests.xml)
- [pytest.xml](../../../../artifacts/methods/v23_4/multi_knowledge_p4_001/pytest.xml)

`cases/R05/` 和 `cases/R06/` 保留实际 System Prompt、调用参数和历史来源关系；完整 bundle、模型视图和消息位于归档。P4 当时仅准备输入，没有调用真实模型。

[公共读取工具](../archive_io.py) 支持通过原路径读取归档，并合并枚举分开保存的目录。实验入口、测试读取和后续消费者已适配；历史 JSON 中的路径保持原文。历史启动与审计校验没有放宽，本次未调用模型或重新发布 Memory。只克隆 Git 不包含完整原始数据。
