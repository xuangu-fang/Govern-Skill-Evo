# v18 实验索引

2026-09-27 目录整理；原始内容未改写、未删除。

| 实验 | 分类 | 当前位置 |
|---|---|---|
| v18_pilot_001 | pilot | [v18_pilot_001](../../../../artifacts/methods/v18/pilot/v18_pilot_001) |
| v18_v4_formal_002 | formal | [v18_v4_formal_002](../../../../artifacts/methods/v18/formal/v18_v4_formal_002) |

## 阅读与使用

- [旧路径 → 新路径](path-map.json)：按最长旧路径前缀替换，原始绝对路径可先去掉 workspace 前缀再映射。
- 正式实验 `campaign.json`、每轮产物和最终 Skill 均随目录整体保留；阶段目录里的 retry 和失败记录不拆散。
- 原始 JSON、历史报告及冻结来源中的旧路径保持原文。原有运行脚本也未修改：其中使用旧路径的默认输出、上游输入及历史恢复命令，需要适配后才能使用。此次不是 run/resume 改造，不应直接启动旧脚本。
- `experiments/configs/`、`manifests/`、benchmark 数据和冻结来源仍在原位，不随运行目录迁移。
- Git 保留本索引和路径映射；运行目录全部忽略。
- [逐文件完整性校验](../../../../artifacts/methods/v17/archive/legacy/_organization_audit/verification.json)：v17/v18 共 22 个目录、6,582 个文件内容一致，冻结配置与相关源码未变。

v18_pilot_001 与 v18_v4_formal_002 的 campaign 均为 COMPLETE / ROUND_LIMIT。当前没有需要移入 archive/v18 的独立过期运行；原目录内的恢复记录完整保留。v19 继续使用原位的 `experiments/methods/v18/v18_formal_003/config`。

## 2026-10-12 后续迁移

本页保留此前整理的历史说明；当前实体位置见上表链接。原始运行现位于 `artifacts/methods/`，历史 JSON 和冻结代码保持原字节。新运行与恢复入口见[统一运行说明](../../RUNTIME.md)，本页旧 path-map JSON 仅记录此前迁移。
