# v25_6_spreadsheetbench_deepseek

官方 DeepSeek Flash，训练使用 120 道题，共 8 轮，每轮 15 题。R02 的 Gate 保留 R01，R07 的 Diagnosis 判定无需更新并沿用 R06。两题专项复跑使用 R08 Skill，结果为 1/2，题目为 `test:38985` 和 `test:48969`。共用 R00 的 203/280 和同期 SkillAdam 评测见[原对照目录](../../../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/)。

[冻结训练配置](config/train.json) · [冻结 Test 配置](config/test.json) · [源码合同](config/contract.json) · [运行环境](config/runtime.json) · [发布记录](results/training_summary.json) · [原始目录](../../../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek)

## 逐轮发布

| 轮次 | Parent 成功 | Candidate 成功 | 采纳／拒绝／暂缓 | 保留 Skill |
|---|---:|---:|---:|---|
| R00 | — | — | — | [初始 Skill](results/skills/R00.md) |
| R01 | 10/15 | 11/15 | 1／0／2 | [R01 Skill](results/skills/R01.md) |
| R02 | 14/15 | 11/15 | 0／0／1 | [R02 Skill](results/skills/R02.md) |
| R03 | 10/15 | 12/15 | 2／0／0 | [R03 Skill](results/skills/R03.md) |
| R04 | 10/15 | 12/15 | 2／0／0 | [R04 Skill](results/skills/R04.md) |
| R05 | 12/15 | 13/15 | 1／0／1 | [R05 Skill](results/skills/R05.md) |
| R06 | 11/15 | 12/15 | 1／0／1 | [R06 Skill](results/skills/R06.md) |
| R07 | 15/15 | — | — | [R07 Skill](results/skills/R07.md) |
| R08 | 13/15 | 12/15 | 1／0／1 | [R08 Skill](results/skills/R08.md) |

## 评测

R08 三次全量评测为 225、229、222 / 280。 [评测索引](results/evaluations.json)记录实际受测 Skill 的 SHA-256 和原始归档路径。

| 受测轮次 | 评测 | 整题成功 | 摘要 | 原件 |
|---|---|---:|---|---|
| R01 | 首测 | 216/280 | [摘要](results/spreadsheetbench_v25_6_skilladam_rounds_20261112__v25_6_R01/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R01) |
| R02 | 首测 | 206/280 | [摘要](results/R02_R03_20261113_191807__R02/summary.json) | [原始目录](../../../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/R02_R03_20261113_191807/R02) |
| R03 | 首测 | 210/280 | [摘要](results/spreadsheetbench_v25_6_skilladam_rounds_20261112__v25_6_R03/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R03) |
| R03 | 第 2 次评测 | 204/280 | [摘要](results/R03_R08_20261113_1200__R03/summary.json) | [原始目录](../../../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/R03_R08_20261113_1200/R03) |
| R03 | 第 3 次评测 | 210/280 | [摘要](results/R02_R03_20261113_191807__R03/summary.json) | [原始目录](../../../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/R02_R03_20261113_191807/R03) |
| R04 | 首测 | 226/280 | [摘要](results/spreadsheetbench_v25_6_skilladam_rounds_20261112__v25_6_R04/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R04) |
| R05 | 首测 | 229/280 | [摘要](results/spreadsheetbench_v25_6_skilladam_rounds_20261112__v25_6_R05/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R05) |
| R06 | 首测 | 231/280 | [摘要](results/spreadsheetbench_v25_6_skilladam_rounds_20261112__v25_6_R06/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_6_skilladam_rounds_20261112/v25_6_R06) |
| R08 | 首测 | 225/280 | [摘要](results/v25_6_spreadsheetbench_deepseek__test/summary.json) | [原始目录](../../../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/test) |
| R08 | 第 2 次评测 | 229/280 | [摘要](results/test280_20261112_225939__test/summary.json) | [原始目录](../../../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/test280_20261112_225939/test) |
| R08 | 两题专项复跑 | 1/2 | [摘要](results/R08_38985_48969_20261113_104005__test/summary.json) | [原始目录](../../../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/R08_38985_48969_20261113_104005/test) |
| R08 | 第 3 次评测 | 222/280 | [摘要](results/R03_R08_20261113_1200__R08/summary.json) | [原始目录](../../../../artifacts/methods/v25_6/v25_6_spreadsheetbench_deepseek/reruns/R03_R08_20261113_1200/R08) |

在[版本索引](../README.md)可找到离线核验命令。
