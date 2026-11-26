# v28_12_searchqa600_batch60_20261109_024436

训练十轮，每轮 60 题。R09 为最后一次改变保留 Skill 的轮次，R10 沿用。该训练的初始 Skill 用于共用 R00。

[冻结训练配置](config/config.json) · [完成回执](reports/training_summary.json) · [训练状态](reports/state.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [最终训练检查点](../../../campaigns/v28_12_searchqa600_batch60_20261109_024436/rounds/R09/selected.md) · [原始训练](../../../campaigns/v28_12_searchqa600_batch60_20261109_024436) · [运行入口](../../../../scripts/runs/run_v28_12_campaign.py)

## Test1400

全部使用 DeepSeek Flash。每条评测沿用原评测 ID。

| 评测 | EM 题数 | Token F1 | 证据 |
| --- | ---: | ---: | --- |
| R01 保留 Skill | 1,132/1,400 | 89.67% | [受测 Skill](results/searchqa_checkpoints_20261111/v28_12_R01/skill.md) · [摘要](results/searchqa_checkpoints_20261111/v28_12_R01/summary.json) · [原始评测计划](../../../evaluations/searchqa_checkpoints_20261111/v28_12_R01/evaluation.json) · [原始逐题回执](../../../evaluations/searchqa_checkpoints_20261111/v28_12_R01/runs/records.json) |
| R03 保留 Skill | 1,161/1,400 | 90.29% | [受测 Skill](results/searchqa_checkpoints_20261111/v28_12_R03/skill.md) · [摘要](results/searchqa_checkpoints_20261111/v28_12_R03/summary.json) · [原始评测计划](../../../evaluations/searchqa_checkpoints_20261111/v28_12_R03/evaluation.json) · [原始逐题回执](../../../evaluations/searchqa_checkpoints_20261111/v28_12_R03/runs/records.json) |
| R04 保留 Skill | 1,179/1,400 | 91.16% | [受测 Skill](results/searchqa_checkpoints_20261111/v28_12_R04/skill.md) · [摘要](results/searchqa_checkpoints_20261111/v28_12_R04/summary.json) · [原始评测计划](../../../evaluations/searchqa_checkpoints_20261111/v28_12_R04/evaluation.json) · [原始逐题回执](../../../evaluations/searchqa_checkpoints_20261111/v28_12_R04/runs/records.json) |
| R07 保留 Skill | 1,173/1,400 | 90.98% | [受测 Skill](results/searchqa_checkpoints_20261111/v28_12_R07/skill.md) · [摘要](results/searchqa_checkpoints_20261111/v28_12_R07/summary.json) · [原始评测计划](../../../evaluations/searchqa_checkpoints_20261111/v28_12_R07/evaluation.json) · [原始逐题回执](../../../evaluations/searchqa_checkpoints_20261111/v28_12_R07/runs/records.json) |
| R08 保留 Skill | 1,177/1,400 | 91.32% | [受测 Skill](results/searchqa_checkpoints_20261111/v28_12_R08/skill.md) · [摘要](results/searchqa_checkpoints_20261111/v28_12_R08/summary.json) · [原始评测计划](../../../evaluations/searchqa_checkpoints_20261111/v28_12_R08/evaluation.json) · [原始逐题回执](../../../evaluations/searchqa_checkpoints_20261111/v28_12_R08/runs/records.json) |
| 最终 Skill 首测 | 1,172/1,400 | 90.58% | [受测 Skill](results/v28_12_searchqa600_batch60_20261109_024436_test1400/skill.md) · [摘要](results/v28_12_searchqa600_batch60_20261109_024436_test1400/summary.json) · [原始评测计划](../../../evaluations/v28_12_searchqa600_batch60_20261109_024436_test1400/evaluation.json) · [原始逐题回执](../../../evaluations/v28_12_searchqa600_batch60_20261109_024436_test1400/runs/records.json) |
| 最终 Skill 第 1 次复测 | 1,181/1,400 | 91.03% | [受测 Skill](results/v28_12_searchqa600_batch60_20261109_024436_test1400_retest_20261109_123544/skill.md) · [摘要](results/v28_12_searchqa600_batch60_20261109_024436_test1400_retest_20261109_123544/summary.json) · [原始评测计划](../../../evaluations/v28_12_searchqa600_batch60_20261109_024436_test1400_retest_20261109_123544/evaluation.json) · [原始逐题回执](../../../evaluations/v28_12_searchqa600_batch60_20261109_024436_test1400_retest_20261109_123544/runs/records.json) |
| 最终 Skill 第 2 次复测 | 1,177/1,400 | 90.82% | [受测 Skill](results/v28_12_searchqa600_batch60_20261109_024436_test1400_third_20261111/skill.md) · [摘要](results/v28_12_searchqa600_batch60_20261109_024436_test1400_third_20261111/summary.json) · [原始评测计划](../../../evaluations/v28_12_searchqa600_batch60_20261109_024436_test1400_third_20261111/evaluation.json) · [原始逐题回执](../../../evaluations/v28_12_searchqa600_batch60_20261109_024436_test1400_third_20261111/runs/records.json) |

R02 沿用 R01，R05、R06 沿用 R04，R10 沿用 R09。各对保留 Skill 已逐字节核对。[共用 R00](../../../benchmarks/searchqa/controls/searchqa_checkpoints_20261111/R00/README.md) · [原逐轮对照](../../../evaluations/searchqa_checkpoints_20261111/%E9%80%90%E8%BD%AE%E6%B5%8B%E8%AF%95%E7%BB%93%E6%9E%9C.md)

[历史验收清单](../../../benchmarks/searchqa/v28_11-v28_15.json) · [SearchQA 实验索引](../../SEARCHQA.md)
