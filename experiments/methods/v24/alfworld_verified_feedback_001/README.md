# V24 ALFWorld 配置来源

该实验以 v23.5 同名实验的最终配置为来源。
`config/baseline_manifest.json` 记录来源名称、目录和普通文件清单。

当前候选为 `v24_alfworld_verified_feedback_001_rc1`，材料位于
[候选导航与日志现址](../candidates/README.md)。
模型、任务、prompt 原文、Actor 行为和预算沿用原基线；方法版本与适配器入口更新，
运行记录简化。原实验不被改写，也不复制为新实验成绩。

## 来源与读取边界

本目录只保存来源说明和 [baseline_manifest.json](config/baseline_manifest.json)，不是已完成的六轮运行目录。正式配置、任务划分和单轮计划保存在 RC1 候选包中。

[基线准备代码](../../../../src/skill_evolution/v24/baseline.py)仍读取以下原位置：

- [v23.5 正式配置](../../v23_5/alfworld_verified_feedback_001/config/campaign.json)、[任务划分](../../v23_5/alfworld_verified_feedback_001/data/)、[预算](../../v23_5/alfworld_verified_feedback_001/config/budget.json)和[初始基线说明](../../v23_5/alfworld_verified_feedback_001/config/initial_baseline_reference.json)。
- 原归档中的 [S1/config.json](../../../../artifacts/methods/v23_5/alfworld_verified_feedback_001/S1/config.json) 与 [S1/initial_config.json](../../../../artifacts/methods/v23_5/alfworld_verified_feedback_001/S1/initial_config.json)。

这些来源未迁移或改写。RC1 的历史验收与后来的 [单轮 smoke 结果](../alfworld_rc1_smoke_001/REPORT.md)分开阅读；当前工作区另有 [Preconditioner 调整](../../../../docs/methods/v24/PRECONDITIONER_ROLE.md)，不能据 RC1 历史报告推断新 Prompt 的效果。

v25 继续从 RC1 的 [config/campaign.json](../candidates/v24_alfworld_verified_feedback_001_rc1/config/campaign.json)读取继承预算。配置和冻结 Prompt 保持原路径。2026-10-27 本批只整理导航与候选测试日志，没有运行实验或测试。
