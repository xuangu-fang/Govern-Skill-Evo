# v19 历史归档

这里保留被后续方案替代的实验，不删除原始数据，不将失败输出当作有效结果。

| 目录 | 用途 |
|---|---|
| [v19_v4_pilot_001](v19_v4_pilot_001/) | 早期 v19 流程及其运行历史，不是当前拆分流程的最终两轮 Pilot |
| [local_review_once_001](v19_v4_local_review_once_001/) | 首次局部审阅尝试，连接失败 |
| [local_review_once_002](v19_v4_local_review_once_002/) | 输入预算及输出截断阶段的尝试 |
| [local_review_once_003](v19_v4_local_review_once_003/) | 包含旧上下文补充协议的审阅尝试 |
| [local_review_once_004](v19_v4_local_review_once_004/) | 被统一重跑替代的审阅尝试 |
| [launch_metadata](launch_metadata/) | 上述阶段的顶层日志和启动记录 |
| [_organization_audit](_organization_audit/) | 本次移动前逐文件 SHA256 清单、迁移脚本及校验结果 |

最终两轮 Pilot 见 [v19 索引](../../v19/INDEX.md)。
原始文件中的旧绝对路径和旧源码摘要不改写，按 [路径映射](../../v19/path-map.json) 找到当前位置。
已纳入有效阶段校验或来源链的失败尝试仍随该阶段保存，避免拆散证据链。
所有历史脚本仅供审计；不应直接运行或 resume。
