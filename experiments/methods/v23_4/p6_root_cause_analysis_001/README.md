# p6_root_cause_analysis_001

本目录是 P6 的只读根因分析，现有六个文件全部保留。

- [REPORT.md](REPORT.md)：根因分析结论、证据与解释边界。
- [EVIDENCE.json](EVIDENCE.json)：提取的事实、输出引文和来源；后续分层诊断也读取此文件。
- [analyze.py](analyze.py)：分析脚本，通过公共读取工具访问已归档的 P4、P6 和候选实验输入。
- [VERIFICATION.json](VERIFICATION.json)、[FINAL_CHECKS.json](FINAL_CHECKS.json)：历史检查结果。
- [READ_ONLY_BEFORE.json](READ_ONLY_BEFORE.json)：既有只读边界记录，保留原文。

本目录没有独立模型调用、完整运行轨迹或待迁移的 HTTP 数据。P6 原始输入与调用数据见 [P6 归档](../../../../artifacts/methods/v23_4/multi_knowledge_p6_001/)，后续研究见 [分层诊断](../replay_layered_diagnostic_001/README.md)。本次整理未重新运行历史冻结校验或生成新的校验记录。
