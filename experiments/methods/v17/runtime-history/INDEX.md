# v17 实验索引

2026-09-27 目录整理；原始内容未改写、未删除。

| 实验 | 分类 | 当前位置 |
|---|---|---|
| v17_compiler_pilot_001 | pilot | [v17_compiler_pilot_001](../../../../artifacts/methods/v17/pilot/v17_compiler_pilot_001) |
| v17_diagnosis_analysis_001 | archive | [v17_diagnosis_analysis_001](../../../../artifacts/methods/v17/archive/legacy/v17_diagnosis_analysis_001) |
| v17_diagnosis_pilot_001 | archive | [v17_diagnosis_pilot_001](../../../../artifacts/methods/v17/archive/legacy/v17_diagnosis_pilot_001) |
| v17_diagnosis_pilot_002 | pilot | [v17_diagnosis_pilot_002](../../../../artifacts/methods/v17/pilot/v17_diagnosis_pilot_002) |
| v17_diagnosis_prompt3_001 | archive | [v17_diagnosis_prompt3_001](../../../../artifacts/methods/v17/archive/legacy/v17_diagnosis_prompt3_001) |
| v17_diagnosis_prompt3_analysis_001 | archive | [v17_diagnosis_prompt3_analysis_001](../../../../artifacts/methods/v17/archive/legacy/v17_diagnosis_prompt3_analysis_001) |
| v17_diagnosis_prompt3_g6_retry_001 | archive | [v17_diagnosis_prompt3_g6_retry_001](../../../../artifacts/methods/v17/archive/legacy/v17_diagnosis_prompt3_g6_retry_001) |
| v17_diagnosis_prompt4_001 | archive | [v17_diagnosis_prompt4_001](../../../../artifacts/methods/v17/archive/legacy/v17_diagnosis_prompt4_001) |
| v17_diagnosis_prompt4_analysis_001 | archive | [v17_diagnosis_prompt4_analysis_001](../../../../artifacts/methods/v17/archive/legacy/v17_diagnosis_prompt4_analysis_001) |
| v17_diagnosis_prompt5_001 | archive | [v17_diagnosis_prompt5_001](../../../../artifacts/methods/v17/archive/legacy/v17_diagnosis_prompt5_001) |
| v17_diagnosis_prompt5_analysis_001 | archive | [v17_diagnosis_prompt5_analysis_001](../../../../artifacts/methods/v17/archive/legacy/v17_diagnosis_prompt5_analysis_001) |
| v17_diagnosis_prompt7_001 | pilot | [v17_diagnosis_prompt7_001](../../../../artifacts/methods/v17/pilot/v17_diagnosis_prompt7_001) |
| v17_diagnosis_prompt7_analysis_001 | pilot | [v17_diagnosis_prompt7_analysis_001](../../../../artifacts/methods/v17/pilot/v17_diagnosis_prompt7_analysis_001) |
| v17_diagnosis_retry_001 | archive | [v17_diagnosis_retry_001](../../../../artifacts/methods/v17/archive/legacy/v17_diagnosis_retry_001) |
| v17_editor_pilot_001 | pilot | [v17_editor_pilot_001](../../../../artifacts/methods/v17/pilot/v17_editor_pilot_001) |
| v17_formal_001 | formal | [v17_formal_001](../../../../artifacts/methods/v17/formal/v17_formal_001) |
| v17_grouping_pilot_001 | pilot | [v17_grouping_pilot_001](../../../../artifacts/methods/v17/pilot/v17_grouping_pilot_001) |
| v17_grouping_pilot_002 | pilot | [v17_grouping_pilot_002](../../../../artifacts/methods/v17/pilot/v17_grouping_pilot_002) |
| v17_monitor_pilot_001 | pilot | [v17_monitor_pilot_001](../../../../artifacts/methods/v17/pilot/v17_monitor_pilot_001) |
| v17_monitor_preflight_001 | pilot | [v17_monitor_preflight_001](../../../../artifacts/methods/v17/pilot/v17_monitor_preflight_001) |

## 阅读与使用

- [旧路径 → 新路径](path-map.json)：按最长旧路径前缀替换，原始绝对路径可先去掉 workspace 前缀再映射。
- 正式实验 `campaign.json`、每轮产物和最终 Skill 均随目录整体保留；阶段目录里的 retry 和失败记录不拆散。
- 原始 JSON、历史报告及冻结来源中的旧路径保持原文。原有运行脚本也未修改：其中使用旧路径的默认输出、上游输入及历史恢复命令，需要适配后才能使用。此次不是 run/resume 改造，不应直接启动旧脚本。
- `experiments/configs/`、`manifests/`、benchmark 数据和冻结来源仍在原位，不随运行目录迁移。
- Git 保留本索引和路径映射；运行目录全部忽略。
- [逐文件完整性校验](../../../../artifacts/methods/v17/archive/legacy/_organization_audit/verification.json)：v17/v18 共 22 个目录、6,582 个文件内容一致，冻结配置与相关源码未变。

v17 保留最终 prompt7 Diagnosis 与其选取清单、作为请求来源的 diagnosis_pilot_002，以及分组、Compiler、Editor、Monitor 阶段。较早的 Diagnosis/Prompt 试验及分析放入 archive/v17；归档表示已被后续流程替代，不表示所有历史结果均失败。

## 2026-10-12 后续迁移

本页保留此前整理的历史说明；当前实体位置见上表链接。原始运行现位于 `artifacts/methods/`，历史 JSON 和冻结代码保持原字节。新运行与恢复入口见[统一运行说明](../../RUNTIME.md)，本页旧 path-map JSON 仅记录此前迁移。
