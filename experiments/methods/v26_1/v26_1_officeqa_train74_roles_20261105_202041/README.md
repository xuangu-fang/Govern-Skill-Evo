# v26_1_officeqa_train74_roles_20261105_202041

74 道优化题，完成 8 轮训练。最终 Skill 来自 R06。

[冻结训练配置](config/config.json) · [可执行配置副本](../profiles/v26_1_officeqa_train74.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [训练摘要](results/training_summary.json) · [原始训练](../../../campaigns/v26_1_officeqa_train74_roles_20261105_202041) · [运行入口](../../../../scripts/runs/run_v26_1_campaign.py)

| 评测 | Actor | EM 题数 | 证据 |
| --- | --- | ---: | --- |
| R01 测试 | deepseek-flash | 110/172 | [受测 Skill](results/officeqa_checkpoints_20261111/v26_1_R01/skill.md) · [摘要](results/officeqa_checkpoints_20261111/v26_1_R01/summary.json) · [原始评分日志](../../../evaluations/officeqa_checkpoints_20261111/v26_1_R01/runs/actor/results.jsonl) |
| R02 测试 | deepseek-flash | 120/172 | [受测 Skill](results/officeqa_checkpoints_20261111/v26_1_R02/skill.md) · [摘要](results/officeqa_checkpoints_20261111/v26_1_R02/summary.json) · [原始评分日志](../../../evaluations/officeqa_checkpoints_20261111/v26_1_R02/runs/actor/results.jsonl) |
| 最终 Skill 原测 | deepseek-flash | 123/171（缺 UID0111） | [受测 Skill](results/v26_1_officeqa_train74_roles_20261105_202041/skill.md) · [摘要](results/v26_1_officeqa_train74_roles_20261105_202041/incomplete.json) · [原始评分日志](../../../evaluations/v26_1_officeqa_train74_roles_20261105_202041/runs/actor/results.jsonl) |
| 补测后的完整测试 | deepseek-flash | 124/172 | [受测 Skill](results/v26_1_officeqa_UID0111_65536_20261105_225536/skill.md) · [摘要](results/v26_1_officeqa_UID0111_65536_20261105_225536/combined_report.json) · [原测日志](../../../evaluations/v26_1_officeqa_train74_roles_20261105_202041/runs/actor/results.jsonl) · [补测回执](../../../evaluations/v26_1_officeqa_UID0111_65536_20261105_225536/result.json) |
| 最终 Skill 的 v4.1 Flash 限定子集 | deepseek-v4.1-flash | 115/171 | [受测 Skill](results/v26_1_skill_v41flash_w20_20261118_142004/skill.md) · [摘要](results/v26_1_skill_v41flash_w20_20261118_142004/summary.json) · [原始评分日志](../../../evaluations/v26_1_skill_v41flash_w20_20261118_142004/runs/actor/results.jsonl) |

DeepSeek Flash 原测缺 UID0111。该题用相同 Skill、65,536 输出 token 的单题预算补测答对，合并为 124/172。另一次 v4.1 Flash 评测按预先限定的 171 题执行，计划明确排除 UID0111。

[实际路径映射与验收清单](../../../benchmarks/officeqa/v26_1-v26_2.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/v26_1-v26_2.json --method v26.1
```
