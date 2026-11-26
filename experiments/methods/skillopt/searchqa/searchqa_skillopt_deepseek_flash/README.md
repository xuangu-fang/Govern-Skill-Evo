# searchqa_skillopt_deepseek_flash

完成训练，已记录 40 步。

[冻结配置](config/run.json) · [进度回执](reports/selection.json) · [初始 Skill](config/initial_skill.md) · [原始训练](../../../../baselines/searchqa_skillopt_deepseek_flash) · [运行入口](../../../../../scripts/runs/skillopt/searchqa/run.py) · [最终 Skill](results/best_skill.md)

## 评测

| 评测 | Actor | EM 题数 | Token F1 | 证据 |
| --- | --- | ---: | ---: | --- |
| 最终 Skill 终测 | deepseek-flash | 1,174/1,400 | 90.40% | [受测 Skill](results/test/skill.md) · [摘要](results/test/report.json) · [评测计划](../../../../baselines/searchqa_skillopt_deepseek_flash/test/plan.json) · [原始逐题回执](../../../../baselines/searchqa_skillopt_deepseek_flash/test/batch/records.json) |
| 最终 Skill 复测 | deepseek-flash | 1,173/1,400 | 90.57% | [受测 Skill](results/searchqa_skillopt_best_parallel_20261123_011258/retest_1/test/skill.md) · [摘要](results/searchqa_skillopt_best_parallel_20261123_011258/retest_1/test/report.json) · [评测计划](../../../../evaluations/searchqa_skillopt_best_parallel_20261123_011258/retest_1/test/plan.json) · [原始逐题回执](../../../../evaluations/searchqa_skillopt_best_parallel_20261123_011258/retest_1/test/batch/records.json) |
| 最终 Skill 复测 | deepseek-flash | 1,180/1,400 | 90.98% | [受测 Skill](results/searchqa_skillopt_best_parallel_20261123_011258/retest_2/test/skill.md) · [摘要](results/searchqa_skillopt_best_parallel_20261123_011258/retest_2/test/report.json) · [评测计划](../../../../evaluations/searchqa_skillopt_best_parallel_20261123_011258/retest_2/test/plan.json) · [原始逐题回执](../../../../evaluations/searchqa_skillopt_best_parallel_20261123_011258/retest_2/test/batch/records.json) |
| Epoch 末 | deepseek-flash | 1,169/1,400 | 90.46% | [受测 Skill](results/searchqa_skillopt_epoch_end_skill_v0010_20261123/skill.md) · [摘要](results/searchqa_skillopt_epoch_end_skill_v0010_20261123/report.json) · [评测计划](../../../../evaluations/searchqa_skillopt_epoch_end_skill_v0010_20261123/plan.json) · [原始逐题回执](../../../../evaluations/searchqa_skillopt_epoch_end_skill_v0010_20261123/batch/records.json) |
| Epoch 末复测 | deepseek-flash | 1,177/1,400 | 90.78% | [受测 Skill](results/searchqa_skillopt_epoch_end_skill_v0010_20261123_retest_1/skill.md) · [摘要](results/searchqa_skillopt_epoch_end_skill_v0010_20261123_retest_1/report.json) · [评测计划](../../../../evaluations/searchqa_skillopt_epoch_end_skill_v0010_20261123_retest_1/plan.json) · [原始逐题回执](../../../../evaluations/searchqa_skillopt_epoch_end_skill_v0010_20261123_retest_1/batch/records.json) |

[历史验收清单](../../../../benchmarks/searchqa/remaining-history.json) · [SearchQA 实验索引](../../../SEARCHQA.md)
