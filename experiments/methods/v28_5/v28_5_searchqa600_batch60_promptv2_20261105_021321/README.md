# v28_5_searchqa600_batch60_promptv2_20261105_021321

完成训练，已记录 10 轮。

[冻结配置](config/config.json) · [进度回执](reports/state.json) · [初始 Skill](config/initial_skill.md) · [原始训练](../../../campaigns/v28_5_searchqa600_batch60_promptv2_20261105_021321) · [运行入口](../../../../scripts/runs/run_v28_5_campaign.py) · [原调度状态](reports/launch/v28_5_searchqa600_batch60_promptv2_20261105_021321/status.json) · [完成回执](reports/training_summary.json) · [最终 Skill](results/final_skill.md)

[原实验说明](../../../automations/v28_5_searchqa600_batch60_promptv2_20261105_021321/README.md) · [原运行快照](../../../campaigns/v28_5_searchqa600_batch60_promptv2_20261105_021321/runtime.json)

## 评测

| 评测 | Actor | EM 题数 | Token F1 | 证据 |
| --- | --- | ---: | ---: | --- |
| 最终 Skill 终测 | deepseek-flash | 1,182/1,400 | 91.11% | [受测 Skill](results/v28_5_searchqa600_batch60_promptv2_20261105_021321_test1400/skill.md) · [摘要](results/v28_5_searchqa600_batch60_promptv2_20261105_021321_test1400/summary.json) · [评测计划](../../../evaluations/v28_5_searchqa600_batch60_promptv2_20261105_021321_test1400/evaluation.json) · [原始逐题回执](../../../evaluations/v28_5_searchqa600_batch60_promptv2_20261105_021321_test1400/runs/records.json) |
| 最终 Skill 复测 | deepseek-flash | 1,186/1,400 | 91.54% | [受测 Skill](results/v28_5_searchqa600_batch60_promptv2_20261105_021321_test1400_retest_20261107_030741/skill.md) · [摘要](results/v28_5_searchqa600_batch60_promptv2_20261105_021321_test1400_retest_20261107_030741/summary.json) · [评测计划](../../../evaluations/v28_5_searchqa600_batch60_promptv2_20261105_021321_test1400_retest_20261107_030741/evaluation.json) · [原始逐题回执](../../../evaluations/v28_5_searchqa600_batch60_promptv2_20261105_021321_test1400_retest_20261107_030741/runs/records.json) |

[历史验收清单](../../../benchmarks/searchqa/remaining-history.json) · [SearchQA 实验索引](../../SEARCHQA.md)
