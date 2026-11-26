# v25_7_spreadsheetbench_official_20261118_212017

11 月 18 日使用官方 DeepSeek Flash 训练，11 月 19 日启动该运行的 R08 评测。源码合同与当前维护的 v25.7 版本一致。训练使用 120 道题，共 8 轮，每轮 15 题。

[冻结训练配置](config/train.json) · [冻结 Test 配置](config/test.json) · [源码合同](config/contract.json) · [运行环境](config/runtime.json) · [发布记录](results/training_summary.json) · [原始目录](../../../../artifacts/methods/v25_7/v25_7_spreadsheetbench_official_20261118_212017)

## 逐轮发布

| 轮次 | Parent 成功 | Candidate 成功 | 采纳／拒绝／暂缓 | 保留 Skill |
|---|---:|---:|---:|---|
| R00 | — | — | — | [初始 Skill](results/skills/R00.md) |
| R01 | 10/15 | 12/15 | 1／0／3 | [R01 Skill](results/skills/R01.md) |
| R02 | 10/15 | 11/15 | 1／0／4 | [R02 Skill](results/skills/R02.md) |
| R03 | 9/15 | 9/15 | 2／0／4 | [R03 Skill](results/skills/R03.md) |
| R04 | 10/15 | 10/15 | 1／0／3 | [R04 Skill](results/skills/R04.md) |
| R05 | 12/15 | 12/15 | 1／1／3 | [R05 Skill](results/skills/R05.md) |
| R06 | 7/15 | 10/15 | 3／0／1 | [R06 Skill](results/skills/R06.md) |
| R07 | 13/15 | 13/15 | 1／0／1 | [R07 Skill](results/skills/R07.md) |
| R08 | 11/15 | 12/15 | 1／0／3 | [R08 Skill](results/skills/R08.md) |

## 评测

R08 全量评测为 216 / 280。 [评测索引](results/evaluations.json)记录实际受测 Skill 的 SHA-256 和原始归档路径。

| 受测轮次 | 评测 | 整题成功 | 摘要 | 原件 |
|---|---|---:|---|---|
| R08 | 首测 | 216/280 | [摘要](results/v25_7_spreadsheetbench_official_20261118_212017__test/summary.json) | [原始目录](../../../../artifacts/methods/v25_7/v25_7_spreadsheetbench_official_20261118_212017/test) |

在[版本索引](../README.md)可找到离线核验命令。
