# v26_officeqa_official_train74_epoch1_20261029_230230

完成训练。已提交 8 轮，配置范围为 74 道优化题。

[冻结训练配置](config/config.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [状态证据](results/state.json) · [原始训练](../../../campaigns/v26_officeqa_official_train74_epoch1_20261029_230230) · [运行入口](../../../../scripts/runs/run_v26_campaign.py)

| 评测 | 已评分／计划 | EM 题数 | 待评 | 证据 |
| --- | ---: | ---: | --- | --- |
| 首测 | 171/172 | 118 | UID0111 | [受测 Skill](results/v26_officeqa_official_test172_20261030_012818/skill.md) · [摘要](results/v26_officeqa_official_test172_20261030_012818/report.json) · [原始评分日志](../../../evaluations/v26_officeqa_official_test172_20261030_012818/batch/actor/results.jsonl) |
| 补测后的完整测试 | 172/172 | 118 | — | [受测 Skill](results/v26_officeqa_UID0111_65536_20261030_025803/skill.md) · [摘要](results/v26_officeqa_UID0111_65536_20261030_025803/combined_report.json) · [原测日志](../../../evaluations/v26_officeqa_official_test172_20261030_012818/batch/actor/results.jsonl) · [补测回执](../../../evaluations/v26_officeqa_UID0111_65536_20261030_025803/result.json) |

[实际路径映射与验收清单](../../../benchmarks/officeqa/v26-remaining.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/v26-remaining.json --method v26
```
