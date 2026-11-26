# v26_2_officeqa_train74_20261117_013308

74 道优化题，完成 7 轮训练。最终 Skill 来自 R06。

[冻结训练配置](config/config.json) · [可执行配置副本](../profiles/v26_2_officeqa_train74.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [训练摘要](results/training_summary.json) · [原始训练](../../../campaigns/v26_2_officeqa_train74_20261117_013308) · [运行入口](../../../../scripts/runs/run_v26_2_campaign.py)

| 评测 | Actor | EM 题数 | 证据 |
| --- | --- | ---: | --- |
| 最终 Skill 首测 | deepseek-v4.1-flash | 120/171（缺 UID0111） | [受测 Skill](results/v26_2_officeqa_train74_20261117_013308/skill.md) · [摘要](results/v26_2_officeqa_train74_20261117_013308/incomplete.json) · [原始评分日志](../../../evaluations/v26_2_officeqa_train74_20261117_013308/runs/actor/results.jsonl) |
| 最终 Skill 复测 | deepseek-v4.1-flash | 118/171（缺 UID0111） | [受测 Skill](results/v26_2_officeqa_final_test172_repeat_20261117_111113/skill.md) · [摘要](reports/launches/v26_2_officeqa_final_test172_repeat_20261117_111113/stop_report.json) · [原始评分日志](../../../evaluations/v26_2_officeqa_final_test172_repeat_20261117_111113/runs/actor/results.jsonl) |

两次评测均计划执行 Test172，实际评分覆盖相同的 171 个 UID，均缺 UID0111。完整 Test172 的 EM/F1 留空。

[实际路径映射与验收清单](../../../benchmarks/officeqa/v26_1-v26_2.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/v26_1-v26_2.json --method v26.2
```
