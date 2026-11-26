# skilladam_officeqa_flash41_7rounds_20261116_212008

完成训练。74 道优化题，完成 7 次迭代。

[冻结配置](config/plan.json) · [初始 Skill](config/initial_skill.md) · [最终 Skill](results/final_skill.md) · [状态证据](results/result.json) · [原始训练材料](../../../../../baselines/skilladam_officeqa_flash41_7rounds_20261116_212008) · [历史运行入口](../../../../../../scripts/runs/run_officeqa_skilladam_batch_schedule.py) · [启动和恢复记录](../../../../../launches/skilladam_officeqa_flash41_7rounds_20261116_212008)

| 评测 | 已评分／计划 | EM 题数 | 待评 | 证据 |
| --- | ---: | ---: | --- | --- |
| R00 原测 | 171/172 | 92 | UID0111 | [受测 Skill](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R00/test172/skill.md) · [摘要](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R00/test172/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R00/test172/batch/actor/results.jsonl) |
| 最终 Skill 首测 | 171/172 | 124 | UID0111 | [受测 Skill](results/skilladam_officeqa_flash41_7rounds_20261116_212008_test172/skill.md) · [摘要](results/skilladam_officeqa_flash41_7rounds_20261116_212008_test172/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_test172/batch/actor/results.jsonl) |
| 最终 Skill 复测 | 172/172 | 115 | — | [受测 Skill](results/skilladam_officeqa_flash41_7rounds_20261116_212008_test172_repeat_20261117_114018/skill.md) · [摘要](results/skilladam_officeqa_flash41_7rounds_20261116_212008_test172_repeat_20261117_114018/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_test172_repeat_20261117_114018/batch/actor/results.jsonl) |
| R01 补测 | 2/2 | 1 | — | [受测 Skill](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R01/test172/skill.md) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R01/supplement_01/actor/results.jsonl) |
| R01 原测 | 170/172 | 121 | UID0183、UID0205 | [受测 Skill](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R01/test172/skill.md) · [摘要](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R01/test172/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R01/test172/batch/actor/results.jsonl) |
| R03 原测 | 172/172 | 118 | — | [受测 Skill](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R03/test172/skill.md) · [摘要](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R03/test172/report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R03/test172/batch/actor/results.jsonl) |
| R00 汇总 | 171/172 | 92 | UID0111 | [受测 Skill](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R00/skill.md) · [摘要](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R00/combined_report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R00/test172/batch/actor/results.jsonl) |
| R01 汇总 | 172/172 | 122 | — | [受测 Skill](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R01/skill.md) · [摘要](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R01/combined_report.json) · [原测日志](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R01/test172/batch/actor/results.jsonl) · [补测回执](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R01/supplement_01/actor/results.jsonl) |
| R03 汇总 | 172/172 | 118 | — | [受测 Skill](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R03/skill.md) · [摘要](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R03/combined_report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R03/test172/batch/actor/results.jsonl) |
| R05 汇总 | 171/172 | 124 | UID0111 | [受测 Skill](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R05/skill.md) · [摘要](results/skilladam_officeqa_flash41_7rounds_20261116_212008_round_tests/R05/combined_report.json) · [原始评分日志](../../../../../evaluations/skilladam_officeqa_flash41_7rounds_20261116_212008_test172/batch/actor/results.jsonl) |

[实际路径映射与验收清单](../../../../../benchmarks/officeqa/skilladam-history.json)

在仓库根目录运行。

```sh
python3 scripts/runs/officeqa/verify_comparison.py --manifest experiments/benchmarks/officeqa/skilladam-history.json
```
