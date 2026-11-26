# skilladam_spreadsheetbench_v25_5_feedback_20261112_201115

11 月 12 日独立训练，复用对齐 Actor 配置。运行目录保存了原生 checkpoint、恢复入口和最终 Skill，独立冻结配置副本未找到。

[逐轮原生 checkpoint](results/checkpoints.json) · [评测索引](results/evaluations.json) · [训练归档](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261112_201115) · [配置来源](../../aligned_actor/skilladam_v25_1_actor_aligned_20261030_001/config/shared_config.json)

| 轮次 | 选优决策 | Skill |
|---|---|---|
| R00 | 初始 | [Skill](results/skills/R00.md) |
| R01 | 沿用 | [Skill](results/skills/R01.md) |
| R02 | 采纳 | [Skill](results/skills/R02.md) |
| R03 | 沿用 | [Skill](results/skills/R03.md) |
| R04 | 采纳 | [Skill](results/skills/R04.md) |
| R05 | 沿用 | [Skill](results/skills/R05.md) |
| R06 | 沿用 | [Skill](results/skills/R06.md) |
| R07 | 沿用 | [Skill](results/skills/R07.md) |
| R08 | 沿用 | [Skill](results/skills/R08.md) |

## 评测

| 受测 Skill | Actor | 成功 | 摘要 | 原始目录 |
|---|---|---:|---|---|
| [R02](results/skills/R02.md) | `deepseek-flash` | 207/280 | [摘要](results/spreadsheetbench_v25_6_skilladam_rounds_20261112__SkillAdam_R02/summary.json) | [轨迹](../../../../../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/SkillAdam_R02) |
| [R08](results/skills/R08.md) | `deepseek-flash` | 220/280 | [摘要](results/skilladam_spreadsheetbench_v25_5_feedback_20261112_201115__test280/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v25_5_feedback_20261112_201115/test280) |
