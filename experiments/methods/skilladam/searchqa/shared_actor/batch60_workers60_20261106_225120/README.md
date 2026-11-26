# batch60_workers60_20261106_225120

完成训练，已记录 10 轮。

[冻结配置](config/frozen.json) · [进度回执](reports/native/checkpoint.json) · [初始 Skill](config/initial_skill.md) · [原始训练](../../../../../baselines/searchqa_skilladam/batch60_workers60_20261106_225120) · [运行入口](../../../../../../scripts/runs/run_searchqa_skilladam.py) · [原调度状态](reports/launch/searchqa_skilladam_batch60_workers60_20261106_225120/status.json) · [最终 Skill](results/final_skill.md)

## 评测

| 评测 | Actor | EM 题数 | Token F1 | 证据 |
| --- | --- | ---: | ---: | --- |
| 最终 Skill 终测 | deepseek-flash | 1,172/1,400 | 90.56% | [受测 Skill](results/batch60_workers60_20261106_225120/skill.md) · [摘要](results/batch60_workers60_20261106_225120/report.json) · [评测计划](../../../../../evaluations/searchqa_skilladam/batch60_workers60_20261106_225120/plan.json) · [原始逐题回执](../../../../../evaluations/searchqa_skilladam/batch60_workers60_20261106_225120/batch/records.json) |
| 最终 Skill 复测 | deepseek-flash | 1,166/1,400 | 90.55% | [受测 Skill](results/batch60_workers60_20261106_225120_retest_20261107_030741/skill.md) · [摘要](results/batch60_workers60_20261106_225120_retest_20261107_030741/report.json) · [评测计划](../../../../../evaluations/searchqa_skilladam/batch60_workers60_20261106_225120_retest_20261107_030741/plan.json) · [原始逐题回执](../../../../../evaluations/searchqa_skilladam/batch60_workers60_20261106_225120_retest_20261107_030741/batch/records.json) |

[历史验收清单](../../../../../benchmarks/searchqa/remaining-history.json) · [SearchQA 实验索引](../../../../SEARCHQA.md)
