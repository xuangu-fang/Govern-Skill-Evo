# v28_11_aligned_batch60_20261116_123000

11 月 16 日 12:30 对齐训练完成十轮，每轮 60 道训练题及同批 Parent／Candidate 验证。R04 沿用 R03，R05 发布最终 Skill，R06–R10 沿用。

[冻结训练配置](config/frozen.json) · [完成回执](reports/native/checkpoint.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [原始训练](../../../../../baselines/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000) · [运行入口](../../../../../../scripts/runs/run_searchqa_skilladam.py)

## Test1400

全部评测使用 DeepSeek Flash。主图采用一列标明逐轮、逐步取值及用于最终中位数的复测。

| 评测 | EM 题数 | 主图采用 | 证据 |
| --- | ---: | --- | --- |
| 最终 Skill 首测 | 1,160/1,400 | 最终中位数 | [受测 Skill](results/v28_11_aligned_batch60_20261116_123000/skill.md) · [摘要](results/v28_11_aligned_batch60_20261116_123000/report.json) · [原始评测计划](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000/plan.json) · [原始逐题日志](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000/batch/records.json) |
| 最终 Skill 第 1 次复测 | 1,164/1,400 | 最终中位数 | [受测 Skill](results/v28_11_aligned_batch60_20261116_123000_retest_20261116_134454/skill.md) · [摘要](results/v28_11_aligned_batch60_20261116_123000_retest_20261116_134454/report.json) · [原始评测计划](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_retest_20261116_134454/plan.json) · [原始逐题日志](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_retest_20261116_134454/batch/records.json) |
| 最终 Skill 第 2 次复测 | 1,162/1,400 | 最终中位数 | [受测 Skill](results/v28_11_aligned_batch60_20261116_123000_retest2_20261119_234857/skill.md) · [摘要](results/v28_11_aligned_batch60_20261116_123000_retest2_20261119_234857/report.json) · [原始评测计划](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_retest2_20261119_234857/plan.json) · [原始逐题日志](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_retest2_20261119_234857/batch/records.json) |
| R01 | 1,171/1,400 | R01 | [受测 Skill](results/v28_11_aligned_batch60_20261116_123000_checkpoints/R01/skill.md) · [摘要](results/v28_11_aligned_batch60_20261116_123000_checkpoints/R01/report.json) · [原始评测计划](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_checkpoints/R01/plan.json) · [原始逐题日志](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_checkpoints/R01/batch/records.json) |
| R02 | 1,167/1,400 | R02 | [受测 Skill](results/v28_11_aligned_batch60_20261116_123000_checkpoints/R02/skill.md) · [摘要](results/v28_11_aligned_batch60_20261116_123000_checkpoints/R02/report.json) · [原始评测计划](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_checkpoints/R02/plan.json) · [原始逐题日志](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_checkpoints/R02/batch/records.json) |
| R03、R04 | 1,169/1,400 | R03、R04 | [受测 Skill](results/v28_11_aligned_batch60_20261116_123000_checkpoints/R03/skill.md) · [摘要](results/v28_11_aligned_batch60_20261116_123000_checkpoints/R03/report.json) · [原始评测计划](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_checkpoints/R03/plan.json) · [原始逐题日志](../../../../../evaluations/searchqa_skilladam/v28_11_aligned_batch60_20261116_123000_checkpoints/R03/batch/records.json) |

[原始路径、SHA-256 和核验清单](../../../../../benchmarks/searchqa/main-comparison.json) · [SearchQA 主对照索引](../../../../SEARCHQA.md)
