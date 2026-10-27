# V24 候选版离线验收

本报告保留 rc1 冻结版的历史验收结果。当前工作区的 Preconditioner 职责、Prompt
和模型输入已有明确调整，见 [更新说明](PRECONDITIONER_ROLE.md)；不能据本报告
声称新版与旧版 Prompt 完全相同或具有相同模型效果。

候选版本：`v24_alfworld_verified_feedback_001_rc1`。
本次清理运行记录后重新执行完整验收：**100 项通过，0 失败、0 跳过、0 错误**。
真实模型请求和真实环境 episode 均为 0。

## 比较结果

- 原基线仍为 `v23_5/alfworld_verified_feedback_001`。
- Actor 的动作选择、Skill 注入、环境步进和请求重试实现与原版对照通过。
- 原 prompt 模板字节一致；实际任务事实、Plan、补丁、Gate、知识核验修复和 Memory 对照通过。
- 七模块重试、输入额度、保存响应恢复、发布前后恢复和 Actor 部分完成恢复通过。
- 模拟环境与 HTTP 响应下，新版 Actor 的实际 CLI、动作反馈及最终评估通过。
- 使用原 R01–R03 记录对照；独立进程禁止旧源码导入与读取后，R01 完整重放及恢复通过。

## 明确允许的变化

运行记录已简化为版本名称、路径和实际内容，移除额外机器标识及其相关校验。
初始 Skill 配置只保留来源和正文。Actor 使用 v24 自带入口。
Verifier/Repair 输入同步减少这部分运行元数据，任务事实、原文 prompt 和方法不变。
因此本报告证明已覆盖路径的行为对照通过，不声称每个输入字节都与旧记录相同。

测试总数由上一轮 93 项调整为本次 100 项：取消两个已移除机制的测试，
增加九项新版 Actor 行为及实际入口测试。此前原版与共享 Actor 的 674 项通过结果
只作为历史记录，不代替本次对新版 Actor 的验证。

## 保存位置

候选材料中的 [validation/report.json](../../../experiments/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/validation/report.json)保留历史机器可读结论。完整 [tests.xml](../../../artifacts/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/validation/tests.xml)
与 [console.txt](../../../artifacts/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/validation/console.txt)
已于 2026-10-27 归档至 `artifacts/methods/v24/candidates/v24_alfworld_verified_feedback_001_rc1/validation/`，由 Git 忽略。
源码、配置、任务划分、测试副本与历史报告保留原位和原文；本次整理没有重新运行验收。

[候选导航与历史路径说明](../../../experiments/methods/v24/candidates/README.md)

## 复验

在原项目中执行，输出目录须为新目录。离线对照需要保留原实验档案和旧版测试夹具。

```bash
python scripts/runs/verify_v24_offline.py --output artifacts/methods/v24/offline_recheck
```

离线通过不证明真实成功率不下降。后续小规模真实验证和同条件效果对照
按照 [实验方案](NEXT_EXPERIMENTS.md) 单独授权、单独执行。
