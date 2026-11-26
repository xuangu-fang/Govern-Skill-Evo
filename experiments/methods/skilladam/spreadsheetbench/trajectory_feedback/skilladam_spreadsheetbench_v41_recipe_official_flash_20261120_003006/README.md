# skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006

11 月 20 日使用官方 DeepSeek Flash 训练。R06 采纳后，R07 和 R08 沿用同一份 Skill。五次同模型测试为 220、225、230、228、225 / 280；GPT-5.4-mini 全量评测为 177/280。

[逐轮原生 checkpoint](results/checkpoints.json) · [评测索引](results/evaluations.json) · [训练归档](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006) · [配置来源](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/config/shared_config.json)

| 轮次 | 选优决策 | Skill |
|---|---|---|
| R00 | 初始 | [Skill](results/skills/R00.md) |
| R01 | 采纳 | [Skill](results/skills/R01.md) |
| R02 | 采纳 | [Skill](results/skills/R02.md) |
| R03 | 沿用 | [Skill](results/skills/R03.md) |
| R04 | 沿用 | [Skill](results/skills/R04.md) |
| R05 | 采纳 | [Skill](results/skills/R05.md) |
| R06 | 采纳 | [Skill](results/skills/R06.md) |
| R07 | 沿用 | [Skill](results/skills/R07.md) |
| R08 | 沿用 | [Skill](results/skills/R08.md) |

## 评测

| 受测 Skill | Actor | 成功 | 摘要 | 原始目录 |
|---|---|---:|---|---|
| [R08](results/skills/R08.md) | `gpt-5.4-mini` | 177/280 | [摘要](results/spreadsheetbench_skilladam_1120_final_gpt54mini_20261120__test/summary.json) | [轨迹](../../../../../../artifacts/analysis/spreadsheetbench_skilladam_1120_final_gpt54mini_20261120/test) |
| [R02](results/skills/R02.md) | `deepseek-flash` | 218/280 | [摘要](results/R02_R05_R06_retests_20261120_215624__R02/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R02_R05_R06_retests_20261120_215624/R02) |
| [R05](results/skills/R05.md) | `deepseek-flash` | 224/280 | [摘要](results/R02_R05_R06_retests_20261120_215624__R05/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R02_R05_R06_retests_20261120_215624/R05) |
| [R06](results/skills/R06.md) | `deepseek-flash` | 225/280 | [摘要](results/R02_R05_R06_retests_20261120_215624__R06/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R02_R05_R06_retests_20261120_215624/R06) |
| [R05](results/skills/R05.md) | `deepseek-flash` | 224/280 | [摘要](results/R05_R06_retests_20261120_130320__R05/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R05_R06_retests_20261120_130320/R05) |
| [R06](results/skills/R06.md) | `deepseek-flash` | 225/280 | [摘要](results/R05_R06_retests_20261120_130320__R06/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R05_R06_retests_20261120_130320/R06) |
| [R06](results/skills/R06.md) | `deepseek-flash` | 228/280 | [摘要](results/R06_fourth_test_20261120_133647__R06/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R06_fourth_test_20261120_133647/R06) |
| [R06](results/skills/R06.md) | `deepseek-flash` | 230/280 | [摘要](results/R06_third_test_20261120_132028__R06/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/R06_third_test_20261120_132028/R06) |
| [R01](results/skills/R01.md) | `deepseek-flash` | 222/280 | [摘要](results/checkpoint_tests_20261120_124039__R01/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/checkpoint_tests_20261120_124039/R01) |
| [R02](results/skills/R02.md) | `deepseek-flash` | 220/280 | [摘要](results/checkpoint_tests_20261120_124039__R02/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/checkpoint_tests_20261120_124039/R02) |
| [R05](results/skills/R05.md) | `deepseek-flash` | 231/280 | [摘要](results/checkpoint_tests_20261120_124039__R05/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/checkpoint_tests_20261120_124039/R05) |
| [R08](results/skills/R08.md) | `deepseek-flash` | 220/280 | [摘要](results/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006__test280/summary.json) | [轨迹](../../../../../../artifacts/methods/skilladam/spreadsheetbench/trajectory_feedback/skilladam_spreadsheetbench_v41_recipe_official_flash_20261120_003006/test280) |
