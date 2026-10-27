# Preconditioner 输出协议：审计材料

[历史审计报告](reports/AUDIT.md) · [HTTP 审计元数据](results/http_audit.json) · [历史测试记录](results/validation.json)

本目录记录输出协议与错误定位修改，以及两次已有 JSON 失败的 HTTP 正文核查。历史测试数字保持原文，本次整理没有执行这些测试或生产校验函数。

## 必要失败证据

- [001 实验 / 第 001 次回答](evidence/knowledge_only_single_round_001_attempt_001/response.json)及[原校验记录](evidence/knowledge_only_single_round_001_attempt_001/validation.json)。
- [002 实验 / 第 002 次回答](evidence/knowledge_only_single_round_002_attempt_002/response.json)及[原校验记录](evidence/knowledge_only_single_round_002_attempt_002/validation.json)。
- [HTTP 字段分界摘录](evidence/http_boundaries.json)：从原 HTTP 直接提取正文开头与独立推理末尾，注明来源及字符数；不据此断言模型或代理的根因。

两份 response.json 和 validation.json 均按原字节复制。原校验记录是当时的诊断，更新后的 JSON 错误定位见 http_audit.json；两者不互相覆盖。

## 原始归档与边界

完整输入、请求与 HTTP 仍属于 [knowledge_only_single_round_001](../../../../artifacts/methods/v23_5/knowledge_only_single_round_001/runs/R03/preconditioner/memory_v3/attempts/001/) 和 [knowledge_only_single_round_002](../../../../artifacts/methods/v23_5/knowledge_only_single_round_002/runs/R03/preconditioner/memory_v3/attempts/002/)。不为这次只读审计再复制一套运行目录，不改变其他实验的读取路径。

2026-10-27 整理只补充证据与导航，没有新模型请求或重新运行历史校验。完整归档被 Git 忽略，当前目录保留可独立查看的结论及失败回答。
