# v26_7_officeqa_train74_20261118_023806

完成训练。已提交 7 轮，配置范围为 74 道优化题。

[冻结训练配置](config/config.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [状态证据](results/training_summary.json) · [原始训练](../../../campaigns/v26_7_officeqa_train74_20261118_023806) · [运行入口](../../../../scripts/runs/run_v26_7_campaign.py)

| 评测 | 已评分／计划 | EM 题数 | 待评 | 证据 |
| --- | ---: | ---: | --- | --- |
| 20 并发评测 | 171/172 | 115 | UID0111 | [受测 Skill](results/v26_7_officeqa_final_test172_w20_20261118_023806/skill.md) · [摘要](results/v26_7_officeqa_final_test172_w20_20261118_023806/incomplete.json) · [原始评分日志](../../../evaluations/v26_7_officeqa_final_test172_w20_20261118_023806/runs/actor/results.jsonl) |
| UID0111 同预算补测尝试 | 0/1 | — | UID0111 | [受测 Skill](results/v26_7_officeqa_final_test172_w20_20261118_023806/supplement_UID0111_same_budget_01/skill.md) · [摘要](results/v26_7_officeqa_final_test172_w20_20261118_023806/supplement_UID0111_same_budget_01/incomplete.json) · [原始评分日志](../../../evaluations/v26_7_officeqa_final_test172_w20_20261118_023806/supplement_UID0111_same_budget_01/runs/actor/results.jsonl) |

[R06 两题专项](../../../benchmarks/officeqa/comparisons/v26_8_v26_7_R06_percent_20261118_114935/README.md)

[实际路径映射与验收清单](../../../benchmarks/officeqa/v26-remaining.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/v26-remaining.json --method v26.7
```
