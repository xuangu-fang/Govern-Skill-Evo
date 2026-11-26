# SkillOpt SpreadsheetBench 正式运行

11 月 22 日运行使用官方 DeepSeek Flash。完成 4 个 epoch 和 8 次普通更新。Selection 选中第 7 步，**39/40**。R07 和 R08 使用同一份保留 Skill，三次官方测试为 **226、220、221/280**。GPT-5.4-mini 测试为 **178/280**，其中 `test:191-40` 由独立补测补齐。

[训练配置](config/skillopt.json) · [训练 Actor](config/train_actor.json) · [测试 Actor](config/test_actor.json) · [Selection](results/selection.json) · [Best Skill](results/best_skill.md) · [普通与慢更新](results/checkpoints.json) · [评测索引](results/evaluations.json)

R02 的两份文本分别来自第 2 步的[占位前候选](results/skills/R02_pre_placeholder.md)和 epoch 结束后的[保留快照](results/skills/R02.md)。两者哈希不同，各次评测按实际受测文本登记。第 2–4 个 epoch 的慢更新均未通过 Selection Gate。

| 实际受测 Skill | Actor | 成功 | 摘要 | 原始目录 |
|---|---|---:|---|---|
| [R02_pre_placeholder](results/skills/R02_pre_placeholder.md) | `deepseek-flash` | 220/280 | [摘要](results/spreadsheetbench_skillopt_R02_pre_placeholder_retest280_20261123_SsyMlq__test/summary.json) | [轨迹](../../../../../artifacts/analysis/spreadsheetbench_skillopt_R02_pre_placeholder_retest280_20261123_SsyMlq/test) |
| [R02_pre_placeholder](results/skills/R02_pre_placeholder.md) | `deepseek-flash` | 228/280 | [摘要](results/spreadsheetbench_skillopt_R02_pre_placeholder_test280_20261123_82RTMo__test/summary.json) | [轨迹](../../../../../artifacts/analysis/spreadsheetbench_skillopt_R02_pre_placeholder_test280_20261123_82RTMo/test) |
| [R02_pre_placeholder](results/skills/R02_pre_placeholder.md) | `deepseek-flash` | 226/280 | [摘要](results/spreadsheetbench_skillopt_R02_pre_placeholder_third280_20261123_qSd9pv__test/summary.json) | [轨迹](../../../../../artifacts/analysis/spreadsheetbench_skillopt_R02_pre_placeholder_third280_20261123_qSd9pv/test) |
| [best_skill](results/best_skill.md) | `gpt-5.4-mini` | 178/280 | [摘要](results/spreadsheetbench_skillopt_final_gpt54mini_20261124__test/summary.json) | [轨迹](../../../../../artifacts/analysis/spreadsheetbench_skillopt_final_gpt54mini_20261124/test) |
| [best_skill](results/best_skill.md) | `deepseek-flash` | 220/280 | [摘要](results/spreadsheetbench_skillopt_r07_retest_20261122_204550__test/summary.json) | [轨迹](../../../../../artifacts/analysis/spreadsheetbench_skillopt_r07_retest_20261122_204550/test) |
| [best_skill](results/best_skill.md) | `deepseek-flash` | 221/280 | [摘要](results/spreadsheetbench_skillopt_r07_third_20261122_205639__test/summary.json) | [轨迹](../../../../../artifacts/analysis/spreadsheetbench_skillopt_r07_third_20261122_205639/test) |
| [R01](results/skills/R01.md) | `deepseek-flash` | 223/280 | [摘要](results/spreadsheetbench_skillopt_step_tests_20261122_214430__R01/summary.json) | [轨迹](../../../../../artifacts/analysis/spreadsheetbench_skillopt_step_tests_20261122_214430/R01) |
| [R02](results/skills/R02.md) | `deepseek-flash` | 224/280 | [摘要](results/spreadsheetbench_skillopt_step_tests_20261122_214430__R02/summary.json) | [轨迹](../../../../../artifacts/analysis/spreadsheetbench_skillopt_step_tests_20261122_214430/R02) |
| [best_skill](results/best_skill.md) | `deepseek-flash` | 226/280 | [摘要](results/spreadsheetbench_v25_8__test/summary.json) | [轨迹](../../../../../artifacts/methods/skillopt/spreadsheetbench_v25_8/test) |
