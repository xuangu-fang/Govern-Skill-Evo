# v25_7_spreadsheetbench_v41_20261116

11 月 16 日使用内网 DeepSeek v4.1 Flash。R03 和 R04 沿用 R02，R07 沿用 R06。该运行使用[早期冻结源码](../20261116_frozen_sources/README.md)。训练使用 120 道题，共 8 轮，每轮 15 题。

[冻结训练配置](config/train.json) · [冻结 Test 配置](config/test.json) · [源码合同](config/contract.json) · [运行环境](config/runtime.json) · [发布记录](results/training_summary.json) · [原始目录](../../../../artifacts/methods/v25_7/v25_7_spreadsheetbench_v41_20261116)

## 逐轮发布

| 轮次 | Parent 成功 | Candidate 成功 | 采纳／拒绝／暂缓 | 保留 Skill |
|---|---:|---:|---:|---|
| R00 | — | — | — | [初始 Skill](results/skills/R00.md) |
| R01 | 11/15 | 11/15 | 1／0／1 | [R01 Skill](results/skills/R01.md) |
| R02 | 10/15 | 10/15 | 1／0／1 | [R02 Skill](results/skills/R02.md) |
| R03 | 9/15 | 11/15 | 0／0／1 | [R03 Skill](results/skills/R03.md) |
| R04 | 12/15 | 11/15 | 0／0／2 | [R04 Skill](results/skills/R04.md) |
| R05 | 11/15 | 12/15 | 1／0／1 | [R05 Skill](results/skills/R05.md) |
| R06 | 12/15 | 12/15 | 1／0／2 | [R06 Skill](results/skills/R06.md) |
| R07 | 15/15 | 15/15 | 0／0／1 | [R07 Skill](results/skills/R07.md) |
| R08 | 11/15 | 10/15 | 1／0／2 | [R08 Skill](results/skills/R08.md) |

## 评测

R08 全量评测为 227、226、226 / 280。 [评测索引](results/evaluations.json)记录实际受测 Skill 的 SHA-256 和原始归档路径。

| 受测轮次 | 评测 | 整题成功 | 摘要 | 原件 |
|---|---|---:|---|---|
| R01 | 首测 | 228/280 | [摘要](results/spreadsheetbench_v25_7_v41_rounds_20261116__R01/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_7_v41_rounds_20261116/R01) |
| R01 | 第 2 次评测 | 226/280 | [摘要](results/spreadsheetbench_v25_7_v41_R01_R08_repeat_20261117__R01/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_7_v41_R01_R08_repeat_20261117/R01) |
| R01 | 第 3 次评测 | 217/280 | [摘要](results/spreadsheetbench_v25_7_v41_R01_third_20261117__R01/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_7_v41_R01_third_20261117/R01) |
| R02 | 首测 | 222/280 | [摘要](results/spreadsheetbench_v25_7_v41_rounds_20261116__R02/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_7_v41_rounds_20261116/R02) |
| R02 | 第 2 次评测 | 218/280 | [摘要](results/spreadsheetbench_v25_7_v41_R02_repeat_20261117__R02/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_7_v41_R02_repeat_20261117/R02) |
| R05 | 首测 | 226/280 | [摘要](results/spreadsheetbench_v25_7_v41_rounds_20261116__R05/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_7_v41_rounds_20261116/R05) |
| R06 | 首测 | 228/280 | [摘要](results/spreadsheetbench_v25_7_v41_rounds_20261116__R06/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_7_v41_rounds_20261116/R06) |
| R08 | 首测 | 227/280 | [摘要](results/v25_7_spreadsheetbench_v41_20261116__test/summary.json) | [原始目录](../../../../artifacts/methods/v25_7/v25_7_spreadsheetbench_v41_20261116/test) |
| R08 | 第 2 次评测 | 226/280 | [摘要](results/spreadsheetbench_v25_7_v41_rounds_20261116__R08/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_7_v41_rounds_20261116/R08) |
| R08 | 第 3 次评测 | 226/280 | [摘要](results/spreadsheetbench_v25_7_v41_R01_R08_repeat_20261117__R08/summary.json) | [原始目录](../../../../artifacts/analysis/spreadsheetbench_v25_7_v41_R01_R08_repeat_20261117/R08) |

在[版本索引](../README.md)可找到离线核验命令。
