# v28_15_searchqa600_batch60_20261112_120121

训练十轮，每轮 60 题。R10 发布最终保留 Skill，完成一次 Test1400。

[冻结训练配置](config/config.json) · [完成回执](reports/training_summary.json) · [训练状态](reports/state.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [最终训练检查点](../../../campaigns/v28_15_searchqa600_batch60_20261112_120121/rounds/R10/selected.md) · [原始训练](../../../campaigns/v28_15_searchqa600_batch60_20261112_120121) · [运行入口](../../../../scripts/runs/run_v28_15_campaign.py)

## Test1400

全部使用 DeepSeek Flash。每条评测沿用原评测 ID。

| 评测 | EM 题数 | Token F1 | 证据 |
| --- | ---: | ---: | --- |
| 最终 Skill 首测 | 1,163/1,400 | 90.68% | [受测 Skill](results/v28_15_searchqa600_batch60_20261112_120121_test1400/skill.md) · [摘要](results/v28_15_searchqa600_batch60_20261112_120121_test1400/summary.json) · [原始评测计划](../../../evaluations/v28_15_searchqa600_batch60_20261112_120121_test1400/evaluation.json) · [原始逐题回执](../../../evaluations/v28_15_searchqa600_batch60_20261112_120121_test1400/runs/records.json) |

[历史验收清单](../../../benchmarks/searchqa/v28_11-v28_15.json) · [SearchQA 实验索引](../../SEARCHQA.md)
