# ALFWorld 两次联合运行的归档与汇总文件清理记录

## 单个实验的记录入口

| 原运行 | 归属 | 已归档材料 |
|---|---|---|
| 2026-10-30 | [Autonomous GSE v24.1](../../experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/README.md) | 5 份训练启动文件、4 份首测启动文件。首测执行时间、耗时和额外请求数见该实验的 [执行记录](../../experiments/methods/v24_1/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001/results/alfworld_reviewed_no_review_workers10_official_deepseek_flash_20261030_001_test134/execution.json)。 |
| 2026-10-30 | [SkillAdam 原生重试 · Actor 和优化器均用官方模型](../../experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/README.md) | 5 份训练启动文件、4 份首测启动文件、12 份首轮补丁[失败与恢复记录](../../artifacts/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/recovery/iteration_0_patch)。首测时间及请求数见该实验的 [执行记录](../../experiments/methods/skilladam/alfworld/native_retry/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001/results/skilladam_alfworld_official_actor_optimizer_deepseek_flash_20261030_001_test134/execution.json)。 |
| 2026-10-25 | [SkillAdam 共用 Actor 配置](../../experiments/methods/skilladam/alfworld/shared_actor/skilladam_current_actor_20261025/README.md) | 5 份启动文件，包括训练和最终评测所在进程的日志与状态。 |
| 2026-10-25 | [SkillOpt 基线](../../experiments/baselines/alfworld/alfworld_current_actor_20261025/README.md) | 5 份启动文件。[Initial Skill](../../artifacts/baselines/skillopt/alfworld_current_actor_20261025/test_eval_baseline)、[Best Skill](../../artifacts/baselines/skillopt/alfworld_current_actor_20261025/test_eval) 和 [No Skill](../../artifacts/baselines/noskill/alfworld_current_actor_20261025) 的逐任务结果沿用各自原目录。 |

40 份原始文件放在各实验的本地 `artifacts/` 下，按仓库惯例由 Git 忽略。两份首测执行记录放在各实验的 `results/` 下，可随实验说明纳入版本管理。旧路径通过[路径映射](../../experiments/methods/canonical-paths.json)查找。

## 已清理的汇总文件

- 2026-10-25 的 `comparison.md` 和 `comparison.json` 已删除。四组成绩可从各实验目录读回，当晚监控记录保留完成通知和时间。
- 2026-10-30 的 `final_test_report.json` 已删除。两份首测执行记录分别引用本实验的进程回执、请求用量和逐任务轨迹，并保留当时的核验结论与核验时间。SkillAdam 的补丁恢复台账归在训练实验的恢复目录。

## 有独立用途的历史文件

- 10-25 的[监控状态](../../artifacts/baselines/overnight_20261025/monitor_state.json)保留启动、异常停机、重试通知和完成时间线。[调度登记](../../artifacts/baselines/overnight_20261025/automations.json)和[进程保活记录](../../artifacts/baselines/overnight_20261025/keep_awake.json)各有用途。[运行入口](../../scripts/runs/alfworld/launch_alfworld_overnight.py)仍读取[计划](../../experiments/baselines/overnight_20261025/schedule.json)和[输入清单](../../experiments/baselines/overnight_20261025/manifest.json)。
- 10-30 的 [final_monitor_report.json](../../experiments/automations/alfworld_v24_1_skilladam_20261030_001/execution/final_monitor_report.json) 记录 v24.1 已结束、SkillAdam 受阻、自动化暂停的时点；[monitor_state.json](../../experiments/automations/alfworld_v24_1_skilladam_20261030_001/execution/monitor_state.json) 记录恢复后两次首测完成、核验和通知的时点。两个时点都保留。
- 10-30 的[首测前训练快照](../../experiments/automations/alfworld_v24_1_skilladam_20261030_001/pre_test_training_snapshot.json)、[原调度计划](../../experiments/automations/alfworld_v24_1_skilladam_20261030_001/plan.json)、[当时的调度条件](../../experiments/automations/alfworld_v24_1_skilladam_20261030_001/test_start_condition.json)、[历史修订](../../experiments/automations/alfworld_v24_1_skilladam_20261030_001/revisions)和原目录中的自动化脚本、离线检查、模型配置说明均保留。单实验入口直接指向本实验的训练、首测或恢复记录。
