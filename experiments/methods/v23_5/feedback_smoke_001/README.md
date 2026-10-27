# 有限反馈小规模验证：材料与归档

[实验协议](PROTOCOL.md) · [历史结果](reports/RESULTS.md) · [配置与案例顺序](config/protocol.json) · [逐组结果和人工核查](results/summary.json)

历史实验包含 3 个失败案例、每例两组各一次续试，共 6 次新请求；原样组与反馈组完整校验均为 0/3。三份历史 seed 不计入这 6 次请求，不把越过首个错误等同于完整成功。

## 保留材料

- [冻结的共同 Prompt](prompts/preconditioner.md)：从三个案例的相同 prompt.md 原样保留一份，独立于当前生产 Prompt。
- [历史失败正文与诊断](evidence/seeds/)：json、reference、schema 三个 seed 的 response.json 和 error.json。
- [两组续试证据](evidence/runs/)：六份实际回答及原 validation.json。完整回答支持比较字段变化、旧补丁错误和后续错误，不只保存一句错误摘要。
- summary.json 原样保留人工审阅、重复诊断统计和研究限制；本次未执行 summarize，以免重新生成时丢失人工补充。

## 原始归档与依赖

[归档目录](../../../../artifacts/methods/v23_5/feedback_smoke_001/) 继续保存完整 material、base/feedback/unchanged messages、request、HTTP 正文和调用记录。[run.py](run.py) 的读写路径保持不变。

后续 [Schema 定位反馈实验](../feedback_schema_001/README.md) 从本实验归档的 schema seed 和输入构造历史续试；此来源路径未迁移。config/protocol.json 是研究配置副本，运行器继续读取归档 manifest。

2026-10-27 整理只复制必要证据并补齐导航，没有运行模型、生产校验或测试。历史报告的后续建议保留其当时含义。归档被 Git 忽略；证据副本不参与恢复或自动更新。
