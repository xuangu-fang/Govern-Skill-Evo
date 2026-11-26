# v28_13_searchqa600_batch60_20261111_220738

训练十轮，每轮 60 题。R10 发布最终保留 Skill，完成首测与一次复测。

[冻结训练配置](config/config.json) · [完成回执](reports/training_summary.json) · [训练状态](reports/state.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [最终训练检查点](../../../campaigns/v28_13_searchqa600_batch60_20261111_220738/rounds/R10/selected.md) · [原始训练](../../../campaigns/v28_13_searchqa600_batch60_20261111_220738) · [运行入口](../../../../scripts/runs/run_v28_13_campaign.py)

## Test1400

全部使用 DeepSeek Flash。每条评测沿用原评测 ID。

| 评测 | EM 题数 | Token F1 | 证据 |
| --- | ---: | ---: | --- |
| 最终 Skill 首测 | 1,179/1,400 | 91.39% | [受测 Skill](results/v28_13_searchqa600_batch60_20261111_220738_test1400/skill.md) · [摘要](results/v28_13_searchqa600_batch60_20261111_220738_test1400/summary.json) · [原始评测计划](../../../evaluations/v28_13_searchqa600_batch60_20261111_220738_test1400/evaluation.json) · [原始逐题回执](../../../evaluations/v28_13_searchqa600_batch60_20261111_220738_test1400/runs/records.json) |
| 最终 Skill 第 1 次复测 | 1,173/1,400 | 91.08% | [受测 Skill](results/v28_13_searchqa600_batch60_20261111_220738_test1400_retest_20261111_231012/skill.md) · [摘要](results/v28_13_searchqa600_batch60_20261111_220738_test1400_retest_20261111_231012/summary.json) · [原始评测计划](../../../evaluations/v28_13_searchqa600_batch60_20261111_220738_test1400_retest_20261111_231012/evaluation.json) · [原始逐题回执](../../../evaluations/v28_13_searchqa600_batch60_20261111_220738_test1400_retest_20261111_231012/runs/records.json) |

[历史验收清单](../../../benchmarks/searchqa/v28_11-v28_15.json) · [SearchQA 实验索引](../../SEARCHQA.md)
