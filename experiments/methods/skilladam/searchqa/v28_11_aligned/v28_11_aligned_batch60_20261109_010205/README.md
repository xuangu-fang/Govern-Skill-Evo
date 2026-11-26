# v28_11_aligned_batch60_20261109_010205

完成训练，已记录 10 轮。

[冻结配置](config/frozen.json) · [进度回执](reports/native/checkpoint.json) · [初始 Skill](config/initial_skill.md) · [原始训练](../../../../../baselines/searchqa_skilladam/v28_11_aligned_batch60_20261109_010205) · [运行入口](../../../../../../scripts/runs/run_searchqa_skilladam.py) · [原调度状态](reports/launch/searchqa_skilladam_v28_11_aligned_batch60_20261109_010205/status.json) · [最终 Skill](results/final_skill.md)

## 评测

| 评测 | Actor | EM 题数 | Token F1 | 证据 |
| --- | --- | ---: | ---: | --- |
| skilladam_R01 保留 Skill | deepseek-flash | 1,145/1,400 | 89.79% | [受测 Skill](results/searchqa_checkpoints_20261111/skilladam_R01/skill.md) · [摘要](results/searchqa_checkpoints_20261111/skilladam_R01/report.json) · [评测计划](../../../../../evaluations/searchqa_checkpoints_20261111/skilladam_R01/plan.json) · [原始逐题回执](../../../../../evaluations/searchqa_checkpoints_20261111/skilladam_R01/batch/records.json) |
| skilladam_R04 保留 Skill | deepseek-flash | 1,145/1,400 | 89.84% | [受测 Skill](results/searchqa_checkpoints_20261111/skilladam_R04/skill.md) · [摘要](results/searchqa_checkpoints_20261111/skilladam_R04/report.json) · [评测计划](../../../../../evaluations/searchqa_checkpoints_20261111/skilladam_R04/plan.json) · [原始逐题回执](../../../../../evaluations/searchqa_checkpoints_20261111/skilladam_R04/batch/records.json) |
| 最终 Skill 终测 | deepseek-flash | 1,172/1,400 | 90.86% | [受测 Skill](results/v28_11_aligned_batch60_20261109_010205/skill.md) · [摘要](results/v28_11_aligned_batch60_20261109_010205/report.json) · [评测计划](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261109_010205/plan.json) · [原始逐题回执](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261109_010205/batch/records.json) |

[历史验收清单](../../../../../benchmarks/searchqa/remaining-history.json) · [SearchQA 实验索引](../../../../SEARCHQA.md)
