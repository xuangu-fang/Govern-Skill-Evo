# v26_5_officeqa_train74_20261117_165841

完成训练。已提交 7 轮，配置范围为 74 道优化题。

[冻结训练配置](config/config.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [状态证据](results/training_summary.json) · [原始训练](../../../campaigns/v26_5_officeqa_train74_20261117_165841) · [运行入口](../../../../scripts/runs/run_v26_5_campaign.py)

| 评测 | 已评分／计划 | EM 题数 | 待评 | 证据 |
| --- | ---: | ---: | --- | --- |
| 首测 | 171/172 | 116 | UID0171 | [受测 Skill](results/v26_5_officeqa_train74_20261117_165841/skill.md) · [摘要](results/v26_5_officeqa_train74_20261117_165841/incomplete.json) · [原始评分日志](../../../evaluations/v26_5_officeqa_train74_20261117_165841/runs/actor/results.jsonl) |
| 复测 19:47 | 67/172 | 46 | 105 题 | [受测 Skill](results/v26_5_officeqa_final_test172_repeat_20261117_194750/skill.md) · [原始评分日志](../../../evaluations/v26_5_officeqa_final_test172_repeat_20261117_194750/runs/actor/results.jsonl) |
| 复测 20:09 | 171/172 | 117 | UID0111 | [受测 Skill](results/v26_5_officeqa_final_test172_repeat_20261117_200935/skill.md) · [摘要](results/v26_5_officeqa_final_test172_repeat_20261117_200935/incomplete.json) · [原始评分日志](../../../evaluations/v26_5_officeqa_final_test172_repeat_20261117_200935/runs/actor/results.jsonl) |
| 20 并发评测 | 171/172 | 119 | UID0111 | [受测 Skill](results/v26_5_officeqa_final_test172_w20_20261117_214857/skill.md) · [摘要](results/v26_5_officeqa_final_test172_w20_20261117_214857/incomplete.json) · [原始评分日志](../../../evaluations/v26_5_officeqa_final_test172_w20_20261117_214857/runs/actor/results.jsonl) |

[实际路径映射与验收清单](../../../benchmarks/officeqa/v26-remaining.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/v26-remaining.json --method v26.5
```
