# batch60_workers60_20261105_004702

完成训练，已记录 10 轮。

[冻结配置](config/frozen.json) · [进度回执](reports/native/checkpoint.json) · [初始 Skill](config/initial_skill.md) · [原始训练](../../../../../baselines/searchqa_skilladam/batch60_workers60_20261105_004702) · [运行入口](../../../../../../scripts/runs/run_searchqa_skilladam.py) · [原调度状态](reports/launch/searchqa_skilladam_batch60_workers60_20261105_004702/status.json) · [最终 Skill](results/final_skill.md)

[原实验说明](../../../../../automations/searchqa_skilladam_batch60_workers60_20261105_004702/README.md)

## 评测

| 评测 | Actor | EM 题数 | Token F1 | 证据 |
| --- | --- | ---: | ---: | --- |
| 最终 Skill 终测 | deepseek-flash | 1,181/1,400 | 90.88% | [受测 Skill](results/batch60_workers60_20261105_004702/skill.md) · [摘要](results/batch60_workers60_20261105_004702/report.json) · [评测计划](../../../../../evaluations/searchqa_skilladam/batch60_workers60_20261105_004702/plan.json) · [原始逐题回执](../../../../../evaluations/searchqa_skilladam/batch60_workers60_20261105_004702/batch/records.json) |
| 最终 Skill 复测 | deepseek-flash | 1,186/1,400 | 91.30% | [受测 Skill](results/batch60_workers60_20261105_004702_retest_20261106_080507/skill.md) · [摘要](results/batch60_workers60_20261105_004702_retest_20261106_080507/report.json) · [评测计划](../../../../../evaluations/searchqa_skilladam/batch60_workers60_20261105_004702_retest_20261106_080507/plan.json) · [原始逐题回执](../../../../../evaluations/searchqa_skilladam/batch60_workers60_20261105_004702_retest_20261106_080507/batch/records.json) |

[历史验收清单](../../../../../benchmarks/searchqa/remaining-history.json) · [SearchQA 实验索引](../../../../SEARCHQA.md)
