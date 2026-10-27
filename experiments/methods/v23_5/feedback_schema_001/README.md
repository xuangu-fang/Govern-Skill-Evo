# Schema 定位反馈验证：材料与归档

[实验协议](PROTOCOL.md) · [历史结果](reports/RESULTS.md) · [配置](config/protocol.json) · [逐次诊断与 usage](results/summary.json)

本实验导入一次历史失败，再新增 2 次真实请求；共 3 次尝试，选中第 003 次。第 001 次不是新 API 调用，第 003 次结构有效不等于策略语义或任务成功率已验证。

## 保留材料

- [来源记录](results/provenance.json)：保留 schema seed 的原始归档来源。
- [三次尝试](evidence/preconditioner/attempts/)：原样保留回答、错误、反馈来源上下文和运行状态；第 003 次另保留有效输出与校验记录。
- [有效提案及编译结果](evidence/preconditioner/attempts/003/validated.json)：已有保存结果的副本，没有重新调用编译或校验函数。
- [选择结果](evidence/preconditioner/result.json)：`attempts/003` 相对引用在本地证据目录中仍可解析。
- [共同冻结 Prompt](../feedback_smoke_001/prompts/preconditioner.md)：与本实验归档 base_messages 的 system 正文直接比较一致，无需重复保存。

本目录的 [.gitignore](.gitignore) 仅放行上述三个编号下的 JSON 证据，避免被仓库通用 `attempt*/` 规则隐藏；完整运行归档仍被忽略。

config/protocol.json 原样保留历史配置中继承的 rounds 字段；实际运行仅为 R04 Preconditioner 的该单个案例，以 PROTOCOL.md、逐次结果和选择记录为准。

## 原始归档与恢复

[归档目录](../../../../artifacts/methods/v23_5/feedback_schema_001/) 继续保存完整输入、base/messages、request、HTTP、contract 和重试链。[run.py](run.py) 仍读取归档的 config.json、base_messages.json、attempts 和 result.json；证据副本不替代恢复入口。request_context 内的来源路径保留原值，仍指向原归档。

2026-10-27 整理只补充静态证据副本与导航，没有发请求、重跑恢复、校验或测试。历史报告中的测试数量及成功结论不代表此次重新验证；完整归档被 Git 忽略。
