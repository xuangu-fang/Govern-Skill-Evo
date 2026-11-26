# v28_11_aligned_batch60_20261108_224443

完成训练，已记录 10 轮。

[冻结配置](config/frozen.json) · [进度回执](reports/native/checkpoint.json) · [初始 Skill](config/initial_skill.md) · [原始训练](../../../../../baselines/searchqa_skilladam/v28_11_aligned_batch60_20261108_224443) · [运行入口](../../../../../../scripts/runs/run_searchqa_skilladam.py) · [原调度状态](reports/launch/searchqa_skilladam_v28_11_aligned_batch60_20261108_224443/status.json) · [最终 Skill](results/final_skill.md)

## 评测

| 评测 | Actor | EM 题数 | Token F1 | 证据 |
| --- | --- | ---: | ---: | --- |
| 最终 Skill 终测 | deepseek-flash | 1,202/1,400 | 92.09% | [受测 Skill](results/v28_11_aligned_batch60_20261108_224443/skill.md) · [摘要](results/v28_11_aligned_batch60_20261108_224443/report.json) · [评测计划](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261108_224443/plan.json) · [原始逐题回执](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261108_224443/batch/records.json) |
| 最终 Skill 复测 | deepseek-flash | 1,188/1,400 | 91.42% | [受测 Skill](results/v28_11_aligned_batch60_20261108_224443_retest_20261109_005148/skill.md) · [摘要](results/v28_11_aligned_batch60_20261108_224443_retest_20261109_005148/report.json) · [评测计划](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261108_224443_retest_20261109_005148/plan.json) · [原始逐题回执](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261108_224443_retest_20261109_005148/batch/records.json) |

[历史验收清单](../../../../../benchmarks/searchqa/remaining-history.json) · [SearchQA 实验索引](../../../../SEARCHQA.md)
