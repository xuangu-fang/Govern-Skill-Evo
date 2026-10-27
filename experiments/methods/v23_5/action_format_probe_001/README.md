# Action 输出格式验证：材料与归档

[实验协议](PROTOCOL.md) · [历史结论](RESULTS.md) · [配置摘要](config/protocol.json)

历史实验完成 16 次请求：12 次 Actor 响应比较、4 次 Editor 比较，没有执行环境动作。Actor 的 `valid` 表示新的 action-only 约束，旧解析器能否提取合法动作须看 `projected_action_valid`。Editor 有两份通过结构校验的回答、两份 length 截断回答；这些结果不代表任务成功率改善。

## 保留材料

- [16 次逐请求结果](results/summary.json)：结束原因、usage、动作解析及 Editor 校验结论。
- [历史离线核对记录](results/offline_verification.json)：原样保留当时记录；其中校验字段不是此次整理重新执行的结果。
- [回答证据](evidence/calls/)：按原 case ID 保留全部 16 份 response.json，包含两份 Editor 有效补丁回答及两份截断失败正文。原实验没有单独保存生成后的 Candidate 文件，本次不调用补丁应用器重新生成。
- [两份失败的 HTTP 字段分界摘录](evidence/http_boundaries.json)：保留正文开头与独立推理末尾的原文片段，注明字符数及来源；完整 HTTP 仍在归档。

## 原始归档与读取

[归档目录](../../../../artifacts/methods/v23_5/action_format_probe_001/) 保存完整 manifest、输入 messages、request、HTTP 正文及每次调用的原始结果。[run.py](run.py) 继续直接读写该位置。配置摘要只选取原 manifest 的实验参数及 case 身份，不含完整输入，也不是运行器的新配置入口。

2026-10-27 整理只补充静态研究证据副本和导航，没有新增请求、重跑校验或改写历史归档。RESULTS.md 中“暂不修改正式配置”描述的是当时的实验阶段。归档被 Git 忽略，仅克隆仓库不包含完整运行数据；研究证据副本不会由运行器自动更新。
